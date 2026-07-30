import random
import re
from datetime import datetime, timedelta
from typing import Any

from .registry import registry

registry.CACHE_TYPES = {
    "rusty": {"label": "🎁 صندوق زنگ\u200cزده", "radio": False},
    "medium": {"label": "📦 صندوق متوسط", "radio": False},
    "military": {"label": "🪖 صندوق نظامی", "radio": True},
    "smuggler": {"label": "🕶️ صندوق قاچاقچی", "radio": True},
    "legendary": {"label": "👑 صندوق افسانه\u200cای", "radio": True},
}
registry.CACHE_ORDER = ["rusty", "medium", "military", "smuggler", "legendary"]
registry.CACHE_OPEN_BUTTON = {
    k: f"باز کردن: {v['label']}" for k, v in registry.CACHE_TYPES.items()
}
registry.CONSUMABLE_ITEMS = {
    "small_medkit": {"label": "🩹 کیت پزشکی کوچک", "desc": "استفاده: ❤️ جان +۴۰"},
    "weak_smoke": {
        "label": "🌫️ دودزا ضعیف",
        "desc": "خودکار: شکست گشت را سبک\u200cتر می\u200cکند",
    },
    "alley_map": {
        "label": "🧭 نقشه کوچه",
        "desc": "کلکسیونی/کمک روایی برای گشت\u200cهای امن",
    },
    "small_repair_tool": {
        "label": "🔧 ابزار تعمیر کوچک",
        "desc": "استفاده: ۲۵٪ از زمان ارتقای فعال کم می\u200cکند",
    },
    "emp_weak": {
        "label": "💣 EMP ضعیف",
        "desc": "خودکار در حمله بعدی: دفاع هدف ۱۵٪ کمتر",
    },
    "emp_strong": {
        "label": "💣 EMP قوی",
        "desc": "خودکار در حمله بعدی: دفاع هدف ۳۰٪ کمتر",
    },
    "spy_drone": {"label": "🚁 پهپاد یک\u200cبارمصرف", "desc": "یک حمله دقیق رایگان"},
    "smoke_shield": {"label": "🛡️ محافظ دودزا", "desc": "استفاده: محافظ ۳ ساعته"},
    "anti_toxin_serum": {
        "label": "🧪 سرم ضدآلودگی",
        "desc": "استفاده: جان کامل می\u200cشود",
    },
    "war_adrenaline": {
        "label": "⚔️ آدرنالین جنگی",
        "desc": "خودکار در حمله بعدی: حمله +۲۰٪",
    },
    "temp_defense_plate": {
        "label": "🚧 صفحه دفاعی موقت",
        "desc": "استفاده: دفاع تا ۲ ساعت +۱۵٪",
    },
    "bunker_map": {
        "label": "🧭 نقشه بنکر",
        "desc": "خودکار در گشت بنکر: شانس صندوق بیشتر",
    },
}
registry.USE_ITEM_BUTTON = {
    k: f"استفاده: {v['label']}" for k, v in registry.CONSUMABLE_ITEMS.items()
}
registry.NIGHT_SMUGGLER_STOCK = {
    "scrap": 80,
    "plastic": 60,
    "glass": 30,
    "copper": 12,
    "battery": 4,
}
registry.NIGHT_SMUGGLER_CAP = {
    "scrap": 25,
    "plastic": 20,
    "glass": 12,
    "copper": 4,
    "battery": 2,
}
registry.NIGHT_SMUGGLER_BUY_BUTTON = {
    r: f"خرید قاچاق: {registry.RES_ICON[r]} {registry.RES_NAME[r]}"
    for r in registry.RESOURCES
}
registry.TERRITORIES = {
    "iron_workshop": {
        "label": "♻️ کارگاه آهن",
        "base_def": 900,
        "reward": {"scrap": 2},
        "reward_text": "♻️ اوراق × ۲ برای هر عضو",
    },
    "cable_factory": {
        "label": "🔶 کارخانه کابل",
        "base_def": 1300,
        "reward": {"copper": 1},
        "reward_text": "🔶 مس × ۱ برای هر عضو",
    },
    "burnt_powerplant": {
        "label": "🔋 نیروگاه سوخته",
        "base_def": 1800,
        "reward_random": {"battery": 1, "count": 3},
        "reward_text": "🔋 باتری × ۱ برای ۳ عضو تصادفی",
    },
    "glass_house": {
        "label": "🫙 شیشه\u200cخانه شکسته",
        "base_def": 1000,
        "reward": {"glass": 3},
        "reward_text": "🫙 شیشه × ۳ برای هر عضو",
    },
    "plastic_depot": {
        "label": "🗑️ انبار پلاستیک",
        "base_def": 850,
        "reward": {"plastic": 4},
        "reward_text": "🗑️ پلاستیک × ۴ برای هر عضو",
    },
    "old_well": {
        "label": "💧 چاه تصفیه قدیمی",
        "base_def": 1600,
        "reward": {"water": 60},
        "reward_text": "💧 آب × ۶۰ برای هر عضو",
    },
    "radio_tower": {
        "label": "📡 برج رادیویی",
        "base_def": 2000,
        "radio_bonus": True,
        "reward_text": "روزی ۱ پیام تبلیغاتی/تهدیدآمیز در رادیو",
    },
}
registry.TERRITORY_ATTACK_BUTTON = {
    k: f"⚔️ حمله به {v['label']}" for k, v in registry.TERRITORIES.items()
}
registry.ALLIANCE_MISSION_TEMPLATES = [
    {
        "key": "alliance_scavenge",
        "title": "اعضا با هم ۱۵ بار گشت بزنند",
        "goal": 15,
        "reward": {"vault_water": 300},
    },
    {
        "key": "alliance_barter",
        "title": "۳ معاوضه منابع انجام دهند",
        "goal": 3,
        "reward": {"vault_copper": 5},
    },
    {
        "key": "group_raid",
        "title": "یک حمله گروهی موفق",
        "goal": 1,
        "reward": {"member_cache_medium": 1},
    },
    {
        "key": "capture_zone",
        "title": "یک منطقه شهری را تصرف کنید",
        "goal": 1,
        "reward": {"season_points": 100},
    },
]
registry._orig_new_player = registry.new_player
registry._orig_default_game = registry.default_game
registry._orig_migrate_game = registry.migrate_game
registry._orig_market_keypad = registry.market_keypad
registry._orig_handle_city_map = registry.handle_city_map
registry._orig_handle_inventory = registry.handle_inventory
registry._orig_handle_attack_menu = registry.handle_attack_menu
registry._orig_alliance_keypad = registry.alliance_keypad
registry._orig_handle_alliance_menu = registry.handle_alliance_menu
registry._orig_inc_mission = registry.inc_mission
registry._orig_fmt_reward_dict = registry.fmt_reward_dict
registry._orig_award_mission_reward = registry.award_mission_reward
registry._orig_maybe_find_cache = registry.maybe_find_cache
registry._orig_handle_open_cache = registry.handle_open_cache
registry._orig_maybe_roll_season = registry.maybe_roll_season
registry._orig_group_radio_periodic_text = registry.group_radio_periodic_text
registry._orig_periodic_group_radio = registry.periodic_group_radio
registry._orig_handle_state = registry.handle_state
registry._orig_dispatch = registry.dispatch


def ensure_player_expansion_fields(p: dict[str, Any]) -> dict[str, Any]:
    p.setdefault("caches", {})
    for k in registry.CACHE_ORDER:
        p["caches"].setdefault(k, 0)
    old = int(p.get("loot_caches", 0) or 0)
    total = sum(int(p["caches"].get(k, 0) or 0) for k in registry.CACHE_ORDER)
    if old > total:
        p["caches"]["rusty"] = int(p["caches"].get("rusty", 0)) + (old - total)
    p["loot_caches"] = sum(
        int(p["caches"].get(k, 0) or 0) for k in registry.CACHE_ORDER
    )
    p.setdefault("revenge_cd", None)
    p.setdefault("season_titles", [])
    p.setdefault("profile_frames", [])
    p.setdefault("bad_credit", False)
    p.setdefault("next_start_bonus_pct", float(p.get("next_start_bonus_pct", 0) or 0))
    p.setdefault("stats", {})
    for k in [
        "revenge_wins",
        "revenge_losses",
        "bounty_created",
        "bounty_claimed",
        "smuggler_buys",
        "territory_wins",
    ]:
        p["stats"].setdefault(k, 0)
    return p


registry.ensure_player_expansion_fields = ensure_player_expansion_fields


def refresh_cache_total(p: dict[str, Any]) -> int:
    registry.ensure_player_expansion_fields(p)
    total = sum(int(p.get("caches", {}).get(k, 0) or 0) for k in registry.CACHE_ORDER)
    p["loot_caches"] = total
    return total


registry.refresh_cache_total = refresh_cache_total


def add_cache_to_player(chat_id: str, cache_type: str = "rusty", qty: int = 1) -> None:
    if cache_type not in registry.CACHE_ORDER:
        cache_type = "rusty"
    p = registry.get_player(chat_id)
    registry.ensure_player_expansion_fields(p)
    p["caches"][cache_type] = int(p["caches"].get(cache_type, 0)) + int(qty)
    registry.refresh_cache_total(p)
    registry.save_game()


registry.add_cache_to_player = add_cache_to_player


def add_inventory_item(p: dict[str, Any], key: str, qty: int = 1) -> None:
    p.setdefault("inventory", {})[key] = int(p.get("inventory", {}).get(key, 0)) + int(
        qty
    )


registry.add_inventory_item = add_inventory_item


def fmt_cache_counts(p: dict[str, Any]) -> str:
    registry.ensure_player_expansion_fields(p)
    parts = []
    for k in registry.CACHE_ORDER:
        q = int(p.get("caches", {}).get(k, 0) or 0)
        if q > 0:
            parts.append(f"{registry.CACHE_TYPES[k]['label']} × {q}")
    return "\n".join(parts) if parts else "صندوقی نداری."


registry.fmt_cache_counts = fmt_cache_counts


def fmt_any_reward(reward: dict[str, int]) -> str:
    parts: list[str] = []
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            parts.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            parts.append(f"🎁 صندوق زنگ\u200cزده × {v}")
        elif k.startswith("cache_"):
            ctype = k.split("_", 1)[1]
            parts.append(
                f"{registry.CACHE_TYPES.get(ctype, registry.CACHE_TYPES['rusty'])['label']} × {v}"
            )
        elif k in registry.RES_ICON:
            parts.append(registry.fmt_res_amount(k, v))
        elif k.startswith("vault_"):
            res = k.split("_", 1)[1]
            if res == "water":
                parts.append(f"خزانه اتحاد: 💧 آب × {v}")
            elif res in registry.RES_ICON:
                parts.append(
                    f"خزانه اتحاد: {registry.RES_ICON[res]} {registry.RES_NAME[res]} × {v}"
                )
        elif k == "season_points":
            parts.append(f"XP/امتیاز اتحاد × {v}")
        elif k == "member_cache_medium":
            parts.append(f"📦 صندوق متوسط × {v} برای اعضای فعال")
        else:
            parts.append(f"{k} × {v}")
    return " + ".join(parts) if parts else "—"


