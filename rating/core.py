#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ECHORATE core v4.0. Единственный источник математики для всех движков.

Правило проекта: цифра без источника не существует. Каждая функция здесь либо
считает по опубликованной формуле, либо падает с понятной ошибкой.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

VERSION = "4.0"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


MODEL = _load("model.json")
LEAGUE_WEIGHTS = {p: {k: float(v) for k, v in w.items()} for p, w in MODEL["league_weights"].items()}
SEASON_WEIGHTS = {k: float(v) for k, v in MODEL["season_weights"].items()}
STAT_ORDER = tuple(MODEL["stat_order"])
STAT_LABELS = MODEL["stat_labels"]
POSITION_LABELS = MODEL["position_labels"]
LO, HI = (float(x) for x in MODEL["clamp"])
EPS = 1e-9

for _pos, _w in LEAGUE_WEIGHTS.items():
    assert abs(sum(_w.values()) - 1.0) < EPS, f"{_pos}: веса не дают 100 процентов"
    assert _w["T"] + _w["S"] + _w["D"] <= 0.5 + EPS, f"{_pos}: судейская часть выше половины"
assert abs(sum(SEASON_WEIGHTS.values()) - 1.0) < EPS, "season: веса не дают 100 процентов"


class DataError(ValueError):
    """Данных не хватает или они без источника."""


def rnd(value: float) -> int:
    return int(math.floor(float(value) + 0.5))


def clamp(value: float, lo: float = LO, hi: float = HI) -> float:
    return max(lo, min(hi, float(value)))


def _positive(value, field: str, who: str) -> float:
    if value is None:
        raise DataError(f"{who}: поле {field} пустое")
    value = float(value)
    if value <= 0:
        raise DataError(f"{who}: поле {field} должно быть больше нуля, получено {value}")
    return value


# ---------------------------------------------------------------- лига

def hits(top5, who: str = "?") -> float:
    """ХИТЫ = 70 + 6 * log2(top5 / 60 000 000). Меряет прослушивания пяти лучших треков."""
    return clamp(70 + 6 * math.log2(_positive(top5, "top5", who) / 60_000_000))


def lives(cap, cities, festival: bool = False, who: str = "?") -> float:
    """ЛАЙВЫ = 70 + 5 * log2(cap_eff / 10 000) + min(6, max(0, cities - 5)).
    Фестивальная площадка идёт с коэффициентом 0,6."""
    cap_eff = _positive(cap, "cap", who) * (0.6 if festival else 1.0)
    if cities is None:
        raise DataError(f"{who}: поле cities пустое")
    cities = int(cities)
    if cities < 0:
        raise DataError(f"{who}: cities не может быть отрицательным")
    return clamp(70 + 5 * math.log2(cap_eff / 10_000) + min(6, max(0, cities - 5)))


def influence(catalog, scene, who: str = "?") -> float:
    """ВЛИЯНИЕ = 70 + 6 * log2(catalog / 300 000 000) + scene. Меряет масштаб каталога."""
    if scene is None:
        raise DataError(f"{who}: поле scene пустое, оно всегда число от -6 до 6")
    scene = float(scene)
    if not -6 <= scene <= 6:
        raise DataError(f"{who}: scene вне диапазона от -6 до 6, получено {scene}")
    return clamp(70 + 6 * math.log2(_positive(catalog, "catalog", who) / 300_000_000) + scene)


def age_bonus(age) -> int:
    if age is None:
        return int(MODEL["age_bonus_unknown"])
    for limit, bonus in MODEL["age_bonus"]:
        if int(age) <= int(limit):
            return int(bonus)
    return int(MODEL["age_bonus_default"])


def form_bonus(change) -> int:
    if change is None:
        return 0
    cfg = MODEL["form_bonus"]
    if float(change) > cfg["up_threshold"]:
        return int(cfg["up"])
    if float(change) < cfg["down_threshold"]:
        return int(cfg["down"])
    return 0


def age_at(born: str | None, on: str) -> int | None:
    """Возраст на дату снимка. Хардкод возраста в коде устаревает каждый год, дата рождения нет."""
    if not born:
        return None
    b = date.fromisoformat(born)
    d = date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def price(ovr: int, potential: int) -> int:
    """ЦЕНА = 3 * 2^((OVR - 55) / 5) * (1 + (ПОТЕНЦИАЛ - OVR) / 40), в миллионах евро.
    Это функция от опубликованного балла, а не заявление о реальной стоимости артиста."""
    cfg = MODEL["price"]
    base = cfg["base"] * 2 ** ((ovr - cfg["pivot"]) / cfg["halving"])
    return rnd(base * (1 + (potential - ovr) / cfg["potential_divisor"]))


REQUIRED_SOURCES = ("src_top5", "src_live", "src_scene")


