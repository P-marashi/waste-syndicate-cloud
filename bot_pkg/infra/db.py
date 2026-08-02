# Deprecated re-export: kept only so any stray external import of
# META_SCALAR_KEYS doesn't hard-crash. The authoritative list now lives in
# repositories/meta_repository.py (SCALAR_KEYS) and collections.py
# (ID_LIST_KEYS / LOG_KEYS).
from ..registry import registry
from ..storage.repositories.meta_repository import SCALAR_KEYS as META_SCALAR_KEYS  # noqa: F401

_mongo_client = None
_db = None


def get_db():
    global _mongo_client, _db

    if _db is not None:
        return _db

    from pymongo import MongoClient

    _mongo_client = MongoClient(
        registry.MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    _db = _mongo_client[registry.MONGO_DB]

    from ..storage.collections import build_repositories

    build_repositories(_db, ensure_indexes=True)

    return _db
