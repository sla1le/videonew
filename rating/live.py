#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЛАЙВЫ, когда концертов нет по внешней причине. Политика v1, модель 4.1.

Зачем это есть. Под дуэлью kizaru против ICEGERGERT комментарий на 447 лайков
говорит: если бы Кизару мог находиться в России, он по концертам рвал бы всех.
Балл ЛАЙВОВ у него посчитан по пустым залам, и зритель прав в том, что это
наказание за обстоятельства, а не за ремесло.

Что делает эта политика. Ось ЛАЙВЫ выбрасывается целиком, её вес раздаётся
остальным пяти осям пропорционально. Никаких скрытых бонусов: причина хранится
в данных, а на кадре обязана стоять строка "Лайвов здесь нет".

    python3 rating/live.py             таблица перераспределённых весов
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402

NOTE = "Лайвов здесь нет"
DROP = "L"


def policy() -> dict:
    return core.MODEL.get("live_blocked", {})


def redistribute(weights: dict, drop: str = DROP) -> dict:
    """Вес выброшенной оси раздаётся остальным пропорционально их доле."""
    rest = {k: float(v) for k, v in weights.items() if k != drop}
    total = sum(rest.values())
    if total <= 0:
        raise core.DataError("после выброса оси не осталось весов")
    out = {k: v / total for k, v in rest.items()}
    assert abs(sum(out.values()) - 1.0) < core.EPS
    return out


def rate_blocked(artist: dict, snapshot: str | None = None) -> dict:
    """Считает артиста без оси ЛАЙВЫ. Причина обязательна."""
    reason = artist.get("live_blocked")
    if not reason or not str(reason).strip():
        raise core.DataError("нужна причина в поле live_blocked, иначе ось не выбрасывается")

    stub = dict(artist)
    stub["cap"] = artist.get("cap") or 1
    stub["cities"] = artist.get("cities") if artist.get("cities") is not None else 0
    base = core.rate(stub, snapshot)

    weights = redistribute(core.LEAGUE_WEIGHTS[artist["pos"]])
    stats = dict(base["stats"])
    stats.pop(DROP, None)
    raw = sum(stats[k] * weights[k] for k in weights)
    ovr = core.rnd(raw)
    potential = min(int(core.HI), max(ovr, ovr + (base["potential"] - base["ovr"])))

    out = dict(base)
    out.update({
        "stats": stats,
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "raw": round(raw, 2),
        "ovr": ovr,
        "potential": potential,
        "gap": potential - ovr,
        "price_mln": core.price(ovr, potential),
        "live_blocked": str(reason),
        "card_note": NOTE,
        "axes": len(stats),
    })
    return out


def diff(artist: dict, snapshot: str | None = None) -> dict:
    """Что политика меняет по сравнению с обычным расчётом."""
    stub = dict(artist)
    stub["cap"] = artist.get("cap") or 1
    stub["cities"] = artist.get("cities") if artist.get("cities") is not None else 0
    full = core.rate(stub, snapshot)
    blocked = rate_blocked(artist, snapshot)
    return {
        "name": artist.get("name", artist.get("key", "?")),
        "ovr_full": full["ovr"],
        "ovr_blocked": blocked["ovr"],
        "delta": blocked["ovr"] - full["ovr"],
        "lives_dropped": full["stats"][DROP],
        "reason": blocked["live_blocked"],
    }


def main() -> int:
    print("Политика:", json.dumps(policy(), ensure_ascii=False))
    print("Строка на кадре:", NOTE)
    print()
    order = [k for k in core.STAT_ORDER if k != DROP]
    print("| Позиция | " + " | ".join(core.STAT_LABELS[k] for k in order) + " |")
    print("|" + "|".join(["---"] * (len(order) + 1)) + "|")
    for pos, weights in core.LEAGUE_WEIGHTS.items():
        new = redistribute(weights)
        print("| %s | " % pos + " | ".join("%.0f%%" % (new[k] * 100) for k in order) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
