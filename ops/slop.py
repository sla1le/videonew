#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Стоп-лист фраз, по которым текст читается как машинный.

    python3 ops/slop.py build/decks
    python3 ops/slop.py build/decks/tm2004.json build/decks/tm2004.desc.txt

Смотрит только то, что видит зритель: тексты дек и описания выпусков.
Документацию линтер не читает: там эти обороты перечислены по делу.

Жёсткий список валит сборку. Мягкий печатается и выпуск не блокирует.

Полный разбор в prompts/style-rules.md, механика площадки в ops/tiktok.md.
Схемы «не X, а Y», длинные тире и эмодзи ловят build/lint.py и ops/selfcheck.py.
"""

import io
import json
import os
import re
import sys

# Фразы, которых в выпуске быть не может. Сборка встаёт.
HARD = [
    u'в современном мире',
    u'на сегодняшний день',
    u'стоит отметить',
    u'важно отметить',
    u'важно понимать',
    u'следует учитывать',
    u'необходимо помнить',
    u'не секрет',
    u'подводя итог',
    u'в заключение',
    u'погрузимся',
    u'играет ключевую роль',
    u'подчёркивает важность',
    u'подчеркивает важность',
    u'неизгладимый след',
    u'поворотный момент',
    u'краеугольный камень',
    u'открывает новые возможности',
    u'революционн',
    u'инновационн',
    u'и знаете что',
    u'хочешь честно',
    u'если откликается',
    u'но есть нюанс',
    u'именно в этом кроется',
    u'успешный успех',
    u'раскрыть потенциал',
    u'может похвастаться',
    u'в самом сердце',
    u'давайте рассмотрим',
    u'перейдём к следующему',
    u'с каждым днём',
]

HARD_RX = [
    (re.compile(u'не только[^.!?\n]{2,60}но и '), u'схема «не только A, но и B»'),
    (re.compile(u'это не [^.!?\n]{2,40}, это '), u'схема «это не X, это Y»'),
]

# Фразы под вопрос. Линтер печатает и идёт дальше.
SOFT = [
    u'таким образом',
    u'самое интересное',
    u'на самом деле',
    u'по сути',
    u'как известно',
    u'разумеется',
    u'безусловно',
    u'разнообразн',
    u'потрясающ',
    u'уникальн',
]


def strings_from(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ('prefix', 'img', 'mos', 'imgs', 't', 'type'):
                continue
            strings_from(value, out)
    elif isinstance(node, list):
        for value in node:
            strings_from(value, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def text_of(path):
    if path.endswith('.json'):
        blob = json.load(io.open(path, encoding='utf-8'))
        return u'\n'.join(strings_from(blob, []))
    return io.open(path, encoding='utf-8').read()


def collect(targets):
    files = []
    for target in targets:
        if os.path.isdir(target):
            for name in sorted(os.listdir(target)):
                if name.endswith('.json') or name.endswith('.desc.txt'):
                    files.append(os.path.join(target, name))
        elif os.path.isfile(target):
            files.append(target)
        else:
            print(u'  мимо  нет файла %s' % target)
    return files


def main():
    targets = sys.argv[1:] or ['build/decks']
    files = collect(targets)
    if not files:
        print(u'Нечего проверять.')
        return 0

    hard_hits = []
    soft_hits = []
    for path in files:
        try:
            text = text_of(path)
        except ValueError as err:
            hard_hits.append(u'%s не читается как JSON: %s' % (path, err))
            continue
        low = text.lower()
        for phrase in HARD:
            if phrase in low:
                hard_hits.append(u'%s: «%s»' % (path, phrase))
        for rx, label in HARD_RX:
            if rx.search(low):
                hard_hits.append(u'%s: %s' % (path, label))
        for phrase in SOFT:
            if phrase in low:
                soft_hits.append(u'%s: «%s»' % (path, phrase))

    print(u'  ok    проверено файлов: %d' % len(files))
    for line in soft_hits:
        print(u'  мягко %s' % line)
    for line in hard_hits:
        print(u'  стоп  %s' % line)

    print('')
    if hard_hits:
        print(u'Фраз из стоп-листа: %d. Разбор в prompts/style-rules.md' % len(hard_hits))
        return 1
    if soft_hits:
        print(u'Жёстких совпадений нет, мягких %d.' % len(soft_hits))
        return 0
    print(u'Чисто.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
