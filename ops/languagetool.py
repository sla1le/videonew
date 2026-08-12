#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Опциональная проверка русского текста через локальный LanguageTool.

По умолчанию ищет сервер на http://127.0.0.1:8081. Адрес меняется переменной
LANGUAGETOOL_URL. Сборку этот слой не блокирует, пока не передан --required.

Примеры:
    python3 ops/languagetool.py build/decks
    LANGUAGETOOL_URL=http://127.0.0.1:8081 python3 ops/languagetool.py build/decks
    python3 ops/languagetool.py build/decks/foo.desc.txt --required
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from slop import collect, text_of


def endpoint():
    base = os.environ.get("LANGUAGETOOL_URL", "http://127.0.0.1:8081").rstrip("/")
    return base + "/v2/check"


def check_text(text):
    payload = urllib.parse.urlencode({
        "language": "ru-RU",
        "text": text,
        "enabledOnly": "false",
    }).encode("utf-8")
    req = urllib.request.Request(endpoint(), data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def sample(text, offset, length, radius=42):
    left = max(0, int(offset) - radius)
    right = min(len(text), int(offset) + int(length) + radius)
    return " ".join(text[left:right].split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="*", default=["build/decks"])
    parser.add_argument("--required", action="store_true")
    parser.add_argument("--max", type=int, default=30, help="максимум замечаний на файл в выводе")
    args = parser.parse_args()

    files = collect(args.targets)
    if not files:
        print("Нечего проверять.")
        return 0

    try:
        check_text("Проверка связи.")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        print("  мимо  LanguageTool недоступен: %s" % err)
        print("         адрес: %s" % endpoint())
        return 1 if args.required else 0

    total = 0
    for path in files:
        try:
            text = text_of(path)
            data = check_text(text)
        except (ValueError, OSError, urllib.error.URLError) as err:
            print("  стоп  %s: %s" % (path, err))
            return 1 if args.required else 0

        matches = data.get("matches") or []
        total += len(matches)
        if not matches:
            print("  ok    %s" % path)
            continue
        print("  язык  %s: %d замечаний" % (path, len(matches)))
        for hit in matches[:args.max]:
            rule = (hit.get("rule") or {}).get("id", "?")
            message = hit.get("message", "")
            context = sample(text, hit.get("offset", 0), hit.get("length", 0))
            print("         %s: %s | %s" % (rule, message, context))

    print("")
    print("LanguageTool: %d замечаний. Это редакционный слой, автоматических правок нет." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
