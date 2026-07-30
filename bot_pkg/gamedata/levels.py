CARTEL_LEVELS = {
    1: {
        "label": "دار و دسته محلی",
        "upgrade_cost": 0,
        "water_bonus": 0.0,
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
        "water_bonus": 0.1,
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
