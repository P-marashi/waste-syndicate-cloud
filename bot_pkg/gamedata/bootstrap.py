from bot_pkg.gamedata.bosses import (
    BOSS_ATTACK_CD,
    BOSS_DURATION,
    BOSS_MAX_INTERVAL,
    BOSS_MIN_INTERVAL,
    BOSS_SPAWN_EVERY,
    BOSS_TEMPLATES,
    MAX_BOSSES_PER_WEEK,
)
from bot_pkg.gamedata.buildings import BUILDINGS
from bot_pkg.gamedata.crafting import CRAFT_ITEMS, SPECIAL_EFFECT_TEXT
from bot_pkg.gamedata.events import DAILY_EVENTS
from bot_pkg.gamedata.legendary import LEGENDARY_ITEMS
from bot_pkg.gamedata.levels import (
    CARTEL_LEVELS,
    HONOR_TITLES,
    LEVELS,
    MAX_CARTEL_LEVEL,
)
from bot_pkg.gamedata.missions import DAILY_MISSION_TEMPLATES
from bot_pkg.gamedata.raid import COOLDOWNS, RAID_BUCKETS
from bot_pkg.gamedata.resources import (
    BASE_PRICE,
    RES_ALIASES,
    RES_ICON,
    RES_NAME,
    RESOURCES,
)
from bot_pkg.gamedata.zones import ZONES
from bot_pkg.registry import registry

registry.RESOURCES = RESOURCES
registry.RES_ICON = RES_ICON
registry.RES_NAME = RES_NAME
registry.RES_ALIASES = RES_ALIASES
registry.BASE_PRICE = BASE_PRICE

registry.CARTEL_LEVELS = CARTEL_LEVELS
registry.MAX_CARTEL_LEVEL = MAX_CARTEL_LEVEL
registry.LEVELS = LEVELS
registry.HONOR_TITLES = HONOR_TITLES

registry.ZONES = ZONES
registry.BUILDINGS = BUILDINGS

registry.CRAFT_ITEMS = CRAFT_ITEMS
registry.SPECIAL_EFFECT_TEXT = SPECIAL_EFFECT_TEXT

registry.LEGENDARY_ITEMS = LEGENDARY_ITEMS

registry.BOSS_SPAWN_EVERY = BOSS_SPAWN_EVERY
registry.BOSS_MIN_INTERVAL = BOSS_MIN_INTERVAL
registry.BOSS_MAX_INTERVAL = BOSS_MAX_INTERVAL
registry.MAX_BOSSES_PER_WEEK = MAX_BOSSES_PER_WEEK
registry.BOSS_DURATION = BOSS_DURATION
registry.BOSS_ATTACK_CD = BOSS_ATTACK_CD
registry.BOSS_TEMPLATES = BOSS_TEMPLATES

registry.DAILY_MISSION_TEMPLATES = DAILY_MISSION_TEMPLATES
registry.DAILY_EVENTS = DAILY_EVENTS

registry.COOLDOWNS = COOLDOWNS
registry.RAID_BUCKETS = RAID_BUCKETS
