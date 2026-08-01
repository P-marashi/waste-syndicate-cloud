"""Pure alliance group-raid math extracted from
`features/alliance_group_raid.py`.

Covers: target power/defense scaling (both player and NPC targets), the
group's combined attack roll and win/loss check, reward splitting
between the alliance vault and members, and the loss-damage roll. Target
*selection* (who's a candidate, `random.choice` among the top 5) and all
messaging/state mutation stay in the handler.
"""

from __future__ import annotations

import random


def candidate_target_power(total_defense: int, total_attack: int, level: int) -> int:
    """Used to rank potential player targets — favors defense with a
    partial attack contribution, same shape as raid_target_score but
    tuned differently for "who's worth raiding as a group".
    """
    return int(total_defense) + int(total_attack * 0.45) + int(level) * 90


def roll_player_target_defense(power: int, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return max(900, int(power * rng.uniform(1.05, 1.35)))


def roll_npc_target_defense(cartel_level: int, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return rng.randint(2800, 4600) * max(1, cartel_level)


def roll_npc_target_water(rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return rng.randint(1200, 2600)


def roll_group_attack_power(total_power: int, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return int(total_power * rng.uniform(0.82, 1.18))


def is_group_raid_win(effective_power: int, enemy_defense: int) -> bool:
    return effective_power >= enemy_defense


def roll_player_target_steal(victim_water: int, rng: random.Random | None = None) -> int:
    """Never takes more than the victim has, and always at least 120 (or
    everything they have, if less than that).
    """
    rng = rng or random.Random()
    victim_water = int(victim_water)
    return min(victim_water, max(120, int(victim_water * rng.uniform(0.08, 0.18))))


def roll_player_target_gross(
    steal: int, member_count: int, rng: random.Random | None = None
) -> int:
    rng = rng or random.Random()
    return steal + rng.randint(250, 650) + member_count * rng.randint(45, 120)


def roll_npc_target_gross(
    member_count: int, cartel_level: int, rng: random.Random | None = None
) -> int:
    rng = rng or random.Random()
    return (
        rng.randint(700, 1400)
        + member_count * rng.randint(90, 180)
        + cartel_level * 260
    )


def split_group_raid_reward(
    gross: int, member_count: int, vault_rate: float = 0.45
) -> tuple[int, int]:
    """Returns (each_member_share, vault_add). Unlike alliance income
    sharing (`alliance_service.distribute_pool`), any integer-division
    remainder here is simply lost (floored), not returned to the vault —
    ported as-is from the original, which didn't account for it either.
    """
    vault_add = int(gross * vault_rate)
    each = max(1, int((gross - vault_add) / max(1, member_count)))
    return each, vault_add


def roll_group_raid_loss_damage(rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    return rng.randint(8, 22)


def rolls_bonus_cache(chance: float = 0.08, rng: random.Random | None = None) -> bool:
    rng = rng or random.Random()
    return rng.random() < chance
