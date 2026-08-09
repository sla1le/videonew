#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Линтер описания под выпуск.

    python3 ops/desclint.py build/decks/gm2018.desc.txt
    python3 ops/desclint.py build/decks

Правила лежат в ops/description.md. Стоп валит выпуск, внимание только печатается.
Код возврата 1, если есть хотя бы один стоп.
"""

import io
import os
import re
import sys

EMDASH = chr(8212)
ENDASH = chr(8211)
EMOJI = re.compile('[\\U0001F000-\\U0001FAFF\\u2600-\\u26FF\\u2700-\\u27BF]')
TAG = re.compile(r'(?<![\w#])#[^\s#]+')
LINK = re.compile(r'(https?://\S+|t\.me/\S+)')
ALLOWED_TAGS = ('#эхо', '#echorate')
OWN_LINK = 't.me/echorate'

FIRST_LINE_MAX = 90
LINE_SOFT_MAX = 110
SOFT_MIN = 200
SOFT_MAX = 500
HARD_MAX = 700
LINES_MIN = 4
LINES_MAX = 6

BANNED = [
    (re.compile(r', а не '), 'оборот с отрицанием во второй части'),
    (re.compile(r'не [^.,!?\n]{2,40}, а '), 'оборот с отрицанием в первой части'),
    (re.compile(r'не просто'), 'усилитель без содержания'),
    (re.compile(r'ИСТОЧНИК'), 'служебная строка про происхождение цифр'),
    (re.compile(r'ПОДТВЕРЖДЕНО'), 'штамп проверки'),
    (re.compile(r'confidence', re.I), 'метка уверенности'),
    (re.compile(r'(ВЫПУСК|EPISODE|EP)\s*[#N]?\s*\d+'), 'номер выпуска'),
    (re.compile(r'данные могут'), 'оговорка про погрешность'),
    (re.compile(r'может отличат'), 'оговорка про погрешность'),
]

NEXT_HINTS = ('дальше', 'следующ', 'завтра')
PROFILE_HINTS = ('телеграм', 't.me', 'в шапке', 'в профиле', 'в комментариях')


def check(path):
    fails = []
    warns = []
    text = io.open(path, encoding='utf-8').read().strip()
    if not text:
        return ['пустой файл'], warns

    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    body_lines = [ln for ln in lines if not ln.startswith('#')]
    body = '\n'.join(body_lines)
    tags = TAG.findall(text)

    if len(tags) > 1:
        fails.append('хештегов %d, потолок один' % len(tags))
    for tag in tags:
        if tag.lower() not in ALLOWED_TAGS:
            warns.append('тег %s вне списка служебных' % tag)
    if tags and not lines[-1].startswith('#'):
        warns.append('тег стоит внутри текста, его место последней строкой')

    if EMDASH in text:
        fails.append('длинное тире')
    if ENDASH in text:
        fails.append('среднее тире')
    hits = EMOJI.findall(text)
    if hits:
        fails.append('эмодзи %s' % ' '.join(sorted(set(hits))))
    for rx, label in BANNED:
        if rx.search(text):
            fails.append(label)

    if len(body) > HARD_MAX:
        fails.append('знаков %d, потолок %d' % (len(body), HARD_MAX))
    elif len(body) > SOFT_MAX:
        warns.append('знаков %d, цель до %d' % (len(body), SOFT_MAX))
    if len(body) < SOFT_MIN:
        warns.append('знаков %d, цель от %d' % (len(body), SOFT_MIN))

    if body_lines:
        first = body_lines[0]
        if len(first) > FIRST_LINE_MAX:
            fails.append('первая строка %d знаков, потолок %d' % (len(first), FIRST_LINE_MAX))
        if not re.search(r'\d', first):
            warns.append('в первой строке нет цифры')
    for i, ln in enumerate(body_lines):
        if len(ln) > LINE_SOFT_MAX:
            warns.append('строка %d длиной %d знаков' % (i + 1, len(ln)))

    if len(body_lines) > LINES_MAX:
        warns.append('строк %d, рабочий диапазон до %d' % (len(body_lines), LINES_MAX))
    if len(body_lines) < LINES_MIN:
        warns.append('строк %d, рабочий диапазон от %d' % (len(body_lines), LINES_MIN))

    low = body.lower()
    if '?' not in body:
        warns.append('нет вопроса зрителю')
    if not any(h in low for h in NEXT_HINTS):
        warns.append('нет обещания следующего выпуска')
    if not any(h in low for h in PROFILE_HINTS):
        warns.append('нет повода открыть профиль')

    links = LINK.findall(body)
    if len(links) > 1:
        fails.append('ссылок %d, разрешена одна' % len(links))
    for link in links:
        if OWN_LINK not in link:
            warns.append('сторонняя ссылка %s' % link)

    return fails, warns


def collect(paths):
    out = []
    for path in paths:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if name.endswith('.desc.txt'):
                    out.append(os.path.join(path, name))
        else:
            out.append(path)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print('укажи файл описания или папку с файлами .desc.txt')
        return 2
    files = collect(args)
    if not files:
        print('файлов .desc.txt не найдено')
        return 2

    stops = 0
    for path in files:
        print(path)
        if not os.path.exists(path):
            print('  стоп      нет файла')
            stops += 1
            continue
        fails, warns = check(path)
        for line in warns:
            print('  внимание %s' % line)
        for line in fails:
            print('  стоп      %s' % line)
        if not fails and not warns:
            print('  чисто')
        stops += len(fails)

    print('')
    if stops:
        print('ОПИСАНИЕ ПРОВАЛЕНО: %d' % stops)
        return 1
    print('ОПИСАНИЕ ПРОЙДЕНО: файлов %d' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
