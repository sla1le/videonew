#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подборщик дуэлей. Модель 4.1.

Что известно по цифрам канала. Опрос kizaru против ICEGERGERT закрылся 95 на 5
при 6275 голосах, и комментарии свелись к "тут даже сравнивать не надо". Опрос
OG Buda против LILDRUGHILL закрылся 52 на 48 при 3748 голосах, и там пошёл
разбор текстов, сцены и метода. Разгром даёт охват, близкая пара даёт спор.

Число опросов пока два, поэтому модуль не печатает предсказанный процент. Он
делит пары на классы и говорит, по какой оси зритель начнёт спорить.

    python3 rating/matchup.py --input data/artists.json
    python3 rating/matchup.py --input data/artists.json --goal спор
    python3 rating/matchup.py --input data/artists.json --vs egor buda
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import core  # noqa: E402

CFG = core.MODEL.get("matchup", {})
CRAFT = ("T", "S", "D")
RECOG = ("H", "I")


def load_pool(path: Path, snapshot: str | None) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw["artists"] if isinstance(raw, dict) and "artists" in raw else raw
    if isinstance(items, dict):
        items = list(items.values())
    pool = []
    for item in items:
        if item.get("stats") and item.get("ovr"):
            row = {"key": item.get("key", item.get("name")), "name": item.get("name", "?"),
                   "pos": item.get("pos", "?"), "stats": item["stats"], "ovr": int(item["ovr"])}
        else:
            rated = core.rate(item, snapshot)
            row = {"key": rated["key"], "name": rated["name"], "pos": rated["pos"],
                   "stats": rated["stats"], "ovr": rated["ovr"]}
        row["craft"] = sum(row["stats"][k] for k in CRAFT) / 3.0
        row["recog"] = sum(row["stats"][k] for k in RECOG) / 2.0
        pool.append(row)
    return pool


def classify(a: dict, b: dict) -> dict:
    gap_ovr = abs(a["ovr"] - b["ovr"])
    gap_recog = abs(a["recog"] - b["recog"])
    debate = gap_ovr <= float(CFG.get("debate_ovr_max", 3)) and gap_recog <= float(CFG.get("debate_recog_max", 4))
    reach = gap_recog >= float(CFG.get("reach_recog_min", 8))
    if debate:
        kind, poll, goal = "спор", "близкий", "комментарии и повторный просмотр"
    elif reach:
        kind, poll, goal = "разгром", "односторонний", "холодный охват"
    else:
        kind, poll, goal = "середина", "перекос", "ни охват, ни спор"

    lower = a if a["recog"] < b["recog"] else b
    higher = b if lower is a else a
    wins = [(lower["stats"][k] - higher["stats"][k], k) for k in core.STAT_ORDER if k in lower["stats"] and k in higher["stats"]]
    wins = [w for w in wins if w[0] > 0]
    axis = core.STAT_LABELS[max(wins)[1]] if wins else "нет"
    return {"a": a, "b": b, "gap_ovr": gap_ovr, "gap_recog": round(gap_recog, 1),
            "kind": kind, "poll": poll, "goal": goal, "axis": axis,
            "underdog": lower["name"], "favourite": higher["name"]}


def row(p: dict) -> list[str]:
    return ["%s против %s" % (p["a"]["name"], p["b"]["name"]), p["kind"], "%d" % p["gap_ovr"],
            "%.1f" % p["gap_recog"], p["poll"], p["axis"], p["underdog"]]


def table(lines: list[list[str]]) -> None:
    head = ["Пара", "Класс", "Разрыв балла", "Разрыв охвата", "Опрос", "Спор пойдёт по оси", "Кого будут защищать"]
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join(["---"] * len(head)) + "|")
    for line in lines:
        print("| " + " | ".join(line) + " |")
    print()


def observed() -> None:
    obs = CFG.get("observed", [])
    if not obs:
        return
    print("Наблюдённые опросы, на них калибрована граница классов:")
    for o in obs:
        print("- %s: %s, голосов %s, класс %s" % (o.get("pair"), " на ".join(str(x) for x in o.get("poll", [])), o.get("votes"), o.get("kind")))
    print("Опросов пока %d, поэтому процент не предсказывается, только класс пары." % len(obs))
    print()


def pick(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and len(argv) > argv.index(flag) + 1 else default


def main() -> int:
    argv = sys.argv[1:]
    path = Path(pick(argv, "--input", str(HERE / "data" / "artists.json")))
    if not path.is_absolute():
        path = HERE / path
    if not path.exists():
        print("нет файла с пулом: %s" % path)
        return 2
    snapshot = pick(argv, "--snapshot")
    pool = load_pool(path, snapshot)
    if len(pool) < 2:
        print("в пуле меньше двух артистов")
        return 2

    if "--vs" in argv:
        i = argv.index("--vs")
        names = [x.lower() for x in argv[i + 1:i + 3]]
        found = [x for x in pool if x["key"].lower() in names or x["name"].lower() in names]
        if len(found) != 2:
            print("не нашёл ровно двух артистов по ключам %s" % names)
            return 2
        p = classify(*found)
        print("%s против %s" % (p["a"]["name"], p["b"]["name"]))
        print("класс пары: %s, цель: %s" % (p["kind"], p["goal"]))
        print("разрыв балла %d, разрыв охвата %.1f" % (p["gap_ovr"], p["gap_recog"]))
        print("спор пойдёт по оси %s, защищать будут %s" % (p["axis"], p["underdog"]))
        print()
        observed()
        return 0

    goal = pick(argv, "--goal")
    pairs = [classify(a, b) for a, b in combinations(pool, 2)]
    if goal in ("спор", "debate"):
        pairs = [p for p in pairs if p["kind"] == "спор"]
        pairs.sort(key=lambda p: (p["gap_ovr"], p["gap_recog"]))
        print("## Пары под спор\n")
    elif goal in ("охват", "reach"):
        pairs = [p for p in pairs if p["kind"] == "разгром"]
        pairs.sort(key=lambda p: -p["gap_recog"])
        print("## Пары под охват\n")
    else:
        pairs.sort(key=lambda p: (p["kind"] != "спор", p["gap_ovr"], p["gap_recog"]))
        print("## Все пары\n")
    if not pairs:
        print("под эту цель пар нет\n")
    else:
        table([row(p) for p in pairs])
    observed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
