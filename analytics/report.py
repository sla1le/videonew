#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отчёт по наблюдаемым цифрам канала. Единственный источник данных: analytics/posts.json.

    python3 analytics/report.py           таблицы в markdown
    python3 analytics/report.py --check    проверка данных, код возврата 1 при поломке

Ничего не додумывает. Если поля нет, в таблице стоит прочерк.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "posts.json"
GOALS = {"охват": "views", "подписки": "fol", "спор": "com"}


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def per_1k(value, views):
    if value is None or not views:
        return None
    return value * 1000.0 / views


def metrics(p: dict) -> dict:
    v = p.get("views") or 0
    seen, slides, play = p.get("seen"), p.get("slides"), p.get("play_h")
    return {
        "id": p["id"],
        "fmt": p.get("fmt", "неизвестно"),
        "views": v,
        "lk": per_1k(p.get("likes"), v),
        "fol": per_1k(p.get("follows"), v),
        "sav": per_1k(p.get("saves"), v),
        "shr": per_1k(p.get("shares"), v),
        "com": per_1k(p.get("comments"), v),
        "depth": (seen / slides * 100.0) if seen and slides else None,
        "spv": (play * 3600.0 / v) if play and v else None,
        "slides": slides,
        "solid": p.get("conf") == "high",
    }


def n(x, digits=2):
    if x is None:
        return "нет"
    if digits == 0:
        return "%d" % round(x)
    return ("%." + str(digits) + "f") % x


def avg(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return sum(vals) / len(vals) if vals else None


def table(head, lines):
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join(["---"] * len(head)) + "|")
    for line in lines:
        print("| " + " | ".join(line) + " |")
    print()


def report(d: dict) -> None:
    rows = [metrics(p) for p in d["posts"]]
    rows.sort(key=lambda r: -r["views"])
    solid = [r for r in rows if r["solid"]]

    print("## Посты\n")
    table(
        ["ID", "Формат", "Просмотры", "Лайки/1к", "Подписки/1к", "Сохран/1к", "Репост/1к", "Комм/1к", "Глубина %", "Сек/просмотр"],
        [[r["id"], r["fmt"], "%d" % r["views"], n(r["lk"], 1), n(r["fol"]), n(r["sav"]), n(r["shr"]), n(r["com"]), n(r["depth"], 1), n(r["spv"], 1)] for r in rows],
    )

    print("## Форматы, только надёжные посты\n")
    fmts = {}
    for r in solid:
        fmts.setdefault(r["fmt"], []).append(r)
    lines = []
    for fmt, group in sorted(fmts.items(), key=lambda kv: -avg(kv[1], "views")):
        lines.append([fmt, "%d" % len(group), n(avg(group, "views"), 0), n(avg(group, "fol")), n(avg(group, "shr")), n(avg(group, "com")), n(avg(group, "sav")), n(avg(group, "depth"), 1)])
    table(["Формат", "Штук", "Просмотры", "Подписки/1к", "Репост/1к", "Комм/1к", "Сохран/1к", "Глубина %"], lines)

    print("## Три цели, у каждой свой лидер\n")
    lines = []
    for goal, key in GOALS.items():
        best = max([r for r in solid if r[key] is not None], key=lambda r: r[key])
        lines.append([goal, best["id"], best["fmt"], n(best[key], 2 if key != "views" else 0)])
    table(["Цель", "Лидер", "Формат", "Значение"], lines)

    print("## Глубина против числа слайдов\n")
    by_slides = {}
    for r in rows:
        if r["slides"] and r["depth"]:
            by_slides.setdefault(r["slides"], []).append(r["depth"])
    table(["Слайдов", "Постов", "Средняя глубина %"], [[str(k), str(len(v)), n(sum(v) / len(v), 1)] for k, v in sorted(by_slides.items())])

    print("## Опросы\n")
    lines = []
    for p in d["posts"]:
        if not p.get("poll"):
            continue
        share = sorted(p["poll"].values(), reverse=True)
        lines.append([p["id"], " против ".join(p["poll"].keys()), "%d на %d" % (share[0], share[-1]), "%d" % p.get("votes", 0), "разгром" if share[0] - share[-1] >= 20 else "спор"])
    table(["ID", "Пара", "Расклад", "Голосов", "Тип"], lines)

    print("## Оговорки\n")
    for w in d.get("warnings", []):
        print("- " + w)
    for p in d["posts"]:
        if p.get("note"):
            print("- %s: %s" % (p["id"], p["note"]))
    print()


def check(d: dict) -> int:
    bad = []
    seen_ids = set()
    for p in d["posts"]:
        who = p.get("id", "?")
        if who in seen_ids:
            bad.append("%s: повтор идентификатора" % who)
        seen_ids.add(who)
        if not p.get("views"):
            bad.append("%s: нет просмотров" % who)
        if p.get("seen") and p.get("slides") and p["seen"] > p["slides"]:
            bad.append("%s: просмотрено слайдов больше, чем есть" % who)
        for key in ("likes", "comments", "shares", "saves", "follows"):
            if p.get(key) is not None and p[key] > (p.get("views") or 0):
                bad.append("%s: %s больше просмотров" % (who, key))
        if p.get("conf") not in ("high", "medium", "low"):
            bad.append("%s: нет отметки надёжности" % who)
    for b in bad:
        print("ПРОВАЛ:", b)
    if bad:
        return 1
    print("ДАННЫЕ В ПОРЯДКЕ: постов %d" % len(d["posts"]))
    return 0


def main() -> int:
    d = load()
    if "--check" in sys.argv:
        return check(d)
    report(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
