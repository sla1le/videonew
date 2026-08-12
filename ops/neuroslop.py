#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Структурный скорер машинного текста для ECHORATE.

Он дополняет ops/slop.py. slop.py ловит точные запрещённые фразы,
neuroslop.py ищет более общий почерк: шаблонные контрасты, ровный ритм,
повтор тезиса, избыток двоеточий и абстрактные финалы.

Примеры:
    python3 ops/neuroslop.py build/decks
    python3 ops/neuroslop.py build/decks/foo.json --max-score 55
    python3 ops/neuroslop.py --self-test

Скор не является AI-детектором. Это редакционный сигнал от 0 до 100.
В сборке блокируется только высокий скор, а найденные фрагменты переписываются
вручную или агентом точечно.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import statistics
import sys

SKIP_KEYS = {
    "prefix", "img", "mos", "imgs", "t", "type", "foot", "skin",
    "src", "href", "url", "cr",
}

PHRASES = [
    ("в современном мире", 35),
    ("на сегодняшний день", 25),
    ("стоит отметить", 25),
    ("важно отметить", 25),
    ("важно понимать", 22),
    ("следует понимать", 22),
    ("необходимо помнить", 22),
    ("на первый взгляд", 14),
    ("в конечном счёте", 14),
    ("в конечном счете", 14),
    ("ключевой момент", 12),
    ("главный вопрос", 8),
    ("говорит само за себя", 18),
    ("говорят сами за себя", 18),
    ("культурный код", 12),
    ("культурный феномен", 16),
    ("настоящий культурный феномен", 18),
    ("не просто", 20),
    ("подводя итог", 24),
    ("в заключение", 20),
    ("играет ключевую роль", 20),
]

PATTERNS = [
    (re.compile(r"\bэто не [^.!?\n]{2,60},\s*это\b", re.I), 22,
     "контрастная формула"),
    (re.compile(r"\bне [^.!?\n]{2,50},\s*а\b", re.I), 22,
     "контрастная формула"),
    (re.compile(r"\bне только [^.!?\n]{2,60},\s*но и\b", re.I), 20,
     "парная формула"),
    (re.compile(r"\bэто (?:гораздо )?больше,?\s+чем\b", re.I), 18,
     "формула больше чем"),
]

ABSTRACT_WORDS = {
    "эпоха", "феномен", "заявление", "манифест", "революционный",
    "революционная", "революционное", "инновационный", "инновационная",
    "инновационное",
}

STOPWORDS = set(
    "и в во на с со у к ко по из от до за для что это как но а же уже был "
    "была были есть его её ее их он она они мы я ты вы этот эта эти того том "
    "там тут при или если то который которая которые".split()
)


