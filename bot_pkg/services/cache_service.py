"""Pure loot-cache math extracted from `features/cache.py`.

Covers: the chance a scavenge zone drops a lucky cache, and the weighted
outcome table for opening one (trap / small water / common resources /
rare resources / big water / legendary). Legendary item *selection*
(`maybe_award_legendary` picking which item from `LEGENDARY_ITEMS`) stays
in the handler — that's a config-table lookup, not math.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

CACHE_FIND_CHANCES: dict[str, float] = {
    "alley": 0.01,
    "suburb": 0.015,
    "center": 0.025,
    "bunker": 0.04,
}
DEFAULT_CACHE_FIND_CHANCE = 0.015


def cache_find_chance(zone_key: str) -> float:
    return CACHE_FIND_CHANCES.get(zone_key, DEFAULT_CACHE_FIND_CHANCE)


def rolls_cache_find(zone_key: str, rng: random.Random | None = None) -> bool:
    rng = rng or random.Random()
    return rng.random() <= cache_find_chance(zone_key)


@dataclass
class CacheOutcome:
    kind: str  # trap | water_small | resources_common | resources_rare | water_big | legendary
    damage: int = 0
    water: int = 0
    resources: dict[str, int] = field(default_factory=dict)
    bonus_cache: bool = False


def roll_cache_outcome(rng: random.Random | None = None) -> CacheOutcome:
    """The weighted table behind opening a loot cache. Cumulative
    thresholds out of 10000: trap 8%, small water 44%, common resources
    33%, rare resources 12%, big water (with a 20% chance of a bonus
    cache) 2.8%, legendary 0.2%.
    """
    rng = rng or random.Random()
    roll = rng.randint(1, 10000)

    if roll <= 800:
        return CacheOutcome(kind="trap", damage=rng.randint(5, 18))

    if roll <= 5200:
        return CacheOutcome(kind="water_small", water=rng.randint(70, 210))

    if roll <= 8500:
        resources = {
            "scrap": rng.randint(8, 24),
            "plastic": rng.randint(6, 20),
            "glass": rng.randint(3, 12),
        }
        return CacheOutcome(kind="resources_common", resources=resources)

    if roll <= 9700:
        resources = {"battery": rng.randint(1, 3), "copper": rng.randint(2, 6)}
        return CacheOutcome(kind="resources_rare", resources=resources)

    if roll <= 9980:
        return CacheOutcome(
            kind="water_big",
            water=rng.randint(260, 520),
            bonus_cache=rng.random() < 0.2,
        )

    return CacheOutcome(kind="legendary")