registry.fmt_any_reward = fmt_any_reward


def fmt_reward_dict(reward: dict[str, int]) -> str:
    return registry.fmt_any_reward(reward)


registry.fmt_reward_dict = fmt_reward_dict


def award_mission_reward(p: dict[str, Any], reward: dict[str, int]) -> str:
    paid: list[str] = []
    owner_id = None
    for cid, pp in registry.game.get("players", {}).items():
        if pp is p:
            owner_id = cid
            break
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            registry.add_xp(p, v)
            paid.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            if owner_id:
                registry.add_cache_to_player(owner_id, "rusty", v)
            else:
                p["loot_caches"] = int(p.get("loot_caches", 0)) + v
            paid.append(f"🎁 صندوق زنگ\u200cزده × {v}")
        elif k.startswith("cache_"):
            ctype = k.split("_", 1)[1]
            if owner_id:
                registry.add_cache_to_player(owner_id, ctype, v)
            paid.append(
                f"{registry.CACHE_TYPES.get(ctype, registry.CACHE_TYPES['rusty'])['label']} × {v}"
            )
        else:
            registry.add_amount(p, k, v)
            paid.append(registry.fmt_res_amount(k, v))
    return " + ".join(paid) if paid else "—"


registry.award_mission_reward = award_mission_reward


def new_player(name: str | None = None, chat_id: str = "") -> dict[str, Any]:
    p = registry._orig_new_player(name, chat_id)
    registry.ensure_player_expansion_fields(p)
    return p


registry.new_player = new_player


def default_game() -> dict[str, Any]:
    g = registry._orig_default_game()
    g.setdefault("night_smuggler", None)
    g.setdefault("revenge_targets", [])
    g.setdefault("next_revenge_id", 1)
    g.setdefault("bounty_contracts", [])
    g.setdefault("next_bounty_id", 1)
    g.setdefault("territories", {})
    g.setdefault("last_territory_reward_day", None)
    return g


registry.default_game = default_game


def ensure_territories() -> dict[str, Any]:
    terr = registry.game.setdefault("territories", {})
    for key, cfg in registry.TERRITORIES.items():
        terr.setdefault(
            key, {"owner": None, "last_attack_at": None, "last_reward_day": None}
        )
        terr[key].setdefault("owner", None)
        terr[key].setdefault("last_attack_at", None)
        terr[key].setdefault("last_reward_day", None)
    return terr


registry.ensure_territories = ensure_territories


def migrate_game(g: dict[str, Any]) -> dict[str, Any]:
    base = registry._orig_migrate_game(g)
    base.setdefault("night_smuggler", None)
    base.setdefault("revenge_targets", [])
    base.setdefault("next_revenge_id", 1)
    base.setdefault("bounty_contracts", [])
    base.setdefault("next_bounty_id", 1)
    base.setdefault("territories", {})
    base.setdefault("last_territory_reward_day", None)
    for cid, p in list(base.get("players", {}).items()):
        registry.ensure_player_expansion_fields(p)
    for al in base.get("alliances", {}).values():
        if isinstance(al, dict):
            al.setdefault("resource_vault", {})
            for r in registry.RESOURCES:
                al["resource_vault"].setdefault(r, 0)
            al.setdefault("mission_day", None)
            al.setdefault("alliance_missions", [])
            al.setdefault("territory_cd", {})
    terr = base.setdefault("territories", {})
    for key in registry.TERRITORIES:
        terr.setdefault(
            key, {"owner": None, "last_attack_at": None, "last_reward_day": None}
        )
    return base


registry.migrate_game = migrate_game


def market_keypad() -> dict[str, Any]:
    return registry.make_keypad(
        [
            [registry.B("market_people"), registry.B("market_create_order")],
            [registry.B("market_my_orders"), registry.B("market_barter")],
            [registry.B("market_my_barters"), registry.B("market_resource_rentals")],
            [registry.B("night_smuggler"), registry.B("market_system_buy")],
            [registry.B("market_system_sell"), registry.B("market_prices")],
            [registry.B("main_menu")],
        ]
    )


registry.market_keypad = market_keypad


