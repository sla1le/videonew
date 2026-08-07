#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регрессионные тесты ECHORATE v4.0.

    cd rating && python3 test_rating.py

Закрепляют опубликованные баллы. Если тест упал, значит либо сломалась модель,
либо выпущенный в эфир выпуск теперь невоспроизводим. Оба случая требуют записи в corrections.md.
"""
from __future__ import annotations

import sys
import traceback

import core
import formats
import season

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(fn) -> None:
    try:
        fn()
        PASSED.append(fn.__name__)
    except Exception as err:  # noqa: BLE001
        FAILED.append((fn.__name__, f"{type(err).__name__}: {err}"))


# ---------------------------------------------------------------- базовая математика

def test_rounding():
    assert core.rnd(81.5) == 82, "половина округляется вверх"
    assert core.rnd(81.49) == 81
    assert core.rnd(-0.5) == 0


def test_clamp():
    assert core.clamp(120) == 99
    assert core.clamp(10) == 30
    assert core.clamp(70) == 70


def test_weights_sum():
    for pos, w in core.LEAGUE_WEIGHTS.items():
        assert abs(sum(w.values()) - 1.0) < core.EPS, pos
        assert w["T"] + w["S"] + w["D"] <= 0.5 + core.EPS, pos


def test_hits_anchor():
    assert abs(core.hits(60_000_000) - 70) < core.EPS, "60 млн это якорь 70"
    assert abs(core.hits(120_000_000) - 76) < core.EPS, "удвоение даёт плюс 6"


def test_lives_anchor():
    assert abs(core.lives(10_000, 5) - 70) < core.EPS, "10 000 и 5 городов это якорь 70"
    assert abs(core.lives(20_000, 5) - 75) < core.EPS, "удвоение зала даёт плюс 5"
    assert abs(core.lives(10_000, 11) - 76) < core.EPS, "бонус за города упирается в 6"
    assert abs(core.lives(10_000, 40) - 76) < core.EPS, "потолок бонуса работает"


def test_influence_anchor():
    assert abs(core.influence(300_000_000, 0) - 70) < core.EPS
    assert abs(core.influence(600_000_000, 0) - 76) < core.EPS


def test_influence_scene_range():
    try:
        core.influence(300_000_000, 9)
    except core.DataError:
        return
    raise AssertionError("scene выше 6 должен падать")


def test_age_and_form_bonus():
    assert core.age_bonus(20) == 8
    assert core.age_bonus(25) == 4
    assert core.age_bonus(40) == 0
    assert core.age_bonus(None) == 2
    assert core.form_bonus(20) == 3
    assert core.form_bonus(-20) == -2
    assert core.form_bonus(0) == 0


def test_age_from_born():
    assert core.age_at("2000-10-22", "2026-08-07") == 25, "день рождения ещё не наступил"
    assert core.age_at("1994-06-25", "2026-08-07") == 32, "день рождения уже прошёл"
    assert core.age_at(None, "2026-08-07") is None


# ---------------------------------------------------------------- лига

PUBLISHED_LEAGUE = [
    ("ЕГОР КРИД", 82.30, 82, 83),
    ("OG BUDA", 79.75, 80, 81),
    ("KAI ANGEL", 78.75, 79, 81),
    ("9MICE", 77.85, 78, 80),
    ("LILDRUGHILL", 74.45, 74, 76),
    ("THRILL PILL", 68.20, 68, 70),
]


def test_league_matches_published():
    rows = {r["name"]: r for r in core.league()["rows"]}
    for name, raw, ovr, potential in PUBLISHED_LEAGUE:
        row = rows[name]
        assert abs(row["raw"] - raw) < 0.005, f"{name}: raw {row['raw']} вместо {raw}"
        assert row["ovr"] == ovr, f"{name}: OVR {row['ovr']} вместо {ovr}"
        assert row["potential"] == potential, f"{name}: ПОТ {row['potential']} вместо {potential}"


def test_league_order():
    names = [r["name"] for r in core.league()["rows"]]
    assert names == [n for n, _, _, _ in PUBLISHED_LEAGUE], names


def test_sources_required():
    broken = {"key": "x", "name": "X", "pos": "ST", "T": 70, "S": 70, "D": 70,
              "top5": 1_000_000, "cap": 1000, "cities": 5, "catalog": 1_000_000, "scene": 0}
    try:
        core.rate(broken)
    except core.DataError:
        return
    raise AssertionError("артист без источников должен падать")


# ---------------------------------------------------------------- сезоны

def test_season_2015():
    rows = season.solve_year(2015)["rows"]
    got = [(r["n"], r["ovr"]) for r in rows[:3]]
    assert got == [("СКРИПТОНИТ", 90), ("ЛСП", 86), ("OXXXYMIRON", 86)], got


def test_season_2017():
    rows = season.solve_year(2017)["rows"]
    got = [(r["n"], r["ovr"]) for r in rows[:3]]
    assert got == [("ЛСП", 88), ("PHARAOH", 87), ("СКРИПТОНИТ", 85)], got


def test_season_2016_blocked():
    result = season.solve_year(2016)
    assert result["status"] == "needs_sources", result["status"]
    assert result["rows"] == []
    assert result["blocked_by"], "должен быть список того, чего не хватает"


def test_season_role_penalty():
    assert core.season_hits(1, "lead") == 96
    assert core.season_hits(1, "colead") == 93
    assert core.season_hits(1, "guest") == 87
    assert core.season_hits(None) == 62, "вне топ-10 это 62"
    assert core.season_hits(11) == 62


def test_season_vote_bonus():
    assert core.season_influence(1, 1) == 96, "потолок 96 держит"
    assert core.season_influence(5, 1) == core.clamp(96 - 7 * 2.321928094887362 + 5)
    assert core.season_influence(5, 9) == core.clamp(96 - 7 * 2.321928094887362), "голос вне топ-5 не даёт бонуса"


def test_season_no_transitive_merge():
    """Группы тайбрейка собираются от якоря, а не цепочкой."""
    pool = [
        {"n": "A", "pos": "ST", "T": 90, "S": 90, "D": 90, "tr": 1, "alb": 1, "spots": [1, 1]},
        {"n": "B", "pos": "CM", "T": 89, "S": 89, "D": 89, "tr": 1, "alb": 1, "spots": [1]},
        {"n": "C", "pos": "CB", "T": 88, "S": 88, "D": 88, "tr": 1, "alb": 1, "spots": [1]},
    ]
    rows = core.season_solve(pool)
    assert rows[0]["n"] == "A"
    assert [r["place"] for r in rows] == [1, 2, 3]


# ---------------------------------------------------------------- форматы

def test_price_monotonic():
    assert core.price(90, 90) > core.price(80, 80) > core.price(70, 70)
    assert core.price(80, 90) > core.price(80, 80), "запас поднимает цену"


def test_squad_budget():
    result = formats.squad()
    assert result["combos"], "должен быть хотя бы один вариант"
    for combo in result["combos"]:
        assert combo["cost"] <= result["budget"], combo
        assert len(combo["names"]) == 3, combo


def test_squad_excludes_top_artist():
    """Крид за 130 не влезает ни в одно трио. Это ключевой драматургический факт формата."""
    result = formats.squad()
    assert not any("ЕГОР КРИД" in c["names"] for c in result["combos"])


def test_hidden_leader():
    result = formats.hidden()
    assert result["rows"][0]["name"] == "LILDRUGHILL", result["rows"][0]["name"]
    assert result["rows"][-1]["name"] == "ЕГОР КРИД"
    assert result["rows"][-1]["hidden_gap"] < 0, "у Крида охват выше ремесла"
    assert len(result["winners"]) == 4


def test_wonderkids_blocked():
    result = formats.wonderkids()
    assert result["ready"] is False, "в лиге нет никого младше 24"
    assert result["blocked_by"]


def test_toty_2017():
    team = season.toty(2017)
    assert team["slots"]["RW"]["name"] == "ЛСП"
    assert team["slots"]["LW"]["name"] == "PHARAOH"
    assert team["slots"]["CDM"]["name"] == "СКРИПТОНИТ"
    assert team["slots"]["CAM"]["name"] == "ХАСКИ"


def test_toty_no_position_swap():
    """Пустая позиция остаётся пустой. Затыкать её чужим артистом запрещено."""
    team = season.toty(2017)
    assert team["slots"]["CM"] is None, "в пуле 2017 нет ни одного CM"
    assert "CM" in team["empty"]
    names = [v["name"] for v in team["slots"].values() if v]
    assert len(names) == len(set(names)), "артист не может занять две позиции"


def test_icons_peak_year():
    rows = {r["name"]: r for r in formats.icons()["rows"]}
    assert rows["СКРИПТОНИТ"]["peak_year"] == 2015
    assert rows["PHARAOH"]["peak_year"] == 2017
    assert rows["ЛСП"]["peak_year"] == 2017


def test_rookies_blocked():
    result = formats.rookies(2026)
    assert result["ready"] is False, "в базе нет дебютантов 2025 и 2026"
    assert result["blocked_by"]


def test_puskas_blocked_without_data():
    result = formats.puskas()
    if not (core.DATA / "puskas.json").exists():
        assert result["ready"] is False
        assert result["blocked_by"]


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        check(test)
    print(f"пройдено {len(PASSED)} из {len(PASSED) + len(FAILED)}")
    for name, err in FAILED:
        print(f"  ПАДАЕТ {name}: {err}")
    sys.exit(1 if FAILED else 0)