def strings_from(node, out):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SKIP_KEYS:
                continue
            strings_from(value, out)
    elif isinstance(node, list):
        for value in node:
            strings_from(value, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def text_of(path):
    if path.endswith(".json"):
        blob = json.load(io.open(path, encoding="utf-8"))
        return "\n".join(strings_from(blob, []))
    return io.open(path, encoding="utf-8").read()


def collect(targets):
    files = []
    for target in targets:
        if os.path.isdir(target):
            for root, _, names in os.walk(target):
                for name in sorted(names):
                    if name.endswith(".json") or name.endswith(".desc.txt"):
                        files.append(os.path.join(root, name))
        elif os.path.isfile(target):
            files.append(target)
        else:
            print("  мимо  нет файла %s" % target)
    return sorted(set(files))


def words(text):
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text.lower())


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def excerpt(text, needle, width=84):
    low = text.lower()
    idx = low.find(needle.lower())
    if idx < 0:
        return needle
    left = max(0, idx - width // 2)
    right = min(len(text), idx + len(needle) + width // 2)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def score_text(text):
    low = text.lower()
    score = 0
    issues = []

    for phrase, weight in PHRASES:
        count = low.count(phrase)
        if count:
            points = min(40, weight * count)
            score += points
            issues.append((points, phrase, excerpt(text, phrase)))

    for rx, weight, label in PATTERNS:
        matches = list(rx.finditer(text))
        if matches:
            points = min(40, weight * len(matches))
            score += points
            issues.append((points, label, re.sub(r"\s+", " ", matches[0].group(0))))

    ss = sentences(text)
    lengths = [len(words(s)) for s in ss if words(s)]
    if len(lengths) >= 4:
        mean = sum(lengths) / float(len(lengths))
        if mean >= 6:
            cv = statistics.pstdev(lengths) / mean if mean else 1.0
            if cv < 0.18:
                score += 12
                issues.append((12, "ровная длина предложений", "cv %.2f" % cv))
            elif cv < 0.25:
                score += 6
                issues.append((6, "слишком ровный ритм", "cv %.2f" % cv))

    starts = []
    for sentence in ss:
        ws = words(sentence)
        starts.append(" ".join(ws[:2]) if ws else "")
    for i in range(max(0, len(starts) - 2)):
        if starts[i] and starts[i] == starts[i + 1] == starts[i + 2]:
            score += 12
            issues.append((12, "три одинаковых начала", starts[i]))
            break

    for first, second in zip(ss, ss[1:]):
        a = {w for w in words(first) if len(w) > 3 and w not in STOPWORDS}
        b = {w for w in words(second) if len(w) > 3 and w not in STOPWORDS}
        if min(len(a), len(b)) < 4:
            continue
        overlap = len(a & b) / float(len(a | b))
        if overlap >= 0.55:
            score += 10
            issues.append((10, "соседние предложения повторяют тезис", "overlap %.2f" % overlap))
            break

    wc = max(1, len(words(text)))
    colons = text.count(":")
    if wc >= 20 and colons >= 3:
        per100 = colons * 100.0 / wc
        if per100 >= 5:
            score += 10
            issues.append((10, "слишком много двоеточий", "%.1f на 100 слов" % per100))
        elif per100 >= 3:
            score += 5
            issues.append((5, "много двоеточий", "%.1f на 100 слов" % per100))

    for sentence in ss:
        ws = set(words(sentence))
        found = sorted(ws & ABSTRACT_WORDS)
        if found and not re.search(r"\d", sentence) and len(words(sentence)) >= 7:
            score += 4
            issues.append((4, "абстракция без конкретной опоры", ", ".join(found)))
            break

    if ss:
        last = ss[-1].lower()
        if (any(x in last for x in ("эпоха", "феномен", "культурный код", "манифест", "заявление"))
                and not re.search(r"\d", last)):
            score += 8
            issues.append((8, "абстрактный финал", re.sub(r"\s+", " ", ss[-1])[:120]))

    issues.sort(key=lambda row: -row[0])
    return min(100, score), issues


def self_test():
    slop = (
        "Этот альбом — не просто релиз, а настоящий культурный феномен, "
        "который во многом определил звучание целого поколения."
    )
    clean = (
        "В 2017-м FACE был уже не интернет-мемом: тур на 20 городов и "
        "несколько больших хитов вынесли его в мейнстрим."
    )
    a, _ = score_text(slop)
    b, _ = score_text(clean)
    print("  тест  slop=%d clean=%d" % (a, b))
    if a < 70 or b > 20:
        print("ПРОВАЛ: скорер потерял разделение контрольных примеров")
        return 1
    print("  ok    контрольные примеры разделены")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*", default=["build/decks"])
    parser.add_argument("--max-score", type=int, default=65)
    parser.add_argument("--warn-score", type=int, default=25)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test and not args.targets:
        return self_test()
    if args.self_test:
        failed = self_test()
        if failed:
            return failed

    files = collect(args.targets)
    if not files:
        print("Нечего проверять.")
        return 0

    bad = []
    for path in files:
        try:
            text = text_of(path)
        except (OSError, ValueError) as err:
            bad.append((path, 100, [(100, "файл не читается", str(err))]))
            continue
        score, issues = score_text(text)
        tag = "стоп" if score > args.max_score else ("мягко" if score >= args.warn_score else "ok")
        print("  %-5s %3d  %s" % (tag, score, path))
        if score >= args.warn_score:
            for points, label, sample in issues[:5]:
                print("         +%-2d %s: %s" % (points, label, sample))
        if score > args.max_score:
            bad.append((path, score, issues))

    print("")
    if bad:
        print("Высокий neuroslop_score у файлов: %d. Потолок %d." % (len(bad), args.max_score))
        return 1
    print("Структурный антислоп пройден. Потолок %d." % args.max_score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
