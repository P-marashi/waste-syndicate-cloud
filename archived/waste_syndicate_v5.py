# -*- coding: utf-8 -*-
"""
Waste Syndicate Bot v4 — Local Keypad Edition
Rubika Bot Game

Run:
  pip install requests
  python waste_syndicate_bot_v4_seasonal.py

Files created/used:
  waste_syndicate_save.json       -> players, alliances, market, seasons
  waste_syndicate_texts_fa.json   -> all visible Persian texts/buttons

Notes:
- Inline buttons are intentionally NOT used. Everything is chat_keypad/text based.
- Replace BOT_TOKEN or set environment variable BOT_TOKEN before running.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN = os.getenv(
    "BOT_TOKEN", "BGAIAH0KKQWFDMJIKWGIJIWTUFSNGDFWAFLXUOPOKXBSAZWJTMVCHPWGAIMRZYEG"
)
API_BASE = f"https://botapi.rubika.ir/v3/{BOT_TOKEN}"
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "3"))
SAVE_FILE = Path(os.getenv("SYNDICATE_SAVE", "waste_syndicate_save.json"))
TEXTS_FILE = Path(os.getenv("SYNDICATE_TEXTS", "waste_syndicate_texts_fa.json"))
DEBUG = os.getenv("SYNDICATE_DEBUG", "1") == "1"
OFFSET_FILE = "offset.json"
SKIP_PENDING_ON_START = True

# ====================== بالانس بازی ======================
SEASON_LENGTH_DAYS = int(os.getenv("SEASON_LENGTH_DAYS", "21"))
DAILY_EVENT_HOUR = int(os.getenv("DAILY_EVENT_HOUR", "7"))

ALLIANCE_MAX = 8
ALLIANCE_TAX_RATE = 0.06  # مالیات اتحاد از درآمد
ALLIANCE_BONUS_RATE = 0.04  # بونوس سیستم به اتحاد
ALLIANCE_DISTRIBUTE_RATE = 0.25  # درصد پخش به اعضا

SHIELD_DURATION = 12 * 3600  # ۱۲ ساعت محافظ

# ====================== سیستم بازار ======================
SYSTEM_DAILY_RESTOCK = {
    "scrap": 25,
    "plastic": 20,
    "glass": 12,
    "battery": 3,
    "copper": 6,
}
SYSTEM_STOCK_CAP = {
    "scrap": 75,
    "plastic": 60,
    "glass": 36,
    "battery": 9,
    "copper": 18,
}

# ====================== لاگ و محدودیت‌ها ======================
MAX_ACTION_LOG = 60
MAX_PRIVATE_MESSAGES = 500
MAX_ADMIN_LOG = 300
ADMIN_PLAYERS_PAGE_SIZE = 8

# ====================== ادمین و گروه ======================
ADMIN_IDS = {
    x.strip()
    for x in os.getenv("ADMIN_IDS", "u0Jgdwc0ef4e0a32e417ae6f75a7c47f").split(",")
    if x.strip()
}

GAME_GROUP_ID = os.getenv("GAME_GROUP_ID", "g0IEJRv03995aeeeee2977f77fc3babe").strip()
GROUP_RADIO_ENABLED = os.getenv("GROUP_RADIO_ENABLED", "1") == "1"
GROUP_RADIO_MIN_INTERVAL = int(os.getenv("GROUP_RADIO_MIN_INTERVAL", str(2 * 3600)))
GROUP_BOSS_REPORT_INTERVAL = int(os.getenv("GROUP_BOSS_REPORT_INTERVAL", str(30 * 60)))

# ══════════════════════════════════════════════════════
#  TEXT SYSTEM
# ══════════════════════════════════════════════════════
TEXTS: dict[str, Any] = {}


def load_offset():
    if not os.path.exists(OFFSET_FILE):
        return None

    try:
        with open(OFFSET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("next_offset_id")
    except Exception:
        return None


def save_offset(offset):
    if not offset:
        return

    try:
        with open(OFFSET_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"next_offset_id": offset},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        print("[OFFSET]", e)


def skip_old_updates():
    """
    موقع روشن شدن بات،
    تمام پیام‌های قدیمی فقط خوانده میشن
    ولی Process نمیشن.
    """

    print("⏩ Skipping pending updates...")

    offset = load_offset()

    while True:
        payload = {"limit": 100}

        if offset:
            payload["offset_id"] = offset

        resp = api("getUpdates", payload)

        updates = resp.get("updates", [])

        next_offset = resp.get("next_offset_id")

        if next_offset:
            offset = next_offset
            save_offset(offset)

        if not updates:
            break

    print("✅ Bot synced.")


def deep_get(d: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def load_texts() -> None:
    global TEXTS
    if not TEXTS_FILE.exists():
        raise SystemExit(
            f"Text file not found: {TEXTS_FILE}\n"
            "Keep waste_syndicate_texts_fa.json next to this script."
        )
    with TEXTS_FILE.open("r", encoding="utf-8") as f:
        TEXTS = json.load(f)


def T(key: str, **kwargs: Any) -> str:
    val = deep_get(TEXTS, key, key)
    if isinstance(val, list):
        val = random.choice(val)
    if not isinstance(val, str):
        return str(val)
    try:
        return val.format(**kwargs)
    except Exception:
        return val


def B(key: str) -> str:
    return T(f"buttons.{key}")


# ══════════════════════════════════════════════════════
#  GAME TABLES
# ══════════════════════════════════════════════════════
RESOURCES = ["scrap", "plastic", "glass", "battery", "copper"]
RES_ICON = {
    "water": "💧",
    "scrap": "♻️",
    "plastic": "🗑️",
    "glass": "🫙",
    "battery": "🔋",
    "copper": "🔶",
}
RES_NAME = {
    "water": "آب",
    "scrap": "اوراق",
    "plastic": "پلاستیک",
    "glass": "شیشه",
    "battery": "باتری",
    "copper": "مس",
}
RES_ALIASES = {
    "اوراق": "scrap",
    "آهن": "scrap",
    "اهن": "scrap",
    "scrap": "scrap",
    "پلاستیک": "plastic",
    "plastic": "plastic",
    "شیشه": "glass",
    "شيشه": "glass",
    "glass": "glass",
    "باتری": "battery",
    "باطری": "battery",
    "battery": "battery",
    "مس": "copper",
    "copper": "copper",
}
BASE_PRICE = {"scrap": 60, "plastic": 30, "glass": 50, "battery": 120, "copper": 80}

CARTEL_LEVELS = {
    1: {
        "label": "دار و دسته محلی",
        "upgrade_cost": 0,
        "water_bonus": 0.00,
        "score_bonus": 0,
    },
    2: {
        "label": "کارتل محله",
        "upgrade_cost": 600,
        "water_bonus": 0.03,
        "score_bonus": 400,
    },
    3: {
        "label": "کارتل شهر",
        "upgrade_cost": 1800,
        "water_bonus": 0.06,
        "score_bonus": 1000,
    },
    4: {
        "label": "سندیکای منطقه",
        "upgrade_cost": 4500,
        "water_bonus": 0.10,
        "score_bonus": 2200,
    },
    5: {
        "label": "امپراتوری زباله",
        "upgrade_cost": 10000,
        "water_bonus": 0.15,
        "score_bonus": 5000,
    },
}
MAX_CARTEL_LEVEL = max(CARTEL_LEVELS)

LEVELS = {
    1: {"xp": 10, "label": "مبتدی"},
    2: {"xp": 25, "label": "بازمانده"},
    3: {"xp": 60, "label": "دلال"},
    4: {"xp": 120, "label": "تاجر"},
    5: {"xp": 220, "label": "سردسته"},
    6: {"xp": 380, "label": "کارتل"},
    7: {"xp": 600, "label": "ارباب"},
    8: {"xp": 900, "label": "امپراتور"},
    9: {"xp": 1300, "label": "افسانه"},
    10: {"xp": 9999, "label": "پادشاه زباله 👑"},
}
HONOR_TITLES = [
    (-9999, -1000, "ضعیف‌کش بی‌قایه ☠️"),
    (-999, -500, "غارتگر سیاه 🖤"),
    (-499, -1, "آشوبگر 😈"),
    (0, 0, "بی‌طرف ⚪"),
    (1, 199, "محافظ 🟢"),
    (200, 499, "قهرمان ⭐"),
    (500, 999, "لژیونر 🏅"),
    (1000, 9999, "پاسدار افسانه‌ای 🌟"),
]

ZONES = {
    "alley": {
        "risk": 1,
        "loot_min": 3,
        "loot_max": 7,
        "xp": 2,
        "cd_min": 8,
        "label_key": "scavenge_alley",
        "desc": "کم‌خطر، مناسب شروع",
    },
    "suburb": {
        "risk": 3,
        "loot_min": 6,
        "loot_max": 13,
        "xp": 4,
        "cd_min": 12,
        "label_key": "scavenge_suburb",
        "desc": "ریسک متوسط، لوت خوب",
    },
    "center": {
        "risk": 5,
        "loot_min": 10,
        "loot_max": 24,
        "xp": 7,
        "cd_min": 18,
        "label_key": "scavenge_center",
        "desc": "خطرناک، منابع کمیاب",
    },
    "bunker": {
        "risk": 7,
        "loot_min": 18,
        "loot_max": 42,
        "xp": 11,
        "cd_min": 25,
        "label_key": "scavenge_bunker",
        "desc": "مرگبار، اما پاداش سنگین",
    },
}

BUILDINGS = {
    "purifier": {
        "label": "💧 دستگاه تصفیه آب",
        "levels": {
            1: {
                "cost": {"scrap": 8, "plastic": 4},
                "prod": 12,
                "time": 90,
                "def": 0,
                "atk": 0,
            },
            2: {
                "cost": {"scrap": 20, "plastic": 10},
                "prod": 24,
                "time": 240,
                "def": 0,
                "atk": 0,
            },
            3: {
                "cost": {"scrap": 45, "copper": 8},
                "prod": 42,
                "time": 600,
                "def": 0,
                "atk": 0,
            },
            4: {
                "cost": {"scrap": 90, "copper": 20},
                "prod": 68,
                "time": 1200,
                "def": 0,
                "atk": 0,
            },
            5: {
                "cost": {"scrap": 180, "copper": 50, "battery": 10},
                "prod": 105,
                "time": 2400,
                "def": 0,
                "atk": 0,
            },
        },
    },

    "wall": {
        "label": "🧱 دیوار دفاعی",
        "levels": {
            1: {
                "cost": {"scrap": 5, "plastic": 3},
                "time": 60,
                "def": 120,
                "atk": 0,
            },
            2: {
                "cost": {"scrap": 15, "plastic": 8},
                "time": 180,
                "def": 280,
                "atk": 0,
            },
            3: {
                "cost": {"scrap": 35, "copper": 5},
                "time": 480,
                "def": 520,
                "atk": 0,
            },
            4: {
                "cost": {"scrap": 70, "copper": 15},
                "time": 900,
                "def": 900,
                "atk": 0,
            },
            5: {
                "cost": {"scrap": 150, "copper": 40, "battery": 8},
                "time": 1800,
                "def": 1450,
                "atk": 0,
            },
        },
    },

    "armory": {
        "label": "⚔️ زرادخانه",
        "levels": {
            1: {
                "cost": {"scrap": 6, "plastic": 4},
                "time": 60,
                "atk": 90,
            },
            2: {
                "cost": {"scrap": 18, "plastic": 10},
                "time": 180,
                "atk": 210,
            },
            3: {
                "cost": {"scrap": 40, "copper": 6},
                "time": 480,
                "atk": 390,
            },
            4: {
                "cost": {"scrap": 80, "copper": 18},
                "time": 900,
                "atk": 680,
            },
            5: {
                "cost": {"scrap": 160, "copper": 45, "battery": 9},
                "time": 1800,
                "atk": 1080,
            },
        },
    },

    "lab": {
        "label": "🔬 آزمایشگاه",
        "levels": {
            1: {
                "cost": {"scrap": 10, "glass": 5, "battery": 2},
                "prod": 0,
                "time": 180,
                "def": 0,
                "atk": 0,
                "discount": 0.03,
            },
            2: {
                "cost": {"scrap": 25, "glass": 12, "battery": 5},
                "prod": 0,
                "time": 450,
                "def": 0,
                "atk": 0,
                "discount": 0.07,
            },
            3: {
                "cost": {"scrap": 60, "glass": 30, "battery": 12},
                "prod": 0,
                "time": 900,
                "def": 0,
                "atk": 0,
                "discount": 0.12,
            },
        },
    },

    "market_stall": {
        "label": "🏪 غرفه بازار",
        "levels": {
            1: {
                "cost": {"scrap": 8, "plastic": 6},
                "prod": 0,
                "time": 120,
                "def": 0,
                "atk": 0,
                "fee_cut": 0.02,
            },
            2: {
                "cost": {"scrap": 20, "plastic": 15},
                "prod": 0,
                "time": 300,
                "def": 0,
                "atk": 0,
                "fee_cut": 0.04,
            },
            3: {
                "cost": {"scrap": 50, "plastic": 30},
                "prod": 0,
                "time": 720,
                "def": 0,
                "atk": 0,
                "fee_cut": 0.07,
            },
        },
    },

    "hospital": {
        "label": "🏥 درمانگاه",
        "levels": {
            1: {
                "cost": {"plastic": 8, "glass": 4},
                "prod": 0,
                "time": 150,
                "def": 40,
                "atk": 0,
                "heal_bonus": 5,
            },
            2: {
                "cost": {"plastic": 20, "glass": 12},
                "prod": 0,
                "time": 360,
                "def": 90,
                "atk": 0,
                "heal_bonus": 12,
            },
            3: {
                "cost": {"plastic": 45, "glass": 30, "copper": 5},
                "prod": 0,
                "time": 840,
                "def": 170,
                "atk": 0,
                "heal_bonus": 25,
            },
        },
    },
}

CRAFT_ITEMS = {
    "shock_rifle": {
        "cost": {"water": 220, "scrap": 8, "battery": 3, "copper": 5},
        "atk": 65,
        "label": "⚡ تفنگ شوکر",
    },
    "nail_crossbow": {
        "cost": {"water": 120, "scrap": 18, "plastic": 8, "copper": 3},
        "atk": 45,
        "label": "🏹 کمان میخ‌پرتاب",
    },
    "scrap_shotgun": {
        "cost": {"water": 360, "scrap": 30, "copper": 10, "battery": 3},
        "atk": 125,
        "label": "🔫 شاتگان اوراقی",
    },
    "plasma_cannon": {
        "cost": {"water": 620, "battery": 10, "copper": 16, "glass": 6},
        "atk": 190,
        "label": "🔴 کانون پلاسما",
    },
    "flame_thrower": {
        "cost": {"water": 900, "battery": 14, "copper": 22, "plastic": 18, "glass": 4},
        "atk": 285,
        "label": "🔥 شعله‌افکن زباله‌سوز",
    },
    "drone_swarm": {
        "cost": {
            "water": 1500,
            "battery": 22,
            "copper": 34,
            "plastic": 25,
            "glass": 12,
        },
        "atk": 480,
        "label": "🛸 دسته پهپاد شکاری",
    },
    "heavy_armor": {
        "cost": {"water": 180, "scrap": 18, "plastic": 10},
        "def": 240,
        "label": "🛡️ زره سنگین",
    },
    "riot_shield": {
        "cost": {"water": 260, "scrap": 26, "plastic": 14, "glass": 5},
        "def": 330,
        "label": "🚧 سپر ضدشورش",
    },
    "shield_gen": {
        "cost": {"water": 430, "battery": 7, "glass": 8, "copper": 5},
        "def": 460,
        "label": "🔰 سپر انرژی",
    },
    "bunker_plate": {
        "cost": {"water": 900, "scrap": 55, "copper": 20, "battery": 6},
        "def": 900,
        "label": "🏯 صفحه بنکر",
    },
    "medkit": {
        "cost": {"water": 60, "plastic": 5, "glass": 3},
        "heal": 40,
        "label": "🩹 کیت پزشکی",
    },
    "mega_medkit": {
        "cost": {"water": 180, "plastic": 14, "glass": 10, "battery": 3},
        "heal": 100,
        "label": "💊 مگا-کیت پزشکی",
    },
    "adrenal_shot": {
        "cost": {"water": 140, "plastic": 10, "glass": 7, "battery": 2},
        "heal": 65,
        "label": "💉 آمپول آدرنالین",
    },
    "emp_bomb": {
        "cost": {"water": 420, "battery": 8, "copper": 12, "glass": 5},
        "special": "emp",
        "label": "💣 بمب EMP",
    },
    "spy_drone": {
        "cost": {"water": 650, "battery": 8, "copper": 12, "plastic": 10, "glass": 6},
        "special": "spy",
        "label": "🚁 پهپاد جاسوسی",
    },
    "smoke_mine": {
        "cost": {"water": 180, "scrap": 14, "plastic": 12, "glass": 4},
        "special": "smoke",
        "label": "🌫️ مین دودزا",
    },
    "repair_kit": {
        "cost": {"water": 220, "scrap": 18, "plastic": 10, "copper": 2},
        "special": "repair",
        "label": "🔧 کیت تعمیر",
    },
    "shield_generator": {
        "cost": {"water": 250, "battery": 1, "copper": 3, "glass": 5},
        "special": "shield",
        "duration": 12 * 3600,
        "label": "🛡️ ژنراتور محافظ",
    },
}

SPECIAL_EFFECT_TEXT = {
    "emp_bomb": "💣 بمب EMP: در غارت بعدی خودکار مصرف می‌شود و دفاع هدف را ۲۵٪ کم می‌کند.",
    "spy_drone": "🚁 پهپاد جاسوسی: مصرفی است؛ با هر عددش می‌توانی یک بازیکن مشخص را برای غارت دقیق انتخاب کنی.",
    "smoke_mine": "🌫️ مین دودزا: در شکست گشت خودکار مصرف می‌شود و آسیب و ضرر منابع را نصف می‌کند.",
    "repair_kit": "🔧 کیت تعمیر: فقط وقتی ارتقای فعال داری مفید است و زمان ارتقاها را نصف می‌کند.",
    "shield_generator": "🛡️ ژنراتور محافظ: ۱۲ ساعت محافظ فعال می‌کند؛ اگر خودت غارت کنی می‌شکند.",
}


# آیتم‌های افسانه‌ای از کارگاه ساخته نمی‌شوند؛ فقط از صندوق، باس یا گشت خیلی نادر می‌افتند.
LEGENDARY_ITEMS = {
    "reactor_core": {"atk": 180, "def": 80, "label": "☢️ هسته راکتور قدیمی"},
    "king_crown": {"atk": 60, "def": 260, "label": "👑 تاج پادشاه زباله"},
    "ancient_tank": {"atk": 320, "def": 120, "label": "🛞 تانک اوراقی باستانی"},
    "water_heart": {"atk": 0, "def": 380, "label": "💙 قلب تصفیه‌گر"},
    "void_blade": {"atk": 420, "def": 50, "label": "⚔️ تیغ خلاء"},
    "rad_shield": {"atk": 80, "def": 450, "label": "☢️ سپر پرتوزا"},
    "ghost_drone": {"atk": 250, "def": 180, "label": "👻 پهپاد روح"},
    "blood_fuel": {"atk": 300, "def": 0, "label": "🩸 سوخت خون"},
    "ruin_cannon": {"atk": 520, "def": 90, "label": "🛠️ توپ ویرانه"},
    "eternal_core": {"atk": 150, "def": 520, "label": "🌌 هسته ابدی"},
}

BOSS_SPAWN_EVERY = int(os.getenv("BOSS_SPAWN_EVERY", str(random.randint(5, 9) * 3600)))
BOSS_MIN_INTERVAL = 48 * 3600
BOSS_MAX_INTERVAL = 72 * 3600
MAX_BOSSES_PER_WEEK = 3
BOSS_DURATION = 4 * 3600
BOSS_ATTACK_CD = 15 * 60

BOSS_TEMPLATES = [
    {"name": "☣️ تایتان زباله", "hp": 90000, "atk": 14, "reward_mod": 1.0},
    {"name": "🦂 عقرب اسیدی", "hp": 70000, "atk": 18, "reward_mod": 0.9},
    {"name": "🤖 ماشین جنگی اوراقی", "hp": 120000, "atk": 22, "reward_mod": 1.25},
    {"name": "🐉 اژدهای دودزا", "hp": 150000, "atk": 26, "reward_mod": 1.5},
]

DAILY_MISSION_TEMPLATES = [
    {
        "key": "scavenge",
        "title": "۳ بار گشت‌زنی کن",
        "goal": 3,
        "reward": {"water": 80, "xp": 5},
    },
    {
        "key": "raid",
        "title": "۱ بار غارت انجام بده",
        "goal": 1,
        "reward": {"water": 90, "xp": 6},
    },
    {
        "key": "market_sell",
        "title": "۱ معامله در بازار یا معاوضه انجام بده",
        "goal": 1,
        "reward": {"copper": 2},
    },
    {
        "key": "barter",
        "title": "۱ معاوضه منابع انجام بده",
        "goal": 1,
        "reward": {"scrap": 20, "xp": 4},
    },
    {
        "key": "boss_attack",
        "title": "۱ بار به باس جهانی حمله کن",
        "goal": 1,
        "reward": {"loot_cache": 1},
    },
    {
        "key": "open_cache",
        "title": "۱ صندوق شانسی باز کن",
        "goal": 1,
        "reward": {"battery": 1, "xp": 5},
    },
]

DAILY_EVENTS = [
    {
        "id": "acid_storm",
        "title": "⛈️ طوفان اسیدی",
        "desc": "ابرهای سبز روی شهر خوابیده‌اند.",
        "effect_text": "دیوارهای ضعیف آسیب می‌بینند؛ گشت خطرناک‌تر می‌شود.",
        "mods": {"risk": 1},
        "one_time": "acid",
    },
    {
        "id": "merchant_caravan",
        "title": "🐪 کاروان تاجران",
        "desc": "کاروانی از غرب وارد شده و دنبال اوراق است.",
        "effect_text": "قیمت اوراق ۲ برابر می‌شود.",
        "mods": {"price_scrap": 2.0},
    },
    {
        "id": "black_battery",
        "title": "🕶️ بازار سیاه باتری",
        "desc": "باتری کمیاب شده و همه دنبال برق اضطراری‌اند.",
        "effect_text": "قیمت باتری ۲ برابر می‌شود.",
        "mods": {"price_battery": 2.0},
    },
    {
        "id": "clean_rain",
        "title": "🌧️ باران تمیز",
        "desc": "برای چند ساعت، باران قابل تصفیه از آسمان می‌بارد.",
        "effect_text": "تولید آب دستگاه تصفیه ۲ برابر می‌شود.",
        "mods": {"passive_water": 2.0},
    },
    {
        "id": "drought",
        "title": "🔥 خشکسالی قرمز",
        "desc": "چاه‌ها خشک شده‌اند و قیمت‌ها عصبی‌اند.",
        "effect_text": "تولید آب نصف می‌شود ولی قیمت بازار بالا می‌رود.",
        "mods": {"passive_water": 0.5, "all_prices": 1.25},
    },
    {
        "id": "junk_bloom",
        "title": "♻️ شکوفایی زباله",
        "desc": "باد، زباله‌های دفن‌شده را از زیر خاک بیرون آورده.",
        "effect_text": "لوت گشت‌زنی بیشتر می‌شود.",
        "mods": {"loot": 1.5},
    },
    {
        "id": "safe_routes",
        "title": "🛣️ مسیرهای امن",
        "desc": "نقشه قاچاقچی‌ها لو رفته.",
        "effect_text": "ریسک گشت‌زنی کمتر می‌شود.",
        "mods": {"risk": -2},
    },
    {
        "id": "war_drum",
        "title": "🥁 طبل جنگ",
        "desc": "همه کارتل‌ها آماده درگیری‌اند.",
        "effect_text": "کولداون غارت ۴۰٪ کمتر می‌شود.",
        "mods": {"raid_cd": 0.6},
    },
    {
        "id": "fog_of_war",
        "title": "🌫️ مه جنگ",
        "desc": "هیچ‌کس درست نمی‌بیند از کجا حمله می‌شود.",
        "effect_text": "دفاع هدف‌ها ۱۵٪ بیشتر حساب می‌شود.",
        "mods": {"defense": 1.15},
    },
    {
        "id": "forge_fever",
        "title": "🔥 تب آهنگری",
        "desc": "کارگاه‌ها شبانه‌روزی کار می‌کنند.",
        "effect_text": "هزینه ساخت آیتم‌ها ۱۵٪ کمتر می‌شود.",
        "mods": {"craft_discount": 0.15},
    },
    {
        "id": "radioactive_gold",
        "title": "☢️ فلزات پرتوزا",
        "desc": "مس و باتری در خرابه‌های آلوده زیاد شده.",
        "effect_text": "شانس پیدا شدن مس و باتری در گشت بیشتر می‌شود.",
        "mods": {"rare_loot": 1.8, "risk": 1},
    },
    {
        "id": "syndicate_tax_day",
        "title": "🏦 روز مالیات سندیکا",
        "desc": "اتحادها سازمان‌یافته‌تر شده‌اند.",
        "effect_text": "سهم پخش‌شده اتحاد ۳۰٪ بیشتر می‌شود.",
        "mods": {"alliance_pool": 1.3},
    },
    {
        "id": "medic_day",
        "title": "🏥 روز درمانگرها",
        "desc": "درمانگرهای دوره‌گرد به شهر رسیده‌اند.",
        "effect_text": "همه کمی HP بازیابی می‌کنند.",
        "mods": {},
        "one_time": "heal",
    },
    {
        "id": "government_airdrop",
        "title": "✈️ ایردراپ دولتی",
        "desc": "یه هواپیمای ناشناس بسته‌هایی رها کرد.",
        "effect_text": "به همه منابع تصادفی می‌رسد.",
        "mods": {},
        "one_time": "airdrop",
    },
    {
        "id": "market_crash",
        "title": "📉 سقوط بازار",
        "desc": "همه می‌فروشند، کمتر کسی می‌خرد.",
        "effect_text": "قیمت مرجع همه منابع ۳۰٪ کمتر می‌شود.",
        "mods": {"all_prices": 0.7},
    },
    {
        "id": "market_boom",
        "title": "📈 تب معامله",
        "desc": "بازار مردم شلوغ شده.",
        "effect_text": "قیمت مرجع همه منابع ۲۰٪ بیشتر می‌شود.",
        "mods": {"all_prices": 1.2},
    },
    {
        "id": "xp_festival",
        "title": "🎉 جشن بازماندگان",
        "desc": "امید کمی برگشته.",
        "effect_text": "XP دریافتی ۲ برابر می‌شود.",
        "mods": {"xp": 2.0},
    },
    {
        "id": "raider_plague",
        "title": "🦠 طاعون غارتگرها",
        "desc": "اردوگاه دزدها مریض شده.",
        "effect_text": "غارت سخت‌تر اما پاداشش بیشتر می‌شود.",
        "mods": {"raid_loot": 1.25, "risk": 1},
    },
    {
        "id": "quiet_day",
        "title": "🕊️ روز سکوت",
        "desc": "شهر برای یک روز عجیب آرام است.",
        "effect_text": "ریسک گشت کم می‌شود و دفاع کمی بیشتر است.",
        "mods": {"risk": -1, "defense": 1.05},
    },
    {
        "id": "copper_rush",
        "title": "🔶 هجوم مس",
        "desc": "کارخانه قدیمی کابل‌کشی پیدا شده.",
        "effect_text": "قیمت مس ۲ برابر و شانس پیدا کردن مس بیشتر می‌شود.",
        "mods": {"price_copper": 2.0, "rare_loot": 1.4},
    },
]

COOLDOWNS = {"scavenge": 15 * 60, "raid": 45 * 60}

RAID_BUCKETS = {
    "weak": {
        "button_key": "raid_weak",
        "title": "ضعیف",
        "loot_mod": 0.65,
        "atk_mod": 1.10,
        "xp": 3,
        "honor_win": 1,
        "honor_lose": -1,
    },
    "medium": {
        "button_key": "raid_medium",
        "title": "متوسط",
        "loot_mod": 1.00,
        "atk_mod": 1.00,
        "xp": 6,
        "honor_win": 6,
        "honor_lose": -4,
    },
    "strong": {
        "button_key": "raid_strong",
        "title": "قوی",
        "loot_mod": 1.35,
        "atk_mod": 0.90,
        "xp": 10,
        "honor_win": 12,
        "honor_lose": -7,
    },
}

# ══════════════════════════════════════════════════════
#  GLOBAL GAME STATE
# ══════════════════════════════════════════════════════
game: dict[str, Any] = {}

# آخرین sender_id دیده‌شده برای هر chat_id؛ برای ادمین‌چک در چت خصوصی لازم است.
LAST_SENDER_BY_CHAT: dict[str, str] = {}


# ══════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════
def build_meta_bold(text: str, phrases: list[tuple[str, int] | str]) -> list[dict]:
    """
    برای هر phrase، اگه توی text پیدا شد یک بولد اضافه می‌کند؛ اگه پیدا نشد، بی‌سروصدا رد می‌شود.
    phrases می‌تواند str (خودش بولد می‌شود) یا (search_str, length) باشد.
    """
    meta: list[dict] = []
    for item in phrases:
        if isinstance(item, tuple):
            search, length = item
        else:
            search, length = item, len(item)
        idx = text.find(search)
        if idx == -1:
            continue
        meta.append({"type": "Bold", "from_index": idx, "length": length})
    return meta or None


def now() -> datetime:
    return datetime.now()


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def fromiso(value: Optional[str], default: Optional[datetime] = None) -> datetime:
    if not value:
        return default or now()
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return default or now()


def today_key() -> str:
    return now().strftime("%Y-%m-%d")


def fmt_cd(seconds: float) -> str:
    seconds = max(0, int(seconds))
    if seconds <= 0:
        return "آماده! ✅"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d:
        return f"{d} روز و {h} ساعت"
    if h:
        return f"{h} ساعت" if m == 0 else f"{h} ساعت و {m} دقیقه"
    if m:
        return f"{m} دقیقه" if s == 0 else f"{m} دقیقه و {s} ثانیه"
    return f"{s} ثانیه"


def fmt_dt(value: Optional[str]) -> str:
    dt = fromiso(value, now())
    return dt.strftime("%Y/%m/%d ساعت %H:%M")


def bidi(value: Any) -> str:
    # Unicode isolate keeps English names/numbers from breaking Persian RTL order.
    return f"\u2068{value}\u2069"


def fmt_num(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def display_name(value: Any) -> str:
    return bidi(str(value or "بی‌نام"))


def effective_sender_id(chat_id: str, sender_id: str = "") -> str:
    """
    در چت خصوصی روبیکا ممکن است chat_id با sender_id یکی نباشد.
    برای پنل ادمین باید sender_id واقعی کاربر را ملاک بگیریم.
    اگر sender_id مستقیم پاس داده نشده باشد، از آخرین sender_id همان chat استفاده می‌کنیم.
    """
    return str(sender_id or LAST_SENDER_BY_CHAT.get(str(chat_id), "") or chat_id)


def is_admin(chat_id: str, sender_id: str = "") -> bool:
    uid = effective_sender_id(chat_id, sender_id)
    return uid in ADMIN_IDS or str(chat_id) in ADMIN_IDS


def is_group_admin(sender_id: str) -> bool:
    return str(sender_id) in ADMIN_IDS


def xp_bar(xp: int, max_xp: int, width: int = 10) -> str:
    filled = min(width, int((xp / max(1, max_xp)) * width))
    pct = int((xp / max(1, max_xp)) * 100)
    return "⬛" * filled + "⬜" * (width - filled) + f" {pct}%"


def safe_int(s: Any, default: int = 0) -> int:
    try:
        return int(str(s).strip())
    except Exception:
        return default


def clean_name(value: str, max_len: int = 24) -> Optional[str]:
    value = re.sub(r"\s+", " ", (value or "").strip())
    value = value.replace("\n", " ")
    if len(value) < 2 or len(value) > max_len:
        return None
    if any(x in value.lower() for x in ["http", "@", "/", "\\", "<", ">", "{"]):
        return None
    return value


def res_key(value: str) -> Optional[str]:
    return RES_ALIASES.get((value or "").strip().lower()) or RES_ALIASES.get(
        (value or "").strip()
    )


def amount_of(p: dict[str, Any], key: str) -> int:
    if key == "water":
        return int(p.get("water", 0))
    return int(p.get("resources", {}).get(key, 0))


def add_amount(p: dict[str, Any], key: str, amount: int) -> None:
    if key == "water":
        p["water"] = int(p.get("water", 0)) + int(amount)
    else:
        p.setdefault("resources", {})[key] = int(
            p.get("resources", {}).get(key, 0)
        ) + int(amount)


def pay_cost(p: dict[str, Any], cost: dict[str, int]) -> None:
    for key, amount in cost.items():
        add_amount(p, key, -int(amount))


def fmt_res_amount(key: str, amount: int, sign: str = "×") -> str:
    icon = RES_ICON.get(key, "")
    name = RES_NAME.get(key, key)
    return f"{icon} {name} {sign} {amount}"


def fmt_res_dict(cost: dict[str, int]) -> str:
    if not cost:
        return "—"
    return " + ".join(fmt_res_amount(k, v) for k, v in cost.items())


def fmt_res_lines(cost: dict[str, int]) -> str:
    if not cost:
        return "—"
    return "\n".join(f"• {fmt_res_amount(k, v)}" for k, v in cost.items())


def fmt_res_loss(cost: dict[str, int]) -> str:
    if not cost:
        return "• بدون ضرر منابع"
    return "\n".join(
        f"• {RES_ICON.get(k, '')} {RES_NAME.get(k, k)}: -{v}" for k, v in cost.items()
    )


def fmt_res_shortage(cost: dict[str, int], p: dict[str, Any]) -> str:
    lines = ["📦 نیاز / موجودی / کمبود"]
    for r, need in cost.items():
        have = amount_of(p, r)
        miss = max(0, int(need) - have)
        status = "✅ کافی" if miss == 0 else f"❌ کمبود: {miss}"
        lines.append(
            f"• {RES_ICON.get(r, '')} {RES_NAME.get(r, r)}: نیاز {need} | داری {have} | {status}"
        )
    return "\n".join(lines)


def has_resources(p: dict[str, Any], cost: dict[str, int]) -> bool:
    return all(amount_of(p, r) >= int(q) for r, q in cost.items())


def log_action(
    chat_id: str, action: str, data: Optional[dict[str, Any]] = None
) -> None:
    p = game["players"].get(chat_id)
    if not p:
        return
    p.setdefault("action_log", []).append(
        {"at": iso(now()), "action": action, "data": data or {}}
    )
    p["action_log"] = p["action_log"][-MAX_ACTION_LOG:]


def admin_audit(
    admin_id: str, action: str, data: Optional[dict[str, Any]] = None
) -> None:
    aid = int(game.get("next_admin_log_id", 1))
    game["next_admin_log_id"] = aid + 1
    game.setdefault("admin_logs", []).append(
        {
            "id": aid,
            "at": iso(now()),
            "admin": admin_id,
            "action": action,
            "data": data or {},
        }
    )
    game["admin_logs"] = game["admin_logs"][-MAX_ADMIN_LOG:]


def is_banned(chat_id: str) -> bool:
    return bool(game.get("players", {}).get(chat_id, {}).get("banned"))


def ban_reason(chat_id: str) -> str:
    return str(
        game.get("players", {}).get(chat_id, {}).get("ban_reason") or "بدون دلیل ثبت‌شده"
    )


# ══════════════════════════════════════════════════════
#  SAVE / LOAD / MIGRATION
# ══════════════════════════════════════════════════════
def default_season(season_id: int = 1) -> dict[str, Any]:
    start = now()
    end = start + timedelta(days=SEASON_LENGTH_DAYS)
    return {"id": season_id, "start": iso(start), "end": iso(end), "archives": []}


def generate_ref_code(chat_id: str) -> str:
    base = abs(hash(str(chat_id))) % 900000 + 100000
    return f"REF{base}"


def new_player(name: Optional[str] = None, chat_id: str = "") -> dict[str, Any]:
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
        "last_passive": iso(now()),
        "registered_at": iso(now()),
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
        "career": {"seasons_played": 0, "best_rank": None, "best_score": 0},
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
        "market_supply": {r: 0 for r in RESOURCES},
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


def migrate_game(g: dict[str, Any]) -> dict[str, Any]:
    base = default_game()
    base.update(g or {})
    base["version"] = 4
    base.setdefault("players", {})
    base.setdefault("alliances", {})
    base.setdefault("market_orders", [])
    base.setdefault("next_order_id", 1)
    base.setdefault("barter_orders", [])
    base.setdefault("next_barter_id", 1)
    base.setdefault("resource_rentals", [])
    base.setdefault("next_rental_id", 1)
    base.setdefault("chat_states", {})
    base.setdefault("season", default_season(1))
    base.setdefault("world_event_active", None)
    base.setdefault("last_daily_event", None)
    base.setdefault("world_boss", None)
    base.setdefault("last_boss_spawn", None)
    base.setdefault("news_feed", [])
    base.setdefault("last_group_radio_at", None)
    base.setdefault("last_group_boss_report_at", None)
    base.setdefault("last_group_rank1", None)
    base.setdefault("group_radio_log", [])
    base.setdefault("last_system_restock", None)
    base.setdefault("system_stock_log", [])
    base.setdefault("market_supply", {r: 0 for r in RESOURCES})
    base.setdefault("private_messages", [])
    base.setdefault("next_private_message_id", 1)
    base.setdefault("admin_logs", [])
    base.setdefault("next_admin_log_id", 1)
    for r in RESOURCES:
        base["market_supply"].setdefault(r, 0)

    for cid, p in list(base["players"].items()):
        fresh = new_player(p.get("name") or "", cid)
        fresh.update(p)
        fresh.setdefault("registered", bool(fresh.get("name")))
        fresh.setdefault("resources", {})
        for r, v in new_player("", cid)["resources"].items():
            fresh["resources"].setdefault(r, v)
        fresh.setdefault("inventory", {})
        fresh.setdefault("buildings", {})
        fresh.setdefault("upgrades_in_progress", [])
        fresh.setdefault("stats", {})
        for k, v in new_player("", cid)["stats"].items():
            fresh["stats"].setdefault(k, v)
        fresh.setdefault("ref_code", generate_ref_code(cid))
        fresh.setdefault("referral_used", False)
        fresh.setdefault("referrals_count", 0)
        fresh.setdefault("loot_caches", 0)
        fresh.setdefault("mission_day", None)
        fresh.setdefault("daily_missions", [])
        fresh.setdefault("boss_cd", None)
        fresh.setdefault("season_points_bonus", 0)
        fresh.setdefault(
            "career", {"seasons_played": 0, "best_rank": None, "best_score": 0}
        )
        fresh.setdefault("action_log", [])
        fresh.setdefault("banned", False)
        fresh.setdefault("ban_reason", "")
        fresh.setdefault("banned_at", None)
        fresh.setdefault("banned_by", None)
        fresh.setdefault("admin_notes", [])
        base["players"][cid] = fresh

    # v3 alliances were: name -> [chat_ids]. Convert to managed alliance object.
    for name, al in list(base["alliances"].items()):
        if isinstance(al, list):
            members = [x for x in al if isinstance(x, str)]
            base["alliances"][name] = {
                "name": name,
                "owner": members[0] if members else "",
                "members": members,
                "open": True,
                "applicants": [],
                "vault": 0,
                "total_shared": 0,
                "level": 1,
                "group_raid_session": None,
                "group_raid_cd": None,
                "created_at": iso(now()),
                "log": [],
            }
        else:
            al.setdefault("name", name)
            al.setdefault("owner", (al.get("members") or [""])[0])
            al.setdefault("members", [])
            al.setdefault("open", True)
            al.setdefault("applicants", [])
            al.setdefault("vault", 0)
            al.setdefault("total_shared", 0)
            al.setdefault("level", 1)
            al.setdefault("group_raid_session", None)
            al.setdefault("group_raid_cd", None)
            al.setdefault("log", [])
    return base


def load_game() -> None:
    global game
    if SAVE_FILE.exists():
        with SAVE_FILE.open("r", encoding="utf-8") as f:
            game = migrate_game(json.load(f))
    else:
        game = default_game()

    # === مهاجرت بونوس ساختمان‌ها برای همه بازیکن‌ها ===
    print("🔧 Migrating building bonuses for existing players...")
    for cid in list(game["players"].keys()):
        if game["players"][cid].get("registered"):
            migrate_player_building_bonuses(cid)
    print("✅ Building bonuses migrated.")

    save_game()


def save_game() -> None:
    tmp = SAVE_FILE.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(game, f, ensure_ascii=False, indent=2)
        tmp.replace(SAVE_FILE)
    except Exception as e:
        print(T("errors.save_failed", error=e))


# ══════════════════════════════════════════════════════
#  RUBIKA API
# ══════════════════════════════════════════════════════
def api(
    method: str, payload: Optional[dict[str, Any]] = None, retries: int = 3
) -> dict[str, Any]:
    payload = payload or {}
    for attempt in range(retries):
        try:
            r = requests.post(f"{API_BASE}/{method}", json=payload, timeout=12)
            # اگر پاسخ HTML یا خالی بود، خطا بده
            if not r.text.strip() or r.text.strip().startswith("<!DOCTYPE"):
                raise ValueError("Invalid response (HTML or empty)")
            data = r.json()
            if DEBUG or r.status_code != 200:
                print(f"[API {method}] HTTP={r.status_code} {data}")
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                return data["data"]
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, ValueError, requests.RequestException) as e:
            print(f"[API] {method} attempt {attempt + 1}/{retries}: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def make_keypad(rows: list[list[str]]) -> dict[str, Any]:
    return {
        "rows": [
            {
                "buttons": [
                    {"id": txt, "type": "Simple", "button_text": txt} for txt in row
                ]
            }
            for row in rows
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def main_keypad(chat_id: Optional[str] = None, sender_id: str = "") -> dict[str, Any]:
    # نظم منوی اصلی:
    # نقشه شهر = همه فعالیت‌های PvE مثل گشت، باس، صندوق و اخبار
    # غارت = PvP جداگانه
    # اتحاد = مدیریت اتحاد و حمله گروهی
    rows = [
        [B("profile"), B("city_map")],
        [B("market"), B("buildings")],
        [B("craft"), B("attack")],
        [B("alliance"), B("inventory")],
        [B("daily_missions"), B("daily")],
        [B("season"), B("leaderboard")],
        [B("messages"), B("event")],
        [B("help")],
    ]
    if chat_id and is_admin(chat_id, sender_id):
        rows.append([B("admin_panel")])
    return make_keypad(rows)


def send(
    chat_id: str,
    text: str,
    keypad: Optional[dict[str, Any]] = None,
    remove_keypad: bool = False,
    meta_data: Optional[list[dict]] = None,  # ← جدید
) -> dict[str, Any]:
    payload = {"chat_id": chat_id, "text": text or " "}

    if meta_data:
        payload["meta_data"] = meta_data

    if not str(chat_id).startswith(("g", "c")):
        if keypad:
            payload["chat_keypad"] = keypad
            payload["chat_keypad_type"] = "New"
        elif remove_keypad:
            payload["chat_keypad_type"] = "Remove"

    return api("sendMessage", payload)


# ══════════════════════════════════════════════════════
#  PLAYER HELPERS
# ══════════════════════════════════════════════════════
def get_player(chat_id: str, name: str = "") -> dict[str, Any]:
    if chat_id not in game["players"]:
        game["players"][chat_id] = new_player(None, chat_id)
    p = game["players"][chat_id]
    if name and not p.get("name"):
        p["name"] = name
    return p


def player_name(chat_id: str) -> str:
    p = game["players"].get(chat_id)
    return p.get("name") if p and p.get("name") else str(chat_id)[-6:]


def find_player_by_name(
    name: str, candidates: Optional[list[str]] = None
) -> Optional[str]:
    name_norm = (name or "").strip().lower()
    pool = candidates or list(game["players"].keys())
    for cid in pool:
        if game["players"].get(cid, {}).get("name", "").strip().lower() == name_norm:
            return cid
    for cid in pool:
        if (
            name_norm
            and name_norm
            in game["players"].get(cid, {}).get("name", "").strip().lower()
        ):
            return cid
    return None


def recalc_power(p: dict[str, Any]) -> None:
    atk = 0
    dfc = 0

    # ساختمان‌ها (دفاع کمی nerf شد)
    for bk, lv in p.get("buildings", {}).items():
        if lv > 0 and bk in BUILDINGS:
            data = BUILDINGS[bk]["levels"].get(int(lv), {})
            atk += data.get("atk", 0)
            dfc += data.get("def", 0)

    # آیتم‌ها (حمله کمی قوی‌تر از دفاع)
    for ik, qty in p.get("inventory", {}).items():
        item = CRAFT_ITEMS.get(ik) or LEGENDARY_ITEMS.get(ik)
        if item and qty > 0:
            atk += item.get("atk", 0) * qty * 1.12
            dfc += item.get("def", 0) * qty * 1.05  # Legendary defense کمی nerf

    p["total_attack"] = int(atk)
    p["total_defense"] = int(dfc)


def apply_building_bonuses(p: dict[str, Any]) -> None:
    """اعمال تمام اثرات ساختمان‌ها"""
    buildings = p.get("buildings", {})

    # Purifier → passive water (در passive_income هم استفاده می‌شه)
    purifier_lv = int(buildings.get("purifier", 0))
    if purifier_lv > 0:
        p.setdefault(
            "_purifier_bonus",
            BUILDINGS["purifier"]["levels"].get(purifier_lv, {}).get("prod", 0),
        )

    # Lab → craft discount
    lab_lv = int(buildings.get("lab", 0))
    p["_craft_discount"] = (
        BUILDINGS["lab"]["levels"].get(lab_lv, {}).get("discount", 0)
        if lab_lv > 0
        else 0
    )

    # Market Stall → fee cut
    stall_lv = int(buildings.get("market_stall", 0))
    p["_market_fee_cut"] = (
        BUILDINGS["market_stall"]["levels"].get(stall_lv, {}).get("fee_cut", 0)
        if stall_lv > 0
        else 0
    )


def honor_title(honor: int) -> str:
    for lo, hi, title in HONOR_TITLES:
        if lo <= honor <= hi:
            return title
    return "ناشناخته"


def level_info(p: dict[str, Any]) -> tuple[int, int, int, str]:
    lv = int(p.get("level", 1))
    xp = int(p.get("xp", 0))
    max_xp = LEVELS.get(lv, {}).get("xp", 9999)
    label = LEVELS.get(lv, {}).get("label", "؟")
    return lv, xp, max_xp, label


def add_xp(p: dict[str, Any], amount: int) -> bool:
    amount = int(amount * event_mod("xp", 1.0))
    p["xp"] = int(p.get("xp", 0)) + amount
    leveled = False
    while p["level"] < 10:
        max_xp = LEVELS.get(p["level"], {}).get("xp", 9999)
        if p["xp"] < max_xp:
            break
        p["xp"] -= max_xp
        p["level"] += 1
        leveled = True
    return leveled


def cd_remaining(p: dict[str, Any], key: str) -> float:
    return (
        max(0, (fromiso(p.get(f"{key}_cd"), now()) - now()).total_seconds())
        if p.get(f"{key}_cd")
        else 0
    )


def set_cd(p: dict[str, Any], key: str, seconds: float) -> None:
    p[f"{key}_cd"] = iso(now() + timedelta(seconds=int(seconds)))


def shield_remaining(p: dict[str, Any]) -> float:
    return (
        max(0, (fromiso(p.get("shield_until"), now()) - now()).total_seconds())
        if p.get("shield_until")
        else 0
    )


def handle_event(chat_id: str) -> None:
    ev = current_event()
    if not ev:
        send(
            chat_id,
            "🌪️ رویداد روز\n\nفعلاً هیچ رویدادی فعال نیست.",
            keypad=main_keypad(chat_id),
        )
        return

    left = fmt_cd((fromiso(ev.get("expires_at"), now()) - now()).total_seconds())

    send(
        chat_id,
        f"🌪️ رویداد روز\n\n"
        f"{ev['title']}\n"
        f"{ev['desc']}\n\n"
        f"📌 اثر:\n{ev['effect_text']}\n\n"
        f"⏳ زمان باقی‌مانده: {left}",
        keypad=main_keypad(chat_id),
    )


def is_shielded(p: dict[str, Any]) -> bool:
    return shield_remaining(p) > 0


def base_status_label(p: dict[str, Any]) -> str:
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


def finish_upgrades(p: dict[str, Any]) -> list[dict[str, Any]]:
    finished, remaining = [], []
    for u in p.get("upgrades_in_progress", []):
        if fromiso(u.get("finish"), now()) <= now():
            bk = u.get("bldg")
            lvl = int(u.get("to_level", 1))
            if bk in BUILDINGS:
                p.setdefault("buildings", {})[bk] = lvl
                finished.append(u)
        else:
            remaining.append(u)
    p["upgrades_in_progress"] = remaining
    recalc_power(p)
    apply_building_bonuses(p)
    recalc_power(p)
    return finished


def upgrade_in_progress(p: dict[str, Any], bk: str) -> Optional[float]:
    for u in p.get("upgrades_in_progress", []):
        if u.get("bldg") == bk:
            return max(0, (fromiso(u.get("finish"), now()) - now()).total_seconds())
    return None


def passive_income(chat_id: str) -> int:
    p = game["players"][chat_id]
    current = now()
    last = fromiso(p.get("last_passive"), current)
    elapsed = max(0, (current - last).total_seconds())
    p["last_passive"] = iso(current)
    purifier_lv = int(p.get("buildings", {}).get("purifier", 0))
    if purifier_lv <= 0:
        return 0
    rate = BUILDINGS["purifier"]["levels"].get(purifier_lv, {}).get("prod", 0)
    rate *= event_mod("passive_water", 1.0)
    rate *= 1.0 + cartel_water_bonus(chat_id)
    earned = int(elapsed * rate / 3600)
    if earned > 0:
        award_water(chat_id, earned, "passive_income", alliance_share=True)
    return earned


# ══════════════════════════════════════════════════════
#  ALLIANCE ECONOMY
# ══════════════════════════════════════════════════════
def get_alliance(name: Optional[str]) -> Optional[dict[str, Any]]:
    if not name:
        return None
    return game.get("alliances", {}).get(name)


def player_alliance(chat_id: str) -> Optional[dict[str, Any]]:
    p = game["players"].get(chat_id)
    return get_alliance(p.get("alliance")) if p else None


def alliance_mode_text(al: dict[str, Any]) -> str:
    return T("alliance.open") if al.get("open") else T("alliance.closed")


def cartel_level(al: Optional[dict[str, Any]]) -> int:
    if not al:
        return 1
    return max(1, min(MAX_CARTEL_LEVEL, int(al.get("level", 1))))


def cartel_level_data(al: Optional[dict[str, Any]]) -> dict[str, Any]:
    return CARTEL_LEVELS.get(cartel_level(al), CARTEL_LEVELS[1])


def cartel_next_upgrade_cost(al: dict[str, Any]) -> int:
    lv = cartel_level(al)
    if lv >= MAX_CARTEL_LEVEL:
        return 0
    return int(CARTEL_LEVELS[lv + 1]["upgrade_cost"])


def cartel_water_bonus(chat_id: str) -> float:
    al = player_alliance(chat_id)
    return float(cartel_level_data(al).get("water_bonus", 0.0)) if al else 0.0


def cartel_score_bonus(chat_id: str) -> int:
    al = player_alliance(chat_id)
    return int(cartel_level_data(al).get("score_bonus", 0)) if al else 0


def cartel_perks_text(al: Optional[dict[str, Any]]) -> str:
    data = cartel_level_data(al)
    lines = [
        f"• 💧 پاداش تولید آب اعضا: +{int(float(data.get('water_bonus', 0)) * 100)}٪",
        f"• 🏆 پاداش امتیاز سیزن برای هر عضو: +{int(data.get('score_bonus', 0))}",
    ]
    return "\n".join(lines)


def alliance_log(
    al: dict[str, Any], action: str, data: Optional[dict[str, Any]] = None
) -> None:
    al.setdefault("log", []).append(
        {"at": iso(now()), "action": action, "data": data or {}}
    )
    al["log"] = al["log"][-80:]


def distribute_alliance_income(
    source_id: str, pool: int, reason: str
) -> tuple[int, int, str]:
    if pool <= 0:
        return 0, 0, ""
    al = player_alliance(source_id)
    if not al:
        return 0, 0, ""
    pool = int(pool * event_mod("alliance_pool", 1.0))
    members = [
        cid
        for cid in al.get("members", [])
        if cid in game["players"] and cid != source_id
    ]
    if not members:
        al["vault"] = int(al.get("vault", 0)) + pool
        al["total_shared"] = int(al.get("total_shared", 0)) + pool
        return 0, pool, T("alliance.no_share")
    distributed = int(pool * ALLIANCE_DISTRIBUTE_RATE)
    vault_add = max(0, pool - distributed)
    each = max(1, distributed // len(members)) if distributed > 0 else 0
    actual_dist = each * len(members)
    for cid in members:
        mp = game["players"][cid]
        mp["water"] = int(mp.get("water", 0)) + each
        mp.setdefault("stats", {})["alliance_received"] = (
            mp.get("stats", {}).get("alliance_received", 0) + each
        )
        log_action(
            cid,
            "alliance_dividend",
            {"from": source_id, "amount": each, "reason": reason},
        )
    al["vault"] = int(al.get("vault", 0)) + vault_add + (distributed - actual_dist)
    al["total_shared"] = int(al.get("total_shared", 0)) + pool
    source = game["players"][source_id]
    source.setdefault("stats", {})["alliance_shared"] = (
        source.get("stats", {}).get("alliance_shared", 0) + pool
    )
    return (
        actual_dist,
        vault_add + (distributed - actual_dist),
        T(
            "alliance.share_note",
            pool=pool,
            distributed=actual_dist,
            vault_add=vault_add,
        ),
    )


def award_water(
    chat_id: str, gross: int, reason: str, alliance_share: bool = True
) -> tuple[int, str]:
    p = game["players"][chat_id]
    gross = max(0, int(gross))
    if gross <= 0:
        return 0, ""
    net = gross
    note = ""
    if alliance_share and p.get("alliance"):
        tax = int(gross * ALLIANCE_TAX_RATE)
        bonus = int(gross * ALLIANCE_BONUS_RATE)
        net = max(0, gross - tax)
        pool = tax + bonus
        _, _, note = distribute_alliance_income(chat_id, pool, reason)
    p["water"] = int(p.get("water", 0)) + net
    p.setdefault("stats", {})["water_earned"] = (
        p.get("stats", {}).get("water_earned", 0) + net
    )
    log_action(chat_id, "water_income", {"gross": gross, "net": net, "reason": reason})
    return net, note


# ══════════════════════════════════════════════════════
#  WOW FEATURES: NEWS / MISSIONS / CACHES / BOSS / MAP / GROUP RAID
# ══════════════════════════════════════════════════════
def is_game_group_chat(chat_id: str) -> bool:
    return bool(GAME_GROUP_ID) and str(chat_id) == str(GAME_GROUP_ID)


def group_radio_is_enabled() -> bool:
    return bool(GROUP_RADIO_ENABLED and GAME_GROUP_ID)


def send_group_radio(text: str, force: bool = False, reason: str = "radio") -> bool:
    """Send a cinematic public message only to the configured game group."""
    if not group_radio_is_enabled():
        return False
    text = (text or "").strip()
    if not text:
        return False
    if not force:
        last = fromiso(
            game.get("last_group_radio_at"),
            now() - timedelta(seconds=GROUP_RADIO_MIN_INTERVAL + 1),
        )
        if (now() - last).total_seconds() < GROUP_RADIO_MIN_INTERVAL:
            return False
    send(GAME_GROUP_ID, text)
    game["last_group_radio_at"] = iso(now())
    log = game.setdefault("group_radio_log", [])
    log.insert(0, {"at": iso(now()), "reason": reason, "text": text[:220]})
    del log[80:]
    return True


def add_news(text: str, important: bool = False) -> None:
    item = {"at": iso(now()), "text": text}
    feed = game.setdefault("news_feed", [])
    feed.insert(0, item)
    del feed[60:]
    if important:
        send_group_radio(
            T("group_radio.important_news", text=text),
            force=True,
            reason="important_news",
        )
        for cid, p in list(game.get("players", {}).items()):
            if p.get("registered") and not p.get("banned"):
                send(cid, f"📰 خبر فوری آخرالزمان\n\n{text}", keypad=main_keypad(cid))


def group_radio_boss_status_text(boss: Optional[dict[str, Any]] = None) -> str:
    boss = boss or active_boss()
    if not boss:
        return T("group_radio.no_boss")
    hp = int(boss.get("hp", 0))
    max_hp = max(1, int(boss.get("max_hp", 1)))
    hp_pct = int(hp / max_hp * 100)
    parts = boss.get("participants", {})
    top = sorted(parts.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True)[
        :3
    ]
    top_lines = (
        "\n".join(
            f"{i}. {player_name(cid)} — {fmt_num(v.get('damage', 0))} آسیب"
            for i, (cid, v) in enumerate(top, 1)
        )
        or "هنوز کسی جرئت نکرده جلو بره."
    )
    left = fmt_cd((fromiso(boss.get("expires_at"), now()) - now()).total_seconds())
    return T(
        "group_radio.boss_status",
        name=boss.get("name", "باس جهانی"),
        hp=fmt_num(hp),
        max_hp=fmt_num(max_hp),
        pct=hp_pct,
        left=left,
        top=top_lines,
    )


def group_radio_leaderboard_text() -> str:
    rows = ranked_players()[:3]
    if not rows:
        return T("group_radio.no_players")
    top_lines = "\n".join(
        f"{i}. {player_name(cid)} — {fmt_num(score)} امتیاز"
        for i, (cid, score) in enumerate(rows, 1)
    )
    return T("group_radio.leaderboard", top=top_lines)


def group_radio_titles_text() -> str:
    today = today_key()
    active_rows = []
    completed = 0
    silent = []
    for cid, p in game.get("players", {}).items():
        if not p.get("registered") or p.get("banned"):
            continue
        missions = p.get("daily_missions") if p.get("mission_day") == today else []
        progress = sum(
            int(m.get("progress", 0)) for m in missions if isinstance(m, dict)
        )
        goals = sum(int(m.get("goal", 0)) for m in missions if isinstance(m, dict))
        if (
            missions
            and goals
            and all(
                int(m.get("progress", 0)) >= int(m.get("goal", 1)) for m in missions
            )
        ):
            completed += 1
        if progress > 0:
            active_rows.append((cid, progress))
        else:
            silent.append(cid)
    active_rows.sort(key=lambda x: x[1], reverse=True)
    active = (
        player_name(active_rows[0][0]) if active_rows else "هنوز کسی خودش رو ثابت نکرده"
    )
    sleepy = (
        player_name(random.choice(silent)) if silent else "امروز کسی کامل خواب نیست"
    )
    return T("group_radio.titles", active=active, sleepy=sleepy, completed=completed)


def group_radio_alliance_text() -> str:
    alliances = [
        al for al in game.get("alliances", {}).values() if isinstance(al, dict)
    ]
    if not alliances:
        return T("group_radio.no_alliance")
    alliances.sort(
        key=lambda al: (
            int(al.get("level", 1)),
            int(al.get("vault", 0)),
            len(al.get("members", [])),
        ),
        reverse=True,
    )
    al = alliances[0]
    return T(
        "group_radio.alliance",
        name=al.get("name", "بی‌نام"),
        level=cartel_level(al),
        members=len(al.get("members", [])),
        vault=fmt_num(al.get("vault", 0)),
    )


def group_radio_market_text() -> str:
    today = today_key()
    sold_today = 0
    open_orders = 0
    for o in game.get("market_orders", []):
        if o.get("status") == "open":
            open_orders += 1
        if o.get("status") == "sold" and str(o.get("sold_at", "")).startswith(today):
            sold_today += 1
    return T("group_radio.market", sold=sold_today, open=open_orders)


def group_radio_rumor_text() -> str:
    return T("group_radio.rumor")


def group_radio_periodic_text() -> str:
    boss = active_boss()
    if boss and random.random() < 0.55:
        return group_radio_boss_status_text(boss)
    choices = [
        group_radio_leaderboard_text,
        group_radio_titles_text,
        group_radio_alliance_text,
        group_radio_market_text,
        group_radio_rumor_text,
    ]
    return random.choice(choices)()


def maybe_group_rank_change() -> None:
    rows = ranked_players()[:2]
    if not rows:
        return
    top_id = rows[0][0]
    old_top = game.get("last_group_rank1")
    if old_top and old_top != top_id:
        challenger = player_name(top_id)
        fallen = (
            player_name(old_top) if old_top in game.get("players", {}) else "نفر قبلی"
        )
        send_group_radio(
            T("group_radio.rank_changed", challenger=challenger, fallen=fallen),
            force=True,
            reason="rank_changed",
        )
    game["last_group_rank1"] = top_id


def periodic_group_radio() -> None:
    if not group_radio_is_enabled():
        return
    maybe_group_rank_change()
    boss = active_boss()
    if boss:
        last_boss = fromiso(
            game.get("last_group_boss_report_at"),
            now() - timedelta(seconds=GROUP_BOSS_REPORT_INTERVAL + 1),
        )
        if (now() - last_boss).total_seconds() >= GROUP_BOSS_REPORT_INTERVAL:
            if send_group_radio(
                group_radio_boss_status_text(boss), force=True, reason="boss_status"
            ):
                game["last_group_boss_report_at"] = iso(now())
            return
    send_group_radio(group_radio_periodic_text(), force=False, reason="periodic")


def handle_group_message(chat_id: str, text: str, sender_id: str = "") -> None:
    """Keep the public group clean: ignore chatter, allow only admin radio commands."""
    text = (text or "").strip()
    if not text:
        return
    if not is_group_admin(sender_id):
        return
    if text in ["/radio_test", "تست رادیو", "📡 تست رادیو"]:
        send_group_radio(T("group_radio.admin_test"), force=True, reason="admin_test")
        return
    if text in ["/radio_status", "وضعیت رادیو", "📡 وضعیت رادیو"]:
        last = (
            fmt_dt(game.get("last_group_radio_at"))
            if game.get("last_group_radio_at")
            else "هنوز پیامی ثبت نشده"
        )
        log_count = len(game.get("group_radio_log", []))
        send_group_radio(
            T(
                "group_radio.admin_status",
                group=GAME_GROUP_ID,
                last=last,
                count=log_count,
            ),
            force=True,
            reason="admin_status",
        )
        return
    if text.startswith("/radio "):
        msg = text[len("/radio ") :].strip()
        if msg:
            send_group_radio(msg, force=True, reason="admin_manual")
        return


def registered_player_ids(include_banned: bool = False) -> list[str]:
    return [
        cid
        for cid, p in game.get("players", {}).items()
        if p.get("registered") and (include_banned or not p.get("banned"))
    ]


def boss_power_estimate(p: dict[str, Any]) -> int:
    recalc_power(p)
    return max(
        35,
        int(p.get("total_attack", 0))
        + int(int(p.get("total_defense", 0)) * 0.25)
        + int(p.get("level", 1)) * 35,
    )


def boss_scaled_stats(template: dict[str, Any]) -> dict[str, int]:
    """
    باس باید با تعداد بازیکن‌ها بزرگ شود، اما غیرممکن نشود.
    هدف این فرمول:
    - با تعداد بازیکن بیشتر، خون باس زیاد شود.
    - برای گروه کوچک هم باس قابل‌زدن ولی سخت بماند.
    - با ۲۷ بازیکن، باس نیاز به مشارکت جدی داشته باشد، نه چند ضربه ساده.
    """
    ids = registered_player_ids()
    player_count = max(1, len(ids))
    powers = [boss_power_estimate(game["players"][cid]) for cid in ids]
    avg_power = int(sum(powers) / max(1, len(powers))) if powers else 90

    # در ۴ ساعت و کولداون ۱۵ دقیقه، سقف نظری ۱۶ ضربه است؛
    # اما برای سختی، فرض می‌کنیم فقط بخشی از بازیکن‌ها چند ضربه واقعی می‌زنند.
    expected_hits_per_player = 3.8 + min(2.2, player_count / 18)
    difficulty = float(template.get("reward_mod", 1.0)) * random.uniform(1.12, 1.38)

    scaled_hp = int(avg_power * player_count * expected_hits_per_player * difficulty)
    floor_hp = int(16000 + player_count * 2600)
    ceiling_hp = int(max(floor_hp, avg_power * player_count * 8.5))

    hp = max(floor_hp, min(scaled_hp, ceiling_hp))
    atk = int(template.get("atk", 14) + min(28, player_count * 0.55) + avg_power / 180)
    return {
        "hp": hp,
        "atk": max(10, atk),
        "players": player_count,
        "avg_power": avg_power,
    }


def fmt_reward_dict(reward: dict[str, int]) -> str:
    parts = []
    for k, v in (reward or {}).items():
        if k == "xp":
            parts.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            parts.append(f"🎁 صندوق زنگ‌زده × {v}")
        else:
            parts.append(fmt_res_amount(k, int(v)))
    return " + ".join(parts) if parts else "—"


def award_mission_reward(p: dict[str, Any], reward: dict[str, int]) -> str:
    """Give a mission reward and return a clear receipt line for the player."""
    paid: list[str] = []
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            add_xp(p, v)
            paid.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            p["loot_caches"] = int(p.get("loot_caches", 0)) + v
            paid.append(f"🎁 صندوق زنگ‌زده × {v}")
        else:
            add_amount(p, k, v)
            paid.append(fmt_res_amount(k, v))
    return " + ".join(paid) if paid else "—"


def mission_line_text(m: dict[str, Any]) -> str:
    progress = int(m.get("progress", 0))
    goal = int(m.get("goal", 1))
    done = progress >= goal
    if m.get("claimed"):
        icon = "✅"
        status = "دریافت شده ✅"
        reward_label = "پاداش دریافتی"
    elif done:
        icon = "🎁"
        status = "آماده دریافت 🎁"
        reward_label = "پاداش آماده"
    else:
        icon = "⬜"
        status = "در حال انجام"
        reward_label = "پاداش"
    return T(
        "missions.line",
        ok=icon,
        title=m.get("title"),
        progress=progress,
        goal=goal,
        reward=fmt_reward_dict(m.get("reward", {})),
        status=status,
        reward_label=reward_label,
    )


def profile_daily_missions_text(chat_id: str) -> str:
    missions = ensure_daily_missions(chat_id)
    lines = []
    for m in missions:
        lines.append(mission_line_text(m))
    if daily_missions_claimed(chat_id):
        note = T("missions.claimed")
    elif daily_missions_done(chat_id):
        note = T("missions.ready_in_profile")
    else:
        note = T("missions.profile_hint")
    return T("missions.profile_block", lines="\n".join(lines), note=note)


def handle_news(chat_id: str) -> None:
    feed = game.get("news_feed", [])[:12]
    if not feed:
        send(chat_id, T("news.empty"), keypad=main_keypad(chat_id))
        return
    lines = []
    for item in feed:
        lines.append(
            T("news.line", time=fmt_dt(item.get("at")), text=item.get("text", ""))
        )
    send(chat_id, T("news.text", lines="\n".join(lines)), keypad=main_keypad(chat_id))


def ensure_daily_missions(chat_id: str) -> list[dict[str, Any]]:
    p = get_player(chat_id)
    if p.get("mission_day") != today_key() or not isinstance(
        p.get("daily_missions"), list
    ):
        chosen = random.sample(DAILY_MISSION_TEMPLATES, 3)
        p["mission_day"] = today_key()
        p["daily_final_claimed"] = False
        p["daily_missions"] = [
            {
                "key": m["key"],
                "title": m["title"],
                "goal": int(m["goal"]),
                "progress": 0,
                "reward": dict(m.get("reward", {})),
                "claimed": False,
            }
            for m in chosen
        ]
    # Backfill old mission records created before per-mission rewards existed.
    templates = {m.get("key"): m for m in DAILY_MISSION_TEMPLATES}
    for m in p.get("daily_missions", []):
        if not isinstance(m, dict):
            continue
        tpl = templates.get(m.get("key"), {})
        if not m.get("title") and tpl.get("title"):
            m["title"] = tpl["title"]
        if not m.get("reward") and tpl.get("reward"):
            m["reward"] = dict(tpl.get("reward", {}))
        m.setdefault("claimed", False)
        m["progress"] = min(
            int(m.get("progress", 0)), int(m.get("goal", tpl.get("goal", 1)))
        )
    return p["daily_missions"]


def inc_mission(chat_id: str, key: str, amount: int = 1) -> None:
    missions = ensure_daily_missions(chat_id)
    for m in missions:
        if m.get("key") == key and not m.get("claimed"):
            m["progress"] = min(
                int(m.get("goal", 1)), int(m.get("progress", 0)) + amount
            )


def daily_missions_done(chat_id: str) -> bool:
    missions = ensure_daily_missions(chat_id)
    return all(int(m.get("progress", 0)) >= int(m.get("goal", 1)) for m in missions)


def daily_missions_claimed(chat_id: str) -> bool:
    missions = ensure_daily_missions(chat_id)
    return bool(missions) and all(bool(m.get("claimed")) for m in missions)


def handle_daily_missions(chat_id: str) -> None:
    p = get_player(chat_id)
    missions = ensure_daily_missions(chat_id)
    receipts: list[str] = []
    for m in missions:
        ready = int(m.get("progress", 0)) >= int(m.get("goal", 1))
        if ready and not m.get("claimed"):
            paid = award_mission_reward(p, m.get("reward", {}))
            m["claimed"] = True
            m["claimed_at"] = iso(now())
            receipts.append(
                T("missions.receipt_line", title=m.get("title", "مأموریت"), reward=paid)
            )
    final_note = ""
    if all(bool(m.get("claimed")) for m in missions) and not p.get(
        "daily_final_claimed"
    ):
        p["water"] = int(p.get("water", 0)) + 150
        p["loot_caches"] = int(p.get("loot_caches", 0)) + 1
        p["daily_final_claimed"] = True
        p.setdefault("stats", {})["missions_completed"] = (
            int(p.get("stats", {}).get("missions_completed", 0)) + 1
        )
        add_news(
            f"📜 {player_name(chat_id)} مأموریت‌های روزانه را کامل کرد و پاداش نهایی گرفت."
        )
        final_note = T("missions.final_reward")
    lines = [mission_line_text(m) for m in missions]
    if receipts:
        note = T("missions.receipt", lines="\n".join(receipts))
    elif all(bool(m.get("claimed")) for m in missions):
        note = T("missions.claimed")
    else:
        ready_count = sum(
            1
            for m in missions
            if int(m.get("progress", 0)) >= int(m.get("goal", 1))
            and not m.get("claimed")
        )
        note = (
            T("missions.ready_hint", count=ready_count)
            if ready_count
            else T("missions.in_progress")
        )
    if final_note:
        note += "\n" + final_note
    save_game()
    send(
        chat_id,
        T("missions.text", lines="\n".join(lines), note=note),
        keypad=make_keypad(
            [[B("daily_missions")], [B("open_cache")], [B("main_menu")]]
        ),
    )


def maybe_award_legendary(chat_id: str, source: str, chance: float = 0.006) -> str:
    if random.random() > chance:
        return ""
    p = get_player(chat_id)
    key, item = random.choice(list(LEGENDARY_ITEMS.items()))
    p.setdefault("inventory", {})[key] = int(p.get("inventory", {}).get(key, 0)) + 1
    p.setdefault("stats", {})["legendary_found"] = (
        p.get("stats", {}).get("legendary_found", 0) + 1
    )
    recalc_power(p)
    text = T("cache.legendary", label=item["label"], source=source)
    add_news(
        f"✨ {player_name(chat_id)} از {source} آیتم افسانه‌ای پیدا کرد: {item['label']}",
        important=True,
    )
    return text


def maybe_find_cache(chat_id: str, zone_key: str) -> str:
    # صندوق باید حس «اتفاق نادر» بدهد، نه پاداش روزمره.
    chances = {"alley": 0.010, "suburb": 0.015, "center": 0.025, "bunker": 0.040}
    if random.random() > chances.get(zone_key, 0.015):
        return ""
    p = get_player(chat_id)
    p["loot_caches"] = int(p.get("loot_caches", 0)) + 1
    add_news(f"🎁 {player_name(chat_id)} در گشت‌زنی یک صندوق شانسی پیدا کرد.")
    return T("cache.found", count=p["loot_caches"])


def handle_open_cache(chat_id: str) -> None:
    p = get_player(chat_id)
    if int(p.get("loot_caches", 0)) <= 0:
        send(chat_id, T("cache.no_cache"), keypad=main_keypad(chat_id))
        return
    p["loot_caches"] = int(p.get("loot_caches", 0)) - 1
    p.setdefault("stats", {})["caches_opened"] = (
        p.get("stats", {}).get("caches_opened", 0) + 1
    )
    inc_mission(chat_id, "open_cache", 1)

    # ۱ تا ۱۰۰۰۰ برای کنترل دقیق احتمال‌ها.
    # آیتم افسانه‌ای: حدود ۰.۲٪ از هر صندوق، کم اما غیرممکن نیست.
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
        lines.append(fmt_res_lines(loot))
    elif roll <= 9700:
        loot = {"battery": random.randint(1, 3), "copper": random.randint(2, 6)}
        for r, q in loot.items():
            p["resources"][r] = p["resources"].get(r, 0) + q
        lines.append(fmt_res_lines(loot))
    elif roll <= 9980:
        water = random.randint(260, 520)
        p["water"] = int(p.get("water", 0)) + water
        p["loot_caches"] = int(p.get("loot_caches", 0)) + (
            1 if random.random() < 0.20 else 0
        )
        lines.append(f"💎 صندوق پرارزش بود! 💧 آب × {water}")
    else:
        legendary = maybe_award_legendary(chat_id, "صندوق شانسی", chance=1.0)
        lines.append(legendary or "✨ رد یک آیتم افسانه‌ای دیدی، اما دستت بهش نرسید.")

    save_game()
    send(
        chat_id,
        T("cache.opened", result="\n".join(lines), left=p.get("loot_caches", 0)),
        keypad=make_keypad([[B("open_cache")], [B("main_menu")]]),
    )


def active_boss() -> Optional[dict[str, Any]]:
    boss = game.get("world_boss")
    if not boss:
        return None
    if fromiso(boss.get("expires_at"), now()) <= now() or int(boss.get("hp", 0)) <= 0:
        return None
    return boss


def maybe_spawn_boss(force: bool = False) -> Optional[dict[str, Any]]:
    boss = active_boss()
    if boss:
        return boss

    # شمارش باس‌های این هفته
    week_start = now() - timedelta(days=now().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    bosses_this_week = 0
    last_spawn = fromiso(game.get("last_boss_spawn"))

    if last_spawn and last_spawn >= week_start:
        # شمارش ساده (برای دقت بیشتر می‌تونی لاگ جدا نگه داری)
        bosses_this_week = 1  # تقریبی — بعداً می‌تونیم دقیق‌تر کنیم

    if not force:
        if bosses_this_week >= MAX_BOSSES_PER_WEEK:
            return None

        last = fromiso(game.get("last_boss_spawn"), now() - timedelta(days=10))
        elapsed = (now() - last).total_seconds()

        if elapsed < BOSS_MIN_INTERVAL:
            return None

        # شانس اسپاون — هر چی زمان بیشتر گذشته، شانس بالاتر
        time_factor = min(
            1.0, (elapsed - BOSS_MIN_INTERVAL) / (BOSS_MAX_INTERVAL - BOSS_MIN_INTERVAL)
        )
        spawn_chance = 0.45 + (time_factor * 0.48)  # بین ۴۵٪ تا ۹۳٪

        # آخر هفته کمی بیشتر
        if now().weekday() >= 5:  # جمعه و شنبه
            spawn_chance += 0.15

        if random.random() > spawn_chance:
            return None

    # ==================== اسپاون باس ====================
    tmpl = dict(random.choice(BOSS_TEMPLATES))
    scaled = boss_scaled_stats(tmpl)

    boss_id = f"boss-{int(time.time())}"
    boss = {
        "id": boss_id,
        "name": tmpl["name"],
        "hp": int(scaled["hp"]),
        "max_hp": int(scaled["hp"]),
        "atk": int(scaled["atk"]),
        "reward_mod": float(tmpl["reward_mod"]),
        "spawned_at": iso(now()),
        "expires_at": iso(now() + timedelta(seconds=BOSS_DURATION)),
        "participants": {},
        "scaled_for_players": int(scaled["players"]),
        "avg_player_power": int(scaled["avg_power"]),
    }

    game["world_boss"] = boss
    game["last_boss_spawn"] = iso(now())

    add_news(
        T(
            "boss.spawned",
            name=boss["name"],
            hp=fmt_num(boss["max_hp"]),
            players=fmt_num(boss["scaled_for_players"]),
        ),
        important=True,
    )

    send_group_radio(
        f"☣️ هشدار بزرگ!\n{boss['name']} بعد از مدت‌ها دوباره ظاهر شد!\n"
        f"❤️ جان: {fmt_num(boss['max_hp'])}\n"
        f"⏳ فرصت: {BOSS_DURATION // 3600} ساعت",
        force=True,
        reason="boss_spawn",
    )

    save_game()
    return boss


def boss_keypad() -> dict[str, Any]:
    return make_keypad([[B("boss_attack")], [B("city_map"), B("main_menu")]])


def handle_world_boss(chat_id: str) -> None:
    boss = active_boss() or maybe_spawn_boss(False)
    if not boss:
        last = fromiso(
            game.get("last_boss_spawn"), now() - timedelta(seconds=BOSS_SPAWN_EVERY)
        )
        wait = max(0, BOSS_SPAWN_EVERY - int((now() - last).total_seconds()))
        send(chat_id, T("boss.none", time=fmt_cd(wait)), keypad=main_keypad(chat_id))
        return

    parts = boss.get("participants", {})
    top = sorted(parts.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True)[
        :5
    ]
    top_lines = (
        "\n".join(
            f"{i}. {player_name(cid)} — {fmt_num(v.get('damage', 0))}"
            for i, (cid, v) in enumerate(top, 1)
        )
        or "هنوز کسی نزده."
    )
    hp_pct = int(int(boss.get("hp", 0)) / max(1, int(boss.get("max_hp", 1))) * 100)

    text = T(
        "boss.menu",
        name=boss["name"],
        hp=fmt_num(boss["hp"]),
        max_hp=fmt_num(boss["max_hp"]),
        pct=hp_pct,
        left=fmt_cd((fromiso(boss.get("expires_at"), now()) - now()).total_seconds()),
        top=top_lines,
        cd=fmt_cd(cd_remaining(get_player(chat_id), "boss")),
        players=fmt_num(boss.get("scaled_for_players", len(registered_player_ids()))),
        avg_power=fmt_num(boss.get("avg_player_power", 0)),
    )

    meta = build_meta_bold(
        text,
        [
            (text[:25], 25),
            "جان:",
            "زمان باقی‌مانده:",
        ],
    )

    send(chat_id, text, keypad=boss_keypad(), meta_data=meta)


def finish_boss_if_dead(killer_id: str) -> bool:
    boss = game.get("world_boss")
    if not boss or int(boss.get("hp", 0)) > 0:
        return False

    participants = boss.get("participants", {})
    if not participants:
        game["world_boss"] = None
        return True

    total_damage = sum(int(v.get("damage", 0)) for v in participants.values())
    if total_damage <= 0:
        game["world_boss"] = None
        return True

    sorted_parts = sorted(
        participants.items(), key=lambda x: int(x[1].get("damage", 0)), reverse=True
    )

    reward_lines = []
    big_hitters = 0

    for rank, (cid, info) in enumerate(sorted_parts, 1):
        if cid not in game["players"]:
            continue
        p = game["players"][cid]
        dmg = int(info.get("damage", 0))

        # پایه پاداش
        water = int((160 + dmg / 35) * float(boss.get("reward_mod", 1.0)))

        # پاداش ویژه ضربه سنگین
        if dmg >= 2000:
            water += 450
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 2
            big_hitters += 1
            send(cid, "🏆 ضربه سنگین! (+۴۵۰ آب + ۲ صندوق)", keypad=main_keypad(cid))

        # رتبه‌بندی
        if rank == 1:
            water += 320
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 3
        elif rank <= 3:
            water += 180
            p["loot_caches"] = int(p.get("loot_caches", 0)) + 2

        # تقسیم عادلانه‌تر بر اساس سهم دمیج
        damage_share = dmg / total_damage
        extra = int(800 * damage_share)
        water += extra

        p["water"] = int(p.get("water", 0)) + water
        # باتری و مس هم بده
        p["resources"]["battery"] = p["resources"].get("battery", 0) + (
            3 if rank <= 3 else 1
        )
        p["resources"]["copper"] = p["resources"].get("copper", 0) + (
            6 if rank <= 3 else 2
        )

        maybe_award_legendary(cid, "باس جهانی", chance=0.03 if rank <= 3 else 0.008)

        send(
            cid,
            T(
                "boss.reward",
                name=boss["name"],
                rank=rank,
                damage=fmt_num(dmg),
                water=fmt_num(water),
            ),
            keypad=main_keypad(cid),
        )
        reward_lines.append(f"{rank}. {player_name(cid)} — {fmt_num(dmg)} dmg")

    add_news(
        T(
            "boss.defeated",
            name=boss["name"],
            killer=player_name(killer_id),
            top="\n".join(reward_lines[:8]),
        ),
        important=True,
    )
    game["world_boss"] = None
    return True


def handle_boss_attack(chat_id: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    recalc_power(p)
    boss = active_boss() or maybe_spawn_boss(False)
    if not boss:
        send(chat_id, T("boss.none", time=fmt_cd(0)), keypad=main_keypad(chat_id))
        return
    if cd_remaining(p, "boss") > 0:
        send(
            chat_id,
            T("boss.cooldown", time=fmt_cd(cd_remaining(p, "boss"))),
            keypad=boss_keypad(),
        )
        return
    power = (
        int(p.get("total_attack", 0))
        + int(p.get("total_defense", 0)) * 0.25
        + int(p.get("level", 1)) * 35
    )
    damage = max(25, int(power * random.uniform(0.80, 1.25)))
    boss["hp"] = max(0, int(boss.get("hp", 0)) - damage)
    part = boss.setdefault("participants", {}).setdefault(
        chat_id, {"damage": 0, "hits": 0}
    )
    part["damage"] = int(part.get("damage", 0)) + damage
    part["hits"] = int(part.get("hits", 0)) + 1
    p.setdefault("stats", {})["boss_damage"] = (
        p.get("stats", {}).get("boss_damage", 0) + damage
    )
    p.setdefault("stats", {})["boss_hits"] = p.get("stats", {}).get("boss_hits", 0) + 1
    inc_mission(chat_id, "boss_attack", 1)
    boss_hit = random.randint(0, int(boss.get("atk", 10)))
    p["hp"] = max(1, int(p.get("hp", 100)) - boss_hit)
    set_cd(p, "boss", BOSS_ATTACK_CD)
    defeated = finish_boss_if_dead(chat_id)
    save_game()
    if defeated:
        send(
            chat_id,
            T("boss.killshot", damage=fmt_num(damage)),
            keypad=main_keypad(chat_id),
        )
    else:
        send(
            chat_id,
            T(
                "boss.attack_result",
                name=boss["name"],
                damage=fmt_num(damage),
                boss_hp=fmt_num(boss["hp"]),
                hp=p.get("hp", 100),
                hit=boss_hit,
                cd=fmt_cd(BOSS_ATTACK_CD),
            ),
            keypad=boss_keypad(),
        )


def handle_city_map(chat_id: str) -> None:
    boss = active_boss()
    boss_line = (
        T("map.boss_active", name=boss["name"], hp=fmt_num(boss["hp"]))
        if boss
        else T("map.boss_none")
    )
    p = get_player(chat_id)
    cache_line = T("map.cache_line", count=int(p.get("loot_caches", 0)))
    send(
        chat_id,
        T("map.text", boss=boss_line, cache=cache_line),
        keypad=make_keypad(
            [
                [B("scavenge_alley"), B("scavenge_suburb")],
                [B("scavenge_center"), B("scavenge_bunker")],
                [B("world_boss"), B("open_cache")],
                [B("daily_missions"), B("news")],
                [B("main_menu")],
            ]
        ),
    )


def alliance_group_raid_target(al: dict[str, Any]) -> dict[str, Any]:
    member_set = set(al.get("members", []))
    candidates = []
    for cid, p in game.get("players", {}).items():
        if cid in member_set or not p.get("registered") or p.get("banned"):
            continue
        if is_shielded(p):
            continue
        recalc_power(p)
        power = (
            int(p.get("total_defense", 0))
            + int(p.get("total_attack", 0) * 0.45)
            + int(p.get("level", 1)) * 90
        )
        candidates.append((cid, p, power))

    if candidates:
        # فقط قوی‌ترین‌ها: از بین ۵ هدف برتر یکی انتخاب می‌شود.
        candidates.sort(key=lambda x: x[2], reverse=True)
        top = candidates[: min(5, len(candidates))]
        cid, p, power = random.choice(top)
        return {
            "type": "player",
            "chat_id": cid,
            "name": p.get("name"),
            "defense": max(900, int(power * random.uniform(1.05, 1.35))),
            "water": int(p.get("water", 0)),
        }

    # اگر هدف بازیکنی نبود، یک پایگاه NPC سخت می‌سازیم تا دکمه بی‌اثر نماند.
    level = cartel_level(al)
    return {
        "type": "npc",
        "chat_id": "",
        "name": random.choice(
            ["🏰 قلعه آهن‌خوارها", "☢️ برج نگهبانان بنکر", "🦂 لانه فرماندهان اسیدی"]
        ),
        "defense": random.randint(2800, 4600) * max(1, level),
        "water": random.randint(1200, 2600),
    }


def alliance_group_session(al: dict[str, Any]) -> Optional[dict[str, Any]]:
    session = al.get("group_raid_session")
    if not isinstance(session, dict):
        return None
    if fromiso(session.get("expires_at"), now()) <= now():
        al.pop("group_raid_session", None)
        return None
    return session


def alliance_group_ready_lines(
    al: dict[str, Any], session: dict[str, Any]
) -> tuple[str, int, int]:
    ready = set(session.get("ready", []))
    member_ids = [cid for cid in al.get("members", []) if cid in game["players"]]
    lines = []
    for cid in member_ids:
        mark = "✅" if cid in ready else "⬜"
        lines.append(f"{mark} {player_name(cid)}")
    return "\n".join(lines), len(ready), len(member_ids)


def handle_alliance_group_raid(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return
    if al.get("group_raid_cd") and fromiso(al.get("group_raid_cd"), now()) > now():
        send(
            chat_id,
            T(
                "alliance.group_raid_cd",
                time=fmt_cd(
                    (fromiso(al.get("group_raid_cd"), now()) - now()).total_seconds()
                ),
            ),
            keypad=alliance_keypad(chat_id),
        )
        return

    session = alliance_group_session(al)
    if not session:
        target = alliance_group_raid_target(al)
        session = {
            "created_at": iso(now()),
            "expires_at": iso(now() + timedelta(minutes=20)),
            "ready": [],
            "target": target,
        }
        al["group_raid_session"] = session
        alliance_log(al, "group_raid_created", {"target": target.get("name")})
        send_group_radio(
            T(
                "group_radio.group_raid_lobby",
                alliance=al.get("name"),
                target=target.get("name"),
                total=len(
                    [cid for cid in al.get("members", []) if cid in game["players"]]
                ),
            ),
            force=True,
            reason="group_raid_lobby",
        )

    ready_lines, ready_count, total_members = alliance_group_ready_lines(al, session)
    save_game()
    target = session.get("target", {})
    can_start = ready_count >= total_members and total_members > 0
    rows = [[B("alliance_group_ready")]]
    if can_start:
        rows.append([B("alliance_group_start")])
    if al.get("owner") == chat_id:
        rows.append([B("alliance_group_cancel")])
    rows.append([B("alliance")])
    rows.append([B("main_menu")])

    send(
        chat_id,
        T(
            "alliance.group_raid_lobby",
            target=display_name(target.get("name")),
            defense=fmt_num(target.get("defense", 0)),
            water=fmt_num(target.get("water", 0)),
            ready=ready_count,
            total=total_members,
            members=ready_lines,
            left=fmt_cd(
                (fromiso(session.get("expires_at"), now()) - now()).total_seconds()
            ),
            status=T("alliance.group_raid_can_start")
            if can_start
            else T("alliance.group_raid_waiting"),
        ),
        keypad=make_keypad(rows),
    )


def handle_alliance_group_ready(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return
    session = alliance_group_session(al)
    if not session:
        return handle_alliance_group_raid(chat_id)
    ready = session.setdefault("ready", [])
    if chat_id not in ready:
        ready.append(chat_id)
        alliance_log(al, "group_raid_ready", {"player": chat_id})
    ready_count = len(set(ready))
    total_members = len(
        [cid for cid in al.get("members", []) if cid in game["players"]]
    )
    if total_members > 0 and ready_count >= total_members:
        send_group_radio(
            T(
                "group_radio.group_raid_ready",
                alliance=al.get("name"),
                total=total_members,
            ),
            force=True,
            reason="group_raid_ready",
        )
    save_game()
    handle_alliance_group_raid(chat_id)


def handle_alliance_group_cancel(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return
    if al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    al.pop("group_raid_session", None)
    alliance_log(al, "group_raid_cancelled", {"by": chat_id})
    save_game()
    send(chat_id, T("alliance.group_raid_cancelled"), keypad=alliance_keypad(chat_id))


def handle_alliance_group_start(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return
    if al.get("group_raid_cd") and fromiso(al.get("group_raid_cd"), now()) > now():
        return handle_alliance_group_raid(chat_id)
    session = alliance_group_session(al)
    if not session:
        return handle_alliance_group_raid(chat_id)

    member_ids = [cid for cid in al.get("members", []) if cid in game["players"]]
    ready = set(session.get("ready", []))
    if not set(member_ids).issubset(ready):
        send(
            chat_id,
            T("alliance.group_raid_not_all_ready"),
            keypad=alliance_keypad(chat_id),
        )
        return

    total_power = 0
    for cid in member_ids:
        mp = game["players"][cid]
        recalc_power(mp)
        total_power += int(mp.get("total_attack", 0)) + int(mp.get("level", 1)) * 25

    target = session.get("target", {})
    enemy_def = int(target.get("defense", 1000))
    roll = random.uniform(0.82, 1.18)
    effective = int(total_power * roll)
    al["group_raid_cd"] = iso(now() + timedelta(hours=4))
    al.pop("group_raid_session", None)

    if effective >= enemy_def:
        if target.get("type") == "player" and target.get("chat_id") in game["players"]:
            victim = game["players"][target["chat_id"]]
            steal = min(
                int(victim.get("water", 0)),
                max(120, int(victim.get("water", 0) * random.uniform(0.08, 0.18))),
            )
            victim["water"] = max(0, int(victim.get("water", 0)) - steal)
            victim.setdefault("stats", {})["water_lost"] = (
                victim.get("stats", {}).get("water_lost", 0) + steal
            )
            send(
                target["chat_id"],
                T(
                    "alliance.group_raid_victim",
                    alliance=al.get("name"),
                    lost=fmt_num(steal),
                ),
                keypad=main_keypad(target["chat_id"]),
            )
            gross = (
                steal
                + random.randint(250, 650)
                + len(member_ids) * random.randint(45, 120)
            )
        else:
            gross = (
                random.randint(700, 1400)
                + len(member_ids) * random.randint(90, 180)
                + cartel_level(al) * 260
            )

        vault_add = int(gross * 0.45)
        al["vault"] = int(al.get("vault", 0)) + vault_add
        each = max(1, int((gross - vault_add) / max(1, len(member_ids))))
        for cid in member_ids:
            mp = game["players"][cid]
            mp["water"] = int(mp.get("water", 0)) + each
            # صندوق از حمله گروهی هم کم‌یاب باشد.
            mp["loot_caches"] = int(mp.get("loot_caches", 0)) + (
                1 if random.random() < 0.08 else 0
            )
            mp.setdefault("stats", {})["group_raids"] = (
                mp.get("stats", {}).get("group_raids", 0) + 1
            )
        alliance_log(
            al,
            "group_raid_win",
            {
                "target": target.get("name"),
                "gross": gross,
                "vault": vault_add,
                "each": each,
            },
        )
        add_news(
            T(
                "alliance.group_raid_news",
                name=al.get("name"),
                target=target.get("name"),
                gross=fmt_num(gross),
            ),
            important=True,
        )
        msg = T(
            "alliance.group_raid_win",
            target=display_name(target.get("name")),
            power=fmt_num(effective),
            defense=fmt_num(enemy_def),
            gross=fmt_num(gross),
            each=fmt_num(each),
            vault=fmt_num(vault_add),
        )
    else:
        dmg = random.randint(8, 22)
        for cid in member_ids:
            mp = game["players"][cid]
            mp["hp"] = max(1, int(mp.get("hp", 100)) - dmg)
        alliance_log(
            al, "group_raid_lose", {"target": target.get("name"), "damage": dmg}
        )
        msg = T(
            "alliance.group_raid_lose",
            target=display_name(target.get("name")),
            power=fmt_num(effective),
            defense=fmt_num(enemy_def),
            damage=dmg,
        )
    if effective < enemy_def:
        send_group_radio(
            T(
                "group_radio.group_raid_lost",
                alliance=al.get("name"),
                target=target.get("name"),
                power=fmt_num(effective),
                defense=fmt_num(enemy_def),
            ),
            force=True,
            reason="group_raid_lost",
        )
    save_game()
    for cid in member_ids:
        send(cid, msg, keypad=alliance_keypad(cid))


def current_event() -> Optional[dict[str, Any]]:
    ev = game.get("world_event_active")
    if not ev:
        return None
    if fromiso(ev.get("expires_at"), now()) <= now():
        game["world_event_active"] = None
        return None
    return ev


def event_mod(key: str, default: float = 1.0) -> float:
    ev = current_event()
    if not ev:
        return default
    mods = ev.get("mods", {})
    return float(mods.get(key, default))


def maybe_daily_event() -> None:
    # One event per calendar day. It activates when bot is running after DAILY_EVENT_HOUR.
    today = today_key()
    if game.get("last_daily_event") == today:
        return
    if now().hour < DAILY_EVENT_HOUR:
        return
    ev = dict(random.choice(DAILY_EVENTS))
    ev["started_at"] = iso(now())
    ev["expires_at"] = iso(now() + timedelta(hours=24))
    game["world_event_active"] = ev
    game["last_daily_event"] = today
    apply_event_one_time(ev)
    send_group_radio(
        T(
            "group_radio.daily_event",
            title=ev["title"],
            desc=ev["desc"],
            effect_text=ev["effect_text"],
        ),
        force=True,
        reason="daily_event",
    )
    for cid in list(game["players"].keys()):
        if game["players"][cid].get("registered"):
            send(
                cid,
                T(
                    "world.daily_event",
                    title=ev["title"],
                    desc=ev["desc"],
                    effect_text=ev["effect_text"],
                ),
                keypad=main_keypad(cid),
            )
    save_game()


def apply_event_one_time(ev: dict[str, Any]) -> None:
    kind = ev.get("one_time")
    if not kind:
        return
    for cid, p in game["players"].items():
        if not p.get("registered"):
            continue
        if kind == "acid":
            wall = int(p.get("buildings", {}).get("wall", 0))
            if wall < 2:
                p["hp"] = max(1, int(p.get("hp", 100)) - random.randint(6, 16))
        elif kind == "heal":
            p["hp"] = min(100, int(p.get("hp", 100)) + random.randint(10, 25))
        elif kind == "airdrop":
            for r in ["scrap", "plastic", "glass"]:
                p.setdefault("resources", {})[r] = p.get("resources", {}).get(
                    r, 0
                ) + random.randint(4, 14)


def season_score_breakdown(chat_id: str) -> dict[str, int]:
    p = game["players"][chat_id]
    recalc_power(p)

    atk = int(p.get("total_attack", 0))
    dfc = int(p.get("total_defense", 0))
    balanced_power_bonus = min(atk, dfc) * 0.45  # تشویق تعادل حمله/دفاع

    # کامبت: غارت خیلی مهم‌تر شد
    combat = int(
        atk * 1.45
        + dfc * 1.25
        + balanced_power_bonus
        + int(p.get("stats", {}).get("raids_done", 0)) * 180  # غارت خیلی مهم
        + int(p.get("stats", {}).get("boss_damage", 0)) * 0.08  # آسیب به باس
    )

    # اقتصاد: آب مهمه ولی منابع خام کمتر تأثیرگذار
    res_value = sum(
        int(p.get("resources", {}).get(r, 0)) * system_reference_price(r)
        for r in RESOURCES
    )
    economy = int(
        int(p.get("water", 0)) * 1.1  # آب همچنان پاداش خوب
        + res_value * 0.28  # منابع خام nerf شد
        + int(p.get("stats", {}).get("market_sales", 0)) * 90
        + int(p.get("stats", {}).get("alliance_shared", 0)) * 70
    )

    # پیشرفت (ساختمان، لول، فعالیت)
    building_levels = sum(int(v) for v in p.get("buildings", {}).values())
    stats = p.get("stats", {})

    progress = int(
        cartel_score_bonus(chat_id) * 1.2
        + int(p.get("level", 1)) * 950  # لول خیلی مهم
        + int(p.get("xp", 0)) * 18
        + building_levels * 420  # ساختمان قوی‌تر
        + int(stats.get("scavenge_success", 0)) * 65
        + int(stats.get("raids_done", 0)) * 95  # غارت هم اینجا امتیاز می‌ده
        + int(stats.get("missions_completed", 0)) * 180
        + int(p.get("season_points_bonus", 0)) * 1.4
    )

    honor = int(p.get("honor", 0)) * 6.5  # افتخار کمی قوی‌تر

    total = max(0, combat + economy + progress + honor)

    return {
        "combat": combat,
        "economy": economy,
        "progress": progress,
        "honor": honor,
        "total": total,
    }


def season_score(chat_id: str) -> int:
    return season_score_breakdown(chat_id)["total"]


def ranked_players(include_banned: bool = False) -> list[tuple[str, int]]:
    rows = [
        (cid, season_score(cid))
        for cid, p in game["players"].items()
        if p.get("registered") and (include_banned or not p.get("banned"))
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows


def season_left_text() -> str:
    end = fromiso(game.get("season", {}).get("end"), now())
    sec = max(0, int((end - now()).total_seconds()))
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return T("season.left_days", days=d, hours=h)
    if h:
        return T("season.left_hours", hours=h, minutes=m)
    return T("season.left_minutes", minutes=m)


def maybe_roll_season() -> None:
    season = game.get("season") or default_season(1)
    if fromiso(season.get("end"), now()) > now():
        return

    rows = ranked_players()
    winners_lines = []
    archive_rows = []

    # جوایز افتخاری (بدون بوست قوی)
    top_prizes = {
        1: "👑 پادشاه زباله",
        2: "🥈 امپراتور نقره‌ای",
        3: "🥉 لرد برنزی",
        4: "قهرمان آهن",
        5: "بازمانده افسانه‌ای",
    }

    for i, (cid, score) in enumerate(rows[:10], start=1):
        p = game["players"][cid]
        title = top_prizes.get(i, "مدال برتر")

        # ذخیره عنوان دائمی
        p.setdefault("season_titles", [])
        if title not in p["season_titles"]:
            p["season_titles"].append(title)

        line = f"{i}. {display_name(p.get('name'))} — {fmt_num(score)} امتیاز\n   🏆 {title}"
        winners_lines.append(line)
        archive_rows.append(
            {"rank": i, "chat_id": cid, "name": p.get("name"), "score": score}
        )

    old_id = int(season.get("id", 1))
    new_id = old_id + 1

    old_archive = {
        "id": old_id,
        "ended_at": iso(now()),
        "winners": archive_rows,
    }

    # === ریست بازیکن‌ها ===
    preserved: dict[str, dict[str, Any]] = {}
    for cid, p in game["players"].items():
        rank = next((i for i, (x, _) in enumerate(rows, start=1) if x == cid), None)
        score = season_score(cid) if p.get("registered") else 0

        np = new_player(p.get("name") or "", cid)
        np["registered"] = p.get("registered", bool(p.get("name")))
        np["ref_code"] = p.get("ref_code", generate_ref_code(cid))
        np["referrals_count"] = p.get("referrals_count", 0)
        np["referral_used"] = p.get("referral_used", False)
        np["referred_by"] = p.get("referred_by")
        np["career"] = p.get(
            "career", {"seasons_played": 0, "best_rank": None, "best_score": 0}
        )
        np["season_titles"] = p.get("season_titles", [])
        np["profile_frames"] = p.get("profile_frames", [])
        np["honor"] = p.get("honor", 0)

        if p.get("registered"):
            np["career"]["seasons_played"] = (
                int(np["career"].get("seasons_played", 0)) + 1
            )
            if rank and (
                np["career"].get("best_rank") is None
                or rank < np["career"].get("best_rank")
            ):
                np["career"]["best_rank"] = rank
            if score > int(np["career"].get("best_score", 0)):
                np["career"]["best_score"] = score

        preserved[cid] = np

    # === اعمال تغییرات ===
    game["players"] = preserved
    for al in game.get("alliances", {}).values():
        al["vault"] = 0
        al["total_shared"] = 0
        al["level"] = 1
        al["applicants"] = []
        al["group_raid_session"] = None
        al["group_raid_cd"] = None
        al["log"] = []
        al.setdefault("resource_vault", {})
        for r in RESOURCES:
            al["resource_vault"][r] = 0
        al["mission_day"] = None
        al["alliance_missions"] = []
        # فقط اعضایی که هنوز بازیکن فعال و ثبت‌نام‌شده‌اند نگه داشته شوند
        al["members"] = [
            cid
            for cid in al.get("members", [])
            if cid in game["players"] and game["players"][cid].get("registered")
        ]
    game["market_orders"] = []
    game["next_order_id"] = 1
    game["world_event_active"] = None

    archives = list(season.get("archives", []))[-5:] + [old_archive]
    game["season"] = default_season(new_id)
    game["season"]["archives"] = archives

    winners_text = "\n".join(winners_lines) or "بدون بازیکن"

    # پیام حماسی پایان فصل — بدون تگ HTML، بولد فقط با متادیتا
    end_msg = f"""🏁 پایان سیزن {old_id} — حماسه آخرالزمان

