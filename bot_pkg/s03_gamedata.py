"""
Bootstrap Game Data Registry.

این فایل تمام داده‌های ثابت بازی را داخل `registry` ثبت می‌کند.

پس از import کردن این فایل، موارد زیر در دسترس خواهند بود:

Resources
---------
- RESOURCES
- RES_ICON
- RES_NAME
- RES_ALIASES
- BASE_PRICE

Levels
------
- LEVELS
- CARTEL_LEVELS
- MAX_CARTEL_LEVEL
- HONOR_TITLES

World
-----
- ZONES
- BUILDINGS

Crafting
--------
- CRAFT_ITEMS
- SPECIAL_EFFECT_TEXT
- LEGENDARY_ITEMS

Bosses
-------
- BOSS_TEMPLATES
- BOSS_SPAWN_EVERY
- BOSS_MIN_INTERVAL
- BOSS_MAX_INTERVAL
- MAX_BOSSES_PER_WEEK
- BOSS_DURATION
- BOSS_ATTACK_CD

Missions & Events
-----------------
- DAILY_MISSION_TEMPLATES
- DAILY_EVENTS

Combat
------
- COOLDOWNS
- RAID_BUCKETS

Usage
-----
from bot_pkg.gamedata.bootstrap import *
"""

from bot_pkg.gamedata.bootstrap import *
