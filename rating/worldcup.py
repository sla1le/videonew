#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""КУБОК АЛЬБОМОВ v4.0.

    python3 worldcup.py table
    python3 worldcup.py seed
    python3 worldcup.py r16 --json
    python3 worldcup.py bracket

Пул берётся из data/albums.json. Половина балла судейская, половина считается
из опубликованных списков. Сетка детерминированная: посев по баллу, пары
составляются схемой первый против последнего.

Альбом без единой записи в списках в пул не попадает. Пустая позиция лучше
выдуманного числа.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import core

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROUND_NAMES = {32: "1/16", 16: "1/8", 8: "1/4", 4: "1/2", 2: "ФИНАЛ"}


def load() -> dict:
    path = DATA / "albums.json"
    if not path.exists():
        raise core.DataError("нет файла data/albums.json")
    return json.loads(path.read_text(encoding="utf-8"))


def canon(album: dict, lists: dict) -> float:
    """Сумма кредитов по всем опубликованным спискам."""
    total = 0.0
    for key, value in (album.get("lists") or {}).items():
        meta = lists.get(key)
        if meta is None:
            raise core.DataError(f"{album['key']}: неизвестный список {key}")
        if meta["ranked"]:
            place = int(value)
            size = int(meta["size"])
            if not 1 <= place <= size:
                raise core.DataError(f"{album['key']}: место {place} вне списка {key}")
            total += (size + 1 - place) / size
        elif value:
            total += 1.0
    return total


def influence(value: float, model: dict) -> float:
    if value <= 0:
        return float(model["influence_outside"])
    base = float(model["influence_base"])
    step = float(model["influence_step"])
    anchor = float(model["influence_anchor"])
    return core.clamp(base + step * math.log2(value / anchor))


def score(album: dict, lists: dict, model: dict) -> dict:
    for key in ("T", "S", "D"):
        mark = album.get(key)
        if mark is None or not 30 <= int(mark) <= 99:
            raise core.DataError(f"{album['key']}: судейский балл {key} вне шкалы 30..99")
    if not album.get("src"):
        raise core.DataError(f"{album['key']}: нет ни одного источника")
    if not (album.get("lists") or {}):
        raise core.DataError(f"{album['key']}: нет ни одной записи в опубликованных списках")
    weights = model["weights"]
    canon_value = canon(album, lists)
    infl = influence(canon_value, model)
    raw = (
        weights["T"] * album["T"]
        + weights["S"] * album["S"]
        + weights["D"] * album["D"]
        + weights["I"] * infl
    )
    return {
        "key": album["key"],
        "artist": album["artist"],
        "title": album["title"],
        "year": album["year"],
        "T": album["T"],
        "S": album["S"],
        "D": album["D"],
        "canon": round(canon_value, 4),
        "I": round(infl, 2),
        "raw": round(raw, 2),
        "ovr": core.rnd(raw),
        "lists": album.get("lists") or {},
        "accuracy": album.get("accuracy", "B"),
        "note": album.get("note"),
    }


def table() -> dict:
    payload = load()
    model = payload["model"]
    weight_sum = sum(model["weights"].values())
    if abs(weight_sum - 1.0) > core.EPS:
        raise core.DataError(f"веса не дают единицу: {weight_sum}")
    jury = model["weights"]["T"] + model["weights"]["S"] + model["weights"]["D"]
    if jury > 0.5 + core.EPS:
        raise core.DataError(f"судейская часть {jury} больше половины")
    lists = {item["key"]: item for item in payload["lists"]}
    rows = [score(album, lists, model) for album in payload["albums"]]
    seen: dict[str, str] = {}
    for row in rows:
        if row["artist"] in seen:
            raise core.DataError(
                f"два альбома одного артиста: {seen[row['artist']]} и {row['key']}"
            )
        seen[row["artist"]] = row["key"]
        if row["year"] < payload["window"]["from"]:
            raise core.DataError(f"{row['key']}: год {row['year']} вне окна кубка")
    rows.sort(key=lambda r: (-r["raw"], -r["I"], r["year"], r["artist"]))
    for index, row in enumerate(rows, start=1):
        row["seed"] = index
    return {
        "format": "КУБОК АЛЬБОМОВ",
        "snapshot": payload["snapshot"],
        "formula": model["_formula_score"],
        "lists": [
            {"short": item["short"], "name": item["name"], "size": item["size"], "ranked": item["ranked"]}
            for item in payload["lists"]
        ],
        "rows": rows,
    }


def better(left: dict, right: dict) -> dict:
    """Тайбрейк: балл, затем влияние, затем более ранний год, затем имя."""
    order = (
        (-left["raw"], -left["I"], left["year"], left["artist"]),
        (-right["raw"], -right["I"], right["year"], right["artist"]),
    )
    return left if order[0] <= order[1] else right


