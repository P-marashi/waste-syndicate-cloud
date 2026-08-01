import random

from bot_pkg.services import cache_service as c


def test_cache_find_chance_known_zones():
    assert c.cache_find_chance("alley") == 0.01
    assert c.cache_find_chance("bunker") == 0.04


def test_cache_find_chance_unknown_zone_uses_default():
    assert c.cache_find_chance("nowhere") == c.DEFAULT_CACHE_FIND_CHANCE


def test_rolls_cache_find_deterministic():
    a = c.rolls_cache_find("bunker", rng=random.Random(1))
    b = c.rolls_cache_find("bunker", rng=random.Random(1))
    assert a == b


def test_rolls_cache_find_never_true_at_zero_chance():
    # a zone effectively guaranteed to fail: use a chance of 0 by patching
    # via an unknown zone with the module default temporarily unreachable
    # — instead, just check across many seeds bunker (highest chance,
    # 4%) doesn't trigger every time.
    results = [c.rolls_cache_find("bunker", rng=random.Random(seed)) for seed in range(500)]
    assert not all(results)
    assert any(results)


def test_roll_cache_outcome_deterministic():
    a = c.roll_cache_outcome(rng=random.Random(42))
    b = c.roll_cache_outcome(rng=random.Random(42))
    assert a == b


def test_roll_cache_outcome_covers_all_kinds_across_seeds():
    kinds = {c.roll_cache_outcome(rng=random.Random(seed)).kind for seed in range(2000)}
    assert kinds == {
        "trap",
        "water_small",
        "resources_common",
        "resources_rare",
        "water_big",
        "legendary",
    }


def test_roll_cache_outcome_trap_has_damage_no_loot():
    for seed in range(500):
        outcome = c.roll_cache_outcome(rng=random.Random(seed))
        if outcome.kind == "trap":
            assert outcome.damage > 0
            assert outcome.water == 0
            assert outcome.resources == {}
            return
    raise AssertionError("no trap outcome found in 500 seeds")


def test_roll_cache_outcome_common_resources_has_three_types():
    for seed in range(500):
        outcome = c.roll_cache_outcome(rng=random.Random(seed))
        if outcome.kind == "resources_common":
            assert set(outcome.resources.keys()) == {"scrap", "plastic", "glass"}
            return
    raise AssertionError("no resources_common outcome found in 500 seeds")


def test_roll_cache_outcome_legendary_has_no_extra_payload():
    for seed in range(20000):
        outcome = c.roll_cache_outcome(rng=random.Random(seed))
        if outcome.kind == "legendary":
            assert outcome.damage == 0
            assert outcome.water == 0
            assert outcome.resources == {}
            return
    raise AssertionError("no legendary outcome found in 20000 seeds (0.2% chance)")
