from bot_pkg.services import market_service as m


# ---------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------


def test_reference_price_drops_as_supply_grows():
    low_supply = m.system_reference_price(100, supply=0)
    high_supply = m.system_reference_price(100, supply=200)
    assert high_supply < low_supply


def test_reference_price_clamped_to_0_65x_minimum():
    # absurdly high supply should still floor at 0.65x base
    price = m.system_reference_price(100, supply=100000)
    assert price >= int(100 * 0.65)


def test_reference_price_clamped_to_1_8x_maximum():
    price = m.system_reference_price(100, supply=0, all_prices_mod=10.0)
    assert price <= int(100 * 1.8) * 10  # mod applies after clamp, by design


def test_reference_price_never_below_1():
    price = m.system_reference_price(1, supply=1000)
    assert price >= 1


def test_buy_price_is_quarter_of_reference():
    assert m.system_buy_price(100) == 25


def test_sell_price_is_2_5x_reference():
    assert m.system_sell_price(100) == 250


def test_buy_and_sell_price_never_zero():
    assert m.system_buy_price(1) >= 1
    assert m.system_sell_price(0) >= 1


# ---------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------

RESOURCES = {"scrap", "plastic", "glass", "battery", "copper"}


def resolver(token: str) -> str | None:
    aliases = {"آهن": "scrap", "پلاستیک": "plastic", "شیشه": "glass"}
    return aliases.get(token)


def test_parse_resource_pairs_basic():
    result = m.parse_resource_pairs("آهن 5 پلاستیک 3", resolver, RESOURCES)
    assert result == {"scrap": 5, "plastic": 3}


def test_parse_resource_pairs_rejects_unknown_resource():
    assert m.parse_resource_pairs("طلا 5", resolver, RESOURCES) is None


def test_parse_resource_pairs_rejects_water():
    def resolver_with_water(token):
        return "water" if token == "آب" else resolver(token)

    assert m.parse_resource_pairs("آب 5", resolver_with_water, RESOURCES) is None


def test_parse_resource_pairs_rejects_missing_qty():
    assert m.parse_resource_pairs("آهن", resolver, RESOURCES) is None


def test_parse_resource_pairs_rejects_zero_or_negative_qty():
    assert m.parse_resource_pairs("آهن 0", resolver, RESOURCES) is None


def test_parse_resource_pairs_empty_text():
    assert m.parse_resource_pairs("", resolver, RESOURCES) is None


def test_parse_resource_pairs_merges_duplicate_resources():
    result = m.parse_resource_pairs("آهن 5 آهن 3", resolver, RESOURCES)
    assert result == {"scrap": 8}


def test_parse_barter_text_requires_equals_sign():
    assert m.parse_barter_text("آهن 5 پلاستیک 3", resolver, RESOURCES) is None


def test_parse_barter_text_valid():
    give, want = m.parse_barter_text("آهن 5 = پلاستیک 3", resolver, RESOURCES)
    assert give == {"scrap": 5}
    assert want == {"plastic": 3}


def test_parse_rental_text_trailing_qty_is_ambiguous_with_hours():
    """Pre-existing quirk, ported as-is (not something to silently fix
    here): since a valid `repay` side always ends in a quantity digit,
    that digit is indistinguishable from an explicit hours suffix. The
    trailing number always gets consumed as "hours", leaving the last
    resource without its quantity — so a rental offer with no *explicit*
    hours suffix fails to parse rather than falling back to the 6h
    default. Worth flagging upstream; out of scope for this pass.
    """
    result = m.parse_rental_text("آهن 5 = پلاستیک 3", resolver, RESOURCES)
    assert result is None


def test_parse_rental_text_custom_duration():
    give, repay, seconds = m.parse_rental_text(
        "آهن 5 = پلاستیک 3 12", resolver, RESOURCES
    )
    assert seconds == 12 * 3600


def test_parse_rental_text_duration_clamped_to_48h():
    give, repay, seconds = m.parse_rental_text(
        "آهن 5 = پلاستیک 3 999", resolver, RESOURCES
    )
    assert seconds == 48 * 3600


def test_parse_rental_text_zero_hour_token_is_not_treated_as_duration():
    # "0" isn't a positive int, so it's NOT consumed as an hours token —
    # it's left as part of the repay text instead, which then fails to
    # parse as a resource token, so the whole rental offer is rejected.
    result = m.parse_rental_text("آهن 5 = پلاستیک 3 0", resolver, RESOURCES)
    assert result is None


# ---------------------------------------------------------------------
# rental_profit_ok
# ---------------------------------------------------------------------


def test_rental_profit_ok_allows_1_3x_same_resource():
    assert m.rental_profit_ok({"scrap": 10}, {"scrap": 13}) is True


def test_rental_profit_ok_blocks_over_1_3x_same_resource():
    assert m.rental_profit_ok({"scrap": 10}, {"scrap": 14}) is False


def test_rental_profit_ok_ignores_multi_resource_deals():
    # rule only applies to single-resource-for-same-resource deals
    assert m.rental_profit_ok({"scrap": 10, "glass": 1}, {"scrap": 100}) is True


def test_rental_profit_ok_allows_different_resources_any_ratio():
    assert m.rental_profit_ok({"scrap": 1}, {"battery": 100}) is True


# ---------------------------------------------------------------------
# compute_daily_restock
# ---------------------------------------------------------------------


def test_restock_adds_up_to_daily_amount():
    new_supply, added = m.compute_daily_restock(
        current_supply={"scrap": 0},
        resources=["scrap"],
        daily_amounts={"scrap": 25},
        caps={"scrap": 75},
    )
    assert added == {"scrap": 25}
    assert new_supply["scrap"] == 25


def test_restock_respects_cap():
    new_supply, added = m.compute_daily_restock(
        current_supply={"scrap": 70},
        resources=["scrap"],
        daily_amounts={"scrap": 25},
        caps={"scrap": 75},
    )
    assert added == {"scrap": 5}  # only room for 5 more before hitting cap
    assert new_supply["scrap"] == 75


def test_restock_adds_nothing_when_already_at_cap():
    new_supply, added = m.compute_daily_restock(
        current_supply={"scrap": 75},
        resources=["scrap"],
        daily_amounts={"scrap": 25},
        caps={"scrap": 75},
    )
    assert added == {}
    assert new_supply["scrap"] == 75


def test_restock_handles_missing_resource_in_current_supply():
    new_supply, added = m.compute_daily_restock(
        current_supply={},
        resources=["scrap", "plastic"],
        daily_amounts={"scrap": 25, "plastic": 20},
        caps={"scrap": 75, "plastic": 60},
    )
    assert new_supply == {"scrap": 25, "plastic": 20}
