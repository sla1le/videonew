# -*- coding: utf-8 -*-
"""Генератор дек ЭХО. Версия 5.

Запуск: python3 build/gen.py build/decks/prime.json
Пишет build/html/<prefix>.html и копирует активы рядом.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "html")
THEME = os.path.join(HERE, "theme.css")
IMG = os.path.join(HERE, "img")


def esc(s):
    s = str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- пометки
def svg_mark(kind, dark):
    col = "#FFFFFF" if dark else "#101010"
    if kind == "c":
        return (
            '<svg class="mk mkc" viewBox="0 0 300 100" preserveAspectRatio="none">'
            '<path d="M150 6 C 45 6, 8 30, 8 50 C 8 74, 60 95, 152 95 '
            'C 244 95, 292 73, 292 50 C 292 27, 246 7, 140 8" '
            'stroke="%s" stroke-width="4" fill="none" stroke-linecap="round"/></svg>' % col
        )
    if kind == "s":
        return (
            '<svg class="mk mks" viewBox="0 0 300 30" preserveAspectRatio="none">'
            '<path d="M3 18 C 80 8, 190 26, 297 12" stroke="%s" stroke-width="6" '
            'fill="none" stroke-linecap="round"/></svg>' % col
        )
    return (
        '<svg class="mk mku" viewBox="0 0 300 26" preserveAspectRatio="none">'
        '<path d="M4 15 C 62 5, 148 23, 296 9" stroke="%s" stroke-width="7" '
        'fill="none" stroke-linecap="round"/>'
        '<path d="M10 23 C 74 15, 156 28, 290 18" stroke="%s" stroke-width="3" '
        'fill="none" stroke-linecap="round" opacity=".55"/></svg>' % (col, col)
    )


def mark_words(text, mark, dark):
    """Оборачивает указанные слова в пометку от руки."""
    if not mark:
        return esc(text)
    words = mark.get("words", "")
    if words not in text:
        raise SystemExit("ПОМЕТКА НЕ НАЙДЕНА: %r в %r" % (words, text))
    before, after = text.split(words, 1)
    return "%s<span class=\"u\">%s%s</span>%s" % (
        esc(before), esc(words), svg_mark(mark.get("type", "u"), dark), esc(after))


# ---------------------------------------------------------------- блоки
def head(f, idx, total):
    kick = esc(f.get("kick", ""))
    out = ['<div class="top"><div class="kick">%s</div><div class="fill"></div>'
           '<div class="idx">%02d/%02d</div></div>' % (kick, idx, total)]
    out.append('<div class="%s"></div>' % ("rule" if f.get("rule", True) else "hair"))
    return "".join(out)


def foot():
    return '<div class="pg"><div class="sq"></div><div class="tx">@ECHORATE</div></div>'


def titles(f, dark):
    out = []
    if f.get("h1"):
        out.append('<div class="h1">%s</div>' % mark_words(f["h1"], f.get("mark"), dark))
    if f.get("h2"):
        m = f.get("mark") if not f.get("h1") else None
        out.append('<div class="h2">%s</div>' % mark_words(f["h2"], m, dark))
    if f.get("h3"):
        out.append('<div class="h3">%s</div>' % esc(f["h3"]))
    return "".join(out)


def tails(f):
    out = []
    if f.get("lead"):
        out.append('<div class="lead">%s</div>' % esc(f["lead"]))
    if f.get("acc"):
        out.append('<div class="acc">%s</div>' % esc(f["acc"]))
    if f.get("note"):
        out.append('<div class="note">%s</div>' % esc(f["note"]))
    return "".join(out)


def ph(src, cr=""):
    inner = '<img src="%s">' % esc(src)
    if cr:
        inner += '<div class="cr">%s</div>' % esc(cr)
    return '<div class="ph">%s</div>' % inner


def body_cover(f, dark):
    out = []
    if f.get("pair"):
        cells = []
        for p in f["pair"]:
            cells.append('<div>%s<div class="nm">%s</div><div class="yr">%s</div></div>'
                         % (ph(p["img"], p.get("cr", "")), esc(p["nm"]), esc(p.get("yr", ""))))
        out.append('<div class="pair">%s</div>' % "".join(cells))
    if f.get("mos"):
        out.append('<div class="mos"><img src="%s"></div>' % esc(f["mos"]))
    out.append('<div class="bd top0">%s%s</div>' % (titles(f, dark), tails(f)))
    return "".join(out)


def body_text(f, dark):
    return '<div class="bd">%s%s</div>' % (titles(f, dark), tails(f))


def body_photo(f, dark):
    out = [titles(f, dark)]
    out.append('<div class="wide">%s</div>' % ph(f["img"], f.get("cr", "")))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_duocover(f, dark):
    out = [titles(f, dark)]
    out.append('<div class="duo"><img src="%s"><div class="tx"><b>%s</b>%s</div></div>'
               % (esc(f["img"]), esc(f.get("title", "")), esc(f.get("tx", ""))))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_formula(f, dark):
    out = [titles(f, dark)]
    lines = "".join('<div class="l">%s</div>' % l for l in f.get("lines_html", [])) \
        or "".join('<div class="l">%s</div>' % esc(l) for l in f.get("lines", []))
    out.append('<div class="fx">%s</div>' % lines)
    if f.get("weights"):
        cells = "".join('<div><div class="k">%s</div><div class="v">%s</div></div>'
                        % (esc(k), esc(v)) for k, v in f["weights"])
        out.append('<div class="wt">%s</div>' % cells)
    out.append(tails(f))
    return '<div class="bd">%s</div>' % "".join(out)


def body_facts(f, dark):
    short = len(f.get("rows", [])) <= 3
    out = [titles(f, dark)]
    rows = "".join('<div class="r"><div class="k">%s</div><div class="t">%s</div></div>'
                   % (esc(k), esc(t)) for k, t in f["rows"])
    cls = "fl tight" if f.get("tight") else "fl"
    out.append('<div class="%s">%s</div>' % (cls, rows))
    out.append(tails(f))
    return '<div class="bd%s">%s</div>' % ("" if short else " top0", "".join(out))


def body_duel(f, dark):
    out = [titles(f, dark)]
    a, b = f["a"], f["b"]
    aw = a.get("win", True)
    out.append('<div class="duel">')
    out.append('<div class="side%s"><div><div class="nm">%s</div><div class="al">%s</div></div>'
               '<div class="chip %s">%s</div></div>'
               % ("" if aw else " l", esc(a["nm"]), esc(a.get("al", "")),
                  "w" if aw else "l", esc(a["v"])))
    out.append('<div class="vs"><div class="ln"></div><div class="tx">%s</div>'
               '<div class="ln"></div></div>' % esc(f.get("vs", "ПРОТИВ")))
    out.append('<div class="side%s"><div><div class="nm">%s</div><div class="al">%s</div></div>'
               '<div class="chip %s">%s</div></div>'
               % ("" if not aw else " l", esc(b["nm"]), esc(b.get("al", "")),
                  "w" if not aw else "l", esc(b["v"])))
    out.append("</div>")
    if f.get("gapv"):
        out.append('<div class="gap"><div class="k">%s</div><div class="v">%s</div></div>'
                   % (esc(f.get("gapk", "РАЗРЫВ")), esc(f["gapv"])))
        w = float(f.get("bar", 0.5)) * 100.0
        out.append('<div class="bar"><i style="width:%.1f%%"></i></div>' % w)
    out.append(tails(f))
    return '<div class="bd">%s</div>' % "".join(out)


def body_stats(f, dark):
    out = [titles(f, dark)]
    hdr = f.get("heads")
    if hdr:
        out.append('<div class="gap"><div class="k">%s</div><div class="k">%s</div></div>'
                   % (esc(hdr[0]), esc(hdr[1])))
    rows = []
    for r in f["rows"]:
        k, a, b = r[0], float(r[1]), float(r[2])
        wa = max(4.0, (a - 30.0) / 69.0 * 100.0)
        wb = max(4.0, (b - 30.0) / 69.0 * 100.0)
        rows.append(
            '<div class="row"><div class="lb"><div class="k">%s</div>'
            '<div><span class="a">%s</span> <span class="b">%s</span></div></div>'
            '<div class="tw"><span class="fa" style="width:%.1f%%"></span>'
            '<span class="fb" style="width:%.1f%%"></span></div></div>'
            % (esc(k), esc(r[1]), esc(r[2]), wa / 2.0, wb / 2.0))
    out.append('<div class="st">%s</div>' % "".join(rows))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_table(f, dark):
    out = [titles(f, dark)]
    rows = []
    for r in f["rows"]:
        hi = " hi" if r[0] in f.get("hi", []) else ""
        sub = '<small>%s</small>' % esc(r[2]) if len(r) > 2 and r[2] else ""
        rows.append('<div class="tr%s"><div class="n">%s</div>'
                    '<div class="t">%s%s</div><div class="v">%s</div></div>'
                    % (hi, esc(r[0]), esc(r[1]), sub, esc(r[3])))
    out.append('<div class="tb">%s</div>' % "".join(rows))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_bracket(f, dark):
    out = [titles(f, dark)]
    cells = []
    for m in f["matches"]:
        hot = " hot" if m.get("hot") else ""
        cells.append(
            '<div class="m%s"><div class="i">%s</div>'
            '<div class="n">%s</div><div class="v">%s</div>'
            '<div class="n lo">%s</div><div class="v lo">%s</div></div>'
            % (hot, esc(m["i"]), esc(m["a"]), esc(m["av"]), esc(m["b"]), esc(m["bv"])))
    half = (len(cells) + 1) // 2
    out.append('<div class="br"><div>%s</div><div>%s</div></div>'
               % ("".join(cells[:half]), "".join(cells[half:])))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_verdict(f, dark):
    out = [titles(f, dark)]
    cls = "big"
    if f.get("tone") == "g":
        cls = "big g"
    if f.get("tone") == "r":
        cls = "big r"
    out.append('<div class="bigrow"><div class="%s">%s</div><div class="un">%s</div></div>'
               % (cls, esc(f["big"]), esc(f.get("un", ""))))
    if f.get("stamp"):
        out.append('<div style="margin-top:26px"><span class="stamp">%s</span></div>'
                   % esc(f["stamp"]))
    out.append(tails(f))
    return '<div class="bd">%s</div>' % "".join(out)


def body_covers(f, dark):
    out = [titles(f, dark)]
    imgs = "".join('<img src="%s">' % esc(s) for s in f["imgs"])
    out.append('<div class="cvs">%s</div>' % imgs)
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_cta(f, dark):
    out = [titles(f, dark), tails(f)]
    if f.get("rows"):
        rows = "".join('<div class="r"><div class="k">%s</div><div class="t">%s</div></div>'
                       % (esc(k), esc(t)) for k, t in f["rows"])
        out.append('<div class="fl tight">%s</div>' % rows)
    out.append('<div class="cta mid"><div class="a">%s</div><div class="b">%s</div></div>'
               % (esc(f["a"]), esc(f["b"])))
    return '<div class="bd">%s</div>' % "".join(out)


BODIES = {
    "cover": body_cover,
    "text": body_text,
    "photo": body_photo,
    "duocover": body_duocover,
    "formula": body_formula,
    "facts": body_facts,
    "duel": body_duel,
    "stats": body_stats,
    "table": body_table,
    "bracket": body_bracket,
    "verdict": body_verdict,
    "covers": body_covers,
    "cta": body_cta,
}


def frame(f, idx, total, prefix):
    kind = f.get("t", "text")
    if kind not in BODIES:
        raise SystemExit("НЕИЗВЕСТНЫЙ КАДР: " + kind)
    dark = bool(f.get("dark"))
    cls = "s dk" if dark else "s lt"
    dense = ' data-dense="1"' if f.get("dense") else ""
    return ('<section class="%s" data-name="%s_%02d"%s>%s%s%s</section>'
            % (cls, prefix, idx, dense, head(f, idx, total),
               BODIES[kind](f, dark), foot()))


def build(deck):
    prefix = deck["prefix"]
    frames = deck["frames"]
    total = len(frames)
    if total > 20:
        raise SystemExit("КАДРОВ %d, КАРУСЕЛЬ ДЕРЖИТ 20" % total)
    parts = [frame(f, i + 1, total, prefix) for i, f in enumerate(frames)]
    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<title>%s</title><link rel="stylesheet" href="theme.css"></head>'
        '<body>%s</body></html>' % (esc(deck.get("title", prefix)), "".join(parts))
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit("укажи путь к деке, например build/decks/prime.json")
    deck = json.load(open(sys.argv[1], encoding="utf-8"))
    os.makedirs(HTML, exist_ok=True)
    if not os.path.exists(THEME):
        raise SystemExit("НЕТ theme.css")
    shutil.copy(THEME, os.path.join(HTML, "theme.css"))
    if not os.path.isdir(IMG):
        raise SystemExit("НЕТ папки img")
    dst_img = os.path.join(HTML, "img")
    if os.path.isdir(dst_img):
        shutil.rmtree(dst_img)
    shutil.copytree(IMG, dst_img)
    html = build(deck)
    out = os.path.join(HTML, deck["prefix"] + ".html")
    open(out, "w", encoding="utf-8").write(html)
    print("дека собрана: %s, кадров %d" % (out, len(deck["frames"])))


if __name__ == "__main__":
    main()
