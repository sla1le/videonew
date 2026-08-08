#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Замер эталонных кадров. Пишет refs/manifest.json и refs/frames.csv.

Зачем вообще: пороги дизайна и автопроверки выведены из выпусков, которые
сработали, а не из вкуса. Новый эталон добавляется папкой в refs и попадает в замер
без правки кода. Кадры деки лежат в корне папки, рейтинговые карточки в cards.

Значения: top и bottom первая и последняя полоса с чернилами, left и right крайние
столбцы, max_gap самый большой вертикальный разрыв и его начало, bands число
смысловых полос, photo_rows сколько полос залито шире 60 процентов ширины.

    python3 refs/analyze.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
INK_DELTA = 16      # отличие от фона, после которого пиксель считается чернилами
STEP = 4            # шаг по горизонтали
WIDE_ROW = 0.6      # доля заливки, после которой полоса считается фото или плашкой
BAND_TOL = 8        # пустые полосы внутри одного блока
CSV_HEAD = ("deck,kind,file,w,h,top,bottom,left,right,max_gap,max_gap_at,"
            "ink_pct,bands,photo_rows,bg,sha16")


def measure(path: Path) -> dict:
    raw = path.read_bytes()
    image = Image.open(io.BytesIO(raw)).convert("L")
    width, height = image.size
    px = image.load()

    corners = [px[3, 3], px[width - 4, 3], px[3, height - 4], px[width - 4, height - 4]]
    bg = max(set(corners), key=corners.count)

    xs = list(range(0, width, STEP))
    fill = []
    for y in range(height):
        hits = sum(1 for x in xs if abs(px[x, y] - bg) > INK_DELTA)
        fill.append(hits / float(len(xs)))

    rows = [y for y, value in enumerate(fill) if value > 0]
    if not rows:
        return {"file": path.name, "w": width, "h": height, "empty": True,
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

    gap, gap_at, previous = 0, 0, rows[0]
    bands = 1
    for y in rows[1:]:
        span = y - previous
        if span > gap:
            gap, gap_at = span, previous
        if span > BAND_TOL:
            bands += 1
        previous = y

    cols = [x for x in range(width)
            if any(abs(px[x, y] - bg) > INK_DELTA for y in range(0, height, 5))]

    return {
        "file": path.name,
        "w": width,
        "h": height,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "bg": "#%02X%02X%02X" % (bg, bg, bg),
        "dark": bool(bg < 128),
        "ink_pct": round(sum(fill) / float(height) * 100, 2),
        "top": rows[0],
        "bottom": rows[-1],
        "left": cols[0] if cols else 0,
        "right": cols[-1] if cols else 0,
        "max_gap": gap,
        "max_gap_at": gap_at,
        "bands": bands,
        "photo_rows": sum(1 for value in fill if value > WIDE_ROW),
    }


def main() -> None:
    decks = []
    for folder in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name != "prev"):
        frames = sorted(folder.glob("*.png"))
        cards = sorted((folder / "cards").glob("*.png")) if (folder / "cards").is_dir() else []
        if not frames and not cards:
            continue
        print("%s: кадров %d, карт %d" % (folder.name, len(frames), len(cards)))
        decks.append({
            "deck": folder.name,
            "frames": [measure(p) for p in frames],
            "cards": [measure(p) for p in cards],
        })

    if not decks:
        print("НЕТ КАДРОВ: положите папку с png в refs и повторите замер")
        return

    manifest = {"generated": dt.datetime.now().isoformat(timespec="seconds"), "decks": decks}
    with io.open(ROOT / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    lines = [CSV_HEAD]
    for deck in decks:
        for kind in ("frames", "cards"):
            for m in deck[kind]:
                if m.get("empty"):
                    continue
                lines.append("%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d,%.2f,%d,%d,%s,%s" % (
                    deck["deck"], kind[:-1], m["file"], m["w"], m["h"], m["top"],
                    m["bottom"], m["left"], m["right"], m["max_gap"], m["max_gap_at"],
                    m["ink_pct"], m["bands"], m["photo_rows"], m["bg"], m["sha256"][:16]))
    with io.open(ROOT / "frames.csv", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    frames = [m for d in decks for m in d["frames"] if not m.get("empty")]
    print("\nсводка по кадрам дек: %d" % len(frames))
    for key in ("top", "bottom", "left", "right", "max_gap", "bands", "ink_pct"):
        values = sorted(m[key] for m in frames)
        print("  %-9s минимум %-8s середина %-8s максимум %-8s" % (
            key, values[0], values[len(values) // 2], values[-1]))
    print("\nзаписано: refs/manifest.json и refs/frames.csv")


if __name__ == "__main__":
    main()
