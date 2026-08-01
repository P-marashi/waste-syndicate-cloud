def test_add_and_get(repos):
    repos["market_orders"].add({"id": 1, "seller_id": "1", "resource": "scrap", "qty": 5})

    order = repos["market_orders"].get(1)

    assert order["resource"] == "scrap"
    assert order["qty"] == 5


def test_update_only_touches_given_fields(repos):
    repos["market_orders"].add(
        {"id": 1, "seller_id": "1", "resource": "scrap", "qty": 5, "status": "open"}
    )

    repos["market_orders"].update(1, {"status": "closed"})

    order = repos["market_orders"].get(1)
    assert order["status"] == "closed"
    assert order["qty"] == 5  # untouched


def test_delete(repos):
    repos["market_orders"].add({"id": 1, "resource": "scrap"})
    repos["market_orders"].delete(1)

    assert repos["market_orders"].get(1) is None


def test_list_all(repos):
    repos["market_orders"].add({"id": 1, "resource": "scrap"})
    repos["market_orders"].add({"id": 2, "resource": "plastic"})

    orders = repos["market_orders"].list_all()

    assert {o["id"] for o in orders} == {1, 2}


def test_replace_all_syncs_full_list_and_drops_removed_items(repos):
    """This is the transitional path used by save_game(): the whole
    in-memory list gets synced, items no longer present get deleted.
    """
    repos["market_orders"].replace_all(
        [{"id": 1, "resource": "scrap"}, {"id": 2, "resource": "plastic"}]
    )
    assert len(repos["market_orders"].list_all()) == 2

    # order #1 got fulfilled/removed from the in-memory list
    repos["market_orders"].replace_all([{"id": 2, "resource": "plastic", "qty": 9}])

    remaining = repos["market_orders"].list_all()
    assert len(remaining) == 1
    assert remaining[0]["id"] == 2
    assert remaining[0]["qty"] == 9
