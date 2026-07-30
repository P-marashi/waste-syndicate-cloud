"""
Bootstrap Player Registry.

ثبت تمام توابع مربوط به مدیریت بازیکن در registry.

Core
----
- get_player
- player_name
- find_player_by_name

Progression
-----------
- honor_title
- level_info
- add_xp

Combat
------
- recalc_power
- shield_remaining
- is_shielded
- base_status_label

Cooldowns
---------
- cd_remaining
- set_cd

Buildings
---------
- apply_building_bonuses
- finish_upgrades
- upgrade_in_progress

Passive
-------
- passive_income

Events
------
- handle_event
"""

from ..registry import registry
from .buildings import apply_building_bonuses, finish_upgrades, upgrade_in_progress
from .combat import base_status_label, is_shielded, recalc_power, shield_remaining
from .cooldowns import cd_remaining, set_cd
from .core import find_player_by_name, get_player, player_name
from .events import handle_event
from .passive import passive_income
from .progression import add_xp, honor_title, level_info

registry.get_player = get_player
registry.player_name = player_name
registry.find_player_by_name = find_player_by_name

registry.honor_title = honor_title
registry.level_info = level_info
registry.add_xp = add_xp

registry.recalc_power = recalc_power
registry.shield_remaining = shield_remaining
registry.is_shielded = is_shielded
registry.base_status_label = base_status_label

registry.cd_remaining = cd_remaining
registry.set_cd = set_cd

registry.apply_building_bonuses = apply_building_bonuses
registry.finish_upgrades = finish_upgrades
registry.upgrade_in_progress = upgrade_in_progress

registry.passive_income = passive_income

registry.handle_event = handle_event
