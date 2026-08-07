#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${1:?usage: bash build/run.sh <work_dir> <prefix>}"
PREFIX="${2:?usage: bash build/run.sh <work_dir> <prefix>}"
WORK="$(cd "$WORK" && pwd)"

mkdir -p "$WORK/html" "$WORK/assets" "$WORK/out"

if [[ -f "$WORK/gen_card.py" ]]; then
  (cd "$WORK" && python3 gen_card.py)
  cp "$WORK/card.css" "$WORK/html/card.css"
  rm -rf "$WORK/html/photos"
  [[ -d "$WORK/photos" ]] && cp -r "$WORK/photos" "$WORK/html/photos"
  rm -f "$WORK/assets"/*.png
  node "$ROOT/shot.js" "$WORK/html/cards.html" "$WORK/assets" card_ .wrap 1080 1350 2>&1 | sed '/Floss/d'
fi

(cd "$WORK" && python3 gen_deck.py)
cp "$WORK/deck.css" "$WORK/html/deck.css"
rm -rf "$WORK/html/photos" "$WORK/html/assets"
[[ -d "$WORK/photos" ]] && cp -r "$WORK/photos" "$WORK/html/photos"
cp -r "$WORK/assets" "$WORK/html/assets"
rm -f "$WORK/out"/*.png
node "$ROOT/shot.js" "$WORK/html/slides.html" "$WORK/out" "$PREFIX" .s 1080 1440 2>&1 | sed '/Floss/d'
python3 "$ROOT/qa.py" "$WORK/out" "$WORK/html/slides.html" "$WORK/deck.css"
magick montage "$WORK/out"/*.png -tile x1 -geometry 330x440+6+6 -background '#cccccc' "$WORK/probe.png"
echo "DONE $WORK/probe.png"
