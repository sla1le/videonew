#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Линтер стиля ЭХО. Проверяет текст кадра, тогда как qa.py проверяет геометрию.

Запреты собраны из prompts/style-rules.md и prompts/design-rules.md.
До v4.0 они существовали только прозой в промпте и нарушались молча.

    python3 build/lint.py <папка выпуска>

Код возврата 1, если найдено хотя бы одно нарушение уровня ERROR.
"""
import re
import sys
from pathlib import Path

EMDASH = chr(8212)

EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0F"
    "]"
)

STAT_ORDER = ["ТЕКСТЫ", "ЗВУК", "ПОДАЧА", "ХИТЫ", "ЛАЙВЫ", "ВЛИЯНИЕ"]

STAT_ABBR = ["TEX", "ЗВК", "ПДЧ", "ХИТ", "ЛВ", "ВЛН", "POT", "OVR PLUS"]

BANNED_FONTS = [
    "Oswald", "Bebas", "Roboto", "Montserrat",
    "Inter", "Nimbus Sans Narrow", "Noto Sans",
]

TAGS = re.compile(r"<[^>]+>")


def text_of(html):
    """Грубое снятие разметки. Для подсчёта слов и чисел этого достаточно."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAGS.sub(" ", body)).strip()


def find_line(src, idx):
    return src.count("\n", 0, idx) + 1


# ---------------------------------------------------------------- проверки

def check_emdash(name, src, out):
    for m in re.finditer(re.escape(EMDASH), src):
        out.append(("ERROR", name, find_line(src, m.start()), "длинное тире U+2014"))


def check_emoji(name, src, out):
    for m in EMOJI.finditer(src):
        out.append(("ERROR", name, find_line(src, m.start()),
                    "эмодзи %r" % m.group(0)))


def check_ne_a(name, src, out):
    for pat, msg in (
        (r"не [^.,!?<>]{2,40}, а ", "конструкция вида не X, а Y"),
        (r", а не ", "конструкция вида X, а не Y"),
        (r"не просто", "оборот не просто"),
    ):
        for m in re.finditer(pat, src, flags=re.I):
            out.append(("ERROR", name, find_line(src, m.start()), msg))


def check_stat_names(name, src, out):
    txt = text_of(src)
    if "POT" in txt:
        out.append(("ERROR", name, 0, "POT вместо ПОТЕНЦИАЛ"))
    for abbr in STAT_ABBR:
        if abbr == "POT":
            continue
        if re.search(r"\b%s\b" % re.escape(abbr), txt):
            out.append(("ERROR", name, 0, "аббревиатура стата %s" % abbr))


def check_stat_order(name, src, out):
    txt = text_of(src)
    seen = [s for s in re.findall("|".join(STAT_ORDER), txt)]
    if len(seen) < 6:
        return
    first6 = seen[:6]
    if first6 != STAT_ORDER:
        out.append(("ERROR", name, 0,
                    "порядок статов нарушен: %s" % " ".join(first6)))


def check_episode_number(name, src, out):
    txt = text_of(src)
    for m in re.finditer(r"(ВЫПУСК|EPISODE|EP)\s*[#N]?\s*\d+", txt, flags=re.I):
        out.append(("ERROR", name, 0, "номер выпуска на кадре: %s" % m.group(0)))


def check_marks(name, src, out):
    n = src.count('class="mk')
    if n != 3:
        out.append(("ERROR", name, 0,
                    "рукописных пометок %d, требуется ровно 3" % n))


def check_fonts(name, src, out):
    for f in BANNED_FONTS:
        if f.lower() in src.lower():
            out.append(("ERROR", name, 0, "запрещённый шрифт %s" % f))


def check_font_shorthand(name, src, out):
    for m in re.finditer(r"font:[^;}]+", src):
        decl = m.group(0)
        if "var(" in decl:
            continue
        out.append(("ERROR", name, find_line(src, m.start()),
                    "сокращённая запись без семейства: %s" % decl.strip()))


def check_georgia_on_numbers(name, src, out):
    for m in re.finditer(r"\.(num|ovr|stat)[^{]*\{[^}]*Georgia", src, flags=re.I):
        out.append(("ERROR", name, find_line(src, m.start()),
                    "Georgia на числах, разрешена только для акцентной прозы"))


def check_headline(name, src, out):
    for m in re.finditer(r"<h1[^>]*>(.*?)</h1>", src, flags=re.S | re.I):
        words = text_of(m.group(1)).split()
        if len(words) > 6:
            out.append(("ERROR", name, find_line(src, m.start()),
                        "заголовок из %d слов, потолок 6" % len(words)))


def check_numbers_per_frame(name, src, out):
    txt = text_of(src)
    nums = re.findall(r"(?<![\w])\d[\d\s]*(?:[.,]\d+)?", txt)
    nums = [n for n in nums if n.strip()]
    if len(nums) > 3:
        out.append(("WARN", name, 0,
                    "чисел на кадре %d, потолок 3: %s" % (len(nums), " ".join(nums[:6]))))


def check_triads(name, src, out):
    txt = text_of(src)
    for m in re.finditer(r"\b([А-ЯЁа-яё]{3,}), ([А-ЯЁа-яё]{3,}) и ([А-ЯЁа-яё]{3,})\b", txt):
        out.append(("WARN", name, 0, "триада через запятую: %s" % m.group(0)))


def check_footer(name, src, out):
    if "1440" in src and "@ECHORATE" not in src:
        out.append(("WARN", name, 0, "в деке нет подвала @ECHORATE"))
    if "1350" in src and "T.ME/ECHORATE" not in src:
        out.append(("WARN", name, 0, "на карточке нет подвала T.ME/ECHORATE"))


HTML_CHECKS = [
    check_emdash, check_emoji, check_ne_a, check_stat_names, check_stat_order,
    check_episode_number, check_marks, check_fonts, check_headline,
    check_numbers_per_frame, check_triads, check_footer,
]

CSS_CHECKS = [
    check_emdash, check_emoji, check_fonts,
    check_font_shorthand, check_georgia_on_numbers,
]


def main():
    if len(sys.argv) < 2:
        print("использование: python3 build/lint.py <папка выпуска>")
        return 2

    root = Path(sys.argv[1])
    if not root.exists():
        print("нет такой папки: %s" % root)
        return 2

    out = []
    files = sorted(root.rglob("*.html")) + sorted(root.rglob("*.css"))
    if not files:
        print("в папке нет html и css")
        return 2

    for path in files:
        src = path.read_text(encoding="utf-8")
        checks = HTML_CHECKS if path.suffix == ".html" else CSS_CHECKS
        for fn in checks:
            fn(path.name, src, out)

    errors = [r for r in out if r[0] == "ERROR"]
    warns = [r for r in out if r[0] == "WARN"]

    print("ЛИНТЕР СТИЛЯ   файлов: %d" % len(files))
    print()

    for level, name, line, msg in errors + warns:
        where = "%s:%d" % (name, line) if line else name
        print("%-5s %-28s %s" % (level, where, msg))

    if not out:
        print("нарушений нет")

    print()
    print("ошибок: %d   предупреждений: %d" % (len(errors), len(warns)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
