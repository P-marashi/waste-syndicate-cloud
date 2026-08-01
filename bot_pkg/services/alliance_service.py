"""Pure alliance economy math extracted from `s09_alliance_economy.py`.

Covers: cartel level lookups/clamping, the water tax/bonus split an
individual player's income goes through, and how a shared pool gets
divided among alliance members (the trickiest part — integer division
with a remainder that has to go somewhere, and an edge case when there
are no other members to share with).

Member lookup, `registry.game` mutation, logging, and text formatting
(`alliance.share_note`, etc.) stay in the handler.
"""

from __future__ import annotations

from typing import Any


def cartel_level(raw_level: int, max_level: int) -> int:
    """Clamps to [1, max_level] — an alliance always has at least level 1,
    even if `raw_level` is missing/zero/negative.
    """
    return max(1, min(max_level, int(raw_level)))


def cartel_level_data(level: int, cartel_levels: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Looks up the perk table for `level`, falling back to level 1's
    data if the level isn't in the table (shouldn't normally happen once
    `cartel_level` has clamped it, but matches the original's defensive
    `.get(level, cartel_levels[1])`).
    """
    return cartel_levels.get(level, cartel_levels[1])


def cartel_next_upgrade_cost(
    level: int, max_level: int, cartel_levels: dict[int, dict[str, Any]]
) -> int:
    """0 means already maxed out."""
    if level >= max_level:
        return 0
    return int(cartel_levels[level + 1]["upgrade_cost"])


def split_water_tax(gross: int, tax_rate: float, bonus_rate: float) -> tuple[int, int, int]:
    """When a player in an alliance earns water, some gets taxed to the
    alliance pool (`tax_rate`) and the alliance kicks in a bonus on top
    (`bonus_rate`, funded by the game, not the player). Returns
    (net_to_player, tax_amount, bonus_amount) — `tax_amount + bonus_amount`
    is the pool that then gets divided among members via
    `distribute_pool`.
    """
    gross = max(0, int(gross))
    tax = int(gross * tax_rate)
    bonus = int(gross * bonus_rate)
    net = max(0, gross - tax)
    return net, tax, bonus


def distribute_pool(
    pool: int, other_member_count: int, distribute_rate: float
) -> tuple[int, int, int]:
    """Splits a pool between "goes to members now" and "stays in the
    alliance vault". Only `distribute_rate` of the pool is actually handed
    out; the rest goes straight to the vault. What IS handed out gets
    divided evenly among `other_member_count` members (the source player
    excluded) — each member gets at least 1 if anything is being
    distributed at all, and whatever's left over from integer division
    (because `distributed` doesn't divide evenly) falls back to the vault
    too, so nothing is lost.

    Returns (each_member_share, actual_amount_distributed, vault_add).
    If there are no other members, everything goes to the vault.
    """
    if pool <= 0:
        return 0, 0, 0

    if other_member_count <= 0:
        return 0, 0, pool

    distributed = int(pool * distribute_rate)
    each = max(1, distributed // other_member_count) if distributed > 0 else 0
    actual_distributed = each * other_member_count
    vault_add = max(0, pool - distributed) + (distributed - actual_distributed)

    return each, actual_distributed, vault_add
