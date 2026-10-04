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


class DataError(ValueError):
    """Данных не хватает или они без источника."""

for _pos, _w in LEAGUE_WEIGHTS.items():
    if abs(sum(_w.values()) - 1.0) >= EPS:
        raise DataError(f"{_pos}: веса не дают 100 процентов")
    if _w["T"] + _w["S"] + _w["D"] > 0.5 + EPS:
        raise DataError(f"{_pos}: судейская часть выше половины")
if abs(sum(SEASON_WEIGHTS.values()) - 1.0) >= EPS:
    raise DataError("season: веса не дают 100 процентов")


def rnd(value: float) -> int:
    return int(math.floor(float(value) + 0.5))


def clamp(value: float, lo: float = LO, hi: float = HI) -> float:
    return max(lo, min(hi, float(value)))


def _positive(value, field: str, who: str) -> float:
    if value is None:
        raise DataError(f"{who}: поле {field} пустое")
    try:
        value = float(value)
    except (TypeError, ValueError) as err:
        raise DataError(f"{who}: поле {field} должно быть числом") from err
    if not math.isfinite(value) or value <= 0:
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
    try:
        city_count = float(cities)
    except (TypeError, ValueError) as err:
        raise DataError(f"{who}: cities должно быть целым числом") from err
    if not math.isfinite(city_count) or not city_count.is_integer() or city_count < 0:
        raise DataError(f"{who}: cities должно быть неотрицательным целым числом")
    cities = int(city_count)
    return clamp(70 + 5 * math.log2(cap_eff / 10_000) + min(6, max(0, cities - 5)))


def influence(catalog, scene, who: str = "?") -> float:
    """ВЛИЯНИЕ = 70 + 6 * log2(catalog / 300 000 000) + scene. Меряет масштаб каталога."""
    if scene is None:
        raise DataError(f"{who}: поле scene пустое, оно всегда число от -6 до 6")
    try:
        scene = float(scene)
    except (TypeError, ValueError) as err:
        raise DataError(f"{who}: scene должно быть числом от -6 до 6") from err
    if not math.isfinite(scene) or not -6 <= scene <= 6:
        raise DataError(f"{who}: scene вне диапазона от -6 до 6, получено {scene}")
    return clamp(70 + 6 * math.log2(_positive(catalog, "catalog", who) / 300_000_000) + scene)


def age_bonus(age) -> int:
    if age is None:
        return int(MODEL["age_bonus_unknown"])
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        raise DataError(f"возраст должен быть неотрицательным целым числом, получено {age!r}")
    for limit, bonus in MODEL["age_bonus"]:
        if int(age) <= int(limit):
            return int(bonus)
    return int(MODEL["age_bonus_default"])


def form_bonus(change) -> int:
    if change is None:
        return 0
    try:
        change = float(change)
    except (TypeError, ValueError) as err:
        raise DataError("form должна быть числом") from err
    if not math.isfinite(change):
        raise DataError("form должна быть конечным числом")
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
    try:
        b = date.fromisoformat(born)
        d = date.fromisoformat(on)
    except (TypeError, ValueError) as err:
        raise DataError(f"некорректная дата рождения или снимка: {born!r}, {on!r}") from err
    if b > d:
        raise DataError(f"дата рождения {born} позже даты снимка {on}")
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def price(ovr: int, potential: int) -> int:
    """ЦЕНА = 3 * 2^((OVR - 55) / 5) * (1 + (ПОТЕНЦИАЛ - OVR) / 40), в миллионах евро.
    Это функция от опубликованного балла, а не заявление о реальной стоимости артиста."""
    cfg = MODEL["price"]
    base = cfg["base"] * 2 ** ((ovr - cfg["pivot"]) / cfg["halving"])
    return rnd(base * (1 + (potential - ovr) / cfg["potential_divisor"]))


REQUIRED_SOURCES = ("src_top5", "src_live", "src_scene")
SOURCE_FIELDS = {"kind", "url", "captured_at", "value", "archive_url", "description", "status"}


