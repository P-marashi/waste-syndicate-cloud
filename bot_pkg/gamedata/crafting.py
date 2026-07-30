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
        "cost": {
            "water": 900,
            "battery": 14,
            "copper": 22,
            "plastic": 18,
            "glass": 4,
        },
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
        "cost": {
            "water": 650,
            "battery": 8,
            "copper": 12,
            "plastic": 10,
            "glass": 6,
        },
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
