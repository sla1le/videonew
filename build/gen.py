# -*- coding: utf-8 -*-
"""Генератор дек ЭХО."""
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
    if f.get("bare"):
        return ""
    out = []
    want_idx = f.get("idx", True)
    if f.get("kick") or want_idx:
        num = '<div class="idx">%02d/%02d</div>' % (idx, total) if want_idx else ""
        out.append('<div class="top"><div class="kick">%s</div>'
                   '<div class="fill"></div>%s</div>' % (esc(f.get("kick", "")), num))
    out.append('<div class="%s"></div>' % ("rule" if f.get("rule", True) else "hair"))
    return "".join(out)


FOOT_VARIANTS = {"gold": "pg gd", "box": "pg bx", "mid": "pg md"}


def foot(f=None):
    cls = FOOT_VARIANTS.get((f or {}).get("foot", ""), "pg")
    return ('<div class="%s"><div class="sq"></div>'
            '<div class="tx">@ECHORATE</div></div>' % cls)


def titles(f, dark):
    out = []
    if f.get("h1"):
        out.append('<div class="h1">%s</div>' % mark_words(f["h1"], f.get("mark"), dark))
    if f.get("h2"):
        m = f.get("mark") if not f.get("h1") else None
        out.append('<div class="h2">%s</div>' % mark_words(f["h2"], m, dark))
    if f.get("h3"):
        out.append('<div class="h3">%s</div>' % esc(f["h3"]))
    if f.get("scope"):
        out.append('<div class="sco">%s</div>' % esc(f["scope"]))
    return "".join(out)


def tails(f):
    out = []
    if f.get("lead"):
        out.append('<div class="lead">%s</div>' % esc(f["lead"]))
    if f.get("acc"):
        out.append('<div class="acc">%s</div>' % esc(f["acc"]))
    for line in f.get("why", []):
        out.append('<div class="rsn">%s</div>' % esc(line))
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
    if f.get("rows"):
        out.append('<div class="fl tight">%s</div>' % "".join(
            '<div class="r"><div class="k">%s</div><div class="t">%s</div></div>'
            % (esc(k), esc(t)) for k, t in f["rows"]))
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
    short = len(f.get("rows", [])) <= 3 and not f.get("weights")
    out = [titles(f, dark)]
    if f.get("weights"):
        out.append('<div class="wg">%s</div>' % "".join(
            '<div><div class="k">%s</div><div class="v">%s</div></div>'
            % (esc(k), esc(v)) for k, v in f["weights"]))
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
    out.append('<div class="%s">%s</div>'
               % ("tb tall" if f.get("tall") else "tb", "".join(rows)))
    out.append(tails(f))
    short = len(f.get("rows", [])) <= 3 and not f.get("tall")
    return '<div class="bd%s">%s</div>' % ("" if short else " top0", "".join(out))


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


def body_cta(f, dark):
    out = [titles(f, dark), tails(f)]
    if f.get("rows"):
        rows = "".join('<div class="r"><div class="k">%s</div><div class="t">%s</div></div>'
                       % (esc(k), esc(t)) for k, t in f["rows"])
        out.append('<div class="fl tight">%s</div>' % rows)
    out.append('<div class="cta mid"><div class="a">%s</div><div class="b">%s</div></div>'
               % (esc(f["a"]), esc(f["b"])))
    return '<div class="bd">%s</div>' % "".join(out)


def body_card(f, dark):
    """Карта игрока внутри деки. Порядок статов задаёт дека."""
    c = f["card"]
    cells = []
    for row in c.get("stats", []):
        lab, val = row[0], row[1]
        why = row[2] if len(row) > 2 else ""
        try:
            w = max(0.0, min(100.0, (float(val) - 30.0) / 69.0 * 100.0))
        except (TypeError, ValueError):
            w = 0.0
        rsn = '<div class="rsn in">%s</div>' % esc(why) if why else ""
        cells.append('<div><div class="lab">%s</div><div class="ln2">%s</div>'
                     '<div class="br2"><i style="width:%.2f%%"></i></div>%s</div>'
                     % (esc(lab), esc(val), w, rsn))
    photo = ('<img class="ph2" src="%s" alt="">' % esc(c["img"])) if c.get("img") \
        else '<div class="ph2"></div>'
    card = ('<div class="fc"><div class="top2"><div class="lft">'
            '<div class="ovr">%s</div><div class="pos">%s</div></div>%s</div>'
            '<div class="rl"></div><div class="nm">%s</div>'
            '<div class="sb">%s</div><div class="gr">%s</div>'
            '<div class="pt"><span class="k">ПОТЕНЦИАЛ</span>'
            '<span class="v">%s</span></div>'
            '<div class="ft">T.ME/ECHORATE</div></div>'
            % (esc(c.get("ovr", "")), esc(c.get("pos", "")), photo,
               esc(c.get("name", "")), esc(c.get("sub", "")), "".join(cells),
               esc(c.get("pot", ""))))
    return '<div class="bd top0">%s%s%s</div>' % (titles(f, dark), card, tails(f))


