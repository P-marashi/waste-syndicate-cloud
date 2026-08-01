"""Pure season-score math extracted from `features/season.py`.

Covers the four-way score breakdown (combat/economy/progress/honor) used
for the leaderboard and season-end rankings. Doesn't cover
`maybe_roll_season()` (the actual season-reset flow) — that's pure
orchestration: resetting every player, archiving winners, messaging
everyone. Low pure-math value, high risk to touch.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SeasonScoreInputs:
    total_attack: int = 0
    total_defense: int = 0
    raids_done: int = 0
    boss_damage: int = 0

    water: int = 0
    resource_value: int = 0  # sum(qty * reference_price) across all resources
    market_sales: int = 0
    alliance_shared: int = 0

    cartel_score_bonus: int = 0
    level: int = 1
    xp: int = 0
    building_levels: int = 0  # sum of all building levels
    scavenge_success: int = 0
    missions_completed: int = 0
    season_points_bonus: int = 0

    honor: int = 0


def compute_combat_score(inputs: SeasonScoreInputs) -> int:
    atk = int(inputs.total_attack)
    dfc = int(inputs.total_defense)
    balanced_power_bonus = min(atk, dfc) * 0.45
    return int(
        atk * 1.45
        + dfc * 1.25
        + balanced_power_bonus
        + int(inputs.raids_done) * 180
        + int(inputs.boss_damage) * 0.08
    )


def compute_economy_score(inputs: SeasonScoreInputs) -> int:
    return int(
        int(inputs.water) * 1.1
        + int(inputs.resource_value) * 0.28
        + int(inputs.market_sales) * 90
        + int(inputs.alliance_shared) * 70
    )


def compute_progress_score(inputs: SeasonScoreInputs) -> int:
    return int(
        int(inputs.cartel_score_bonus) * 1.2
        + int(inputs.level) * 950
        + int(inputs.xp) * 18
        + int(inputs.building_levels) * 420
        + int(inputs.scavenge_success) * 65
        + int(inputs.raids_done) * 95
        + int(inputs.missions_completed) * 180
        + int(inputs.season_points_bonus) * 1.4
    )


def compute_honor_score(inputs: SeasonScoreInputs) -> float:
    """NOT int-cast, unlike the other three components — matches the
    original exactly (e.g. honor=7 -> 45.5, not 45). Rounding this would
    silently shave points off every player's score.
    """
    return int(inputs.honor) * 6.5


def season_score_breakdown(inputs: SeasonScoreInputs) -> dict[str, float]:
    combat = compute_combat_score(inputs)
    economy = compute_economy_score(inputs)
    progress = compute_progress_score(inputs)
    honor = compute_honor_score(inputs)
    total = max(0, combat + economy + progress + honor)
    return {
        "combat": combat,
        "economy": economy,
        "progress": progress,
        "honor": honor,
        "total": total,
    }


def split_time_left(total_seconds: float) -> tuple[int, int, int]:
    """Returns (days, hours, minutes) for a countdown, floored at 0."""
    seconds = max(0, int(total_seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    return days, hours, minutes
