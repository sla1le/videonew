#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Геометрия и текст кадров ЭХО. Версия 6.0.

Пороги взяты не из головы, а измерены на четырёх выпусках, которые автор считает
удачными: kreed_v3, buda_004, buda_vs_dhill_v2, gm_2016. Цифры и способ замера
лежат в refs/frames.csv и refs/design-canon.md.

Что изменилось против 5.0:
  1. Разрыв перед нижним блоком больше не считается ошибкой. В эталонах такой
     разрыв есть на половине кадров и доходит до 422 пикселей. Прежний потолок 118
     заставлял уплотнять кадр и убивал иерархию.
  2. Поля считаются только по текстовым полосам. Фото на всю ширину больше не
     валит левое поле. В эталонах есть кадр с left 0 и right 1079.
  3. Подвал живёт ниже тела и проверяется отдельно: в подвальной полосе может
     стоять только мелкая плашка.
  4. Добавлена плотность чернил. Кадр ниже 6 процентов пустой, выше 48
     перегружен. Диапазон эталонов 7,8 до 42,4.
  5. Режим --refs проверяет чужую папку кадров без html и css.
  6. Замечания разделены на провалы и предупреждения. Предупреждение не валит
     сборку, но требует взгляда глазами.

    python3 build/qa.py <out_dir> [slides.html] [theme.css]
    python3 build/qa.py --refs refs/gm_2016
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

# Допустимые размеры кадра. 1350 оставлен для старых выпусков.
SIZES = {(1080, 1440), (1080, 1350)}
FOOTER_BAND = 140          # полоса подвала от низа кадра
FOOTER_INK_MAX = 10.0      # процент чернил в подвальной полосе, чёрная плашка даёт 7,3
MAX_GAP = 150              # разрыв внутри тела
BOTTOM_BREAK_FROM = 700    # ниже этой линии разрешён один большой разрыв
BOTTOM_BREAK_MAX = 440     # потолок того разрыва
HEADER_AIR_UNTIL = 240     # воздух под шапкой
HEADER_AIR_MAX = 520
MIN_TOP = 40
MIN_LEFT = 58
MAX_RIGHT = 1032           # рукописная пометка законно выходит за колонку, в эталонах до 1029
INK_DELTA = 16
INK_MIN_PCT = 6.0
INK_MAX_PCT = 48.0
WIDE_ROW = 0.55            # полоса шире этого считается фото или плашкой
ALLOWED = {8470, 171, 187, 8226, 183, 8722, 1025, 1105, 215}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def fail(self, message: str) -> None:
        print("ПРОВАЛ", message)
        self.failures.append(message)

    def warn(self, message: str) -> None:
        print("ВНИМАНИЕ", message)
        self.warnings.append(message)


def check_text(html_path: Path, css_path: Path | None, report: Report) -> None:
    source = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8") if css_path else ""

    text = re.sub(r"<[^>]+>", " ", source)
    text = re.sub(r"\s+", " ", text)

    broken = [m for m in re.findall(r"font:[^;}]+", css) if "var(" not in m]
    if broken:
        report.fail(f"сокращённая запись font без семейства: {broken}")
    if chr(8212) in text:
        report.fail(f"длинное тире, штук: {text.count(chr(8212))}")
    if re.findall(r", а не ", text, flags=re.I):
        report.fail("оборот X, а не Y")
    if re.findall(r"не [^.,!?]{2,40}, а ", text, flags=re.I):
        report.fail("оборот не X, а Y")
    if "не просто" in text.lower():
        report.fail("оборот не просто")

    marks = source.count('class="mk')
    if marks != 3:
        report.fail(f"рукописных пометок {marks}, требуется ровно 3")

    weird = sorted({c for c in text if ord(c) > 1103 and ord(c) not in ALLOWED})
    if weird:
        report.fail(f"неожиданные символы: {weird}")