def lines_block(f, dark):
    out = []
    at = f.get("mark_line")
    for i, line in enumerate(f.get("lines", [])):
        m = f.get("mark") if at == i else None
        out.append('<div class="gmh">%s</div>' % mark_words(line, m, dark))
    return "".join(out)


def body_gmcover(f, dark):
    out = [lines_block(f, dark)]
    cells = []
    for p in f.get("slots", []):
        cells.append('<div class="sl">%s<div class="cp">%s</div></div>'
                     % (ph(p["img"]), esc(p["nm"])))
    out.append('<div class="tri">%s</div>' % "".join(cells))
    out.append('<div class="hr"></div>')
    out.append('<div class="nt">%s</div>' % esc(f.get("note", "")))
    out.append('<div class="hr"></div>')
    return '<div class="bd top0">%s</div>' % "".join(out)


def rank_rows(rows, small=False):
    out = []
    for r in rows:
        sub = '<small>%s</small>' % esc(r[2]) if len(r) > 2 and r[2] else ""
        out.append('<div class="rk%s"><div class="n">%s</div>'
                   '<div class="t">%s%s</div></div>'
                   % (" sm" if small else "", esc(r[0]), esc(r[1]), sub))
    return '<div class="rks">%s</div>' % "".join(out)


def body_ranks(f, dark):
    out = [titles(f, dark), rank_rows(f["rows"]), tails(f)]
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_albums(f, dark):
    cap = '<div class="cp2">%s</div>' % esc(f["cap"]) if f.get("cap") else ""
    out = [titles(f, dark)]
    out.append('<div class="alb">%s<div class="cv">%s%s</div></div>'
               % (rank_rows(f["rows"], True), ph(f["img"]), cap))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_matrix(f, dark):
    out = [titles(f, dark)]
    heads = "".join('<div class="hd">%s</div>' % esc(h) for h in f["heads"])
    out.append('<div class="mx"><div class="rw hh"><div class="nm"></div>%s</div>' % heads)
    for row in f["rows"]:
        cells = []
        for v in row[1]:
            val, tone = v if isinstance(v, list) else (v, "")
            cells.append('<div class="vl %s"><span>%s</span><i></i></div>'
                         % (esc(tone), esc(val)))
        out.append('<div class="rw"><div class="nm">%s</div>%s</div>'
                   % (esc(row[0]), "".join(cells)))
    out.append("</div>")
    if f.get("verdict"):
        out.append('<div class="vd"><div class="k">%s</div><div class="t">%s</div></div>'
                   % (esc(f.get("vdk", "ВЫВОД")), esc(f["verdict"])))
    out.append(tails(f))
    return '<div class="bd top0">%s</div>' % "".join(out)


def body_weights(f, dark):
    out = [titles(f, dark)]
    out.append('<div class="wl">%s</div>' % "".join(
        '<div class="wr"><div class="k">%s</div><div class="v">%s</div></div>'
        % (esc(k), esc(v)) for k, v in f["weights"]))
    if f.get("big"):
        out.append('<div class="bigrow"><div class="big">%s</div>'
                   '<div class="un">%s</div></div>'
                   % (esc(f["big"]), esc(f.get("un", ""))))
    if f.get("note"):
        out.append('<div class="note">%s</div>' % esc(f["note"]))
    if f.get("fin"):
        out.append('<div class="fin">%s <b>%s</b></div>'
                   % (esc(f["fin"]), esc(f.get("finb", ""))))
    return '<div class="bd top0">%s</div>' % "".join(out)


CROWN = ('<svg class="cr2" viewBox="0 0 120 74" preserveAspectRatio="none">'
         '<path d="M6 70 L14 14 L40 44 L60 6 L80 44 L106 14 L114 70 Z" '
         'fill="#B08D1E"/></svg>')


def body_podium(f, dark):
    out = [titles(f, dark)]
    rows = []
    for i, r in enumerate(f["rows"]):
        rows.append('<div class="pd%s">%s<div class="n">%s</div>'
                    '<div class="t">%s</div><div class="v">%s</div></div>'
                    % (" win" if i == 0 else "", CROWN if i == 0 else "",
                       esc(r[0]), esc(r[1]), esc(r[2])))
    out.append('<div class="pds">%s</div>' % "".join(rows))
    out.append(tails(f))
    return '<div class="bd">%s</div>' % "".join(out)


