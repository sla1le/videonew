#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гигиена всех json в репозитории. Зависимостей нет, только стандартная библиотека.

Проверяет то, что ломалось на практике:
  1. Файл разбирается и читается в utf-8.
  2. Нет повторяющихся ключей в одном объекте. json.load тихо берёт последний,
     и именно так разошлись баллы, когда одна цифра лежала в двух местах.
  3. Нет NaN и Infinity: такое json пройдёт в python и упадёт в любом другом месте.
  4. В строках нет длинного тире, среднего тире и эмодзи. Данные попадают на кадр
     напрямую, и запреты стиля начинаются здесь, а не на верстке.
  5. Строка, которая начинается как дата, должна быть реальной датой.
     Фактовые даты не могут быть из будущего. Плановые могут: дедлайн ценза,
     дата ближайшего выпуска, срок годности данных. Список плановых полей
     лежит в PLAN_KEYS, горизонт ограничен пятью годами, чтобы опечатка
     вида 2226-08-24 всё равно ловилась.
  6. Целые баллы лежат в шкале от 30 до 99, если поле называется ovr, potential,
     score или rating.

    python3 ops/validate_data.py [папка ...]
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = ["rating/data", "ops/data", "formats/data", "iceberg/data", "refs", "build/decks"]
DASHES = {chr(8212): "длинное тире", chr(8211): "среднее тире"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
INDEX_RE = re.compile(r"\[\d+\]$")
SCORE_KEYS = {"ovr", "potential", "score", "rating"}

# Поля, где дата в будущем это нормальная плановая величина, а не опечатка.
# Совпадение по вхождению, поэтому deadline_at и planned_date тоже попадают.
PLAN_KEYS = (
    "deadline",
    "plan",
    "due",
    "target",
    "eta",
    "next",
    "until",
    "till",
    "expires",
    "expiry",
    "valid_",
    "cutoff",
    "schedule",
    "slot",
    "upcoming",
    "forecast",
)
PLAN_HORIZON_DAYS = 365 * 5


def is_emoji(ch: str) -> bool:
    code = ord(ch)
    return (0x1F000 <= code <= 0x1FAFF) or (0x2600 <= code <= 0x27BF) or code in (0xFE0F, 0x2B50)


def leaf_name(path: str) -> str:
    leaf = path.rsplit(".", 1)[-1].lower()
    return INDEX_RE.sub("", leaf)


def is_plan_field(path: str) -> bool:
    leaf = leaf_name(path)
    return any(word in leaf for word in PLAN_KEYS)


def no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"повтор ключа {key!r}")
        seen[key] = value
    return seen


def check_date(node: str, path: str, problems: list[str], today: dt.date) -> None:
    head = node[:10]
    try:
        value = dt.date.fromisoformat(head)
    except ValueError:
        problems.append(f"{path}: даты {head} не существует")
        return
    if is_plan_field(path):
        if value > today + dt.timedelta(days=PLAN_HORIZON_DAYS):
            problems.append(f"{path}: плановая дата {head} дальше пяти лет, похоже на опечатку")
        return
    if value > today + dt.timedelta(days=1):
        problems.append(f"{path}: дата {head} в будущем")


def walk(node, path: str, problems: list[str], today: dt.date) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            walk(value, f"{path}.{key}", problems, today)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk(value, f"{path}[{index}]", problems, today)
    elif isinstance(node, str):
        for ch, name in DASHES.items():
            if ch in node:
                problems.append(f"{path}: {name} в строке")
        bad = sorted({c for c in node if is_emoji(c)})
        if bad:
            problems.append(f"{path}: эмодзи {bad}")
        if DATE_RE.match(node):
            check_date(node, path, problems, today)
    elif isinstance(node, float):
        if node != node or node in (float("inf"), float("-inf")):
            problems.append(f"{path}: нечисловое значение")
    elif isinstance(node, bool):
        return
    elif isinstance(node, int):
        if leaf_name(path) in SCORE_KEYS and not 30 <= node <= 99:
            problems.append(f"{path}: балл {node} вне шкалы 30 до 99")


def check_file(path: Path, problems: list[str], today: dt.date) -> None:
    raw = io.open(path, encoding="utf-8").read()
    if "NaN" in raw or "Infinity" in raw:
        problems.append(f"{path}: в тексте есть NaN или Infinity")
    try:
        blob = json.loads(raw, object_pairs_hook=no_duplicates)
    except ValueError as error:
        problems.append(f"{path}: {error}")
        return
    walk(blob, path.name, problems, today)


def main() -> None:
    dirs = sys.argv[1:] or DEFAULT_DIRS
    problems: list[str] = []
    today = dt.date.today()
    files: list[Path] = []
    for name in dirs:
        folder = ROOT / name
        if folder.is_dir():
            files.extend(sorted(folder.rglob("*.json")))
    if not files:
        print("НЕТ ФАЙЛОВ: json не найдены, проверка пропущена")
        return
    for path in files:
        check_file(path, problems, today)
    for line in problems:
        print("ПРОВАЛ", line)
    if problems:
        print(f"ДАННЫЕ ПРОВАЛЕНЫ: {len(problems)}")
        raise SystemExit(1)
    print(f"ДАННЫЕ В ПОРЯДКЕ: файлов {len(files)}")


if __name__ == "__main__":
    main()
