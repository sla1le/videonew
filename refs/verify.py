#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверка эталонных кадров с refs/frames.csv по хешу. Зависимостей нет.

Смысл: в git едут замеры и логика, сами png могут лежать рядом или не лежать
вовсе. Когда картинки на месте, проверка ловит подмену и пережатие: эталон,
который молча поменялся, перестаёт быть эталоном. Когда картинок нет,
проверка пропускается и не валит сборку.

    python3 refs/verify.py
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLE = ROOT / "frames.csv"


def main() -> None:
    if not TABLE.exists():
        print("НЕТ ЗАМЕРОВ: refs/frames.csv отсутствует, соберите его командой make refs")
        raise SystemExit(1)

    rows = list(csv.DictReader(io.open(TABLE, encoding="utf-8")))
    if not rows:
        print("ПУСТО: в refs/frames.csv нет строк")
        raise SystemExit(1)

    present, missing, bad = 0, 0, []
    for row in rows:
        name = row["file"]
        path = ROOT / row["deck"] / (name if row["kind"] == "frame" else Path("cards") / name)
        if not path.exists():
            missing += 1
            continue
        present += 1
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        if digest != row["sha16"]:
            bad.append(f"{row['deck']}/{name}: в таблице {row['sha16']}, на диске {digest}")

    if present == 0:
        print(f"ПРОПУСК: картинок рядом нет, замеров в таблице {len(rows)}")
        return

    for line in bad:
        print("ПРОВАЛ", line)
    if bad:
        print(f"ЭТАЛОНЫ РАССОГЛАСОВАНЫ: {len(bad)} из {present}")
        raise SystemExit(1)
    print(f"ЭТАЛОНЫ СОВПАДАЮТ: проверено {present}, нет на диске {missing}")


if __name__ == "__main__":
    main()
