from datetime import datetime, timedelta

from bot_pkg.services import player_service

BUILDINGS = {
    "wall": {"levels": {1: {"atk": 0, "def": 120}, 2: {"atk": 0, "def": 300}}},
    "armory": {"levels": {1: {"atk": 80, "def": 0}}},
    "purifier": {"levels": {1: {"prod": 12}, 2: {"prod": 24}}},
    "lab": {"levels": {1: {"discount": 0.05}}},
    "market_stall": {"levels": {1: {"fee_cut": 0.02}}},
}
CRAFT_ITEMS = {"spy_drone": {"atk": 10, "def": 0}}
LEGENDARY_ITEMS = {"void_blade": {"atk": 420, "def": 50}}
LEVELS = {1: {"xp": 10, "label": "مبتدی"}, 2: {"xp": 25, "label": "بازمانده"}}
HONOR_TITLES = [(-999, -1, "آشوبگر"), (0, 0, "بی‌طرف"), (1, 999, "قهرمان")]


# --------------------------- combat power ---------------------------


def test_compute_power_sums_building_and_inventory():
    atk, dfc = player_service.compute_power(
        {"wall": 2, "armory": 1},
        {"spy_drone": 3},
        buildings_table=BUILDINGS,
        craft_items=CRAFT_ITEMS,
        legendary_items=LEGENDARY_ITEMS,
    )
    # wall lvl2 def=300, armory lvl1 atk=80, 3x spy_drone atk=10*3*1.12=33.6->int in total
    assert dfc == 300
    assert atk == int(80 + 10 * 3 * 1.12)


def test_compute_power_ignores_zero_level_buildings():
    atk, dfc = player_service.compute_power(
        {"wall": 0}, {}, buildings_table=BUILDINGS, craft_items={}, legendary_items={}
    )
    assert (atk, dfc) == (0, 0)


def test_compute_power_counts_legendary_items():
    atk, dfc = player_service.compute_power(
        {}, {"void_blade": 1}, buildings_table=BUILDINGS, craft_items={}, legendary_items=LEGENDARY_ITEMS
    )
    assert atk == int(420 * 1 * 1.12)
    assert dfc == int(50 * 1 * 1.05)


def test_status_label_thresholds():
    assert player_service.status_label_for_defense(0) == "ابتدایی 🏚️"
    assert player_service.status_label_for_defense(500) == "ضعیف 🪵"
    assert player_service.status_label_for_defense(50000) == "بنکر افسانه‌ای 🏯"


# --------------------------- countdowns ---------------------------


def test_seconds_until_none_target_is_zero():
    assert player_service.seconds_until(None, datetime.now()) == 0


def test_seconds_until_future_target_positive():
    now = datetime(2026, 1, 1, 12, 0, 0)
    target = now + timedelta(seconds=90)
    assert player_service.seconds_until(target, now) == 90


def test_seconds_until_past_target_floors_at_zero():
    now = datetime(2026, 1, 1, 12, 0, 0)
    target = now - timedelta(seconds=90)
    assert player_service.seconds_until(target, now) == 0


def test_future_timestamp_adds_seconds():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert player_service.future_timestamp(now, 60) == now + timedelta(seconds=60)


# --------------------------- progression ---------------------------


def test_honor_title_matches_range():
    assert player_service.honor_title(-500, HONOR_TITLES) == "آشوبگر"
    assert player_service.honor_title(0, HONOR_TITLES) == "بی‌طرف"
    assert player_service.honor_title(500, HONOR_TITLES) == "قهرمان"


def test_honor_title_out_of_range_is_unknown():
    assert player_service.honor_title(99999, HONOR_TITLES) == "ناشناخته"


def test_level_info_returns_max_xp_and_label():
    assert player_service.level_info(1, 4, LEVELS) == (1, 4, 10, "مبتدی")


def test_apply_xp_no_level_up():
    level, xp, leveled = player_service.apply_xp(1, 4, 3, LEVELS)
    assert (level, xp, leveled) == (1, 7, False)


def test_apply_xp_single_level_up():
    level, xp, leveled = player_service.apply_xp(1, 8, 5, LEVELS)  # 13 xp, needs 10
    assert leveled is True
    assert level == 2
    assert xp == 3  # 13 - 10


def test_apply_xp_multiple_level_ups_in_one_call():
    level, xp, leveled = player_service.apply_xp(1, 0, 40, LEVELS, max_level=2)
    # level1 needs 10 -> level2 (30 left), level2 is max_level so stop even with xp left
    assert level == 2
    assert leveled is True


def test_apply_xp_respects_multiplier():
    level, xp, leveled = player_service.apply_xp(1, 0, 10, LEVELS, xp_multiplier=2.0)
    assert xp == 10  # 20 xp gained, needs 10 to level -> level 2, 10 left
    assert level == 2


# --------------------------- buildings ---------------------------


def test_purifier_production_rate_zero_when_no_building():
    assert player_service.purifier_production_rate(0, BUILDINGS) == 0


def test_purifier_production_rate_reads_table():
    assert player_service.purifier_production_rate(2, BUILDINGS) == 24


def test_resolve_finished_upgrades_splits_due_and_pending():
    now = datetime(2026, 1, 1, 12, 0, 0)

    def fromiso(value, default):
        return value if isinstance(value, datetime) else default

    upgrades = [
        {"bldg": "wall", "to_level": 2, "finish": now - timedelta(seconds=1)},  # due
        {"bldg": "armory", "to_level": 2, "finish": now + timedelta(seconds=60)},  # pending
    ]
    finished, remaining, new_levels = player_service.resolve_finished_upgrades(
        upgrades, buildings_table=BUILDINGS, now=now, fromiso=fromiso
    )
    assert len(finished) == 1
    assert finished[0]["bldg"] == "wall"
    assert new_levels == {"wall": 2}
    assert len(remaining) == 1
    assert remaining[0]["bldg"] == "armory"


def test_resolve_finished_upgrades_skips_unknown_building():
    now = datetime(2026, 1, 1, 12, 0, 0)

    def fromiso(value, default):
        return value if isinstance(value, datetime) else default

    upgrades = [{"bldg": "not_a_real_building", "to_level": 2, "finish": now}]
    finished, remaining, new_levels = player_service.resolve_finished_upgrades(
        upgrades, buildings_table=BUILDINGS, now=now, fromiso=fromiso
    )
    assert finished == []
    assert new_levels == {}
    assert remaining == []  # it's neither finished nor kept, since it's due but invalid


# --------------------------- passive income ---------------------------


def test_compute_passive_water_zero_without_purifier():
    assert player_service.compute_passive_water(3600, 0, buildings_table=BUILDINGS) == 0


def test_compute_passive_water_one_hour_at_base_rate():
    # purifier lvl1 prod=12/hr, 3600s elapsed -> 12 water
    assert player_service.compute_passive_water(3600, 1, buildings_table=BUILDINGS) == 12


def test_compute_passive_water_applies_event_and_cartel_bonus():
    earned = player_service.compute_passive_water(
        3600, 1, buildings_table=BUILDINGS, event_mod=2.0, cartel_bonus=0.5
    )
    # 12 * 2.0 * 1.5 = 36
    assert earned == 36
