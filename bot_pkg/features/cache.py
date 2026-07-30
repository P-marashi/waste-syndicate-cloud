import random

from ..registry import registry


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
    chances = {"alley": 0.01, "suburb": 0.015, "center": 0.025, "bunker": 0.04}
    if random.random() > chances.get(zone_key, 0.015):
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
    roll = random.randint(1, 10000)
    lines = []
    if roll <= 800:
        damage = random.randint(5, 18)
        p["hp"] = max(1, int(p.get("hp", 100)) - damage)
        lines.append(f"💥 صندوق تله داشت! جان نیروها -{damage} شد.")
    elif roll <= 5200:
        water = random.randint(70, 210)
        p["water"] = int(p.get("water", 0)) + water
        lines.append(f"💧 آب × {water}")
    elif roll <= 8500:
        loot = {
            "scrap": random.randint(8, 24),
            "plastic": random.randint(6, 20),
            "glass": random.randint(3, 12),
        }
        for r, q in loot.items():
            p["resources"][r] = p["resources"].get(r, 0) + q
        lines.append(registry.fmt_res_lines(loot))
    elif roll <= 9700:
        loot = {"battery": random.randint(1, 3), "copper": random.randint(2, 6)}
        for r, q in loot.items():
            p["resources"][r] = p["resources"].get(r, 0) + q
        lines.append(registry.fmt_res_lines(loot))
    elif roll <= 9980:
        water = random.randint(260, 520)
        p["water"] = int(p.get("water", 0)) + water
        p["loot_caches"] = int(p.get("loot_caches", 0)) + (
            1 if random.random() < 0.2 else 0
        )
        lines.append(f"💎 صندوق پرارزش بود! 💧 آب × {water}")
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
