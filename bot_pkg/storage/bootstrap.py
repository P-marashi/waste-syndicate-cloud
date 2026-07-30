"""
Bootstrap Storage Registry.

این فایل تمام توابع مربوط به ساخت، مهاجرت، دیتابیس و
ذخیره‌سازی بازی را داخل registry ثبت می‌کند.

Factories
---------
- default_season
- generate_ref_code
- new_player
- default_game

Migration
---------
- migrate_game

Database
--------
- get_db

Persistence
-----------
- load_game
- save_game

Usage
-----
from bot_pkg.storage.bootstrap import *
"""

from ..registry import registry
from .database import get_db
from .factories import default_game, default_season, generate_ref_code, new_player
from .migration import migrate_game
from .persistence import load_game, save_game

registry.default_season = default_season
registry.generate_ref_code = generate_ref_code
registry.new_player = new_player
registry.default_game = default_game

registry.migrate_game = migrate_game

registry.get_db = get_db

registry.load_game = load_game
registry.save_game = save_game
