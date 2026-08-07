#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Дека кубка альбомов, раунд 1/16. Восемнадцать кадров.

    python3 build/gen_worldcup.py

Тексты лежат в COPY и привязаны к ключу победителя. Если движок пересчитает
посев и пара поменяется, генератор упадёт с понятной ошибкой, а не выпустит
кадр с чужим текстом. Заголовок до шести слов, тело до двадцати.
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

COPY = {
    "skryptonite_dsny": (
        "САМЫЙ ЖЕСТОКИЙ МАТЧ СЕТКИ",
        "Первый номер посева против последнего. Афиша поставила Децла на 98 место.",
    ),
    "lsp_tragiccity": (
        "У ЛСП ДВА СПИСКА ИЗ ДВУХ",
        "Афиша и The Flow взяли его оба. У МакSим одна запись в конце сотни.",
    ),
    "atl_marabu": (
        "МАРАБУ ПРОХОДИТ БЕЗ ВОПРОСОВ",
        "Марабу есть и у Афиши, и у The Flow. Фобос только у Афиши.",
    ),
    "husky_lubimye": (
        "ЛУЧШИЕ СЛОВА ВО ВСЕЙ СЕТКЕ",
        "Хаски набрал за слова 94 балла. У Сказки сильная музыка и тонкий канон.",
    ),
    "oxxxymiron_gorgorod": (
        "ГОРГОРОДА НЕТ В СОТНЕ АФИШИ",
        "Перечитаны все сто мест. Горгород держится на одной записи The Flow.",
    ),
    "zemfira_pmml": (
        "ЕДИНСТВЕННАЯ ЖЕНЩИНА В ВЕРХНЕЙ ПОЛОВИНЕ",
        "Полтора миллиона проданных копий. Место 22 у Афиши.",
    ),
    "2517_podorozhnik": (
        "ПОДОРОЖНИК ВЫБИВАЕТ ГОРОД ДОРОГ",
        "К каждой песне альбома снят клип. The Flow взял его в двадцатку.",
    ),
    "pharaoh_pinkphloyd": (
        "ФАРАОНА АФИША НЕ ЗАМЕТИЛА ВООБЩЕ",
        "Ни одной строки в сотне. Одна запись The Flow вытягивает его дальше.",
    ),
    "depo_oldblood": (
        "САМЫЙ СВЕЖИЙ АЛЬБОМ СЕТКИ",
        "Old Blood вышел в 2020 году. Позже в списки не попал уже никто.",
    ),
    "nrktk_planeta": (
        "АЛЬБОМ, КОТОРЫЙ ВСЕ ЗАБЫЛИ",
        "Планета Любовь стоит у Афиши выше Горгорода и выше Марабу.",
    ),
    "tatu_200": (
        "ПОП ВЫБИВАЕТ РЭП",
        "200 по встречной стоит у Афиши выше любого рэпа в этой сетке.",
    ),
    "ptitsuem_dzom": (
        "ДВА САМЫХ НЕУДОБНЫХ АЛЬБОМА",
        "Девятнадцатое место против сорок шестого. Обоих в эфире не крутили.",
    ),
    "kaspiy_storona": (
        "ПРЕДПОСЛЕДНЯЯ СТРОКА ПРОХОДИТ ДАЛЬШЕ",
        "Афиша дала предпоследнюю строку, The Flow взял в двадцатку. Два списка бьют один.",
    ),
    "triagrutrika_vecher": (
        "ЧЕЛЯБИНСК ПРОТИВ ДЕЛЬФИНА",
        "Разрыв меньше балла. Год Вечернего Челябинска в источниках спорный и помечен.",
    ),
    "dorn_randorn": (
        "ОДИНАКОВЫЕ ОЦЕНКИ, РАЗНЫЕ СОТЫЕ",
        "Дорн стоит у Афиши на десятом месте, Дачники на двадцать шестом.",
    ),
    "kasta_gvvt": (
        "САМЫЙ БЛИЗКИЙ МАТЧ РАУНДА",
        "Разрыв 0.13 балла. Слова Касты против продакшна Грибов.",
    ),
}

CIRCLE_ON = "oxxxymiron_gorgorod"
CIRCLE_WORDS = "НЕТ В СОТНЕ"
UNDER_ON = "kasta_gvvt"
UNDER_WORD = "БЛИЗКИЙ"


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


def frame(number: int, body: str) -> str:
    return (
        f'<section class="s" data-name="{number:02d}">'
        f'{body}<div class="pg">@ECHORATE</div></section>'
    )


