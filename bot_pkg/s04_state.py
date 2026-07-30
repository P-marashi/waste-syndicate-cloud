from typing import Any

from .registry import registry

registry.game: dict[str, Any] = {}
registry.LAST_SENDER_BY_CHAT: dict[str, str] = {}
