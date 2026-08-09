#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гигиена всех json в репозитории. Зависимостей нет, только стандартная библиотека.

Проверяет то, что ломалось на практике:
  1. Файл разбирается и читается в utf-8.
  2. Нет повторяющихся ключей в одном объекте.
  3. Нет NaN и Infinity.
  4. В строках нет длинного тире, среднего тире и эмодзи.
  5. Строка, которая начинается как дата, должна быть реальной датой.
     Будущая дата запрещена для фактов и снимков, но разрешена в плановых полях.
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
SCORE_KEYS = {"ovr", "potential", "score", "rating"}
FUTURE_DATE_KEYS = {
    "deadline", "due", "due_date", "cutoff", "expires", "expires_at",
    "expiry", "expiry_date", "scheduled_at", "scheduled_for",
    "publish_at", "publish_date", "target_date", "next_date",
}
FUTURE_DATE_SUFFIXES = (
    "_deadline", "_due", "_expires", "_expiry", "_scheduled", "_target",
)


def is_emoji(ch: str) -> bool:
    code = ord(ch)
    return (0x1F000 <= code <= 0x1FAFF) or (0x2600 <= code <= 0x27BF) or code in (0xFE0F, 0x2B50)


def no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"повтор ключа {key!r}")
        seen[key] = value
    return seen


def leaf_key(path: str) -> str:
    leaf = path.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]$", "", leaf)
    return leaf.lower()


def future_date_allowed(path: str) -> bool:
    leaf = leaf_key(path)
    return leaf in FUTURE_DATE_KEYS or leaf.endswith(FUTURE_DATE_SUFFIXES)


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
            head = node[:10]
            try:
                value = dt.date.fromisoformat(head)
            except ValueError:
                problems.append(f"{path}: даты {head} не существует")
            else:
                if value > today + dt.timedelta(days=1) and not future_date_allowed(path):
                    problems.append(f"{path}: дата {head} в будущем")
    elif isinstance(node, float):
        if node != node or node in (float("inf"), float("-inf")):
            problems.append(f"{path}: нечисловое значение")
    elif isinstance(node, bool):
        return
    elif isinstance(node, int):
        leaf = leaf_key(path)
        if leaf in SCORE_KEYS and not 30 <= node <= 99:
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