def _background(px, width: int, height: int) -> int:
    probes = [px[x, y] for x, y in (
        (3, 3), (width - 4, 3), (3, height - 4), (width - 4, height - 4),
        (width // 2, 3), (width // 2, height - 4))]
    return Counter(probes).most_common(1)[0][0]


def check_image(path: Path, report: Report) -> None:
    image = Image.open(path).convert("L")
    width, height = image.size
    if (width, height) not in SIZES:
        report.fail(f"{path.name}: {width}x{height}, разрешены {sorted(SIZES)}")
        return
    px = image.load()
    bg = _background(px, width, height)
    body_bottom = height - FOOTER_BAND

    def ink(x: int, y: int) -> bool:
        return abs(px[x, y] - bg) > INK_DELTA

    # занятость каждой полосы, шаг 4 пикселя по горизонтали
    xs = range(0, width, 4)
    row_fill = [sum(1 for x in xs if ink(x, y)) / float(len(xs)) for y in range(height)]

    body_rows = [y for y in range(body_bottom) if row_fill[y] > 0]
    if not body_rows:
        report.fail(f"{path.name}: кадр пустой")
        return

    if body_rows[0] < MIN_TOP:
        report.fail(f"{path.name}: верх {body_rows[0]} меньше {MIN_TOP}")

    # подвал: только мелкая плашка
    footer_ink = sum(row_fill[body_bottom:]) / float(FOOTER_BAND) * 100
    if footer_ink > FOOTER_INK_MAX:
        report.fail(f"{path.name}: в подвальной полосе чернил {footer_ink:.1f} процента, потолок {FOOTER_INK_MAX}")

    # разрывы по вертикали
    hard, soft = [], []
    previous = body_rows[0]
    for y in body_rows[1:]:
        span = y - previous
        if span > MAX_GAP:
            header_air = previous < HEADER_AIR_UNTIL and span <= HEADER_AIR_MAX
            bottom_break = previous >= BOTTOM_BREAK_FROM and span <= BOTTOM_BREAK_MAX
            if header_air:
                pass
            elif bottom_break:
                soft.append((previous, y, span))
            else:
                hard.append((previous, y, span))
        previous = y
    if hard:
        report.fail(f"{path.name}: дыры по вертикали {hard}")
    if len(soft) > 1:
        report.fail(f"{path.name}: нижних разрывов {len(soft)}, разрешён один {soft}")

    # поля считаются по полосам. Полоса с фото или плашкой выходит в край по замыслу,
    # и вся такая полоса из проверки полей исключается целиком вместе с подписями внутри неё.
    bands: list[list[int]] = []
    for y in body_rows:
        if bands and y - bands[-1][-1] <= 8:
            bands[-1].append(y)
        else:
            bands.append([y])
    text_bands = [b for b in bands if max(row_fill[y] for y in b) <= WIDE_ROW]
    left, right = width, 0
    for band in text_bands:
        for y in band[::4]:
            row = [x for x in range(width) if ink(x, y)]
            if row:
                left = min(left, row[0])
                right = max(right, row[-1])
    if right:
        if left < MIN_LEFT:
            report.fail(f"{path.name}: левое поле {left} меньше {MIN_LEFT}")
        if right > MAX_RIGHT:
            report.fail(f"{path.name}: правое поле {right} больше {MAX_RIGHT}")

    # плотность чернил
    ink_pct = sum(row_fill) / float(height) * 100
    if ink_pct < INK_MIN_PCT:
        report.warn(f"{path.name}: чернил {ink_pct:.1f} процента, кадр пустоват")
    elif ink_pct > INK_MAX_PCT:
        report.warn(f"{path.name}: чернил {ink_pct:.1f} процента, кадр перегружен")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit("использование: python3 qa.py <out_dir> [slides.html] [theme.css] | --refs <dir>")

    report = Report()
    if args[0] == "--refs":
        out_dir = Path(args[1])
        html_path = css_path = None
    else:
        out_dir = Path(args[0])
        html_path = Path(args[1]) if len(args) > 1 else None
        css_path = Path(args[2]) if len(args) > 2 else None

    if html_path:
        check_text(html_path, css_path, report)

    images = sorted(out_dir.glob("*.png"))
    if not images:
        report.fail(f"в {out_dir} нет png")
    for image in images:
        check_image(image, report)

    if report.failures:
        print(f"QA ПРОВАЛЕН: {len(report.failures)}, предупреждений {len(report.warnings)}")
        raise SystemExit(1)
    print(f"QA ПРОЙДЕН: кадров {len(images)}, предупреждений {len(report.warnings)}"
          )


if __name__ == "__main__":
    main()