def validate_source(source, field: str, who: str) -> None:
    if not isinstance(source, dict):
        raise DataError(f"{who}: {field} должен быть структурированной записью источника")
    missing = SOURCE_FIELDS - source.keys()
    if missing:
        raise DataError(f"{who}: {field} не содержит поля {sorted(missing)}")
    if not source["kind"] or not source["description"] or source["value"] is None:
        raise DataError(f"{who}: {field} требует kind, description и value")
    if source["url"] is not None and not str(source["url"]).startswith(("https://", "http://")):
        raise DataError(f"{who}: {field}.url должен быть http(s) URL или null")
    if source["archive_url"] is not None and not str(source["archive_url"]).startswith(("https://", "http://")):
        raise DataError(f"{who}: {field}.archive_url должен быть http(s) URL или null")
    if source["status"] not in {"needs_url", "editorial", "verified"}:
        raise DataError(f"{who}: {field}.status не поддерживается")
    if source["status"] == "verified" and not source["url"]:
        raise DataError(f"{who}: {field} помечен verified без URL")


def rate(artist: dict, snapshot: str | None = None) -> dict:
    """Считает одного артиста лиги. Без трёх источников артист не считается."""
    who = artist.get("name", artist.get("key", "?"))
    missing = [k for k in REQUIRED_SOURCES if not artist.get(k)]
    if missing:
        raise DataError(f"{who}: нет источников {missing}")
    for key in REQUIRED_SOURCES:
        validate_source(artist[key], key, who)
    source_values = {
        "src_top5": artist.get("top5"),
        "src_live": {"capacity": artist.get("cap"), "completed_cities": artist.get("cities"),
                     "festival": bool(artist.get("fest"))},
        "src_scene": artist.get("scene"),
    }
    for key, expected in source_values.items():
        if artist[key]["value"] != expected:
            raise DataError(f"{who}: значение {key}.value не совпадает с расчётным полем")
    if not isinstance(artist.get("pos"), str) or artist["pos"] not in LEAGUE_WEIGHTS:
        raise DataError(f"{who}: позиция {artist.get('pos')} не описана в model.json")
    if not isinstance(artist.get("fest", False), bool):
        raise DataError(f"{who}: fest должен быть true или false")
    for key in ("T", "S", "D"):
        value = artist.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 30 <= value <= 99:
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
    elif age is not None and (isinstance(age, bool) or not isinstance(age, int) or age < 0):
        raise DataError(f"{who}: age должен быть неотрицательным целым числом")
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
    rank = _positive_rank(rank, "место в топе треков")
    if rank is None or rank > 10:
        return clamp(OUTSIDE)
    if role not in ROLE_PENALTY:
        raise DataError(f"роль {role} не описана в model.json")
    return clamp(96 - 8 * math.log2(rank) + ROLE_PENALTY[role])


def season_influence(album_rank, vote_rank=None) -> float:
    album_rank = _positive_rank(album_rank, "место в топе альбомов")
    vote_rank = _positive_rank(vote_rank, "место в голосовании")
    base = OUTSIDE if album_rank is None or album_rank > 10 else 96 - 7 * math.log2(album_rank)
    top = int(MODEL["season_vote_bonus_max_rank"])
    bonus = max(0.0, 6 - vote_rank) if vote_rank is not None and vote_rank <= top else 0.0
    return clamp(base + bonus)


def _positive_rank(value, field: str) -> int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as err:
        raise DataError(f"{field}: ожидается положительное целое число или null") from err
    if not math.isfinite(number) or not number.is_integer() or number < 1:
        raise DataError(f"{field}: ожидается положительное целое число, получено {value!r}")
    return int(number)


def season_score(entry: dict) -> dict:
    for key in ("T", "S", "D"):
        value = entry.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 30 <= value <= 99:
            raise DataError(f"{entry.get('n', '?')}: {key} должен быть целым баллом от 30 до 99")
    if entry.get("pos") not in LEAGUE_WEIGHTS:
        raise DataError(f"{entry.get('n', '?')}: позиция {entry.get('pos')} не описана в model.json")
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
