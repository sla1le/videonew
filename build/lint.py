# -*- coding: utf-8 -*-
"""Линтер текста и вёрстки деки. Версия 5.

Запуск: python3 build/lint.py build/html/slides.html build/theme.css
"""
import os
import re
import sys

EMDASH = chr(8212)
ENDASH = chr(8211)
STAT_ORDER = ["ТЕКСТЫ", "ЗВУК", "ПОДАЧА", "ХИТЫ", "ЛАЙВЫ", "ВЛИЯНИЕ"]
STAT_ABBR = ["POT", "OVR PLUS", "ТЕК", "ЗВК", "ПДЧ", "ХИТ ", "ВЛН"]
BANNED_FONTS = ["Oswald", "Bebas", "Roboto", "Montserrat", "Inter",
                "Nimbus Sans Narrow", "Noto Sans"]
FOOTER = "@ECHORATE"
YEAR_LO, YEAR_HI = 1990, 2035

fails = []
warns = []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def strip_tags(chunk):
    chunk = re.sub(r"<svg[\s\S]*?</svg>", " ", chunk)
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = chunk.replace("&nbsp;", " ").replace("&amp;", "&")
    chunk = chunk.replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", chunk).strip()


def split_frames(html):
    parts = re.findall(r"<section class=\"s[\s\S]*?</section>", html)
    return parts


# ---------------------------------------------------------------- текст
def check_global_text(text):
    if EMDASH in text:
        fail("длинное тире в тексте")
    if ENDASH in text:
        fail("среднее тире в тексте")
    for m in re.finditer(r"не [^.,!?<>]{2,40}, а ", text):
        fail("шаблон не X, а Y: " + m.group(0)[:60])
    for m in re.finditer(r", а не ", text):
        fail("шаблон X, а не Y")
    if "не просто" in text.lower():
        fail("оборот не просто")
    for ch in text:
        o = ord(ch)
        if 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF:
            fail("эмодзи в тексте: " + ch)
            break
    if re.search(r"(ВЫПУСК|EPISODE|EP)\s*[#N]?\s*\d+", text):
        fail("номер выпуска на кадре")
    for ab in STAT_ABBR:
        if re.search(r"(?<![А-ЯёЁA-Z])%s(?![А-ЯёЁA-Z])" % ab.strip(), text):
            fail("аббревиатура стата: " + ab.strip())


def check_stat_order(frame_text):
    seen = [s for s in STAT_ORDER if s in frame_text]
    if len(seen) < 3:
        return
    idx = [frame_text.index(s) for s in seen]
    if idx != sorted(idx):
        fail("порядок статов нарушен: " + ", ".join(seen))


def numbers_in(text):
    out = []
    for m in re.finditer(r"\d[\d\u00a0.,]*", text):
        raw = m.group(0).strip(".,")
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            continue
        if len(digits) == 4 and YEAR_LO <= int(digits) <= YEAR_HI:
            continue
        out.append(raw)
    return out


def check_frame(i, frame):
    name = re.search(r'data-name="([^"]+)"', frame)
    name = name.group(1) if name else "frame%02d" % (i + 1)
    dense = 'data-dense="1"' in frame
    text = strip_tags(frame)

    if FOOTER not in text:
        fail("%s: нет подвала %s" % (name, FOOTER))

    for tag in ("h1", "h2"):
        for m in re.finditer(r'<div class="%s"[^>]*>([\s\S]*?)</div>' % tag, frame):
            words = strip_tags(m.group(1)).split()
            limit = 6 if tag == "h1" else 8
            if len(words) > limit:
                warn("%s: заголовок %s из %d слов" % (name, tag, len(words)))

    inner = re.sub(r'<div class="top">[\s\S]*?</div>\s*</div>', " ", frame)
    inner = re.sub(r'<div class="idx">[\s\S]*?</div>', " ", inner)
    nums = numbers_in(strip_tags(inner).replace(FOOTER, " "))
    if not dense:
        if len(nums) > 6:
            fail("%s: чисел на кадре %d" % (name, len(nums)))
        elif len(nums) > 3:
            warn("%s: чисел на кадре %d %s" % (name, len(nums), nums))

    check_stat_order(text)

    body = strip_tags(re.sub(r'<div class="pg"[\s\S]*?</div>\s*</div>', " ", frame))
    if len(body) < 40:
        warn("%s: почти пустой кадр" % name)
    return name


def check_marks(html, expected=3):
    got = html.count('class="mk')
    if got != expected:
        fail("пометок от руки %d, нужно %d" % (got, expected))


def check_cta(html):
    got = html.count('class="cta')
    if got != 1:
        fail("призывов в деке %d, нужен один" % got)


# ---------------------------------------------------------------- css
def check_css(css):
    for f in BANNED_FONTS:
        if f in css:
            fail("запрещённый шрифт в css: " + f)
    for m in re.finditer(r"[^-a-z]font:\s*([^;}]+)", css):
        if "var(" not in m.group(1):
            fail("сокращённый font без var: " + m.group(1)[:40])
    for m in re.finditer(r"\.(num|big|chip|tr \.v)[^{]*\{[^}]*Georgia", css):
        fail("Georgia на числах: " + m.group(0)[:40])


def main():
    if len(sys.argv) < 2:
        print("укажи путь к slides.html")
        return 2
    html_path = sys.argv[1]
    css_path = sys.argv[2] if len(sys.argv) > 2 else None
    html = open(html_path, encoding="utf-8").read()

    frames = split_frames(html)
    if not frames:
        print("ПРОВАЛ: кадров не найдено")
        return 1
    if len(frames) > 20:
        fail("кадров %d, карусель держит 20" % len(frames))

    check_global_text(strip_tags(html))
    check_marks(html)
    check_cta(html)
    for i, fr in enumerate(frames):
        check_frame(i, fr)

    if css_path and os.path.exists(css_path):
        check_css(open(css_path, encoding="utf-8").read())

    for w in warns:
        print("ВНИМАНИЕ:", w)
    for f in fails:
        print("ПРОВАЛ:", f)
    if fails:
        print("ЛИНТ ПРОВАЛЕН: %d" % len(fails))
        return 1
    print("ЛИНТ ПРОЙДЕН: кадров %d, замечаний %d" % (len(frames), len(warns)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
