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

Ephemeral state (Redis)
------------------------
- chat_state_repo

Usage
-----
from bot_pkg.storage.bootstrap import *
"""

from ..registry import registry
from ..infra.db import get_db
from .factories import default_game, default_season, generate_ref_code, new_player
from .migration import migrate_game
from .persistence import load_game, save_game
from .repositories.chat_state_repository import ChatStateRepository

registry.default_season = default_season
registry.generate_ref_code = generate_ref_code
registry.new_player = new_player
registry.default_game = default_game

registry.migrate_game = migrate_game

registry.get_db = get_db

registry.load_game = load_game
registry.save_game = save_game

# Transitional: legacy handlers (sXX_h_*.py) still reach through
# `registry`. New code should import ChatStateRepository directly
# instead of adding more to this object — see registry.py's docstring
# and INTEGRATION_GUIDE.md's registry sunset checklist.
registry.chat_state_repo = ChatStateRepository()
