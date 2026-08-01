def test_log_append_preserves_order(repos):
    repos["news_feed"].append({"text": "first"})
    repos["news_feed"].append({"text": "second"})

    feed = repos["news_feed"].list_all()

    assert [item["text"] for item in feed] == ["first", "second"]
    assert "seq" not in feed[0]  # internal ordering field, not leaked


def test_log_list_all_respects_limit(repos):
    for i in range(5):
        repos["news_feed"].append({"text": str(i)})

    latest_two = repos["news_feed"].list_all(limit=2)

    assert [item["text"] for item in latest_two] == ["3", "4"]


def test_meta_only_stores_known_scalar_keys(repos):
    repos["meta"].save(
        {
            "version": 4,
            "next_order_id": 7,
            "market_orders": [{"id": 1}],  # should be ignored — not a scalar key
        }
    )

    meta = repos["meta"].get()

    assert meta["version"] == 4
    assert meta["next_order_id"] == 7
    assert "market_orders" not in meta


def test_meta_increment_is_atomic_counter(repos):
    first = repos["meta"].increment("next_order_id")
    second = repos["meta"].increment("next_order_id")

    assert second == first + 1