🔥 برترین‌های این فصل:
{winners_text}

👑 تالار مشاهیر به‌روزرسانی شد.

سیزن {new_id} آغاز شد.
همه از صفر شروع می‌کنند، اما نام افسانه‌ها برای همیشه باقی می‌ماند.

شهر دوباره منتظر حماسه است..."""

    meta = build_meta_bold(
        end_msg,
        [
            f"پایان سیزن {old_id} — حماسه آخرالزمان",
            "برترین‌های این فصل:",
            "تالار مشاهیر",
            f"سیزن {new_id}",
        ],
    )

    # ارسال به همه بازیکن‌ها
    for cid, p in game["players"].items():
        if p.get("registered"):
            send(
                cid,
                end_msg,
                keypad=main_keypad(cid),
                meta_data=meta,
            )

    # ارسال به گروه رادیو
    send_group_radio(end_msg, force=True, reason="season_end")

    save_game()


# ══════════════════════════════════════════════════════
#  MARKET
# ══════════════════════════════════════════════════════
def system_reference_price(res: str) -> int:
    base = BASE_PRICE[res]
    supply = max(0, int(game.get("market_supply", {}).get(res, 0)))
    # قیمت مرجع بازار باید راهنما باشد، نه چاپخانه آب.
    # قبلاً قیمت سیستم در ایونت‌ها خیلی بالا می‌رفت و بازیکن‌ها همان ساعات اول هزاران آب می‌گرفتند.
    price = int(base * 1.05 - min(base * 0.35, supply * 0.25))
    price = max(int(base * 0.65), min(price, int(base * 1.8)))
    price = int(price * event_mod("all_prices", 1.0))
    price = int(price * event_mod(f"price_{res}", 1.0))
    return max(1, price)


def system_buy_price(res: str) -> int:
    # فروش فوری باید اضطراری باشد، نه بهترین راه پولدار شدن.
    return max(1, int(system_reference_price(res) * 0.25))


def system_sell_price(res: str) -> int:
    # خرید از سیستم باید فقط راه اضطراری باشد.
    # سیستم خیلی ارزان می‌خرد و خیلی گران می‌فروشد تا بازار مردم جذاب‌تر بماند.
    return max(1, int(system_reference_price(res) * 2.50))


def maybe_system_daily_restock() -> bool:
    """
    روزی یک بار مقدار کمی موجودی اضطراری به سیستم اضافه می‌کند.
    این شارژ بی‌نهایت نیست: فقط تا سقف تعیین‌شده پر می‌شود.
    موجودی‌ای که بازیکن‌ها با «فروش فوری به سیستم» اضافه می‌کنند، جداگانه باقی می‌ماند.
    """
    today = today_key()
    if game.get("last_system_restock") == today:
        return False
    if now().hour < DAILY_EVENT_HOUR:
        return False

    supply = game.setdefault("market_supply", {r: 0 for r in RESOURCES})
    added: dict[str, int] = {}
    for r in RESOURCES:
        current = max(0, int(supply.get(r, 0)))
        daily = max(0, int(SYSTEM_DAILY_RESTOCK.get(r, 0)))
        cap = max(daily, int(SYSTEM_STOCK_CAP.get(r, daily)))

        # فقط موجودی رایگان روزانه را تا سقف پر کن؛
        # اگر بازیکن‌ها قبلاً زیاد به سیستم فروخته باشند، چیزی حذف نمی‌شود.
        qty = max(0, min(daily, cap - current))
        if qty > 0:
            supply[r] = current + qty
            added[r] = qty
        else:
            supply[r] = current

    game["last_system_restock"] = today
    if added:
        log = game.setdefault("system_stock_log", [])
        log.append({"date": today, "added": added})
        del log[:-30]
    save_game()
    return bool(added)


def market_keypad() -> dict[str, Any]:
    return make_keypad(
        [
            [B("market_people"), B("market_create_order")],
            [B("market_my_orders"), B("market_barter")],
            [B("market_my_barters"), B("market_resource_rentals")],
            [B("market_system_sell"), B("market_system_buy")],
            [B("market_prices")],
            [B("main_menu")],
        ]
    )


def system_sell_keypad() -> dict[str, Any]:
    return make_keypad(
        [
            [B("system_sell_scrap"), B("system_sell_plastic")],
            [B("system_sell_glass"), B("system_sell_battery")],
            [B("system_sell_copper")],
            [B("back_market"), B("main_menu")],
        ]
    )


def system_buy_keypad() -> dict[str, Any]:
    return make_keypad(
        [
            [B("system_buy_scrap"), B("system_buy_plastic")],
            [B("system_buy_glass"), B("system_buy_battery")],
            [B("system_buy_copper")],
            [B("back_market"), B("main_menu")],
        ]
    )


def open_barter_orders() -> list[dict[str, Any]]:
    expire_barter_orders()
    return [o for o in game.get("barter_orders", []) if o.get("status") == "open"]


def parse_resource_pairs(text: str) -> Optional[dict[str, int]]:
    # Supports: "مس 10" and multi-resource text like "اوراق 30 شیشه 5".
    if not text:
        return None
    tokens = re.findall(r"[\wآ-یئ]+|\d+", text.replace("×", " ").replace("،", " "))
    result: dict[str, int] = {}
    i = 0
    while i < len(tokens):
        r = res_key(tokens[i])
        if not r or r == "water" or r not in RESOURCES:
            return None
        if i + 1 >= len(tokens):
            return None
        qty = safe_int(tokens[i + 1], -1)
        if qty <= 0:
            return None
        result[r] = result.get(r, 0) + qty
        i += 2
    return result or None


def parse_barter_text(text: str) -> Optional[tuple[dict[str, int], dict[str, int]]]:
    if "=" not in text:
        return None
    left, right = text.split("=", 1)
    give = parse_resource_pairs(left)
    want = parse_resource_pairs(right)
    if not give or not want:
        return None
    return give, want


def expire_barter_orders() -> None:
    changed = False
    now_ts = now()
    for o in game.setdefault("barter_orders", []):
        if o.get("status") != "open":
            continue
        expires_at = fromiso(o.get("expires_at"), now_ts)
        if expires_at > now_ts:
            continue
        seller = game.get("players", {}).get(o.get("seller_id"))
        if seller:
            for r, q in o.get("give", {}).items():
                add_amount(seller, r, int(q))
        o["status"] = "expired"
        o["expired_at"] = iso(now_ts)
        changed = True
    if changed:
        save_game()


def handle_barter_menu(chat_id: str) -> None:
    orders = [o for o in open_barter_orders() if o.get("seller_id") != chat_id]
    if not orders:
        rows = [
            [B("market_create_barter")],
            [B("market_my_barters")],
            [B("back_market"), B("main_menu")],
        ]
        send(chat_id, T("barter.empty"), keypad=make_keypad(rows))
        return
    lines = []
    rows: list[list[str]] = []
    for o in orders[:10]:
        lines.append(
            T(
                "barter.order_line",
                id=o["id"],
                seller=display_name(player_name(o["seller_id"])),
                give=fmt_res_dict(o.get("give", {})),
                want=fmt_res_dict(o.get("want", {})),
                left=fmt_cd(
                    (fromiso(o.get("expires_at"), now()) - now()).total_seconds()
                ),
            )
        )
        rows.append([f"قبول معاوضه #{o['id']}"])
    rows.append([B("market_create_barter"), B("market_my_barters")])
    rows.append([B("back_market"), B("main_menu")])
    send(chat_id, T("barter.list", orders="\n\n".join(lines)), keypad=make_keypad(rows))


def handle_create_barter_prompt(chat_id: str) -> None:
    p = get_player(chat_id)
    active = [o for o in open_barter_orders() if o.get("seller_id") == chat_id]
    if len(active) >= 3:
        send(chat_id, T("barter.too_many"), keypad=market_keypad())
        return
    game["chat_states"][chat_id] = {"state": "awaiting_barter_order"}
    save_game()
    send(
        chat_id,
        T("barter.create_prompt"),
        keypad=make_keypad([[B("back_market"), B("main_menu")]]),
    )


def handle_create_barter(chat_id: str, text: str) -> None:
    p = get_player(chat_id)
    parsed = parse_barter_text(text)
    if not parsed:
        send(chat_id, T("barter.bad_format"), keypad=market_keypad())
        return
    give, want = parsed
    active = [o for o in open_barter_orders() if o.get("seller_id") == chat_id]
    if len(active) >= 3:
        send(chat_id, T("barter.too_many"), keypad=market_keypad())
        return
    if not has_resources(p, give):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(give, p)),
            keypad=market_keypad(),
        )
        return
    pay_cost(p, give)
    oid = int(game.get("next_barter_id", 1))
    game["next_barter_id"] = oid + 1
    order = {
        "id": oid,
        "seller_id": chat_id,
        "give": give,
        "want": want,
        "status": "open",
        "created_at": iso(now()),
        "expires_at": iso(now() + timedelta(hours=12)),
    }
    game.setdefault("barter_orders", []).append(order)
    game["chat_states"].pop(chat_id, None)
    log_action(chat_id, "barter_create", order)
    save_game()
    send(
        chat_id,
        T("barter.created", id=oid, give=fmt_res_dict(give), want=fmt_res_dict(want)),
        keypad=market_keypad(),
    )


def find_barter_order(barter_id: int) -> Optional[dict[str, Any]]:
    for o in open_barter_orders():
        if int(o.get("id", -1)) == int(barter_id):
            return o
    return None


def handle_accept_barter(chat_id: str, text: str) -> None:
    oid = parse_order_id(text)
    o = find_barter_order(oid or -1)
    if not o:
        send(chat_id, T("barter.not_found"), keypad=market_keypad())
        return
    if o.get("seller_id") == chat_id:
        send(chat_id, T("barter.cannot_accept_own"), keypad=market_keypad())
        return
    buyer = get_player(chat_id)
    seller = get_player(o["seller_id"])
    want = o.get("want", {})
    give = o.get("give", {})
    if not has_resources(buyer, want):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(want, buyer)),
            keypad=market_keypad(),
        )
        return
    pay_cost(buyer, want)
    for r, q in give.items():
        add_amount(buyer, r, int(q))
    for r, q in want.items():
        add_amount(seller, r, int(q))
    o["status"] = "done"
    o["buyer_id"] = chat_id
    o["done_at"] = iso(now())
    buyer.setdefault("stats", {})["barter_done"] = (
        int(buyer.get("stats", {}).get("barter_done", 0)) + 1
    )
    seller.setdefault("stats", {})["barter_done"] = (
        int(seller.get("stats", {}).get("barter_done", 0)) + 1
    )
    inc_mission(chat_id, "barter", 1)
    inc_mission(o["seller_id"], "barter", 1)
    inc_mission(chat_id, "market_sell", 1)
    inc_mission(o["seller_id"], "market_sell", 1)
    log_action(chat_id, "barter_accept", {"id": oid})
    save_game()
    send(
        chat_id,
        T(
            "barter.accepted_buyer",
            give=fmt_res_dict(want),
            got=fmt_res_dict(give),
            seller=display_name(player_name(o["seller_id"])),
        ),
        keypad=market_keypad(),
    )
    send(
        o["seller_id"],
        T(
            "barter.accepted_seller",
            give=fmt_res_dict(give),
            got=fmt_res_dict(want),
            buyer=display_name(player_name(chat_id)),
        ),
        keypad=main_keypad(chat_id),
    )


def handle_my_barters(chat_id: str) -> None:
    expire_barter_orders()
    orders = [
        o
        for o in game.get("barter_orders", [])
        if o.get("seller_id") == chat_id and o.get("status") == "open"
    ]
    if not orders:
        send(chat_id, T("barter.my_empty"), keypad=market_keypad())
        return
    lines = [
        T(
            "barter.my_line",
            id=o["id"],
            give=fmt_res_dict(o.get("give", {})),
            want=fmt_res_dict(o.get("want", {})),
            left=fmt_cd((fromiso(o.get("expires_at"), now()) - now()).total_seconds()),
        )
        for o in orders
    ]
    rows = [[f"لغو معاوضه #{o['id']}"] for o in orders[:10]] + [
        [B("market_create_barter")],
        [B("back_market"), B("main_menu")],
    ]
    send(
        chat_id,
        T("barter.my_list", orders="\n\n".join(lines)),
        keypad=make_keypad(rows),
    )


def handle_cancel_barter(chat_id: str, text: str) -> None:
    oid = parse_order_id(text)
    o = find_barter_order(oid or -1)
    if not o or o.get("seller_id") != chat_id:
        send(chat_id, T("barter.not_found"), keypad=market_keypad())
        return
    p = get_player(chat_id)
    for r, q in o.get("give", {}).items():
        add_amount(p, r, int(q))
    o["status"] = "cancelled"
    o["cancelled_at"] = iso(now())
    log_action(chat_id, "barter_cancel", {"id": oid})
    save_game()
    send(chat_id, T("barter.cancelled", id=oid), keypad=market_keypad())


def open_rental_contracts() -> list[dict[str, Any]]:
    process_resource_rentals()
    return [x for x in game.get("resource_rentals", []) if x.get("status") == "open"]


def parse_rental_text(
    text: str,
) -> Optional[tuple[dict[str, int], dict[str, int], int]]:
    # Simple format: "مس 10 = مس 12 6" meaning 6 hours.
    if "=" not in text:
        return None
    left, right = text.split("=", 1)
    right_tokens = right.split()
    hours = 6
    if right_tokens and safe_int(right_tokens[-1], -1) > 0:
        hours = safe_int(right_tokens[-1], 6)
        right = " ".join(right_tokens[:-1])
    give = parse_resource_pairs(left)
    repay = parse_resource_pairs(right)
    if not give or not repay:
        return None
    hours = max(1, min(48, int(hours)))
    return give, repay, hours * 3600


def rental_profit_ok(give: dict[str, int], repay: dict[str, int]) -> bool:
    # Restrict obvious single-resource high interest to 30%.
    if len(give) == 1 and len(repay) == 1:
        rg, qg = next(iter(give.items()))
        rr, qr = next(iter(repay.items()))
        if rg == rr and int(qr) > int(qg * 1.30 + 0.999):
            return False
    return True


def player_has_active_rental(chat_id: str) -> bool:
    for c in game.get("resource_rentals", []):
        if c.get("status") in {"accepted", "overdue"} and (
            c.get("borrower") == chat_id or c.get("lender") == chat_id
        ):
            return True
    return False


def process_resource_rentals() -> None:
    changed = False
    now_ts = now()
    for c in game.setdefault("resource_rentals", []):
        if c.get("status") not in {"accepted", "overdue"}:
            continue
        borrower = game.get("players", {}).get(c.get("borrower"))
        lender = game.get("players", {}).get(c.get("lender"))
        if not borrower or not lender:
            continue
        if fromiso(c.get("due_at"), now_ts) <= now_ts:
            c["status"] = "overdue"
            changed = True
        if c.get("status") == "overdue":
            remaining = c.setdefault("remaining", dict(c.get("repay", {})))
            for r, need in list(remaining.items()):
                take = min(int(need), amount_of(borrower, r))
                if take > 0:
                    add_amount(borrower, r, -take)
                    add_amount(lender, r, take)
                    remaining[r] = int(need) - take
                    changed = True
                if int(remaining.get(r, 0)) <= 0:
                    remaining.pop(r, None)
            if not remaining:
                c["status"] = "repaid"
                c["repaid_at"] = iso(now_ts)
                changed = True
    if changed:
        save_game()


def rental_keypad() -> dict[str, Any]:
    return make_keypad(
        [[B("rental_create"), B("rental_my")], [B("back_market"), B("main_menu")]]
    )


def handle_resource_rentals(chat_id: str) -> None:
    contracts = [c for c in open_rental_contracts() if c.get("lender") != chat_id]
    lines = []
    rows: list[list[str]] = []
    for c in contracts[:10]:
        lines.append(
            T(
                "rental.line",
                id=c["id"],
                lender=display_name(player_name(c["lender"])),
                give=fmt_res_dict(c.get("give", {})),
                repay=fmt_res_dict(c.get("repay", {})),
                time=fmt_cd(int(c.get("duration_seconds", 0))),
            )
        )
        rows.append([f"قبول قرارداد #{c['id']}"])
    rows.append([B("rental_create"), B("rental_my")])
    rows.append([B("back_market"), B("main_menu")])
    txt = T("rental.list", contracts="\n\n".join(lines) if lines else T("rental.empty"))
    send(chat_id, txt, keypad=make_keypad(rows))


def handle_create_rental_prompt(chat_id: str) -> None:
    p = get_player(chat_id)
    if int(p.get("level", 1)) < 3:
        send(chat_id, T("rental.level_required"), keypad=market_keypad())
        return
    if player_has_active_rental(chat_id):
        send(chat_id, T("rental.active_limit"), keypad=market_keypad())
        return
    game["chat_states"][chat_id] = {"state": "awaiting_rental_order"}
    save_game()
    send(
        chat_id,
        T("rental.create_prompt"),
        keypad=make_keypad([[B("back_market"), B("main_menu")]]),
    )


def handle_create_rental(chat_id: str, text: str) -> None:
    p = get_player(chat_id)
    parsed = parse_rental_text(text)
    if not parsed:
        send(chat_id, T("rental.bad_format"), keypad=market_keypad())
        return
    give, repay, duration = parsed
    if not rental_profit_ok(give, repay):
        send(chat_id, T("rental.profit_limit"), keypad=market_keypad())
        return
    if not has_resources(p, give):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(give, p)),
            keypad=market_keypad(),
        )
        return
    pay_cost(p, give)
    cid = int(game.get("next_rental_id", 1))
    game["next_rental_id"] = cid + 1
    c = {
        "id": cid,
        "lender": chat_id,
        "borrower": None,
        "give": give,
        "repay": repay,
        "duration_seconds": duration,
        "accepted_at": None,
        "due_at": None,
        "status": "open",
        "created_at": iso(now()),
    }
    game.setdefault("resource_rentals", []).append(c)
    game["chat_states"].pop(chat_id, None)
    log_action(chat_id, "rental_create", c)
    save_game()
    send(
        chat_id,
        T(
            "rental.created",
            id=cid,
            give=fmt_res_dict(give),
            repay=fmt_res_dict(repay),
            time=fmt_cd(duration),
        ),
        keypad=market_keypad(),
    )


def find_rental_contract(cid: int) -> Optional[dict[str, Any]]:
    for c in game.get("resource_rentals", []):
        if int(c.get("id", -1)) == int(cid) and c.get("status") == "open":
            return c
    return None


def handle_accept_rental(chat_id: str, text: str) -> None:
    cid = parse_order_id(text)
    c = find_rental_contract(cid or -1)
    if not c:
        send(chat_id, T("rental.not_found"), keypad=market_keypad())
        return
    if c.get("lender") == chat_id:
        send(chat_id, T("rental.cannot_accept_own"), keypad=market_keypad())
        return
    if player_has_active_rental(chat_id):
        send(chat_id, T("rental.active_limit"), keypad=market_keypad())
        return
    borrower = get_player(chat_id)
    lender = get_player(c["lender"])
    for r, q in c.get("give", {}).items():
        add_amount(borrower, r, int(q))
    c["borrower"] = chat_id
    c["accepted_at"] = iso(now())
    c["due_at"] = iso(now() + timedelta(seconds=int(c.get("duration_seconds", 0))))
    c["remaining"] = dict(c.get("repay", {}))
    c["status"] = "accepted"
    borrower.setdefault("stats", {})["rentals_taken"] = (
        int(borrower.get("stats", {}).get("rentals_taken", 0)) + 1
    )
    lender.setdefault("stats", {})["rentals_given"] = (
        int(lender.get("stats", {}).get("rentals_given", 0)) + 1
    )
    save_game()
    send(
        chat_id,
        T(
            "rental.accepted_borrower",
            got=fmt_res_dict(c.get("give", {})),
            repay=fmt_res_dict(c.get("repay", {})),
            due=fmt_dt(c.get("due_at")),
            lender=display_name(player_name(c["lender"])),
        ),
        keypad=market_keypad(),
    )
    send(
        c["lender"],
        T(
            "rental.accepted_lender",
            borrower=display_name(player_name(chat_id)),
            give=fmt_res_dict(c.get("give", {})),
            repay=fmt_res_dict(c.get("repay", {})),
            due=fmt_dt(c.get("due_at")),
        ),
        keypad=main_keypad(chat_id),
    )


def handle_my_rentals(chat_id: str) -> None:
    process_resource_rentals()
    mine = [
        c
        for c in game.get("resource_rentals", [])
        if c.get("lender") == chat_id or c.get("borrower") == chat_id
    ]
    active = [c for c in mine if c.get("status") in {"open", "accepted", "overdue"}]
    if not active:
        send(chat_id, T("rental.my_empty"), keypad=rental_keypad())
        return
    lines = []
    rows: list[list[str]] = []
    for c in active[:10]:
        role = "قرض‌دهنده" if c.get("lender") == chat_id else "قرض‌گیرنده"
        lines.append(
            T(
                "rental.my_line",
                id=c["id"],
                role=role,
                status=c.get("status"),
                give=fmt_res_dict(c.get("give", {})),
                repay=fmt_res_dict(c.get("remaining") or c.get("repay", {})),
                due=fmt_dt(c.get("due_at")) if c.get("due_at") else "هنوز قبول نشده",
            )
        )
        if c.get("status") == "open" and c.get("lender") == chat_id:
            rows.append([f"لغو قرارداد #{c['id']}"])
    rows.append([B("back_market"), B("main_menu")])
    send(
        chat_id,
        T("rental.my_list", contracts="\n\n".join(lines)),
        keypad=make_keypad(rows),
    )


def handle_cancel_rental(chat_id: str, text: str) -> None:
    cid = parse_order_id(text)
    c = find_rental_contract(cid or -1)
    if not c or c.get("lender") != chat_id:
        send(chat_id, T("rental.not_found"), keypad=market_keypad())
        return
    p = get_player(chat_id)
    for r, q in c.get("give", {}).items():
        add_amount(p, r, int(q))
    c["status"] = "cancelled"
    c["cancelled_at"] = iso(now())
    save_game()
    send(chat_id, T("rental.cancelled", id=cid), keypad=market_keypad())


# ══════════════════════════════════════════════════════
#  HANDLERS: REGISTRATION
# ══════════════════════════════════════════════════════
def extract_ref_from_start(text: str) -> Optional[str]:
    m = re.search(r"REF\d{4,}", text or "", re.I)
    return m.group(0).upper() if m else None


def normalize_unique_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def garage_name_exists(name: str, except_chat_id: str | None = None) -> bool:
    target = normalize_unique_name(name)

    for cid, player in game.get("players", {}).items():
        if except_chat_id and cid == except_chat_id:
            continue

        existing = normalize_unique_name(player.get("name", ""))

        if existing == target:
            return True

    return False


def is_reserved_registration_name(value: str) -> bool:
    """Prevent keypad/menu labels from being saved as garage names."""
    raw = (value or "").strip()
    norm = normalize_unique_name(raw)

    button_labels = []
    try:
        button_labels = [str(v) for v in TEXTS.get("buttons", {}).values()]
    except Exception:
        button_labels = []

    reserved = {
        "/start",
        "start",
        "شروع",
        "منوی اصلی",
        "↩️ منوی اصلی",
        *button_labels,
    }
    return norm in {normalize_unique_name(x) for x in reserved if x}


def ensure_registered(chat_id: str, text: str, sender_name: str) -> bool:
    p = get_player(chat_id)
    if extract_ref_from_start(text):
        p["pending_referral"] = extract_ref_from_start(text)
    state = game.setdefault("chat_states", {}).get(chat_id, {}).get("state")

    # Registration states must be handled before the normal registered shortcut.
    if state == "awaiting_name":
        if is_reserved_registration_name(text):
            send(
                chat_id,
                T("registration.bad_name"),
                remove_keypad=True,
            )
            return False

        name = clean_name(text, 20)
        if not name:
            send(
                chat_id,
                T("registration.bad_name"),
                remove_keypad=True,
            )
            return False
        if garage_name_exists(name, except_chat_id=chat_id):
            send(
                chat_id,
                T("registration.name_taken"),
                remove_keypad=True,
            )
            return False
        p["name"] = name
        p["registered"] = True
        p["registered_at"] = iso(now())
        game["chat_states"][chat_id] = {"state": "awaiting_referral_optional"}
        save_game()
        send(chat_id, T("registration.ask_ref"), keypad=make_keypad([[B("skip")]]))
        return False

    if state == "awaiting_referral_optional":
        code = text.strip()
        pending = p.get("pending_referral")
        if code != B("skip") or pending:
            apply_referral(chat_id, pending or code)
        p["pending_referral"] = None
        game["chat_states"].pop(chat_id, None)
        save_game()
        send(
            chat_id,
            T(
                "registration.done",
                name=p["name"],
                water=p["water"],
                scrap=p["resources"].get("scrap"),
                plastic=p["resources"].get("plastic"),
                glass=p["resources"].get("glass"),
            ),
            keypad=main_keypad(chat_id),
        )
        return False

    if p.get("registered"):
        return True

    game["chat_states"][chat_id] = {"state": "awaiting_name"}
    save_game()
    # Do not show the main-menu keypad while we are asking for a name.
    # Otherwise a user can tap it and accidentally register as "↩️ منوی اصلی".
    send(chat_id, T("registration.ask_name"), remove_keypad=True)
    return False


def apply_referral(chat_id: str, code: str) -> bool:
    code = (code or "").strip().upper()
    p = game["players"][chat_id]
    if p.get("referral_used"):
        return False
    inviter_id = None
    for cid, op in game["players"].items():
        if cid != chat_id and op.get("ref_code", "").upper() == code:
            inviter_id = cid
            break
    if not inviter_id:
        return False
    inviter = game["players"][inviter_id]
    p["referral_used"] = True
    p["referred_by"] = inviter_id
    p["water"] += 500
    p["resources"]["scrap"] += 15
    p["resources"]["plastic"] += 15
    p["resources"]["glass"] += 8
    p["season_points_bonus"] += 500
    inviter["referrals_count"] = int(inviter.get("referrals_count", 0)) + 1
    inviter["water"] += 700
    inviter["resources"]["scrap"] += 20
    inviter["resources"]["copper"] += 5
    inviter["resources"]["battery"] += 1
    inviter["season_points_bonus"] += 1000
    log_action(chat_id, "referral_used", {"inviter": inviter_id})
    log_action(inviter_id, "referral_invited", {"new_player": chat_id})
    send(
        inviter_id,
        T("registration.ref_ok", inviter=display_name(inviter.get("name")), water=700),
        keypad=main_keypad(inviter_id),
    )
    return True


# ══════════════════════════════════════════════════════
#  HANDLERS: MAIN / PROFILE
# ══════════════════════════════════════════════════════


def profile_upgrades_text(p: dict[str, Any]) -> str:
    ups = p.get("upgrades_in_progress", [])
    if not ups:
        return T("profile.upgrades_none")
    lines = [T("profile.upgrades_title")]
    for u in ups:
        bk = u.get("bldg")
        if bk not in BUILDINGS:
            continue
        lines.append(
            T(
                "profile.upgrade_line",
                label=BUILDINGS[bk]["label"],
                level=u.get("to_level", "؟"),
                time=fmt_cd((fromiso(u.get("finish"), now()) - now()).total_seconds()),
            )
        )
    return "\n".join(lines) if len(lines) > 1 else T("profile.upgrades_none")


def handle_start(chat_id: str, name: str = "") -> None:
    p = get_player(chat_id, name)
    passive_income(chat_id)
    finish_upgrades(p)
    recalc_power(p)
    save_game()
    send(
        chat_id,
        T("start.welcome", name=p.get("name") or player_name(chat_id)),
        keypad=main_keypad(chat_id),
    )


def handle_profile(chat_id: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finished = finish_upgrades(p)
    for u in finished:
        send(
            chat_id,
            T(
                "buildings.finished",
                label=BUILDINGS[u["bldg"]]["label"],
                level=u["to_level"],
            ),
        )
    recalc_power(p)
    lv, xp, mx, label = level_info(p)
    stats = p.get("stats", {})
    sh = shield_remaining(p)
    shield_line = (
        T("profile.shield_active", time=fmt_cd(sh)) if sh else T("profile.shield_off")
    )
    total_sv = stats.get("scavenges", 0)
    ok_sv = stats.get("scavenge_success", 0)
    fail_sv = max(0, total_sv - ok_sv)
    rate = f"{int(ok_sv / max(1, total_sv) * 100)}%" if total_sv else "0%"
    al = p.get("alliance") or "ندارم"

    txt = T(
        "profile.text",
        name=display_name(p.get("name")),
        season_id=game.get("season", {}).get("id", 1),
        season_left=season_left_text(),
        level_label=label,
        scavenge_ready="✅" if cd_remaining(p, "scavenge") == 0 else "💤",
        scavenge_cd=fmt_cd(cd_remaining(p, "scavenge")),
        raid_ready="✅" if cd_remaining(p, "raid") == 0 else "💤",
        raid_cd=fmt_cd(cd_remaining(p, "raid")),
        shield_line=shield_line,
        honor=p.get("honor", 0),
        honor_title=honor_title(p.get("honor", 0)),
        level=lv,
        xp=xp,
        max_xp=mx,
        xp_bar=xp_bar(xp, mx),
        hp=p.get("hp", 100),
        water=p.get("water", 0),
        scrap=p["resources"].get("scrap", 0),
        plastic=p["resources"].get("plastic", 0),
        glass=p["resources"].get("glass", 0),
        battery=p["resources"].get("battery", 0),
        copper=p["resources"].get("copper", 0),
        attack=f"{p.get('total_attack', 0):,}",
        defense=f"{p.get('total_defense', 0):,}",
        power=f"{p.get('total_attack', 0) + p.get('total_defense', 0):,}",
        alliance=al,
        alliance_shared=stats.get("alliance_shared", 0),
        scavenges=total_sv,
        scavenge_success=ok_sv,
        scavenge_fail=fail_sv,
        scavenge_rate=rate,
        raids_done=stats.get("raids_done", 0),
        raids_received=stats.get("raids_received", 0),
        base_status=base_status_label(p),
        upgrades=profile_upgrades_text(p),
    )
    txt += "\n\n" + profile_daily_missions_text(chat_id)

    meta = build_meta_bold(
        txt,
        [
            (txt[:25], 25),
            "سطح:",
            "حمله:",
            "دفاع:",
            "افتخار:",
        ],
    )

    save_game()
    send(chat_id, txt, keypad=main_keypad(chat_id), meta_data=meta)


# ══════════════════════════════════════════════════════
#  HANDLERS: SCAVENGE
# ══════════════════════════════════════════════════════
def scavenge_keypad() -> dict[str, Any]:
    return make_keypad(
        [
            [B("scavenge_alley"), B("scavenge_suburb")],
            [B("scavenge_center"), B("scavenge_bunker")],
            [B("main_menu")],
        ]
    )


def handle_scavenge_menu(chat_id: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    if cd_remaining(p, "scavenge") > 0:
        send(
            chat_id,
            T("scavenge.cooldown", time=fmt_cd(cd_remaining(p, "scavenge"))),
            keypad=main_keypad(chat_id),
        )
        return
    lines = []
    for key, z in ZONES.items():
        risk = max(0, z["risk"] + int(event_mod("risk", 0)))
        chance = max(5, min(95, 100 - risk * 12))
        lines.append(
            T(
                "scavenge.zone_line",
                label=B(z["label_key"]),
                desc=z["desc"],
                chance=chance,
                loot_min=z["loot_min"],
                loot_max=z["loot_max"],
                xp=z["xp"],
            )
        )
    ev = current_event()
    event_line = ""
    if ev:
        event_line = f"\n\n🌪️ رویداد فعال: {ev['title']}\n📌 {ev['effect_text']}"
    send(
        chat_id,
        T(
            "scavenge.menu",
            zones="\n".join(lines) + event_line,
        ),
        keypad=scavenge_keypad(),
    )


def zone_by_label(text: str) -> Optional[str]:
    for key, z in ZONES.items():
        if text == B(z["label_key"]):
            return key
    return None


def handle_scavenge(chat_id: str, zone_key: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    if cd_remaining(p, "scavenge") > 0:
        send(
            chat_id,
            T("scavenge.cooldown", time=fmt_cd(cd_remaining(p, "scavenge"))),
            keypad=main_keypad(chat_id),
        )
        return
    z = ZONES[zone_key]
    risk = max(0, z["risk"] + int(event_mod("risk", 0)))
    chance = max(5, min(95, 100 - risk * 12))
    roll = random.randint(1, 100)
    p["stats"]["scavenges"] = p["stats"].get("scavenges", 0) + 1
    inc_mission(chat_id, "scavenge", 1)
    base_cd = z["cd_min"] * 60
    loot_note = ""
    if roll <= chance:
        p["stats"]["scavenge_success"] = p["stats"].get("scavenge_success", 0) + 1
        total = random.randint(z["loot_min"], z["loot_max"])
        total = int(total * event_mod("loot", 1.0))
        pool = ["scrap", "plastic", "glass", "battery", "copper"]
        weights = {
            "alley": [42, 35, 18, 3, 2],
            "suburb": [30, 28, 24, 10, 8],
            "center": [22, 20, 24, 18, 16],
            "bunker": [15, 15, 20, 25, 25],
        }[zone_key]
        rare_mod = event_mod("rare_loot", 1.0)
        weights[3] = int(weights[3] * rare_mod)
        weights[4] = int(weights[4] * rare_mod)
        loot: dict[str, int] = {}
        for _ in range(total):
            r = random.choices(pool, weights=weights)[0]
            loot[r] = loot.get(r, 0) + 1
            p["resources"][r] = p["resources"].get(r, 0) + 1
        level_up = add_xp(p, z["xp"])
        set_cd(p, "scavenge", base_cd)
        save_game()
        loot_str = fmt_res_lines(loot)
        extra_lines = []
        cache_note = maybe_find_cache(chat_id, zone_key)
        if cache_note:
            extra_lines.append(cache_note)
        legendary_note = maybe_award_legendary(chat_id, "گشت‌زنی", chance=0.001)
        if legendary_note:
            extra_lines.append(legendary_note)
        if extra_lines:
            loot_str += "\n\n" + "\n".join(extra_lines)
        lvl_msg = T("scavenge.level_up", level=p["level"]) if level_up else ""
        log_action(chat_id, "scavenge_success", {"zone": zone_key, "loot": loot})
        msg = T(
            "scavenge.success",
            zone=B(z["label_key"]),
            story=T("scavenge.stories_success"),
            loot=loot_str,
            xp=int(z["xp"] * event_mod("xp", 1.0)),
            chance=chance,
            roll=roll,
            level_msg=lvl_msg,
            alliance_note=loot_note or T("scavenge.no_share"),
            cooldown=fmt_cd(base_cd),
        )
    else:
        damage = random.randint(5, 20 + risk * 3)
        p["hp"] = max(1, p.get("hp", 100) - damage)
        lost = {}
        for r in RESOURCES:
            have = p["resources"].get(r, 0)
            if have > 0:
                qty = random.randint(0, min(3, have))
                if qty:
                    p["resources"][r] -= qty
                    lost[r] = qty
        lost_str = fmt_res_loss(lost)
        set_cd(p, "scavenge", base_cd)
        save_game()
        log_action(
            chat_id, "scavenge_fail", {"zone": zone_key, "damage": damage, "lost": lost}
        )
        msg = T(
            "scavenge.fail",
            zone=B(z["label_key"]),
            story=T("scavenge.stories_fail"),
            damage=damage,
            hp=p["hp"],
            lost=lost_str,
            chance=chance,
            roll=roll,
            cooldown=fmt_cd(base_cd),
        )
    save_game()
    send(chat_id, msg, keypad=main_keypad(chat_id))


# ══════════════════════════════════════════════════════
#  HANDLERS: MARKET
# ══════════════════════════════════════════════════════
def handle_market_menu(chat_id: str) -> None:
    maybe_system_daily_restock()
    prices = []
    for r in RESOURCES:
        prices.append(
            T(
                "market.price_line",
                icon=RES_ICON[r],
                name=RES_NAME[r],
                public=system_reference_price(r),
                system=system_buy_price(r),
                system_sell=system_sell_price(r),
            )
        )
    send(chat_id, T("market.menu", prices="\n".join(prices)), keypad=market_keypad())


def open_orders() -> list[dict[str, Any]]:
    """Return currently open player market orders.

    Kept as a small helper because several market/admin screens call it.
    Missing this function caused NameError when pressing «سفارش‌های من».
    """
    return [
        o
        for o in game.get("market_orders", [])
        if isinstance(o, dict) and o.get("status") == "open"
    ]


def handle_market_people(chat_id: str) -> None:
    orders = open_orders()
    if not orders:
        send(chat_id, T("market.people_empty"), keypad=market_keypad())
        return
    lines = []
    rows: list[list[str]] = []
    for o in orders[:10]:
        r = o["resource"]
        lines.append(
            T(
                "market.order_line",
                id=o["id"],
                icon=RES_ICON[r],
                res_name=RES_NAME[r],
                qty=o["qty"],
                unit=o["unit_price"],
                total=o["qty"] * o["unit_price"],
                seller=display_name(player_name(o["seller_id"])),
            )
        )
        rows.append([f"خرید #{o['id']}"])
    rows.append([B("back_market"), B("main_menu")])
    send(
        chat_id,
        T("market.people_list", id=orders[0]["id"], orders="\n".join(lines)),
        keypad=make_keypad(rows),
    )


def handle_create_order_prompt(chat_id: str) -> None:
    game["chat_states"][chat_id] = {"state": "awaiting_market_order"}
    save_game()
    send(
        chat_id,
        T("market.create_prompt"),
        keypad=make_keypad([[B("back_market"), B("main_menu")]]),
    )


def handle_create_order(chat_id: str, text: str) -> None:
    p = get_player(chat_id)
    parts = text.replace("×", " ").split()
    if len(parts) < 3:
        send(
            chat_id,
            T("market.bad_format") + "\n\n" + T("market.create_prompt"),
            keypad=market_keypad(),
        )
        return
    r = res_key(parts[0])
    qty = safe_int(parts[1], -1)
    unit = safe_int(parts[2], -1)
    if not r:
        send(chat_id, T("market.bad_resource"), keypad=market_keypad())
        return
    if qty <= 0 or unit <= 0:
        send(
            chat_id,
            T("market.bad_format") + "\nمثال: اوراق 10 80",
            keypad=market_keypad(),
        )
        return
    if p["resources"].get(r, 0) < qty:
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage({r: qty}, p)),
            keypad=market_keypad(),
        )
        return
    p["resources"][r] -= qty
    oid = int(game.get("next_order_id", 1))
    game["next_order_id"] = oid + 1
    order = {
        "id": oid,
        "seller_id": chat_id,
        "resource": r,
        "qty": qty,
        "unit_price": unit,
        "status": "open",
        "created_at": iso(now()),
    }
    game.setdefault("market_orders", []).append(order)
    game["chat_states"].pop(chat_id, None)
    log_action(chat_id, "market_create_order", order)
    save_game()
    send(
        chat_id,
        T(
            "market.created",
            id=oid,
            res_name=RES_NAME[r],
            qty=qty,
            unit=unit,
            total=qty * unit,
        ),
        keypad=market_keypad(),
    )


def find_order(order_id: int) -> Optional[dict[str, Any]]:
    for o in game.get("market_orders", []):
        if int(o.get("id", -1)) == order_id and o.get("status") == "open":
            return o
    return None


def parse_order_id(text: str) -> Optional[int]:
    m = re.search(r"#?\s*(\d+)", text or "")
    return int(m.group(1)) if m else None


def handle_buy_order(chat_id: str, text: str) -> None:
    oid = parse_order_id(text)
    if not oid:
        send(chat_id, T("market.order_not_found"), keypad=market_keypad())
        return
    o = find_order(oid)
    if not o:
        send(chat_id, T("market.order_not_found"), keypad=market_keypad())
        return
    if o["seller_id"] == chat_id:
        send(chat_id, T("market.cannot_buy_own"), keypad=market_keypad())
        return
    buyer = get_player(chat_id)
    seller = get_player(o["seller_id"])
    total = int(o["qty"] * o["unit_price"])
    if buyer.get("water", 0) < total:
        send(
            chat_id,
            T("errors.not_enough_water", need=total, have=buyer.get("water", 0)),
            keypad=market_keypad(),
        )
        return
    buyer["water"] -= total
    buyer["resources"][o["resource"]] = buyer["resources"].get(o["resource"], 0) + int(
        o["qty"]
    )
    net, note = award_water(o["seller_id"], total, "market_sale", alliance_share=True)
    o["status"] = "sold"
    o["buyer_id"] = chat_id
    o["sold_at"] = iso(now())
    buyer["stats"]["market_buys"] = buyer["stats"].get("market_buys", 0) + 1
    seller["stats"]["market_sales"] = seller["stats"].get("market_sales", 0) + 1
    inc_mission(o["seller_id"], "market_sell", 1)
    add_news(
        f"⚖️ {player_name(o['seller_id'])} یک بسته در بازار فروخت: {RES_NAME[o['resource']]} × {o['qty']}"
    )
    log_action(chat_id, "market_buy", {"order_id": oid, "total": total})
    log_action(
        o["seller_id"], "market_sold", {"order_id": oid, "gross": total, "net": net}
    )
    save_game()
    send(
        chat_id,
        T(
            "market.bought_buyer",
            seller=display_name(player_name(o["seller_id"])),
            res_name=RES_NAME[o["resource"]],
            qty=o["qty"],
            total=total,
            water=buyer["water"],
        ),
        keypad=market_keypad(),
    )
    send(
        o["seller_id"],
        T(
            "market.bought_seller",
            buyer=player_name(chat_id),
            res_name=RES_NAME[o["resource"]],
            qty=o["qty"],
            gross=total,
            net=net,
            share_note=note,
        ),
        keypad=main_keypad(chat_id),
    )


def handle_my_orders(chat_id: str) -> None:
    orders = [o for o in open_orders() if o["seller_id"] == chat_id]
    if not orders:
        send(chat_id, T("market.own_orders_empty"), keypad=market_keypad())
        return
    lines = [
        T(
            "market.order_line",
            id=o["id"],
            icon=RES_ICON[o["resource"]],
            res_name=RES_NAME[o["resource"]],
            qty=o["qty"],
            unit=o["unit_price"],
            total=o["qty"] * o["unit_price"],
            seller=player_name(chat_id),
        )
        for o in orders
    ]
    rows = [[f"لغو #{o['id']}"] for o in orders[:10]] + [
        [B("back_market"), B("main_menu")]
    ]
    send(
        chat_id,
        T("market.own_orders", orders="\n".join(lines), id=orders[0]["id"]),
        keypad=make_keypad(rows),
    )


def handle_cancel_order(chat_id: str, text: str) -> None:
    oid = parse_order_id(text)
    o = find_order(oid or -1)
    if not o or o.get("seller_id") != chat_id:
        send(chat_id, T("market.order_not_found"), keypad=market_keypad())
        return
    p = get_player(chat_id)
    p["resources"][o["resource"]] = p["resources"].get(o["resource"], 0) + int(o["qty"])
    o["status"] = "cancelled"
    o["cancelled_at"] = iso(now())
    log_action(chat_id, "market_cancel", {"order_id": oid})
    save_game()
    send(chat_id, T("market.cancelled", id=oid), keypad=market_keypad())


def handle_system_sell_menu(chat_id: str) -> None:
    send(chat_id, T("market.system_prompt"), keypad=system_sell_keypad())


def system_sell_resource_from_text(text: str) -> Optional[str]:
    for r in RESOURCES:
        if text == B(f"system_sell_{r}"):
            return r
    return None


def handle_system_sell_select(chat_id: str, r: str) -> None:
    p = get_player(chat_id)
    game["chat_states"][chat_id] = {"state": "awaiting_system_sell_qty", "resource": r}
    save_game()
    send(
        chat_id,
        T(
            "market.system_qty_prompt",
            res_name=RES_NAME[r],
            have=p["resources"].get(r, 0),
            price=system_buy_price(r),
        ),
        keypad=make_keypad([["همه"], [B("back_market"), B("main_menu")]]),
    )


def handle_system_sell_qty(chat_id: str, text: str) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    r = st.get("resource")
    if r not in RESOURCES:
        game["chat_states"].pop(chat_id, None)
        handle_market_menu(chat_id)
        return
    p = get_player(chat_id)
    have = int(p["resources"].get(r, 0))
    qty = have if text.strip() == "همه" else safe_int(text, -1)
    if qty <= 0 or qty > have:
        send(chat_id, T("errors.bad_number"), keypad=system_sell_keypad())
        return
    price = system_buy_price(r)
    gross = qty * price
    p["resources"][r] -= qty
    game.setdefault("market_supply", {})[r] = (
        int(game.get("market_supply", {}).get(r, 0)) + qty
    )
    net, note = award_water(chat_id, gross, "system_sale", alliance_share=True)
    game["chat_states"].pop(chat_id, None)
    log_action(
        chat_id, "system_sell", {"resource": r, "qty": qty, "gross": gross, "net": net}
    )
    save_game()
    send(
        chat_id,
        T(
            "market.system_sold",
            res_name=RES_NAME[r],
            qty=qty,
            price=price,
            gross=gross,
            net=net,
            share_note=note,
        ),
        keypad=market_keypad(),
    )


def handle_system_buy_menu(chat_id: str) -> None:
    maybe_system_daily_restock()
    supply = game.setdefault("market_supply", {})
    lines = []
    for r in RESOURCES:
        lines.append(
            T(
                "market.system_buy_line",
                icon=RES_ICON[r],
                res_name=RES_NAME[r],
                price=system_sell_price(r),
                available=int(supply.get(r, 0)),
            )
        )
    send(
        chat_id,
        T(
            "market.system_buy_prompt",
            items="\n".join(lines),
            hour=DAILY_EVENT_HOUR,
            daily_scrap=SYSTEM_DAILY_RESTOCK["scrap"],
            daily_plastic=SYSTEM_DAILY_RESTOCK["plastic"],
            daily_glass=SYSTEM_DAILY_RESTOCK["glass"],
            daily_battery=SYSTEM_DAILY_RESTOCK["battery"],
            daily_copper=SYSTEM_DAILY_RESTOCK["copper"],
        ),
        keypad=system_buy_keypad(),
    )


def system_buy_resource_from_text(text: str) -> Optional[str]:
    for r in RESOURCES:
        if text == B(f"system_buy_{r}"):
            return r
    return None


def handle_system_buy_select(chat_id: str, r: str) -> None:
    supply = int(game.setdefault("market_supply", {}).get(r, 0))
    if supply <= 0:
        send(
            chat_id,
            T("market.system_buy_empty", res_name=RES_NAME[r]),
            keypad=system_buy_keypad(),
        )
        return
    p = get_player(chat_id)
    price = system_sell_price(r)
    water = int(p.get("water", 0))
    max_buy = min(supply, water // price)
    if max_buy <= 0:
        send(
            chat_id,
            T("errors.not_enough_water", need=price, have=water),
            keypad=system_buy_keypad(),
        )
        return
    game["chat_states"][chat_id] = {"state": "awaiting_system_buy_qty", "resource": r}
    save_game()
    send(
        chat_id,
        T(
            "market.system_buy_qty_prompt",
            res_name=RES_NAME[r],
            available=supply,
            price=price,
            water=water,
            max_buy=max_buy,
        ),
        keypad=make_keypad([["حداکثر"], [B("back_market"), B("main_menu")]]),
    )


def handle_system_buy_qty(chat_id: str, text: str) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    r = st.get("resource")
    if r not in RESOURCES:
        game["chat_states"].pop(chat_id, None)
        handle_market_menu(chat_id)
        return

    p = get_player(chat_id)
    supply = int(game.setdefault("market_supply", {}).get(r, 0))
    price = system_sell_price(r)
    max_buy = min(supply, int(p.get("water", 0)) // price)
    wants_max = text.strip() in {"حداکثر", "همه"}
    qty = max_buy if wants_max else safe_int(text, -1)

    if qty <= 0:
        if wants_max:
            send(
                chat_id,
                T("errors.not_enough_water", need=price, have=int(p.get("water", 0))),
                keypad=system_buy_keypad(),
            )
        else:
            send(chat_id, T("errors.bad_number"), keypad=system_buy_keypad())
        return
    if supply <= 0:
        game["chat_states"].pop(chat_id, None)
        send(
            chat_id,
            T("market.system_buy_empty", res_name=RES_NAME[r]),
            keypad=market_keypad(),
        )
        return
    if qty > supply:
        send(
            chat_id,
            T(
                "market.system_buy_not_enough_supply",
                res_name=RES_NAME[r],
                available=supply,
            ),
            keypad=system_buy_keypad(),
        )
        return

    total = qty * price
    if int(p.get("water", 0)) < total:
        send(
            chat_id,
            T("errors.not_enough_water", need=total, have=int(p.get("water", 0))),
            keypad=system_buy_keypad(),
        )
        return

    p["water"] = int(p.get("water", 0)) - total
    p["resources"][r] = int(p["resources"].get(r, 0)) + qty
    game["market_supply"][r] = supply - qty
    p.setdefault("stats", {})["market_buys"] = (
        int(p.get("stats", {}).get("market_buys", 0)) + 1
    )
    game["chat_states"].pop(chat_id, None)
    log_action(
        chat_id,
        "system_buy",
        {"resource": r, "qty": qty, "price": price, "total": total},
    )
    save_game()
    send(
        chat_id,
        T(
            "market.system_bought",
            res_name=RES_NAME[r],
            qty=qty,
            price=price,
            total=total,
            water=int(p.get("water", 0)),
        ),
        keypad=market_keypad(),
    )


# ══════════════════════════════════════════════════════
#  HANDLERS: BUILDINGS / CRAFT
# ══════════════════════════════════════════════════════
def building_effect_text(data: dict[str, Any]) -> str:
    parts = []
    if data.get("prod"):
        parts.append(f"تولید {data['prod']}💧/ساعت")
    if data.get("def"):
        parts.append(f"دفاع +{data['def']}")
    if data.get("atk"):
        parts.append(f"حمله +{data['atk']}")
    if data.get("discount"):
        parts.append(f"تخفیف ساخت {int(data['discount'] * 100)}٪")
    if data.get("fee_cut"):
        parts.append(f"کاهش هزینه بازار {int(data['fee_cut'] * 100)}٪")
    if data.get("heal_bonus"):
        parts.append(f"درمان +{data['heal_bonus']}")
    return " | ".join(parts) or "اثر ویژه"


def buildings_keypad() -> dict[str, Any]:
    rows = [[f"⬆️ {data['label']}"] for data in BUILDINGS.values()]
    rows.append([B("main_menu")])
    return make_keypad(rows)


def handle_buildings_menu(chat_id: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finished = finish_upgrades(p)
    lines = []
    for bk, bdata in BUILDINGS.items():
        lv = int(p.get("buildings", {}).get(bk, 0))
        inprog = upgrade_in_progress(p, bk)
        max_lv = max(bdata["levels"].keys())
        if inprog is not None:
            status = T("buildings.progress", time=fmt_cd(inprog))
        elif lv <= 0:
            status = T("buildings.not_built")
        elif lv >= max_lv:
            status = T("buildings.max", level=lv)
        else:
            status = T("buildings.level", level=lv)
        if lv >= max_lv:
            next_info = "سقف فعلی"
        else:
            nd = bdata["levels"][lv + 1]
            next_info = T(
                "buildings.next_info",
                cost=fmt_res_dict(nd["cost"]),
                time=fmt_cd(nd["time"]),
                effect=building_effect_text(nd),
            )
        lines.append(
            T(
                "buildings.line",
                label=bdata["label"],
                status=status,
                next_info=next_info,
            )
        )
    save_game()
    send(
        chat_id, T("buildings.menu", lines="\n".join(lines)), keypad=buildings_keypad()
    )


def building_key_from_text(text: str) -> Optional[str]:
    for bk, bd in BUILDINGS.items():
        if text == f"⬆️ {bd['label']}":
            return bk
    return None


def handle_upgrade(chat_id: str, bk: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    bd = BUILDINGS[bk]
    lv = int(p.get("buildings", {}).get(bk, 0))
    max_lv = max(bd["levels"].keys())
    if lv >= max_lv:
        send(
            chat_id, T("buildings.maxed", label=bd["label"]), keypad=buildings_keypad()
        )
        return
    inprog = upgrade_in_progress(p, bk)
    if inprog is not None:
        send(
            chat_id,
            T("buildings.already_progress", label=bd["label"], time=fmt_cd(inprog)),
            keypad=buildings_keypad(),
        )
        return
    nd = bd["levels"][lv + 1]
    cost = dict(nd["cost"])
    # lab discounts building costs a little after level 1
    lab_lv = int(p.get("buildings", {}).get("lab", 0))
    discount = 0.0
    if lab_lv and bk != "lab":
        discount = BUILDINGS["lab"]["levels"].get(lab_lv, {}).get("discount", 0)
    if discount:
        cost = {r: max(1, int(q * (1 - discount))) for r, q in cost.items()}
    if not has_resources(p, cost):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(cost, p)),
            keypad=buildings_keypad(),
        )
        return
    pay_cost(p, cost)
    finish = iso(now() + timedelta(seconds=nd["time"]))
    p.setdefault("upgrades_in_progress", []).append(
        {"bldg": bk, "to_level": lv + 1, "finish": finish}
    )
    log_action(
        chat_id, "upgrade_start", {"building": bk, "level": lv + 1, "cost": cost}
    )
    save_game()
    send(
        chat_id,
        T(
            "buildings.upgrade_started",
            label=bd["label"],
            level=lv + 1,
            cost=fmt_res_lines(cost),
            time=fmt_cd(nd["time"]),
        ),
        keypad=buildings_keypad(),
    )
    apply_building_bonuses(p)
    recalc_power(p)


def craft_keypad() -> dict[str, Any]:
    rows = [[item["label"]] for item in CRAFT_ITEMS.values()]
    rows.append([B("main_menu")])
    return make_keypad(rows)


def craft_key_from_text(text: str) -> Optional[str]:
    for k, item in CRAFT_ITEMS.items():
        if text == item["label"]:
            return k
    return None


def discounted_craft_cost(p: dict[str, Any], cost: dict[str, int]) -> dict[str, int]:
    disc = event_mod("craft_discount", 0.0)
    lab_lv = int(p.get("buildings", {}).get("lab", 0))
    if lab_lv:
        disc += BUILDINGS["lab"]["levels"].get(lab_lv, {}).get("discount", 0)
    disc = min(0.35, disc)
    return {r: max(1, int(q * (1 - disc))) for r, q in cost.items()}


def handle_craft_menu(chat_id: str) -> None:
    p = get_player(chat_id)
    lines = []
    for k, item in CRAFT_ITEMS.items():
        cost = discounted_craft_cost(p, item["cost"])
        effect = []
        if item.get("atk"):
            effect.append(f"⚔️ حمله +{item['atk']}")
        if item.get("def"):
            effect.append(f"🛡️ دفاع +{item['def']}")
        if item.get("heal"):
            effect.append(f"❤️ جان +{item['heal']}")
        if item.get("special"):
            effect.append(SPECIAL_EFFECT_TEXT.get(k, "✨ آیتم خاص"))
        lines.append(
            T(
                "craft.line",
                label=item["label"],
                cost=fmt_res_dict(cost),
                effect=" | ".join(effect),
            )
        )
    send(chat_id, T("craft.menu", lines="\n".join(lines)), keypad=craft_keypad())


def handle_craft(chat_id: str, item_key: str) -> None:
    p = get_player(chat_id)
    item = CRAFT_ITEMS[item_key]
    cost = discounted_craft_cost(p, item["cost"])
    if not has_resources(p, cost):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(cost, p)),
            keypad=craft_keypad(),
        )
        return
    spec = item.get("special")
    if spec == "repair" and not p.get("upgrades_in_progress"):
        send(
            chat_id,
            "🔧 الان هیچ ارتقایی در جریان نداری.\n\nکیت تعمیر وقتی به درد می‌خورد که یک ساختمان در حال ارتقا باشد.",
            keypad=craft_keypad(),
        )
        return
    if spec == "shield" and is_shielded(p):
        send(
            chat_id,
            T("shield.active", time=fmt_cd(shield_remaining(p))),
            keypad=craft_keypad(),
        )
        return
    pay_cost(p, cost)
    if spec == "shield":
        if is_shielded(p):
            send(
                chat_id,
                T("shield.active", time=fmt_cd(shield_remaining(p))),
                keypad=craft_keypad(),
            )
            return
        p["shield_until"] = iso(
            now() + timedelta(seconds=int(item.get("duration", SHIELD_DURATION)))
        )
        msg = T(
            "craft.shield_activated",
            time=fmt_cd(int(item.get("duration", SHIELD_DURATION))),
        )
    elif spec == "repair":
        for u in p.get("upgrades_in_progress", []):
            finish = fromiso(u.get("finish"), now())
            left = max(0, (finish - now()).total_seconds())
            u["finish"] = iso(now() + timedelta(seconds=left * 0.5))
        msg = T("craft.repair")
    elif spec:
        p.setdefault("inventory", {})[item_key] = (
            p.get("inventory", {}).get(item_key, 0) + 1
        )
        msg = T("craft.special", label=item["label"], qty=p["inventory"][item_key])
    elif item.get("heal"):
        heal_bonus = 0
        h_lv = int(p.get("buildings", {}).get("hospital", 0))
        if h_lv:
            heal_bonus = (
                BUILDINGS["hospital"]["levels"].get(h_lv, {}).get("heal_bonus", 0)
            )
        heal = min(100 - p.get("hp", 100), item["heal"] + heal_bonus)
        p["hp"] = min(100, p.get("hp", 100) + heal)
        msg = T("craft.healed", label=item["label"], heal=heal, hp=p["hp"])
    else:
        p.setdefault("inventory", {})[item_key] = (
            p.get("inventory", {}).get(item_key, 0) + 1
        )
        recalc_power(p)
        msg = T(
            "craft.crafted",
            label=item["label"],
            attack=f"{p['total_attack']:,}",
            defense=f"{p['total_defense']:,}",
        )
    log_action(chat_id, "craft", {"item": item_key, "cost": cost})
    save_game()
    send(chat_id, msg, keypad=craft_keypad())


# ══════════════════════════════════════════════════════
#  HANDLERS: RAID / SHIELD
# ══════════════════════════════════════════════════════
def raid_target_button(name: str) -> str:
    return T("raid.button", name=name)


def raid_bucket_from_text(text: str) -> Optional[str]:
    for key, cfg in RAID_BUCKETS.items():
        if text == B(cfg["button_key"]):
            return key
    return None


def raid_target_score(p: dict[str, Any]) -> int:
    recalc_power(p)
    return (
        int(p.get("water", 0))
        + int(p.get("total_defense", 0)) * 2
        + int(p.get("total_attack", 0)) * 2
        + int(p.get("level", 1)) * 120
    )


def raid_candidates(
    chat_id: str, include_shielded: bool = False
) -> list[tuple[str, dict[str, Any]]]:
    rows = []
    for cid, rp in game["players"].items():
        if cid == chat_id or not rp.get("registered"):
            continue
        if not include_shielded and is_shielded(rp):
            continue
        recalc_power(rp)
        rows.append((cid, rp))
    rows.sort(key=lambda x: raid_target_score(x[1]))
    return rows


def raid_bucket_targets(
    chat_id: str, bucket_key: str
) -> list[tuple[str, dict[str, Any]]]:
    candidates = raid_candidates(chat_id)
    if len(candidates) <= 2:
        return candidates
    third = max(1, (len(candidates) + 2) // 3)
    if bucket_key == "weak":
        return candidates[:third]
    if bucket_key == "medium":
        return candidates[third : third * 2] or candidates
    if bucket_key == "strong":
        return candidates[third * 2 :] or candidates[-third:]
    return candidates


def handle_attack_menu(chat_id: str) -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    recalc_power(p)
    if p.get("hp", 100) < 25:
        send(chat_id, T("raid.low_hp"), keypad=main_keypad(chat_id))
        return
    if cd_remaining(p, "raid") > 0:
        send(
            chat_id,
            T("raid.cooldown", time=fmt_cd(cd_remaining(p, "raid"))),
            keypad=main_keypad(chat_id),
        )
        return
    if int(p.get("total_attack", 0)) <= 0:
        send(chat_id, T("raid.zero_attack"), keypad=main_keypad(chat_id))
        return

    candidates = raid_candidates(chat_id)
    if not candidates:
        send(chat_id, T("errors.no_rivals"), keypad=main_keypad(chat_id))
        return

    bucket_lines = []
    rows = []
    for key, cfg in RAID_BUCKETS.items():
        targets = raid_bucket_targets(chat_id, key)
        button = B(cfg["button_key"])
        bucket_lines.append(
            T(
                "raid.bucket_line",
                button=button,
                title=cfg["title"],
                count=len(targets),
                loot=int(cfg["loot_mod"] * 100),
                risk="کم"
                if key == "weak"
                else ("معمولی" if key == "medium" else "زیاد"),
            )
        )
        rows.append([button])

    drone_count = int(p.get("inventory", {}).get("spy_drone", 0))
    direct_lines = []
    if drone_count > 0:
        direct_targets = sorted(
            candidates, key=lambda x: raid_target_score(x[1]), reverse=True
        )[:12]
        for cid, rp in direct_targets:
            button = raid_target_button(rp.get("name"))
            direct_lines.append(
                T(
                    "raid.direct_line",
                    button=button,
                    name=display_name(rp.get("name")),
                    level=rp.get("level", 1),
                    defense=f"{rp.get('total_defense', 0):,}",
                    water=f"{rp.get('water', 0):,}",
                )
            )
            rows.append([button])
        drone_hint = T("raid.drone_available", count=drone_count)
    else:
        drone_hint = T("raid.drone_hint")
        direct_lines.append(drone_hint)

    rows.append([B("main_menu")])
    send(
        chat_id,
        T(
            "raid.menu",
            attack=f"{p.get('total_attack', 0):,}",
            bucket_lines="\n".join(bucket_lines),
            direct_lines="\n".join(direct_lines),
            drone_count=drone_count,
        ),
        keypad=make_keypad(rows),
    )


def raid_target_from_text(text: str) -> Optional[str]:
    if text.startswith("حمله دقیق:"):
        name = text.split(":", 1)[1].strip()
        return find_player_by_name(name)
    # compatibility with old buttons
    if text.startswith("حمله:"):
        name = text.split(":", 1)[1].strip()
        return find_player_by_name(name)
    return None


def handle_random_raid(chat_id: str, bucket_key: str) -> None:
    targets = raid_bucket_targets(chat_id, bucket_key)
    if not targets:
        send(
            chat_id,
            T("raid.no_bucket_targets", title=RAID_BUCKETS[bucket_key]["title"]),
            keypad=main_keypad(chat_id),
        )
        return
    target_id, _ = random.choice(targets)
    handle_raid(chat_id, target_id, bucket_key=bucket_key, precise=False)


def handle_raid(
    chat_id: str,
    target_id: str,
    bucket_key: Optional[str] = None,
    precise: bool = False,
) -> None:
    p = get_player(chat_id)
    t = game["players"].get(target_id)
    if not t:
        send(chat_id, T("errors.target_not_found"), keypad=main_keypad(chat_id))
        return

    # جلوگیری از حمله به هم‌اتحادی
    if p.get("alliance") and t.get("alliance") == p.get("alliance"):
        send(
            chat_id,
            "❌ نمی‌توانی به اعضای اتحاد خودت حمله کنی.",
            keypad=main_keypad(chat_id),
        )
        return

    passive_income(chat_id)
    finish_upgrades(p)
    recalc_power(p)
    recalc_power(t)

    if p.get("hp", 100) < 25:
        send(chat_id, T("raid.low_hp"), keypad=main_keypad(chat_id))
        return
    if cd_remaining(p, "raid") > 0:
        send(
            chat_id,
            T("raid.cooldown", time=fmt_cd(cd_remaining(p, "raid"))),
            keypad=main_keypad(chat_id),
        )
        return
    if is_shielded(t):
        send(
            chat_id,
            T("raid.shielded", name=display_name(t.get("name"))),
            keypad=main_keypad(chat_id),
        )
        return
    if int(p.get("total_attack", 0)) <= 0:
        send(chat_id, T("raid.zero_attack"), keypad=main_keypad(chat_id))
        return

    raid_notes = []
    if is_shielded(p):
        p["shield_until"] = None
        raid_notes.append("⚠️ محافظت شکست.")

    drone_used = False
    if precise:
        if int(p.get("inventory", {}).get("spy_drone", 0)) <= 0:
            send(chat_id, T("raid.need_drone"), keypad=main_keypad(chat_id))
            return
        # چک سطح هدف برای پهپاد
        if t.get("level", 1) < 3 and abs(t.get("level", 1) - p.get("level", 1)) > 3:
            send(
                chat_id,
                "❌ پهپاد فقط برای اهداف سطح ۳ به بالا یا نزدیک به سطح تو کار می‌کند.",
                keypad=main_keypad(chat_id),
            )
            return
        p["inventory"]["spy_drone"] -= 1
        if p["inventory"].get("spy_drone", 0) <= 0:
            p["inventory"].pop("spy_drone", None)
        drone_used = True
        raid_notes.append("🚁 پهپاد جاسوسی مصرف شد؛ هدف دقیق قفل شد.")

    bucket_key = bucket_key or "medium"
    cfg = RAID_BUCKETS.get(bucket_key, RAID_BUCKETS["medium"])
    raid_type = (
        T("raid.mode_direct") if precise else T("raid.mode_random", title=cfg["title"])
    )

    p["stats"]["raids_done"] = p["stats"].get("raids_done", 0) + 1
    t["stats"]["raids_received"] = t["stats"].get("raids_received", 0) + 1
    inc_mission(chat_id, "raid", 1)

    # فرمول بالانس
    atk = int(p.get("total_attack", 0) * random.uniform(0.92, 1.28) * cfg["atk_mod"])
    atk = int(atk * (1 + p.get("level", 1) * 0.028))

    defense = int(t.get("total_defense", 0) * random.uniform(0.82, 1.18))
    defense = int(defense * (1 + max(0, t.get("level", 1) - 4) * 0.04))

    defense *= event_mod("defense", 1.0)

    # مصرف EMP
    emp_mult = consume_next_raid_emp(chat_id, p, raid_notes)
    if emp_mult < 1.0:
        defense = int(defense * emp_mult)

    if p.get("inventory", {}).get("emp_bomb", 0) > 0:
        p["inventory"]["emp_bomb"] -= 1
        if p["inventory"].get("emp_bomb", 0) <= 0:
            p["inventory"].pop("emp_bomb", None)
        defense = int(defense * 0.75)
        raid_notes.append("💣 بمب EMP مصرف شد؛ دفاع هدف ۲۵٪ ضعیف‌تر شد.")

    if (
        t.get("temp_defense_until")
        and fromiso(t.get("temp_defense_until"), now()) > now()
    ):
        defense = int(defense * 1.15)

    raid_note = "\n".join(raid_notes)
    cd = int(32 * 60 * event_mod("raid_cd", 1.0))

    # ادامه منطق win/lose (همان کد قبلی)
    if atk > defense:
        loot_pct = 0.135 * cfg["loot_mod"] * event_mod("raid_loot", 1.0)
        gross = min(t.get("water", 0), int(t.get("water", 0) * loot_pct))
        t["water"] = max(0, int(t.get("water", 0)) - gross)
        t["stats"]["water_lost"] = t["stats"].get("water_lost", 0) + gross
        net, note = award_water(chat_id, gross, "raid", alliance_share=True)
        p["honor"] += int(cfg["honor_win"])
        t["honor"] -= 4
        leveled = add_xp(p, int(cfg["xp"]))
        set_cd(p, "raid", cd)

        log_action(
            chat_id,
            "raid_win",
            {
                "target": target_id,
                "gross": gross,
                "net": net,
                "bucket": bucket_key,
                "precise": precise,
                "drone_used": drone_used,
            },
        )
        log_action(target_id, "raid_lost", {"attacker": chat_id, "lost": gross})
        register_revenge_target(chat_id, target_id, gross)
        complete_bounty_contracts(chat_id, target_id)

        add_news(
            f"⚔️ {player_name(chat_id)} به {player_name(target_id)} حمله کرد و {gross:,} آب غارت کرد."
        )

        send(
            target_id,
            T("raid.victim", attacker=display_name(p.get("name")), lost=gross),
            keypad=main_keypad(target_id),
        )
        send(
            chat_id,
            T(
                "raid.win",
                raid_type=raid_type,
                target=display_name(t.get("name")),
                atk=f"{int(atk):,}",
                defense=f"{int(defense):,}",
                gross=f"{gross:,}",
                net=f"{net:,}",
                raid_note=(raid_note + "\n") if raid_note else "",
                share_note=note,
                honor=p["honor"],
                level_msg=T("scavenge.level_up", level=p["level"]) if leveled else "",
                cooldown=fmt_cd(cd),
            ),
            keypad=main_keypad(chat_id),
        )
    else:
        dmg = random.randint(10, 28)
        p["hp"] = max(1, p.get("hp", 100) - dmg)
        p["honor"] += int(cfg["honor_lose"])
        t["honor"] += 4
        set_cd(p, "raid", cd)

        log_action(
            chat_id,
            "raid_lose",
            {
                "target": target_id,
                "damage": dmg,
                "bucket": bucket_key,
                "precise": precise,
                "drone_used": drone_used,
            },
        )

        send(
            chat_id,
            T(
                "raid.lose",
                raid_type=raid_type,
                target=display_name(t.get("name")),
                atk=f"{int(atk):,}",
                defense=f"{int(defense):,}",
                raid_note=(raid_note + "\n") if raid_note else "",
                hp=p["hp"],
                honor=p["honor"],
                cooldown=fmt_cd(cd),
            ),
            keypad=main_keypad(chat_id),
        )

    save_game()


def handle_shield(chat_id: str) -> None:
    p = get_player(chat_id)
    sh = shield_remaining(p)
    if sh > 0:
        send(chat_id, T("shield.active", time=fmt_cd(sh)), keypad=main_keypad(chat_id))
        return
    cost = 150
    send(
        chat_id,
        T("shield.menu", cost=cost, water=p.get("water", 0)),
        keypad=make_keypad([[B("shield_buy")], [B("main_menu")]]),
    )


def handle_buy_shield(chat_id: str) -> None:
    p = get_player(chat_id)
    cost = 150
    if p.get("water", 0) < cost:
        send(
            chat_id,
            T("errors.not_enough_water", need=cost, have=p.get("water", 0)),
            keypad=main_keypad(chat_id),
        )
        return
    p["water"] -= cost
    p["shield_until"] = iso(now() + timedelta(seconds=SHIELD_DURATION))
    log_action(chat_id, "buy_shield", {"cost": cost})
    save_game()
    send(chat_id, T("shield.bought", water=p["water"]), keypad=main_keypad(chat_id))


# ══════════════════════════════════════════════════════
#  HANDLERS: ALLIANCE
# ══════════════════════════════════════════════════════


def alliance_keypad(chat_id: str) -> dict[str, Any]:
    p = get_player(chat_id)
    al = player_alliance(chat_id)
    if not al:
        return make_keypad(
            [[B("alliance_create"), B("alliance_list")], [B("main_menu")]]
        )
    rows = [[B("alliance_group_raid"), B("alliance_vault")], [B("alliance_leave")]]
    if al.get("owner") == chat_id:
        rows.insert(0, [B("alliance_manage")])
    rows.append([B("main_menu")])
    return make_keypad(rows)


def handle_alliance_menu(chat_id: str) -> None:
    p = get_player(chat_id)
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return
    lines = []
    for cid in al.get("members", []):
        mp = game["players"].get(cid)
        if mp:
            recalc_power(mp)
            lines.append(
                T(
                    "alliance.member_line",
                    name=mp.get("name"),
                    level=mp.get("level", 1),
                    water=mp.get("water", 0),
                    power=f"{mp.get('total_attack', 0) + mp.get('total_defense', 0):,}",
                )
            )
    send(
        chat_id,
        T(
            "alliance.view",
            name=al.get("name"),
            owner=player_name(al.get("owner")),
            mode=alliance_mode_text(al),
            count=len(al.get("members", [])),
            max_members=ALLIANCE_MAX,
            members="\n".join(lines),
            vault=al.get("vault", 0),
            shared=al.get("total_shared", 0),
            cartel_level=cartel_level(al),
            cartel_label=cartel_level_data(al).get("label"),
            perks=cartel_perks_text(al),
            next_cost=cartel_next_upgrade_cost(al) or T("alliance.max_level"),
        ),
        keypad=alliance_keypad(chat_id),
    )


def handle_create_alliance_prompt(chat_id: str) -> None:
    p = get_player(chat_id)
    if p.get("alliance"):
        send(chat_id, T("alliance.already_member"), keypad=alliance_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_alliance_name"}
    save_game()
    send(chat_id, T("alliance.create_prompt"), keypad=make_keypad([[B("main_menu")]]))


def handle_create_alliance(chat_id: str, text: str) -> None:
    p = get_player(chat_id)
    name = clean_name(text, 24)
    if not name:
        send(chat_id, T("alliance.bad_name"), keypad=make_keypad([[B("main_menu")]]))
        return
    if name in game["alliances"]:
        send(chat_id, T("alliance.exists"), keypad=alliance_keypad(chat_id))
        return
    if p.get("alliance"):
        send(chat_id, T("alliance.already_member"), keypad=alliance_keypad(chat_id))
        return
    game["alliances"][name] = {
        "name": name,
        "owner": chat_id,
        "members": [chat_id],
        "open": True,
        "applicants": [],
        "vault": 0,
        "total_shared": 0,
        "level": 1,
        "created_at": iso(now()),
        "log": [],
    }
    p["alliance"] = name
    game["chat_states"].pop(chat_id, None)
    log_action(chat_id, "alliance_create", {"name": name})
    save_game()
    send(chat_id, T("alliance.created", name=name), keypad=alliance_keypad(chat_id))


def handle_list_alliances(chat_id: str) -> None:
    if not game["alliances"]:
        send(chat_id, T("alliance.list_empty"), keypad=alliance_keypad(chat_id))
        return
    lines, rows = [], []
    for name, al in list(game["alliances"].items())[:12]:
        lines.append(
            T(
                "alliance.list_line",
                status=alliance_mode_text(al),
                name=name,
                count=len(al.get("members", [])),
                max_members=ALLIANCE_MAX,
                owner=player_name(al.get("owner")),
            )
        )
        rows.append([T("alliance.join_button", name=name)])
    rows.append([B("main_menu")])
    send(chat_id, T("alliance.list", lines="\n".join(lines)), keypad=make_keypad(rows))


def handle_join_alliance(chat_id: str, text: str) -> None:
    p = get_player(chat_id)
    if p.get("alliance"):
        send(chat_id, T("alliance.already_member"), keypad=alliance_keypad(chat_id))
        return
    name = text.split(":", 1)[1].strip() if ":" in text else text.strip()
    al = game["alliances"].get(name)
    if not al:
        send(chat_id, T("market.order_not_found"), keypad=alliance_keypad(chat_id))
        return
    if len(al.get("members", [])) >= ALLIANCE_MAX:
        send(chat_id, T("alliance.full"), keypad=alliance_keypad(chat_id))
        return
    if al.get("open"):
        al["members"].append(chat_id)
        p["alliance"] = name
        log_action(chat_id, "alliance_join", {"name": name})
        save_game()
        send(chat_id, T("alliance.joined", name=name), keypad=alliance_keypad(chat_id))
    else:
        if chat_id not in al.setdefault("applicants", []):
            al["applicants"].append(chat_id)
        save_game()
        send(
            chat_id, T("alliance.requested", name=name), keypad=alliance_keypad(chat_id)
        )
        if al.get("owner") in game["players"]:
            send(
                al["owner"],
                T("alliance.request_notice", alliance=name, player=p.get("name")),
                keypad=alliance_keypad(al["owner"]),
            )


def handle_leave_alliance(chat_id: str) -> None:
    p = get_player(chat_id)
    al = player_alliance(chat_id)
    if not al:
        handle_alliance_menu(chat_id)
        return
    if al.get("owner") == chat_id and len(al.get("members", [])) > 1:
        send(chat_id, T("alliance.owner_cant_leave"), keypad=alliance_keypad(chat_id))
        return
    name = al.get("name")
    if chat_id in al.get("members", []):
        al["members"].remove(chat_id)
    p["alliance"] = None
    if not al.get("members"):
        game["alliances"].pop(name, None)
    log_action(chat_id, "alliance_leave", {"name": name})
    save_game()
    send(chat_id, T("alliance.left", name=name), keypad=main_keypad(chat_id))


def handle_alliance_manage(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    send(
        chat_id,
        T(
            "alliance.manage",
            name=al.get("name"),
            mode=alliance_mode_text(al),
            applicants=len(al.get("applicants", [])),
            count=len(al.get("members", [])),
            max_members=ALLIANCE_MAX,
            vault=al.get("vault", 0),
            cartel_level=cartel_level(al),
            cartel_label=cartel_level_data(al).get("label"),
            next_cost=cartel_next_upgrade_cost(al) or T("alliance.max_level"),
        ),
        keypad=make_keypad(
            [
                [B("alliance_open_toggle"), B("alliance_applicants")],
                [B("alliance_kick"), B("alliance_vault")],
                [B("alliance_upgrade"), B("alliance_group_raid")],
                [B("alliance"), B("main_menu")],
            ]
        ),
    )


def handle_toggle_alliance(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    al["open"] = not bool(al.get("open"))
    save_game()
    send(
        chat_id,
        T("alliance.mode_changed", mode=alliance_mode_text(al)),
        keypad=alliance_keypad(chat_id),
    )


def handle_alliance_upgrade(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    lv = cartel_level(al)
    if lv >= MAX_CARTEL_LEVEL:
        send(chat_id, T("alliance.upgrade_max"), keypad=alliance_keypad(chat_id))
        return
    cost = cartel_next_upgrade_cost(al)
    vault = int(al.get("vault", 0))
    if vault < cost:
        send(
            chat_id,
            T("alliance.upgrade_not_enough", need=cost, have=vault),
            keypad=alliance_keypad(chat_id),
        )
        return
    al["vault"] = vault - cost
    al["level"] = lv + 1
    alliance_log(
        al, "cartel_upgrade", {"from_level": lv, "to_level": lv + 1, "cost": cost}
    )
    save_game()
    msg = T(
        "alliance.upgraded",
        level=al["level"],
        label=cartel_level_data(al).get("label"),
        cost=cost,
        perks=cartel_perks_text(al),
    )
    for cid in al.get("members", []):
        if cid in game["players"]:
            send(cid, msg, keypad=main_keypad(cid))


def handle_applicants(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    apps = [cid for cid in al.get("applicants", []) if cid in game["players"]]
    if not apps:
        send(chat_id, T("alliance.applicants_empty"), keypad=alliance_keypad(chat_id))
        return
    lines = [f"- {player_name(cid)}" for cid in apps]
    rows = []
    for cid in apps[:6]:
        rows.append([f"قبول: {player_name(cid)}", f"رد: {player_name(cid)}"])
    rows.append([B("alliance_manage"), B("main_menu")])
    send(
        chat_id,
        T("alliance.applicants", lines="\n".join(lines)),
        keypad=make_keypad(rows),
    )


def handle_applicant_decision(chat_id: str, text: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    accept = text.startswith("قبول:")
    name = text.split(":", 1)[1].strip()
    target = find_player_by_name(name, al.get("applicants", []))
    if not target:
        send(chat_id, T("alliance.kick_not_found"), keypad=alliance_keypad(chat_id))
        return
    al["applicants"].remove(target)
    if accept:
        if len(al.get("members", [])) >= ALLIANCE_MAX:
            send(chat_id, T("alliance.full"), keypad=alliance_keypad(chat_id))
            return
        al["members"].append(target)
        game["players"][target]["alliance"] = al["name"]
        save_game()
        send(
            chat_id,
            T("alliance.approved", player=player_name(target)),
            keypad=alliance_keypad(chat_id),
        )
        send(target, T("alliance.joined", name=al["name"]), keypad=main_keypad(target))
    else:
        save_game()
        send(
            chat_id,
            T("alliance.rejected", player=player_name(target)),
            keypad=alliance_keypad(chat_id),
        )


def handle_kick_prompt(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    members = [cid for cid in al.get("members", []) if cid != chat_id]
    game["chat_states"][chat_id] = {"state": "awaiting_kick_member"}
    save_game()
    send(
        chat_id,
        T(
            "alliance.kick_prompt",
            members="\n".join(f"- {player_name(cid)}" for cid in members)
            or "عضوی نداری",
        ),
        keypad=make_keypad([[B("alliance_manage"), B("main_menu")]]),
    )


def handle_kick_member(chat_id: str, text: str) -> None:
    al = player_alliance(chat_id)
    if not al or al.get("owner") != chat_id:
        send(chat_id, T("alliance.not_owner"), keypad=alliance_keypad(chat_id))
        return
    members = [cid for cid in al.get("members", []) if cid != chat_id]
    target = find_player_by_name(text, members)
    if not target:
        send(chat_id, T("alliance.kick_not_found"), keypad=alliance_keypad(chat_id))
        return
    al["members"].remove(target)
    game["players"][target]["alliance"] = None
    game["chat_states"].pop(chat_id, None)
    save_game()
    send(
        chat_id,
        T("alliance.kicked", player=player_name(target)),
        keypad=alliance_keypad(chat_id),
    )
    send(
        target,
        T("alliance.kicked_notice", alliance=al["name"]),
        keypad=main_keypad(target),
    )


# ══════════════════════════════════════════════════════
#  HANDLERS: INVENTORY / DAILY / INVITE / SEASON / LEADERBOARD / HELP
# ══════════════════════════════════════════════════════
def handle_inventory(chat_id: str) -> None:
    p = get_player(chat_id)
    items = []
    for k, qty in p.get("inventory", {}).items():
        if qty > 0 and k in CRAFT_ITEMS:
            items.append(f"{CRAFT_ITEMS[k]['label']} × {qty}")
        elif qty > 0 and k in LEGENDARY_ITEMS:
            items.append(f"✨ {LEGENDARY_ITEMS[k]['label']} × {qty}")
    if int(p.get("loot_caches", 0)) > 0:
        items.append(f"🎁 صندوق شانسی × {p.get('loot_caches', 0)}")
    send(
        chat_id,
        T(
            "inventory.text",
            items="\n".join(items) or T("inventory.empty"),
            scrap=p["resources"].get("scrap", 0),
            plastic=p["resources"].get("plastic", 0),
            glass=p["resources"].get("glass", 0),
            battery=p["resources"].get("battery", 0),
            copper=p["resources"].get("copper", 0),
            water=p.get("water", 0),
        ),
        keypad=main_keypad(chat_id),
    )


def handle_daily(chat_id: str) -> None:
    p = get_player(chat_id)
    if p.get("daily_last") == today_key():
        tomorrow = (now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        send(
            chat_id,
            T("daily.already", time=fmt_cd((tomorrow - now()).total_seconds())),
            keypad=main_keypad(chat_id),
        )
        return
    yesterday = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
    p["daily_streak"] = (
        int(p.get("daily_streak", 0)) + 1 if p.get("daily_last") == yesterday else 1
    )
    p["daily_last"] = today_key()
    streak = p["daily_streak"]
    water = 60 + min(200, streak * 10)
    scrap = 10 + min(50, streak * 2)
    plastic = 8 + min(40, streak * 2)
    battery = 1 if streak % 3 == 0 else 0
    p["water"] += water
    p["resources"]["scrap"] += scrap
    p["resources"]["plastic"] += plastic
    p["resources"]["battery"] += battery
    reward = fmt_res_dict(
        {
            "water": water,
            "scrap": scrap,
            "plastic": plastic,
            **({"battery": battery} if battery else {}),
        }
    )
    log_action(chat_id, "daily", {"reward": reward, "streak": streak})
    save_game()
    send(
        chat_id,
        T("daily.claimed", reward=reward, streak=streak),
        keypad=main_keypad(chat_id),
    )


def handle_invite(chat_id: str) -> None:
    p = get_player(chat_id)
    send(
        chat_id,
        T("invite.text", code=p.get("ref_code")),
        keypad=make_keypad([[B("enter_referral")], [B("main_menu")]]),
    )


def handle_enter_referral(chat_id: str) -> None:
    p = get_player(chat_id)
    if p.get("referral_used"):
        send(chat_id, T("invite.already"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_referral_code"}
    save_game()
    send(chat_id, T("invite.prompt"), keypad=make_keypad([[B("main_menu")]]))


def handle_referral_code(chat_id: str, text: str) -> None:
    ok = apply_referral(chat_id, text)
    game["chat_states"].pop(chat_id, None)
    save_game()
    if ok:
        inviter_id = game["players"][chat_id].get("referred_by")
        send(
            chat_id,
            T("invite.used", inviter=player_name(inviter_id)),
            keypad=main_keypad(chat_id),
        )
    else:
        send(chat_id, T("invite.bad"), keypad=main_keypad(chat_id))


def handle_season(chat_id: str) -> None:
    rows = ranked_players()
    rank = next((i for i, (cid, _) in enumerate(rows, start=1) if cid == chat_id), "—")
    s = game.get("season", default_season(1))
    br = season_score_breakdown(chat_id)
    send(
        chat_id,
        T(
            "season.text",
            id=s.get("id", 1),
            start=fmt_dt(s.get("start")),
            end=fmt_dt(s.get("end")),
            left=season_left_text(),
            score=br["total"],
            rank=rank,
            combat_score=br["combat"],
            eco_score=br["economy"],
            progress_score=br["progress"],
        ),
        keypad=main_keypad(chat_id),
    )


def leaderboard_personal_note(chat_id: str, rows: list[tuple[str, int]]) -> str:
    total_players = len(rows)

    my_rank = None
    my_score = None

    for i, (cid, score) in enumerate(rows, start=1):
        if cid == chat_id:
            my_rank = i
            my_score = score
            break

    if not my_rank:
        return T("leaderboard.no_rank", total=total_players)

    if my_rank <= 10:
        return T(
            "leaderboard.in_top",
            rank=my_rank,
            total=total_players,
            score=my_score,
        )

    roasts = T("leaderboard.roasts")
    if isinstance(roasts, list):
        roast = random.choice(roasts)
    else:
        roast = str(roasts)

    return T(
        "leaderboard.out_of_top",
        rank=my_rank,
        total=total_players,
        score=my_score,
        roast=roast,
    )


def previous_season_champion() -> Optional[dict[str, Any]]:
    archives = game.get("season", {}).get("archives", [])
    if not archives:
        return None
    last = archives[-1]
    winners = last.get("winners", [])
    if not winners:
        return None
    champ = winners[0]  # رتبه ۱ فصل قبل
    return {
        "chat_id": champ.get("chat_id"),
        "name": champ.get("name"),
        "score": champ.get("score"),
        "season_id": last.get("id"),
    }


def handle_leaderboard(chat_id: str) -> None:
    rows = ranked_players()
    medals = ["🥇", "🥈", "🥉"]
    champ = previous_season_champion()
    champ_id = champ.get("chat_id") if champ else None

    lines = []
    for i, (cid, score) in enumerate(rows[:10]):
        p = game["players"][cid]
        recalc_power(p)
        crown = " 👑 قهرمان فصل قبل" if champ_id and cid == champ_id else ""
        lines.append(
            T(
                "leaderboard.line",
                medal=medals[i] if i < 3 else f"{i + 1}.",
                name=display_name(p.get("name")) + crown,
                level=p.get("level", 1),
                score=score,
                water=p.get("water", 0),
                attack=f"{p.get('total_attack', 0):,}",
                defense=f"{p.get('total_defense', 0):,}",
                power=f"{p.get('total_attack', 0) + p.get('total_defense', 0):,}",
                me=T("leaderboard.me") if cid == chat_id else "",
            )
        )

    hof_line = ""
    if champ:
        hof_line = (
            f"🏛️ تالار مشاهیر\n"
            f"👑 قهرمان فصل {champ['season_id']}: {display_name(champ['name'])} "
            f"— {fmt_num(champ['score'])} امتیاز\n"
            f"این لقب تا پایان همین فصل روی اسمش می‌مونه.\n\n"
        )

    note = leaderboard_personal_note(chat_id, rows)
    send(
        chat_id,
        hof_line
        + T("leaderboard.text", lines="\n".join(lines) or "هنوز کسی نیست.", note=note),
        keypad=main_keypad(chat_id),
    )


# ══════════════════════════════════════════════════════
#  HANDLERS: PLAYER MESSAGES
# ══════════════════════════════════════════════════════
def private_message_keypad() -> dict[str, Any]:
    return make_keypad([[B("messages_send")], [B("main_menu")]])


def private_message_story() -> str:
    stories = T("messages.stories")
    if isinstance(stories, str):
        return stories
    return random.choice(stories or ["یک پیک ناشناس از دل خرابه‌ها پیام را رساند."])


def message_preview(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def handle_messages_menu(chat_id: str) -> None:
    inbox = [m for m in game.get("private_messages", []) if m.get("to") == chat_id][-5:]
    if not inbox:
        body = T("messages.inbox_empty")
    else:
        lines = []
        for m in reversed(inbox):
            lines.append(
                T(
                    "messages.inbox_line",
                    id=m.get("id"),
                    sender=player_name(m.get("from", "")),
                    time=fmt_dt(m.get("at")),
                    preview=message_preview(m.get("text", "")),
                )
            )
        body = T("messages.inbox", lines="\n".join(lines))
    send(chat_id, body, keypad=private_message_keypad())


def handle_private_message_target_prompt(chat_id: str) -> None:
    game["chat_states"][chat_id] = {"state": "awaiting_private_message_target"}
    save_game()
    send(chat_id, T("messages.target_prompt"), keypad=make_keypad([[B("main_menu")]]))


def handle_private_message_target(chat_id: str, text: str) -> None:
    target = find_player_by_name(text)
    if not target or not game["players"].get(target, {}).get("registered"):
        send(chat_id, T("messages.target_not_found"), keypad=private_message_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    if target == chat_id:
        send(chat_id, T("messages.cannot_self"), keypad=private_message_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    game["chat_states"][chat_id] = {
        "state": "awaiting_private_message_body",
        "target": target,
    }
    save_game()
    send(
        chat_id,
        T("messages.body_prompt", target=player_name(target)),
        keypad=make_keypad([[B("main_menu")]]),
    )


def handle_private_message_body(chat_id: str, text: str) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    if not target or target not in game.get("players", {}):
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        send(chat_id, T("messages.target_not_found"), keypad=private_message_keypad())
        return
    body = (text or "").strip()
    if len(body) < 2:
        send(
            chat_id,
            T("messages.body_too_short"),
            keypad=make_keypad([[B("main_menu")]]),
        )
        return
    body = body[:700]
    mid = int(game.get("next_private_message_id", 1))
    game["next_private_message_id"] = mid + 1
    story = private_message_story()
    record = {
        "id": mid,
        "from": chat_id,
        "to": target,
        "text": body,
        "story": story,
        "at": iso(now()),
    }
    game.setdefault("private_messages", []).append(record)
    game["private_messages"] = game["private_messages"][-MAX_PRIVATE_MESSAGES:]
    game.get("chat_states", {}).pop(chat_id, None)
    log_action(chat_id, "private_message_sent", {"to": target, "message_id": mid})
    log_action(target, "private_message_received", {"from": chat_id, "message_id": mid})
    save_game()
    send(
        target,
        T(
            "messages.delivered_to_target",
            sender=player_name(chat_id),
            story=story,
            message=body,
        ),
        keypad=main_keypad(target),
    )
    send(
        chat_id,
        T("messages.sent", target=player_name(target), id=mid),
        keypad=private_message_keypad(),
    )


# ══════════════════════════════════════════════════════
#  HANDLERS: ADMIN
# ══════════════════════════════════════════════════════
def admin_keypad() -> dict[str, Any]:
    return make_keypad(
        [
            [B("admin_broadcast"), B("admin_stats")],
            [B("admin_messages"), B("admin_players")],
            [B("admin_rename_player"), B("admin_rename_alliance")],
            [B("admin_ban_player"), B("admin_unban_player")],
            [B("admin_penalty_player")],
            [B("admin_alliances"), B("admin_market")],
            [B("main_menu")],
        ]
    )


def admin_cancel_keypad() -> dict[str, Any]:
    return make_keypad([[B("admin_panel"), B("main_menu")]])


def handle_admin_panel(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    send(chat_id, T("admin.panel"), keypad=admin_keypad())


def migrate_player_building_bonuses(chat_id: str) -> None:
    """یک بار برای همه بازیکن‌ها بونوس ساختمان‌های قدیمی رو اعمال کن"""
    p = get_player(chat_id)
    apply_building_bonuses(p)


def handle_admin_stats(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    rows = ranked_players()
    top_player = "—"
    top_score = 0
    if rows:
        top_player = display_name(player_name(rows[0][0]))
        top_score = rows[0][1]
    send(
        chat_id,
        T(
            "admin.stats",
            players=sum(
                1 for p in game.get("players", {}).values() if p.get("registered")
            ),
            alliances=len(game.get("alliances", {})),
            orders=len(open_orders()),
            season_id=game.get("season", {}).get("id", 1),
            top_player=top_player,
            top_score=top_score,
            messages=len(game.get("private_messages", [])),
            market_supply=sum(int(v) for v in game.get("market_supply", {}).values()),
            vault_total=sum(
                int(al.get("vault", 0)) for al in game.get("alliances", {}).values()
            ),
        ),
        keypad=admin_keypad(),
    )


def handle_admin_messages(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    rows = game.get("private_messages", [])[-12:]
    if not rows:
        send(chat_id, T("admin.messages_empty"), keypad=admin_keypad())
        return
    lines = []
    for m in reversed(rows):
        lines.append(
            T(
                "admin.message_line",
                id=m.get("id"),
                time=fmt_dt(m.get("at")),
                sender=player_name(m.get("from", "")),
                target=player_name(m.get("to", "")),
                text=message_preview(m.get("text", ""), 160),
            )
        )
    send(chat_id, T("admin.messages", lines="\n".join(lines)), keypad=admin_keypad())


def admin_players_page_button(page: int) -> str:
    return T("admin.players_page_button", page=page)


def admin_players_keypad(page: int, pages: int) -> dict[str, Any]:
    rows: list[list[str]] = []
    nav: list[str] = []
    if page > 1:
        nav.append(admin_players_page_button(page - 1))
    if page < pages:
        nav.append(admin_players_page_button(page + 1))
    if nav:
        rows.append(nav)
    rows.append([B("admin_panel")])
    rows.append([B("main_menu")])
    return make_keypad(rows)


def parse_admin_players_page(text: str) -> Optional[int]:
    m = re.match(r"^👥 بازیکن‌ها صفحه (\d+)$", text.strip())
    if not m:
        return None
    try:
        return max(1, int(m.group(1)))
    except Exception:
        return None


def handle_admin_players(chat_id: str, page: int = 1, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    ranked = ranked_players(include_banned=True)
    total = len(ranked)
    pages = max(1, (total + ADMIN_PLAYERS_PAGE_SIZE - 1) // ADMIN_PLAYERS_PAGE_SIZE)
    page = min(max(1, page), pages)
    start = (page - 1) * ADMIN_PLAYERS_PAGE_SIZE
    rows = []
    for idx, (cid, score) in enumerate(
        ranked[start : start + ADMIN_PLAYERS_PAGE_SIZE], start=start + 1
    ):
        p = game.get("players", {}).get(cid, {})
        rows.append(
            T(
                "admin.player_line",
                rank=idx,
                name=player_name(cid),
                level=fmt_num(p.get("level", 1)),
                water=fmt_num(p.get("water", 0)),
                alliance=p.get("alliance") or "—",
                score=fmt_num(score),
                status=T("admin.player_status_banned")
                if p.get("banned")
                else T("admin.player_status_active"),
            )
        )
    send(
        chat_id,
        T(
            "admin.players",
            page=page,
            pages=pages,
            total=fmt_num(total),
            from_rank=fmt_num(start + 1 if total else 0),
            to_rank=fmt_num(min(start + ADMIN_PLAYERS_PAGE_SIZE, total)),
            lines="\n\n".join(rows) or "—",
        ),
        keypad=admin_players_keypad(page, pages),
    )


def handle_admin_alliances(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    lines = []
    for name, al in sorted(
        game.get("alliances", {}).items(),
        key=lambda x: int(x[1].get("vault", 0)),
        reverse=True,
    )[:15]:
        lines.append(
            T(
                "admin.alliance_line",
                name=name,
                owner=player_name(al.get("owner")),
                count=len(al.get("members", [])),
                vault=al.get("vault", 0),
                level=cartel_level(al),
                label=cartel_level_data(al).get("label"),
            )
        )
    send(
        chat_id,
        T("admin.alliances", lines="\n".join(lines) or "—"),
        keypad=admin_keypad(),
    )


def handle_admin_market(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    supply_lines = []
    for r in RESOURCES:
        supply_lines.append(
            T(
                "admin.market_supply_line",
                icon=RES_ICON[r],
                name=RES_NAME[r],
                qty=int(game.get("market_supply", {}).get(r, 0)),
                buy=system_reference_price(r),
                sell=system_buy_price(r),
            )
        )
    send(
        chat_id,
        T("admin.market", orders=len(open_orders()), supply="\n".join(supply_lines)),
        keypad=admin_keypad(),
    )


def handle_admin_broadcast_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_broadcast"}
    save_game()
    send(chat_id, T("admin.broadcast_prompt"), keypad=make_keypad([[B("main_menu")]]))


def handle_admin_broadcast(chat_id: str, text: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    count = 0
    for cid, player in list(game.get("players", {}).items()):
        if cid == chat_id or not player.get("registered") or player.get("banned"):
            continue
        send(cid, T("admin.broadcast_header", message=text), keypad=main_keypad(cid))
        count += 1
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    send(chat_id, T("admin.broadcast_done", count=count), keypad=admin_keypad())


def player_name_exists(name: str, exclude: Optional[str] = None) -> bool:
    norm = (name or "").strip().lower()
    for cid, p in game.get("players", {}).items():
        if exclude is not None and cid == exclude:
            continue
        if p.get("name", "").strip().lower() == norm:
            return True
    return False


def find_alliance_by_name(name: str) -> Optional[str]:
    norm = (name or "").strip().lower()
    if not norm:
        return None
    for aname in game.get("alliances", {}).keys():
        if aname.strip().lower() == norm:
            return aname
    for aname in game.get("alliances", {}).keys():
        if norm in aname.strip().lower():
            return aname
    return None


def handle_admin_rename_player_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_rename_player_target"}
    save_game()
    send(chat_id, T("admin.rename_player_target_prompt"), keypad=admin_cancel_keypad())


def handle_admin_rename_player_target(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    target = find_player_by_name(text)
    if not target or not game.get("players", {}).get(target, {}).get("registered"):
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_player_name",
        "target": target,
    }
    save_game()
    send(
        chat_id,
        T("admin.rename_player_name_prompt", player=player_name(target)),
        keypad=admin_cancel_keypad(),
    )


def handle_admin_rename_player_name(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    p = game.get("players", {}).get(target or "")
    new_name = clean_name(text, 24)
    if not target or not p:
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    if not new_name:
        send(chat_id, T("admin.bad_name"), keypad=admin_cancel_keypad())
        return
    if player_name_exists(new_name, exclude=target):
        send(chat_id, T("admin.name_taken"), keypad=admin_cancel_keypad())
        return
    old_name = p.get("name") or player_name(target)
    p["name"] = new_name
    log_action(
        target,
        "admin_rename_player",
        {"old": old_name, "new": new_name, "admin": chat_id},
    )
    admin_audit(
        chat_id, "rename_player", {"target": target, "old": old_name, "new": new_name}
    )
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    send(
        target,
        T("admin.rename_player_notice", old=old_name, new=new_name),
        keypad=main_keypad(target),
    )
    send(
        chat_id,
        T("admin.rename_player_done", old=old_name, new=new_name),
        keypad=admin_keypad(),
    )


def handle_admin_rename_alliance_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_rename_alliance_target"}
    save_game()
    send(
        chat_id, T("admin.rename_alliance_target_prompt"), keypad=admin_cancel_keypad()
    )


def handle_admin_rename_alliance_target(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    old_name = find_alliance_by_name(text)
    if not old_name:
        send(chat_id, T("admin.alliance_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    game["chat_states"][chat_id] = {
        "state": "awaiting_admin_rename_alliance_name",
        "old_name": old_name,
    }
    save_game()
    send(
        chat_id,
        T("admin.rename_alliance_name_prompt", alliance=old_name),
        keypad=admin_cancel_keypad(),
    )


def handle_admin_rename_alliance_name(
    chat_id: str, text: str, sender_id: str = ""
) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    old_name = st.get("old_name")
    new_name = clean_name(text, 24)
    if not old_name or old_name not in game.get("alliances", {}):
        send(chat_id, T("admin.alliance_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    if not new_name:
        send(chat_id, T("admin.bad_name"), keypad=admin_cancel_keypad())
        return
    if new_name in game.get("alliances", {}) and new_name != old_name:
        send(chat_id, T("admin.alliance_name_taken"), keypad=admin_cancel_keypad())
        return
    al = game["alliances"].pop(old_name)
    al["name"] = new_name
    alliance_log(
        al,
        "admin_rename_alliance",
        {"old": old_name, "new": new_name, "admin": chat_id},
    )
    game["alliances"][new_name] = al
    for p in game.get("players", {}).values():
        if p.get("alliance") == old_name:
            p["alliance"] = new_name
    admin_audit(chat_id, "rename_alliance", {"old": old_name, "new": new_name})
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    for member in al.get("members", []):
        if member in game.get("players", {}):
            send(
                member,
                T("admin.rename_alliance_notice", old=old_name, new=new_name),
                keypad=main_keypad(member),
            )
    send(
        chat_id,
        T(
            "admin.rename_alliance_done",
            old=old_name,
            new=new_name,
            count=len(al.get("members", [])),
        ),
        keypad=admin_keypad(),
    )


def handle_admin_ban_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_ban_target"}
    save_game()
    send(chat_id, T("admin.ban_target_prompt"), keypad=admin_cancel_keypad())


def handle_admin_ban_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = find_player_by_name(text)
    if not target or not game.get("players", {}).get(target, {}).get("registered"):
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    game["chat_states"][chat_id] = {
        "state": "awaiting_admin_ban_reason",
        "target": target,
    }
    save_game()
    send(
        chat_id,
        T("admin.ban_reason_prompt", player=player_name(target)),
        keypad=admin_cancel_keypad(),
    )


def handle_admin_ban_reason(chat_id: str, text: str, sender_id: str = "") -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    p = game.get("players", {}).get(target or "")
    if not target or not p:
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    reason = message_preview(text or "بدون دلیل ثبت‌شده", 180)
    p["banned"] = True
    p["ban_reason"] = reason
    p["banned_at"] = iso(now())
    p["banned_by"] = chat_id
    log_action(target, "admin_ban", {"admin": chat_id, "reason": reason})
    admin_audit(chat_id, "ban_player", {"target": target, "reason": reason})
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    send(
        target,
        T("admin.ban_notice_to_player", reason=reason),
        keypad=make_keypad([[B("help")]]),
    )
    send(
        chat_id,
        T("admin.ban_done", player=player_name(target), reason=reason),
        keypad=admin_keypad(),
    )


def handle_admin_unban_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_unban_target"}
    save_game()
    send(chat_id, T("admin.unban_target_prompt"), keypad=admin_cancel_keypad())


def handle_admin_unban_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = find_player_by_name(text)
    if not target or not game.get("players", {}).get(target, {}).get("registered"):
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    p = game["players"][target]
    p["banned"] = False
    p["ban_reason"] = ""
    p["banned_at"] = None
    p["banned_by"] = None
    log_action(target, "admin_unban", {"admin": chat_id})
    admin_audit(chat_id, "unban_player", {"target": target})
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    send(target, T("admin.unban_notice_to_player"), keypad=main_keypad(target))
    send(
        chat_id,
        T("admin.unban_done", player=player_name(target)),
        keypad=admin_keypad(),
    )


PENALTY_ALIASES = {
    "water": "water",
    "آب": "water",
    "scrap": "scrap",
    "اوراق": "scrap",
    "آهن": "scrap",
    "اهن": "scrap",
    "plastic": "plastic",
    "پلاستیک": "plastic",
    "glass": "glass",
    "شیشه": "glass",
    "شيشه": "glass",
    "battery": "battery",
    "باتری": "battery",
    "باطری": "battery",
    "copper": "copper",
    "مس": "copper",
    "xp": "xp",
    "تجربه": "xp",
    "score": "score",
    "points": "score",
    "امتیاز": "score",
    "رتبه": "score",
    "honor": "honor",
    "افتخار": "honor",
    "hp": "hp",
    "جان": "hp",
}


def parse_admin_penalty(text: str) -> tuple[dict[str, int], str]:
    raw = (text or "").strip()
    reason = "بدون دلیل ثبت‌شده"
    m = re.search(r"(?:^|\s)(?:دلیل|reason)\s*[=:]\s*(.+)$", raw, re.IGNORECASE)
    if m:
        reason = message_preview(m.group(1), 180)
        raw = raw[: m.start()].strip()
    items: dict[str, int] = {}
    for key, amount in re.findall(r"([A-Za-z_آ-یي]+)\s*[=:]\s*(-?\d+)", raw):
        mapped = PENALTY_ALIASES.get(key.strip()) or PENALTY_ALIASES.get(
            key.strip().lower()
        )
        if not mapped:
            continue
        value = abs(int(amount))
        if value <= 0:
            continue
        items[mapped] = items.get(mapped, 0) + value
    return items, reason


def apply_admin_penalty(target: str, penalties: dict[str, int]) -> list[str]:
    p = game["players"][target]
    lines: list[str] = []
    for key, amount in penalties.items():
        if key == "water":
            before = int(p.get("water", 0))
            taken = min(before, amount)
            p["water"] = before - taken
            lines.append(
                T(
                    "admin.penalty_change_line",
                    label="💧 آب",
                    amount=fmt_num(taken),
                    now=fmt_num(p["water"]),
                )
            )
        elif key in RESOURCES:
            before = int(p.get("resources", {}).get(key, 0))
            taken = min(before, amount)
            p.setdefault("resources", {})[key] = before - taken
            lines.append(
                T(
                    "admin.penalty_change_line",
                    label=f"{RES_ICON[key]} {RES_NAME[key]}",
                    amount=fmt_num(taken),
                    now=fmt_num(p["resources"][key]),
                )
            )
        elif key == "xp":
            before = int(p.get("xp", 0))
            taken = min(before, amount)
            p["xp"] = before - taken
            lines.append(
                T(
                    "admin.penalty_change_line",
                    label="⭐ تجربه",
                    amount=fmt_num(taken),
                    now=fmt_num(p["xp"]),
                )
            )
        elif key == "score":
            p["season_points_bonus"] = int(p.get("season_points_bonus", 0)) - amount
            lines.append(
                T(
                    "admin.penalty_score_line",
                    amount=fmt_num(amount),
                    now=fmt_num(season_score(target)),
                )
            )
        elif key == "honor":
            p["honor"] = int(p.get("honor", 0)) - amount
            lines.append(
                T(
                    "admin.penalty_change_line",
                    label="🎖️ افتخار",
                    amount=fmt_num(amount),
                    now=fmt_num(p["honor"]),
                )
            )
        elif key == "hp":
            before = int(p.get("hp", 100))
            taken = min(before, amount)
            p["hp"] = max(0, before - taken)
            lines.append(
                T(
                    "admin.penalty_change_line",
                    label="❤️ جان",
                    amount=fmt_num(taken),
                    now=fmt_num(p["hp"]),
                )
            )
    return lines


def handle_admin_penalty_prompt(chat_id: str, sender_id: str = "") -> None:
    if not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return
    game["chat_states"][chat_id] = {"state": "awaiting_admin_penalty_target"}
    save_game()
    send(chat_id, T("admin.penalty_target_prompt"), keypad=admin_cancel_keypad())


def handle_admin_penalty_target(chat_id: str, text: str, sender_id: str = "") -> None:
    target = find_player_by_name(text)
    if not target or not game.get("players", {}).get(target, {}).get("registered"):
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    game["chat_states"][chat_id] = {
        "state": "awaiting_admin_penalty_details",
        "target": target,
    }
    save_game()
    send(
        chat_id,
        T("admin.penalty_details_prompt", player=player_name(target)),
        keypad=admin_cancel_keypad(),
    )


def handle_admin_penalty_details(chat_id: str, text: str, sender_id: str = "") -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    target = st.get("target")
    if not target or target not in game.get("players", {}):
        send(chat_id, T("admin.player_not_found"), keypad=admin_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        save_game()
        return
    penalties, reason = parse_admin_penalty(text)
    if not penalties:
        send(chat_id, T("admin.penalty_bad_format"), keypad=admin_cancel_keypad())
        return
    before_score = season_score(target)
    lines = apply_admin_penalty(target, penalties)
    after_score = season_score(target)
    p = game["players"][target]
    note = {
        "admin": chat_id,
        "penalties": penalties,
        "reason": reason,
        "before_score": before_score,
        "after_score": after_score,
    }
    p.setdefault("admin_notes", []).append({"at": iso(now()), **note})
    p["admin_notes"] = p["admin_notes"][-30:]
    log_action(target, "admin_penalty", note)
    admin_audit(chat_id, "penalty_player", {"target": target, **note})
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    send(
        target,
        T("admin.penalty_notice_to_player", reason=reason, lines="\n".join(lines)),
        keypad=main_keypad(target),
    )
    send(
        chat_id,
        T(
            "admin.penalty_done",
            player=player_name(target),
            before=fmt_num(before_score),
            after=fmt_num(after_score),
            reason=reason,
            lines="\n".join(lines),
        ),
        keypad=admin_keypad(),
    )


def handle_help(chat_id: str) -> None:
    ev = current_event()
    event_text = (
        T("world.current", title=ev["title"], effect_text=ev["effect_text"])
        if ev
        else T("world.none")
    )
    send(chat_id, T("help.text") + "\n\n" + event_text, keypad=main_keypad(chat_id))


# ══════════════════════════════════════════════════════
#  STATE HANDLER / DISPATCHER
# ══════════════════════════════════════════════════════
def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:
    st = game.get("chat_states", {}).get(chat_id)
    if not st:
        return False
    if text == B("main_menu"):
        game["chat_states"].pop(chat_id, None)
        save_game()
        handle_profile(chat_id)
        return True

    if text in ["/start", "شروع"]:
        game["chat_states"].pop(chat_id, None)
        save_game()
        handle_start(chat_id)
        return True
    if text == B("back_market"):
        game["chat_states"].pop(chat_id, None)
        save_game()
        handle_market_menu(chat_id)
        return True
    if text == B("alliance_manage"):
        game["chat_states"].pop(chat_id, None)
        save_game()
        handle_alliance_manage(chat_id)
        return True
    if text == B("admin_panel") and is_admin(chat_id, sender_id):
        game["chat_states"].pop(chat_id, None)
        save_game()
        handle_admin_panel(chat_id, sender_id)
        return True
    state = st.get("state")
    if str(state).startswith("awaiting_admin_") and not is_admin(chat_id, sender_id):
        send(chat_id, T("admin.not_allowed"), keypad=main_keypad(chat_id))
        return True
    if state == "awaiting_market_order":
        handle_create_order(chat_id, text)
        return True
    if state == "awaiting_barter_order":
        handle_create_barter(chat_id, text)
        return True
    if state == "awaiting_rental_order":
        handle_create_rental(chat_id, text)
        return True
    if state == "awaiting_system_sell_qty":
        handle_system_sell_qty(chat_id, text)
        return True
    if state == "awaiting_system_buy_qty":
        handle_system_buy_qty(chat_id, text)
        return True
    if state == "awaiting_alliance_name":
        handle_create_alliance(chat_id, text)
        return True
    if state == "awaiting_kick_member":
        handle_kick_member(chat_id, text)
        return True
    if state == "awaiting_referral_code":
        handle_referral_code(chat_id, text)
        return True
    if state == "awaiting_private_message_target":
        handle_private_message_target(chat_id, text)
        return True
    if state == "awaiting_private_message_body":
        handle_private_message_body(chat_id, text)
        return True
    if state == "awaiting_admin_broadcast":
        handle_admin_broadcast(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_player_target":
        handle_admin_rename_player_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_player_name":
        handle_admin_rename_player_name(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_alliance_target":
        handle_admin_rename_alliance_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_rename_alliance_name":
        handle_admin_rename_alliance_name(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_ban_target":
        handle_admin_ban_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_ban_reason":
        handle_admin_ban_reason(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_unban_target":
        handle_admin_unban_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_penalty_target":
        handle_admin_penalty_target(chat_id, text, sender_id)
        return True
    if state == "awaiting_admin_penalty_details":
        handle_admin_penalty_details(chat_id, text, sender_id)
        return True
    return False


def dispatch(
    chat_id: str,
    text: str,
    sender_name: str,
    button_id: str = "",
    sender_id: str = "",
) -> None:
    text = (text or button_id or "").strip()
    if not ensure_registered(chat_id, text, sender_name):
        return
    if is_banned(chat_id) and not is_admin(chat_id):
        send(
            chat_id,
            T("admin.banned_blocked", reason=ban_reason(chat_id)),
            keypad=make_keypad([[B("help")]]),
        )
        return
    expire_barter_orders()
    process_resource_rentals()
    if handle_state(chat_id, text, sender_id):
        return

    if text == B("main_menu"):
        return handle_profile(chat_id)

    if text in ["/start", "start", "شروع"]:
        return handle_start(chat_id, sender_name)
    if text == B("city_map"):
        return handle_city_map(chat_id)
    if text == B("world_boss"):
        return handle_world_boss(chat_id)
    if text == B("boss_attack"):
        return handle_boss_attack(chat_id)
    if text == B("news"):
        return handle_news(chat_id)
    if text == B("daily_missions"):
        return handle_daily_missions(chat_id)
    if text == B("open_cache"):
        return handle_open_cache(chat_id)
    if text == B("event"):
        return handle_event(chat_id)
    if text == B("messages"):
        return handle_messages_menu(chat_id)
    if text == B("messages_send"):
        return handle_private_message_target_prompt(chat_id)
    if text == B("profile"):
        return handle_profile(chat_id)
    if text == B("scavenge"):
        return handle_scavenge_menu(chat_id)
    if zone_by_label(text):
        return handle_scavenge(chat_id, zone_by_label(text) or "alley")
    if text == B("market") or text == B("back_market"):
        return handle_market_menu(chat_id)
    if text == B("market_people"):
        return handle_market_people(chat_id)
    if text == B("market_create_order"):
        return handle_create_order_prompt(chat_id)
    if text == B("market_my_orders"):
        return handle_my_orders(chat_id)
    if text == B("market_barter"):
        return handle_barter_menu(chat_id)
    if text == B("market_create_barter"):
        return handle_create_barter_prompt(chat_id)
    if text == B("market_my_barters"):
        return handle_my_barters(chat_id)
    if text == B("market_resource_rentals"):
        return handle_resource_rentals(chat_id)
    if text == B("rental_create"):
        return handle_create_rental_prompt(chat_id)
    if text == B("rental_my"):
        return handle_my_rentals(chat_id)
    if text == B("market_system_sell"):
        return handle_system_sell_menu(chat_id)
    if text == B("market_system_buy"):
        return handle_system_buy_menu(chat_id)
    if text == B("market_prices"):
        return handle_market_menu(chat_id)
    if text.startswith("قبول معاوضه"):
        return handle_accept_barter(chat_id, text)
    if text.startswith("لغو معاوضه"):
        return handle_cancel_barter(chat_id, text)
    if text.startswith("قبول قرارداد"):
        return handle_accept_rental(chat_id, text)
    if text.startswith("لغو قرارداد"):
        return handle_cancel_rental(chat_id, text)
    if text.startswith("خرید #"):
        return handle_buy_order(chat_id, text)
    if text.startswith("لغو #"):
        return handle_cancel_order(chat_id, text)
    if system_sell_resource_from_text(text):
        return handle_system_sell_select(
            chat_id, system_sell_resource_from_text(text) or "scrap"
        )
    if system_buy_resource_from_text(text):
        return handle_system_buy_select(
            chat_id, system_buy_resource_from_text(text) or "scrap"
        )
    if text == B("buildings"):
        return handle_buildings_menu(chat_id)
    if building_key_from_text(text):
        return handle_upgrade(chat_id, building_key_from_text(text) or "purifier")
    if text == B("craft"):
        return handle_craft_menu(chat_id)
    if craft_key_from_text(text):
        return handle_craft(chat_id, craft_key_from_text(text) or "shock_rifle")
    if text == B("attack"):
        return handle_attack_menu(chat_id)
    bucket = raid_bucket_from_text(text)
    if bucket:
        return handle_random_raid(chat_id, bucket)
    if text.startswith("حمله دقیق:") or text.startswith("حمله:"):
        target = raid_target_from_text(text)
        return (
            handle_raid(chat_id, target, precise=True)
            if target
            else send(
                chat_id, T("errors.target_not_found"), keypad=main_keypad(chat_id)
            )
        )
    if text == B("shield"):
        return handle_shield(chat_id)
    if text == B("shield_buy"):
        return handle_buy_shield(chat_id)
    if text == B("alliance"):
        return handle_alliance_menu(chat_id)
    if text == B("alliance_group_raid"):
        return handle_alliance_group_raid(chat_id)
    if text == B("alliance_group_ready"):
        return handle_alliance_group_ready(chat_id)
    if text == B("alliance_group_start"):
        return handle_alliance_group_start(chat_id)
    if text == B("alliance_group_cancel"):
        return handle_alliance_group_cancel(chat_id)
    if text == B("alliance_create"):
        return handle_create_alliance_prompt(chat_id)
    if text == B("alliance_list"):
        return handle_list_alliances(chat_id)
    if text.startswith("پیوستن:"):
        return handle_join_alliance(chat_id, text)
    if text == B("alliance_leave"):
        return handle_leave_alliance(chat_id)
    if text == B("alliance_manage"):
        return handle_alliance_manage(chat_id)
    if text == B("alliance_open_toggle"):
        return handle_toggle_alliance(chat_id)
    if text == B("alliance_applicants"):
        return handle_applicants(chat_id)
    if text.startswith("قبول:") or text.startswith("رد:"):
        return handle_applicant_decision(chat_id, text)
    if text == B("alliance_kick"):
        return handle_kick_prompt(chat_id)
    if text == B("alliance_upgrade"):
        return handle_alliance_upgrade(chat_id)
    if text == B("alliance_vault"):
        return handle_alliance_menu(chat_id)
    if text == B("inventory"):
        return handle_inventory(chat_id)
    if text == B("daily"):
        return handle_daily(chat_id)
    if text == B("invite"):
        return handle_invite(chat_id)
    if text == B("enter_referral"):
        return handle_enter_referral(chat_id)
    if text == B("season"):
        return handle_season(chat_id)
    if text == B("leaderboard"):
        return handle_leaderboard(chat_id)
    if text == B("admin_panel"):
        return handle_admin_panel(chat_id, sender_id)
    if text == B("admin_broadcast"):
        return handle_admin_broadcast_prompt(chat_id, sender_id)
    if text == B("admin_stats"):
        return handle_admin_stats(chat_id, sender_id)
    if text == B("admin_rename_player"):
        return handle_admin_rename_player_prompt(chat_id, sender_id)
    if text == B("admin_rename_alliance"):
        return handle_admin_rename_alliance_prompt(chat_id, sender_id)
    if text == B("admin_ban_player"):
        return handle_admin_ban_prompt(chat_id, sender_id)
    if text == B("admin_unban_player"):
        return handle_admin_unban_prompt(chat_id, sender_id)
    if text == B("admin_penalty_player"):
        return handle_admin_penalty_prompt(chat_id, sender_id)
    if text == B("admin_messages"):
        return handle_admin_messages(chat_id, sender_id)
    if text == B("admin_players"):
        return handle_admin_players(chat_id, 1, sender_id)
    admin_players_page = parse_admin_players_page(text)
    if admin_players_page is not None:
        return handle_admin_players(chat_id, admin_players_page, sender_id)
    if text == B("admin_alliances"):
        return handle_admin_alliances(chat_id, sender_id)
    if text == B("admin_market"):
        return handle_admin_market(chat_id, sender_id)
    if text == B("help"):
        return handle_help(chat_id)

    send(chat_id, T("errors.unknown"), keypad=main_keypad(chat_id))
    handle_start(chat_id, sender_name)


# ══════════════════════════════════════════════════════
#  UPDATE PROCESSING
# ══════════════════════════════════════════════════════
def process_update(raw: dict[str, Any]) -> None:
    upd = raw.get("update", raw)
    if "inline_message" in raw:
        # Inline is not used in v4, but process it just in case.
        il = raw["inline_message"]
        chat_id = il.get("chat_id", "")
        aux = il.get("aux_data") or {}
        inline_sender_id = str(il.get("sender_id", chat_id))
        LAST_SENDER_BY_CHAT[str(chat_id)] = inline_sender_id
        dispatch(
            chat_id,
            il.get("text", ""),
            inline_sender_id[-6:],
            aux.get("button_id", ""),
            inline_sender_id,
        )
        return
    chat_id = upd.get("chat_id", "")
    msg = upd.get("new_message") or upd.get("updated_message") or {}
    if not msg or not chat_id:
        return
    text = msg.get("text", "") or ""
    aux = msg.get("aux_data") or {}
    bid = aux.get("button_id", "") or ""
    sender_id = str(msg.get("sender_id", chat_id))
    LAST_SENDER_BY_CHAT[str(chat_id)] = sender_id
    sender_name = sender_id[-6:]
    if DEBUG:
        print(f"[UPDATE] chat={chat_id} sender={sender_id} text={text!r} bid={bid!r}")
    # ─────────────────────────────────────────
    # GROUP / CHANNEL HANDLER — must be before player flow
    # ─────────────────────────────────────────
    if str(chat_id).startswith(("g", "c")):
        if str(chat_id) == str(GAME_GROUP_ID):
            if DEBUG:
                print(f"[GROUP RADIO] chat={chat_id} sender={sender_id} text={text!r}")
            handle_group_message(str(chat_id), text or bid or "", str(sender_id))
        elif DEBUG:
            print(f"[GROUP IGNORED] chat={chat_id} sender={sender_id} text={text!r}")
        return
    dispatch(chat_id, text or bid, sender_name, bid, sender_id)


# ══════════════════════════════════════════════════════
#  EXPANSION PATCH: SEASON / SMUGGLER / REVENGE / BOUNTY / CACHES / TERRITORIES
# ══════════════════════════════════════════════════════
# این بخش عمداً به‌صورت لایه افزایشی نوشته شده تا سیوهای قدیمی خراب نشوند.
# اگر کلیدهای جدید در فایل متن نبودند، B() همان key را برمی‌گرداند؛ اما JSON هم پایین‌تر پچ شده.

CACHE_TYPES = {
    "rusty": {"label": "🎁 صندوق زنگ‌زده", "radio": False},
    "medium": {"label": "📦 صندوق متوسط", "radio": False},
    "military": {"label": "🪖 صندوق نظامی", "radio": True},
    "smuggler": {"label": "🕶️ صندوق قاچاقچی", "radio": True},
    "legendary": {"label": "👑 صندوق افسانه‌ای", "radio": True},
}
CACHE_ORDER = ["rusty", "medium", "military", "smuggler", "legendary"]
CACHE_OPEN_BUTTON = {k: f"باز کردن: {v['label']}" for k, v in CACHE_TYPES.items()}

CONSUMABLE_ITEMS = {
    "small_medkit": {"label": "🩹 کیت پزشکی کوچک", "desc": "استفاده: ❤️ جان +۴۰"},
    "weak_smoke": {"label": "🌫️ دودزا ضعیف", "desc": "خودکار: شکست گشت را سبک‌تر می‌کند"},
    "alley_map": {
        "label": "🧭 نقشه کوچه",
        "desc": "کلکسیونی/کمک روایی برای گشت‌های امن",
    },
    "small_repair_tool": {
        "label": "🔧 ابزار تعمیر کوچک",
        "desc": "استفاده: ۲۵٪ از زمان ارتقای فعال کم می‌کند",
    },
    "emp_weak": {
        "label": "💣 EMP ضعیف",
        "desc": "خودکار در حمله بعدی: دفاع هدف ۱۵٪ کمتر",
    },
    "emp_strong": {
        "label": "💣 EMP قوی",
        "desc": "خودکار در حمله بعدی: دفاع هدف ۳۰٪ کمتر",
    },
    "spy_drone": {"label": "🚁 پهپاد یک‌بارمصرف", "desc": "یک حمله دقیق رایگان"},
    "smoke_shield": {"label": "🛡️ محافظ دودزا", "desc": "استفاده: محافظ ۳ ساعته"},
    "anti_toxin_serum": {"label": "🧪 سرم ضدآلودگی", "desc": "استفاده: جان کامل می‌شود"},
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
USE_ITEM_BUTTON = {k: f"استفاده: {v['label']}" for k, v in CONSUMABLE_ITEMS.items()}

NIGHT_SMUGGLER_STOCK = {
    "scrap": 80,
    "plastic": 60,
    "glass": 30,
    "copper": 12,
    "battery": 4,
}
NIGHT_SMUGGLER_CAP = {
    "scrap": 25,
    "plastic": 20,
    "glass": 12,
    "copper": 4,
    "battery": 2,
}
NIGHT_SMUGGLER_BUY_BUTTON = {
    r: f"خرید قاچاق: {RES_ICON[r]} {RES_NAME[r]}" for r in RESOURCES
}

TERRITORIES = {
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
        "label": "🫙 شیشه‌خانه شکسته",
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
TERRITORY_ATTACK_BUTTON = {k: f"⚔️ حمله به {v['label']}" for k, v in TERRITORIES.items()}

ALLIANCE_MISSION_TEMPLATES = [
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

# Save original functions so the extension can wrap them safely.
_orig_new_player = new_player
_orig_default_game = default_game
_orig_migrate_game = migrate_game
_orig_market_keypad = market_keypad
_orig_handle_city_map = handle_city_map
_orig_handle_inventory = handle_inventory
_orig_handle_attack_menu = handle_attack_menu
_orig_alliance_keypad = alliance_keypad
_orig_handle_alliance_menu = handle_alliance_menu
_orig_inc_mission = inc_mission
_orig_fmt_reward_dict = fmt_reward_dict
_orig_award_mission_reward = award_mission_reward
_orig_maybe_find_cache = maybe_find_cache
_orig_handle_open_cache = handle_open_cache
_orig_maybe_roll_season = maybe_roll_season
_orig_group_radio_periodic_text = group_radio_periodic_text
_orig_periodic_group_radio = periodic_group_radio
_orig_handle_state = handle_state
_orig_dispatch = dispatch


def ensure_player_expansion_fields(p: dict[str, Any]) -> dict[str, Any]:
    p.setdefault("caches", {})
    for k in CACHE_ORDER:
        p["caches"].setdefault(k, 0)
    old = int(p.get("loot_caches", 0) or 0)
    total = sum(int(p["caches"].get(k, 0) or 0) for k in CACHE_ORDER)
    if old > total:
        p["caches"]["rusty"] = int(p["caches"].get("rusty", 0)) + (old - total)
    p["loot_caches"] = sum(int(p["caches"].get(k, 0) or 0) for k in CACHE_ORDER)
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


def refresh_cache_total(p: dict[str, Any]) -> int:
    ensure_player_expansion_fields(p)
    total = sum(int(p.get("caches", {}).get(k, 0) or 0) for k in CACHE_ORDER)
    p["loot_caches"] = total
    return total


def add_cache_to_player(chat_id: str, cache_type: str = "rusty", qty: int = 1) -> None:
    if cache_type not in CACHE_ORDER:
        cache_type = "rusty"
    p = get_player(chat_id)
    ensure_player_expansion_fields(p)
    p["caches"][cache_type] = int(p["caches"].get(cache_type, 0)) + int(qty)
    refresh_cache_total(p)
    save_game()  # اضافه شد


def add_inventory_item(p: dict[str, Any], key: str, qty: int = 1) -> None:
    p.setdefault("inventory", {})[key] = int(p.get("inventory", {}).get(key, 0)) + int(
        qty
    )


def fmt_cache_counts(p: dict[str, Any]) -> str:
    ensure_player_expansion_fields(p)
    parts = []
    for k in CACHE_ORDER:
        q = int(p.get("caches", {}).get(k, 0) or 0)
        if q > 0:
            parts.append(f"{CACHE_TYPES[k]['label']} × {q}")
    return "\n".join(parts) if parts else "صندوقی نداری."


def fmt_any_reward(reward: dict[str, int]) -> str:
    parts: list[str] = []
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            parts.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            parts.append(f"🎁 صندوق زنگ‌زده × {v}")
        elif k.startswith("cache_"):
            ctype = k.split("_", 1)[1]
            parts.append(
                f"{CACHE_TYPES.get(ctype, CACHE_TYPES['rusty'])['label']} × {v}"
            )
        elif k in RES_ICON:
            parts.append(fmt_res_amount(k, v))
        elif k.startswith("vault_"):
            res = k.split("_", 1)[1]
            if res == "water":
                parts.append(f"خزانه اتحاد: 💧 آب × {v}")
            elif res in RES_ICON:
                parts.append(f"خزانه اتحاد: {RES_ICON[res]} {RES_NAME[res]} × {v}")
        elif k == "season_points":
            parts.append(f"XP/امتیاز اتحاد × {v}")
        elif k == "member_cache_medium":
            parts.append(f"📦 صندوق متوسط × {v} برای اعضای فعال")
        else:
            parts.append(f"{k} × {v}")
    return " + ".join(parts) if parts else "—"


def fmt_reward_dict(reward: dict[str, int]) -> str:  # override
    return fmt_any_reward(reward)


def award_mission_reward(p: dict[str, Any], reward: dict[str, int]) -> str:  # override
    paid: list[str] = []
    # Find owner id for cache awards where possible.
    owner_id = None
    for cid, pp in game.get("players", {}).items():
        if pp is p:
            owner_id = cid
            break
    for k, v in (reward or {}).items():
        v = int(v)
        if v <= 0:
            continue
        if k == "xp":
            add_xp(p, v)
            paid.append(f"⭐ XP × {v}")
        elif k == "loot_cache":
            if owner_id:
                add_cache_to_player(owner_id, "rusty", v)
            else:
                p["loot_caches"] = int(p.get("loot_caches", 0)) + v
            paid.append(f"🎁 صندوق زنگ‌زده × {v}")
        elif k.startswith("cache_"):
            ctype = k.split("_", 1)[1]
            if owner_id:
                add_cache_to_player(owner_id, ctype, v)
            paid.append(
                f"{CACHE_TYPES.get(ctype, CACHE_TYPES['rusty'])['label']} × {v}"
            )
        else:
            add_amount(p, k, v)
            paid.append(fmt_res_amount(k, v))
    return " + ".join(paid) if paid else "—"


def new_player(
    name: Optional[str] = None, chat_id: str = ""
) -> dict[str, Any]:  # override
    p = _orig_new_player(name, chat_id)
    ensure_player_expansion_fields(p)
    return p


def default_game() -> dict[str, Any]:  # override
    g = _orig_default_game()
    g.setdefault("night_smuggler", None)
    g.setdefault("revenge_targets", [])
    g.setdefault("next_revenge_id", 1)
    g.setdefault("bounty_contracts", [])
    g.setdefault("next_bounty_id", 1)
    g.setdefault("territories", {})
    g.setdefault("last_territory_reward_day", None)
    return g


def ensure_territories() -> dict[str, Any]:
    terr = game.setdefault("territories", {})
    for key, cfg in TERRITORIES.items():
        terr.setdefault(
            key, {"owner": None, "last_attack_at": None, "last_reward_day": None}
        )
        terr[key].setdefault("owner", None)
        terr[key].setdefault("last_attack_at", None)
        terr[key].setdefault("last_reward_day", None)
    return terr


def migrate_game(g: dict[str, Any]) -> dict[str, Any]:  # override
    base = _orig_migrate_game(g)
    base.setdefault("night_smuggler", None)
    base.setdefault("revenge_targets", [])
    base.setdefault("next_revenge_id", 1)
    base.setdefault("bounty_contracts", [])
    base.setdefault("next_bounty_id", 1)
    base.setdefault("territories", {})
    base.setdefault("last_territory_reward_day", None)
    for cid, p in list(base.get("players", {}).items()):
        ensure_player_expansion_fields(p)
    for al in base.get("alliances", {}).values():
        if isinstance(al, dict):
            al.setdefault("resource_vault", {})
            for r in RESOURCES:
                al["resource_vault"].setdefault(r, 0)
            al.setdefault("mission_day", None)
            al.setdefault("alliance_missions", [])
            al.setdefault("territory_cd", {})
    # Ensure territory container without requiring global game.
    terr = base.setdefault("territories", {})
    for key in TERRITORIES:
        terr.setdefault(
            key, {"owner": None, "last_attack_at": None, "last_reward_day": None}
        )
    return base


def market_keypad() -> dict[str, Any]:  # override
    return make_keypad(
        [
            [B("market_people"), B("market_create_order")],
            [B("market_my_orders"), B("market_barter")],
            [B("market_my_barters"), B("market_resource_rentals")],
            [B("night_smuggler"), B("market_system_buy")],
            [B("market_system_sell"), B("market_prices")],
            [B("main_menu")],
        ]
    )


def handle_city_map(chat_id: str) -> None:  # override
    boss = active_boss()
    boss_line = (
        T("map.boss_active", name=boss["name"], hp=fmt_num(boss["hp"]))
        if boss
        else T("map.boss_none")
    )
    p = get_player(chat_id)
    cache_line = fmt_cache_counts(p)
    ensure_territories()
    owners = []
    for k, cfg in TERRITORIES.items():
        owner = game.get("territories", {}).get(k, {}).get("owner")
        owners.append(f"{cfg['label']}: {owner or 'بدون مالک'}")
    text = (
        "🗺️ نقشه شهر\n━━━━━━━━━━━━\n"
        "اینجا مرکز گشت، باس، صندوق‌ها و جنگ کارتل‌هاست.\n\n"
        f"☣️ باس جهانی: {boss_line}\n\n"
        f"🎁 صندوق‌های تو:\n{cache_line}\n\n"
        "🏴 مناطق قابل تصرف:\n" + "\n".join(owners[:7])
    )
    send(
        chat_id,
        f"🗺️ نقشه شهر آخرالزمان\n\n"
        f"{boss_line}\n\n"
        f"🎁 صندوق‌های تو:\n{cache_line}\n\n"
        f"🕶️ قاچاقچی شبانه → بخش بازار",
        keypad=make_keypad(
            [
                [B("scavenge_alley"), B("scavenge_suburb")],
                [B("scavenge_center"), B("scavenge_bunker")],
                [B("world_boss"), B("open_cache")],
                [B("daily_missions"), B("news"), B("event")],
                [B("main_menu")],
            ]
        ),
    )


def maybe_find_cache(chat_id: str, zone_key: str) -> str:  # override
    chances = {"alley": 0.010, "suburb": 0.018, "center": 0.032, "bunker": 0.055}
    p = get_player(chat_id)
    if zone_key == "bunker" and int(p.get("inventory", {}).get("bunker_map", 0)) > 0:
        p["inventory"]["bunker_map"] -= 1
        if p["inventory"].get("bunker_map", 0) <= 0:
            p["inventory"].pop("bunker_map", None)
        chances["bunker"] += 0.10
    if random.random() > chances.get(zone_key, 0.015):
        return ""
    ctype = "rusty"
    if zone_key == "center" and random.random() < 0.25:
        ctype = "medium"
    if zone_key == "bunker":
        ctype = (
            "military"
            if random.random() < 0.18
            else ("medium" if random.random() < 0.45 else "rusty")
        )
    add_cache_to_player(chat_id, ctype, 1)
    add_news(
        f"🎁 {player_name(chat_id)} در گشت‌زنی {CACHE_TYPES[ctype]['label']} پیدا کرد."
    )
    return f"\n🎁 پیدا کردی: {CACHE_TYPES[ctype]['label']}\n📦 صندوق‌های تو الان: {refresh_cache_total(p)}"


def handle_open_cache(chat_id: str) -> None:  # override: now opens a cache menu
    p = get_player(chat_id)
    total = refresh_cache_total(p)
    if total <= 0:
        send(
            chat_id,
            "🎁 صندوقی برای باز کردن نداری.\n\nاز گشت‌های خطرناک، باس، مأموریت‌ها یا جایزه‌ها صندوق بگیر.",
            keypad=main_keypad(chat_id),
        )
        return
    rows = []
    for k in CACHE_ORDER:
        if int(p.get("caches", {}).get(k, 0) or 0) > 0:
            rows.append([CACHE_OPEN_BUTTON[k]])
    rows.append([B("main_menu")])
    send(
        chat_id,
        "🎁 صندوق‌ها\n━━━━━━━━━━━━\n"
        + fmt_cache_counts(p)
        + "\n\nکدوم صندوق را باز کنم؟",
        keypad=make_keypad(rows),
    )


def weighted_choice(items: list[tuple[str, int]]) -> str:
    total = sum(w for _, w in items)
    r = random.randint(1, max(1, total))
    cur = 0
    for key, w in items:
        cur += w
        if r <= cur:
            return key
    return items[-1][0]


def grant_cache_reward(chat_id: str, cache_type: str) -> list[str]:
    p = get_player(chat_id)
    lines: list[str] = []
    if cache_type == "rusty":
        kind = weighted_choice(
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
                add_amount(p, r, q)
            lines.append(fmt_res_lines(loot))
        elif kind == "medium_cache":
            add_cache_to_player(chat_id, "medium", 1)
            lines.append("📦 صندوق متوسط × ۱")
        else:
            key = random.choice(
                ["small_medkit", "weak_smoke", "alley_map", "small_repair_tool"]
            )
            add_inventory_item(p, key)
            lines.append(CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "medium":
        kind = weighted_choice(
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
                add_amount(p, r, q)
            lines.append(fmt_res_lines(loot))
        elif kind == "military_cache":
            add_cache_to_player(chat_id, "military", 1)
            lines.append("🪖 صندوق نظامی × ۱")
        elif kind == "legendary_roll":
            lg = maybe_award_legendary(chat_id, "صندوق متوسط", 0.045)
            if lg:
                lines.append(lg)
            else:
                add_amount(p, "copper", 4)
                lines.append("🔶 مس × ۴")
        else:
            key = random.choice(
                ["emp_weak", "spy_drone", "smoke_shield", "anti_toxin_serum"]
            )
            add_inventory_item(p, key)
            lines.append(CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "military":
        kind = weighted_choice(
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
                add_amount(p, r, q)
            lines.append(fmt_res_lines(loot))
        elif kind == "smuggler_cache":
            add_cache_to_player(chat_id, "smuggler", 1)
            lines.append("🕶️ صندوق قاچاقچی × ۱")
        elif kind == "legendary_roll":
            lg = maybe_award_legendary(chat_id, "صندوق نظامی", 0.12)
            if lg:
                lines.append(lg)
            else:
                add_inventory_item(p, "emp_strong")
                lines.append(CONSUMABLE_ITEMS["emp_strong"]["label"] + " × ۱")
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
            add_inventory_item(p, key)
            lines.append(CONSUMABLE_ITEMS[key]["label"] + " × ۱")
        send_group_radio(
            f"🎁 صدای فلز از صندوق\n{player_name(chat_id)} یه صندوق نظامی باز کرد.\nاگه امشب کسی رو زد، نگید شانسی بود.",
            force=True,
            reason="military_cache",
        )
    elif cache_type == "smuggler":
        loot = {"copper": random.randint(4, 10), "battery": random.randint(1, 4)}
        for r, q in loot.items():
            add_amount(p, r, q)
        lines.append(fmt_res_lines(loot))
        key = random.choice(["emp_weak", "emp_strong", "spy_drone", "war_adrenaline"])
        add_inventory_item(p, key)
        lines.append(CONSUMABLE_ITEMS[key]["label"] + " × ۱")
    elif cache_type == "legendary":
        lg = maybe_award_legendary(chat_id, "صندوق افسانه‌ای", 1.0)
        if lg:
            lines.append(lg)
        add_inventory_item(
            p, random.choice(["emp_strong", "war_adrenaline", "temp_defense_plate"]), 2
        )
        p["season_points_bonus"] = int(p.get("season_points_bonus", 0)) + 500
        lines.append("🏆 امتیاز سیزن × ۵۰۰")
        send_group_radio(
            f"👑 بوی افسانه\n{player_name(chat_id)} از صندوق افسانه‌ای چیزی بیرون کشید که نباید دست هیچ آدم سالمی باشه.",
            force=True,
            reason="legendary_cache",
        )
    return lines


def handle_open_cache_type(chat_id: str, text: str) -> None:
    ctype = next((k for k, b in CACHE_OPEN_BUTTON.items() if text == b), None)
    if not ctype:
        return handle_open_cache(chat_id)

    p = get_player(chat_id)
    ensure_player_expansion_fields(p)

    if int(p.get("caches", {}).get(ctype, 0) or 0) <= 0:
        send(chat_id, "❌ از این نوع صندوق نداری.", keypad=main_keypad(chat_id))
        return

    # === فیکس اصلی ===
    p["caches"][ctype] -= 1

    # محاسبه مستقیم مجموع (بدون صدا زدن ensure_player_expansion_fields)
    new_total = sum(int(p.get("caches", {}).get(k, 0) or 0) for k in CACHE_ORDER)
    p["loot_caches"] = new_total
    p.setdefault("stats", {})["caches_opened"] = (
        int(p.get("stats", {}).get("caches_opened", 0)) + 1
    )
    inc_mission(chat_id, "open_cache", 1)

    lines = grant_cache_reward(chat_id, ctype)

    save_game()  # خیلی مهم!
    print("CACHE DEBUG", ctype, p["caches"], p["loot_caches"])

    send(
        chat_id,
        f"✅ {CACHE_TYPES[ctype]['label']} باز شد!\n━━━━━━━━━━━━\n"
        + "\n".join(lines)
        + f"\n\n📦 صندوق‌های باقی‌مانده: {p.get('loot_caches', 0)}",
        keypad=make_keypad([[B("open_cache")], [B("inventory")], [B("main_menu")]]),
    )


def consume_next_raid_emp(
    chat_id: str, p: dict[str, Any], raid_notes: list[str]
) -> float:
    inv = p.setdefault("inventory", {})
    for key, mult, label in [
        ("emp_strong", 0.70, "💣 EMP قوی"),
        ("emp_weak", 0.85, "💣 EMP ضعیف"),
    ]:
        if int(inv.get(key, 0) or 0) > 0:
            inv[key] -= 1
            if inv.get(key, 0) <= 0:
                inv.pop(key, None)
            raid_notes.append(f"{label} مصرف شد؛ دفاع هدف کمتر حساب شد.")
            return mult
    return 1.0


def consume_next_raid_boosters(
    chat_id: str, p: dict[str, Any], raid_notes: list[str]
) -> float:
    inv = p.setdefault("inventory", {})
    if int(inv.get("war_adrenaline", 0) or 0) > 0:
        inv["war_adrenaline"] -= 1
        if inv.get("war_adrenaline", 0) <= 0:
            inv.pop("war_adrenaline", None)
        raid_notes.append("⚔️ آدرنالین جنگی مصرف شد؛ حمله بعدی ۲۰٪ قوی‌تر شد.")
        return 1.20
    return 1.0


def handle_use_consumable(chat_id: str, text: str) -> None:
    key = next((k for k, b in USE_ITEM_BUTTON.items() if text == b), None)
    if not key:
        return handle_inventory(chat_id)
    p = get_player(chat_id)
    inv = p.setdefault("inventory", {})
    if int(inv.get(key, 0) or 0) <= 0:
        send(chat_id, "❌ از این آیتم نداری.", keypad=main_keypad(chat_id))
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
        if is_shielded(p):
            send(
                chat_id,
                f"🛡️ الان محافظ داری: {fmt_cd(shield_remaining(p))} باقی مانده.",
                keypad=main_keypad(chat_id),
            )
            return
        p["shield_until"] = iso(now() + timedelta(hours=3))
        msg = "🛡️ محافظ دودزا فعال شد. تا ۳ ساعت یک لایه امنیت داری."
    elif key == "temp_defense_plate":
        p["temp_defense_until"] = iso(now() + timedelta(hours=2))
        msg = "🚧 صفحه دفاعی نصب شد. تا ۲ ساعت دفاعت در غارت‌ها ۱۵٪ بیشتر حساب می‌شود."
    elif key == "small_repair_tool":
        if not p.get("upgrades_in_progress"):
            send(
                chat_id,
                "🔧 ارتقای فعالی نداری که تعمیر/تسریع شود.",
                keypad=main_keypad(chat_id),
            )
            return
        for u in p.get("upgrades_in_progress", []):
            finish = fromiso(u.get("finish"), now())
            left = max(0, (finish - now()).total_seconds())
            u["finish"] = iso(now() + timedelta(seconds=left * 0.75))
        msg = "🔧 ابزار تعمیر مصرف شد. زمان ارتقاهای فعال ۲۵٪ کمتر شد."
    else:
        send(
            chat_id,
            "این آیتم در زمان مناسب خودکار مصرف می‌شود: "
            + CONSUMABLE_ITEMS[key]["desc"],
            keypad=main_keypad(chat_id),
        )
        return
    inv[key] -= 1
    if inv.get(key, 0) <= 0:
        inv.pop(key, None)
    save_game()
    send(chat_id, msg, keypad=main_keypad(chat_id))


def handle_inventory(chat_id: str) -> None:  # override
    p = get_player(chat_id)
    ensure_player_expansion_fields(p)
    items = []
    rows = []
    for k, qty in sorted(p.get("inventory", {}).items()):
        if qty <= 0:
            continue
        if k in CRAFT_ITEMS:
            items.append(f"{CRAFT_ITEMS[k]['label']} × {qty}")
        elif k in LEGENDARY_ITEMS:
            items.append(f"✨ {LEGENDARY_ITEMS[k]['label']} × {qty}")
        elif k in CONSUMABLE_ITEMS:
            items.append(
                f"{CONSUMABLE_ITEMS[k]['label']} × {qty}\n  {CONSUMABLE_ITEMS[k]['desc']}"
            )
            if k in USE_ITEM_BUTTON and k in [
                "small_medkit",
                "anti_toxin_serum",
                "smoke_shield",
                "temp_defense_plate",
                "small_repair_tool",
            ]:
                rows.append([USE_ITEM_BUTTON[k]])
    if refresh_cache_total(p) > 0:
        items.append("🎁 صندوق‌ها:\n" + fmt_cache_counts(p))
        rows.append([B("open_cache")])
    rows.append([B("main_menu")])
    send(
        chat_id,
        T(
            "inventory.text",
            items="\n\n".join(items) or T("inventory.empty"),
            scrap=p["resources"].get("scrap", 0),
            plastic=p["resources"].get("plastic", 0),
            glass=p["resources"].get("glass", 0),
            battery=p["resources"].get("battery", 0),
            copper=p["resources"].get("copper", 0),
            water=p.get("water", 0),
        ),
        keypad=make_keypad(rows),
    )


def smuggler_active_window(dt: Optional[datetime] = None) -> bool:
    dt = dt or now()
    return dt.hour >= 22 or dt.hour < 2


def smuggler_day_key(dt: Optional[datetime] = None) -> str:
    dt = dt or now()
    if dt.hour < 2:
        dt = dt - timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


def smuggler_active_until(dt: Optional[datetime] = None) -> datetime:
    dt = dt or now()
    if dt.hour >= 22:
        return (dt + timedelta(days=1)).replace(
            hour=2, minute=0, second=0, microsecond=0
        )
    return dt.replace(hour=2, minute=0, second=0, microsecond=0)


def maybe_setup_night_smuggler() -> Optional[dict[str, Any]]:
    if not smuggler_active_window():
        return None
    day = smuggler_day_key()
    sm = game.get("night_smuggler")
    if not isinstance(sm, dict) or sm.get("day") != day:
        prices = {
            r: max(1, int(BASE_PRICE[r] * random.uniform(0.45, 0.70)))
            for r in RESOURCES
        }
        sm = {
            "day": day,
            "active_until": iso(smuggler_active_until()),
            "stock": dict(NIGHT_SMUGGLER_STOCK),
            "prices": prices,
            "buyers": {},
            "announced": False,
            "soldout_announced": False,
        }
        game["night_smuggler"] = sm
    if not sm.get("announced"):
        sm["announced"] = True
        send_group_radio(
            "🕶️ قاچاقچی شبانه رسید\nبارش کمه، قیمت‌ها کثیفاً ارزونه.\nهرکی خواب بمونه، فردا فقط غر می‌زنه.",
            force=True,
            reason="night_smuggler",
        )
        add_news("🕶️ قاچاقچی شبانه رسیده؛ موجودی محدود و قیمت‌ها پایین‌تر از بازار است.")
    if all(int(v) <= 0 for v in sm.get("stock", {}).values()) and not sm.get(
        "soldout_announced"
    ):
        sm["soldout_announced"] = True
        send_group_radio(
            "📦 بار قاچاقچی خالی شد.\nشهر سریع‌تر از چیزی که فکر می‌کردی گرسنه بود.",
            force=True,
            reason="night_smuggler_empty",
        )
    return sm


def handle_night_smuggler(chat_id: str) -> None:
    sm = maybe_setup_night_smuggler()
    if not sm:
        send(
            chat_id,
            "🕶️ قاچاقچی شبانه\n━━━━━━━━━━━━\nفعلاً پیداش نیست. معمولاً از ساعت ۲۲:۰۰ تا ۰۲:۰۰ بارش را می‌آورد.\n\nقاچاقچی فقط منابع می‌فروشد؛ آیتم و صندوق نه.",
            keypad=market_keypad(),
        )
        return
    lines = []
    rows = []
    for r in RESOURCES:
        stock = int(sm.get("stock", {}).get(r, 0) or 0)
        price = int(sm.get("prices", {}).get(r, BASE_PRICE[r]) or BASE_PRICE[r])
        lines.append(
            f"{RES_ICON[r]} {RES_NAME[r]} × {stock} — قیمت: {price} آب / هر عدد — سقف تو: {NIGHT_SMUGGLER_CAP[r]}"
        )
        if stock > 0:
            rows.append([NIGHT_SMUGGLER_BUY_BUTTON[r]])
    rows.append([B("back_market"), B("main_menu")])
    left = fmt_cd((fromiso(sm.get("active_until"), now()) - now()).total_seconds())
    send(
        chat_id,
        "🕶️ قاچاقچی شبانه\n━━━━━━━━━━━━\nامشب بارش محدوده. هرکی زودتر بخرد، برده.\n\n📦 موجودی امشب:\n"
        + "\n".join(lines)
        + f"\n\n⏳ زمان باقی‌مانده: {left}\n📌 هر بازیکن هر شب حداکثر از ۲ نوع منبع می‌خرد.",
        keypad=make_keypad(rows),
    )


def handle_smuggler_select(chat_id: str, text: str) -> None:
    res = next((r for r, b in NIGHT_SMUGGLER_BUY_BUTTON.items() if text == b), None)
    sm = maybe_setup_night_smuggler()
    if not res or not sm:
        return handle_night_smuggler(chat_id)
    stock = int(sm.get("stock", {}).get(res, 0) or 0)
    if stock <= 0:
        send(chat_id, "❌ این بار قاچاقچی تمام شده.", keypad=market_keypad())
        return
    buyers = sm.setdefault("buyers", {}).setdefault(chat_id, {})
    bought_types = [r for r, q in buyers.items() if int(q) > 0]
    if res not in bought_types and len(bought_types) >= 2:
        send(
            chat_id,
            "❌ امشب از ۲ نوع منبع خرید کردی. بیشتر از این قاچاقچی بهت رو نمی‌ده.",
            keypad=market_keypad(),
        )
        return
    already = int(buyers.get(res, 0) or 0)
    cap_left = max(0, NIGHT_SMUGGLER_CAP[res] - already)
    if cap_left <= 0:
        send(chat_id, "❌ سقف خرید امشب این منبع را پر کردی.", keypad=market_keypad())
        return
    game.setdefault("chat_states", {})[chat_id] = {
        "state": "awaiting_smuggler_qty",
        "res": res,
    }
    save_game()
    send(
        chat_id,
        f"چند تا {RES_ICON[res]} {RES_NAME[res]} از قاچاقچی بخرم؟\nموجودی قاچاقچی: {stock}\nسقف باقی‌مانده تو: {cap_left}\nقیمت واحد: {sm['prices'][res]} آب",
        keypad=make_keypad([[B("night_smuggler")], [B("main_menu")]]),
    )


def handle_smuggler_qty(chat_id: str, text: str) -> None:
    st = game.get("chat_states", {}).get(chat_id, {})
    res = st.get("res")
    sm = maybe_setup_night_smuggler()
    if not sm or res not in RESOURCES:
        game.get("chat_states", {}).pop(chat_id, None)
        return handle_night_smuggler(chat_id)
    qty = safe_int(text, -1)
    if qty <= 0:
        send(
            chat_id,
            "❌ عدد معتبر بفرست.",
            keypad=make_keypad([[B("night_smuggler")], [B("main_menu")]]),
        )
        return
    buyers = sm.setdefault("buyers", {}).setdefault(chat_id, {})
    already = int(buyers.get(res, 0) or 0)
    cap_left = max(0, NIGHT_SMUGGLER_CAP[res] - already)
    qty = min(qty, cap_left, int(sm.get("stock", {}).get(res, 0) or 0))
    if qty <= 0:
        send(chat_id, "❌ سقف خرید یا موجودی قاچاقچی تمام شده.", keypad=market_keypad())
        game.get("chat_states", {}).pop(chat_id, None)
        return
    price = int(sm.get("prices", {}).get(res, BASE_PRICE[res]))
    total = qty * price
    p = get_player(chat_id)
    if int(p.get("water", 0)) < total:
        send(
            chat_id,
            T("errors.not_enough_water", need=total, have=p.get("water", 0)),
            keypad=market_keypad(),
        )
        return
    p["water"] = int(p.get("water", 0)) - total
    add_amount(p, res, qty)
    sm["stock"][res] = int(sm["stock"].get(res, 0)) - qty
    buyers[res] = already + qty
    p.setdefault("stats", {})["smuggler_buys"] = (
        int(p.get("stats", {}).get("smuggler_buys", 0)) + 1
    )
    game.get("chat_states", {}).pop(chat_id, None)
    if all(int(v) <= 0 for v in sm.get("stock", {}).values()) and not sm.get(
        "soldout_announced"
    ):
        sm["soldout_announced"] = True
        send_group_radio(
            "📦 بار قاچاقچی خالی شد.\nشهر سریع‌تر از چیزی که فکر می‌کردی گرسنه بود.",
            force=True,
            reason="night_smuggler_empty",
        )
    save_game()
    send(
        chat_id,
        f"✅ خرید قاچاق انجام شد!\n\nگرفتی: {fmt_res_amount(res, qty)}\nپرداختی: 💧 آب × {total}\n💧 آب باقی‌مانده: {p.get('water', 0)}",
        keypad=market_keypad(),
    )


def expire_revenge_targets() -> None:
    for r in game.setdefault("revenge_targets", []):
        if not r.get("used") and fromiso(r.get("expires_at"), now()) <= now():
            r["used"] = True
            r["expired"] = True


def register_revenge_target(attacker_id: str, victim_id: str, lost: int = 0) -> None:
    if attacker_id == victim_id:
        return
    rid = int(game.get("next_revenge_id", 1))
    game["next_revenge_id"] = rid + 1
    rec = {
        "id": rid,
        "attacker": attacker_id,
        "victim": victim_id,
        "lost": int(lost or 0),
        "created_at": iso(now()),
        "expires_at": iso(now() + timedelta(hours=24)),
        "used": False,
    }
    game.setdefault("revenge_targets", []).append(rec)
    game["revenge_targets"] = game["revenge_targets"][-200:]
    try:
        send(
            victim_id,
            f"🚨 گاراژت غارت شد!\nمهاجم: {display_name(player_name(attacker_id))}\nضرر: 💧 آب × {fmt_num(lost)}\n\n🔥 فرصت انتقام باز شد. تا ۲۴ ساعت می‌تونی بدون پهپاد به همین مهاجم حمله کنی.",
            keypad=main_keypad(victim_id),
        )
    except Exception:
        pass


def open_revenge_records(chat_id: str) -> list[dict[str, Any]]:
    expire_revenge_targets()
    return [
        r
        for r in game.get("revenge_targets", [])
        if r.get("victim") == chat_id and not r.get("used")
    ]


def handle_revenge_menu(chat_id: str) -> None:
    recs = open_revenge_records(chat_id)
    if not recs:
        send(
            chat_id,
            "🔥 لیست انتقام‌ها\n━━━━━━━━━━━━\nفعلاً فرصت انتقام فعالی نداری.\n\nوقتی کسی گاراژت را بزند، ۲۴ ساعت فرصت جواب دادن می‌گیری.",
            keypad=make_keypad([[B("attack")], [B("main_menu")]]),
        )
        return
    lines = []
    rows = []
    for r in recs[:8]:
        left = fmt_cd((fromiso(r.get("expires_at"), now()) - now()).total_seconds())
        lines.append(
            f"#{r['id']} — {player_name(r['attacker'])}\n⏳ باقی‌مانده: {left}\n🎯 مزیت: بدون نیاز به پهپاد، افتخار بیشتر"
        )
        rows.append([f"🔥 انتقام #{r['id']}"])
    rows.append([B("attack"), B("main_menu")])
    send(
        chat_id,
        "🔥 لیست انتقام‌ها\n━━━━━━━━━━━━\n" + "\n\n".join(lines),
        keypad=make_keypad(rows),
    )


def handle_revenge_attack(chat_id: str, text: str) -> None:
    rid = safe_int(re.sub(r"\D+", "", text), -1)
    rec = next(
        (r for r in open_revenge_records(chat_id) if int(r.get("id", -1)) == rid), None
    )
    if not rec:
        send(
            chat_id,
            "❌ این انتقام پیدا نشد یا وقتش تمام شده.",
            keypad=main_keypad(chat_id),
        )
        return
    p = get_player(chat_id)
    if p.get("revenge_cd") and fromiso(p.get("revenge_cd"), now()) > now():
        send(
            chat_id,
            f"⏳ هنوز نیروهای انتقام خسته‌اند.\nزمان باقی‌مانده: {fmt_cd((fromiso(p.get('revenge_cd'), now()) - now()).total_seconds())}",
            keypad=main_keypad(chat_id),
        )
        return
    target_id = rec.get("attacker")
    target = game.get("players", {}).get(target_id)
    if not target:
        send(chat_id, "❌ مهاجم قبلی پیدا نشد.", keypad=main_keypad(chat_id))
        return
    if is_shielded(target):
        send(
            chat_id,
            "🛡️ هدف محافظ دارد. فعلاً نمی‌شود انتقام گرفت.",
            keypad=main_keypad(chat_id),
        )
        return
    # Bypass normal raid cooldown for revenge, but preserve it if it was longer.
    old_cd = p.get("raid_cd")
    p["raid_cd"] = None
    before_log_len = len(p.get("action_log", []))
    handle_raid(chat_id, target_id, bucket_key="medium", precise=False)
    p = get_player(chat_id)
    p["revenge_cd"] = iso(now() + timedelta(minutes=30))
    if old_cd and fromiso(old_cd, now()) > fromiso(p.get("raid_cd"), now()):
        p["raid_cd"] = old_cd
    rec["used"] = True
    last = (p.get("action_log") or [None])[-1]
    if isinstance(last, dict) and last.get("action") == "raid_win":
        p["honor"] = int(p.get("honor", 0)) + 8
        p.setdefault("stats", {})["revenge_wins"] = (
            int(p.get("stats", {}).get("revenge_wins", 0)) + 1
        )
        send_group_radio(
            f"🔥 انتقام ثبت شد\n{player_name(chat_id)} جواب {player_name(target_id)} رو داد.\nشهر یاد گرفت بعضی گاراژها دیر می‌زنن، ولی بد می‌زنن.",
            force=True,
            reason="revenge_win",
        )
        send(
            chat_id,
            "🔥 انتقام موفق حساب شد!\n🎖️ افتخار اضافه: +8\nاین یکی فقط غارت نبود؛ جواب بود.",
            keypad=main_keypad(chat_id),
        )
    else:
        p.setdefault("stats", {})["revenge_losses"] = (
            int(p.get("stats", {}).get("revenge_losses", 0)) + 1
        )
        send_group_radio(
            f"💀 انتقام شکست خورد\n{player_name(chat_id)} برگشت جواب بده، ولی {player_name(target_id)} دوباره نگهش داشت.",
            force=True,
            reason="revenge_lose",
        )
    save_game()


def expire_bounty_contracts() -> None:
    for b in game.setdefault("bounty_contracts", []):
        if b.get("status") == "open" and fromiso(b.get("expires_at"), now()) <= now():
            b["status"] = "expired"
            creator = b.get("creator")
            if creator in game.get("players", {}):
                for r, q in b.get("reward", {}).items():
                    add_amount(game["players"][creator], r, int(q))


def parse_reward_resources(text: str) -> dict[str, int]:
    tokens = re.findall(r"([آ-یA-Za-z_]+)\s+(\d+)", text or "")
    out: dict[str, int] = {}
    for name, qty in tokens:
        rk = res_key(name)
        if rk and rk in RESOURCES:
            out[rk] = out.get(rk, 0) + int(qty)
    return out


def parse_bounty_text(text: str) -> tuple[Optional[str], dict[str, int]]:
    if "=" not in text:
        return None, {}
    left, right = text.split("=", 1)
    return left.strip(), parse_reward_resources(right)


def handle_bounty_board(chat_id: str) -> None:
    expire_bounty_contracts()
    rows = []
    lines = []
    for b in [x for x in game.get("bounty_contracts", []) if x.get("status") == "open"][
        :12
    ]:
        target = game.get("players", {}).get(b.get("target"), {})
        left = fmt_cd((fromiso(b.get("expires_at"), now()) - now()).total_seconds())
        creator_name = "ناشناس" if b.get("anonymous") else player_name(b.get("creator"))
        lines.append(
            f"#{b['id']}\nهدف: {player_name(b.get('target'))}\nلول: {target.get('level', '—')}\nجایزه: {fmt_res_dict(b.get('reward', {}))}\nثبت‌کننده: {creator_name}\n⏳ باقی‌مانده: {left}"
        )
    rows = [[B("bounty_create")], [B("bounty_my")], [B("attack"), B("main_menu")]]
    send(
        chat_id,
        "🎯 تابلو جایزه‌بگیرها\n━━━━━━━━━━━━\n"
        + ("\n\n".join(lines) if lines else "فعلاً قراردادی روی دیوار نیست."),
        keypad=make_keypad(rows),
    )


def handle_create_bounty_prompt(chat_id: str) -> None:
    game.setdefault("chat_states", {})[chat_id] = {"state": "awaiting_bounty_order"}
    save_game()
    send(
        chat_id,
        "🧾 ثبت قرارداد جایزه\n━━━━━━━━━━━━\nفرمت را اینطوری بفرست:\n\nاکبر آهنی = مس 5 باتری 1\n\nقوانین:\n• هدف باید لول ۳ به بالا باشد.\n• جایزه فقط منابع است.\n• جایزه از موجودی تو قفل می‌شود.\n• هر بازیکن روزی ۲ قرارداد می‌تواند ثبت کند.",
        keypad=make_keypad([[B("bounty_board")], [B("main_menu")]]),
    )


def handle_create_bounty(chat_id: str, text: str) -> None:
    target_name, reward = parse_bounty_text(text)
    if not target_name or not reward:
        send(
            chat_id,
            "❌ فرمت درست نیست. مثال: اکبر آهنی = مس 5 باتری 1",
            keypad=main_keypad(chat_id),
        )
        return
    target_id = find_player_by_name(target_name)
    if not target_id or target_id == chat_id:
        send(
            chat_id,
            "❌ هدف پیدا نشد یا نمی‌تونی روی خودت قرارداد بگذاری.",
            keypad=main_keypad(chat_id),
        )
        return
    target = game.get("players", {}).get(target_id, {})
    if int(target.get("level", 1)) < 3:
        send(
            chat_id,
            "❌ روی بازیکن لول ۱ و ۲ نمی‌شود قرارداد جایزه گذاشت.",
            keypad=main_keypad(chat_id),
        )
        return
    open_on_target = [
        b
        for b in game.get("bounty_contracts", [])
        if b.get("status") == "open" and b.get("target") == target_id
    ]
    if len(open_on_target) >= 3:
        send(
            chat_id,
            "❌ روی این هدف همین الان ۳ قرارداد فعال هست.",
            keypad=main_keypad(chat_id),
        )
        return
    today = today_key()
    made_today = sum(
        1
        for b in game.get("bounty_contracts", [])
        if b.get("creator") == chat_id
        and str(b.get("created_at", "")).startswith(today)
    )
    if made_today >= 2:
        send(
            chat_id,
            "❌ سقف امروزت پر شده؛ روزی ۲ قرارداد بیشتر نمی‌شود.",
            keypad=main_keypad(chat_id),
        )
        return
    p = get_player(chat_id)
    if not has_resources(p, reward):
        send(
            chat_id,
            T("errors.not_enough_res", need=fmt_res_shortage(reward, p)),
            keypad=main_keypad(chat_id),
        )
        return
    pay_cost(p, reward)
    bid = int(game.get("next_bounty_id", 1))
    game["next_bounty_id"] = bid + 1
    b = {
        "id": bid,
        "creator": chat_id,
        "target": target_id,
        "reward": reward,
        "status": "open",
        "created_at": iso(now()),
        "expires_at": iso(now() + timedelta(hours=12)),
        "anonymous": False,
    }
    game.setdefault("bounty_contracts", []).append(b)
    p.setdefault("stats", {})["bounty_created"] = (
        int(p.get("stats", {}).get("bounty_created", 0)) + 1
    )
    game.get("chat_states", {}).pop(chat_id, None)
    save_game()
    msg = f"🎯 قرارداد جایزه ثبت شد!\n━━━━━━━━━━━━\nهدف: {player_name(target_id)}\nجایزه: {fmt_res_dict(reward)}\n\nهرکس تا ۱۲ ساعت آینده هدف را با غارت موفق بزند، جایزه را می‌گیرد."
    send(chat_id, msg, keypad=main_keypad(chat_id))
    send_group_radio(
        f"🎯 اسم روی دیوار\nبرای زدن {player_name(target_id)} جایزه گذاشتن:\n{fmt_res_dict(reward)}\n\nاگه {player_name(target_id)} امشب راحت خوابید، یعنی شهر مرده.",
        force=True,
        reason="bounty_created",
    )


def handle_my_bounties(chat_id: str) -> None:
    expire_bounty_contracts()
    rows = []
    lines = []
    for b in [
        x
        for x in game.get("bounty_contracts", [])
        if x.get("creator") == chat_id and x.get("status") == "open"
    ]:
        left = fmt_cd((fromiso(b.get("expires_at"), now()) - now()).total_seconds())
        lines.append(
            f"#{b['id']} — هدف: {player_name(b.get('target'))}\nجایزه: {fmt_res_dict(b.get('reward', {}))}\n⏳ {left}\nبرای لغو: لغو جایزه #{b['id']}"
        )
        rows.append([f"لغو جایزه #{b['id']}"])
    rows.append([B("bounty_board"), B("main_menu")])
    send(
        chat_id,
        "📜 قراردادهای جایزه من\n━━━━━━━━━━━━\n"
        + ("\n\n".join(lines) if lines else "قرارداد فعال نداری."),
        keypad=make_keypad(rows),
    )


def handle_cancel_bounty(chat_id: str, text: str) -> None:
    bid = safe_int(re.sub(r"\D+", "", text), -1)
    b = next(
        (
            x
            for x in game.get("bounty_contracts", [])
            if int(x.get("id", -1)) == bid
            and x.get("creator") == chat_id
            and x.get("status") == "open"
        ),
        None,
    )
    if not b:
        send(chat_id, "❌ قرارداد پیدا نشد.", keypad=main_keypad(chat_id))
        return
    b["status"] = "cancelled"
    p = get_player(chat_id)
    for r, q in b.get("reward", {}).items():
        add_amount(p, r, int(q))
    save_game()
    send(
        chat_id, f"✅ قرارداد #{bid} لغو شد و جایزه برگشت.", keypad=main_keypad(chat_id)
    )


def complete_bounty_contracts(hunter_id: str, target_id: str) -> None:
    expire_bounty_contracts()
    paid_any = False
    for b in game.get("bounty_contracts", []):
        if (
            b.get("status") == "open"
            and b.get("target") == target_id
            and b.get("creator") != hunter_id
        ):
            b["status"] = "claimed"
            b["claimed_by"] = hunter_id
            b["claimed_at"] = iso(now())
            hunter = get_player(hunter_id)
            for r, q in b.get("reward", {}).items():
                add_amount(hunter, r, int(q))
            hunter.setdefault("stats", {})["bounty_claimed"] = (
                int(hunter.get("stats", {}).get("bounty_claimed", 0)) + 1
            )
            paid_any = True
            try:
                send(
                    hunter_id,
                    f"🏆 قرارداد جایزه انجام شد!\nهدف را زدی: {player_name(target_id)}\n\nجایزه پرداخت شد:\n{fmt_res_dict(b.get('reward', {}))}",
                    keypad=main_keypad(hunter_id),
                )
                send(
                    b.get("creator"),
                    f"✅ قرارداد جایزه‌ات انجام شد.\n{player_name(hunter_id)} هدف را زد: {player_name(target_id)}",
                    keypad=main_keypad(b.get("creator")),
                )
            except Exception:
                pass
            send_group_radio(
                f"🏆 قرارداد جایزه انجام شد!\n{player_name(hunter_id)} هدف را زد: {player_name(target_id)}\n\nجایزه پرداخت شد:\n{fmt_res_dict(b.get('reward', {}))}",
                force=True,
                reason="bounty_claimed",
            )
    if paid_any:
        save_game()


def handle_attack_menu(
    chat_id: str,
) -> None:  # override to add revenge and bounty buttons
    p = get_player(chat_id)
    passive_income(chat_id)
    finish_upgrades(p)
    recalc_power(p)
    extra_rows = [
        [B("revenge_menu"), B("bounty_board")],
        [B("bounty_create"), B("bounty_my")],
    ]
    if p.get("hp", 100) < 25:
        send(
            chat_id,
            T("raid.low_hp"),
            keypad=make_keypad(extra_rows + [[B("main_menu")]]),
        )
        return
    if cd_remaining(p, "raid") > 0:
        # Still show social combat options, because revenge may have separate cooldown.
        cd_text = T("raid.cooldown", time=fmt_cd(cd_remaining(p, "raid")))
    else:
        cd_text = ""
    if int(p.get("total_attack", 0)) <= 0:
        send(
            chat_id,
            T("raid.zero_attack"),
            keypad=make_keypad(extra_rows + [[B("main_menu")]]),
        )
        return
    candidates = raid_candidates(chat_id)
    rows = []
    bucket_lines = []
    for key, cfg in RAID_BUCKETS.items():
        targets = raid_bucket_targets(chat_id, key)
        button = B(cfg["button_key"])
        bucket_lines.append(
            T(
                "raid.bucket_line",
                button=button,
                title=cfg["title"],
                count=len(targets),
                loot=int(cfg["loot_mod"] * 100),
                risk="کم"
                if key == "weak"
                else ("معمولی" if key == "medium" else "زیاد"),
            )
        )
        rows.append([button])
    drone_count = int(p.get("inventory", {}).get("spy_drone", 0))
    direct_lines = []
    if drone_count > 0 and candidates:
        direct_targets = sorted(
            candidates, key=lambda x: raid_target_score(x[1]), reverse=True
        )[:12]
        for cid, rp in direct_targets:
            if is_shielded(rp):
                continue
            button = raid_target_button(rp.get("name"))
            direct_lines.append(
                T(
                    "raid.direct_line",
                    button=button,
                    name=display_name(rp.get("name")),
                    level=rp.get("level", 1),
                    defense=f"{rp.get('total_defense', 0):,}",
                    water=f"{rp.get('water', 0):,}",
                )
            )
            rows.append([button])
        drone_hint = T("raid.drone_available", count=drone_count)
    else:
        drone_hint = T("raid.drone_hint")
        direct_lines.append(drone_hint)
    rows = extra_rows + rows + [[B("main_menu")]]
    shield_hint = "\n📌 بازیکن‌های دارای محافظ از هدف‌های شانسی حذف می‌شوند."
    text = (
        T(
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
    send(chat_id, text, keypad=make_keypad(rows))


def alliance_keypad(chat_id: str) -> dict[str, Any]:  # override
    al = player_alliance(chat_id)
    if not al:
        return make_keypad(
            [[B("alliance_create"), B("alliance_list")], [B("main_menu")]]
        )
    rows = [
        [B("alliance_group_raid"), B("alliance_vault")],
        [B("territories"), B("alliance_missions")],
        [B("alliance_leave")],
    ]
    if al.get("owner") == chat_id:
        rows.insert(0, [B("alliance_manage")])
    rows.append([B("main_menu")])
    return make_keypad(rows)


def handle_alliance_menu(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, T("alliance.none"), keypad=alliance_keypad(chat_id))
        return

    ensure_alliance_missions(al)  # اگر مأموریت اتحاد داری

    lines = []
    for cid in al.get("members", []):
        mp = game["players"].get(cid)
        if mp:
            recalc_power(mp)
            lines.append(
                T(
                    "alliance.member_line",
                    name=mp.get("name"),
                    level=mp.get("level", 1),
                    water=mp.get("water", 0),
                    power=f"{mp.get('total_attack', 0) + mp.get('total_defense', 0):,}",
                )
            )

    # اطلاعات مناطق تصرف‌شده
    owned = [
        cfg["label"]
        for k, cfg in TERRITORIES.items()
        if game.get("territories", {}).get(k, {}).get("owner") == al.get("name")
    ]

    rv = al.setdefault("resource_vault", {})
    rv_text = (
        " | ".join(fmt_res_amount(r, q) for r, q in rv.items() if int(q) > 0) or "خالی"
    )

    send(
        chat_id,
        T(
            "alliance.view",
            name=al.get("name"),
            owner=player_name(al.get("owner")),
            mode=alliance_mode_text(al),
            count=len(al.get("members", [])),
            max_members=ALLIANCE_MAX,
            members="\n".join(lines),
            vault=al.get("vault", 0),
            shared=al.get("total_shared", 0),
            cartel_level=cartel_level(al),
            cartel_label=cartel_level_data(al).get("label"),
            perks=cartel_perks_text(al),
            next_cost=cartel_next_upgrade_cost(al) or T("alliance.max_level"),
        )
        + f"\n\n🏴 مناطق تصرف‌شده: {', '.join(owned) if owned else 'ندارد'}\n🏦 خزانه منابع: {rv_text}",
        keypad=alliance_keypad(chat_id),
    )


def alliance_power(al: dict[str, Any]) -> int:
    total = 0
    for cid in al.get("members", []):
        p = game.get("players", {}).get(cid)
        if p:
            recalc_power(p)
            total += int(p.get("total_attack", 0)) + int(p.get("total_defense", 0))
    return total


def handle_territories(chat_id: str) -> None:
    ensure_territories()
    al = player_alliance(chat_id)
    rows = []
    lines = []
    for k, cfg in TERRITORIES.items():
        data = game["territories"].get(k, {})
        owner = data.get("owner") or "بدون مالک"
        cd_left = 0
        if data.get("last_attack_at"):
            cd_left = max(
                0,
                6 * 3600
                - int(
                    (now() - fromiso(data.get("last_attack_at"), now())).total_seconds()
                ),
            )
        status = "آماده" if cd_left <= 0 else fmt_cd(cd_left)
        lines.append(
            f"{cfg['label']}\nمالک فعلی: {owner}\nپاداش روزانه: {cfg['reward_text']}\n⏳ قابل حمله: {status}"
        )
        if al:
            rows.append([TERRITORY_ATTACK_BUTTON[k]])
    rows.append([B("alliance"), B("main_menu")])
    send(
        chat_id,
        "🏴 مناطق قابل تصرف\n━━━━━━━━━━━━\n" + "\n\n".join(lines),
        keypad=make_keypad(rows),
    )


def handle_attack_territory(chat_id: str, text: str) -> None:
    key = next((k for k, b in TERRITORY_ATTACK_BUTTON.items() if text == b), None)
    if not key:
        return handle_territories(chat_id)
    al = player_alliance(chat_id)
    if not al:
        send(
            chat_id,
            "❌ فقط اعضای اتحاد می‌توانند برای تصرف منطقه حمله کنند.",
            keypad=main_keypad(chat_id),
        )
        return
    if len(al.get("members", [])) < 2:
        send(
            chat_id,
            "❌ برای حمله منطقه‌ای حداقل ۲ عضو در اتحاد لازم است.",
            keypad=alliance_keypad(chat_id),
        )
        return
    ensure_territories()
    data = game["territories"][key]
    cfg = TERRITORIES[key]
    if (
        data.get("last_attack_at")
        and (now() - fromiso(data.get("last_attack_at"), now())).total_seconds()
        < 6 * 3600
    ):
        left = (
            6 * 3600
            - (now() - fromiso(data.get("last_attack_at"), now())).total_seconds()
        )
        send(
            chat_id,
            f"⏳ این منطقه تازه جنگیده. زمان باقی‌مانده: {fmt_cd(left)}",
            keypad=alliance_keypad(chat_id),
        )
        return
    owned_count = sum(
        1
        for t in game.get("territories", {}).values()
        if t.get("owner") == al.get("name")
    )
    if data.get("owner") != al.get("name") and owned_count >= 2:
        send(
            chat_id,
            "❌ هر اتحاد همزمان حداکثر ۲ منطقه می‌تواند داشته باشد.",
            keypad=alliance_keypad(chat_id),
        )
        return
    old_owner_name = data.get("owner")
    attack = int(alliance_power(al) * random.uniform(0.75, 1.25))
    defense = int(cfg["base_def"])
    if old_owner_name and old_owner_name in game.get("alliances", {}):
        defense += int(alliance_power(game["alliances"][old_owner_name]) * 0.40)
    data["last_attack_at"] = iso(now())
    if attack > defense or not old_owner_name:
        data["owner"] = al.get("name")
        al.setdefault("stats", {})["territory_wins"] = (
            int(al.get("stats", {}).get("territory_wins", 0)) + 1
        )
        for cid in al.get("members", []):
            if cid in game.get("players", {}):
                game["players"][cid].setdefault("stats", {})["territory_wins"] = (
                    int(game["players"][cid].get("stats", {}).get("territory_wins", 0))
                    + 1
                )
        inc_alliance_mission(al, "capture_zone", 1)
        news = f"🏴 منطقه تصرف شد!\nاتحاد {al.get('name')} منطقه {cfg['label']} را گرفت.\nپاداش روزانه: {cfg['reward_text']}"
        add_news(news, important=True)
        if old_owner_name:
            send_group_radio(
                f"🔥 منطقه سقوط کرد\n{old_owner_name} نتونست {cfg['label']} رو نگه داره.\n{al.get('name')} اومد، زد، برد.",
                force=True,
                reason="territory_taken",
            )
        else:
            send_group_radio(
                f"🏴 شهر عوض شد\nاتحاد {al.get('name')} منطقه {cfg['label']} رو گرفت.\nبقیه اتحادها فعلاً فقط دارن نقشه رو نگاه می‌کنن.",
                force=True,
                reason="territory_taken",
            )
        msg = f"🏴 منطقه تصرف شد!\n━━━━━━━━━━━━\nاتحاد {al.get('name')} منطقه {cfg['label']} را گرفت.\n\nقدرت حمله: {fmt_num(attack)}\nدفاع منطقه: {fmt_num(defense)}\n\nپاداش روزانه:\n{cfg['reward_text']}"
    else:
        msg = f"💀 حمله منطقه‌ای شکست خورد!\n━━━━━━━━━━━━\nمنطقه: {cfg['label']}\nقدرت حمله اتحاد: {fmt_num(attack)}\nدفاع منطقه: {fmt_num(defense)}"
    save_game()
    send(chat_id, msg, keypad=alliance_keypad(chat_id))


def award_territory_daily() -> None:
    ensure_territories()
    today = today_key()
    if game.get("last_territory_reward_day") == today:
        return

    changed = False
    for key, data in list(game.get("territories", {}).items()):
        if data.get("last_reward_day") == today or not data.get("owner"):
            continue

        al_name = data.get("owner")
        al = game.get("alliances", {}).get(al_name)
        cfg = TERRITORIES.get(key)

        if not al or not cfg:
            data["owner"] = None
            changed = True
            continue

        members = [
            cid for cid in al.get("members", []) if cid in game.get("players", {})
        ]
        if not members:
            continue

        if cfg.get("reward"):
            for cid in members:
                for r, q in cfg["reward"].items():
                    add_amount(game["players"][cid], r, int(q))
            changed = True

        if cfg.get("reward_random"):
            rr = cfg["reward_random"]
            picks = random.sample(members, min(int(rr.get("count", 1)), len(members)))
            for cid in picks:
                add_amount(game["players"][cid], "battery", int(rr.get("battery", 1)))
            changed = True

        data["last_reward_day"] = today
        changed = True

        # ✅ خبر را اینجا بفرست، جایی که cfg قطعاً مقدار دارد
        add_news(
            f"🏴 پاداش روزانه منطقه {cfg['label']} به اتحاد {al.get('name')} رسید."
        )

    if changed:
        game["last_territory_reward_day"] = today
        save_game()


def ensure_alliance_missions(al: dict[str, Any]) -> list[dict[str, Any]]:
    if al.get("mission_day") != today_key() or not isinstance(
        al.get("alliance_missions"), list
    ):
        al["mission_day"] = today_key()
        al["alliance_missions"] = []
        for tpl in ALLIANCE_MISSION_TEMPLATES:
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


def inc_alliance_mission(
    al: Optional[dict[str, Any]], key: str, amount: int = 1
) -> None:
    if not al:
        return
    missions = ensure_alliance_missions(al)
    for m in missions:
        if m.get("key") == key and not m.get("claimed"):
            m["progress"] = min(
                int(m.get("goal", 1)), int(m.get("progress", 0)) + int(amount)
            )


def inc_alliance_mission_for_player(chat_id: str, key: str, amount: int = 1) -> None:
    al = player_alliance(chat_id)
    if not al:
        return
    mapping = {"scavenge": "alliance_scavenge", "barter": "alliance_barter"}
    if key in mapping:
        inc_alliance_mission(al, mapping[key], amount)


def inc_mission(chat_id: str, key: str, amount: int = 1) -> None:  # override
    _orig_inc_mission(chat_id, key, amount)
    inc_alliance_mission_for_player(chat_id, key, amount)


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
            lines.append(f"خزانه منابع: {fmt_res_amount(res, v)}")
        elif k == "member_cache_medium":
            for cid in al.get("members", []):
                add_cache_to_player(cid, "medium", v)
            lines.append(f"📦 صندوق متوسط × {v} برای اعضا")
        elif k == "season_points":
            al["season_points"] = int(al.get("season_points", 0)) + v
            lines.append(f"امتیاز اتحاد +{v}")
    m["claimed"] = True
    m["claimed_at"] = iso(now())
    send_group_radio(
        f"🤝 کارتل بیدار شد\nاتحاد {al.get('name')} یک مأموریت اتحاد را کامل کرد: {m.get('title')}",
        force=True,
        reason="alliance_mission",
    )
    return " + ".join(lines) if lines else "—"


def handle_alliance_missions(chat_id: str) -> None:
    al = player_alliance(chat_id)
    if not al:
        send(chat_id, "❌ عضو اتحادی نیستی.", keypad=main_keypad(chat_id))
        return
    missions = ensure_alliance_missions(al)
    receipts = []
    lines = []
    for m in missions:
        ready = int(m.get("progress", 0)) >= int(m.get("goal", 1))
        if ready and not m.get("claimed"):
            receipts.append(
                f"• {m.get('title')}: {claim_alliance_mission_reward(al, m)}"
            )
        icon = "✅" if m.get("claimed") else ("🎁" if ready else "⬜")
        status = (
            "دریافت شد"
            if m.get("claimed")
            else ("آماده دریافت" if ready else "در حال انجام")
        )
        lines.append(
            f"{icon} {m.get('title')}\nپیشرفت: {m.get('progress', 0)}/{m.get('goal', 1)}\nوضعیت: {status}\n🎁 پاداش: {fmt_any_reward(m.get('reward', {}))}"
        )
    note = "\n\n✅ پاداش‌های واریزشده:\n" + "\n".join(receipts) if receipts else ""
    save_game()
    send(
        chat_id,
        "🤝 مأموریت‌های اتحاد امروز\n━━━━━━━━━━━━\n" + "\n\n".join(lines) + note,
        keypad=alliance_keypad(chat_id),
    )


def pick_group_radio_subject() -> dict[str, Any]:
    players = [
        (cid, p)
        for cid, p in game.get("players", {}).items()
        if p.get("registered") and not p.get("banned")
    ]
    if not players:
        return {"type": "rumor"}
    bounties = [
        b for b in game.get("bounty_contracts", []) if b.get("status") == "open"
    ]
    if bounties and random.random() < 0.18:
        b = random.choice(bounties)
        return {
            "type": "bounty",
            "target": b.get("target"),
            "reward": b.get("reward", {}),
        }
    shielded = [(cid, p) for cid, p in players if is_shielded(p)]
    if shielded and random.random() < 0.14:
        cid, p = random.choice(shielded)
        return {"type": "shielded", "player": cid}
    rich = [
        (cid, p)
        for cid, p in players
        if int(p.get("water", 0)) >= 500 and not is_shielded(p)
    ]
    if rich and random.random() < 0.16:
        cid, p = max(rich, key=lambda x: int(x[1].get("water", 0)))
        return {"type": "rich_unshielded", "player": cid, "water": p.get("water", 0)}
    rows = ranked_players()
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
        and random.random() < 0.18
    ):
        return {"type": "victim", "player": victims[0][0]}
    low = rows[-1][0] if rows else random.choice(players)[0]
    if random.random() < 0.20:
        return {"type": "low_rank", "player": low}
    active_alliances = [
        al
        for al in game.get("alliances", {}).values()
        if isinstance(al, dict) and al.get("members")
    ]
    if active_alliances and random.random() < 0.15:
        al = max(
            active_alliances,
            key=lambda a: int(a.get("vault", 0)) + len(a.get("members", [])) * 100,
        )
        return {"type": "alliance", "alliance": al}
    return {"type": "inactive", "player": random.choice(players)[0]}


def render_group_radio_v2(subject: dict[str, Any]) -> str:
    typ = subject.get("type")
    if typ == "low_rank":
        return f"🐀 گزارش کف جدول\n{player_name(subject['player'])} هنوز ته جدوله، ولی حداقل هنوز نفس می‌کشه.\nدو تا گشت، یه معاوضه درست، شاید از زیر خاک بیاد بیرون."
    if typ == "inactive":
        return f"📻 رادیوی زباله‌زار\n{player_name(subject['player'])} امروز اونقدر ساکت بوده که موش‌های گاراژش فکر کردن صاحب نداره."
    if typ == "top_rank":
        return f"👑 تاج روی سر {player_name(subject['player'])} فعلاً مونده.\nولی تو این شهر، تاج بیشتر شبیه هدف تیراندازیه تا افتخار."
    if typ == "chaser":
        return f"📡 هشدار رشد\n{player_name(subject['player'])} فقط {fmt_num(subject.get('gap', 0))} امتیاز تا تاج فاصله داره.\nیکی باید جلوشو بگیره، یا خودش بقیه رو می‌گیره."
    if typ == "rich_unshielded":
        return f"💧 بوی آب پیچیده\n{player_name(subject['player'])} با {fmt_num(subject.get('water', 0))} آب بدون محافظ نشسته.\nغارتگرها لازم نیست زرنگ باشن؛ فقط باید بیدار باشن."
    if typ == "shielded":
        return f"🛡️ ترس یا عقل؟\n{player_name(subject['player'])} محافظ روشن کرد.\nبعضیا میگن ترسیده، بعضیا میگن حداقل مغز داره."
    if typ == "victim":
        return f"🚨 قربانی روز\n{player_name(subject['player'])} بیشتر از درِ زنگ‌زده کتک خورده.\nدکمه انتقام برای قشنگی نیست."
    if typ == "bounty":
        return f"🎯 اسم روی دیوار\nبرای زدن {player_name(subject.get('target'))} جایزه گذاشتن:\n{fmt_res_dict(subject.get('reward', {}))}\n\nحالا ببینیم شهر هنوز دندون داره یا نه."
    if typ == "alliance":
        al = subject.get("alliance", {})
        return f"🤝 کارتل بیدار شد\nاتحاد {al.get('name')} امروز بیشتر از بقیه صدا داده.\nبقیه اتحادها فعلاً بیشتر شبیه گروه چت‌اند تا کارتل."
    return group_radio_rumor_text()


def group_radio_periodic_text() -> str:  # override
    boss = active_boss()
    if boss and random.random() < 0.35:
        return group_radio_boss_status_text(boss)
    return render_group_radio_v2(pick_group_radio_subject())


def periodic_group_radio() -> (
    None
):  # override: includes smuggler and territories daily ticks
    maybe_setup_night_smuggler()
    award_territory_daily()
    _orig_periodic_group_radio()


def season_special_awards(rows: list[tuple[str, int]]) -> list[str]:
    awards = []
    players = [(cid, game["players"][cid]) for cid, _ in rows]

    def best_by(stat, title):
        cand = [(cid, int(p.get("stats", {}).get(stat, 0))) for cid, p in players]
        cand = [x for x in cand if x[1] > 0]
        if cand:
            cid, val = max(cand, key=lambda x: x[1])
            awards.append(f"{title}: {player_name(cid)} ({fmt_num(val)})")
            return cid

    best_by("scavenges", "فعال‌ترین گشت‌زن")
    # trader score combines market and barter.
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
        awards.append(f"بهترین تاجر/معاوضه‌گر: {player_name(cid)} ({fmt_num(val)})")
    best_by("boss_damage", "بیشترین آسیب به باس")
    best_by("alliance_shared", "بیشترین کمک به اتحاد")
    best_by("revenge_wins", "بیشترین انتقام موفق")
    best_by("bounty_claimed", "بیشترین قرارداد جایزه انجام‌شده")
    # Newcomer: highest score among first-season players.
    newcomers = [
        (cid, score)
        for cid, score in rows
        if int(game["players"][cid].get("career", {}).get("seasons_played", 0)) <= 0
    ]
    if newcomers:
        awards.append(f"بهترین تازه‌وارد سیزن: {player_name(newcomers[0][0])}")
    return awards


# def maybe_roll_season() -> None:  # override enhanced season prizes
#     season = game.get("season") or default_season(1)
#     if fromiso(season.get("end"), now()) > now():
#         return
#     rows = ranked_players()
#     winners_lines = []
#     archive_rows = []
#     special_awards = season_special_awards(rows)
#     prizes = {
#         1: {
#             "title": "پادشاه زباله",
#             "frame": "طلایی",
#             "cache": ("legendary", 1),
#             "start_bonus": 0.10,
#             "line": "👑 قهرمان سیزن",
#         },
#         2: {
#             "title": "قصاب نقره‌ای",
#             "frame": "نقره‌ای",
#             "cache": ("military", 2),
#             "start_bonus": 0.07,
#             "line": "🥈 قصاب نقره‌ای",
#         },
#         3: {
#             "title": "بازمانده برنزی",
#             "frame": "برنزی",
#             "cache": ("military", 1),
#             "start_bonus": 0.05,
#             "line": "🥉 بازمانده برنزی",
#         },
#     }
#     top_prize_cache: dict[str, tuple[str, int]] = {}
#     top_bonus: dict[str, float] = {}
#     for i, (cid, score) in enumerate(rows[:10], start=1):
#         p = game["players"][cid]
#         if i in prizes:
#             pr = prizes[i]
#             p.setdefault("season_titles", [])
#             if pr["title"] not in p["season_titles"]:
#                 p["season_titles"].append(pr["title"])
#             p.setdefault("profile_frames", [])
#             if pr["frame"] not in p["profile_frames"]:
#                 p["profile_frames"].append(pr["frame"])
#             top_prize_cache[cid] = pr["cache"]
#             top_bonus[cid] = pr["start_bonus"]
#             prize_line = f"{pr['line']} — {CACHE_TYPES[pr['cache'][0]]['label']} × {pr['cache'][1]} — شروع فصل بعد +{int(pr['start_bonus'] * 100)}٪ کیت شروع"
#         else:
#             p["honor"] = int(p.get("honor", 0)) + 50
#             top_prize_cache[cid] = ("medium", 1)
#             prize_line = "🏅 مدال ده نفر برتر — 📦 صندوق متوسط × ۱ + افتخار دائمی"
#         winners_lines.append(
#             f"{i}. {display_name(p.get('name'))} — {fmt_num(score)} امتیاز\n   {prize_line}"
#         )
#         archive_rows.append(
#             {"rank": i, "chat_id": cid, "name": p.get("name"), "score": score}
#         )
#     old_id = int(season.get("id", 1))
#     new_id = old_id + 1
#     old_archive = {
#         "id": old_id,
#         "ended_at": iso(now()),
#         "winners": archive_rows,
#         "special_awards": special_awards,
#     }
#     preserved = {}
#     for cid, p in game["players"].items():
#         rank = next((i for i, (x, _) in enumerate(rows, start=1) if x == cid), None)
#         score = season_score(cid) if p.get("registered") else 0
#         np = new_player(p.get("name") or "", cid)
#         np["registered"] = p.get("registered", bool(p.get("name")))
#         for field in [
#             "ref_code",
#             "referrals_count",
#             "referral_used",
#             "referred_by",
#             "season_titles",
#             "profile_frames",
#         ]:
#             if field in p:
#                 np[field] = p.get(field)
#         np["career"] = p.get(
#             "career", {"seasons_played": 0, "best_rank": None, "best_score": 0}
#         )
#         if p.get("registered"):
#             np["career"]["seasons_played"] = (
#                 int(np["career"].get("seasons_played", 0)) + 1
#             )
#             if rank and (
#                 np["career"].get("best_rank") is None
#                 or rank < np["career"].get("best_rank")
#             ):
#                 np["career"]["best_rank"] = rank
#             if score > int(np["career"].get("best_score", 0)):
#                 np["career"]["best_score"] = score
#         bonus = float(top_bonus.get(cid, 0) or p.get("next_start_bonus_pct", 0) or 0)
#         if bonus:
#             np["water"] += int(np["water"] * bonus)
#             for r in RESOURCES:
#                 np["resources"][r] += int(np["resources"].get(r, 0) * bonus)
#         preserved[cid] = np
#     game["players"] = preserved
#     for cid, (ctype, qty) in top_prize_cache.items():
#         if cid in game["players"]:
#             add_cache_to_player(cid, ctype, qty)
#     game["alliances"] = {}
#     game["market_orders"] = []
#     game["barter_orders"] = []
#     game["resource_rentals"] = []
#     game["bounty_contracts"] = []
#     game["revenge_targets"] = []
#     game["next_order_id"] = 1
#     game["next_barter_id"] = 1
#     game["next_rental_id"] = 1
#     game["world_event_active"] = None
#     game["territories"] = {
#         k: {"owner": None, "last_attack_at": None, "last_reward_day": None}
#         for k in TERRITORIES
#     }
#     archives = list(season.get("archives", []))[-5:] + [old_archive]
#     game["season"] = default_season(new_id)
#     game["season"]["archives"] = archives
#     winners_text = "\n".join(winners_lines) or "بدون بازیکن"
#     end_msg = f"""🏁 <b>پایان سیزن {old_id} — حماسه آخرالزمان</b>

