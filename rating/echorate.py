#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Лига ECHORATE v4.0.

    python3 echorate.py                 таблица лиги
    python3 echorate.py --artist kai    карточка одного артиста
    python3 echorate.py --check         проверка данных перед выпуском
    python3 echorate.py --json          машинный вывод для генераторов
    python3 echorate.py --write         обновить data/league.json

Математика живёт только в core.py, данные только в data/artists.json.
До v4.0 те же цифры лежали в двух местах и успели разойтись.
"""
from __future__ import annotations

import argparse
import json
import sys

import core


def bar(value: int, width: int = 28) -> str:
    filled = int(round((value - 30) / 69 * width))
    return "#" * max(0, min(width, filled))


def print_table(result: dict) -> None:
    print(f"ECHORATE v{result['version']}   снимок {result['snapshot']}   округление {result['rounding']}")
    print("-" * 96)
    head = f"{'#':>2} {'АРТИСТ':<13} {'ПОЗ':<5}"
    for key in core.STAT_ORDER:
        head += f" {core.STAT_LABELS[key][:4]:>5}"
    head += f" {'RAW':>7} {'OVR':>4} {'ПОТ':>4} {'ЦЕНА':>6} {'ТОЧ':>3}"
    print(head)
    print("-" * 96)
    for row in result["rows"]:
        line = f"{row['rank']:>2} {row['name']:<13} {row['pos']:<5}"
        for key in core.STAT_ORDER:
            line += f" {row['stats'][key]:>5}"
        line += f" {row['raw']:>7.2f} {row['ovr']:>4} {row['potential']:>4} {row['price_mln']:>6} {row['accuracy']:>3}"
        print(line)
    print("-" * 96)
    for row in result["rows"]:
        if row["was"] and row["was"] != row["ovr"]:
            print(f"  БЫЛО {row['was']}, СТАЛО {row['ovr']}: {row['name']}. Старый балл зачёркивается на кадре.")
    for row in result["rows"]:
        if row["accuracy"] == "C":
            print(f"  ТОЧНОСТЬ C: {row['name']}. На кадре нужна пометка об оценке.")
    for item in result["skipped"]:
        print(f"  ПРОПУЩЕН {item['name']}: {item['reason']}")


def print_card(row: dict) -> None:
    print(f"{row['name']}   {row['pos']} {core.POSITION_LABELS.get(row['pos'], '')}")
    print(f"OVR {row['ovr']}   ПОТЕНЦИАЛ {row['potential']}   ЦЕНА {row['price_mln']} млн")
    if row["was"] and row["was"] != row["ovr"]:
        print(f"БЫЛО {row['was']}")
    print("-" * 52)
    for key in core.STAT_ORDER:
        value = row["stats"][key]
        print(f"  {core.STAT_LABELS[key]:<9} {value:>3}  {bar(value)}")
    print("-" * 52)
    for name, text in row["sources"].items():
        print(f"  {name}: {text['description']}")
        print(f"    URL: {text['url'] or 'не внесён'}; снимок: {text['captured_at'] or 'не указан'}")
        if text["archive_url"]:
            print(f"    Архив: {text['archive_url']}")


def check() -> int:
    """Ловит то, что раньше ловилось глазами или не ловилось вовсе."""
    payload, artists = core.load_artists()
    snapshot = payload["snapshot"]
    errors: list[str] = []
    warnings: list[str] = []

    for artist in artists:
        who = artist["name"]
        if not artist.get("in_league"):
            if not artist.get("needs"):
                warnings.append(f"{who}: резерв без списка недостающих полей")
            continue
        try:
            row = core.rate(artist, snapshot)
        except core.DataError as err:
            errors.append(str(err))
            continue
        if artist.get("born"):
            computed = core.age_at(artist["born"], snapshot)
            if artist.get("age") is not None and artist["age"] != computed:
                errors.append(f"{who}: возраст {artist['age']} в файле, но по дате рождения {computed}")
        else:
            warnings.append(f"{who}: нет даты рождения, возраст забит руками и устареет")
        total = artist.get("spotify_total")
        if total and artist.get("catalog"):
            drift = abs(artist["catalog"] - total) / total
            if drift > 0.15:
                warnings.append(
                    f"{who}: catalog {artist['catalog']:,} расходится с Spotify {total:,} на {drift:.0%}"
                )
        if row["accuracy"] not in ("A", "B", "C"):
            errors.append(f"{who}: точность {row['accuracy']} вне шкалы")
        for issue in artist.get("open_issues", []):
            warnings.append(f"{who}: {issue}")
        for key in core.REQUIRED_SOURCES:
            source = artist[key]
            if source["status"] == "needs_url":
                warnings.append(f"{who}: {key} описан, но URL ещё не внесён")
            elif source["status"] == "editorial":
                warnings.append(f"{who}: {key} является авторской оценкой")

    print(f"проверено артистов: {len(artists)}")
    for text in warnings:
        print(f"  ПРЕДУПРЕЖДЕНИЕ: {text}")
    for text in errors:
        print(f"  ОШИБКА: {text}")
    print(f"итог: {'ошибок нет' if not errors else str(len(errors)) + ' ошибок'}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Лига ECHORATE")
    parser.add_argument("--artist", help="ключ артиста, например kai")
    parser.add_argument("--json", action="store_true", help="машинный вывод")
    parser.add_argument("--check", action="store_true", help="проверка данных")
    parser.add_argument("--write", action="store_true", help="обновить data/league.json")
    args = parser.parse_args(argv)

    if args.check:
        return check()

    result = core.league()

    if args.artist:
        found = [r for r in result["rows"] if r["key"] == args.artist or r["name"] == args.artist.upper()]
        if not found:
            keys = ", ".join(r["key"] for r in result["rows"])
            print(f"нет такого артиста. Есть: {keys}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(found[0], ensure_ascii=False, indent=2))
        else:
            print_card(found[0])
        return 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_table(result)

    if args.write:
        path = core.DATA / "league.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"записано {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