def reason(win: dict, lose: dict) -> str:
    if win["ovr"] != lose["ovr"]:
        return "балл"
    if abs(win["raw"] - lose["raw"]) > 0.005:
        return "сотые балла"
    if abs(win["I"] - lose["I"]) > 0.005:
        return "влияние"
    return "более ранний год"


def pair_up(rows: list[dict]) -> list[dict]:
    size = len(rows)
    name = ROUND_NAMES.get(size, f"раунд на {size}")
    matches = []
    for index in range(size // 2):
        left, right = rows[index], rows[size - 1 - index]
        win = better(left, right)
        lose = right if win is left else left
        matches.append(
            {
                "round": name,
                "match": index + 1,
                "top": left,
                "bottom": right,
                "winner": win["key"],
                "margin": round(abs(left["raw"] - right["raw"]), 2),
                "decided_by": reason(win, lose),
            }
        )
    return matches


def round_of(size: int = 32) -> dict:
    data = table()
    rows = data["rows"]
    if size > len(rows):
        return {
            "format": "КУБОК АЛЬБОМОВ",
            "ready": False,
            "blocked_by": [f"в пуле {len(rows)} альбомов, для раунда нужно {size}"],
            "matches": [],
        }
    current = rows[:size]
    return {
        "format": "КУБОК АЛЬБОМОВ",
        "ready": True,
        "round": ROUND_NAMES.get(size, str(size)),
        "snapshot": data["snapshot"],
        "formula": data["formula"],
        "matches": pair_up(current),
    }


def bracket() -> dict:
    data = table()
    rows = data["rows"]
    payload = load()
    size = int(payload["model"]["bracket_size"])
    if len(rows) < size:
        return {
            "format": "КУБОК АЛЬБОМОВ",
            "ready": False,
            "blocked_by": [f"в пуле {len(rows)} альбомов из {size}"],
            "rounds": [],
        }
    by_key = {row["key"]: row for row in rows}
    current = rows[:size]
    rounds = []
    while len(current) > 1:
        matches = pair_up(current)
        rounds.append({"round": matches[0]["round"], "matches": matches})
        current = [by_key[m["winner"]] for m in matches]
    return {
        "format": "КУБОК АЛЬБОМОВ",
        "ready": True,
        "snapshot": data["snapshot"],
        "formula": data["formula"],
        "rounds": rounds,
        "champion": current[0],
    }


def _short(row: dict) -> str:
    return f"{row['artist']} {row['title']}"[:44]


def print_table(data: dict) -> None:
    print(f"КУБОК АЛЬБОМОВ  снимок {data['snapshot']}")
    print(data["formula"])
    print()
    print(f"{'ПОС':<4} {'АЛЬБОМ':<46} {'ГОД':<5} {'ВЛИЯН':<6} {'БАЛЛ':<5} {'ОЦ':<3} ТОЧН")
    for row in data["rows"]:
        print(
            f"{row['seed']:<4} {_short(row):<46} {row['year']:<5} "
            f"{row['I']:<6.2f} {row['raw']:<5.2f} {row['ovr']:<3} {row['accuracy']}"
        )


def print_round(data: dict) -> None:
    if not data.get("ready"):
        print("РАУНД ЗАБЛОКИРОВАН")
        for item in data["blocked_by"]:
            print(f"  {item}")
        return
    print(f"КУБОК АЛЬБОМОВ  {data['round']}  снимок {data['snapshot']}")
    print()
    for match in data["matches"]:
        top, bottom = match["top"], match["bottom"]
        win = match["winner"]
        for row in (top, bottom):
            flag = "->" if row["key"] == win else "  "
            print(f"  {flag} {row['seed']:>2}  {_short(row):<46} {row['ovr']:>3}")
        print(f"     матч {match['match']:>2}  разрыв {match['margin']:.2f}  решил {match['decided_by']}")
        print()


def print_bracket(data: dict) -> None:
    if not data.get("ready"):
        print("СЕТКА ЗАБЛОКИРОВАНА")
        for item in data["blocked_by"]:
            print(f"  {item}")
        return
    for stage in data["rounds"]:
        print(f"== {stage['round']}")
        for match in stage["matches"]:
            top, bottom = match["top"], match["bottom"]
            winner = top if top["key"] == match["winner"] else bottom
            print(
                f"  {_short(top):<40} {top['ovr']:>3}   {_short(bottom):<40} {bottom['ovr']:>3}"
                f"   -> {winner['artist']}"
            )
        print()
    champ = data["champion"]
    print(f"ЧЕМПИОН: {champ['artist']} {champ['title']} ({champ['year']}) {champ['ovr']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="КУБОК АЛЬБОМОВ")
    parser.add_argument("command", choices=["table", "seed", "r16", "r8", "bracket"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command in ("table", "seed"):
        data = table()
        printer = print_table
    elif args.command == "r16":
        data = round_of(32)
        printer = print_round
    elif args.command == "r8":
        data = round_of(16)
        printer = print_round
    else:
        data = bracket()
        printer = print_bracket

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        printer(data)


if __name__ == "__main__":
    main()
