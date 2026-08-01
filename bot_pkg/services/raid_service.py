"""Pure raid combat math extracted from `s17_h_raid_shield.py`.

Covers: target scoring, weak/medium/strong bucket splitting, the
attack/defense dice rolls, and the resource-loot-rate calculation. Does
NOT cover the full `handle_raid` flow — that also touches alliance
sharing (`award_water`), EMP/temp-defense modifiers that depend on other
players' state and the current time, drone/inventory consumption,
mission tracking, and multi-player messaging. Those stay in the handler.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

LOOT_RATES: dict[str, float] = {
    "water": 0.135,
    "scrap": 0.09,
    "plastic": 0.08,
    "glass": 0.07,
    "battery": 0.06,
    "copper": 0.05,
}


# ---------------------------------------------------------------------
# Targeting
# ---------------------------------------------------------------------


def raid_target_score(
    water: int, total_defense: int, total_attack: int, level: int
) -> int:
    """Higher score = tougher/richer target. Used to rank raid candidates
    and split them into weak/medium/strong buckets.
    """
    return (
        int(water)
        + int(total_defense) * 2
        + int(total_attack) * 2
        + int(level) * 120
    )


def bucket_slice(candidates: list[Any], bucket_key: str) -> list[Any]:
    """`candidates` must already be sorted ascending by `raid_target_score`.
    Splits into three roughly-equal thirds; falls back to the full list
    (or last third) if a bucket would otherwise come up empty, matching
    the original handler's behavior for small player counts.
    """
    if len(candidates) <= 2:
        return candidates

    third = max(1, (len(candidates) + 2) // 3)

    if bucket_key == "weak":
        return candidates[:third]
    if bucket_key == "medium":
        return candidates[third : third * 2] or candidates
    if bucket_key == "strong":
        return candidates[third * 2 :] or candidates[-third:]
    return candidates


# ---------------------------------------------------------------------
# Combat rolls
# ---------------------------------------------------------------------


def roll_attack(
    total_attack: int,
    atk_mod: float,
    attacker_level: int,
    rng: random.Random | None = None,
) -> int:
    rng = rng or random.Random()
    atk = int(total_attack * rng.uniform(0.92, 1.28) * atk_mod)
    return int(atk * (1 + attacker_level * 0.028))


def roll_defense(
    total_defense: int,
    defender_level: int,
    rng: random.Random | None = None,
) -> int:
    rng = rng or random.Random()
    defense = int(total_defense * rng.uniform(0.82, 1.18))
    return int(defense * (1 + max(0, defender_level - 4) * 0.04))


# ---------------------------------------------------------------------
# Loot
# ---------------------------------------------------------------------


def resource_loot_amount(current_amount: int, loot_pct_base: float, resource: str) -> int:
    """How much of `resource` gets looted from a target holding
    `current_amount`, given the raid bucket's base loot percentage.
    Never loots more than the target actually has.
    """
    rate = LOOT_RATES.get(resource, 0.05) * loot_pct_base
    current = int(current_amount)
    if current <= 0:
        return 0
    return min(current, int(current * rate))


@dataclass
class RaidLootResult:
    water_looted: int = 0
    resources_looted: dict[str, int] = field(default_factory=dict)


def compute_raid_loot(
    target_water: int,
    target_resources: dict[str, int],
    loot_pct_base: float,
    resource_keys: list[str],
) -> RaidLootResult:
    """Computes everything lootable from a target in one pass — doesn't
    mutate anything, just returns amounts. The handler is responsible
    for actually deducting from the target and crediting the attacker
    (water goes through `award_water` for alliance-sharing first).
    """
    water_looted = resource_loot_amount(target_water, loot_pct_base, "water")

    resources_looted = {}
    for resource in resource_keys:
        amount = resource_loot_amount(
            target_resources.get(resource, 0), loot_pct_base, resource
        )
        if amount > 0:
            resources_looted[resource] = amount

    return RaidLootResult(water_looted=water_looted, resources_looted=resources_looted)