#     🔥 <b>برترین‌های این فصل:</b>
#     {winners_text}

#     👑 <b>تالار مشاهیر</b> به‌روزرسانی شد.

#     سیزن <b>{new_id}</b> آغاز شد.
#     شهر دوباره منتظر <i>حماسه</i> است..."""

#     meta = [
#         {"type": "Bold", "from_index": 0, "length": 40},
#         {"type": "Bold", "from_index": end_msg.find("برترین‌های"), "length": 18},
#         {"type": "Bold", "from_index": end_msg.find("تالار مشاهیر"), "length": 15},
#     ]

#     for cid, p in game["players"].items():
#         if p.get("registered"):
#             send(cid, end_msg, keypad=main_keypad(cid), meta_data=meta)
#     send_group_radio(end_msg, force=True, reason="season_end")
#     save_game()


def handle_state(
    chat_id: str, text: str, sender_id: str = ""
) -> bool:  # override state handler
    st = game.get("chat_states", {}).get(chat_id)
    if st:
        state = st.get("state")
        if state == "awaiting_smuggler_qty":
            handle_smuggler_qty(chat_id, text)
            return True
        if state == "awaiting_bounty_order":
            handle_create_bounty(chat_id, text)
            return True
    return _orig_handle_state(chat_id, text, sender_id)


