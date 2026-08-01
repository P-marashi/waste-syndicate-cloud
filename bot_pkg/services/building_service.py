"""Pure buildings/crafting math extracted from `s16_h_buildings_craft.py`.

The original handler had the same "apply lab discount to a cost dict"
logic written out inline three separate times (building-detail preview,
building upgrade, and craft cost) with slightly different rules each
time. Consolidating it here also fixes the duplication, not just the
registry coupling.
"""

from __future__ import annotations

from typing import Any


def apply_discount(cost: dict[str, int], discount_rate: float) -> dict[str, int]:
    """Applies a discount rate to every quantity in `cost`, flooring each
    at 1 (a discount can never make something free). `discount_rate` of 0
    returns a plain copy, unchanged.
    """
    if not discount_rate:
        return dict(cost)
    return {
        resource: max(1, int(qty * (1 - discount_rate)))
        for resource, qty in cost.items()
    }


def lab_discount_rate(
    buildings: dict[str, int],
    lab_levels: dict[int, dict[str, Any]],
    *,
    exclude_key: str | None = None,
) -> float:
    """The lab's own discount rate for upgrading/crafting things — 0 if
    the lab isn't built, and 0 for the lab's *own* upgrade (matches the
    original `if lab_lv and bk != "lab"` rule: the lab doesn't discount
    itself).
    """
    lab_level = int(buildings.get("lab", 0))
    if not lab_level or lab_level not in lab_levels:
        return 0.0
    if exclude_key == "lab":
        return 0.0
    return lab_levels[lab_level].get("discount", 0.0)


def craft_discount_rate(
    buildings: dict[str, int],
    lab_levels: dict[int, dict[str, Any]],
    *,
    event_discount: float = 0.0,
    cap: float = 0.35,
) -> float:
    """Craft discount = active world-event discount + lab discount,
    capped at `cap` (35% by default). Unlike building upgrades, crafting
    has no "exclude the lab itself" rule — the lab isn't a craftable item.
    """
    rate = event_discount + lab_discount_rate(buildings, lab_levels)
    return min(cap, rate)


def compute_heal(
    current_hp: int,
    heal_amount: int,
    *,
    heal_bonus: int = 0,
    max_hp: int = 100,
) -> tuple[int, int]:
    """Returns (actual_heal_applied, new_hp) — heal never overshoots max_hp."""
    heal = min(max_hp - current_hp, heal_amount + heal_bonus)
    heal = max(0, heal)
    return heal, min(max_hp, current_hp + heal)


def halve_remaining_seconds(remaining_seconds: float) -> float:
    """A repair kit cuts remaining upgrade time in half."""
    return remaining_seconds * 0.5
