from typing import Any

from ..registry import registry
from .combat import recalc_power


def apply_building_bonuses(
    p: dict[str, Any],
) -> None:
    """
    اعمال تمام بونوس‌های ساختمان‌ها روی پلیر.
    """

    buildings = p.get("buildings", {})

    purifier_lv = int(buildings.get("purifier", 0))
    if purifier_lv > 0:
        p.setdefault(
            "_purifier_bonus",
            registry.BUILDINGS["purifier"]["levels"]
            .get(purifier_lv, {})
            .get("prod", 0),
        )

    lab_lv = int(buildings.get("lab", 0))
    p["_craft_discount"] = (
        registry.BUILDINGS["lab"]["levels"].get(lab_lv, {}).get("discount", 0)
        if lab_lv > 0
        else 0
    )

    stall_lv = int(buildings.get("market_stall", 0))
    p["_market_fee_cut"] = (
        registry.BUILDINGS["market_stall"]["levels"].get(stall_lv, {}).get("fee_cut", 0)
        if stall_lv > 0
        else 0
    )


def finish_upgrades(
    p: dict[str, Any],
) -> list[dict[str, Any]]:
    finished = []
    remaining = []

    for upgrade in p.get("upgrades_in_progress", []):
        if (
            registry.fromiso(
                upgrade.get("finish"),
                registry.now(),
            )
            <= registry.now()
        ):
            building = upgrade.get("bldg")
            level = int(upgrade.get("to_level", 1))

            if building in registry.BUILDINGS:
                p.setdefault("buildings", {})[building] = level

                finished.append(upgrade)

        else:
            remaining.append(upgrade)

    p["upgrades_in_progress"] = remaining

    recalc_power(p)
    apply_building_bonuses(p)
    recalc_power(p)

    return finished


def upgrade_in_progress(
    p: dict[str, Any],
    building_key: str,
) -> float | None:
    for upgrade in p.get(
        "upgrades_in_progress",
        [],
    ):
        if upgrade.get("bldg") != building_key:
            continue

        return max(
            0,
            (
                registry.fromiso(
                    upgrade.get("finish"),
                    registry.now(),
                )
                - registry.now()
            ).total_seconds(),
        )

    return None
