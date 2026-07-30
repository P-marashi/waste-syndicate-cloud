from ..registry import registry


def passive_income(
    chat_id: str,
) -> int:
    p = registry.game["players"][chat_id]

    current = registry.now()
    last = registry.fromiso(
        p.get("last_passive"),
        current,
    )

    elapsed = max(
        0,
        (current - last).total_seconds(),
    )

    p["last_passive"] = registry.iso(current)

    purifier_level = int(
        p.get("buildings", {}).get(
            "purifier",
            0,
        )
    )

    if purifier_level <= 0:
        return 0

    rate = (
        registry.BUILDINGS["purifier"]["levels"].get(purifier_level, {}).get("prod", 0)
    )

    rate *= registry.event_mod(
        "passive_water",
        1.0,
    )

    rate *= 1.0 + registry.cartel_water_bonus(chat_id)

    earned = int(elapsed * rate / 3600)

    if earned > 0:
        registry.award_water(
            chat_id,
            earned,
            "passive_income",
            alliance_share=True,
        )

    return earned
