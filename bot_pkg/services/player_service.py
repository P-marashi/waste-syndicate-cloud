"""Pure player math: combat power, shield/cooldown countdowns, XP
leveling, building-upgrade completion, and passive income.

Extracted from `bot_pkg/player/{combat,cooldowns,buildings,progression,
passive}.py`, where every function took a `p: dict` plus reached into
`registry.BUILDINGS` / `registry.LEVELS` / `registry.now()` /
`registry.fromiso()` directly — so none of it could be unit-tested
without a live `registry.game`. Here the same math takes its game-data
tables and current time as explicit parameters instead.

`bot_pkg/player/*.py` keeps its current public functions (still the
thing `registry`/handlers call) but each one now just pulls the right
table off `registry` and delegates the actual computation here.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------
# Countdown helper — shield, per-action cooldowns, and building
# upgrades all boil down to "seconds until this ISO timestamp",
# previously duplicated three separate times.
# ---------------------------------------------------------------------


def seconds_until(target: datetime | None, now: datetime) -> float:
    """Seconds remaining until `target`, floored at 0. `target=None`
    means "nothing pending" → 0.
    """
    if target is None:
        return 0.0
    return max(0.0, (target - now).total_seconds())


def future_timestamp(now: datetime, seconds: float) -> datetime:
    """`now` plus `seconds`, for setting a new cooldown/shield expiry."""
    return now + timedelta(seconds=int(seconds))


# ---------------------------------------------------------------------
# Combat power
# ---------------------------------------------------------------------


def compute_power(
    buildings: dict[str, int],
    inventory: dict[str, int],
    *,
    buildings_table: dict[str, Any],
    craft_items: dict[str, Any],
    legendary_items: dict[str, Any],
) -> tuple[int, int]:
    """Returns (total_attack, total_defense) from building levels plus
    equipped craft/legendary inventory items.
    """
    atk = 0.0
    dfc = 0.0

    for bk, lv in buildings.items():
        if lv > 0 and bk in buildings_table:
            data = buildings_table[bk]["levels"].get(int(lv), {})
            atk += data.get("atk", 0)
            dfc += data.get("def", 0)

    for ik, qty in inventory.items():
        item = craft_items.get(ik) or legendary_items.get(ik)
        if item and qty > 0:
            atk += item.get("atk", 0) * qty * 1.12
            dfc += item.get("def", 0) * qty * 1.05

    return int(atk), int(dfc)


def status_label_for_defense(defense: int) -> str:
    if defense == 0:
        return "ابتدایی 🏚️"
    if defense < 1000:
        return "ضعیف 🪵"
    if defense < 5000:
        return "متوسط 🧱"
    if defense < 15000:
        return "قوی 🔩"
    if defense < 40000:
        return "سنگر ☠️"
    return "بنکر افسانه‌ای 🏯"


# ---------------------------------------------------------------------
# Progression: XP / level / honor title
# ---------------------------------------------------------------------


def honor_title(honor: int, honor_titles: list[tuple[int, int, str]]) -> str:
    for lo, hi, title in honor_titles:
        if lo <= honor <= hi:
            return title
    return "ناشناخته"


def level_info(
    level: int,
    xp: int,
    levels_table: dict[int, dict[str, Any]],
) -> tuple[int, int, int, str]:
    max_xp = levels_table.get(level, {}).get("xp", 9999)
    label = levels_table.get(level, {}).get("label", "؟")
    return level, xp, max_xp, label


def apply_xp(
    level: int,
    xp: int,
    amount: int,
    levels_table: dict[int, dict[str, Any]],
    *,
    xp_multiplier: float = 1.0,
    max_level: int = 10,
) -> tuple[int, int, bool]:
    """Returns (new_level, new_xp, leveled_up)."""
    xp = int(xp) + int(amount * xp_multiplier)
    leveled = False

    while level < max_level:
        max_xp = levels_table.get(level, {}).get("xp", 9999)
        if xp < max_xp:
            break
        xp -= max_xp
        level += 1
        leveled = True

    return level, xp, leveled


# ---------------------------------------------------------------------
# Buildings: bonuses + upgrade completion
# ---------------------------------------------------------------------


def purifier_production_rate(purifier_level: int, buildings_table: dict[str, Any]) -> int:
    if purifier_level <= 0:
        return 0
    return buildings_table["purifier"]["levels"].get(purifier_level, {}).get("prod", 0)


def lab_craft_discount(lab_level: int, buildings_table: dict[str, Any]) -> float:
    if lab_level <= 0:
        return 0
    return buildings_table["lab"]["levels"].get(lab_level, {}).get("discount", 0)


def market_stall_fee_cut(stall_level: int, buildings_table: dict[str, Any]) -> float:
    if stall_level <= 0:
        return 0
    return buildings_table["market_stall"]["levels"].get(stall_level, {}).get("fee_cut", 0)


def resolve_finished_upgrades(
    upgrades_in_progress: list[dict[str, Any]],
    *,
    buildings_table: dict[str, Any],
    now: datetime,
    fromiso,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Splits `upgrades_in_progress` into (finished, still_remaining),
    plus a `{building_key: new_level}` map of level changes to apply.

    `fromiso` is injected (rather than imported) so callers can pass
    the project's `bot_pkg.utils.datetime.fromiso`, keeping this module
    free of any dependency on `registry`/`bot_pkg` internals.
    """
    finished: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    new_levels: dict[str, int] = {}

    for upgrade in upgrades_in_progress:
        if fromiso(upgrade.get("finish"), now) <= now:
            building = upgrade.get("bldg")
            level = int(upgrade.get("to_level", 1))
            if building in buildings_table:
                new_levels[building] = level
                finished.append(upgrade)
        else:
            remaining.append(upgrade)

    return finished, remaining, new_levels


# ---------------------------------------------------------------------
# Passive income
# ---------------------------------------------------------------------


def compute_passive_water(
    elapsed_seconds: float,
    purifier_level: int,
    *,
    buildings_table: dict[str, Any],
    event_mod: float = 1.0,
    cartel_bonus: float = 0.0,
) -> int:
    """Water earned over `elapsed_seconds`, given the player's purifier
    level and any active world-event / cartel multipliers. 0 if no
    purifier is built yet.
    """
    if purifier_level <= 0:
        return 0

    rate = purifier_production_rate(purifier_level, buildings_table)
    rate *= event_mod
    rate *= 1.0 + cartel_bonus

    return int(elapsed_seconds * rate / 3600)
