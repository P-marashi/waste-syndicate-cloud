"""save_game()/load_game() must behave exactly as before from the outside
— same registry.game dict shape — even though the underlying storage is
now split across real collections instead of one meta blob.
"""

import mongomock
import pytest


@pytest.fixture
def game_env(monkeypatch):
    from bot_pkg.registry import registry
    from bot_pkg.storage import collections as collections_module
    from bot_pkg.storage import persistence as persistence_module

    client = mongomock.MongoClient()
    fake_db = client["waste_syndicate_test"]

    # Both collections.py and persistence.py do `from .database import
    # get_db`, so the name is bound in *each* module's own namespace —
    # patch it in both places, not on database.py.
    monkeypatch.setattr(collections_module, "get_db", lambda: fake_db)
    monkeypatch.setattr(persistence_module, "get_db", lambda: fake_db)
    collections_module._repos_cache.clear()

    registry.USE_MONGO = True
    registry.game = {}

    yield registry

    collections_module._repos_cache.clear()


def test_save_then_load_roundtrips_players_and_lists(game_env):
    from bot_pkg.storage.persistence import load_game, save_game

    registry = game_env
    registry.game = {
        "version": 4,
        "players": {"1": {"name": "Ali", "level": 5, "resources": {"scrap": 10}}},
        "alliances": {},
        "market_orders": [{"id": 1, "seller_id": "1", "resource": "scrap", "qty": 3}],
        "barter_orders": [],
        "resource_rentals": [],
        "private_messages": [],
        "admin_logs": [],
        "news_feed": [{"text": "season started"}],
        "group_radio_log": [],
        "system_stock_log": [],
        "next_order_id": 2,
    }

    save_game()

    # simulate a fresh process: wipe the in-memory game and reload from db
    registry.game = {}
    from bot_pkg.storage.persistence import _load_game_mongo

    reloaded = _load_game_mongo()

    assert reloaded["players"]["1"]["name"] == "Ali"
    assert reloaded["players"]["1"]["level"] == 5
    assert reloaded["market_orders"][0]["resource"] == "scrap"
    assert reloaded["news_feed"][0]["text"] == "season started"
    assert reloaded["next_order_id"] == 2


def test_save_game_removes_deleted_order_from_next_load(game_env):
    from bot_pkg.storage.persistence import _load_game_mongo, save_game

    registry = game_env
    registry.game = {
        "version": 4,
        "players": {},
        "alliances": {},
        "market_orders": [
            {"id": 1, "resource": "scrap"},
            {"id": 2, "resource": "plastic"},
        ],
        "barter_orders": [],
        "resource_rentals": [],
        "private_messages": [],
        "admin_logs": [],
        "news_feed": [],
        "group_radio_log": [],
        "system_stock_log": [],
        "next_order_id": 3,
    }
    save_game()

    # order #1 got bought and removed from the in-memory list
    registry.game["market_orders"] = [{"id": 2, "resource": "plastic"}]
    save_game()

    reloaded = _load_game_mongo()
    assert [o["id"] for o in reloaded["market_orders"]] == [2]
