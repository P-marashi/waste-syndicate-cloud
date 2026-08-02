import os

# Must happen before anything imports bot_pkg (core/config.py reads
# BOT_TOKEN eagerly at import time).
os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("USE_MONGO", "0")
os.environ.setdefault("MONGO_DB", "waste_syndicate_test")

import mongomock
import pytest


@pytest.fixture
def db():
    """A fresh, isolated in-memory Mongo for each test — no real Mongo
    server needed. Swap `mongomock.MongoClient()` for a real
    `pymongo.MongoClient(...)` pointed at a test database to run the same
    tests against real Mongo.
    """
    client = mongomock.MongoClient()
    return client["waste_syndicate_test"]


@pytest.fixture
def repos(db):
    from bot_pkg.storage.collections import build_repositories

    return build_repositories(db, ensure_indexes=True)
