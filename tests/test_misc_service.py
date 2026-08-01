from bot_pkg.services import misc_service as m


# ---------------------------------------------------------------------
# Daily streak
# ---------------------------------------------------------------------


def test_streak_continues_if_claimed_yesterday():
    assert m.next_daily_streak(5, "2026-07-31", "2026-07-31") == 6


def test_streak_resets_if_gap_in_days():
    assert m.next_daily_streak(5, "2026-07-20", "2026-07-31") == 1


def test_streak_resets_if_never_claimed():
    assert m.next_daily_streak(0, None, "2026-07-31") == 1


def test_streak_starts_at_1_for_first_claim():
    assert m.next_daily_streak(0, None, "2026-01-01") == 1


# ---------------------------------------------------------------------
# Daily reward
# ---------------------------------------------------------------------


def test_daily_reward_scales_with_streak():
    day1 = m.compute_daily_reward(1)
    day5 = m.compute_daily_reward(5)
    assert day5["water"] > day1["water"]
    assert day5["scrap"] > day1["scrap"]


def test_daily_reward_water_caps_at_200_bonus():
    reward = m.compute_daily_reward(streak=100)
    assert reward["water"] == 60 + 200  # capped


def test_daily_reward_scrap_caps_at_50_bonus():
    reward = m.compute_daily_reward(streak=100)
    assert reward["scrap"] == 10 + 50


def test_daily_reward_battery_every_3rd_day():
    assert m.compute_daily_reward(3)["battery"] == 1
    assert m.compute_daily_reward(6)["battery"] == 1
    assert m.compute_daily_reward(1)["battery"] == 0
    assert m.compute_daily_reward(2)["battery"] == 0


def test_daily_reward_day1_baseline():
    reward = m.compute_daily_reward(1)
    assert reward == {"water": 70, "scrap": 12, "plastic": 10, "battery": 0}


# ---------------------------------------------------------------------
# Leaderboard rank
# ---------------------------------------------------------------------


def test_find_leaderboard_rank_found():
    rows = [("a", 100), ("b", 90), ("c", 80)]
    assert m.find_leaderboard_rank("b", rows) == (2, 90)


def test_find_leaderboard_rank_not_found():
    rows = [("a", 100), ("b", 90)]
    assert m.find_leaderboard_rank("z", rows) is None


def test_find_leaderboard_rank_first_place():
    rows = [("a", 100), ("b", 90)]
    assert m.find_leaderboard_rank("a", rows) == (1, 100)


def test_find_leaderboard_rank_empty_rows():
    assert m.find_leaderboard_rank("a", []) is None
