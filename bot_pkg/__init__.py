"""Auto-generated package __init__.

Imports every split module IN ORIGINAL ORDER. Import order matters:
later modules intentionally overwrite names on `registry` that were
set by earlier modules (that's how the EXPANSION PATCH / UX PATCH
sections work).
"""

from . import (
    s01_config,  # noqa: F401
    s02_texts,  # noqa: F401
    s03_gamedata,  # noqa: F401
    s04_state,  # noqa: F401
    s05_utils,  # noqa: F401
    s06_persistence,  # noqa: F401
    s07_rubika_api,  # noqa: F401
    s08_player,  # noqa: F401
    s09_alliance_economy,  # noqa: F401
    s10_world_features,  # noqa: F401
    s11_market_core,  # noqa: F401
    s12_h_registration,  # noqa: F401
    s13_h_profile,  # noqa: F401
    s14_h_scavenge,  # noqa: F401
    s15_h_market,  # noqa: F401
    s16_h_buildings_craft,  # noqa: F401
    s17_h_raid_shield,  # noqa: F401
    s18_h_alliance,  # noqa: F401
    s19_h_misc,  # noqa: F401
    s20_h_messages,  # noqa: F401
    s21_h_admin,  # noqa: F401
    s22_dispatcher,  # noqa: F401
    s23_update_processing,  # noqa: F401
    s24_expansion_patch,  # noqa: F401
    s25_ux_patch,  # noqa: F401
    s26_h_profile,  # noqa: F401
    s27_main_loop,  # noqa: F401
)
from .registry import registry

__all__ = ["registry"]
