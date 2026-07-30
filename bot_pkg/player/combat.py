from typing import Any

from ..registry import registry


def recalc_power(
    p: dict[str, Any],
) -> None:
    atk = 0
    dfc = 0

    for bk, lv in p.get("buildings", {}).items():
        if lv > 0 and bk in registry.BUILDINGS:
            data = registry.BUILDINGS[bk]["levels"].get(
                int(lv),
                {},
            )

            atk += data.get("atk", 0)
            dfc += data.get("def", 0)

    for ik, qty in p.get("inventory", {}).items():
        item = registry.CRAFT_ITEMS.get(ik) or registry.LEGENDARY_ITEMS.get(ik)

        if item and qty > 0:
            atk += item.get("atk", 0) * qty * 1.12
            dfc += item.get("def", 0) * qty * 1.05

    p["total_attack"] = int(atk)
    p["total_defense"] = int(dfc)


def shield_remaining(
    p: dict[str, Any],
) -> float:
    if not p.get("shield_until"):
        return 0

    return max(
        0,
        (
            registry.fromiso(
                p["shield_until"],
                registry.now(),
            )
            - registry.now()
        ).total_seconds(),
    )


def is_shielded(
    p: dict[str, Any],
) -> bool:
    return shield_remaining(p) > 0


def base_status_label(
    p: dict[str, Any],
) -> str:
    dfc = int(p.get("total_defense", 0))

    if dfc == 0:
        return "ابتدایی 🏚️"

    if dfc < 1000:
        return "ضعیف 🪵"

    if dfc < 5000:
        return "متوسط 🧱"

    if dfc < 15000:
        return "قوی 🔩"

    if dfc < 40000:
        return "سنگر ☠️"

    return "بنکر افسانه‌ای 🏯"
