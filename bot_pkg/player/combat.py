from typing import Any

from ..registry import registry
from ..services import player_service
from ..utils.datetime import fromiso, now


def recalc_power(p: dict[str, Any]) -> None:
    atk, dfc = player_service.compute_power(
        p.get("buildings", {}),
        p.get("inventory", {}),
        buildings_table=registry.BUILDINGS,
        craft_items=registry.CRAFT_ITEMS,
        legendary_items=registry.LEGENDARY_ITEMS,
    )
    p["total_attack"] = atk
    p["total_defense"] = dfc


def shield_remaining(p: dict[str, Any]) -> float:
    if not p.get("shield_until"):
        return 0
    return player_service.seconds_until(fromiso(p["shield_until"], now()), now())


def is_shielded(p: dict[str, Any]) -> bool:
    return shield_remaining(p) > 0


def base_status_label(p: dict[str, Any]) -> str:
    return player_service.status_label_for_defense(int(p.get("total_defense", 0)))
