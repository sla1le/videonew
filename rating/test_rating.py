#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Регрессионные тесты ECHORATE. Запуск: python3 rating/test_rating.py

Смысл: после любой правки движка уже опубликованные баллы не должны ехать молча.
Если балл меняется осознанно, сначала правится тест, потом код, потом запись в corrections.md.
"""
from __future__ import annotations

import sys
import traceback

import core
import formats
import season
import worldcup

PASSED, FAILED = [], []


def check(name: str, fn) -> None:
    try:
        fn()
        PASSED.append(name)
    except Exception as err:  # noqa: BLE001
        FAILED.append((name, f"{type(err).__name__}: {err}"))
        traceback.print_exc(limit=1)


# ---------------------------------------------------------------- математика
def test_rounding():
    assert core.rnd(0.5) == 1 and core.rnd(0.49) == 0 and core.rnd(-0.5) == 0
    assert core.rnd(82.5) == 83 and core.rnd(74.45) == 74


def test_clamp():
    assert core.clamp(120) == 99 and core.clamp(1) == 30 and core.clamp(70) == 70


def test_weights_sum():
    for pos, w in core.LEAGUE_WEIGHTS.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9, pos
        assert w["T"] + w["S"] + w["D"] <= 0.5 + 1e-9, pos


def test_hits_anchor():
    assert abs(core.hits(60_000_000) - 70) < 1e-9
    assert abs(core.hits(120_000_000) - 76) < 1e-9


def test_lives_anchor():
    assert abs(core.lives(10_000, 5) - 70) < 1e-9
    assert abs(core.lives(10_000, 12) - 76) < 1e-9, "бонус за города ограничен шестью"
    assert abs(core.lives(10_000, 5, festival=True) - core.lives(6_000, 5)) < 1e-9


def test_influence_anchor():
    assert abs(core.influence(300_000_000, 0) - 70) < 1e-9
    assert abs(core.influence(600_000_000, 0) - 76) < 1e-9


def test_influence_scene_range():
    for bad in (7, -7):
        try:
            core.influence(300_000_000, bad)
        except core.DataError:
            continue
        raise AssertionError(f"scene {bad} должен быть отклонён")


def test_age_and_form_bonus():
    assert core.age_bonus(20) == 8 and core.age_bonus(24) == 6 and core.age_bonus(27) == 4
    assert core.age_bonus(30) == 2 and core.age_bonus(33) == 1 and core.age_bonus(40) == 0
    assert core.age_bonus(None) == 2
    assert core.form_bonus(20) == 3 and core.form_bonus(-20) == -2 and core.form_bonus(0) == 0


def test_age_from_born():
    assert core.age_at("1994-06-25", "2026-08-07") == 32
    assert core.age_at("2000-11-21", "2026-08-07") == 25
    assert core.age_at(None, "2026-08-07") is None


# ---------------------------------------------------------------- лига
LEAGUE_EXPECTED = {
    "kreed":  (82, 83, {"T": 68, "S": 82, "D": 86, "H": 80, "L": 90, "I": 81}, 82.30),
    "buda":   (80, 81, {"T": 76, "S": 85, "D": 88, "H": 75, "L": 70, "I": 80}, 79.75),
    "kai":    (79, 81, {"T": 72, "S": 90, "D": 88, "H": 68, "L": 69, "I": 75}, 78.75),
    "mice":   (78, 80, {"T": 74, "S": 88, "D": 85, "H": 69, "L": 69, "I": 75}, 77.85),
    "dhill":  (74, 76, {"T": 78, "S": 90, "D": 86, "H": 65, "L": 55, "I": 64}, 74.45),
    "thrill": (68, 70, {"T": 64, "S": 74, "D": 80, "H": 67, "L": 62, "I": 59}, 68.20),
}


def test_league_matches_published():
    rows = {r["key"]: r for r in core.league()["rows"]}
    assert set(rows) == set(LEAGUE_EXPECTED), f"состав лиги изменился: {sorted(rows)}"
    for key, (ovr, pot, stats, raw) in LEAGUE_EXPECTED.items():
        row = rows[key]
        assert row["ovr"] == ovr, f"{key}: OVR {row['ovr']}, ждали {ovr}"
        assert row["potential"] == pot, f"{key}: ПОТЕНЦИАЛ {row['potential']}, ждали {pot}"
        assert row["stats"] == stats, f"{key}: статы {row['stats']}"
        assert abs(row["raw"] - raw) < 0.005, f"{key}: raw {row['raw']}, ждали {raw}"


def test_league_order():
    names = [r["name"] for r in core.league()["rows"]]
    assert names == ["ЕГОР КРИД", "OG BUDA", "KAI ANGEL", "9MICE", "LILDRUGHILL", "THRILL PILL"], names


def test_sources_required():
    bad = {"key": "x", "name": "X", "pos": "ST", "T": 70, "S": 70, "D": 70,
           "top5": 1, "cap": 1, "cities": 1, "catalog": 1, "scene": 0}
    try:
        core.rate(bad)
    except core.DataError:
        return
    raise AssertionError("артист без источников не должен считаться")


# ---------------------------------------------------------------- сезон
def test_season_2015():
    rows = season.solve_year("2015")["rows"]
    top = [(r["n"], r["ovr"]) for r in rows[:3]]
    assert top == [("СКРИПТОНИТ", 90), ("ЛСП", 86), ("OXXXYMIRON", 86)], top
    assert abs(rows[0]["raw"] - 90.13) < 0.005
    assert rows[1].get("tiebreak") and rows[2].get("tiebreak"), "второе и третье место через тайбрейк"
    assert rows[1]["raw"] < rows[2]["raw"], "тайбрейк должен переставлять по числу попаданий"


def test_season_2017():
    rows = season.solve_year("2017")["rows"]
    top = [(r["n"], r["ovr"]) for r in rows[:3]]
    assert top == [("ЛСП", 88), ("PHARAOH", 87), ("СКРИПТОНИТ", 85)], top
    assert abs(rows[0]["raw"] - 88.40) < 0.005


def test_season_2016_blocked():
    result = season.solve_year("2016")
    assert result["status"] == "needs_sources", "2016 считать нельзя, нет источников"
    assert result["blocked_by"], "движок обязан сказать, чего не хватает"


def test_season_role_penalty():
    assert abs(core.season_hits(1, "lead") - 96) < 1e-9
    assert abs(core.season_hits(1, "colead") - 93) < 1e-9
    assert abs(core.season_hits(1, "guest") - 87) < 1e-9
    assert core.season_hits(None) == 62 and core.season_hits(11) == 62


def test_season_vote_bonus():
    assert abs(core.season_influence(1, 1) - (96 + 5)) > 1, "потолок 99 должен работать"
    assert core.season_influence(1, 1) == 99
    assert abs(core.season_influence(10, 6) - core.season_influence(10, None)) < 1e-9


def test_season_no_transitive_merge():
    pool = [{"n": f"A{i}", "pos": "ST", "T": 70 + i, "S": 70, "D": 70, "tr": None, "alb": None, "spots": []}
            for i in range(6)]
    rows = core.season_solve(pool)
    assert [r["place"] for r in rows] == [1, 2, 3, 4, 5, 6]


# ---------------------------------------------------------------- форматы
def test_price_monotonic():
    assert core.price(82, 83) == 130 and core.price(80, 81) == 98
    assert core.price(79, 81) == 88 and core.price(78, 80) == 76
    assert core.price(74, 76) == 44 and core.price(68, 70) == 19
    for ovr in range(60, 95):
        assert core.price(ovr + 1, ovr + 1) > core.price(ovr, ovr), "цена обязана расти с баллом"


def test_squad_budget():
    data = formats.squad()
    assert data["budget"] == 200
    positions = {row["name"]: row["pos"] for row in data["prices"]}
    for combo in data["combos"]:
        assert combo["cost"] <= 200
        assert len({positions[name] for name in combo["names"]}) == 3, "трио из трёх разных позиций"
    assert len(data["combos"]) == 4, f"вариантов {len(data['combos'])}, ждали 4"
    assert data["ready"] is True


def test_squad_excludes_top_artist():
    data = formats.squad()
    with_kreed = [combo for combo in data["combos"] if "ЕГОР КРИД" in combo["names"]]
    assert not with_kreed, "в текущей лиге Крид не влезает ни в одно трио с тремя позициями"


def test_hidden_leader():
    data = formats.hidden()
    assert data["rows"][0]["name"] == "LILDRUGHILL"
    assert abs(data["rows"][0]["hidden_gap"] - 20.17) < 0.01
    assert data["rows"][-1]["name"] == "ЕГОР КРИД"
    assert data["rows"][-1]["hidden_gap"] < 0, "у Крида охват выше ремесла"
    assert len(data["winners"]) == 4


def test_wonderkids_blocked():
    data = formats.wonderkids()
    assert data["ready"] is False, "в лиге нет никого до 24 лет, формат не готов"
    assert data["blocked_by"], "движок обязан объяснить, чего не хватает"


def test_toty_2017():
    data = formats.toty("2017")
    slots = {pos: pick["name"] if pick else None for pos, pick in data["slots"].items()}
    assert slots["RW"] == "ЛСП" and slots["LW"] == "PHARAOH"
    assert slots["CDM"] == "СКРИПТОНИТ" and slots["CAM"] == "ХАСКИ"
    assert slots["CM"] is None, "в пуле 2017 нет ни одного CM, слот остаётся пустым"
    assert "CM" in data["empty"]


def test_toty_no_position_swap():
    for year in ("2015", "2017"):
        data = formats.toty(year)
        pool = {r["n"]: r["pos"] for r in season.solve_year(year)["rows"]}
        for pos, pick in data["slots"].items():
            if pick:
                assert pool[pick["name"]] == pos, f"{year}: {pick['name']} поставлен не на свою позицию"


def test_icons_peak_year():
    data = formats.icons()
    cards = {c["name"]: c for c in data["rows"]}
    assert cards["СКРИПТОНИТ"]["peak_year"] == 2015
    assert cards["PHARAOH"]["peak_year"] == 2017
    assert cards["ЛСП"]["peak_year"] == 2017


def test_rookies_blocked():
    data = formats.rookies(2026)
    assert data["ready"] is False, "в базе нет дебютантов 2025 и 2026"
    assert data["blocked_by"]


def test_puskas_blocked_without_data():
    data = formats.puskas()
    assert data["ready"] is False and data["blocked_by"]


# ------------------------------------------------------------ кубок альбомов
def test_worldcup_weights():
    weights = worldcup.load()["model"]["weights"]
    assert abs(sum(weights.values()) - 1.0) < core.EPS
    jury = weights["T"] + weights["S"] + weights["D"]
    assert jury <= 0.5 + core.EPS, f"судейская часть {jury} больше половины"


def test_worldcup_influence_anchor():
    model = worldcup.load()["model"]
    assert abs(worldcup.influence(0.5, model) - 70.0) < 1e-9
    assert abs(worldcup.influence(1.0, model) - 79.0) < 1e-9
    assert worldcup.influence(0.0, model) == 52.0


def test_worldcup_canon_ranked():
    lists = {item["key"]: item for item in worldcup.load()["lists"]}
    first = {"key": "x", "lists": {"afisha100": 1}}
    last = {"key": "y", "lists": {"afisha100": 100}}
    both = {"key": "z", "lists": {"afisha100": 11, "flow20": True}}
    assert abs(worldcup.canon(first, lists) - 1.0) < 1e-9
    assert abs(worldcup.canon(last, lists) - 0.01) < 1e-9
    assert abs(worldcup.canon(both, lists) - 1.90) < 1e-9


def test_worldcup_pool_is_full():
    rows = worldcup.table()["rows"]
    assert len(rows) == 32, f"в пуле {len(rows)} альбомов"


def test_worldcup_one_album_per_artist():
    names = [row["artist"] for row in worldcup.table()["rows"]]
    assert len(names) == len(set(names))


def test_worldcup_sources_required():
    for album in worldcup.load()["albums"]:
        assert album.get("src"), f"{album['key']} без источника"
        assert album.get("lists"), f"{album['key']} без записи в списках"


def test_worldcup_window_from_2000():
    for row in worldcup.table()["rows"]:
        assert row["year"] >= 2000, f"{row['key']} вне окна кубка"


def test_worldcup_seed_top():
    rows = worldcup.table()["rows"]
    top = [(row["artist"], row["ovr"]) for row in rows[:3]]
    assert top == [("СКРИПТОНИТ", 89), ("ЛСП", 88), ("ATL", 87)], top


def test_worldcup_r16_pairs():
    data = worldcup.round_of(32)
    assert data["ready"] is True
    matches = data["matches"]
    assert len(matches) == 16
    assert matches[0]["top"]["seed"] == 1 and matches[0]["bottom"]["seed"] == 32
    assert matches[15]["top"]["seed"] == 16 and matches[15]["bottom"]["seed"] == 17
    keys = [m["top"]["key"] for m in matches] + [m["bottom"]["key"] for m in matches]
    assert len(set(keys)) == 32


def test_worldcup_closest_match_is_last():
    margins = [m["margin"] for m in worldcup.round_of(32)["matches"]]
    assert margins[-1] == min(margins), margins


def test_worldcup_tiebreak_year():
    early = {"key": "a", "artist": "A", "raw": 80.0, "I": 70.0, "year": 2001}
    late = {"key": "b", "artist": "B", "raw": 80.0, "I": 70.0, "year": 2015}
    assert worldcup.better(late, early)["key"] == "a"
    assert worldcup.better(early, late)["key"] == "a"


def test_worldcup_bracket_champion():
    data = worldcup.bracket()
    assert data["ready"] is True
    stages = [stage["round"] for stage in data["rounds"]]
    assert stages == ["1/16", "1/8", "1/4", "1/2", "ФИНАЛ"], stages
    assert data["champion"]["seed"] == 1


def test_worldcup_deck_fits_carousel():
    frames = 2 + len(worldcup.round_of(32)["matches"])
    assert frames <= 20, f"кадров {frames}, потолок карусели 20"


TESTS = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    for name, fn in TESTS:
        check(name, fn)
    print()
    print(f"пройдено {len(PASSED)} из {len(TESTS)}")
    for name, err in FAILED:
        print(f"  ПАДАЕТ {name}: {err}")
    sys.exit(1 if FAILED else 0)
