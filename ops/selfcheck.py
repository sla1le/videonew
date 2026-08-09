#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Одна команда на весь репозиторий.

    python3 ops/selfcheck.py

Гоняется перед каждым выпуском. Проверяет веса модели, полноту данных,
форму прайм-записей, айсберги и текст документации на запрещённые обороты.

Файла нет равно проверка пропущена. Код возврата 1 только на реальной поломке.
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPS = 1e-9

bad = []
skipped = []
ok = []


def rel(*parts):
    return os.path.join(ROOT, *parts)


def read_json(path):
    full = rel(path)
    if not os.path.exists(full):
        skipped.append(u'нет файла %s' % path)
        return None
    try:
        return json.load(io.open(full, encoding='utf-8'))
    except ValueError as err:
        bad.append(u'%s не читается как JSON: %s' % (path, err))
        return None


# 1. Веса модели
model = read_json('rating/data/model.json')
if model:
    for pos, weights in sorted(model.get('league_weights', {}).items()):
        total = sum(weights.values())
        if abs(total - 1.0) > EPS:
            bad.append(u'веса позиции %s дают %.4f вместо 1.0' % (pos, total))
        judged = weights.get('T', 0) + weights.get('S', 0) + weights.get('D', 0)
        if judged > 0.5 + EPS:
            bad.append(u'судейская доля %s равна %.2f, потолок 0.5' % (pos, judged))
    season = model.get('season_weights', {})
    if season:
        total = sum(season.values())
        if abs(total - 1.0) > EPS:
            bad.append(u'сезонные веса дают %.4f вместо 1.0' % total)
        if 'L' in season:
            bad.append(u'в сезонных весах появился ЛАЙВ, его там быть не должно')
    ok.append(u'модель: веса сошлись')


# 2. Артисты
def artist_rows(blob):
    if blob is None:
        return []
    if isinstance(blob, list):
        return [r for r in blob if isinstance(r, dict)]
    if isinstance(blob, dict):
        for key in ('artists', 'rows', 'data'):
            node = blob.get(key)
            if isinstance(node, list):
                return [r for r in node if isinstance(r, dict)]
            if isinstance(node, dict):
                return [r for r in node.values() if isinstance(r, dict)]
    return []


artists = artist_rows(read_json('rating/data/artists.json'))
if artists:
    typed = [r for r in artists if 'T' in r]
    if len(typed) * 2 < len(artists):
        skipped.append(u'структура artists.json не распознана, проверка артистов пропущена')
    else:
        for row in artists:
            if not row.get('in_league', True):
                continue
            name = row.get('name') or row.get('key') or '?'
            for stat in ('T', 'S', 'D'):
                if row.get(stat) is None:
                    bad.append(u'%s: нет судейского балла %s' % (name, stat))
            for src in ('src_top5', 'src_live', 'src_scene'):
                if not row.get(src):
                    bad.append(u'%s: нет источника %s' % (name, src))
        ok.append(u'артисты: %d записей проверено' % len(artists))


# 3. Прайм-записи
primes = read_json('rating/data/primes.json')
if primes:
    entries = primes.get('primes') if isinstance(primes, dict) else primes
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        skipped.append(u'структура primes.json не распознана')
        entries = []
    snapshot_year = None
    art_blob = read_json('rating/data/artists.json')
    if isinstance(art_blob, dict) and art_blob.get('snapshot'):
        snapshot_year = int(str(art_blob['snapshot'])[:4])
    for entry in entries:
        name = entry.get('name', '?')
        judge = entry.get('judge') or {}
        for stat in ('T', 'S', 'D'):
            if judge.get(stat) is None:
                bad.append(u'прайм %s: нет судейского балла %s за прайм-год' % (name, stat))
        if not entry.get('year'):
            bad.append(u'прайм %s: не указан год' % name)
        elif snapshot_year and int(entry['year']) >= snapshot_year:
            bad.append(u'прайм %s: год %s совпадает со снимком лиги или позже него' % (name, entry['year']))
        if 'L' in judge:
            bad.append(u'прайм %s: ЛАЙВЫ в прайм-карте не считаются' % name)
        # Дочартовая эпоха: пика в чарте может не существовать. Тогда в записи
        # обязательно стоит причина, и движок считает ХИТЫ как вне списка.
        peak = entry.get('peak') or {}
        if peak.get('position') is None:
            if peak.get('absent_reason'):
                skipped.append(u'прайм %s: чарта за тот год нет, ХИТЫ идут как вне списка' % name)
            else:
                bad.append(u'прайм %s: нет пикового места в чарте и нет причины его отсутствия' % name)
        # Сегодняшний балл нужен только тем, кто есть в снимке лиги.
        if entry.get('now_ovr') is None:
            skipped.append(u'прайм %s: в лиге его нет, на карте дельты не будет' % name)
    if entries:
        ok.append(u'праймы: %d карт проверено' % len(entries))