def dispatch(
    chat_id: str, text: str, sender_name: str, button_id: str = "", sender_id: str = ""
) -> None:  # override dispatcher for new buttons
    text = (text or button_id or "").strip()
    # Let original registration flow handle unregistered users.
    if not game.get("players", {}).get(chat_id, {}).get("registered"):
        return _orig_dispatch(chat_id, text, sender_name, button_id, sender_id)
    expire_bounty_contracts()
    expire_revenge_targets()
    maybe_setup_night_smuggler()
    if handle_state(chat_id, text, sender_id):
        return
    if text == B("night_smuggler"):
        return handle_night_smuggler(chat_id)
    if text in NIGHT_SMUGGLER_BUY_BUTTON.values():
        return handle_smuggler_select(chat_id, text)
    if text in CACHE_OPEN_BUTTON.values():
        return handle_open_cache_type(chat_id, text)
    if text in USE_ITEM_BUTTON.values():
        return handle_use_consumable(chat_id, text)
    if text == B("revenge_menu"):
        return handle_revenge_menu(chat_id)
    if text.startswith("🔥 انتقام #"):
        return handle_revenge_attack(chat_id, text)
    if text == B("bounty_board"):
        return handle_bounty_board(chat_id)
    if text == B("bounty_create"):
        return handle_create_bounty_prompt(chat_id)
    if text == B("bounty_my"):
        return handle_my_bounties(chat_id)
    if text.startswith("لغو جایزه #"):
        return handle_cancel_bounty(chat_id, text)
    if text == B("territories"):
        return handle_territories(chat_id)
    if text in TERRITORY_ATTACK_BUTTON.values():
        return handle_attack_territory(chat_id, text)
    if text == B("alliance_missions"):
        return handle_alliance_missions(chat_id)
    return _orig_dispatch(chat_id, text, sender_name, button_id, sender_id)


