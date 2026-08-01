"""Scavenge mini-game: risk/chance math, dice roll, and loot table.

Extracted from `s14_h_scavenge.py`, where this logic used to be tangled
together with `registry.send(...)`, `registry.T(...)`, and `save_game()`
calls inside `handle_scavenge`. Everything here is a pure function over
plain dicts — no registry, no I/O — so it can be unit-tested directly
(see tests/test_scavenge_service.py) instead of only being exercisable by
clicking through the bot.

The handler is still responsible for: reading/saving the player,
cooldowns, XP/leveling (`add_xp` lives in player/progression.py and isn't
touched in this pass), cache/legendary rolls, mission progress, and
formatting the outgoing message.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

LOOT_POOL = ("scrap", "plastic", "glass", "battery", "copper")

# Index into LOOT_POOL: battery=3, copper=4 are the "rare" resources that
# world events can boost via `rare_loot_multiplier`.
_RARE_INDEXES = (3, 4)

LOOT_WEIGHTS: dict[str, list[int]] = {
    "alley": [42, 35, 18, 3, 2],
    "suburb": [30, 28, 24, 10, 8],
    "center": [22, 20, 24, 18, 16],
    "bunker": [15, 15, 20, 25, 25],
}


@dataclass
class ScavengeOutcome:
    """Result of one scavenge attempt. Immutable record of what happened —
    turning this into resource/HP changes on a player is a separate step
    (`apply_success` / `apply_failure`) so the roll itself stays trivially
    testable without a player object at all.
    """

    zone_key: str
    success: bool
    chance: int
    roll: int
    risk: int
    cooldown_seconds: int
    loot: dict[str, int] = field(default_factory=dict)
    damage: int = 0


def compute_chance(zone: dict[str, Any], risk_modifier: int = 0) -> tuple[int, int]:
    """Returns (effective_risk, success_chance_percent)."""
    risk = max(0, zone["risk"] + int(risk_modifier))
    chance = max(5, min(95, 100 - risk * 12))
    return risk, chance


def roll_scavenge(
    zone_key: str,
    zone: dict[str, Any],
    *,
    risk_modifier: int = 0,
    loot_multiplier: float = 1.0,
    rare_loot_multiplier: float = 1.0,
    rng: random.Random | None = None,
) -> ScavengeOutcome:
    """Roll a single scavenge attempt against `zone`. Deterministic given
    the same `rng` — pass a seeded `random.Random(seed)` in tests.
    """
    rng = rng or random.Random()
    risk, chance = compute_chance(zone, risk_modifier)
    roll = rng.randint(1, 100)
    cooldown_seconds = zone["cd_min"] * 60

    if roll <= chance:
        total = rng.randint(zone["loot_min"], zone["loot_max"])
        total = int(total * loot_multiplier)

        weights = list(LOOT_WEIGHTS[zone_key])
        for idx in _RARE_INDEXES:
            weights[idx] = int(weights[idx] * rare_loot_multiplier)

        loot: dict[str, int] = {}
        for _ in range(total):
            resource = rng.choices(LOOT_POOL, weights=weights)[0]
            loot[resource] = loot.get(resource, 0) + 1

        return ScavengeOutcome(
            zone_key=zone_key,
            success=True,
            chance=chance,
            roll=roll,
            risk=risk,
            cooldown_seconds=cooldown_seconds,
            loot=loot,
        )

    damage = rng.randint(5, 20 + risk * 3)
    return ScavengeOutcome(
        zone_key=zone_key,
        success=False,
        chance=chance,
        roll=roll,
        risk=risk,
        cooldown_seconds=cooldown_seconds,
        damage=damage,
    )


def apply_success(player: dict[str, Any], outcome: ScavengeOutcome) -> None:
    """Mutate `player` for a successful scavenge: add loot, bump stats.
    Does NOT touch XP/level (still `registry.add_xp`) or cooldown (still
    `registry.set_cd`) — those stay in the handler for now.
    """
    if not outcome.success:
        raise ValueError("apply_success called with a failed outcome")

    stats = player.setdefault("stats", {})
    stats["scavenges"] = stats.get("scavenges", 0) + 1
    stats["scavenge_success"] = stats.get("scavenge_success", 0) + 1

    resources = player.setdefault("resources", {})
    for resource, qty in outcome.loot.items():
        resources[resource] = resources.get(resource, 0) + qty


def apply_failure(
    player: dict[str, Any],
    outcome: ScavengeOutcome,
    rng: random.Random | None = None,
) -> dict[str, int]:
    """Mutate `player` for a failed scavenge: apply damage, lose some
    resources (up to 3 of each currently-held resource, at random).
    Returns what was lost so the handler can format a message from it —
    matches the old inline behavior in `handle_scavenge`.
    """
    if outcome.success:
        raise ValueError("apply_failure called with a successful outcome")

    rng = rng or random.Random()

    stats = player.setdefault("stats", {})
    stats["scavenges"] = stats.get("scavenges", 0) + 1

    player["hp"] = max(1, player.get("hp", 100) - outcome.damage)

    lost: dict[str, int] = {}
    resources = player.setdefault("resources", {})
    for resource in LOOT_POOL:
        have = resources.get(resource, 0)
        if have > 0:
            qty = rng.randint(0, min(3, have))
            if qty:
                resources[resource] -= qty
                lost[resource] = qty

    return lost
