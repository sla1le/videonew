#!/usr/bin/env python3
"""Seven-frame starter deck. Copy to a work folder as gen_deck.py and rewrite the story."""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "rating" / "data" / "league.json"
OUT = HERE / "html" / "slides.html"
UNDER = '<svg class="mk mku" viewBox="0 0 600 30" preserveAspectRatio="none"><path d="M6 17 C 150 5, 350 27, 594 10" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>'
CIRC = '<svg class="mk mkc" viewBox="0 0 300 110" preserveAspectRatio="none"><ellipse cx="150" cy="55" rx="143" ry="48" transform="rotate(-2 150 55)" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/></svg>'


def u(text: str) -> str:
    return f'<span class="u">{html.escape(text)}{UNDER}</span>'


def ci(text: str) -> str:
    return f'<span class="u">{html.escape(text)}{CIRC}</span>'


def head(kick: str, title: str) -> str:
    return f'<div class="kick">{html.escape(kick)}</div><div class="rule"></div><div class="h2">{title}</div>'


def row(number: int, name: str, value: int, cls: str = "") -> str:
    return f'<div class="rowline"><span class="n">{number:02d}</span><span class="t">{html.escape(name)}</span><span class="v {cls}">{value}</span></div>'


def frame(number: int, body: str) -> str:
    return f'<section class="s" data-name="{number:02d}">{body}<div class="pg">@ECHORATE</div></section>'


def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))["rows"]
    winner, second = rows[0], rows[1]
    slides = []
    slides.append(frame(1, head("ECHORATE", f'КТО СЕЙЧАС {u("ПЕРВЫЙ")}?') + '<div class="note">Шесть статов. Один общий балл.</div>'))
    slides.append(frame(2, head("КОНФЛИКТ", f'{u(winner["name"])} ПРОТИВ {html.escape(second["name"])}') + f'<div class="bd"><div class="big r">{winner["ovr"]}</div><div class="note">Лидер текущей таблицы</div></div>'))
    slides.append(frame(3, head("ПЕРВЫЙ АРГУМЕНТ", "ХИТЫ ДАЮТ ТРЕТЬ") + '<div class="frm"><div class="l">ST получает <b>30%</b> итогового балла за хиты.</div></div>'))
    slides.append(frame(4, head("ОДНА ФОРМУЛА", "ВСЕ СЧИТАЮТСЯ ОДИНАКОВО") + '<div class="wts"><div><div class="k">СУДЬИ</div><div class="v">50%</div></div><div><div class="k">ЦИФРЫ</div><div class="v">50%</div></div></div>'))
    top = ''.join(row(i + 1, item["name"], item["ovr"], "r" if i == 0 else "") for i, item in enumerate(rows[:4]))
    slides.append(frame(5, head("ТАБЛИЦА", "ВЕРХ ЛИГИ") + f'<div class="bd">{top}</div>'))
    slides.append(frame(6, head("ПОТЕНЦИАЛ", f'{html.escape(second["name"])} МОЖЕТ ДОГНАТЬ') + f'<div class="bd"><div class="big">{second["potential"]}</div><div class="note">Возраст и текущая форма</div></div>'))
    slides.append(frame(7, head("ТВОЙ ХОД", f'{ci("ГДЕ Я ОШИБСЯ")}?') + '<div class="cta"><div class="a">ГОЛОСУЙ ЗА НЕКСТА</div><div class="b">Опрос уже лежит в @echorate</div></div>'))
    document = '<!doctype html><html lang="ru"><head><meta charset="utf-8"><link rel="stylesheet" href="deck.css"></head><body>' + ''.join(slides) + '</body></html>'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    print(f"WROTE {OUT} {len(slides)} frames")


if __name__ == "__main__":
    main()
