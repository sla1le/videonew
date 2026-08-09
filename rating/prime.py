#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Прайм-карточка v1.1.

Рейтинг пикового года считается сезонным движком, как в formats.icons().
Лиговый движок здесь не применяется: в нём веса и статы сегодняшнего дня.

Статы прайм-карты:
  T S D  судейские баллы ЗА ТОТ ГОД
  H      от пикового места в чарте того года
  I      от места альбома в итогах того года
  ЛАЙВОВ нет, в сезонном движке этого веса нет

Что добавлено в v1.1:
  пик в чарте стал необязательным. Для годов без публичного трекового чарта
  в записи ставится peak.absent_reason, и ХИТЫ идут по строке вне списка, то есть 62.
  Балл сегодня тоже необязателен: если артиста нет в лиге, дельта не считается
  и на карту не выводится.

Запуск:
    python3 rating/prime.py
"""
from __future__ import annotations
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LO, HI = 30.0, 99.0
W = {"T": .15, "S": .15, "D": .15, "H": .25, "I": .30}
assert abs(sum(W.values()) - 1.0) < 1e-9
OUTSIDE = 62.0


def rnd(v: float) -> int:
    return int(math.floor(v + 0.5))


def clamp(v: float) -> float:
    return max(LO, min(HI, v))


def peak_hits(position: int | None) -> float:
    """Пик в чарте того года. Первое место даёт 96, отсутствие чарта даёт 62."""
    if position is None:
        return OUTSIDE
    return clamp(96 - 8 * math.log2(position))


def album_influence(rank: int | None) -> float:
    """Место альбома в итогах года. Нет итогов года равно 62."""
    if rank is None:
        return OUTSIDE
    return clamp(96 - 7 * math.log2(rank))


def price(ovr: int) -> int:
    """Цена прайм-карты. Потенциала у неё нет, множитель равен единице."""
    return rnd(3.0 * 2 ** ((ovr - 55) / 5.0))


def build(entry: dict) -> dict:
    j = entry["judge"]
    peak = entry.get("peak") or {}
    yearend = entry.get("yearend") or {}
    H = peak_hits(peak.get("position"))
    I = album_influence(yearend.get("album_rank"))
    stats = {"T": j["T"], "S": j["S"], "D": j["D"], "H": rnd(H), "I": rnd(I)}
    raw = sum(stats[k] * W[k] for k in W)
    ovr = rnd(raw)
    now = entry.get("now_ovr")
    return {**entry, "stats": stats, "raw": round(raw, 2), "ovr": ovr,
            "price_mln": price(ovr),
            "delta": (ovr - now) if now is not None else None,
            "tier": "gold" if ovr >= 80 else ("silver" if ovr >= 70 else "bronze")}


def load() -> list[dict]:
    data = json.loads((HERE / "data" / "primes.json").read_text(encoding="utf-8"))
    return [build(e) for e in data["primes"]]


if __name__ == "__main__":
    for c in load():
        s = c["stats"]
        d = "без дельты" if c["delta"] is None else "%+d к сегодня" % c["delta"]
        print("%-12s %d  %s  OVR %d (%s)  %d млн  T%d S%d D%d H%d I%d  raw %.2f"
              % (c["name"], c["year"], c["tier"].upper(), c["ovr"], d,
                 c["price_mln"], s["T"], s["S"], s["D"], s["H"], s["I"], c["raw"]))
