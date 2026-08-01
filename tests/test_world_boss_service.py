import random

from bot_pkg.services import world_boss_service as w


def test_boss_power_estimate_floors_at_35():
    assert w.boss_power_estimate(0, 0, 1) >= 35


def test_boss_power_estimate_scales_with_level():
    low = w.boss_power_estimate(100, 100, 1)
    high = w.boss_power_estimate(100, 100, 20)
    assert high > low


def test_scale_boss_stats_empty_player_pool_uses_default_avg_power():
    stats = w.scale_boss_stats([], template_atk=14, template_reward_mod=1.0, rng=random.Random(1))
    assert stats.avg_power == 90
    assert stats.players == 1  # floored at 1 even with no players


def test_scale_boss_stats_hp_never_below_floor():
    stats = w.scale_boss_stats([50], template_atk=14, template_reward_mod=1.0, rng=random.Random(1))
    floor_hp = int(16000 + stats.players * 2600)
    assert stats.hp >= floor_hp


def test_scale_boss_stats_hp_grows_with_more_players():
    small = w.scale_boss_stats([1000] * 3, 14, 1.0, rng=random.Random(1))
    large = w.scale_boss_stats([1000] * 30, 14, 1.0, rng=random.Random(1))
    assert large.hp > small.hp


def test_scale_boss_stats_atk_floors_at_10():
    stats = w.scale_boss_stats([0], template_atk=0, template_reward_mod=1.0, rng=random.Random(1))
    assert stats.atk >= 10


def test_roll_boss_attack_damage_floors_at_25():
    damage = w.roll_boss_attack_damage(power=0, rng=random.Random(1))
    assert damage >= 25


def test_roll_boss_attack_damage_deterministic():
    a = w.roll_boss_attack_damage(1000, rng=random.Random(5))
    b = w.roll_boss_attack_damage(1000, rng=random.Random(5))
    assert a == b


def test_roll_boss_counter_hit_within_range():
    for seed in range(20):
        hit = w.roll_boss_counter_hit(50, rng=random.Random(seed))
        assert 0 <= hit <= 50


def test_compute_boss_reward_top_rank_gets_more():
    total_damage = 1000
    first = w.compute_boss_reward(rank=1, damage=200, total_damage=total_damage, reward_mod=1.0)
    fourth = w.compute_boss_reward(rank=4, damage=200, total_damage=total_damage, reward_mod=1.0)
    assert first.water > fourth.water
    assert first.bonus_loot_caches > fourth.bonus_loot_caches


def test_compute_boss_reward_big_hit_bonus():
    reward = w.compute_boss_reward(rank=5, damage=2000, total_damage=5000, reward_mod=1.0)
    assert reward.big_hitter is True
    assert reward.bonus_loot_caches >= 2


def test_compute_boss_reward_no_big_hit_below_threshold():
    reward = w.compute_boss_reward(rank=5, damage=1999, total_damage=5000, reward_mod=1.0)
    assert reward.big_hitter is False


def test_compute_boss_reward_zero_total_damage_no_crash():
    reward = w.compute_boss_reward(rank=1, damage=0, total_damage=0, reward_mod=1.0)
    assert reward.water >= 0
