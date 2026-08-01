import random

from ..registry import registry
from ..services import cache_service


def maybe_award_legendary(chat_id: str, source: str, chance: float = 0.006) -> str:
    if random.random() > chance:
        return ""
    p = registry.get_player(chat_id)
    key, item = random.choice(list(registry.LEGENDARY_ITEMS.items()))
    p.setdefault("inventory", {})[key] = int(p.get("inventory", {}).get(key, 0)) + 1
    p.setdefault("stats", {})["legendary_found"] = (
        p.get("stats", {}).get("legendary_found", 0) + 1
    )
    registry.recalc_power(p)
    text = registry.T("cache.legendary", label=item["label"], source=source)
    registry.add_news(
        f"✨ {registry.player_name(chat_id)} از {source} آیتم افسانه‌ای پیدا کرد: {item['label']}",
        important=True,
    )
    return text


registry.maybe_award_legendary = maybe_award_legendary


def maybe_find_cache(chat_id: str, zone_key: str) -> str:
    if not cache_service.rolls_cache_find(zone_key):
        return ""
    p = registry.get_player(chat_id)
    p["loot_caches"] = int(p.get("loot_caches", 0)) + 1
    registry.add_news(
        f"🎁 {registry.player_name(chat_id)} در گشت‌زنی یک صندوق شانسی پیدا کرد."
    )
    return registry.T("cache.found", count=p["loot_caches"])


registry.maybe_find_cache = maybe_find_cache


def handle_open_cache(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    if int(p.get("loot_caches", 0)) <= 0:
        registry.send(
            chat_id, registry.T("cache.no_cache"), keypad=registry.main_keypad(chat_id)
        )
        return
    p["loot_caches"] = int(p.get("loot_caches", 0)) - 1
    p.setdefault("stats", {})["caches_opened"] = (
        p.get("stats", {}).get("caches_opened", 0) + 1
    )
    registry.inc_mission(chat_id, "open_cache", 1)
    outcome = cache_service.roll_cache_outcome()
    lines = []
    if outcome.kind == "trap":
        p["hp"] = max(1, int(p.get("hp", 100)) - outcome.damage)
        lines.append(f"💥 صندوق تله داشت! جان نیروها -{outcome.damage} شد.")
    elif outcome.kind == "water_small":
        p["water"] = int(p.get("water", 0)) + outcome.water
        lines.append(f"💧 آب × {outcome.water}")
    elif outcome.kind in ("resources_common", "resources_rare"):
        for r, q in outcome.resources.items():
            p["resources"][r] = p["resources"].get(r, 0) + q
        lines.append(registry.fmt_res_lines(outcome.resources))
    elif outcome.kind == "water_big":
        p["water"] = int(p.get("water", 0)) + outcome.water
        p["loot_caches"] = int(p.get("loot_caches", 0)) + (1 if outcome.bonus_cache else 0)
        lines.append(f"💎 صندوق پرارزش بود! 💧 آب × {outcome.water}")
    else:
        legendary = registry.maybe_award_legendary(chat_id, "صندوق شانسی", chance=1.0)
        lines.append(legendary or "✨ رد یک آیتم افسانه‌ای دیدی، اما دستت بهش نرسید.")
    registry.save_game()
    registry.send(
        chat_id,
        registry.T(
            "cache.opened", result="\n".join(lines), left=p.get("loot_caches", 0)
        ),
        keypad=registry.make_keypad(
            [[registry.B("open_cache")], [registry.B("main_menu")]]
        ),
    )


registry.handle_open_cache = handle_open_cache
