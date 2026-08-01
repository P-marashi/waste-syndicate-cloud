import random

from bot_pkg.services import group_raid_service as g


def test_candidate_target_power_basic():
    power = g.candidate_target_power(total_defense=1000, total_attack=500, level=5)
    assert power == 1000 + int(500 * 0.45) + 5 * 90


def test_roll_player_target_defense_floors_at_900():
    defense = g.roll_player_target_defense(power=10, rng=random.Random(1))
    assert defense >= 900


def test_roll_npc_target_defense_scales_with_cartel_level():
    low = g.roll_npc_target_defense(1, rng=random.Random(1))
    high = g.roll_npc_target_defense(5, rng=random.Random(1))
    assert high > low


def test_roll_npc_target_defense_minimum_level_1():
    defense = g.roll_npc_target_defense(0, rng=random.Random(1))
    # max(1, cartel_level) means level 0 behaves like level 1
    defense_at_1 = g.roll_npc_target_defense(1, rng=random.Random(1))
    assert defense == defense_at_1


def test_is_group_raid_win():
    assert g.is_group_raid_win(1000, 999) is True
    assert g.is_group_raid_win(999, 1000) is False
    assert g.is_group_raid_win(1000, 1000) is True  # ties go to the attacker


def test_roll_player_target_steal_never_exceeds_victim_water():
    for seed in range(50):
        steal = g.roll_player_target_steal(100, rng=random.Random(seed))
        assert steal <= 100


def test_roll_player_target_steal_at_least_120_or_everything():
    # victim has plenty of water -> steal should be around 8-18%, but
    # floored at 120 minimum
    steal = g.roll_player_target_steal(100000, rng=random.Random(1))
    assert steal >= 120
    # victim has very little water -> can't steal more than they have
    steal_poor = g.roll_player_target_steal(50, rng=random.Random(1))
    assert steal_poor <= 50


def test_split_group_raid_reward_each_gets_at_least_1():
    each, vault_add = g.split_group_raid_reward(gross=10, member_count=20)
    assert each >= 1


def test_split_group_raid_reward_vault_share():
    each, vault_add = g.split_group_raid_reward(gross=1000, member_count=5, vault_rate=0.45)
    assert vault_add == 450
    assert each == int((1000 - 450) / 5)


def test_roll_group_raid_loss_damage_within_range():
    for seed in range(50):
        dmg = g.roll_group_raid_loss_damage(rng=random.Random(seed))
        assert 8 <= dmg <= 22


def test_rolls_bonus_cache_deterministic():
    a = g.rolls_bonus_cache(0.5, rng=random.Random(1))
    b = g.rolls_bonus_cache(0.5, rng=random.Random(1))
    assert a == b
