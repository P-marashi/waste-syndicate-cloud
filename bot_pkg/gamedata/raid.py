COOLDOWNS = {
    "scavenge": 15 * 60,
    "raid": 45 * 60,
}

RAID_BUCKETS = {
    "weak": {
        "button_key": "raid_weak",
        "title": "ضعیف",
        "loot_mod": 0.65,
        "atk_mod": 1.1,
        "xp": 3,
        "honor_win": 1,
        "honor_lose": -1,
    },
    "medium": {
        "button_key": "raid_medium",
        "title": "متوسط",
        "loot_mod": 1.0,
        "atk_mod": 1.0,
        "xp": 6,
        "honor_win": 6,
        "honor_lose": -4,
    },
    "strong": {
        "button_key": "raid_strong",
        "title": "قوی",
        "loot_mod": 1.35,
        "atk_mod": 0.9,
        "xp": 10,
        "honor_win": 12,
        "honor_lose": -7,
    },
}
