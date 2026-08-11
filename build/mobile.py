#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Читаемость с телефона и безопасные поля. Версия 1.0.

    python3 build/mobile.py build/theme.css
    python3 build/mobile.py build/theme.css build/out/gm2019

Зачем это есть. Кадр 1080 на 1440 приезжает на экран телефона уменьшенным:
в ленте он занимает около трёх пятых высоты, поэтому кегль 21px с макета
превращается в мелочь, которую не читают. Второе: интерфейс площадки лежит
поверх кадра, справа кнопки, снизу подпись. Всё, что туда попало, зритель
не увидит.

Что проверяется:
  1. Кегль в теме. Ниже MIN_FONT провал, ниже WARN_FONT предупреждение.
  2. Фон светлого кадра. Белый это 250 и выше. Серый фон валит проверку,
     он съедает контраст мелкого текста.
  3. Безопасные поля на готовых PNG: правый край и нижняя полоса.

Код возврата 1, если есть хотя бы один провал.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

MIN_FONT = 26              # ниже этого текст на телефоне не читается
WARN_FONT = 28             # ниже этого только капсовые метки с разрядкой
WHITE_MIN = 250            # фон светлого кадра
DARK_MAX = 40              # фон тёмного кадра
SAFE_RIGHT = 1008          # правее лежат кнопки площадки
SAFE_BOTTOM = 1292         # ниже начинается подпись под роликом
FOOTER_BAND = 148          # своя подвальная полоса, она под подписью и не считается
INK_DELTA = 16

# Селекторы, которым мелкий кегль разрешён: это не текст для чтения.
ALLOWED_SMALL = (".cr", ".idx", ".sq", ".m .i")


class Report:
    def __init__(self) -> None:
        self.fails: list[str] = []
        self.warns: list[str] = []

    def fail(self, msg: str) -> None:
        print("ПРОВАЛ", msg)
        self.fails.append(msg)

    def warn(self, msg: str) -> None:
        print("ВНИМАНИЕ", msg)
        self.warns.append(msg)


def check_css(path: Path, report: Report) -> None:
    css = path.read_text(encoding="utf-8")
    css = re.sub(r"/\*[\s\S]*?\*/", " ", css)
    for block in re.finditer(r"([^{}]+)\{([^}]*)\}", css):
        selector = " ".join(block.group(1).split())
        for size in re.finditer(r"font-size:\s*(\d+)px", block.group(2)):
            value = int(size.group(1))
            if value >= WARN_FONT:
                continue
            if any(part in selector for part in ALLOWED_SMALL):
                continue
            if value < MIN_FONT:
                report.fail("%s: кегль %dpx, нижняя граница %d" % (selector, value, MIN_FONT))
            else:
                report.warn("%s: кегль %dpx, рабочая граница %d" % (selector, value, WARN_FONT))


def check_frame(path: Path, report: Report) -> None:
    from PIL import Image

    image = Image.open(path).convert("L")
    width, height = image.size
    px = image.load()
    corners = [px[3, 3], px[width - 4, 3], px[3, height - 4], px[width - 4, height - 4]]
    bg = Counter(corners).most_common(1)[0][0]

    if bg > 128:
        if bg < WHITE_MIN:
            report.fail("%s: фон %d, светлый кадр должен быть белым от %d"
                        % (path.name, bg, WHITE_MIN))
    elif bg > DARK_MAX:
        report.fail("%s: фон %d, тёмный кадр должен быть до %d" % (path.name, bg, DARK_MAX))

    body_bottom = height - FOOTER_BAND
    right = 0
    bottom = 0
    for y in range(0, body_bottom, 3):
        row = [x for x in range(0, width, 3) if abs(px[x, y] - bg) > INK_DELTA]
        if not row:
            continue
        # полоса во всю ширину это фото или плашка, она выходит в край по замыслу
        if len(row) / float(len(range(0, width, 3))) > 0.55:
            continue
        right = max(right, row[-1])
        bottom = y
    if right > SAFE_RIGHT:
        report.warn("%s: текст доходит до %d, кнопки площадки начинаются с %d"
                    % (path.name, right, SAFE_RIGHT))
    if bottom > SAFE_BOTTOM:
        report.warn("%s: текст опускается до %d, подпись под роликом начинается с %d"
                    % (path.name, bottom, SAFE_BOTTOM))


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("использование: python3 build/mobile.py <theme.css> [out_dir]")
        return 2

    report = Report()
    css_path = Path(args[0])
    if not css_path.exists():
        print("ПРОВАЛ нет файла темы: %s" % css_path)
        return 1
    check_css(css_path, report)

    frames = 0
    if len(args) > 1:
        out_dir = Path(args[1])
        images = sorted(out_dir.glob("*.png"))
        if not images:
            report.fail("в %s нет png" % out_dir)
        for image in images:
            check_frame(image, report)
        frames = len(images)

    if report.fails:
        print("ЧИТАЕМОСТЬ ПРОВАЛЕНА: %d, предупреждений %d"
              % (len(report.fails), len(report.warns)))
        return 1
    print("ЧИТАЕМОСТЬ ПРОЙДЕНА: кадров %d, предупреждений %d" % (frames, len(report.warns)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
