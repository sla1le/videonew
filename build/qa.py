#!/usr/bin/env python3
"""Text and pixel checks for ECHORATE decks."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from PIL import Image

MAX_GAP = 110
BODY_BOTTOM = 1290
MIN_TOP = 40
MIN_LEFT = 60
MAX_RIGHT = 1010
ALLOWED = {8470, 171, 187, 8226, 183, 8722, 1025, 1105, 215}


def fail(message: str, failures: list[str]) -> None:
    print("FAIL", message)
    failures.append(message)


def check_text(html_path: Path, css_path: Path, failures: list[str]) -> None:
    source = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    text = re.sub(r"<[^>]+>", " ", source)
    text = re.sub(r"\s+", " ", text)

    broken = [m for m in re.findall(r"font:[^;}]+", css) if "var(" not in m]
    if broken:
        fail(f"broken font shorthands: {broken}", failures)
    if chr(8212) in text:
        fail(f"em dash count: {text.count(chr(8212))}", failures)
    if re.findall(r", а не ", text, flags=re.I):
        fail("found ', а не '", failures)
    if re.findall(r"не [^.,!?]{2,40}, а ", text, flags=re.I):
        fail("found 'не X, а Y'", failures)
    if "не просто" in text.lower():
        fail("found 'не просто'", failures)

    marks = source.count('class="mk')
    if marks != 3:
        fail(f"handwritten marks: {marks}, expected 3", failures)
    weird = sorted({c for c in text if ord(c) > 1103 and ord(c) not in ALLOWED})
    if weird:
        fail(f"unexpected characters: {weird}", failures)


def check_image(path: Path, failures: list[str]) -> None:
    image = Image.open(path).convert("L")
    width, height = image.size
    if (width, height) != (1080, 1440):
        fail(f"{path.name}: {width}x{height}, expected 1080x1440", failures)
        return
    px = image.load()
    rows = [y for y in range(0, min(BODY_BOTTOM, height)) if any(px[x, y] < 245 for x in range(0, width, 4))]
    if not rows:
        fail(f"{path.name}: no visible content", failures)
        return
    if rows[0] < MIN_TOP:
        fail(f"{path.name}: top {rows[0]} < {MIN_TOP}", failures)
    if rows[-1] > BODY_BOTTOM:
        fail(f"{path.name}: body bottom {rows[-1]} > {BODY_BOTTOM}", failures)
    gaps, previous = [], rows[0]
    for y in rows[1:]:
        if y - previous > MAX_GAP:
            gaps.append((previous, y, y - previous))
        previous = y
    if gaps:
        fail(f"{path.name}: vertical gaps {gaps}", failures)

    cols = [x for x in range(width) if any(px[x, y] < 245 for y in range(0, height, 5))]
    if cols:
        if cols[0] < MIN_LEFT:
            fail(f"{path.name}: left {cols[0]} < {MIN_LEFT}", failures)
        if cols[-1] > MAX_RIGHT:
            fail(f"{path.name}: right {cols[-1]} > {MAX_RIGHT}", failures)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python3 qa.py <out_dir> [slides.html] [deck.css]")
    out_dir = Path(sys.argv[1])
    html_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    css_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    failures: list[str] = []
    if html_path and css_path:
        check_text(html_path, css_path, failures)
    images = sorted(out_dir.glob("*.png"))
    if not images:
        fail(f"no PNG files in {out_dir}", failures)
    for image in images:
        check_image(image, failures)
    if failures:
        print(f"QA FAILED: {len(failures)}")
        raise SystemExit(1)
    print(f"QA OK: {len(images)} frames")


if __name__ == "__main__":
    main()
