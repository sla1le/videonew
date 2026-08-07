#!/usr/bin/env python3
"""ECHORATE league engine v2.1.1. Snapshot: 2026-08-06."""
from __future__ import annotations

import json
import math
from pathlib import Path

SNAP = "2026-08-06"
VER = "2.1.1"

WEIGHTS = {
    "ST":  {"T": .10, "S": .10, "D": .20, "H": .30, "L": .20, "I": .10},
    "CAM": {"T": .25, "S": .10, "D": .15, "H": .15, "L": .15, "I": .20},
    "CM":  {"T": .15, "S": .15, "D": .20, "H": .20, "L": .10, "I": .20},
    "CDM": {"T": .10, "S": .25, "D": .15, "H": .15, "L": .10, "I": .25},
    "LW":  {"T": .10, "S": .25, "D": .15, "H": .20, "L": .10, "I": .20},
    "RW":  {"T": .10, "S": .25, "D": .15, "H": .20, "L": .10, "I": .20},
    "CB":  {"T": .15, "S": .10, "D": .15, "H": .20, "L": .20, "I": .20},
}
for weights in WEIGHTS.values():
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert weights["T"] + weights["S"] + weights["D"] <= .5


def rnd(value: float) -> int:
    return int(math.floor(value + .5))


def clamp(value: float) -> float:
    return max(30.0, min(99.0, value))


def hits(top5: int) -> float:
    return clamp(70 + 6 * math.log2(top5 / 60_000_000))


def lives(capacity: int, cities: int, festival: bool = False) -> float:
    cap_eff = capacity * (.6 if festival else 1.0)
    return clamp(70 + 5 * math.log2(cap_eff / 10_000) + min(6, max(0, cities - 5)))


def influence(catalog: int, scene: float) -> float:
    assert -6 <= scene <= 6
    return clamp(70 + 6 * math.log2(catalog / 300_000_000) + scene)


def age_bonus(age: int | None) -> int:
    if age is None:
        return 2
    if age <= 21:
        return 8
    if age <= 24:
        return 6
    if age <= 27:
        return 4
    if age <= 30:
        return 2
    if age <= 33:
        return 1
    return 0


def form_bonus(change: float | None) -> int:
    if change is None:
        return 0
    if change > 10:
        return 3
    if change < -10:
        return -2
    return 0


def rate(artist: dict) -> dict:
    required_sources = ("src_top5", "src_live", "src_scene")
    missing = [key for key in required_sources if not artist.get(key)]
    if missing:
        raise ValueError(f"{artist['name']}: missing sources {missing}")

    stats = {
        "T": int(artist["T"]),
        "S": int(artist["S"]),
        "D": int(artist["D"]),
        "H": rnd(hits(int(artist["top5"]))),
        "L": rnd(lives(int(artist["cap"]), int(artist["cities"]), bool(artist.get("fest")))),
        "I": rnd(influence(int(artist["catalog"]), float(artist["scene"]))),
    }
    weights = WEIGHTS[artist["pos"]]
    raw = sum(stats[key] * weights[key] for key in stats)
    ovr = rnd(raw)
    potential = min(99, max(ovr, ovr + age_bonus(artist.get("age")) + form_bonus(artist.get("form"))))
    return {
        "key": artist["key"], "name": artist["name"], "pos": artist["pos"],
        "stats": stats, "raw": round(raw, 2), "ovr": ovr, "potential": potential,
        "was": artist.get("was"), "accuracy": artist.get("accuracy", "B"),
        "sources": {key: artist[key] for key in required_sources},
    }


ARTISTS = [
    dict(key="kreed", name="ЕГОР КРИД", pos="ST", age=32, T=68, S=82, D=86,
         top5=190_000_000, cap=80_000, cities=10, fest=False, catalog=639_305_028,
         scene=4, form=0, was=87, accuracy="A", src_top5="kworb Spotify snapshot 2026-08-06",
         src_live="Лужники, 10-11.07.2026", src_scene="Spotify catalog + scene modifier 4"),
    dict(key="buda", name="OG BUDA", pos="CM", age=32, T=76, S=85, D=88,
         top5=107_000_000, cap=10_000, cities=5, fest=False, catalog=642_755_820,
         scene=3, form=0, accuracy="A", src_top5="kworb Spotify snapshot 2026-08-06",
         src_live="confirmed solo venues through 2026-08-06", src_scene="Spotify catalog + scene modifier 3"),
    dict(key="kai", name="KAI ANGEL", pos="CDM", age=29, T=72, S=90, D=88,
         top5=48_000_000, cap=8_500, cities=5, fest=False, catalog=294_317_417,
         scene=5, form=0, was=84, accuracy="A", src_top5="kworb Spotify snapshot 2026-08-06",
         src_live="confirmed solo venues through 2026-08-06", src_scene="Spotify catalog + scene modifier 5"),
    dict(key="mice", name="9MICE", pos="LW", age=28, T=74, S=88, D=85,
         top5=52_000_000, cap=8_500, cities=5, fest=False, catalog=300_000_000,
         scene=5, form=0, was=86, accuracy="C", src_top5="stale kworb snapshot, refresh required",
         src_live="confirmed solo venues through 2026-08-06", src_scene="estimated catalog + scene modifier 5"),
    dict(key="dhill", name="LILDRUGHILL", pos="CDM", age=25, T=78, S=90, D=86,
         top5=34_000_000, cap=1_200, cities=5, fest=False, catalog=95_300_000,
         scene=4, form=-20, accuracy="B", src_top5="kworb Spotify snapshot 2026-08-06",
         src_live="confirmed solo venues through 2026-08-06", src_scene="Spotify catalog + scene modifier 4"),
    dict(key="thrill", name="THRILL PILL", pos="ST", age=25, T=64, S=74, D=80,
         top5=44_133_690, cap=2_000, cities=9, fest=False, catalog=50_300_000,
         scene=4, form=-20, accuracy="B", src_top5="five Spotify counters, snapshot 2026-08-06",
         src_live="earlybird.su tour + graphite.moscow", src_scene="catalog estimate + scene modifier 4"),
]


def main() -> None:
    rows = sorted((rate(a) for a in ARTISTS), key=lambda row: (-row["ovr"], -row["raw"], row["name"]))
    payload = {"version": VER, "snapshot": SNAP, "rows": rows}
    out = Path(__file__).parent / "data" / "league.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for number, row in enumerate(rows, 1):
        s = row["stats"]
        print(number, row["name"], row["pos"], *(s[k] for k in "TSDHLI"), row["raw"], row["ovr"], row["potential"])


if __name__ == "__main__":
    main()
