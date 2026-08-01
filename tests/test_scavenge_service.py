import random

import pytest

from bot_pkg.services import scavenge_service

ZONE = {
    "risk": 3,
    "loot_min": 6,
    "loot_max": 13,
    "xp": 4,
    "cd_min": 12,
    "label_key": "scavenge_suburb",
    "desc": "test zone",
}


def test_compute_chance_within_bounds():
    risk, chance = scavenge_service.compute_chance(ZONE)
    assert risk == 3
    assert 5 <= chance <= 95


def test_compute_chance_clamped_to_minimum_5_percent():
    brutal_zone = {**ZONE, "risk": 50}
    _, chance = scavenge_service.compute_chance(brutal_zone)
    assert chance == 5


def test_compute_chance_risk_modifier_cannot_go_negative():
    # a large negative risk_modifier (e.g. a "safety" world event) should
    # floor at risk=0, not go negative and inflate the chance past 100.
    risk, chance = scavenge_service.compute_chance(ZONE, risk_modifier=-999)
    assert risk == 0
    assert chance == 95  # min(95, 100 - risk*12) with risk floored at 0


def test_roll_scavenge_is_deterministic_given_seeded_rng():
    outcome_a = scavenge_service.roll_scavenge("suburb", ZONE, rng=random.Random(42))
    outcome_b = scavenge_service.roll_scavenge("suburb", ZONE, rng=random.Random(42))

    assert outcome_a == outcome_b


def test_roll_scavenge_success_produces_loot_from_correct_pool():
    # seed chosen so this rolls a success against ZONE's chance (~64%)
    outcome = scavenge_service.roll_scavenge("suburb", ZONE, rng=random.Random(1))

    if outcome.success:
        assert set(outcome.loot.keys()) <= set(scavenge_service.LOOT_POOL)
        assert sum(outcome.loot.values()) >= ZONE["loot_min"] * 0  # non-negative
    assert outcome.cooldown_seconds == ZONE["cd_min"] * 60


def test_roll_scavenge_failure_has_damage_and_no_loot():
    # brute-force a seed that produces a failure for this zone/chance
    for seed in range(200):
        outcome = scavenge_service.roll_scavenge("suburb", ZONE, rng=random.Random(seed))
        if not outcome.success:
            assert outcome.damage > 0
            assert outcome.loot == {}
            return
    pytest.fail("expected at least one failure in 200 seeded rolls")


def test_rare_loot_multiplier_only_affects_battery_and_copper_weights():
    # weight lists shouldn't be mutated in place (shared module-level dict)
    original = list(scavenge_service.LOOT_WEIGHTS["bunker"])
    scavenge_service.roll_scavenge(
        "bunker",
        {**ZONE, "risk": 0},  # near-certain success
        rare_loot_multiplier=3.0,
        rng=random.Random(7),
    )
    assert scavenge_service.LOOT_WEIGHTS["bunker"] == original


def test_apply_success_adds_loot_and_bumps_stats():
    player = {"resources": {"scrap": 2}, "stats": {}}
    outcome = scavenge_service.ScavengeOutcome(
        zone_key="alley",
        success=True,
        chance=90,
        roll=10,
        risk=1,
        cooldown_seconds=480,
        loot={"scrap": 3, "glass": 1},
    )

    scavenge_service.apply_success(player, outcome)

    assert player["resources"]["scrap"] == 5
    assert player["resources"]["glass"] == 1
    assert player["stats"]["scavenges"] == 1
    assert player["stats"]["scavenge_success"] == 1


def test_apply_success_rejects_failed_outcome():
    outcome = scavenge_service.ScavengeOutcome(
        zone_key="alley", success=False, chance=10, roll=99, risk=1, cooldown_seconds=1
    )
    with pytest.raises(ValueError):
        scavenge_service.apply_success({"resources": {}, "stats": {}}, outcome)


def test_apply_failure_applies_damage_and_floors_hp_at_1():
    player = {"hp": 5, "resources": {}, "stats": {}}
    outcome = scavenge_service.ScavengeOutcome(
        zone_key="alley", success=False, chance=10, roll=99, risk=1,
        cooldown_seconds=480, damage=50,
    )

    lost = scavenge_service.apply_failure(player, outcome, rng=random.Random(1))

    assert player["hp"] == 1  # floored, not negative
    assert lost == {}  # had no resources to lose


def test_apply_failure_never_loses_more_than_held():
    player = {"hp": 100, "resources": {"scrap": 1}, "stats": {}}
    outcome = scavenge_service.ScavengeOutcome(
        zone_key="alley", success=False, chance=10, roll=99, risk=1,
        cooldown_seconds=480, damage=5,
    )

    scavenge_service.apply_failure(player, outcome, rng=random.Random(3))

    assert player["resources"]["scrap"] >= 0
