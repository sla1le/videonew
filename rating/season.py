#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Золотой микрофон сезона v4.1.

    python3 season.py 2018            таблица сезона
    python3 season.py --all           все доступные сезоны
    python3 season.py 2018 --toty     сборная года
    python3 season.py 2018 --json     машинный вывод

Сезон без опубликованных итогов не считается. Он печатает список того, чего не хватает.
Пулы годов лежат в data/seasons_input.json, в коде их нет.
"""
from __future__ import annotations

import argparse
import json

import core

SEASONS = core._load("seasons_input.json")["seasons"]


def available() -> list[str]:
    return sorted(SEASONS)


def solve_year(year: str | int) -> dict:
    year = str(year)
    if year not in SEASONS:
        raise core.DataError(f"сезон {year} не описан. Есть: {', '.join(available())}")
    season = SEASONS[year]
    if season["status"] != "published":
        return {"year": year, "status": season["status"], "rows": [],
                "blocked_by": season.get("blocked_by", []),
                "legacy_result": season.get("legacy_result"),
                "legacy_model": season.get("legacy_model")}
    rows = core.season_solve(season["pool"])
    return {"year": year, "status": "ok", "source": season.get("source"),
            "scope": season.get("scope"), "excluded": season.get("excluded", []),
            "published_top3": season.get("published_top3"), "rows": rows}


def toty(year: str | int) -> dict:
    """Сборная года. Пустая позиция остаётся пустой, чужая туда не ставится."""
    result = solve_year(year)
    slots = core.MODEL["toty"]["slots"]
    if result["status"] != "ok":
        return {"year": str(year), "status": result["status"],
                "slots": {s: None for s in slots}, "blocked_by": result.get("blocked_by", [])}
    taken: set[str] = set()
    picks: dict[str, dict | None] = {}
    for slot in slots:
        pool = [r for r in result["rows"] if r["pos"] == slot and r["n"] not in taken]
        if pool:
            best = max(pool, key=lambda r: (r["ovr"], r["raw"]))
            picks[slot] = {"name": best["n"], "ovr": best["ovr"], "place": best["place"]}
            taken.add(best["n"])
        else:
            picks[slot] = None
    filled = [v for v in picks.values() if v]
    return {"year": str(year), "status": "ok", "scheme": core.MODEL["toty"]["scheme"],
            "slots": picks, "filled": len(filled), "empty": [k for k, v in picks.items() if not v],
            "team_ovr": round(sum(v["ovr"] for v in filled) / len(filled), 2) if filled else None}


def print_year(result: dict) -> None:
    year = result["year"]
    if result["status"] != "ok":
        print(f"ЗОЛОТОЙ МИКРОФОН {year}: не считается, статус {result['status']}")
        for item in result.get("blocked_by", []):
            print(f"  требуется: {item}")
        if result.get("legacy_result"):
            print(f"  старый результат по дореформенной модели: {result['legacy_result']}")
            print("  эти баллы несравнимы с остальными сезонами, в выпуск их брать нельзя")
        return
    print(f"ЗОЛОТОЙ МИКРОФОН {year}   источник: {result.get('source')}")
    if result.get("scope"):
        print(f"объём оценки: {result['scope']}")
    print("-" * 86)
    print(f"{'#':>2} {'АРТИСТ':<20} {'ПОЗ':<4} {'Т':>3} {'З':>3} {'П':>3} {'ТР':>3} {'АЛБ':>4} {'ХИТЫ':>6} {'ВЛИЯ':>6} {'RAW':>7} {'OVR':>4}")
    print("-" * 86)
    for row in result["rows"]:
        mark = " TB" if row.get("tiebreak") else ""
        tr = row.get("tr") if row.get("tr") is not None else "−"
        alb = row.get("alb") if row.get("alb") is not None else "−"
        print(f"{row['place']:>2} {row['n']:<20} {row['pos']:<4} {row['T']:>3} {row['S']:>3} {row['D']:>3} "
              f"{str(tr):>3} {str(alb):>4} {row['H']:>6.2f} {row['I']:>6.2f} {row['raw']:>7.2f} {row['ovr']:>4}{mark}")
    print("-" * 86)
    for item in result.get("excluded", []):
        print(f"  вне зачёта: {item['n']}, {item.get('why', '')}")
    if result.get("published_top3"):
        got = [(r["n"], r["ovr"]) for r in result["rows"][:3]]
        want = [tuple(x) for x in result["published_top3"]]
        print(f"  опубликовано: {want}")
        print(f"  посчитано:   {got}")
        print(f"  совпадение: {'да' if got == want else 'НЕТ, разбираемся до выпуска'}")
    if any(r.get("tiebreak") for r in result["rows"]):
        print("  TB это тайбрейк: число попаданий в топы, затем лучшее место, затем голосование")


def print_toty(team: dict) -> None:
    if team["status"] != "ok":
        print(f"СБОРНАЯ {team['year']}: не собирается, статус {team['status']}")
        for item in team.get("blocked_by", []):
            print(f"  требуется: {item}")
        return
    print(f"СБОРНАЯ {team['year']}   схема {team['scheme']}   средний балл {team['team_ovr']}")
    print("-" * 60)
    for slot, pick in team["slots"].items():
        label = core.POSITION_LABELS.get(slot, "")
        if pick:
            print(f"  {slot:<3} {label:<15} {pick['name']:<18} {pick['ovr']:>3}")
        else:
            print(f"  {slot:<3} {label:<15} пусто, нет кандидатов")
    if team["empty"]:
        print(f"  Пустые позиции: {', '.join(team['empty'])}. На кадре говорим об этом прямо.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Золотой микрофон сезона")
    parser.add_argument("year", nargs="?", help="год, например 2018")
    parser.add_argument("--all", action="store_true", help="все сезоны")
    parser.add_argument("--toty", action="store_true", help="сборная года")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    args = parser.parse_args(argv)

    years = available() if args.all or not args.year else [args.year]
    payload = []
    for year in years:
        item = toty(year) if args.toty else solve_year(year)
        payload.append(item)
        if not args.json:
            (print_toty if args.toty else print_year)(item)
            print()
    if args.json:
        print(json.dumps(payload if len(payload) > 1 else payload[0], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