def body_yearcard(f, dark):
    c = f["card"]
    rows = []
    for row in c.get("stats", []):
        lab, val = row[0], row[1]
        tone = row[2] if len(row) > 2 else ""
        why = row[3] if len(row) > 3 else ""
        try:
            w = max(0.0, min(100.0, (float(val) - 30.0) / 69.0 * 100.0))
        except (TypeError, ValueError):
            w = 0.0
        rows.append('<div class="sr"><div class="lb">%s</div>'
                    '<div class="vv %s">%s</div>'
                    '<div class="bx"><i class="%s" style="width:%.2f%%"></i></div></div>'
                    % (esc(lab), esc(tone), esc(val), esc(tone), w))
        if why:
            rows.append('<div class="rsn in">%s</div>' % esc(why))
    photo = ('<img class="pc" src="%s" alt="">' % esc(c["img"])) if c.get("img") \
        else '<div class="pc"></div>'
    card = ('<div class="yc"><div class="hd"><div class="lf">'
            '<div class="ov">%s</div><div class="ps">%s</div>'
            '<div class="se">%s</div></div>%s</div><div class="ln"></div>'
            '<div class="nm">%s</div><div class="sb">%s</div>'
            '<div class="ln"></div><div class="sts">%s</div>'
            '<div class="ft">%s</div></div>'
            % (esc(c.get("ovr", "")), esc(c.get("pos", "")), esc(c.get("season", "")),
               photo, esc(c.get("name", "")), esc(c.get("sub", "")),
               "".join(rows), esc(c.get("ft", ""))))
    out = [card]
    if f.get("a"):
        out.append('<div class="cta plain"><div class="a">%s</div></div>' % esc(f["a"]))
    return '<div class="bd top0">%s</div>' % "".join(out)


BODIES = {
    "cover": body_cover,
    "card": body_card,
    "text": body_text,
    "photo": body_photo,
    "duocover": body_duocover,
    "formula": body_formula,
    "facts": body_facts,
    "duel": body_duel,
    "stats": body_stats,
    "table": body_table,
    "verdict": body_verdict,
    "cta": body_cta,
    "gmcover": body_gmcover,
    "ranks": body_ranks,
    "albums": body_albums,
    "matrix": body_matrix,
    "weights": body_weights,
    "podium": body_podium,
    "yearcard": body_yearcard,
}


def frame(f, idx, total, prefix):
    kind = f.get("t", "text")
    if kind not in BODIES:
        raise SystemExit("НЕИЗВЕСТНЫЙ КАДР: %s. Есть: %s"
                         % (kind, ", ".join(sorted(BODIES))))
    dark = bool(f.get("dark"))
    cls = "s dk" if dark else "s lt"
    if f.get("skin"):
        cls += " " + f["skin"]
    dense = ' data-dense="1"' if f.get("dense") else ""
    return ('<section class="%s" data-name="%s_%02d"%s>%s%s%s</section>'
            % (cls, prefix, idx, dense, head(f, idx, total),
               BODIES[kind](f, dark), foot(f)))


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


def deck_images(node, found=None):
    if found is None:
        found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("img", "mos") and isinstance(value, str):
                found.append(value)
            elif key == "imgs" and isinstance(value, list):
                found.extend(v for v in value if isinstance(v, str))
            else:
                deck_images(value, found)
    elif isinstance(node, list):
        for value in node:
            deck_images(value, found)
    return found


def copy_assets(deck):
    if not os.path.exists(THEME):
        raise SystemExit("НЕТ theme.css в папке build")
    shutil.copy(THEME, os.path.join(HTML, "theme.css"))

    wanted = sorted(set(deck_images(deck)))
    dst = os.path.join(HTML, "img")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    if not wanted:
        return 0
    if not os.path.isdir(IMG):
        raise SystemExit(
            "НЕТ ПАПКИ build/img, а дека просит картинки:\n  "
            + "\n  ".join(wanted))
    missing = [p for p in wanted if not os.path.isfile(os.path.join(HERE, p))]
    if missing:
        raise SystemExit(
            "НЕТ ФОТО, пути считаются от папки build:\n  " + "\n  ".join(missing))
    shutil.copytree(IMG, dst)
    return len(wanted)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("укажи путь к деке")
    src = sys.argv[1]
    if not os.path.isfile(src):
        raise SystemExit("НЕТ ДЕКИ: %s" % src)

    deck = json.load(open(src, encoding="utf-8"))
    prefix = deck.get("prefix")
    if not prefix:
        raise SystemExit("НЕТ ПОЛЯ prefix в %s" % src)
    stem = os.path.splitext(os.path.basename(src))[0]
    if prefix != stem:
        raise SystemExit(
            "ПРЕФИКС НЕ СОВПАДАЕТ: в файле %r, имя файла %r." % (prefix, stem))

    os.makedirs(HTML, exist_ok=True)
    images = copy_assets(deck)

    out = os.path.join(HTML, prefix + ".html")
    open(out, "w", encoding="utf-8").write(build(deck))
    print("дека собрана: %s, кадров %d, картинок %d"
          % (out, len(deck["frames"]), images))


if __name__ == "__main__":
    main()
