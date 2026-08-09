#!/usr/bin/env bash
# Сборка выпуска в отдельном рабочем каталоге.
#
#   bash build/run.sh <work_dir> <prefix>
#
# В рабочем каталоге обязаны лежать gen_deck.py и deck.css. По желанию
# gen_card.py, card.css и папка photos. Стартовые шаблоны лежат в build:
#
#   mkdir -p work
#   cp build/gen_deck_example.py work/gen_deck.py
#   cp build/deck.css work/deck.css
#
# Основной путь проекта другой: make render DECK=<deck>. Этот скрипт нужен,
# когда у выпуска своя вёрстка и свои генераторы.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 2 ]]; then
  echo "использование: bash build/run.sh <work_dir> <prefix>" >&2
  echo "пример:        bash build/run.sh work gm_" >&2
  exit 2
fi

WORK="$1"
PREFIX="$2"

if [[ ! -d "$WORK" ]]; then
  echo "нет каталога $WORK" >&2
  exit 2
fi
WORK="$(cd "$WORK" && pwd)"

for need in gen_deck.py deck.css; do
  if [[ ! -f "$WORK/$need" ]]; then
    echo "нет файла $WORK/$need" >&2
    echo "возьми шаблоны:" >&2
    echo "  cp $ROOT/gen_deck_example.py $WORK/gen_deck.py" >&2
    echo "  cp $ROOT/deck.css $WORK/deck.css" >&2
    exit 2
  fi
done

mkdir -p "$WORK/html" "$WORK/assets" "$WORK/out"

# Раньше здесь стояло [[ -d photos ]] && cp -r ..., и при отсутствии папки
# photos вся сборка тихо обрывалась на set -e, не дойдя до рендера.
copy_photos() {
  rm -rf "$WORK/html/photos"
  if [[ -d "$WORK/photos" ]]; then
    cp -r "$WORK/photos" "$WORK/html/photos"
  fi
}

if [[ -f "$WORK/gen_card.py" ]]; then
  if [[ ! -f "$WORK/card.css" ]]; then
    echo "есть gen_card.py, но нет $WORK/card.css" >&2
    echo "  cp $ROOT/card.css $WORK/card.css" >&2
    exit 2
  fi
  (cd "$WORK" && python3 gen_card.py)
  cp "$WORK/card.css" "$WORK/html/card.css"
  copy_photos
  rm -f "$WORK/assets"/*.png
  node "$ROOT/shot.js" "$WORK/html/cards.html" "$WORK/assets" card_ .wrap 1080 1350
fi

(cd "$WORK" && python3 gen_deck.py)
cp "$WORK/deck.css" "$WORK/html/deck.css"
rm -rf "$WORK/html/assets"
copy_photos
cp -r "$WORK/assets" "$WORK/html/assets"
rm -f "$WORK/out"/*.png
node "$ROOT/shot.js" "$WORK/html/slides.html" "$WORK/out" "$PREFIX" .s 1080 1440
python3 "$ROOT/qa.py" "$WORK/out" "$WORK/html/slides.html" "$WORK/deck.css"

if command -v magick > /dev/null 2>&1; then
  magick montage "$WORK/out"/*.png -tile x1 -geometry 330x440+6+6 -background '#cccccc' "$WORK/probe.png"
  echo "ГОТОВО. Контактка: $WORK/probe.png"
else
  echo "ГОТОВО. magick не найден, контактки нет. Кадры: $WORK/out"
fi
