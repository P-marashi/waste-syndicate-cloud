from ..registry import registry
from ..services import player_service
from ..utils.datetime import fromiso, iso, now


def passive_income(chat_id: str) -> int:
    p = registry.game["players"][chat_id]

    current = now()
    last = fromiso(p.get("last_passive"), current)
    elapsed = max(0.0, (current - last).total_seconds())

    p["last_passive"] = iso(current)

    purifier_level = int(p.get("buildings", {}).get("purifier", 0))

    earned = player_service.compute_passive_water(
        elapsed,
        purifier_level,
        buildings_table=registry.BUILDINGS,
        event_mod=registry.event_mod("passive_water", 1.0),
        cartel_bonus=registry.cartel_water_bonus(chat_id),
    )

    if earned > 0:
        registry.award_water(chat_id, earned, "passive_income", alliance_share=True)

    return earned