def rate(artist: dict, snapshot: str | None = None) -> dict:
    """Считает одного артиста лиги. Без трёх источников артист не считается."""
    who = artist.get("name", artist.get("key", "?"))
    missing = [k for k in REQUIRED_SOURCES if not artist.get(k)]
    if missing:
        raise DataError(f"{who}: нет источников {missing}")
    if artist["pos"] not in LEAGUE_WEIGHTS:
        raise DataError(f"{who}: позиция {artist['pos']} не описана в model.json")
    for key in ("T", "S", "D"):
        value = artist.get(key)
        if value is None:
            raise DataError(f"{who}: судейский балл {key} не выставлен")
        if not 30 <= int(value) <= 99:
            raise DataError(f"{who}: судейский балл {key}={value} вне шкалы 30 до 99")

    stats = {
        "T": int(artist["T"]), "S": int(artist["S"]), "D": int(artist["D"]),
        "H": rnd(hits(artist["top5"], who)),
        "L": rnd(lives(artist["cap"], artist["cities"], bool(artist.get("fest")), who)),
        "I": rnd(influence(artist["catalog"], artist["scene"], who)),
    }
    weights = LEAGUE_WEIGHTS[artist["pos"]]
    raw = sum(stats[k] * weights[k] for k in STAT_ORDER)
    ovr = rnd(raw)

    age = artist.get("age")
    if artist.get("born") and snapshot:
        age = age_at(artist["born"], snapshot)
    bonus = age_bonus(age) + form_bonus(artist.get("form"))
    potential = min(int(HI), max(ovr, ovr + bonus))

    return {
        "key": artist["key"], "name": artist["name"], "pos": artist["pos"],
        "age": age, "stats": stats, "raw": round(raw, 2), "ovr": ovr,
        "potential": potential, "gap": potential - ovr,
        "price_mln": price(ovr, potential),
        "was": artist.get("was"), "accuracy": artist.get("accuracy", "B"),
        "sources": {k: artist[k] for k in REQUIRED_SOURCES},
    }


def load_artists(path: Path | None = None) -> tuple[dict, list[dict]]:
    payload = json.loads((path or DATA / "artists.json").read_text(encoding="utf-8"))
    return payload, payload["artists"]


def league(path: Path | None = None) -> dict:
    payload, artists = load_artists(path)
    snapshot = payload["snapshot"]
    rows, skipped = [], []
    for artist in artists:
        if not artist.get("in_league"):
            skipped.append({"key": artist["key"], "name": artist["name"], "reason": "резерв"})
            continue
        try:
            rows.append(rate(artist, snapshot))
        except DataError as err:
            skipped.append({"key": artist["key"], "name": artist["name"], "reason": str(err)})
    rows.sort(key=lambda r: (-r["ovr"], -r["raw"], r["name"]))
    for number, row in enumerate(rows, 1):
        row["rank"] = number
    return {"version": VERSION, "snapshot": snapshot, "rounding": MODEL["rounding"],
            "rows": rows, "skipped": skipped}


# ---------------------------------------------------------------- сезон

OUTSIDE = float(MODEL["season_outside_top10"])
ROLE_PENALTY = MODEL["season_role_penalty"]


def season_hits(rank, role: str = "lead") -> float:
    if rank is None or int(rank) > 10:
        return clamp(OUTSIDE)
    if role not in ROLE_PENALTY:
        raise DataError(f"роль {role} не описана в model.json")
    return clamp(96 - 8 * math.log2(int(rank)) + ROLE_PENALTY[role])


def season_influence(album_rank, vote_rank=None) -> float:
    base = OUTSIDE if album_rank is None or int(album_rank) > 10 else 96 - 7 * math.log2(int(album_rank))
    top = int(MODEL["season_vote_bonus_max_rank"])
    bonus = max(0.0, 6 - int(vote_rank)) if vote_rank is not None and int(vote_rank) <= top else 0.0
    return clamp(base + bonus)


def season_score(entry: dict) -> dict:
    h = season_hits(entry.get("tr"), entry.get("role", "lead"))
    i = season_influence(entry.get("alb"), entry.get("vote"))
    raw = (entry["T"] * SEASON_WEIGHTS["T"] + entry["S"] * SEASON_WEIGHTS["S"]
           + entry["D"] * SEASON_WEIGHTS["D"] + h * SEASON_WEIGHTS["H"] + i * SEASON_WEIGHTS["I"])
    spots = entry.get("spots") or []
    return {**entry, "H": round(h, 2), "I": round(i, 2), "raw": round(raw, 2), "ovr": rnd(raw),
            "tie_count": len(spots), "tie_best": min(spots) if spots else 99}


def season_solve(pool: list[dict]) -> list[dict]:
    """Группы собираются от якоря-лидера с порогом 1,0. Транзитивная склейка запрещена."""
    threshold = float(MODEL["season_tiebreak_threshold"])
    rows = sorted((season_score(a) for a in pool), key=lambda x: -x["raw"])
    groups: list[list[dict]] = []
    current: list[dict] = []
    for row in rows:
        if not current or current[0]["raw"] - row["raw"] < threshold:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    if current:
        groups.append(current)
    ordered: list[dict] = []
    for group in groups:
        if len(group) > 1:
            group.sort(key=lambda x: (-x["tie_count"], x["tie_best"], x.get("vote") or 99, -x["raw"]))
            for row in group:
                row["tiebreak"] = True
        ordered.extend(group)
    for place, row in enumerate(ordered, 1):
        row["place"] = place
    return ordered