def side(row: dict, winner: bool) -> str:
    css = "a w" if winner else "a l"
    return (
        f'<div class="{css}">'
        f'<div class="i"><div class="ar">{esc(row["artist"])}</div>'
        f'<div class="tt">{esc(row["title"])}, {row["year"]}</div></div>'
        f'<div class="v">{row["ovr"]}</div>'
        "</div>"
    )


def build() -> list[str]:
    data = worldcup.round_of(32)
    if not data.get("ready"):
        raise SystemExit(f"раунд заблокирован: {data['blocked_by']}")
    matches = data["matches"]
    if len(matches) != 16:
        raise SystemExit(f"в раунде {len(matches)} матчей вместо 16")

    slides = []

    cover = (
        head("КУБОК АЛЬБОМОВ", wrap("32 АЛЬБОМА", UNDER) + " С 2000 ГОДА")
        + '<div class="bd">'
        '<div class="frm"><div class="l">Русский язык, паспорт не важен. '
        'От каждого артиста <b>ровно один альбом</b>, самый высокий по баллу.</div></div>'
        '<div class="note">Сегодня только первый раунд. Половина вылетит сразу.</div>'
        "</div>"
    )
    slides.append(frame(1, cover))

    method = (
        head("КАК СЧИТАЛОСЬ", "ПОЛОВИНА БАЛЛА НЕ МОЯ")
        + '<div class="bd">'
        '<div class="wts">'
        '<div><div class="k">СУДЬЯ</div><div class="v">50%</div></div>'
        '<div><div class="k">СПИСКИ</div><div class="v">50%</div></div>'
        "</div>"
        '<div class="frm"><div class="l">ТЕКСТЫ, ЗВУК и ПОДАЧА мои. '
        '<b>ВЛИЯНИЕ</b> считается из двух опубликованных списков: '
        'сотня Афиши Daily и двадцатка The Flow.</div></div>'
        '<div class="note">Прослушивания не считаются. У альбомов нулевых их просто '
        'нет в открытых чартах.</div>'
        "</div>"
    )
    slides.append(frame(2, method))

    for index, match in enumerate(matches):
        key = match["winner"]
        if key not in COPY:
            raise SystemExit(f"нет текста для победителя {key}")
        title, note = COPY[key]
        if len(title.split()) > 6:
            raise SystemExit(f"заголовок длиннее шести слов: {title}")
        if len(note.split()) > 20:
            raise SystemExit(f"тело длиннее двадцати слов: {note}")

        if key == CIRCLE_ON:
            title_html = mark_word(title, CIRCLE_WORDS, CIRC)
        elif key == UNDER_ON:
            title_html = mark_word(title, UNDER_WORD, UNDER)
        else:
            title_html = esc(title)

        top, bottom = match["top"], match["bottom"]
        cta = ""
        if index == len(matches) - 1:
            cta = (
                '<div class="cta"><div class="a">КОГО ВЫБИЛИ ЗРЯ</div>'
                '<div class="b">Пиши в комменты. Продолжение выйдет завтра.</div></div>'
            )

        body = (
            head("1/16 ФИНАЛА", title_html)
            + '<div class="bd"><div class="duel">'
            + side(top, top["key"] == key)
            + '<div class="vs">ПРОТИВ</div>'
            + side(bottom, bottom["key"] == key)
            + "</div>"
            + f'<div class="note">{esc(note)}</div>'
            + cta
            + "</div>"
        )
        slides.append(frame(index + 3, body))

    return slides


def main() -> None:
    slides = build()
    document = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="deck.css">'
        '<link rel="stylesheet" href="worldcup.css"></head><body>'
        + "".join(slides)
        + "</body></html>"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(document, encoding="utf-8")
    # Стили лежат в build, а разметка в build/html. Без копии браузер их не найдёт
    # и отрендерит кадры схлопнутыми вместо 1080 на 1440.
    for name in ("deck.css", "worldcup.css"):
        source = HERE / name
        if not source.exists():
            raise SystemExit(f"нет файла стилей {source}")
        shutil.copy(source, OUT.parent / name)
    marks = document.count('class="mk')
    print(f"кадров: {len(slides)}")
    print(f"пометок: {marks}")
    print(f"файл: {OUT}")
    if marks != 3:
        raise SystemExit(f"пометок должно быть ровно три, а их {marks}")
    if len(slides) > 20:
        raise SystemExit(f"кадров больше двадцати: {len(slides)}")


if __name__ == "__main__":
    main()
