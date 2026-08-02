from typing import Any

from ..registry import registry
from ..services import player_service
from ..utils.datetime import fromiso, now
from .combat import recalc_power


def apply_building_bonuses(p: dict[str, Any]) -> None:
    """اعمال تمام بونوس‌های ساختمان‌ها روی پلیر."""
    buildings = p.get("buildings", {})

    purifier_lv = int(buildings.get("purifier", 0))
    if purifier_lv > 0:
        p.setdefault(
            "_purifier_bonus",
            player_service.purifier_production_rate(purifier_lv, registry.BUILDINGS),
        )

    lab_lv = int(buildings.get("lab", 0))
    p["_craft_discount"] = player_service.lab_craft_discount(lab_lv, registry.BUILDINGS)

    stall_lv = int(buildings.get("market_stall", 0))
    p["_market_fee_cut"] = player_service.market_stall_fee_cut(stall_lv, registry.BUILDINGS)


def finish_upgrades(p: dict[str, Any]) -> list[dict[str, Any]]:
    finished, remaining, new_levels = player_service.resolve_finished_upgrades(
        p.get("upgrades_in_progress", []),
        buildings_table=registry.BUILDINGS,
        now=now(),
        fromiso=fromiso,
    )

    for building, level in new_levels.items():
        p.setdefault("buildings", {})[building] = level

    p["upgrades_in_progress"] = remaining

    recalc_power(p)
    apply_building_bonuses(p)
    recalc_power(p)

    return finished


def upgrade_in_progress(p: dict[str, Any], building_key: str) -> float | None:
    current = now()
    for upgrade in p.get("upgrades_in_progress", []):
        if upgrade.get("bldg") != building_key:
            continue
        return player_service.seconds_until(fromiso(upgrade.get("finish"), current), current)
    return None
