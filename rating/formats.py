#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Движки новых форматов v4.0.

    python3 formats.py all
    python3 formats.py hidden
    python3 formats.py squad --json
    python3 formats.py toty --year 2017

Каждый движок возвращает ready и blocked_by. Формат, который нельзя собрать честно,
не собирается вовсе. Пустая позиция лучше выдуманного числа.
"""
from __future__ import annotations

import argparse
import json
from itertools import combinations

import core
import season as season_mod

SNAPSHOT_YEAR = int(core.load_artists()[0]["snapshot"][:4])


def _league_rows() -> list[dict]:
    return core.league()["rows"]


# ---------------------------------------------------------------- НОВИЧКИ

def rookies(year: int = SNAPSHOT_YEAR) -> dict:
    """Новичок это дебют не раньше чем год назад и возраст до порога."""
    cfg = core.MODEL["rookie"]
    floor_year = year - int(cfg["max_years_since_debut"])
    rows = [r for r in _league_rows()]
    payload, artists = core.load_artists()
    debut = {a["key"]: a.get("debut_year") for a in artists}
    picks = [r for r in rows if debut.get(r["key"]) and debut[r["key"]] >= floor_year
             and (r["age"] is None or r["age"] <= cfg["max_age"])]
    blocked = []
    if not picks:
        blocked.append("в базе нет артистов с дебютом под ценз")
        blocked.append(f"нужно добавить 6 до 8 артистов дебюта {floor_year} и {year} с тремя источниками каждый")
    return {"format": "НОВИЧКИ", "year": year, "ready": bool(picks),
            "rule": f"дебют не раньше {floor_year}", "rows": picks, "blocked_by": blocked}


# ---------------------------------------------------------------- WONDERKIDS

def wonderkids() -> dict:
    """Высокий потенциал при малом возрасте. Запас это ПОТЕНЦИАЛ минус OVR."""
    cfg = core.MODEL["wonderkid"]
    rows = _league_rows()
    picks = [r for r in rows if r["age"] is not None and r["age"] <= cfg["max_age"]
             and r["gap"] >= cfg["min_gap"]]
    picks.sort(key=lambda r: (-r["gap"], -r["potential"], r["age"]))
    blocked = []
    if not picks:
        ages = [r["age"] for r in rows if r["age"] is not None]
        youngest = min(ages) if ages else None
        blocked.append(f"самый молодой в лиге старше {cfg['max_age']}" if youngest else "нет возрастов")
        blocked.append("формат требует минимум 5 артистов до 24 лет в базе")
    if any(r["age"] is None for r in rows):
        blocked.append("у 9MICE возраст без источника, это тоже блокер")
    return {"format": "WONDERKIDS", "ready": bool(picks),
            "rule": f"возраст до {cfg['max_age']} и запас от {cfg['min_gap']}",
            "rows": picks, "blocked_by": blocked}


# ---------------------------------------------------------------- СКРЫТЫЙ ПОТЕНЦИАЛ

def hidden() -> dict:
    """Ремесло высокое, охват низкий. РАЗРЫВ = (T + S + D)/3 - (H + I)/2."""
    cfg = core.MODEL["hidden"]
    rows = []
    for row in _league_rows():
        s = row["stats"]
        craft = (s["T"] + s["S"] + s["D"]) / 3
        reach = (s["H"] + s["I"]) / 2
        rows.append({**row, "craft": round(craft, 2), "reach": round(reach, 2),
                     "hidden_gap": round(craft - reach, 2),
                     "qualifies": craft - reach >= cfg["min_gap"]})
    rows.sort(key=lambda r: -r["hidden_gap"])
    picks = [r for r in rows if r["qualifies"]]
    return {"format": "СКРЫТЫЙ ПОТЕНЦИАЛ", "ready": bool(picks),
            "rule": f"РАЗРЫВ = (ТЕКСТЫ + ЗВУК + ПОДАЧА) / 3 - (ХИТЫ + ВЛИЯНИЕ) / 2, порог {cfg['min_gap']}",
            "rows": rows, "winners": picks, "blocked_by": [] if picks else ["ни у кого нет разрыва выше порога"]}


# ---------------------------------------------------------------- PUSKAS

def puskas() -> dict:
    """Номинанты берутся только из файла с источниками. Придумывать их запрещено."""
    cfg = core.MODEL["puskas"]
    path = core.DATA / "puskas.json"
    if not path.exists():
        return {"format": "PUSKAS", "ready": False, "rows": [],
                "blocked_by": ["нет файла puskas.json с номинантами",
                               f"нужно ровно {cfg['nominees']} номинантов с источником на каждый"]}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for item in data.get("nominees", []):
        score = item["jury"] * cfg["jury_weight"] + item["vote"] * cfg["vote_weight"]
        rows.append({**item, "score": round(score, 2), "ovr": core.rnd(score)})
    rows.sort(key=lambda r: -r["score"])
    blocked = [] if len(rows) == cfg["nominees"] else [f"нужно {cfg['nominees']} номинантов, есть {len(rows)}"]
    return {"format": "PUSKAS", "ready": not blocked, "rows": rows, "blocked_by": blocked}


# ---------------------------------------------------------------- ТРИО ЗА 200 МЛН

def squad(budget: int | None = None) -> dict:
    """Три артиста разных позиций в бюджет.

    Важно. Механика трансферной стоимости была отклонена навсегда как выдуманная цифра
    без источника. Здесь цена это опубликованная функция от OVR и ПОТЕНЦИАЛА, а не оценка
    реальной стоимости человека. Формулу обязательно показывать на кадре.
    """
    cfg = core.MODEL["price"]
    budget = budget or int(cfg["budget_mln"])
    size = int(cfg["squad_size"])
    rows = _league_rows()
    valid = []
    for combo in combinations(rows, size):
        total = sum(r["price_mln"] for r in combo)
        if total > budget:
            continue
        if cfg["distinct_positions"] and len({r["pos"] for r in combo}) != size:
            continue
        valid.append({"names": [r["name"] for r in combo], "cost": total,
                      "ovr_sum": sum(r["ovr"] for r in combo), "left": budget - total})
    valid.sort(key=lambda x: (-x["ovr_sum"], x["cost"]))
    blocked = []
    if len(valid) < 6:
        blocked.append(f"вариантов всего {len(valid)}, для игры с зрителем нужно от 6")
        blocked.append("лигу надо расширить минимум до 9 артистов")
    return {"format": "ТРИО ЗА 200 МЛН", "ready": not blocked, "budget": budget,
            "formula": cfg["_formula"], "prices": [
                {"name": r["name"], "pos": r["pos"], "ovr": r["ovr"],
                 "potential": r["potential"], "price_mln": r["price_mln"]} for r in rows],
            "combos": valid, "blocked_by": blocked}


# ---------------------------------------------------------------- ICONS

def icons() -> dict:
    """Пиковый год артиста по всем посчитанным сезонам."""
    cfg = core.MODEL["icon"]
    payload, artists = core.load_artists()
    debut = {a["name"]: a.get("debut_year") for a in artists}
    best: dict[str, dict] = {}
    for year in season_mod.available():
        result = season_mod.solve_year(year)
        if result["status"] != "ok":
            continue
        for row in result["rows"]:
            prev = best.get(row["n"])
            if not prev or row["ovr"] > prev["ovr"]:
                best[row["n"]] = {"name": row["n"], "peak_year": int(year), "ovr": row["ovr"],
                                  "place": row["place"], "pos": row["pos"]}
    rows = sorted(best.values(), key=lambda r: -r["ovr"])
    for row in rows:
        d = debut.get(row["name"])
        row["debut_year"] = d
        row["qualifies"] = bool(d and SNAPSHOT_YEAR - d >= cfg["min_years_since_debut"])
    return {"format": "ICONS", "ready": bool(rows),
            "rule": f"дебют не позже {SNAPSHOT_YEAR - int(cfg['min_years_since_debut'])}",
            "rows": rows, "blocked_by": [] if rows else ["нет посчитанных сезонов"]}


# ---------------------------------------------------------------- TOTY

def toty(year: int | str = 2017) -> dict:
    team = season_mod.toty(year)
    blocked = []
    if team["status"] == "ok" and team["empty"]:
        blocked.append(f"пустые позиции: {', '.join(team['empty'])}")
        blocked.append("в пуле нет кандидатов на эту позицию, чужая туда не ставится")
    return {"format": "TOTY", "ready": team["status"] == "ok" and not team.get("empty"),
            **team, "blocked_by": blocked + team.get("blocked_by", [])}


ENGINES = {"rookies": rookies, "wonderkids": wonderkids, "hidden": hidden,
           "puskas": puskas, "squad": squad, "icons": icons, "toty": toty}


def _print(result: dict) -> None:
    print("=" * 74)
    print(f"{result['format']}   готовность: {'ДА' if result.get('ready') else 'НЕТ'}")
    if result.get("rule"):
        print(f"правило: {result['rule']}")
    print("=" * 74)

    if result["format"] == "СКРЫТЫЙ ПОТЕНЦИАЛ":
        for row in result["rows"]:
            mark = "  <-- герой" if row["qualifies"] else ""
            print(f"  {row['name']:<13} ремесло {row['craft']:>6} охват {row['reach']:>6} "
                  f"разрыв {row['hidden_gap']:>+7}{mark}")
    elif result["format"] == "ТРИО ЗА 200 МЛН":
        print(f"  формула: {result['formula']}")
        for row in result["prices"]:
            print(f"  {row['name']:<13} {row['pos']:<4} OVR {row['ovr']:>3}  ПОТ {row['potential']:>3}  {row['price_mln']:>4} млн")
        print(f"  вариантов трио в бюджете {result['budget']}: {len(result['combos'])}")
        for combo in result["combos"]:
            print(f"    {combo['cost']:>3} млн  сумма OVR {combo['ovr_sum']:>3}  остаток {combo['left']:>3}  "
                  f"{' + '.join(combo['names'])}")
    elif result["format"] == "ICONS":
        for row in result["rows"]:
            mark = "" if row["qualifies"] else "  ценз не пройден"
            print(f"  {row['name']:<15} пик {row['peak_year']}  OVR {row['ovr']:>3}  место {row['place']}{mark}")
    elif result["format"] == "TOTY":
        for slot, pick in result.get("slots", {}).items():
            label = core.POSITION_LABELS.get(slot, "")
            value = f"{pick['name']:<18}{pick['ovr']:>3}" if pick else "пусто"
            print(f"  {slot:<3} {label:<15} {value}")
    else:
        for row in result.get("rows", []):
            print(f"  {row.get('name', row.get('n')):<15} {row.get('ovr', '')}")

    for item in result.get("blocked_by", []):
        print(f"  БЛОКЕР: {item}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Движки форматов ECHORATE")
    parser.add_argument("engine", nargs="?", default="all",
                        help="all или один из: " + ", ".join(ENGINES))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args(argv)

    names = list(ENGINES) if args.engine == "all" else [args.engine]
    for name in names:
        if name not in ENGINES:
            print(f"нет движка {name}. Есть: {', '.join(ENGINES)}")
            return 1

    payload = []
    for name in names:
        fn = ENGINES[name]
        result = fn(args.year) if args.year and name in ("rookies", "toty") else fn()
        payload.append(result)
        if not args.json:
            _print(result)
    if args.json:
        print(json.dumps(payload if len(payload) > 1 else payload[0], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
