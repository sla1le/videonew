#!/usr/bin/env python3
"""Calculate one ECHORATE artist from a JSON file or the built-in THRILL PILL sample."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from echorate import rate

THRILL_PILL = {
    "key": "thrill", "name": "THRILL PILL", "pos": "ST", "age": 25,
    "T": 64, "S": 74, "D": 80,
    "top5": 17_831_253 + 15_702_673 + 5_535_738 + 3_048_324 + 2_015_702,
    "cap": 2_000, "cities": 9, "fest": False,
    "catalog": 50_300_000, "scene": 4, "form": -20, "accuracy": "B",
    "src_top5": "five Spotify track counters, snapshot 2026-08-06",
    "src_live": "earlybird.su tour + graphite.moscow",
    "src_scene": "catalog estimate + scene modifier 4",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="artist input JSON; defaults to THRILL PILL")
    args = parser.parse_args()
    artist = json.loads(Path(args.json_file).read_text(encoding="utf-8")) if args.json_file else THRILL_PILL
    print(json.dumps(rate(artist), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
