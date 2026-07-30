from datetime import timedelta
from typing import Any

from ..registry import registry


def cd_remaining(
    p: dict[str, Any],
    key: str,
) -> float:
    if not p.get(f"{key}_cd"):
        return 0

    return max(
        0,
        (
            registry.fromiso(
                p[f"{key}_cd"],
                registry.now(),
            )
            - registry.now()
        ).total_seconds(),
    )


def set_cd(
    p: dict[str, Any],
    key: str,
    seconds: float,
) -> None:
    p[f"{key}_cd"] = registry.iso(registry.now() + timedelta(seconds=int(seconds)))
