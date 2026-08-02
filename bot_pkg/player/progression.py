from typing import Any

from ..registry import registry
from ..services import player_service


def honor_title(honor: int) -> str:
    return player_service.honor_title(honor, registry.HONOR_TITLES)


def level_info(p: dict[str, Any]) -> tuple[int, int, int, str]:
    return player_service.level_info(int(p.get("level", 1)), int(p.get("xp", 0)), registry.LEVELS)


def add_xp(p: dict[str, Any], amount: int) -> bool:
    new_level, new_xp, leveled = player_service.apply_xp(
        int(p["level"]),
        int(p.get("xp", 0)),
        amount,
        registry.LEVELS,
        xp_multiplier=registry.event_mod("xp", 1.0),
    )
    p["level"] = new_level
    p["xp"] = new_xp
    return leveled
