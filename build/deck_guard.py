#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет драматургию JSON-деки до вёрстки.

Геометрию проверяет qa.py после рендера. Этот файл ловит более раннюю и более
дорогую ошибку: когда в сборку уехал набор слайдов без истории.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


OPENERS = {"cover", "duocover"}
CONFLICTS = {"duel", "stats", "bracket", "table"}


def check(path: Path) -> list[str]:
    try:
        deck = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return [f"{path}: не читается JSON: {err}"]

    frames = deck.get("frames")
    if not isinstance(frames, list):
        return [f"{path}: нет массива frames"]

    kinds = [frame.get("t", "text") for frame in frames if isinstance(frame, dict)]
    errors: list[str] = []
    if not 6 <= len(frames) <= 8:
        errors.append(f"{path}: кадров {len(frames)}, обычная дека держит 6 до 8")
    if not kinds or kinds[0] not in OPENERS:
        errors.append(f"{path}: первый кадр должен быть cover или duocover")
    if not kinds or kinds[-1] != "cta":
        errors.append(f"{path}: последний кадр должен быть cta")
    if kinds.count("cta") != 1:
        errors.append(f"{path}: призывов {kinds.count('cta')}, нужен ровно один")
    if "formula" not in kinds:
        errors.append(f"{path}: нет кадра formula с воспроизводимой механикой")
    if "verdict" not in kinds and "cta" not in kinds:
        errors.append(f"{path}: нет закрывающего вывода")
    if not any(kind in CONFLICTS for kind in kinds):
        errors.append(f"{path}: нет кадра столкновения позиций или осей")
    for index, (left, right) in enumerate(zip(kinds, kinds[1:]), start=1):
        if left == right and left in {"text", "facts", "table", "duel", "verdict"}:
            errors.append(f"{path}: кадры {index} и {index + 1} оба {left}, ритм повторяется")
    return errors


def main() -> int:
    paths = [Path(arg) for arg in sys.argv[1:]]
    if not paths:
        print("укажи JSON-деки")
        return 2
    failures = [error for path in paths for error in check(path)]
    for failure in failures:
        print("ПРОВАЛ:", failure)
    if failures:
        print(f"DECK GUARD ПРОВАЛЕН: {len(failures)}")
        return 1
    print(f"DECK GUARD ПРОЙДЕН: дек {len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
