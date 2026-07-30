from typing import Any

from ..registry import registry


def honor_title(honor: int) -> str:
    for lo, hi, title in registry.HONOR_TITLES:
        if lo <= honor <= hi:
            return title

    return "ناشناخته"


def level_info(
    p: dict[str, Any],
) -> tuple[int, int, int, str]:
    lv = int(p.get("level", 1))
    xp = int(p.get("xp", 0))

    max_xp = registry.LEVELS.get(lv, {}).get("xp", 9999)
    label = registry.LEVELS.get(lv, {}).get("label", "؟")

    return (
        lv,
        xp,
        max_xp,
        label,
    )


def add_xp(
    p: dict[str, Any],
    amount: int,
) -> bool:
    amount = int(amount * registry.event_mod("xp", 1.0))

    p["xp"] = int(p.get("xp", 0)) + amount

    leveled = False

    while p["level"] < 10:
        max_xp = registry.LEVELS.get(
            p["level"],
            {},
        ).get("xp", 9999)

        if p["xp"] < max_xp:
            break

        p["xp"] -= max_xp
        p["level"] += 1
        leveled = True

    return leveled
