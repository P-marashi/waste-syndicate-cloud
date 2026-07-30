from datetime import timedelta
from typing import Any

from ..registry import registry


def default_season(season_id: int = 1) -> dict[str, Any]:
    start = registry.now()
    end = start + timedelta(days=registry.SEASON_LENGTH_DAYS)

    return {
        "id": season_id,
        "start": registry.iso(start),
        "end": registry.iso(end),
        "archives": [],
    }


def generate_ref_code(chat_id: str) -> str:
    base = abs(hash(str(chat_id))) % 900000 + 100000
    return f"REF{base}"


def new_player(
    name: str | None = None,
    chat_id: str = "",
) -> dict[str, Any]:
    return {
        "name": name or "",
        "registered": bool(name),
        "level": 1,
        "xp": 0,
        "hp": 100,
        "honor": 0,
        "water": 140,
        "resources": {
            "scrap": 55,
            "plastic": 45,
            "glass": 25,
            "battery": 0,
            "copper": 0,
        },
        "inventory": {},
        "buildings": {},
        "upgrades_in_progress": [],
        "scavenge_cd": None,
        "raid_cd": None,
        "boss_cd": None,
        "shield_until": None,
        "alliance": None,
        "total_attack": 0,
        "total_defense": 0,
        "last_passive": registry.iso(registry.now()),
        "registered_at": registry.iso(registry.now()),
        "daily_last": None,
        "daily_streak": 0,
        "ref_code": generate_ref_code(chat_id),
        "referred_by": None,
        "referral_used": False,
        "referrals_count": 0,
        "pending_referral": None,
        "loot_caches": 0,
        "mission_day": None,
        "daily_missions": [],
        "season_points_bonus": 0,
        "career": {
            "seasons_played": 0,
            "best_rank": None,
            "best_score": 0,
        },
        "stats": {
            "scavenges": 0,
            "scavenge_success": 0,
            "raids_done": 0,
            "raids_received": 0,
            "water_earned": 0,
            "water_lost": 0,
            "market_sales": 0,
            "market_buys": 0,
            "barter_done": 0,
            "rentals_given": 0,
            "rentals_taken": 0,
            "rental_bad_debt": 0,
            "alliance_shared": 0,
            "alliance_received": 0,
            "boss_damage": 0,
            "boss_hits": 0,
            "caches_opened": 0,
            "legendary_found": 0,
            "missions_completed": 0,
            "group_raids": 0,
        },
        "action_log": [],
        "banned": False,
        "ban_reason": "",
        "banned_at": None,
        "banned_by": None,
        "admin_notes": [],
    }


def default_game() -> dict[str, Any]:
    return {
        "version": 4,
        "players": {},
        "alliances": {},
        "market_orders": [],
        "next_order_id": 1,
        "barter_orders": [],
        "next_barter_id": 1,
        "resource_rentals": [],
        "next_rental_id": 1,
        "market_supply": {r: 0 for r in registry.RESOURCES},
        "private_messages": [],
        "next_private_message_id": 1,
        "admin_logs": [],
        "next_admin_log_id": 1,
        "last_system_restock": None,
        "system_stock_log": [],
        "world_event_active": None,
        "last_daily_event": None,
        "world_boss": None,
        "last_boss_spawn": None,
        "news_feed": [],
        "last_group_radio_at": None,
        "last_group_boss_report_at": None,
        "last_group_rank1": None,
        "group_radio_log": [],
        "season": default_season(1),
        "chat_states": {},
        "next_offset_id": None,
    }
