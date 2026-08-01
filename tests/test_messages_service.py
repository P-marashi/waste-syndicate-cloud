from bot_pkg.services import messages_service as m


def test_message_preview_short_text_unchanged():
    assert m.message_preview("hello") == "hello"


def test_message_preview_collapses_whitespace():
    assert m.message_preview("hello   \n\n  world") == "hello world"


def test_message_preview_truncates_long_text():
    text = "a" * 200
    preview = m.message_preview(text, limit=90)
    assert len(preview) == 90
    assert preview.endswith("…")


def test_message_preview_exact_limit_not_truncated():
    text = "a" * 90
    assert m.message_preview(text, limit=90) == text


def test_normalize_message_body_strips_and_caps():
    assert m.normalize_message_body("  hi  ") == "hi"
    assert len(m.normalize_message_body("a" * 1000, max_len=700)) == 700


def test_is_body_too_short():
    assert m.is_body_too_short("") is True
    assert m.is_body_too_short("a") is True
    assert m.is_body_too_short("ab") is False
    assert m.is_body_too_short("  a  ") is True  # whitespace doesn't count


def test_trim_message_log_keeps_most_recent():
    messages = list(range(10))
    assert m.trim_message_log(messages, max_count=3) == [7, 8, 9]


def test_trim_message_log_under_limit_unchanged():
    messages = [1, 2, 3]
    assert m.trim_message_log(messages, max_count=10) == [1, 2, 3]


def test_trim_message_log_zero_limit_empties():
    assert m.trim_message_log([1, 2, 3], max_count=0) == []
