import os
import random

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
