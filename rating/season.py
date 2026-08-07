#!/usr/bin/env python3
"""ECHORATE SEASON v3. Golden Ball engine with fixed cross-position weights."""
from __future__ import annotations

import json
import math
from pathlib import Path

VERSION = "3.0"
CUTOFF = "Все официальные итоги сезона, опубликованные до 31 января следующего года"
W = {"T": .15, "S": .15, "D": .15, "H": .25, "I": .30}
OUT = 62.0
assert abs(sum(W.values()) - 1.0) < 1e-9


def rnd(x: float) -> int:
    return int(math.floor(x + .5))


def clamp(x: float) -> float:
    return max(30.0, min(99.0, x))


def hits(rank: int | None, role: str = "lead") -> float:
    value = OUT if rank is None or rank > 10 else 96 - 8 * math.log2(rank)
    if rank is not None and rank <= 10:
        if role == "colead":
            value -= 3
        if role == "guest":
            value -= 9
    return clamp(value)


def influence(album_rank: int | None, vote_rank: int | None = None) -> float:
    base = OUT if album_rank is None or album_rank > 10 else 96 - 7 * math.log2(album_rank)
    bonus = max(0.0, 6 - vote_rank) if vote_rank is not None and vote_rank <= 5 else 0.0
    return clamp(base + bonus)


def score(a: dict) -> dict:
    h = hits(a.get("tr"), a.get("role", "lead"))
    i = influence(a.get("alb"), a.get("vote"))
    raw = a["T"] * W["T"] + a["S"] * W["S"] + a["D"] * W["D"] + h * W["H"] + i * W["I"]
    sp = a.get("spots") or []
    return {**a, "H": round(h, 2), "I": round(i, 2), "raw": round(raw, 2), "ovr": rnd(raw),
            "tie_count": len(sp), "tie_best": min(sp) if sp else 99}


def solve(title: str, pool: list[dict]) -> list[dict]:
    rows = sorted((score(a) for a in pool), key=lambda x: -x["raw"])
    groups, current = [], []
    for row in rows:
        if not current or current[0]["raw"] - row["raw"] < 1.0:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    if current:
        groups.append(current)

    ordered = []
    for group in groups:
        if len(group) > 1:
            group.sort(key=lambda x: (-x["tie_count"], x["tie_best"], x.get("vote") or 99, -x["raw"]))
            for row in group:
                row["tiebreak"] = True
        ordered.extend(group)

    print(title)
    for place, row in enumerate(ordered, 1):
        print(place, row["n"], row["pos"], row["raw"], row["ovr"], "TB" if row.get("tiebreak") else "")
    return ordered


P2015 = [
    dict(n="СКРИПТОНИТ", pos="CDM", T=84, S=96, D=90, tr=3, alb=1, vote=None, spots=[3, 1]),
    dict(n="OXXXYMIRON", pos="CAM", T=96, S=82, D=94, tr=6, alb=2, vote=None, spots=[6, 2]),
    dict(n="ЛСП", pos="RW", T=84, S=86, D=82, tr=1, alb=5, vote=None, role="lead", spots=[1, 5]),
    dict(n="ATL", pos="CDM", T=90, S=92, D=82, tr=5, alb=3, vote=None, spots=[5, 3]),
    dict(n="КАСПИЙСКИЙ ГРУЗ", pos="CB", T=86, S=84, D=84, tr=10, alb=4, vote=None, spots=[10, 4]),
    dict(n="4 ПОЗИЦИИ БРУНО", pos="CDM", T=80, S=88, D=72, tr=4, alb=10, vote=None, spots=[4, 10]),
    dict(n="PHARAOH", pos="LW", T=72, S=88, D=86, tr=2, alb=None, vote=None, spots=[2]),
    dict(n="ВЛАДИ", pos="CAM", T=84, S=78, D=76, tr=8, alb=7, vote=None, role="colead", spots=[8, 7]),
    dict(n="HORUS", pos="CAM", T=88, S=82, D=76, tr=9, alb=9, vote=None, spots=[9, 9]),
    dict(n="ГРОТ", pos="CB", T=82, S=76, D=74, tr=8, alb=6, vote=None, role="colead", spots=[8, 6]),
    dict(n="GUF", pos="CB", T=76, S=84, D=78, tr=None, alb=8, vote=None, spots=[8]),
    dict(n="НОГГАНО", pos="ST", T=74, S=70, D=84, tr=7, alb=None, vote=None, spots=[7]),
]

P2017 = [
    dict(n="ЛСП", pos="RW", T=88, S=86, D=84, tr=4, alb=1, vote=1, spots=[4, 1, 1]),
    dict(n="PHARAOH", pos="LW", T=76, S=92, D=90, tr=1, alb=5, vote=None, spots=[1, 5]),
    dict(n="СКРИПТОНИТ", pos="CDM", T=86, S=96, D=90, tr=5, alb=4, vote=2, role="colead", spots=[5, 4, 7, 2]),
    dict(n="ХАСКИ", pos="CAM", T=92, S=84, D=88, tr=10, alb=3, vote=None, spots=[10, 3]),
    dict(n="ATL", pos="CDM", T=88, S=88, D=80, tr=8, alb=10, vote=None, spots=[8, 10]),
    dict(n="ЭЛДЖЕЙ", pos="ST", T=68, S=86, D=88, tr=2, alb=None, vote=None, role="colead", spots=[2]),
    dict(n="ПОШЛАЯ МОЛЛИ", pos="LW", T=70, S=74, D=82, tr=None, alb=2, vote=None, spots=[2]),
    dict(n="АИГЕЛ", pos="CAM", T=86, S=88, D=84, tr=6, alb=None, vote=None, spots=[6]),
    dict(n="FEDUK", pos="ST", T=70, S=80, D=82, tr=2, alb=None, vote=None, role="colead", spots=[2]),
    dict(n="МАКС КОРЖ", pos="ST", T=74, S=76, D=84, tr=None, alb=6, vote=3, spots=[6, 3]),
    dict(n="25/17", pos="CB", T=86, S=78, D=78, tr=None, alb=8, vote=None, spots=[8]),
    dict(n="КАСПИЙСКИЙ ГРУЗ", pos="CB", T=84, S=80, D=80, tr=None, alb=9, vote=None, spots=[9]),
    dict(n="OXXXYMIRON", pos="CAM", T=96, S=80, D=92, tr=None, alb=None, vote=4, spots=[4]),
    dict(n="ГРИБЫ", pos="ST", T=66, S=82, D=80, tr=3, alb=None, vote=None, spots=[3]),
    dict(n="T-FEST", pos="RW", T=76, S=82, D=82, tr=5, alb=None, vote=None, role="colead", spots=[5]),
    dict(n="СЛАВА КПСС", pos="CAM", T=88, S=70, D=80, tr=7, alb=None, vote=None, spots=[7]),
    dict(n="FACE", pos="ST", T=62, S=74, D=88, tr=9, alb=48, vote=None, spots=[9]),
    dict(n="NOIZE MC", pos="CAM", T=84, S=74, D=80, tr=None, alb=None, vote=5, spots=[5]),
]


def main() -> None:
    r15 = solve("ЗОЛОТОЙ МЯЧ 2015, пул 12", P2015)
    r17 = solve("ЗОЛОТОЙ МЯЧ 2017, пул 18", P2017)
    payload = {"version": VERSION, "cutoff": CUTOFF, "weights": W, "seasons": {"2015": r15, "2017": r17}}
    out = Path(__file__).parent / "data" / "seasons.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
