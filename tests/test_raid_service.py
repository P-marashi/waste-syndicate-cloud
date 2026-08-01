import random

from bot_pkg.services import raid_service as r


# ---------------------------------------------------------------------
# Targeting
# ---------------------------------------------------------------------


def test_raid_target_score_higher_for_tougher_target():
    weak = r.raid_target_score(water=100, total_defense=50, total_attack=50, level=1)
    strong = r.raid_target_score(water=100, total_defense=5000, total_attack=5000, level=10)
    assert strong > weak


def test_bucket_slice_small_pool_returns_everything():
    candidates = ["a", "b"]
    assert r.bucket_slice(candidates, "weak") == candidates
    assert r.bucket_slice(candidates, "strong") == candidates


def test_bucket_slice_splits_into_thirds():
    candidates = list(range(9))  # sorted ascending by score
    assert r.bucket_slice(candidates, "weak") == [0, 1, 2]
    assert r.bucket_slice(candidates, "medium") == [3, 4, 5]
    assert r.bucket_slice(candidates, "strong") == [6, 7, 8]


def test_bucket_slice_unknown_key_returns_all():
    candidates = list(range(9))
    assert r.bucket_slice(candidates, "???") == candidates


def test_bucket_slice_medium_falls_back_when_empty():
    # with very few candidates relative to bucket math, medium slice
    # could come up empty — original code falls back to full list
    candidates = list(range(3))
    result = r.bucket_slice(candidates, "medium")
    assert result  # never empty


# ---------------------------------------------------------------------
# Combat rolls
# ---------------------------------------------------------------------


def test_roll_attack_deterministic_with_seed():
    a = r.roll_attack(1000, 1.0, 5, rng=random.Random(1))
    b = r.roll_attack(1000, 1.0, 5, rng=random.Random(1))
    assert a == b


def test_roll_attack_scales_with_level():
    rng_a = random.Random(1)
    rng_b = random.Random(1)
    low_level = r.roll_attack(1000, 1.0, 1, rng=rng_a)
    high_level = r.roll_attack(1000, 1.0, 50, rng=rng_b)
    assert high_level > low_level


def test_roll_defense_scales_with_level_above_4():
    rng_a = random.Random(1)
    rng_b = random.Random(1)
    low_level = r.roll_defense(1000, 4, rng=rng_a)
    high_level = r.roll_defense(1000, 20, rng=rng_b)
    assert high_level > low_level


def test_roll_defense_no_bonus_below_level_4():
    rng_a = random.Random(1)
    rng_b = random.Random(1)
    lvl1 = r.roll_defense(1000, 1, rng=rng_a)
    lvl4 = r.roll_defense(1000, 4, rng=rng_b)
    assert lvl1 == lvl4  # max(0, level-4) is 0 for both


# ---------------------------------------------------------------------
# Loot
# ---------------------------------------------------------------------


def test_resource_loot_amount_never_exceeds_current():
    amount = r.resource_loot_amount(current_amount=10, loot_pct_base=50.0, resource="scrap")
    assert amount <= 10


def test_resource_loot_amount_zero_when_target_has_none():
    assert r.resource_loot_amount(0, 1.0, "scrap") == 0


def test_resource_loot_amount_unknown_resource_uses_default_rate():
    amount = r.resource_loot_amount(100, 1.0, "unknown_resource")
    assert amount == int(100 * 0.05)  # default 5% rate


def test_compute_raid_loot_full_pass():
    result = r.compute_raid_loot(
        target_water=1000,
        target_resources={"scrap": 100, "plastic": 0, "glass": 50},
        loot_pct_base=1.0,
        resource_keys=["scrap", "plastic", "glass", "battery", "copper"],
    )
    assert result.water_looted == int(1000 * 0.135)
    assert result.resources_looted["scrap"] == int(100 * 0.09)
    assert "plastic" not in result.resources_looted  # target has none, nothing looted
    assert result.resources_looted["glass"] == int(50 * 0.07)
    assert "battery" not in result.resources_looted
    assert "copper" not in result.resources_looted
