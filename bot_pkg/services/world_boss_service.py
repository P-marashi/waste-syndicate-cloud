"""Pure world-boss math extracted from `features/world_boss.py`.

Covers: player power estimate, boss stat scaling (HP/attack based on
player count and average power), the attack/counter-attack damage rolls,
and per-participant reward calculation on boss defeat.

Spawn timing/chance (`maybe_spawn_boss`), the boss lifecycle
(`active_boss`, `finish_boss_if_dead`), and messaging stay in the
handler — those touch `registry.game` state, other players' data, and
multi-player broadcasts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


def boss_power_estimate(total_attack: int, total_defense: int, level: int) -> int:
    """A rough combined-power number used both to estimate a boss's
    difficulty and to size a single attack. Floored at 35 so even a
    fresh level-1 player contributes something.
    """
    return max(
        35,
        int(total_attack) + int(int(total_defense) * 0.25) + int(level) * 35,
    )


@dataclass
class BossScaledStats:
    hp: int
    atk: int
    players: int
    avg_power: int


def scale_boss_stats(
    player_powers: list[int],
    template_atk: int,
    template_reward_mod: float,
    *,
    rng: random.Random | None = None,
) -> BossScaledStats:
    """Scales a boss's HP/attack to the current player pool so it stays
    beatable for a small group but demands real coordination for a large
    one. Floor/ceiling HP bounds exist so the boss is never trivially
    easy (a couple hits) nor effectively unkillable.
    """
    rng = rng or random.Random()
    player_count = max(1, len(player_powers))
    avg_power = int(sum(player_powers) / player_count) if player_powers else 90

    expected_hits_per_player = 3.8 + min(2.2, player_count / 18)
    difficulty = float(template_reward_mod) * rng.uniform(1.12, 1.38)
    scaled_hp = int(avg_power * player_count * expected_hits_per_player * difficulty)

    floor_hp = int(16000 + player_count * 2600)
    ceiling_hp = int(max(floor_hp, avg_power * player_count * 8.5))
    hp = max(floor_hp, min(scaled_hp, ceiling_hp))

    atk = int(template_atk + min(28, player_count * 0.55) + avg_power / 180)

    return BossScaledStats(hp=hp, atk=max(10, atk), players=player_count, avg_power=avg_power)


def roll_boss_attack_damage(power: float, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return max(25, int(power * rng.uniform(0.8, 1.25)))


def roll_boss_counter_hit(boss_atk: int, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return rng.randint(0, int(boss_atk))


@dataclass
class BossReward:
    water: int = 0
    battery: int = 0
    copper: int = 0
    bonus_loot_caches: int = 0
    big_hitter: bool = False


def compute_boss_reward(
    rank: int, damage: int, total_damage: int, reward_mod: float
) -> BossReward:
    """Per-participant reward on boss defeat: a damage-share cut of a
    fixed pool, plus flat bonuses for placing top-3 or having landed a
    single huge hit (>=2000 damage — the original tracks this off the
    same cumulative `damage` value passed in here, not a separate
    per-hit max; ported as-is).
    """
    water = int((160 + damage / 35) * float(reward_mod))
    battery = 3 if rank <= 3 else 1
    copper = 6 if rank <= 3 else 2
    bonus_caches = 0
    big_hitter = False

    if damage >= 2000:
        water += 450
        bonus_caches += 2
        big_hitter = True

    if rank == 1:
        water += 320
        bonus_caches += 3
    elif rank <= 3:
        water += 180
        bonus_caches += 2

    if total_damage > 0:
        damage_share = damage / total_damage
        water += int(800 * damage_share)

    return BossReward(
        water=water,
        battery=battery,
        copper=copper,
        bonus_loot_caches=bonus_caches,
        big_hitter=big_hitter,
    )
