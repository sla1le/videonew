#!/usr/bin/env python3
"""Generate ECHORATE cards from league JSON."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "rating" / "data" / "league.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "html" / "cards.html"
PHOTO_DIR = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "photos"
LABELS = (("T", "ТЕКСТЫ"), ("S", "ЗВУК"), ("D", "ПОДАЧА"), ("H", "ХИТЫ"), ("L", "ЛАЙВЫ"), ("I", "ВЛИЯНИЕ"))
MODEL = json.loads((REPO / "rating" / "data" / "model.json").read_text(encoding="utf-8"))
POS_LABELS = {code: str(text).upper() for code, text in MODEL.get("position_labels", {}).items()}


def strike(value: int) -> str:
    return f'''<div class="was">БЫЛО {value}<svg class="sk" viewBox="0 0 200 40" preserveAspectRatio="none"><path d="M4 27 C 56 13, 142 31, 196 11" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg></div>'''


def stat(label: str, value: int) -> str:
    width = max(0, min(100, (value - 30) / 69 * 100))
    return f'''<div class="stat"><div class="lab">{label}</div><div class="line">{value}</div><div class="bar"><i style="width:{width:.2f}%"></i></div></div>'''


def card(row: dict) -> str:
    name = html.escape(row["name"])
    key = row.get("key", name.lower().replace(" ", "_"))
    path = PHOTO_DIR / f"{key}.png"
    photo = f'<img class="ph" src="photos/{html.escape(path.name)}" alt="{name}">' if path.exists() else '<div class="ph"></div>'
    old = strike(row["was"]) if row.get("was") is not None else ""
    size = "90px" if len(name) > 10 else "132px"
    stats = "".join(stat(label, int(row["stats"][code])) for code, label in LABELS)
    role = html.escape(str(row.get("label") or POS_LABELS.get(row["pos"], "")))
    subtitle = f'{row["pos"]} · {role}' if role else row["pos"]
    return f'''<section class="wrap" data-name="{key}"><article class="card"><div class="top"><div class="lft"><div class="ovr">{row["ovr"]}</div><div class="pos">{row["pos"]}</div>{old}</div>{photo}</div><div class="rule"></div><div class="name" style="font-size:{size}">{name}</div><div class="sub">{subtitle}</div><div class="grid">{stats}</div><div class="pot"><span class="k">ПОТЕНЦИАЛ</span><span class="v">{row["potential"]}</span></div><div class="foot">T.ME/ECHORATE</div></article></section>'''


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    rows = payload["rows"] if isinstance(payload, dict) and "rows" in payload else payload
    body = "".join(card(row) for row in rows)
    document = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><link rel="stylesheet" href="card.css"></head><body>{body}</body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(f"WROTE {OUT} {len(rows)} cards")


if __name__ == "__main__":
    main()