# 4. Айсберги
ICE_TYPES = ('release', 'unreleased', 'leak', 'snippet', 'demo', 'feature')
ice_dir = rel('iceberg', 'data')
if os.path.isdir(ice_dir):
    for fname in sorted(os.listdir(ice_dir)):
        if not fname.endswith('.json'):
            continue
        blob = read_json(os.path.join('iceberg', 'data', fname))
        if not blob:
            continue
        items = blob.get('items') or []
        artist = blob.get('artist', fname)
        for item in items:
            if item.get('type') not in ICE_TYPES:
                bad.append(u'айсберг %s: тип «%s» вне списка' % (artist, item.get('type')))
            level = item.get('level')
            if not isinstance(level, int) or not 1 <= level <= 5:
                bad.append(u'айсберг %s: уровень «%s» вне диапазона 1..5' % (artist, level))
        if blob.get('status') == 'ready' and len(items) < 10:
            bad.append(u'айсберг %s помечен ready, а позиций только %d' % (artist, len(items)))
        if items:
            depth = sum(i.get('level', 0) for i in items) / float(len(items))
            ok.append(u'айсберг %s: %d позиций, глубина %.1f' % (artist, len(items), depth))


# 5. Текст
# Файлы ниже сами описывают запрещённые обороты, поэтому линтер их не читает.
SKIP_TEXT = {
    'prompts/style-rules.md',
    'formats/card-spec.md',
    'formats/iceberg.md',
    'ops/mistakes.md',
    'CHANGELOG.md',
}
DASH = chr(8212)
EMOJI = re.compile(u'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]')
PATTERNS = [
    (re.compile(u', а не '), u'оборот «X, а не Y»'),
    (re.compile(u'не [^.,!?\n]{2,40}, а '), u'оборот «не X, а Y»'),
    (re.compile(u'не просто'), u'оборот «не просто»'),
    (re.compile(u'ИСТОЧНИК'), u'служебная строка ИСТОЧНИК'),
    (re.compile(u'ПОДТВЕРЖДЕНО'), u'штамп ПОДТВЕРЖДЕНО'),
]
checked = 0
for folder, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'out', '__pycache__')]
    for fname in files:
        if not fname.endswith('.md'):
            continue
        path = os.path.relpath(os.path.join(folder, fname), ROOT).replace(os.sep, '/')
        if path in SKIP_TEXT:
            continue
        text = io.open(os.path.join(folder, fname), encoding='utf-8').read()
        checked += 1
        if DASH in text:
            bad.append(u'%s: длинное тире, %d штук' % (path, text.count(DASH)))
        found = EMOJI.findall(text)
        if found:
            bad.append(u'%s: эмодзи %s' % (path, u' '.join(sorted(set(found)))))
        for rx, label in PATTERNS:
            hits = rx.findall(text)
            if hits:
                bad.append(u'%s: %s, %d штук' % (path, label, len(hits)))
ok.append(u'текст: %d файлов проверено' % checked)


for line in ok:
    print(u'  ok    %s' % line)
for line in skipped:
    print(u'  мимо  %s' % line)
for line in bad:
    print(u'  стоп  %s' % line)

print('')
if bad:
    print(u'Найдено проблем: %d' % len(bad))
    sys.exit(1)
print(u'Чисто.')
