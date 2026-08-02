"""Redis connection singleton — same lazy/global-singleton shape as
`storage/database.py`'s `get_db()`, so the two storages read the same
way at a glance.

Redis here is for *ephemeral, non-authoritative* state only: things
that are fine to lose (chat_states, short-lived caches, rate-limit
timestamps). Anything a player would be upset to lose (resources,
buildings, XP, alliance membership) stays in Mongo through the
repositories in `storage/repositories/`. If you're about to put
player progress in Redis, it belongs in Mongo instead.
"""

from __future__ import annotations

import fnmatch

from ..registry import registry

_redis_client = None


class _InMemoryRedis:
    """Drop-in stand-in for `redis.Redis`, used when `USE_REDIS=0` or a
    real Redis server isn't reachable (e.g. local dev without
    `docker-compose up`). Only implements the subset of the API this
    project actually uses.

    Data does NOT survive a process restart — that's expected, since
    everything stored here is explicitly allowed to be ephemeral. This
    mirrors how `database.py` falls back to the local JSON file when
    Mongo is unavailable.
    """

    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    def setex(self, key, ttl, value):
        self._store[key] = value
        return True

    def delete(self, *keys):
        n = 0
        for k in keys:
            if self._store.pop(k, None) is not None:
                n += 1
        return n

    def exists(self, key):
        return 1 if key in self._store else 0

    def keys(self, pattern="*"):
        # Only supports the simple "prefix*" patterns actually used here.
        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    def ping(self):
        return True


def get_redis():
    """Return the shared Redis client, connecting (or falling back to
    the in-memory stand-in) on first use.
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    if not getattr(registry, "USE_REDIS", False):
        print("[REDIS] USE_REDIS=0 → in-memory fallback (dev only)")
        _redis_client = _InMemoryRedis()
        return _redis_client

    try:
        import redis

        client = redis.Redis.from_url(
            registry.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        client.ping()
        _redis_client = client
        print("✅ Connected to Redis")

    except Exception as e:
        print(f"[REDIS] connection failed ({e}) → in-memory fallback")
        _redis_client = _InMemoryRedis()

    return _redis_client


def reset_redis_client_for_tests() -> None:
    """Test-only escape hatch, mirrors the need `_repos_cache.clear()`
    fills for Mongo repositories in tests/conftest.py."""
    global _redis_client
    _redis_client = None
