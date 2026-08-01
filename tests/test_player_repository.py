def test_get_returns_none_for_missing_player(repos):
    assert repos["players"].get("12345") is None


def test_save_then_get_roundtrip(repos):
    repos["players"].save("12345", {"name": "Ali", "level": 3, "resources": {"scrap": 10}})

    player = repos["players"].get("12345")

    assert player["name"] == "Ali"
    assert player["level"] == 3
    assert player["resources"]["scrap"] == 10


def test_save_is_targeted_not_full_dump(repos):
    """Saving one player must not touch any other player's document —
    this is the whole point of moving off the meta-blob dump/load model.
    """
    repos["players"].save("1", {"name": "A", "level": 1})
    repos["players"].save("2", {"name": "B", "level": 1})

    repos["players"].save("1", {"name": "A", "level": 99})

    assert repos["players"].get("1")["level"] == 99
    assert repos["players"].get("2")["level"] == 1


def test_list_all_returns_dict_keyed_by_chat_id(repos):
    repos["players"].save("1", {"name": "A"})
    repos["players"].save("2", {"name": "B"})

    all_players = repos["players"].list_all()

    assert set(all_players.keys()) == {"1", "2"}
    assert all_players["1"]["name"] == "A"


def test_find_banned(repos):
    repos["players"].save("1", {"name": "A", "banned": False})
    repos["players"].save("2", {"name": "B", "banned": True})

    banned = repos["players"].find_banned()

    assert len(banned) == 1
    assert banned[0]["chat_id"] == "2"


def test_delete(repos):
    repos["players"].save("1", {"name": "A"})
    repos["players"].delete("1")

    assert repos["players"].get("1") is None
