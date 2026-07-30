# bot_pkg/features/bootstrap.py


# Import modules so their registry.xxx = ... side-effects run
from . import (
    alliance_group_raid,  # noqa: F401
    cache,  # noqa: F401
    group_radio,  # noqa: F401
    missions,  # noqa: F401
    news,  # noqa: F401
    season,  # noqa: F401
    utils,  # noqa: F401
    world_boss,  # noqa: F401
    world_events,  # noqa: F401
)
