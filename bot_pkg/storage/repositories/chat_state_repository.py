"""Redis-backed storage for ephemeral per-chat dispatcher state
(`awaiting_market_order`, `awaiting_admin_broadcast`, ...).

This used to live at `registry.game["chat_states"][chat_id]`, which
meant every single state transition triggered a full `save_game()` —
a resync of *every* collection (players, alliances, orders, logs...)
to Mongo, just to record that one chat is mid-way through typing a
market order.

Chat state is a near-perfect Redis fit: short-lived, per-chat, fine to
lose on a crash (the user just gets bounced back to the main menu and
tries again), and never needs a cross-chat query. A TTL is set so an
abandoned conversation (user opened "create order" and walked away)
clears itself instead of living forever in memory/DB.

Interface intentionally mirrors `PlayerRepository`
(`get` / `save` / `delete`) so it drops into existing call sites with
minimal churn.
"""

from __future__ import annotations

import json
from typing import Any

from ...infra.redis_client import get_redis

_PREFIX = "chat_state:"
_DEFAULT_TTL = 3600  # 1h of inactivity silently clears an in-progress flow


class ChatStateRepository:
    def __init__(self, redis_client=None, ttl: int = _DEFAULT_TTL):
        self._redis = redis_client or get_redis()
        self._ttl = ttl

    def _key(self, chat_id: str) -> str:
        return f"{_PREFIX}{chat_id}"

    def get(self, chat_id: str) -> dict[str, Any] | None:
        raw = self._redis.get(self._key(chat_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            # Corrupt/unexpected value — treat as "no state" rather than
            # crashing the dispatcher for this chat.
            return None

    def save(self, chat_id: str, state: dict[str, Any]) -> None:
        self._redis.setex(self._key(chat_id), self._ttl, json.dumps(state))

    def delete(self, chat_id: str) -> None:
        self._redis.delete(self._key(chat_id))

    def exists(self, chat_id: str) -> bool:
        return bool(self._redis.exists(self._key(chat_id)))
