#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Рендер прайм-карт ЭХО. Версия 1.

Счёт берётся только из rating/prime.py, руками баллы не вбиваются.
Форма карты по formats/card-spec.md: лента, OVR, позиция, значок, фото,
имя, статы, подвал. Пять статов в порядке ТЕКСТЫ ХИТЫ ЗВУК ВЛИЯНИЕ ПОДАЧА,
шестая ячейка пустая, ЛАЙВОВ на прайм-карте не бывает.
Металл назначает код по OVR: золото 80 и выше, серебро 70 до 79, ниже бронза.
Вместо ПОТЕНЦИАЛА у прайм-карты в подвале ЦЕНА. Дельта печатается только тогда,
когда артист есть в сегодняшней лиге.

Запуск: python3 build/gen_prime.py [ключ,ключ или all]
Дальше: node build/shot.js build/html/primes.html out/cards "" ".wrap" 1080 1350
"""
from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / "rating"))

import prime  # noqa: E402

OUT = HERE / "html" / "primes.html"
CSS = HERE / "card.css"
PHOTO_DIR = HERE / "photos"

# Порядок статов прайм-карты жёсткий.
LABELS = (("T", "ТЕКСТЫ"), ("H", "ХИТЫ"), ("S", "ЗВУК"),
          ("I", "ВЛИЯНИЕ"), ("D", "ПОДАЧА"))

METAL = {
    "gold": ("#D4AF37", "#9a8330"),
    "silver": ("#AEB4BC", "#6B7178"),
    "bronze": ("#B87445", "#7d4e2c"),
}


def stat(label: str, value: int) -> str:
    width = max(0.0, min(100.0, (value - 30) / 69 * 100))
    return ('<div class="stat"><div class="lab">%s</div><div class="line">%d</div>'
            '<div class="bar"><i style="width:%.2f%%"></i></div></div>' % (label, value, width))


def delta_chip(delta: int | None) -> str:
    if delta is None:
        return ""
    sign = "+" if delta > 0 else ""
    return '<div class="was">%s%d К СЕГОДНЯ</div>' % (sign, delta)


def face(card: dict) -> str:
    name = card.get("face")
    if name:
        path = PHOTO_DIR / name
        if path.exists():
            return '<img class="ph" src="photos/%s" alt="">' % html.escape(name)
    return ('<div class="ph" style="display:flex;align-items:flex-end;justify-content:center">'
            '<div style="font-family:Impact,sans-serif;font-size:150px;line-height:1;'
            'color:rgba(255,255,255,.14);padding-bottom:18px">%d</div></div>' % card["year"])


def card_html(card: dict) -> str:
    tone, dim = METAL[card["tier"]]
    name = card["name"]
    size = 90 if len(name) > 10 else 132
    stats = "".join(stat(label, int(card["stats"][code])) for code, label in LABELS)
    stats += '<div class="stat"></div>'

    # Лента держит тип и год карты, роль в выпуске идёт туда же.
    rib = "ПРАЙМ %d" % card["year"]
    if card.get("sub"):
        rib += " · " + card["sub"]
    ribbon = ('<div class="rib" style="font-family:%s;font-size:21px;letter-spacing:6px;'
              'white-space:nowrap;color:%s;margin-bottom:16px">%s</div>'
              % ("'Arial Black',Impact,sans-serif", tone, html.escape(rib)))

    # Под именем одна строка: альбом прайм-года. Две строки рвут низ карты.
    album = card.get("album") or ""
    sub_size = 26 if len(album) <= 26 else 22
    sub = ('<div class="sub" style="font-size:%dpx;white-space:nowrap">%s</div>'
           % (sub_size, html.escape(album)))

    return ('<section class="wrap" data-name="%s"><article class="card" '
            'style="--gold:%s;--dim:%s">%s'
            '<div class="top"><div class="lft"><div class="ovr">%d</div>'
            '<div class="pos">%s</div>%s</div>%s</div>'
            '<div class="rule"></div>'
            '<div class="name" style="font-size:%dpx">%s</div>%s'
            '<div class="grid">%s</div>'
            '<div class="pot"><span class="k">ЦЕНА, МЛН</span><span class="v">%d</span></div>'
            '<div class="foot">T.ME/ECHORATE</div></article></section>'
            % (html.escape(card["key"]), tone, dim, ribbon, card["ovr"],
               html.escape(card["pos"]), delta_chip(card["delta"]), face(card),
               size, html.escape(name), sub, stats, card["price_mln"]))


def main() -> None:
    want = sys.argv[1] if len(sys.argv) > 1 else "all"
    cards = prime.load()
    if want != "all":
        keys = set(want.split(","))
        cards = [c for c in cards if c["key"] in keys]
        if not cards:
            raise SystemExit("НЕТ ТАКОГО КЛЮЧА: " + want)
    body = "".join(card_html(c) for c in cards)
    doc = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
           '<link rel="stylesheet" href="card.css"></head><body>%s</body></html>' % body)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    if not CSS.exists():
        raise SystemExit("НЕТ card.css")
    shutil.copy(CSS, OUT.parent / "card.css")
    for c in cards:
        print("карта %s: OVR %d, %s, %d млн" % (c["key"], c["ovr"], c["tier"], c["price_mln"]))
    print("карты собраны: %s, штук %d" % (OUT, len(cards)))


if __name__ == "__main__":
    main()