# ══════════════════════════════════════════════════════
#  UX PATCH: SAFE STATE ESCAPE + CLEAN MAIN MENU
# ══════════════════════════════════════════════════════
# این لایه دو مشکل UX را حل می‌کند:
# ۱) بازیکن اگر وسط هر ورودی متنی گیر کرد، با هر دکمه اصلی از state خارج می‌شود.
# ۲) «↩️ منوی اصلی» دیگر پروفایل را باز نمی‌کند؛ یک صفحه خانه مرتب با دسترسی سریع می‌دهد.

_ux_prev_main_keypad = main_keypad
_ux_prev_dispatch = dispatch
_ux_prev_handle_state = handle_state


def ux_global_nav_buttons() -> set[str]:
    """دکمه‌هایی که باید از هر state متنی بیرون بزنند و همان صفحه را باز کنند."""
    keys = [
        "main_menu",
        "profile",
        "city_map",
        "scavenge",
        "market",
        "attack",
        "inventory",
        "craft",
        "buildings",
        "alliance",
        "leaderboard",
        "daily_missions",
        "daily",
        "open_cache",
        "season",
        "messages",
        "event",
        "help",
        "back_market",
        "world_boss",
        "news",
        "night_smuggler",
        "revenge_menu",
        "bounty_board",
        "territories",
        "alliance_missions",
        "admin_panel",
    ]
    vals = {B(k) for k in keys if B(k) and not B(k).startswith("buttons.")}
    vals.update(
        {"/start", "start", "شروع", "منو", "منوی اصلی", "لغو", "cancel", "Cancel"}
    )
    return vals


