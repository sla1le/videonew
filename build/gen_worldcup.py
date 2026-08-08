#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запуск Кубка альбомов. Семь кадров вместо списка из шестнадцати матчей.

    python3 build/gen_worldcup.py

Первый раунд не пересказывается целиком. В ленту идут три пары, которые меняют
разговор об альбомах. Полная сетка остаётся данными движка.
"""
from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rating"))

import worldcup  # noqa: E402

OUT = HERE / "html" / "slides.html"

UNDER = (
    '<svg class="mk mku" viewBox="0 0 600 30" preserveAspectRatio="none">'
    '<path d="M6 17 C 150 5, 350 27, 594 10" fill="none" stroke="currentColor" '
    'stroke-width="4" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>'
)
CIRC = (
    '<svg class="mk mkc" viewBox="0 0 300 110" preserveAspectRatio="none">'
    '<ellipse cx="150" cy="55" rx="143" ry="48" transform="rotate(-2 150 55)" fill="none" '
    'stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/></svg>'
)


def esc(text: str) -> str:
    return html.escape(text)


def wrap(text: str, svg: str) -> str:
    return f'<span class="u">{esc(text)}{svg}</span>'


def mark_word(title: str, word: str, svg: str) -> str:
    before, found, after = title.partition(word)
    if not found:
        raise SystemExit(f"в заголовке нет слова для пометки: {word}")
    return f"{esc(before)}{wrap(found, svg)}{esc(after)}"


def head(kick: str, title_html: str) -> str:
    return (
        f'<div class="kick">{esc(kick)}</div>'
        '<div class="rule"></div>'
        f'<div class="h2">{title_html}</div>'
    )


def frame(number: int, body: str, dense: bool = False) -> str:
    attr = ' data-dense="1"' if dense else ""
    return f'<section class="s" data-name="{number:02d}"{attr}>{body}<div class="pg">@ECHORATE</div></section>'


def side(row: dict, winner: bool) -> str:
    css = "a w" if winner else "a l"
    return (
        f'<div class="{css}"><div class="i"><div class="ar">{esc(row["artist"])}</div>'
        f'<div class="tt">{esc(row["title"])}, {row["year"]}</div></div>'
        f'<div class="v">{row["ovr"]}</div></div>'
    )


def match_frame(number: int, match: dict, title: str, note: str, marked: tuple[str, str] | None = None) -> str:
    title_html = mark_word(title, marked[0], marked[1]) if marked else esc(title)
    top, bottom = match["top"], match["bottom"]
    winner = match["winner"]
    body = (
        head("МАТЧ, КОТОРЫЙ МЕНЯЕТ СПОР", title_html)
        + '<div class="bd"><div class="duel">'
        + side(top, top["key"] == winner)
        + '<div class="vs">ПРОТИВ</div>'
        + side(bottom, bottom["key"] == winner)
        + f'</div><div class="note">{esc(note)}</div></div>'
    )
    return frame(number, body)


def featured(matches: list[dict], key: str) -> dict:
    for match in matches:
        if match["winner"] == key:
            return match
    raise SystemExit(f"в 1/16 нет ожидаемого матча: {key}")


def build() -> list[str]:
    data = worldcup.round_of(32)
    if not data.get("ready"):
        raise SystemExit(f"раунд заблокирован: {data['blocked_by']}")
    matches = data["matches"]
    if len(matches) != 16:
        raise SystemExit(f"в раунде {len(matches)} матчей вместо 16")

    gorgorod = featured(matches, "oxxxymiron_gorgorod")
    pharaoh = featured(matches, "pharaoh_pinkphloyd")
    closest = min(matches, key=lambda match: match["margin"])
    important = [matches[0], gorgorod, pharaoh, closest]

    slides = []
    cover = (
        head("КУБОК АЛЬБОМОВ", wrap("32 АЛЬБОМА", UNDER) + " С 2000 ГОДА")
        + '<div class="bd"><div class="frm"><div class="l">Один альбом от артиста. '
        'В сетку попал только релиз с местом в опубликованном списке.</div></div>'
        '<div class="note">Сегодня три пары, из-за которых весь Кубок есть смысл начинать.</div></div>'
    )
    slides.append(frame(1, cover))

    method = (
        head("КАК СЧИТАЛОСЬ", "ПОЛОВИНА БАЛЛА НЕ МОЯ")
        + '<div class="bd"><div class="wts"><div><div class="k">СУДЬЯ</div><div class="v">50%</div></div>'
        '<div><div class="k">СПИСКИ</div><div class="v">50%</div></div></div>'
        '<div class="frm"><div class="l">ТЕКСТЫ, ЗВУК и ПОДАЧА мои. ВЛИЯНИЕ считается '
        'по сотне Афиши Daily и двадцатке The Flow.</div></div>'
        '<div class="note">Прослушивания не считаю. Для нулевых нет общей честной базы.</div></div>'
    )
    slides.append(frame(2, method))
    slides.append(match_frame(
        3, gorgorod, "ГОРГОРОДА НЕТ В СОТНЕ",
        "Перечитал все сто мест. В этой модели Горгород держится на одной записи The Flow.",
        ("НЕТ В СОТНЕ", CIRC),
    ))
    slides.append(match_frame(
        4, pharaoh, "ФАРАОНА АФИША НЕ ЗАМЕТИЛА",
        "У Pink Phloyd нет ни одной строки в сотне. Одна запись The Flow оставляет его в игре.",
    ))
    slides.append(match_frame(
        5, closest, "САМЫЙ БЛИЗКИЙ МАТЧ", "Разрыв решают сотые балла. Здесь исход нельзя угадать по имени.", ("БЛИЗКИЙ", UNDER)))

    rows = "".join(
        '<div class="rowline"><div class="n">%02d</div><div class="t">%s</div><div class="v">%s</div></div>'
        % (match["match"], esc(next(row for row in (match["top"], match["bottom"]) if row["key"] == match["winner"])["artist"]),
           next(row for row in (match["top"], match["bottom"]) if row["key"] == match["winner"])["ovr"])
        for match in important
    )
    summary = (
        head("ПЕРВЫЙ РАУНД", "ЧЕТЫРЕ ПАРЫ, ГДЕ ЕСТЬ СПОР")
        + f'<div class="bd">{rows}<div class="note">Остальные пары не несут новой мысли. Их результат уже лежит в сетке.</div></div>'
    )
    slides.append(frame(6, summary, dense=True))

    cta = (
        head("ВАШ ХОД", "КОГО РАЗОБРАТЬ ДАЛЬШЕ")
        + '<div class="bd"><div class="fact"><div class="d">3 ПАРЫ</div>'
        '<div class="t">Горгород, Pink Phloyd и самый близкий матч раунда.</div></div>'
        '<div class="cta"><div class="a">КОГО ВЫБИЛИ ЗРЯ</div>'
        '<div class="b">Одна пара. Один аргумент в комментариях.</div></div></div>'
    )
    slides.append(frame(7, cta))
    return slides


def main() -> None:
    slides = build()
    if len(slides) != 7:
        raise SystemExit(f"должно быть семь кадров, получено {len(slides)}")
    document = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="deck.css"><link rel="stylesheet" href="worldcup.css"></head><body>'
        + "".join(slides) + "</body></html>"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    for name in ("deck.css", "worldcup.css"):
        shutil.copy(HERE / name, OUT.parent / name)
    marks = document.count('class="mk')
    if marks != 3:
        raise SystemExit(f"пометок должно быть ровно три, а их {marks}")
    print(f"кадров: {len(slides)}")
    print(f"пометок: {marks}")
    print(f"файл: {OUT}")


if __name__ == "__main__":
    main()
