"""Pure daily-reward-streak and leaderboard-ranking math extracted from
`s19_h_misc.py`.
"""

from __future__ import annotations

from typing import Any


def next_daily_streak(previous_streak: int, last_claim_key: str | None, yesterday_key: str) -> int:
    """Streak continues (+1) only if the last claim was exactly yesterday;
    otherwise it resets to 1 (this claim). A `last_claim_key` of None
    (never claimed before) also resets to 1.
    """
    if last_claim_key == yesterday_key:
        return int(previous_streak) + 1
    return 1


def compute_daily_reward(streak: int) -> dict[str, int]:
    """Daily reward scales with streak, each resource capped so long
    streaks don't spiral: water +10/day up to +200, scrap/plastic +2/day
    up to +50/+40, and a bonus battery every 3rd day. `battery` is
    included even when 0 — the caller decides whether to show it.
    """
    return {
        "water": 60 + min(200, streak * 10),
        "scrap": 10 + min(50, streak * 2),
        "plastic": 8 + min(40, streak * 2),
        "battery": 1 if streak % 3 == 0 else 0,
    }


def find_leaderboard_rank(
    chat_id: str, ranked_rows: list[tuple[str, int]]
) -> tuple[int, int] | None:
    """`ranked_rows` is a list of (chat_id, score) already sorted by rank.
    Returns (1-based rank, score) for `chat_id`, or None if not present.
    """
    for i, (cid, score) in enumerate(ranked_rows, start=1):
        if cid == chat_id:
            return i, score
    return None