def clear_chat_state(chat_id: str) -> bool:
    """اگر کاربر در ورودی متنی گیر کرده باشد، state پاک می‌شود."""
    states = game.setdefault("chat_states", {})
    if chat_id in states:
        states.pop(chat_id, None)
        save_game()
        return True
    return False


def main_keypad(chat_id: Optional[str] = None, sender_id: str = "") -> dict[str, Any]:
    """منوی اصلی مرتب‌شده بر اساس کارهای پرتکرار و هاب‌های مهم."""
    rows = [
        [B("profile"), B("city_map")],  # هاب PvE
        [B("market"), B("attack")],  # اقتصاد + غارت
        [B("craft"), B("buildings")],  # ساخت و ساز
        [B("alliance"), B("inventory")],  # اتحاد + انبار
        [B("season"), B("leaderboard")],  # سیزن و رتبه
        [B("invite")],
        [B("help")],  # راهنما
    ]
    if chat_id and is_admin(chat_id, sender_id):
        rows.append([B("admin_panel")])
    return make_keypad(rows)


# ══════════════════════════════════════════════════════
#  HANDLERS: MAIN / PROFILE
# ══════════════════════════════════════════════════════
def fmt_short_num(value: Any) -> str:
    """Readable dashboard numbers; keeps profile/market exact numbers unchanged."""
    try:
        n = int(value)
    except Exception:
        return str(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    units = [
        (1_000_000_000_000, "تریلیون"),
        (1_000_000_000, "میلیارد"),
        (1_000_000, "میلیون"),
        (1_000, "هزار"),
    ]
    for base, label in units:
        if n >= base:
            x = n / base
            s = f"{x:.1f}" if x < 10 else f"{x:.0f}"
            s = s.rstrip("0").rstrip(".")
            return f"{sign}{s} {label}"
    return f"{sign}{n:,}"


def dashboard_cd_line(label: str, remaining: float) -> str:
    if remaining <= 0:
        return f"{label}: آماده ✅"
    return f"{label}: {fmt_cd(remaining)} ⏳"


def dashboard_hp_line(p: dict[str, Any]) -> str:
    hp = int(p.get("hp", 100))
    if hp <= 20:
        return f"❤️ نیروها: {hp}/100 🚨 بحرانی"
    if hp <= 45:
        return f"❤️ نیروها: {hp}/100 ⚠️ نیاز به درمان"
    if hp < 100:
        return f"❤️ نیروها: {hp}/100 🟡 زخمی"
    return "❤️ نیروها: 100/100 ✅ سالم"


def dashboard_mission_line(chat_id: str) -> str:
    missions = ensure_daily_missions(chat_id)
    if not missions:
        return "📜 مأموریت: امروز هنوز چیزی ثبت نشده"
    ready = sum(
        1
        for m in missions
        if int(m.get("progress", 0)) >= int(m.get("goal", 1)) and not m.get("claimed")
    )
    claimed = sum(1 for m in missions if m.get("claimed"))
    done = sum(
        1 for m in missions if int(m.get("progress", 0)) >= int(m.get("goal", 1))
    )
    total = len(missions)
    if ready:
        return f"📜 مأموریت: {ready} پاداش آماده دریافت 🎁"
    if claimed == total:
        return "📜 مأموریت: همه پاداش‌های امروز دریافت شد ✅"
    return f"📜 مأموریت: {done}/{total} تکمیل شده"


def dashboard_next_action(chat_id: str, p: dict[str, Any]) -> str:
    missions = ensure_daily_missions(chat_id)
    ready = any(
        int(m.get("progress", 0)) >= int(m.get("goal", 1)) and not m.get("claimed")
        for m in missions
    )
    if ready:
        return "اول برو 📜 مأموریت‌ها؛ پاداش آماده همان‌جا واریز می‌شود."
    if int(p.get("hp", 100)) <= 25:
        return (
            "نیروهات زخمی‌اند؛ قبل از غارت، از 🎒 انبار یا 🛠️ کارگاه برای درمان کمک بگیر."
        )
    if cd_remaining(p, "scavenge") <= 0:
        return "بهترین حرکت الان: 🗺️ گشت‌زنی برای لوت سریع."
    if cd_remaining(p, "raid") <= 0 and int(p.get("hp", 100)) >= 35:
        return "غارت آماده است؛ اگه ریسک می‌خوای برو ⚔️ غارت."
    return "فعلاً وقت اقتصاد و رشد است: ⚖️ بازار، 🛠️ کارگاه یا 🏗️ ساختمان‌ها."


def handle_main_menu(chat_id: str, sender_id: str = "") -> None:
    p = get_player(chat_id)
    passive_income(chat_id)
    finished = finish_upgrades(p)
    recalc_power(p)
    lv, xp, mx, label = level_info(p)
    sc_cd = cd_remaining(p, "scavenge")
    raid_cd = cd_remaining(p, "raid")
    shield_left = shield_remaining(p)
    shield_line = (
        f"🛡️ محافظ: فعال، {fmt_cd(shield_left)} باقی مانده"
        if shield_left > 0
        else "🛡️ محافظ: خاموش ❌"
    )
    cache_count = int(p.get("loot_caches", 0))
    cache_line = (
        f"🎁 صندوق: {cache_count} آماده بازکردن"
        if cache_count > 0
        else "🎁 صندوق: فعلاً نداری"
    )
    upgrade_line = ""
    if finished:
        names = []
        for u in finished[:2]:
            bk = u.get("bldg")
            if bk in BUILDINGS:
                names.append(f"{BUILDINGS[bk]['label']} سطح {u.get('to_level')}")
        if names:
            more = " و ..." if len(finished) > 2 else ""
            upgrade_line = f"\n🏗️ تکمیل شد: {'، '.join(names)}{more}"

    status_lines = [
        dashboard_cd_line("🗺️ گشت", sc_cd),
        dashboard_cd_line("⚔️ غارت", raid_cd),
        dashboard_hp_line(p),
        shield_line,
        cache_line,
        dashboard_mission_line(chat_id),
    ]
    if current_event():
        ev = current_event()
        status_lines.append(f"🌪️ رویداد: {ev.get('title')}")

    text = (
        "🏚️ پناهگاه مرکزی سندیکا\n"
        "━━━━━━━━━━━━\n"
        f"👤 {display_name(p.get('name', 'بی‌نام'))}\n"
        f"🏷️ {label} — سطح {lv} | ⭐ {xp}/{mx}\n"
        f"💧 خزانه: {fmt_short_num(p.get('water', 0))} | "
        f"🎖️ افتخار: {int(p.get('honor', 0)):+d}\n"
        f"⚔️ حمله: {fmt_short_num(p.get('total_attack', 0))} | "
        f"🛡️ دفاع: {fmt_short_num(p.get('total_defense', 0))}"
        f"{upgrade_line}\n"
        "━━━━━━━━━━━━\n"
        "🚦 وضعیت الان\n"
        + "\n".join(f"• {line}" for line in status_lines)
        + "\n━━━━━━━━━━━━\n"
        "🎯 پیشنهاد سیستم\n"
        f"{dashboard_next_action(chat_id, p)}\n"
        "━━━━━━━━━━━━\n"
        "🧭 مسیرها\n"
        "• اکشن: 🗺️ گشت‌زنی / ⚔️ غارت / 🗺️ نقشه شهر\n"
        "• اقتصاد: ⚖️ بازار / 🎒 انبار / 🎁 صندوق‌ها\n"
        "• رشد: 🛠️ کارگاه / 🏗️ ساختمان‌ها\n"
        "• رقابت: 🤝 اتحاد / 🏆 رتبه / ⏳ سیزن\n"
        "━━━━━━━━━━━━\n"
        "↩️ منوی اصلی، هر عملیات نیمه‌کاره را لغو می‌کند."
    )

    meta = build_meta_bold(
        text,
        [
            "پناهگاه مرکزی سندیکا",
            "خزانه:",
            "افتخار:",
            "حمله:",
            "دفاع:",
        ],
    )

    save_game()
    send(chat_id, text, keypad=main_keypad(chat_id, sender_id), meta_data=meta)


def handle_state(chat_id: str, text: str, sender_id: str = "") -> bool:  # UX override
    st = game.get("chat_states", {}).get(chat_id)
    if st and (text or "").strip() in ux_global_nav_buttons():
        clear_chat_state(chat_id)
        return False
    return _ux_prev_handle_state(chat_id, text, sender_id)


def dispatch(
    chat_id: str, text: str, sender_name: str, button_id: str = "", sender_id: str = ""
) -> None:  # UX override
    text = (text or button_id or "").strip()

    # ثبت‌نام state خودش را دارد؛ تا وقتی کاربر ثبت نشده، همان مسیر اصلی اجرا شود.
    if not game.get("players", {}).get(chat_id, {}).get("registered"):
        return _ux_prev_dispatch(chat_id, text, sender_name, button_id, sender_id)

    # منوی اصلی باید همیشه عملیات جاری را لغو کند و صفحه خانه را نشان دهد.
    if text in {B("main_menu"), "منو", "منوی اصلی", "لغو", "cancel", "Cancel"}:
        return handle_main_menu(chat_id, sender_id)

    # اگر کاربر وسط یک ورودی متنی، یکی از دکمه‌های اصلی را زد، اول state پاک شود؛ بعد همان دکمه اجرا شود.
    if game.get("chat_states", {}).get(chat_id) and text in ux_global_nav_buttons():
        clear_chat_state(chat_id)

    return _ux_prev_dispatch(chat_id, text, sender_name, button_id, sender_id)


# ══════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════
def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN env var is empty. Run with: BOT_TOKEN=... python waste_syndicate_bot.py"
        )
    load_texts()
    load_game()
    print("🛢️  سندیکای دلالان زباله v4 — SEASONAL LOCAL KEYPAD")
    game["next_offset_id"] = load_offset()
    if SKIP_PENDING_ON_START:
        skip_old_updates()
        game["next_offset_id"] = load_offset()
    if BOT_TOKEN == "PUT_YOUR_RUBIKA_BOT_TOKEN_HERE":
        print(
            "⚠️ BOT_TOKEN is not set. Edit the file or run: BOT_TOKEN=... python waste_syndicate_bot_v4_seasonal.py"
        )
    me = api("getMe")
    print("[getMe RAW]", me)
    bot = me.get("bot", {})
    print(f"   Bot: @{bot.get('username', '?')} | {bot.get('bot_title', '?')}")
    while True:
        try:
            maybe_roll_season()
            award_territory_daily()
            maybe_system_daily_restock()
            maybe_daily_event()
            maybe_spawn_boss(False)
            periodic_group_radio()
            payload = {"limit": 30}
            if game.get("next_offset_id"):
                payload["offset_id"] = game["next_offset_id"]
            resp = api("getUpdates", payload)
            if DEBUG:
                print("[getUpdates RAW]", resp)
            next_offset = resp.get("next_offset_id")
            if next_offset:
                game["next_offset_id"] = next_offset
                save_offset(next_offset)

            for raw_upd in resp.get("updates", []):
                process_update(raw_upd)
            save_game()
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            save_game()
            print("\nBot stopped.")
            break
        except Exception as e:
            print("[LOOP]", repr(e))
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

