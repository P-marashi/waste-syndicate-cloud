from bot_pkg.services import admin_service as a


# ---------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------


def test_paginate_basic():
    page, total_pages, start, end = a.paginate(total_items=25, page=1, page_size=8)
    assert total_pages == 4  # ceil(25/8)
    assert start == 0
    assert end == 8


def test_paginate_last_page_partial():
    page, total_pages, start, end = a.paginate(total_items=25, page=4, page_size=8)
    assert start == 24
    assert end == 25  # only 1 item on the last page


def test_paginate_clamps_page_too_high():
    page, total_pages, start, end = a.paginate(total_items=25, page=999, page_size=8)
    assert page == total_pages == 4


def test_paginate_clamps_page_too_low():
    page, *_ = a.paginate(total_items=25, page=0, page_size=8)
    assert page == 1
    page, *_ = a.paginate(total_items=25, page=-5, page_size=8)
    assert page == 1


def test_paginate_zero_items_still_1_page():
    page, total_pages, start, end = a.paginate(total_items=0, page=1, page_size=8)
    assert total_pages == 1
    assert start == 0
    assert end == 0


def test_parse_page_number_valid():
    pattern = r"^👥 بازیکن‌ها صفحه (\d+)$"
    assert a.parse_page_number("👥 بازیکن‌ها صفحه 3", pattern) == 3


def test_parse_page_number_invalid_text():
    pattern = r"^👥 بازیکن‌ها صفحه (\d+)$"
    assert a.parse_page_number("something else", pattern) is None


def test_parse_page_number_floors_at_1():
    pattern = r"^page (-?\d+)$"
    assert a.parse_page_number("page 0", pattern) == 1


# ---------------------------------------------------------------------
# Penalty parsing
# ---------------------------------------------------------------------

ALIASES = {"water": "water", "آب": "water", "xp": "xp", "تجربه": "xp"}


def resolver(token: str) -> str | None:
    return ALIASES.get(token)


def test_parse_penalty_text_basic():
    items, reason = a.parse_penalty_text("water=50 xp=10", resolver)
    assert items == {"water": 50, "xp": 10}
    assert reason == "بدون دلیل ثبت‌شده"  # default when no reason given


def test_parse_penalty_text_with_reason():
    items, reason = a.parse_penalty_text("water=50 دلیل: تقلب در ریید", resolver)
    assert items == {"water": 50}
    assert reason == "تقلب در ریید"


def test_parse_penalty_text_ignores_unknown_keys():
    items, reason = a.parse_penalty_text("gold=50 water=10", resolver)
    assert items == {"water": 10}


def test_parse_penalty_text_ignores_only_exactly_zero_amounts():
    items, reason = a.parse_penalty_text("water=0 xp=-5", resolver)
    # water=0 is dropped (nothing to penalize); xp=-5 becomes xp=5 via abs()
    assert items == {"xp": 5}


def test_parse_penalty_text_takes_absolute_value():
    # a negative amount in the raw text still becomes a positive penalty
    # (the "-" just gets abs()'d, doesn't mean "add instead of subtract")
    items, reason = a.parse_penalty_text("water=-50", resolver)
    assert items == {"water": 50}


def test_parse_penalty_text_merges_duplicate_keys():
    items, reason = a.parse_penalty_text("water=10 آب=5", resolver)
    assert items == {"water": 15}


def test_parse_penalty_text_reason_case_insensitive_english():
    items, reason = a.parse_penalty_text("water=10 reason: cheating", resolver)
    assert reason == "cheating"


# ---------------------------------------------------------------------
# Penalty application
# ---------------------------------------------------------------------


def test_apply_clamped_penalty_normal():
    taken, after = a.apply_clamped_penalty(before=100, amount=30)
    assert taken == 30
    assert after == 70


def test_apply_clamped_penalty_cannot_go_negative():
    taken, after = a.apply_clamped_penalty(before=20, amount=100)
    assert taken == 20  # only takes what's available
    assert after == 0


def test_apply_clamped_penalty_negative_amount_treated_as_zero():
    taken, after = a.apply_clamped_penalty(before=50, amount=-10)
    assert taken == 0
    assert after == 50


def test_apply_unclamped_penalty_can_go_negative():
    assert a.apply_unclamped_penalty(before=5, amount=10) == -5


def test_apply_unclamped_penalty_normal():
    assert a.apply_unclamped_penalty(before=100, amount=30) == 70