def handle_city_map(chat_id: str) -> None:
    boss = registry.active_boss()
    boss_line = (
        registry.T(
            "map.boss_active", name=boss["name"], hp=registry.fmt_num(boss["hp"])
        )
        if boss
        else registry.T("map.boss_none")
    )
    p = registry.get_player(chat_id)
    cache_line = registry.fmt_cache_counts(p)
    registry.ensure_territories()
    owners = []
    for k, cfg in registry.TERRITORIES.items():
        owner = registry.game.get("territories", {}).get(k, {}).get("owner")
        owners.append(f"{cfg['label']}: {owner or 'بدون مالک'}")
    text = (
        f"🗺️ نقشه شهر\n━━━━━━━━━━━━\nاینجا مرکز گشت، باس، صندوق\u200cها و جنگ کارتل\u200cهاست.\n\n☣️ باس جهانی: {boss_line}\n\n🎁 صندوق\u200cهای تو:\n{cache_line}\n\n🏴 مناطق قابل تصرف:\n"
        + "\n".join(owners[:7])
    )
    registry.send(
        chat_id,
        f"🗺️ نقشه شهر آخرالزمان\n\n{boss_line}\n\n🎁 صندوق\u200cهای تو:\n{cache_line}\n\n🕶️ قاچاقچی شبانه → بخش بازار",
        keypad=registry.make_keypad(
            [
                [registry.B("scavenge_alley"), registry.B("scavenge_suburb")],
                [registry.B("scavenge_center"), registry.B("scavenge_bunker")],
                [registry.B("world_boss"), registry.B("open_cache")],
                [registry.B("daily_missions"), registry.B("news"), registry.B("event")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_city_map = handle_city_map


def maybe_find_cache(chat_id: str, zone_key: str) -> str:
    chances = {"alley": 0.01, "suburb": 0.018, "center": 0.032, "bunker": 0.055}
    p = registry.get_player(chat_id)
    if zone_key == "bunker" and int(p.get("inventory", {}).get("bunker_map", 0)) > 0:
        p["inventory"]["bunker_map"] -= 1
        if p["inventory"].get("bunker_map", 0) <= 0:
            p["inventory"].pop("bunker_map", None)
        chances["bunker"] += 0.1
    if random.random() > chances.get(zone_key, 0.015):
        return ""
    ctype = "rusty"
    if zone_key == "center" and random.random() < 0.25:
        ctype = "medium"
    if zone_key == "bunker":
        ctype = (
            "military"
            if random.random() < 0.18
            else "medium"
            if random.random() < 0.45
            else "rusty"
        )
    registry.add_cache_to_player(chat_id, ctype, 1)
    registry.add_news(
        f"🎁 {registry.player_name(chat_id)} در گشت\u200cزنی {registry.CACHE_TYPES[ctype]['label']} پیدا کرد."
    )
    return f"\n🎁 پیدا کردی: {registry.CACHE_TYPES[ctype]['label']}\n📦 صندوق\u200cهای تو الان: {registry.refresh_cache_total(p)}"


registry.maybe_find_cache = maybe_find_cache


def handle_open_cache(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    total = registry.refresh_cache_total(p)
    if total <= 0:
        registry.send(
            chat_id,
            "🎁 صندوقی برای باز کردن نداری.\n\nاز گشت\u200cهای خطرناک، باس، مأموریت\u200cها یا جایزه\u200cها صندوق بگیر.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    rows = []
    for k in registry.CACHE_ORDER:
        if int(p.get("caches", {}).get(k, 0) or 0) > 0:
            rows.append([registry.CACHE_OPEN_BUTTON[k]])
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        "🎁 صندوق\u200cها\n━━━━━━━━━━━━\n"
        + registry.fmt_cache_counts(p)
        + "\n\nکدوم صندوق را باز کنم؟",
        keypad=registry.make_keypad(rows),
    )


registry.handle_open_cache = handle_open_cache


def weighted_choice(items: list[tuple[str, int]]) -> str:
    total = sum((w for _, w in items))
    r = random.randint(1, max(1, total))
    cur = 0
    for key, w in items:
        cur += w
        if r <= cur:
            return key
    return items[-1][0]


registry.weighted_choice = weighted_choice


def grant_cache_reward(chat_id: str, cache_type: str) -> list[str]:
    p = registry.get_player(chat_id)
    lines: list[str] = []
    if cache_type == "rusty":
        kind = registry.weighted_choice(
            [("water", 35), ("basic_res", 40), ("consumable", 22), ("medium_cache", 3)]
        )
        if kind == "water":
            q = random.randint(45, 140)
            p["water"] = int(p.get("water", 0)) + q
            lines.append(f"💧 آب × {q}")
        elif kind == "basic_res":
            loot = {
                "scrap": random.randint(8, 24),
                "plastic": random.randint(6, 18),
                "glass": random.randint(3, 10),
            }
            for r, q in loot.items():
                registry.add_amount(p, r, q)
            lines.append(registry.fmt_res_lines(loot))
        elif kind == "medium_cache":
            registry.add_cache_to_player(chat_id, "medium", 1)
            lines.append("📦 صندوق متوسط × ۱")
        else:
            key = random.choice(
                ["small_medkit", "weak_smoke", "alley_map", "small_repair_tool"]
            )
            registry.add_inventory_item(p, key)
            lines.append(registry.CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "medium":
        kind = registry.weighted_choice(
            [
                ("rare_res", 45),
                ("consumable", 42),
                ("military_cache", 8),
                ("legendary_roll", 5),
            ]
        )
        if kind == "rare_res":
            loot = {
                "scrap": random.randint(12, 30),
                "glass": random.randint(8, 20),
                "copper": random.randint(1, 4),
            }
            if random.random() < 0.35:
                loot["battery"] = random.randint(1, 2)
            for r, q in loot.items():
                registry.add_amount(p, r, q)
            lines.append(registry.fmt_res_lines(loot))
        elif kind == "military_cache":
            registry.add_cache_to_player(chat_id, "military", 1)
            lines.append("🪖 صندوق نظامی × ۱")
        elif kind == "legendary_roll":
            lg = registry.maybe_award_legendary(chat_id, "صندوق متوسط", 0.045)
            if lg:
                lines.append(lg)
            else:
                registry.add_amount(p, "copper", 4)
                lines.append("🔶 مس × ۴")
        else:
            key = random.choice(
                ["emp_weak", "spy_drone", "smoke_shield", "anti_toxin_serum"]
            )
            registry.add_inventory_item(p, key)
            lines.append(registry.CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "military":
        kind = registry.weighted_choice(
            [
                ("rare_res", 38),
                ("strong_consumable", 45),
                ("legendary_roll", 12),
                ("smuggler_cache", 5),
            ]
        )
        if kind == "rare_res":
            loot = {
                "battery": random.randint(1, 3),
                "copper": random.randint(3, 8),
                "glass": random.randint(8, 18),
            }
            for r, q in loot.items():
                registry.add_amount(p, r, q)
            lines.append(registry.fmt_res_lines(loot))
        elif kind == "smuggler_cache":
            registry.add_cache_to_player(chat_id, "smuggler", 1)
            lines.append("🕶️ صندوق قاچاقچی × ۱")
        elif kind == "legendary_roll":
            lg = registry.maybe_award_legendary(chat_id, "صندوق نظامی", 0.12)
            if lg:
                lines.append(lg)
            else:
                registry.add_inventory_item(p, "emp_strong")
                lines.append(registry.CONSUMABLE_ITEMS["emp_strong"]["label"] + " × ۱")
        else:
            key = random.choice(
                [
                    "emp_strong",
                    "smoke_shield",
                    "war_adrenaline",
                    "temp_defense_plate",
                    "bunker_map",
                ]
            )
            registry.add_inventory_item(p, key)
            lines.append(registry.CONSUMABLE_ITEMS[key]["label"] + " × ۱")
        registry.send_group_radio(
            f"🎁 صدای فلز از صندوق\n{registry.player_name(chat_id)} یه صندوق نظامی باز کرد.\nاگه امشب کسی رو زد، نگید شانسی بود.",
            force=True,
            reason="military_cache",
        )
    elif cache_type == "smuggler":
        loot = {"copper": random.randint(4, 10), "battery": random.randint(1, 4)}
        for r, q in loot.items():
            registry.add_amount(p, r, q)
        lines.append(registry.fmt_res_lines(loot))
        key = random.choice(["emp_weak", "emp_strong", "spy_drone", "war_adrenaline"])
        registry.add_inventory_item(p, key)
        lines.append(registry.CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "legendary":
        lg = registry.maybe_award_legendary(chat_id, "صندوق افسانه\u200cای", 1.0)
        if lg:
            lines.append(lg)
        registry.add_inventory_item(
            p, random.choice(["emp_strong", "war_adrenaline", "temp_defense_plate"]), 2
        )
        p["season_points_bonus"] = int(p.get("season_points_bonus", 0)) + 500
        lines.append("🏆 امتیاز سیزن × ۵۰۰")
        registry.send_group_radio(
            f"👑 بوی افسانه\n{registry.player_name(chat_id)} از صندوق افسانه\u200cای چیزی بیرون کشید که نباید دست هیچ آدم سالمی باشه.",
            force=True,
            reason="legendary_cache",
        )
    return lines


registry.grant_cache_reward = grant_cache_reward


def handle_open_cache_type(chat_id: str, text: str) -> None:
    ctype = next((k for k, b in registry.CACHE_OPEN_BUTTON.items() if text == b), None)
    if not ctype:
        return registry.handle_open_cache(chat_id)
    p = registry.get_player(chat_id)
    registry.ensure_player_expansion_fields(p)
    if int(p.get("caches", {}).get(ctype, 0) or 0) <= 0:
        registry.send(
            chat_id, "❌ از این نوع صندوق نداری.", keypad=registry.main_keypad(chat_id)
        )
        return
    p["caches"][ctype] -= 1
    new_total = sum(
        int(p.get("caches", {}).get(k, 0) or 0) for k in registry.CACHE_ORDER
    )
    p["loot_caches"] = new_total
    p.setdefault("stats", {})["caches_opened"] = (
        int(p.get("stats", {}).get("caches_opened", 0)) + 1
    )
    registry.inc_mission(chat_id, "open_cache", 1)
    lines = registry.grant_cache_reward(chat_id, ctype)
    registry.save_game()
    print("CACHE DEBUG", ctype, p["caches"], p["loot_caches"])
    registry.send(
        chat_id,
        f"✅ {registry.CACHE_TYPES[ctype]['label']} باز شد!\n━━━━━━━━━━━━\n"
        + "\n".join(lines)
        + f"\n\n📦 صندوق\u200cهای باقی\u200cمانده: {p.get('loot_caches', 0)}",
        keypad=registry.make_keypad(
            [
                [registry.B("open_cache")],
                [registry.B("inventory")],
                [registry.B("main_menu")],
            ]
        ),
    )


registry.handle_open_cache_type = handle_open_cache_type


def consume_next_raid_emp(
    chat_id: str, p: dict[str, Any], raid_notes: list[str]
) -> float:
    inv = p.setdefault("inventory", {})
    for key, mult, label in [
        ("emp_strong", 0.7, "💣 EMP قوی"),
        ("emp_weak", 0.85, "💣 EMP ضعیف"),
    ]:
        if int(inv.get(key, 0) or 0) > 0:
            inv[key] -= 1
            if inv.get(key, 0) <= 0:
                inv.pop(key, None)
            raid_notes.append(f"{label} مصرف شد؛ دفاع هدف کمتر حساب شد.")
            return mult
    return 1.0


registry.consume_next_raid_emp = consume_next_raid_emp


def consume_next_raid_boosters(
    chat_id: str, p: dict[str, Any], raid_notes: list[str]
) -> float:
    inv = p.setdefault("inventory", {})
    if int(inv.get("war_adrenaline", 0) or 0) > 0:
        inv["war_adrenaline"] -= 1
        if inv.get("war_adrenaline", 0) <= 0:
            inv.pop("war_adrenaline", None)
        raid_notes.append("⚔️ آدرنالین جنگی مصرف شد؛ حمله بعدی ۲۰٪ قوی\u200cتر شد.")
        return 1.2
    return 1.0


registry.consume_next_raid_boosters = consume_next_raid_boosters


def handle_use_consumable(chat_id: str, text: str) -> None:
    key = next((k for k, b in registry.USE_ITEM_BUTTON.items() if text == b), None)
    if not key:
        return registry.handle_inventory(chat_id)
    p = registry.get_player(chat_id)
    inv = p.setdefault("inventory", {})
    if int(inv.get(key, 0) or 0) <= 0:
        registry.send(
            chat_id, "❌ از این آیتم نداری.", keypad=registry.main_keypad(chat_id)
        )
        return
    msg = ""
    if key == "small_medkit":
        heal = min(40, 100 - int(p.get("hp", 100)))
        p["hp"] = min(100, int(p.get("hp", 100)) + 40)
        msg = f"🩹 کیت مصرف شد. جان نیروها +{heal} شد. ❤️ {p['hp']}/100"
    elif key == "anti_toxin_serum":
        p["hp"] = 100
        msg = "🧪 سرم مصرف شد. جان نیروها کامل شد. ❤️ 100/100"
    elif key == "smoke_shield":
        if registry.is_shielded(p):
            registry.send(
                chat_id,
                f"🛡️ الان محافظ داری: {registry.fmt_cd(registry.shield_remaining(p))} باقی مانده.",
                keypad=registry.main_keypad(chat_id),
            )
            return
        p["shield_until"] = registry.iso(registry.now() + timedelta(hours=3))
        msg = "🛡️ محافظ دودزا فعال شد. تا ۳ ساعت یک لایه امنیت داری."
    elif key == "temp_defense_plate":
        p["temp_defense_until"] = registry.iso(registry.now() + timedelta(hours=2))
        msg = "🚧 صفحه دفاعی نصب شد. تا ۲ ساعت دفاعت در غارت\u200cها ۱۵٪ بیشتر حساب می\u200cشود."
    elif key == "small_repair_tool":
        if not p.get("upgrades_in_progress"):
            registry.send(
                chat_id,
                "🔧 ارتقای فعالی نداری که تعمیر/تسریع شود.",
                keypad=registry.main_keypad(chat_id),
            )
            return
        for u in p.get("upgrades_in_progress", []):
            finish = registry.fromiso(u.get("finish"), registry.now())
            left = max(0, (finish - registry.now()).total_seconds())
            u["finish"] = registry.iso(registry.now() + timedelta(seconds=left * 0.75))
        msg = "🔧 ابزار تعمیر مصرف شد. زمان ارتقاهای فعال ۲۵٪ کمتر شد."
    else:
        registry.send(
            chat_id,
            "این آیتم در زمان مناسب خودکار مصرف می\u200cشود: "
            + registry.CONSUMABLE_ITEMS[key]["desc"],
            keypad=registry.main_keypad(chat_id),
        )
        return
    inv[key] -= 1
    if inv.get(key, 0) <= 0:
        inv.pop(key, None)
    registry.save_game()
    registry.send(chat_id, msg, keypad=registry.main_keypad(chat_id))


registry.handle_use_consumable = handle_use_consumable


def handle_inventory(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.ensure_player_expansion_fields(p)
    items = []
    rows = []
    for k, qty in sorted(p.get("inventory", {}).items()):
        if qty <= 0:
            continue
        if k in registry.CRAFT_ITEMS:
            items.append(f"{registry.CRAFT_ITEMS[k]['label']} × {qty}")
        elif k in registry.LEGENDARY_ITEMS:
            items.append(f"✨ {registry.LEGENDARY_ITEMS[k]['label']} × {qty}")
        elif k in registry.CONSUMABLE_ITEMS:
            items.append(
                f"{registry.CONSUMABLE_ITEMS[k]['label']} × {qty}\n  {registry.CONSUMABLE_ITEMS[k]['desc']}"
            )
            if k in registry.USE_ITEM_BUTTON and k in [
                "small_medkit",
                "anti_toxin_serum",
                "smoke_shield",
                "temp_defense_plate",
                "small_repair_tool",
            ]:
                rows.append([registry.USE_ITEM_BUTTON[k]])
    if registry.refresh_cache_total(p) > 0:
        items.append("🎁 صندوق\u200cها:\n" + registry.fmt_cache_counts(p))
        rows.append([registry.B("open_cache")])
    rows.append([registry.B("main_menu")])
    registry.send(
        chat_id,
        registry.T(
            "inventory.text",
            items="\n\n".join(items) or registry.T("inventory.empty"),
            scrap=p["resources"].get("scrap", 0),
            plastic=p["resources"].get("plastic", 0),
            glass=p["resources"].get("glass", 0),
            battery=p["resources"].get("battery", 0),
            copper=p["resources"].get("copper", 0),
            water=p.get("water", 0),
        ),
        keypad=registry.make_keypad(rows),
    )


registry.handle_inventory = handle_inventory


def smuggler_active_window(dt: datetime | None = None) -> bool:
    dt = dt or registry.now()
    return dt.hour >= 22 or dt.hour < 2


registry.smuggler_active_window = smuggler_active_window


def smuggler_day_key(dt: datetime | None = None) -> str:
    dt = dt or registry.now()
    if dt.hour < 2:
        dt = dt - timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


registry.smuggler_day_key = smuggler_day_key


def smuggler_active_until(dt: datetime | None = None) -> datetime:
    dt = dt or registry.now()
    if dt.hour >= 22:
        return (dt + timedelta(days=1)).replace(
            hour=2, minute=0, second=0, microsecond=0
        )
    return dt.replace(hour=2, minute=0, second=0, microsecond=0)


registry.smuggler_active_until = smuggler_active_until


def maybe_setup_night_smuggler() -> dict[str, Any] | None:
    if not registry.smuggler_active_window():
        return None
    day = registry.smuggler_day_key()
    sm = registry.game.get("night_smuggler")
    if not isinstance(sm, dict) or sm.get("day") != day:
        prices = {
            r: max(1, int(registry.BASE_PRICE[r] * random.uniform(0.45, 0.7)))
            for r in registry.RESOURCES
        }
        sm = {
            "day": day,
            "active_until": registry.iso(registry.smuggler_active_until()),
            "stock": dict(registry.NIGHT_SMUGGLER_STOCK),
            "prices": prices,
            "buyers": {},
            "announced": False,
            "soldout_announced": False,
        }
        registry.game["night_smuggler"] = sm
    if not sm.get("announced"):
        sm["announced"] = True
        registry.send_group_radio(
            "🕶️ قاچاقچی شبانه رسید\nبارش کمه، قیمت\u200cها کثیفاً ارزونه.\nهرکی خواب بمونه، فردا فقط غر می\u200cزنه.",
            force=True,
            reason="night_smuggler",
        )
        registry.add_news(
            "🕶️ قاچاقچی شبانه رسیده؛ موجودی محدود و قیمت\u200cها پایین\u200cتر از بازار است."
        )
    if all(int(v) <= 0 for v in sm.get("stock", {}).values()) and (
        not sm.get("soldout_announced")
    ):
        sm["soldout_announced"] = True
        registry.send_group_radio(
            "📦 بار قاچاقچی خالی شد.\nشهر سریع\u200cتر از چیزی که فکر می\u200cکردی گرسنه بود.",
            force=True,
            reason="night_smuggler_empty",
        )
    return sm


registry.maybe_setup_night_smuggler = maybe_setup_night_smuggler


def handle_night_smuggler(chat_id: str) -> None:
    sm = registry.maybe_setup_night_smuggler()
    if not sm:
        registry.send(
            chat_id,
            "🕶️ قاچاقچی شبانه\n━━━━━━━━━━━━\nفعلاً پیداش نیست. معمولاً از ساعت ۲۲:۰۰ تا ۰۲:۰۰ بارش را می\u200cآورد.\n\nقاچاقچی فقط منابع می\u200cفروشد؛ آیتم و صندوق نه.",
            keypad=registry.market_keypad(),
        )
        return
    lines = []
    rows = []
    for r in registry.RESOURCES:
        stock = int(sm.get("stock", {}).get(r, 0) or 0)
        price = int(
            sm.get("prices", {}).get(r, registry.BASE_PRICE[r])
            or registry.BASE_PRICE[r]
        )
        lines.append(
            f"{registry.RES_ICON[r]} {registry.RES_NAME[r]} × {stock} — قیمت: {price} آب / هر عدد — سقف تو: {registry.NIGHT_SMUGGLER_CAP[r]}"
        )
        if stock > 0:
            rows.append([registry.NIGHT_SMUGGLER_BUY_BUTTON[r]])
    rows.append([registry.B("back_market"), registry.B("main_menu")])
    left = registry.fmt_cd(
        (
            registry.fromiso(sm.get("active_until"), registry.now()) - registry.now()
        ).total_seconds()
    )
    registry.send(
        chat_id,
        "🕶️ قاچاقچی شبانه\n━━━━━━━━━━━━\nامشب بارش محدوده. هرکی زودتر بخرد، برده.\n\n📦 موجودی امشب:\n"
        + "\n".join(lines)
        + f"\n\n⏳ زمان باقی\u200cمانده: {left}\n📌 هر بازیکن هر شب حداکثر از ۲ نوع منبع می\u200cخرد.",
        keypad=registry.make_keypad(rows),
    )


registry.handle_night_smuggler = handle_night_smuggler


def handle_smuggler_select(chat_id: str, text: str) -> None:
    res = next(
        (r for r, b in registry.NIGHT_SMUGGLER_BUY_BUTTON.items() if text == b), None
    )
    sm = registry.maybe_setup_night_smuggler()
    if not res or not sm:
        return registry.handle_night_smuggler(chat_id)
    stock = int(sm.get("stock", {}).get(res, 0) or 0)
    if stock <= 0:
        registry.send(
            chat_id, "❌ این بار قاچاقچی تمام شده.", keypad=registry.market_keypad()
        )
        return
    buyers = sm.setdefault("buyers", {}).setdefault(chat_id, {})
    bought_types = [r for r, q in buyers.items() if int(q) > 0]
    if res not in bought_types and len(bought_types) >= 2:
        registry.send(
            chat_id,
            "❌ امشب از ۲ نوع منبع خرید کردی. بیشتر از این قاچاقچی بهت رو نمی\u200cده.",
            keypad=registry.market_keypad(),
        )
        return
    already = int(buyers.get(res, 0) or 0)
    cap_left = max(0, registry.NIGHT_SMUGGLER_CAP[res] - already)
    if cap_left <= 0:
        registry.send(
            chat_id,
            "❌ سقف خرید امشب این منبع را پر کردی.",
            keypad=registry.market_keypad(),
        )
        return
    registry.game.setdefault("chat_states", {})[chat_id] = {
        "state": "awaiting_smuggler_qty",
        "res": res,
    }
    registry.save_game()
    registry.send(
        chat_id,
        f"چند تا {registry.RES_ICON[res]} {registry.RES_NAME[res]} از قاچاقچی بخرم؟\nموجودی قاچاقچی: {stock}\nسقف باقی\u200cمانده تو: {cap_left}\nقیمت واحد: {sm['prices'][res]} آب",
        keypad=registry.make_keypad(
            [[registry.B("night_smuggler")], [registry.B("main_menu")]]
        ),
    )


registry.handle_smuggler_select = handle_smuggler_select


def handle_smuggler_qty(chat_id: str, text: str) -> None:
    st = registry.game.get("chat_states", {}).get(chat_id, {})
    res = st.get("res")
    sm = registry.maybe_setup_night_smuggler()
    if not sm or res not in registry.RESOURCES:
        registry.game.get("chat_states", {}).pop(chat_id, None)
        return registry.handle_night_smuggler(chat_id)
    qty = registry.safe_int(text, -1)
    if qty <= 0:
        registry.send(
            chat_id,
            "❌ عدد معتبر بفرست.",
            keypad=registry.make_keypad(
                [[registry.B("night_smuggler")], [registry.B("main_menu")]]
            ),
        )
        return
    buyers = sm.setdefault("buyers", {}).setdefault(chat_id, {})
    already = int(buyers.get(res, 0) or 0)
    cap_left = max(0, registry.NIGHT_SMUGGLER_CAP[res] - already)
    qty = min(qty, cap_left, int(sm.get("stock", {}).get(res, 0) or 0))
    if qty <= 0:
        registry.send(
            chat_id,
            "❌ سقف خرید یا موجودی قاچاقچی تمام شده.",
            keypad=registry.market_keypad(),
        )
        registry.game.get("chat_states", {}).pop(chat_id, None)
        return
    price = int(sm.get("prices", {}).get(res, registry.BASE_PRICE[res]))
    total = qty * price
    p = registry.get_player(chat_id)
    if int(p.get("water", 0)) < total:
        registry.send(
            chat_id,
            registry.T("errors.not_enough_water", need=total, have=p.get("water", 0)),
            keypad=registry.market_keypad(),
        )
        return
    p["water"] = int(p.get("water", 0)) - total
    registry.add_amount(p, res, qty)
    sm["stock"][res] = int(sm["stock"].get(res, 0)) - qty
    buyers[res] = already + qty
    p.setdefault("stats", {})["smuggler_buys"] = (
        int(p.get("stats", {}).get("smuggler_buys", 0)) + 1
    )
    registry.game.get("chat_states", {}).pop(chat_id, None)
    if all(int(v) <= 0 for v in sm.get("stock", {}).values()) and (
        not sm.get("soldout_announced")
    ):
        sm["soldout_announced"] = True
        registry.send_group_radio(
            "📦 بار قاچاقچی خالی شد.\nشهر سریع\u200cتر از چیزی که فکر می\u200cکردی گرسنه بود.",
            force=True,
            reason="night_smuggler_empty",
        )
    registry.save_game()
    registry.send(
        chat_id,
        f"✅ خرید قاچاق انجام شد!\n\nگرفتی: {registry.fmt_res_amount(res, qty)}\nپرداختی: 💧 آب × {total}\n💧 آب باقی\u200cمانده: {p.get('water', 0)}",
        keypad=registry.market_keypad(),
    )


registry.handle_smuggler_qty = handle_smuggler_qty


def expire_revenge_targets() -> None:
    for r in registry.game.setdefault("revenge_targets", []):
        if (
            not r.get("used")
            and registry.fromiso(r.get("expires_at"), registry.now()) <= registry.now()
        ):
            r["used"] = True
            r["expired"] = True


registry.expire_revenge_targets = expire_revenge_targets


def register_revenge_target(attacker_id: str, victim_id: str, lost: int = 0) -> None:
    if attacker_id == victim_id:
        return
    rid = int(registry.game.get("next_revenge_id", 1))
    registry.game["next_revenge_id"] = rid + 1
    rec = {
        "id": rid,
        "attacker": attacker_id,
        "victim": victim_id,
        "lost": int(lost or 0),
        "created_at": registry.iso(registry.now()),
        "expires_at": registry.iso(registry.now() + timedelta(hours=24)),
        "used": False,
    }
    registry.game.setdefault("revenge_targets", []).append(rec)
    registry.game["revenge_targets"] = registry.game["revenge_targets"][-200:]
    try:
        registry.send(
            victim_id,
            f"🚨 گاراژت غارت شد!\nمهاجم: {registry.display_name(registry.player_name(attacker_id))}\nضرر: 💧 آب × {registry.fmt_num(lost)}\n\n🔥 فرصت انتقام باز شد. تا ۲۴ ساعت می\u200cتونی بدون پهپاد به همین مهاجم حمله کنی.",
            keypad=registry.main_keypad(victim_id),
        )
    except Exception:
        pass


registry.register_revenge_target = register_revenge_target


def open_revenge_records(chat_id: str) -> list[dict[str, Any]]:
    registry.expire_revenge_targets()
    return [
        r
        for r in registry.game.get("revenge_targets", [])
        if r.get("victim") == chat_id and (not r.get("used"))
    ]


registry.open_revenge_records = open_revenge_records


def handle_revenge_menu(chat_id: str) -> None:
    recs = registry.open_revenge_records(chat_id)
    if not recs:
        registry.send(
            chat_id,
            "🔥 لیست انتقام\u200cها\n━━━━━━━━━━━━\nفعلاً فرصت انتقام فعالی نداری.\n\nوقتی کسی گاراژت را بزند، ۲۴ ساعت فرصت جواب دادن می\u200cگیری.",
            keypad=registry.make_keypad(
                [[registry.B("attack")], [registry.B("main_menu")]]
            ),
        )
        return
    lines = []
    rows = []
    for r in recs[:8]:
        left = registry.fmt_cd(
            (
                registry.fromiso(r.get("expires_at"), registry.now()) - registry.now()
            ).total_seconds()
        )
        lines.append(
            f"#{r['id']} — {registry.player_name(r['attacker'])}\n⏳ باقی\u200cمانده: {left}\n🎯 مزیت: بدون نیاز به پهپاد، افتخار بیشتر"
        )
        rows.append([f"🔥 انتقام #{r['id']}"])
    rows.append([registry.B("attack"), registry.B("main_menu")])
    registry.send(
        chat_id,
        "🔥 لیست انتقام\u200cها\n━━━━━━━━━━━━\n" + "\n\n".join(lines),
        keypad=registry.make_keypad(rows),
    )


registry.handle_revenge_menu = handle_revenge_menu


def handle_revenge_attack(chat_id: str, text: str) -> None:
    rid = registry.safe_int(re.sub("\\D+", "", text), -1)
    rec = next(
        (
            r
            for r in registry.open_revenge_records(chat_id)
            if int(r.get("id", -1)) == rid
        ),
        None,
    )
    if not rec:
        registry.send(
            chat_id,
            "❌ این انتقام پیدا نشد یا وقتش تمام شده.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    p = registry.get_player(chat_id)
    if (
        p.get("revenge_cd")
        and registry.fromiso(p.get("revenge_cd"), registry.now()) > registry.now()
    ):
        registry.send(
            chat_id,
            f"⏳ هنوز نیروهای انتقام خسته\u200cاند.\nزمان باقی\u200cمانده: {registry.fmt_cd((registry.fromiso(p.get('revenge_cd'), registry.now()) - registry.now()).total_seconds())}",
            keypad=registry.main_keypad(chat_id),
        )
        return
    target_id = rec.get("attacker")
    target = registry.game.get("players", {}).get(target_id)
    if not target:
        registry.send(
            chat_id, "❌ مهاجم قبلی پیدا نشد.", keypad=registry.main_keypad(chat_id)
        )
        return
    if registry.is_shielded(target):
        registry.send(
            chat_id,
            "🛡️ هدف محافظ دارد. فعلاً نمی\u200cشود انتقام گرفت.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    old_cd = p.get("raid_cd")
    p["raid_cd"] = None
    before_log_len = len(p.get("action_log", []))
    registry.handle_raid(chat_id, target_id, bucket_key="medium", precise=False)
    p = registry.get_player(chat_id)
    p["revenge_cd"] = registry.iso(registry.now() + timedelta(minutes=30))
    if old_cd and registry.fromiso(old_cd, registry.now()) > registry.fromiso(
        p.get("raid_cd"), registry.now()
    ):
        p["raid_cd"] = old_cd
    rec["used"] = True
    last = (p.get("action_log") or [None])[-1]
    if isinstance(last, dict) and last.get("action") == "raid_win":
        p["honor"] = int(p.get("honor", 0)) + 8
        p.setdefault("stats", {})["revenge_wins"] = (
            int(p.get("stats", {}).get("revenge_wins", 0)) + 1
        )
        registry.send_group_radio(
            f"🔥 انتقام ثبت شد\n{registry.player_name(chat_id)} جواب {registry.player_name(target_id)} رو داد.\nشهر یاد گرفت بعضی گاراژها دیر می\u200cزنن، ولی بد می\u200cزنن.",
            force=True,
            reason="revenge_win",
        )
        registry.send(
            chat_id,
            "🔥 انتقام موفق حساب شد!\n🎖️ افتخار اضافه: +8\nاین یکی فقط غارت نبود؛ جواب بود.",
            keypad=registry.main_keypad(chat_id),
        )
    else:
        p.setdefault("stats", {})["revenge_losses"] = (
            int(p.get("stats", {}).get("revenge_losses", 0)) + 1
        )
        registry.send_group_radio(
            f"💀 انتقام شکست خورد\n{registry.player_name(chat_id)} برگشت جواب بده، ولی {registry.player_name(target_id)} دوباره نگهش داشت.",
            force=True,
            reason="revenge_lose",
        )
    registry.save_game()


registry.handle_revenge_attack = handle_revenge_attack


def expire_bounty_contracts() -> None:
    for b in registry.game.setdefault("bounty_contracts", []):
        if (
            b.get("status") == "open"
            and registry.fromiso(b.get("expires_at"), registry.now()) <= registry.now()
        ):
            b["status"] = "expired"
            creator = b.get("creator")
            if creator in registry.game.get("players", {}):
                for r, q in b.get("reward", {}).items():
                    registry.add_amount(registry.game["players"][creator], r, int(q))


registry.expire_bounty_contracts = expire_bounty_contracts


def parse_reward_resources(text: str) -> dict[str, int]:
    tokens = re.findall("([آ-یA-Za-z_]+)\\s+(\\d+)", text or "")
    out: dict[str, int] = {}
    for name, qty in tokens:
        rk = registry.res_key(name)
        if rk and rk in registry.RESOURCES:
            out[rk] = out.get(rk, 0) + int(qty)
    return out


registry.parse_reward_resources = parse_reward_resources


def parse_bounty_text(text: str) -> tuple[str | None, dict[str, int]]:
    if "=" not in text:
        return (None, {})
    left, right = text.split("=", 1)
    return (left.strip(), registry.parse_reward_resources(right))


registry.parse_bounty_text = parse_bounty_text


def handle_bounty_board(chat_id: str) -> None:
    registry.expire_bounty_contracts()
    rows = []
    lines = []
    for b in [
        x
        for x in registry.game.get("bounty_contracts", [])
        if x.get("status") == "open"
    ][:12]:
        target = registry.game.get("players", {}).get(b.get("target"), {})
        left = registry.fmt_cd(
            (
                registry.fromiso(b.get("expires_at"), registry.now()) - registry.now()
            ).total_seconds()
        )
        creator_name = (
            "ناشناس" if b.get("anonymous") else registry.player_name(b.get("creator"))
        )
        lines.append(
            f"#{b['id']}\nهدف: {registry.player_name(b.get('target'))}\nلول: {target.get('level', '—')}\nجایزه: {registry.fmt_res_dict(b.get('reward', {}))}\nثبت\u200cکننده: {creator_name}\n⏳ باقی\u200cمانده: {left}"
        )
    rows = [
        [registry.B("bounty_create")],
        [registry.B("bounty_my")],
        [registry.B("attack"), registry.B("main_menu")],
    ]
    registry.send(
        chat_id,
        "🎯 تابلو جایزه\u200cبگیرها\n━━━━━━━━━━━━\n"
        + ("\n\n".join(lines) if lines else "فعلاً قراردادی روی دیوار نیست."),
        keypad=registry.make_keypad(rows),
    )


registry.handle_bounty_board = handle_bounty_board


def handle_create_bounty_prompt(chat_id: str) -> None:
    registry.game.setdefault("chat_states", {})[chat_id] = {
        "state": "awaiting_bounty_order"
    }
    registry.save_game()
    registry.send(
        chat_id,
        "🧾 ثبت قرارداد جایزه\n━━━━━━━━━━━━\nفرمت را اینطوری بفرست:\n\nاکبر آهنی = مس 5 باتری 1\n\nقوانین:\n• هدف باید لول ۳ به بالا باشد.\n• جایزه فقط منابع است.\n• جایزه از موجودی تو قفل می\u200cشود.\n• هر بازیکن روزی ۲ قرارداد می\u200cتواند ثبت کند.",
        keypad=registry.make_keypad(
            [[registry.B("bounty_board")], [registry.B("main_menu")]]
        ),
    )


registry.handle_create_bounty_prompt = handle_create_bounty_prompt


def handle_create_bounty(chat_id: str, text: str) -> None:
    target_name, reward = registry.parse_bounty_text(text)
    if not target_name or not reward:
        registry.send(
            chat_id,
            "❌ فرمت درست نیست. مثال: اکبر آهنی = مس 5 باتری 1",
            keypad=registry.main_keypad(chat_id),
        )
        return
    target_id = registry.find_player_by_name(target_name)
    if not target_id or target_id == chat_id:
        registry.send(
            chat_id,
            "❌ هدف پیدا نشد یا نمی\u200cتونی روی خودت قرارداد بگذاری.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    target = registry.game.get("players", {}).get(target_id, {})
    if int(target.get("level", 1)) < 3:
        registry.send(
            chat_id,
            "❌ روی بازیکن لول ۱ و ۲ نمی\u200cشود قرارداد جایزه گذاشت.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    open_on_target = [
        b
        for b in registry.game.get("bounty_contracts", [])
        if b.get("status") == "open" and b.get("target") == target_id
    ]
    if len(open_on_target) >= 3:
        registry.send(
            chat_id,
            "❌ روی این هدف همین الان ۳ قرارداد فعال هست.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    today = registry.today_key()
    made_today = sum(
        1
        for b in registry.game.get("bounty_contracts", [])
        if b.get("creator") == chat_id
        and str(b.get("created_at", "")).startswith(today)
    )
    if made_today >= 2:
        registry.send(
            chat_id,
            "❌ سقف امروزت پر شده؛ روزی ۲ قرارداد بیشتر نمی\u200cشود.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    p = registry.get_player(chat_id)
    if not registry.has_resources(p, reward):
        registry.send(
            chat_id,
            registry.T(
                "errors.not_enough_res", need=registry.fmt_res_shortage(reward, p)
            ),
            keypad=registry.main_keypad(chat_id),
        )
        return
    registry.pay_cost(p, reward)
    bid = int(registry.game.get("next_bounty_id", 1))
    registry.game["next_bounty_id"] = bid + 1
    b = {
        "id": bid,
        "creator": chat_id,
        "target": target_id,
        "reward": reward,
        "status": "open",
        "created_at": registry.iso(registry.now()),
        "expires_at": registry.iso(registry.now() + timedelta(hours=12)),
        "anonymous": False,
    }
    registry.game.setdefault("bounty_contracts", []).append(b)
    p.setdefault("stats", {})["bounty_created"] = (
        int(p.get("stats", {}).get("bounty_created", 0)) + 1
    )
    registry.game.get("chat_states", {}).pop(chat_id, None)
    registry.save_game()
    msg = f"🎯 قرارداد جایزه ثبت شد!\n━━━━━━━━━━━━\nهدف: {registry.player_name(target_id)}\nجایزه: {registry.fmt_res_dict(reward)}\n\nهرکس تا ۱۲ ساعت آینده هدف را با غارت موفق بزند، جایزه را می\u200cگیرد."
    registry.send(chat_id, msg, keypad=registry.main_keypad(chat_id))
    registry.send_group_radio(
        f"🎯 اسم روی دیوار\nبرای زدن {registry.player_name(target_id)} جایزه گذاشتن:\n{registry.fmt_res_dict(reward)}\n\nاگه {registry.player_name(target_id)} امشب راحت خوابید، یعنی شهر مرده.",
        force=True,
        reason="bounty_created",
    )


registry.handle_create_bounty = handle_create_bounty


def handle_my_bounties(chat_id: str) -> None:
    registry.expire_bounty_contracts()
    rows = []
    lines = []
    for b in [
        x
        for x in registry.game.get("bounty_contracts", [])
        if x.get("creator") == chat_id and x.get("status") == "open"
    ]:
        left = registry.fmt_cd(
            (
                registry.fromiso(b.get("expires_at"), registry.now()) - registry.now()
            ).total_seconds()
        )
        lines.append(
            f"#{b['id']} — هدف: {registry.player_name(b.get('target'))}\nجایزه: {registry.fmt_res_dict(b.get('reward', {}))}\n⏳ {left}\nبرای لغو: لغو جایزه #{b['id']}"
        )
        rows.append([f"لغو جایزه #{b['id']}"])
    rows.append([registry.B("bounty_board"), registry.B("main_menu")])
    registry.send(
        chat_id,
        "📜 قراردادهای جایزه من\n━━━━━━━━━━━━\n"
        + ("\n\n".join(lines) if lines else "قرارداد فعال نداری."),
        keypad=registry.make_keypad(rows),
    )


registry.handle_my_bounties = handle_my_bounties


def handle_cancel_bounty(chat_id: str, text: str) -> None:
    bid = registry.safe_int(re.sub("\\D+", "", text), -1)
    b = next(
        (
            x
            for x in registry.game.get("bounty_contracts", [])
            if int(x.get("id", -1)) == bid
            and x.get("creator") == chat_id
            and (x.get("status") == "open")
        ),
        None,
    )
    if not b:
        registry.send(
            chat_id, "❌ قرارداد پیدا نشد.", keypad=registry.main_keypad(chat_id)
        )
        return
    b["status"] = "cancelled"
    p = registry.get_player(chat_id)
    for r, q in b.get("reward", {}).items():
        registry.add_amount(p, r, int(q))
    registry.save_game()
    registry.send(
        chat_id,
        f"✅ قرارداد #{bid} لغو شد و جایزه برگشت.",
        keypad=registry.main_keypad(chat_id),
    )


registry.handle_cancel_bounty = handle_cancel_bounty


def complete_bounty_contracts(hunter_id: str, target_id: str) -> None:
    registry.expire_bounty_contracts()
    paid_any = False
    for b in registry.game.get("bounty_contracts", []):
        if (
            b.get("status") == "open"
            and b.get("target") == target_id
            and (b.get("creator") != hunter_id)
        ):
            b["status"] = "claimed"
            b["claimed_by"] = hunter_id
            b["claimed_at"] = registry.iso(registry.now())
            hunter = registry.get_player(hunter_id)
            for r, q in b.get("reward", {}).items():
                registry.add_amount(hunter, r, int(q))
            hunter.setdefault("stats", {})["bounty_claimed"] = (
                int(hunter.get("stats", {}).get("bounty_claimed", 0)) + 1
            )
            paid_any = True
            try:
                registry.send(
                    hunter_id,
                    f"🏆 قرارداد جایزه انجام شد!\nهدف را زدی: {registry.player_name(target_id)}\n\nجایزه پرداخت شد:\n{registry.fmt_res_dict(b.get('reward', {}))}",
                    keypad=registry.main_keypad(hunter_id),
                )
                registry.send(
                    b.get("creator"),
                    f"✅ قرارداد جایزه\u200cات انجام شد.\n{registry.player_name(hunter_id)} هدف را زد: {registry.player_name(target_id)}",
                    keypad=registry.main_keypad(b.get("creator")),
                )
            except Exception:
                pass
            registry.send_group_radio(
                f"🏆 قرارداد جایزه انجام شد!\n{registry.player_name(hunter_id)} هدف را زد: {registry.player_name(target_id)}\n\nجایزه پرداخت شد:\n{registry.fmt_res_dict(b.get('reward', {}))}",
                force=True,
                reason="bounty_claimed",
            )
    if paid_any:
        registry.save_game()


registry.complete_bounty_contracts = complete_bounty_contracts


def handle_attack_menu(chat_id: str) -> None:
    p = registry.get_player(chat_id)
    registry.passive_income(chat_id)
    registry.finish_upgrades(p)
    registry.recalc_power(p)
    extra_rows = [
        [registry.B("revenge_menu"), registry.B("bounty_board")],
        [registry.B("bounty_create"), registry.B("bounty_my")],
    ]
    if p.get("hp", 100) < 25:
        registry.send(
            chat_id,
            registry.T("raid.low_hp"),
            keypad=registry.make_keypad(extra_rows + [[registry.B("main_menu")]]),
        )
        return
    if registry.cd_remaining(p, "raid") > 0:
        cd_text = registry.T(
            "raid.cooldown", time=registry.fmt_cd(registry.cd_remaining(p, "raid"))
        )
    else:
        cd_text = ""
    if int(p.get("total_attack", 0)) <= 0:
        registry.send(
            chat_id,
            registry.T("raid.zero_attack"),
            keypad=registry.make_keypad(extra_rows + [[registry.B("main_menu")]]),
        )
        return
    candidates = registry.raid_candidates(chat_id)
    rows = []
    bucket_lines = []
    for key, cfg in registry.RAID_BUCKETS.items():
        targets = registry.raid_bucket_targets(chat_id, key)
        button = registry.B(cfg["button_key"])
        bucket_lines.append(
            registry.T(
                "raid.bucket_line",
                button=button,
                title=cfg["title"],
                count=len(targets),
                loot=int(cfg["loot_mod"] * 100),
                risk="کم" if key == "weak" else "معمولی" if key == "medium" else "زیاد",
            )
        )
        rows.append([button])
    drone_count = int(p.get("inventory", {}).get("spy_drone", 0))
    direct_lines = []
    if drone_count > 0 and candidates:
        direct_targets = sorted(
            candidates, key=lambda x: registry.raid_target_score(x[1]), reverse=True
        )[:12]
        for cid, rp in direct_targets:
            if registry.is_shielded(rp):
                continue
            button = registry.raid_target_button(rp.get("name"))
            direct_lines.append(
                registry.T(
                    "raid.direct_line",
                    button=button,
                    name=registry.display_name(rp.get("name")),
                    level=rp.get("level", 1),
                    defense=f"{rp.get('total_defense', 0):,}",
                    water=f"{rp.get('water', 0):,}",
                )
            )
            rows.append([button])
        drone_hint = registry.T("raid.drone_available", count=drone_count)
    else:
        drone_hint = registry.T("raid.drone_hint")
        direct_lines.append(drone_hint)
    rows = extra_rows + rows + [[registry.B("main_menu")]]
    shield_hint = (
        "\n📌 بازیکن\u200cهای دارای محافظ از هدف\u200cهای شانسی حذف می\u200cشوند."
    )
    text = (
        registry.T(
            "raid.menu",
            attack=f"{p.get('total_attack', 0):,}",
            bucket_lines="\n".join(bucket_lines),
            direct_lines="\n".join(direct_lines),
            drone_count=drone_count,
        )
        + shield_hint
    )
    if cd_text:
        text = cd_text + "\n\n" + text
    registry.send(chat_id, text, keypad=registry.make_keypad(rows))


registry.handle_attack_menu = handle_attack_menu


def alliance_keypad(chat_id: str) -> dict[str, Any]:
    al = registry.player_alliance(chat_id)
    if not al:
        return registry.make_keypad(
            [
                [registry.B("alliance_create"), registry.B("alliance_list")],
                [registry.B("main_menu")],
            ]
        )
    rows = [
        [registry.B("alliance_group_raid"), registry.B("alliance_vault")],
        [registry.B("territories"), registry.B("alliance_missions")],
        [registry.B("alliance_leave")],
    ]
    if al.get("owner") == chat_id:
        rows.insert(0, [registry.B("alliance_manage")])
    rows.append([registry.B("main_menu")])
    return registry.make_keypad(rows)


registry.alliance_keypad = alliance_keypad


def handle_alliance_menu(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            registry.T("alliance.none"),
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    registry.ensure_alliance_missions(al)
    lines = []
    for cid in al.get("members", []):
        mp = registry.game["players"].get(cid)
        if mp:
            registry.recalc_power(mp)
            lines.append(
                registry.T(
                    "alliance.member_line",
                    name=mp.get("name"),
                    level=mp.get("level", 1),
                    water=mp.get("water", 0),
                    power=f"{mp.get('total_attack', 0) + mp.get('total_defense', 0):,}",
                )
            )
    owned = [
        cfg["label"]
        for k, cfg in registry.TERRITORIES.items()
        if registry.game.get("territories", {}).get(k, {}).get("owner")
        == al.get("name")
    ]
    rv = al.setdefault("resource_vault", {})
    rv_text = (
        " | ".join((registry.fmt_res_amount(r, q) for r, q in rv.items() if int(q) > 0))
        or "خالی"
    )
    registry.send(
        chat_id,
        registry.T(
            "alliance.view",
            name=al.get("name"),
            owner=registry.player_name(al.get("owner")),
            mode=registry.alliance_mode_text(al),
            count=len(al.get("members", [])),
            max_members=registry.ALLIANCE_MAX,
            members="\n".join(lines),
            vault=al.get("vault", 0),
            shared=al.get("total_shared", 0),
            cartel_level=registry.cartel_level(al),
            cartel_label=registry.cartel_level_data(al).get("label"),
            perks=registry.cartel_perks_text(al),
            next_cost=registry.cartel_next_upgrade_cost(al)
            or registry.T("alliance.max_level"),
        )
        + f"\n\n🏴 مناطق تصرف\u200cشده: {(', '.join(owned) if owned else 'ندارد')}\n🏦 خزانه منابع: {rv_text}",
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_alliance_menu = handle_alliance_menu


def alliance_power(al: dict[str, Any]) -> int:
    total = 0
    for cid in al.get("members", []):
        p = registry.game.get("players", {}).get(cid)
        if p:
            registry.recalc_power(p)
            total += int(p.get("total_attack", 0)) + int(p.get("total_defense", 0))
    return total


registry.alliance_power = alliance_power


def handle_territories(chat_id: str) -> None:
    registry.ensure_territories()
    al = registry.player_alliance(chat_id)
    rows = []
    lines = []
    for k, cfg in registry.TERRITORIES.items():
        data = registry.game["territories"].get(k, {})
        owner = data.get("owner") or "بدون مالک"
        cd_left = 0
        if data.get("last_attack_at"):
            cd_left = max(
                0,
                6 * 3600
                - int(
                    (
                        registry.now()
                        - registry.fromiso(data.get("last_attack_at"), registry.now())
                    ).total_seconds()
                ),
            )
        status = "آماده" if cd_left <= 0 else registry.fmt_cd(cd_left)
        lines.append(
            f"{cfg['label']}\nمالک فعلی: {owner}\nپاداش روزانه: {cfg['reward_text']}\n⏳ قابل حمله: {status}"
        )
        if al:
            rows.append([registry.TERRITORY_ATTACK_BUTTON[k]])
    rows.append([registry.B("alliance"), registry.B("main_menu")])
    registry.send(
        chat_id,
        "🏴 مناطق قابل تصرف\n━━━━━━━━━━━━\n" + "\n\n".join(lines),
        keypad=registry.make_keypad(rows),
    )


registry.handle_territories = handle_territories


def handle_attack_territory(chat_id: str, text: str) -> None:
    key = next(
        (k for k, b in registry.TERRITORY_ATTACK_BUTTON.items() if text == b), None
    )
    if not key:
        return registry.handle_territories(chat_id)
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id,
            "❌ فقط اعضای اتحاد می\u200cتوانند برای تصرف منطقه حمله کنند.",
            keypad=registry.main_keypad(chat_id),
        )
        return
    if len(al.get("members", [])) < 2:
        registry.send(
            chat_id,
            "❌ برای حمله منطقه\u200cای حداقل ۲ عضو در اتحاد لازم است.",
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    registry.ensure_territories()
    data = registry.game["territories"][key]
    cfg = registry.TERRITORIES[key]
    if (
        data.get("last_attack_at")
        and (
            registry.now()
            - registry.fromiso(data.get("last_attack_at"), registry.now())
        ).total_seconds()
        < 6 * 3600
    ):
        left = (
            6 * 3600
            - (
                registry.now()
                - registry.fromiso(data.get("last_attack_at"), registry.now())
            ).total_seconds()
        )
        registry.send(
            chat_id,
            f"⏳ این منطقه تازه جنگیده. زمان باقی\u200cمانده: {registry.fmt_cd(left)}",
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    owned_count = sum(
        1
        for t in registry.game.get("territories", {}).values()
        if t.get("owner") == al.get("name")
    )
    if data.get("owner") != al.get("name") and owned_count >= 2:
        registry.send(
            chat_id,
            "❌ هر اتحاد همزمان حداکثر ۲ منطقه می\u200cتواند داشته باشد.",
            keypad=registry.alliance_keypad(chat_id),
        )
        return
    old_owner_name = data.get("owner")
    attack = int(registry.alliance_power(al) * random.uniform(0.75, 1.25))
    defense = int(cfg["base_def"])
    if old_owner_name and old_owner_name in registry.game.get("alliances", {}):
        defense += int(
            registry.alliance_power(registry.game["alliances"][old_owner_name]) * 0.4
        )
    data["last_attack_at"] = registry.iso(registry.now())
    if attack > defense or not old_owner_name:
        data["owner"] = al.get("name")
        al.setdefault("stats", {})["territory_wins"] = (
            int(al.get("stats", {}).get("territory_wins", 0)) + 1
        )
        for cid in al.get("members", []):
            if cid in registry.game.get("players", {}):
                registry.game["players"][cid].setdefault("stats", {})[
                    "territory_wins"
                ] = (
                    int(
                        registry.game["players"][cid]
                        .get("stats", {})
                        .get("territory_wins", 0)
                    )
                    + 1
                )
        registry.inc_alliance_mission(al, "capture_zone", 1)
        news = f"🏴 منطقه تصرف شد!\nاتحاد {al.get('name')} منطقه {cfg['label']} را گرفت.\nپاداش روزانه: {cfg['reward_text']}"
        registry.add_news(news, important=True)
        if old_owner_name:
            registry.send_group_radio(
                f"🔥 منطقه سقوط کرد\n{old_owner_name} نتونست {cfg['label']} رو نگه داره.\n{al.get('name')} اومد، زد، برد.",
                force=True,
                reason="territory_taken",
            )
        else:
            registry.send_group_radio(
                f"🏴 شهر عوض شد\nاتحاد {al.get('name')} منطقه {cfg['label']} رو گرفت.\nبقیه اتحادها فعلاً فقط دارن نقشه رو نگاه می\u200cکنن.",
                force=True,
                reason="territory_taken",
            )
        msg = f"🏴 منطقه تصرف شد!\n━━━━━━━━━━━━\nاتحاد {al.get('name')} منطقه {cfg['label']} را گرفت.\n\nقدرت حمله: {registry.fmt_num(attack)}\nدفاع منطقه: {registry.fmt_num(defense)}\n\nپاداش روزانه:\n{cfg['reward_text']}"
    else:
        msg = f"💀 حمله منطقه\u200cای شکست خورد!\n━━━━━━━━━━━━\nمنطقه: {cfg['label']}\nقدرت حمله اتحاد: {registry.fmt_num(attack)}\nدفاع منطقه: {registry.fmt_num(defense)}"
    registry.save_game()
    registry.send(chat_id, msg, keypad=registry.alliance_keypad(chat_id))


registry.handle_attack_territory = handle_attack_territory


def award_territory_daily() -> None:
    registry.ensure_territories()
    today = registry.today_key()
    if registry.game.get("last_territory_reward_day") == today:
        return
    changed = False
    for key, data in list(registry.game.get("territories", {}).items()):
        if data.get("last_reward_day") == today or not data.get("owner"):
            continue
        al_name = data.get("owner")
        al = registry.game.get("alliances", {}).get(al_name)
        cfg = registry.TERRITORIES.get(key)
        if not al or not cfg:
            data["owner"] = None
            changed = True
            continue
        members = [
            cid
            for cid in al.get("members", [])
            if cid in registry.game.get("players", {})
        ]
        if not members:
            continue
        if cfg.get("reward"):
            for cid in members:
                for r, q in cfg["reward"].items():
                    registry.add_amount(registry.game["players"][cid], r, int(q))
            changed = True
        if cfg.get("reward_random"):
            rr = cfg["reward_random"]
            picks = random.sample(members, min(int(rr.get("count", 1)), len(members)))
            for cid in picks:
                registry.add_amount(
                    registry.game["players"][cid], "battery", int(rr.get("battery", 1))
                )
            changed = True
        data["last_reward_day"] = today
        changed = True
        registry.add_news(
            f"🏴 پاداش روزانه منطقه {cfg['label']} به اتحاد {al.get('name')} رسید."
        )
    if changed:
        registry.game["last_territory_reward_day"] = today
        registry.save_game()


registry.award_territory_daily = award_territory_daily


def ensure_alliance_missions(al: dict[str, Any]) -> list[dict[str, Any]]:
    if al.get("mission_day") != registry.today_key() or not isinstance(
        al.get("alliance_missions"), list
    ):
        al["mission_day"] = registry.today_key()
        al["alliance_missions"] = []
        for tpl in registry.ALLIANCE_MISSION_TEMPLATES:
            al["alliance_missions"].append(
                {
                    "key": tpl["key"],
                    "title": tpl["title"],
                    "goal": tpl["goal"],
                    "progress": 0,
                    "reward": dict(tpl["reward"]),
                    "claimed": False,
                }
            )
    return al["alliance_missions"]


registry.ensure_alliance_missions = ensure_alliance_missions


def inc_alliance_mission(al: dict[str, Any] | None, key: str, amount: int = 1) -> None:
    if not al:
        return
    missions = registry.ensure_alliance_missions(al)
    for m in missions:
        if m.get("key") == key and (not m.get("claimed")):
            m["progress"] = min(
                int(m.get("goal", 1)), int(m.get("progress", 0)) + int(amount)
            )


registry.inc_alliance_mission = inc_alliance_mission


def inc_alliance_mission_for_player(chat_id: str, key: str, amount: int = 1) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        return
    mapping = {"scavenge": "alliance_scavenge", "barter": "alliance_barter"}
    if key in mapping:
        registry.inc_alliance_mission(al, mapping[key], amount)


registry.inc_alliance_mission_for_player = inc_alliance_mission_for_player


def inc_mission(chat_id: str, key: str, amount: int = 1) -> None:
    registry._orig_inc_mission(chat_id, key, amount)
    registry.inc_alliance_mission_for_player(chat_id, key, amount)


registry.inc_mission = inc_mission


def claim_alliance_mission_reward(al: dict[str, Any], m: dict[str, Any]) -> str:
    reward = m.get("reward", {})
    lines = []
    for k, v in reward.items():
        v = int(v)
        if k == "vault_water":
            al["vault"] = int(al.get("vault", 0)) + v
            lines.append(f"خزانه +{v} آب")
        elif k.startswith("vault_"):
            res = k.split("_", 1)[1]
            al.setdefault("resource_vault", {})[res] = (
                int(al.setdefault("resource_vault", {}).get(res, 0)) + v
            )
            lines.append(f"خزانه منابع: {registry.fmt_res_amount(res, v)}")
        elif k == "member_cache_medium":
            for cid in al.get("members", []):
                registry.add_cache_to_player(cid, "medium", v)
            lines.append(f"📦 صندوق متوسط × {v} برای اعضا")
        elif k == "season_points":
            al["season_points"] = int(al.get("season_points", 0)) + v
            lines.append(f"امتیاز اتحاد +{v}")
    m["claimed"] = True
    m["claimed_at"] = registry.iso(registry.now())
    registry.send_group_radio(
        f"🤝 کارتل بیدار شد\nاتحاد {al.get('name')} یک مأموریت اتحاد را کامل کرد: {m.get('title')}",
        force=True,
        reason="alliance_mission",
    )
    return " + ".join(lines) if lines else "—"


registry.claim_alliance_mission_reward = claim_alliance_mission_reward


def handle_alliance_missions(chat_id: str) -> None:
    al = registry.player_alliance(chat_id)
    if not al:
        registry.send(
            chat_id, "❌ عضو اتحادی نیستی.", keypad=registry.main_keypad(chat_id)
        )
        return
    missions = registry.ensure_alliance_missions(al)
    receipts = []
    lines = []
    for m in missions:
        ready = int(m.get("progress", 0)) >= int(m.get("goal", 1))
        if ready and (not m.get("claimed")):
            receipts.append(
                f"• {m.get('title')}: {registry.claim_alliance_mission_reward(al, m)}"
            )
        icon = "✅" if m.get("claimed") else "🎁" if ready else "⬜"
        status = (
            "دریافت شد"
            if m.get("claimed")
            else "آماده دریافت"
            if ready
            else "در حال انجام"
        )
        lines.append(
            f"{icon} {m.get('title')}\nپیشرفت: {m.get('progress', 0)}/{m.get('goal', 1)}\nوضعیت: {status}\n🎁 پاداش: {registry.fmt_any_reward(m.get('reward', {}))}"
        )
    note = "\n\n✅ پاداش\u200cهای واریزشده:\n" + "\n".join(receipts) if receipts else ""
    registry.save_game()
    registry.send(
        chat_id,
        "🤝 مأموریت\u200cهای اتحاد امروز\n━━━━━━━━━━━━\n" + "\n\n".join(lines) + note,
        keypad=registry.alliance_keypad(chat_id),
    )


registry.handle_alliance_missions = handle_alliance_missions


def pick_group_radio_subject() -> dict[str, Any]:
    players = [
        (cid, p)
        for cid, p in registry.game.get("players", {}).items()
        if p.get("registered") and (not p.get("banned"))
    ]
    if not players:
        return {"type": "rumor"}
    bounties = [
        b
        for b in registry.game.get("bounty_contracts", [])
        if b.get("status") == "open"
    ]
    if bounties and random.random() < 0.18:
        b = random.choice(bounties)
        return {
            "type": "bounty",
            "target": b.get("target"),
            "reward": b.get("reward", {}),
        }
    shielded = [(cid, p) for cid, p in players if registry.is_shielded(p)]
    if shielded and random.random() < 0.14:
        cid, p = random.choice(shielded)
        return {"type": "shielded", "player": cid}
    rich = [
        (cid, p)
        for cid, p in players
        if int(p.get("water", 0)) >= 500 and (not registry.is_shielded(p))
    ]
    if rich and random.random() < 0.16:
        cid, p = max(rich, key=lambda x: int(x[1].get("water", 0)))
        return {"type": "rich_unshielded", "player": cid, "water": p.get("water", 0)}
    rows = registry.ranked_players()
    if rows and random.random() < 0.25:
        return {"type": "top_rank", "player": rows[0][0]}
    if len(rows) >= 2 and random.random() < 0.15:
        gap = max(0, rows[0][1] - rows[1][1])
        return {"type": "chaser", "player": rows[1][0], "gap": gap}
    victims = sorted(
        players,
        key=lambda x: int(x[1].get("stats", {}).get("raids_received", 0)),
        reverse=True,
    )
    if (
        victims
        and victims[0][1].get("stats", {}).get("raids_received", 0) > 0
        and (random.random() < 0.18)
    ):
        return {"type": "victim", "player": victims[0][0]}
    low = rows[-1][0] if rows else random.choice(players)[0]
    if random.random() < 0.2:
        return {"type": "low_rank", "player": low}
    active_alliances = [
        al
        for al in registry.game.get("alliances", {}).values()
        if isinstance(al, dict) and al.get("members")
    ]
    if active_alliances and random.random() < 0.15:
        al = max(
            active_alliances,
            key=lambda a: int(a.get("vault", 0)) + len(a.get("members", [])) * 100,
        )
        return {"type": "alliance", "alliance": al}
    return {"type": "inactive", "player": random.choice(players)[0]}


registry.pick_group_radio_subject = pick_group_radio_subject


def render_group_radio_v2(subject: dict[str, Any]) -> str:
    typ = subject.get("type")
    if typ == "low_rank":
        return f"🐀 گزارش کف جدول\n{registry.player_name(subject['player'])} هنوز ته جدوله، ولی حداقل هنوز نفس می\u200cکشه.\nدو تا گشت، یه معاوضه درست، شاید از زیر خاک بیاد بیرون."
    if typ == "inactive":
        return f"📻 رادیوی زباله\u200cزار\n{registry.player_name(subject['player'])} امروز اونقدر ساکت بوده که موش\u200cهای گاراژش فکر کردن صاحب نداره."
    if typ == "top_rank":
        return f"👑 تاج روی سر {registry.player_name(subject['player'])} فعلاً مونده.\nولی تو این شهر، تاج بیشتر شبیه هدف تیراندازیه تا افتخار."
    if typ == "chaser":
        return f"📡 هشدار رشد\n{registry.player_name(subject['player'])} فقط {registry.fmt_num(subject.get('gap', 0))} امتیاز تا تاج فاصله داره.\nیکی باید جلوشو بگیره، یا خودش بقیه رو می\u200cگیره."
    if typ == "rich_unshielded":
        return f"💧 بوی آب پیچیده\n{registry.player_name(subject['player'])} با {registry.fmt_num(subject.get('water', 0))} آب بدون محافظ نشسته.\nغارتگرها لازم نیست زرنگ باشن؛ فقط باید بیدار باشن."
    if typ == "shielded":
        return f"🛡️ ترس یا عقل؟\n{registry.player_name(subject['player'])} محافظ روشن کرد.\nبعضیا میگن ترسیده، بعضیا میگن حداقل مغز داره."
    if typ == "victim":
        return f"🚨 قربانی روز\n{registry.player_name(subject['player'])} بیشتر از درِ زنگ\u200cزده کتک خورده.\nدکمه انتقام برای قشنگی نیست."
    if typ == "bounty":
        return f"🎯 اسم روی دیوار\nبرای زدن {registry.player_name(subject.get('target'))} جایزه گذاشتن:\n{registry.fmt_res_dict(subject.get('reward', {}))}\n\nحالا ببینیم شهر هنوز دندون داره یا نه."
    if typ == "alliance":
        al = subject.get("alliance", {})
        return f"🤝 کارتل بیدار شد\nاتحاد {al.get('name')} امروز بیشتر از بقیه صدا داده.\nبقیه اتحادها فعلاً بیشتر شبیه گروه چت\u200cاند تا کارتل."
    return registry.group_radio_rumor_text()


registry.render_group_radio_v2 = render_group_radio_v2


def group_radio_periodic_text() -> str:
    boss = registry.active_boss()
    if boss and random.random() < 0.35:
        return registry.group_radio_boss_status_text(boss)
    return registry.render_group_radio_v2(registry.pick_group_radio_subject())


registry.group_radio_periodic_text = group_radio_periodic_text


def periodic_group_radio() -> None:
    registry.maybe_setup_night_smuggler()
    registry.award_territory_daily()
    registry._orig_periodic_group_radio()


registry.periodic_group_radio = periodic_group_radio


def season_special_awards(rows: list[tuple[str, int]]) -> list[str]:
    awards = []
    players = [(cid, registry.game["players"][cid]) for cid, _ in rows]

    def best_by(stat, title):
        cand = [(cid, int(p.get("stats", {}).get(stat, 0))) for cid, p in players]
        cand = [x for x in cand if x[1] > 0]
        if cand:
            cid, val = max(cand, key=lambda x: x[1])
            awards.append(
                f"{title}: {registry.player_name(cid)} ({registry.fmt_num(val)})"
            )
            return cid

    best_by("scavenges", "فعال\u200cترین گشت\u200cزن")
    trader = [
        (
            cid,
            int(p.get("stats", {}).get("market_sales", 0))
            + int(p.get("stats", {}).get("market_buys", 0))
            + int(p.get("stats", {}).get("barter_done", 0)),
        )
        for cid, p in players
    ]
    trader = [x for x in trader if x[1] > 0]
    if trader:
        cid, val = max(trader, key=lambda x: x[1])
        awards.append(
            f"بهترین تاجر/معاوضه\u200cگر: {registry.player_name(cid)} ({registry.fmt_num(val)})"
        )
    best_by("boss_damage", "بیشترین آسیب به باس")
    best_by("alliance_shared", "بیشترین کمک به اتحاد")
    best_by("revenge_wins", "بیشترین انتقام موفق")
    best_by("bounty_claimed", "بیشترین قرارداد جایزه انجام\u200cشده")
    newcomers = [
        (cid, score)
        for cid, score in rows
        if int(registry.game["players"][cid].get("career", {}).get("seasons_played", 0))
        <= 0
    ]
    if newcomers:
        awards.append(
            f"بهترین تازه\u200cوارد سیزن: {registry.player_name(newcomers[0][0])}"
        )
    return awards


registry.season_special_awards = season_special_awards


def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:
    st = registry.game.get("chat_states", {}).get(chat_id)
    if st:
        state = st.get("state")
        if state == "awaiting_smuggler_qty":
            registry.handle_smuggler_qty(chat_id, text)
            return True
        if state == "awaiting_bounty_order":
            registry.handle_create_bounty(chat_id, text)
            return True
    return registry._orig_handle_state(chat_id, text, sender_id)


registry.handle_state = handle_state


def dispatch(
    chat_id: str, text: str, sender_name: str, button_id: str = "", sender_id: str = ""
) -> None:
    text = (text or button_id or "").strip()
    if not registry.game.get("players", {}).get(chat_id, {}).get("registered"):
        return registry._orig_dispatch(chat_id, text, sender_name, button_id, sender_id)
    registry.expire_bounty_contracts()
    registry.expire_revenge_targets()
    registry.maybe_setup_night_smuggler()
    if registry.handle_state(chat_id, text, sender_id):
        return
    if text == registry.B("night_smuggler"):
        return registry.handle_night_smuggler(chat_id)
    if text in registry.NIGHT_SMUGGLER_BUY_BUTTON.values():
        return registry.handle_smuggler_select(chat_id, text)
    if text in registry.CACHE_OPEN_BUTTON.values():
        return registry.handle_open_cache_type(chat_id, text)
    if text in registry.USE_ITEM_BUTTON.values():
        return registry.handle_use_consumable(chat_id, text)
    if text == registry.B("revenge_menu"):
        return registry.handle_revenge_menu(chat_id)
    if text.startswith("🔥 انتقام #"):
        return registry.handle_revenge_attack(chat_id, text)
    if text == registry.B("bounty_board"):
        return registry.handle_bounty_board(chat_id)
    if text == registry.B("bounty_create"):
        return registry.handle_create_bounty_prompt(chat_id)
    if text == registry.B("bounty_my"):
        return registry.handle_my_bounties(chat_id)
    if text.startswith("لغو جایزه #"):
        return registry.handle_cancel_bounty(chat_id, text)
    if text == registry.B("territories"):
        return registry.handle_territories(chat_id)
    if text in registry.TERRITORY_ATTACK_BUTTON.values():
        return registry.handle_attack_territory(chat_id, text)
    if text == registry.B("alliance_missions"):
        return registry.handle_alliance_missions(chat_id)
    return registry._orig_dispatch(chat_id, text, sender_name, button_id, sender_id)


registry.dispatch = dispatch
