#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверяет, что сохранённые расчёты совпадают с текущими исходными данными."""
from __future__ import annotations

import json
from pathlib import Path

import core
import season


DATA = Path(__file__).resolve().parent / "data"


def check(name: str, expected: dict) -> bool:
    path = DATA / name
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        print(f"ПРОВАЛ {path}: не удалось прочитать: {err}")
        return False
    if saved != expected:
        print(f"ПРОВАЛ {path}: устаревший результат, пересоберите его командой из rating/README.md")
        return False
    print(f"АКТУАЛЬНО {path}")
    return True


def main() -> int:
    valid = check("league.json", core.league())
    valid = check("seasons.json", season.current_results()) and valid
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
