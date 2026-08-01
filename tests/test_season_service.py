from bot_pkg.services import season_service as s


def make_inputs(**overrides) -> s.SeasonScoreInputs:
    return s.SeasonScoreInputs(**overrides)


def test_combat_score_rewards_balanced_atk_def():
    balanced = s.compute_combat_score(make_inputs(total_attack=1000, total_defense=1000))
    lopsided = s.compute_combat_score(make_inputs(total_attack=2000, total_defense=0))
    # same "total power" (2000 combined), but balanced build scores higher
    # due to the min(atk, dfc) bonus term
    assert balanced > lopsided


def test_combat_score_includes_raids_and_boss_damage():
    base = s.compute_combat_score(make_inputs())
    with_raids = s.compute_combat_score(make_inputs(raids_done=5))
    assert with_raids == base + 5 * 180


def test_economy_score_basic():
    score = s.compute_economy_score(make_inputs(water=1000, resource_value=500))
    assert score == int(1000 * 1.1 + 500 * 0.28)


def test_progress_score_basic():
    score = s.compute_progress_score(make_inputs(level=5, xp=100))
    assert score == int(5 * 950 + 100 * 18)


def test_honor_score_basic():
    assert s.compute_honor_score(make_inputs(honor=100)) == 650


def test_season_score_breakdown_sums_correctly():
    inputs = make_inputs(total_attack=100, total_defense=100, water=500, level=2, honor=10)
    breakdown = s.season_score_breakdown(inputs)
    assert breakdown["total"] == (
        breakdown["combat"] + breakdown["economy"] + breakdown["progress"] + breakdown["honor"]
    )


def test_season_score_never_negative():
    # even a totally empty/default player should score 0, not error or go negative
    breakdown = s.season_score_breakdown(make_inputs())
    assert breakdown["total"] >= 0


# ---------------------------------------------------------------------
# split_time_left
# ---------------------------------------------------------------------


def test_split_time_left_days_hours_minutes():
    # 2 days, 3 hours, 4 minutes
    total = 2 * 86400 + 3 * 3600 + 4 * 60 + 30
    assert s.split_time_left(total) == (2, 3, 4)


def test_split_time_left_floors_at_zero():
    assert s.split_time_left(-100) == (0, 0, 0)


def test_split_time_left_zero():
    assert s.split_time_left(0) == (0, 0, 0)


def test_split_time_left_under_a_minute():
    assert s.split_time_left(45) == (0, 0, 0)
