from bot_pkg.services import registration_service as r


def test_extract_ref_from_start_found():
    assert r.extract_ref_from_start("/start REF123456") == "REF123456"


def test_extract_ref_from_start_case_insensitive():
    assert r.extract_ref_from_start("/start ref123456") == "REF123456"


def test_extract_ref_from_start_not_found():
    assert r.extract_ref_from_start("/start") is None


def test_extract_ref_from_start_requires_min_4_digits():
    assert r.extract_ref_from_start("/start REF12") is None


def test_extract_ref_from_start_empty_text():
    assert r.extract_ref_from_start("") is None
    assert r.extract_ref_from_start(None) is None


def test_normalize_unique_name_collapses_whitespace():
    assert r.normalize_unique_name("Ali   Baba") == "ali baba"


def test_normalize_unique_name_strips_edges():
    assert r.normalize_unique_name("  Ali  ") == "ali"


def test_normalize_unique_name_empty():
    assert r.normalize_unique_name("") == ""
    assert r.normalize_unique_name(None) == ""


def test_is_reserved_name_matches_case_insensitive():
    reserved = {"شروع", "منوی اصلی"}
    assert r.is_reserved_name("شروع", reserved) is True
    assert r.is_reserved_name("  شروع  ", reserved) is True


def test_is_reserved_name_not_matched():
    reserved = {"شروع"}
    assert r.is_reserved_name("Ali", reserved) is False


def test_is_reserved_name_ignores_empty_reserved_entries():
    reserved = {"شروع", "", None}
    assert r.is_reserved_name("Ali", reserved) is False
