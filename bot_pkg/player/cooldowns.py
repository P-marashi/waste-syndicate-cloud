from typing import Any

from ..services import player_service
from ..utils.datetime import fromiso, iso, now


def cd_remaining(p: dict[str, Any], key: str) -> float:
    if not p.get(f"{key}_cd"):
        return 0
    return player_service.seconds_until(fromiso(p[f"{key}_cd"], now()), now())


def set_cd(p: dict[str, Any], key: str, seconds: float) -> None:
    p[f"{key}_cd"] = iso(player_service.future_timestamp(now(), seconds))
