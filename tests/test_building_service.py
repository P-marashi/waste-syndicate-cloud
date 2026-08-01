from bot_pkg.services import building_service as b

LAB_LEVELS = {
    1: {"discount": 0.05},
    2: {"discount": 0.10},
    3: {"discount": 0.15},
}


def test_apply_discount_zero_returns_unchanged_copy():
    cost = {"scrap": 10, "glass": 5}
    result = b.apply_discount(cost, 0)
    assert result == cost
    assert result is not cost  # must be a copy, not the same dict


def test_apply_discount_floors_at_1():
    result = b.apply_discount({"scrap": 1}, 0.9)
    assert result["scrap"] == 1  # never rounds down to 0


def test_apply_discount_rounds_down():
    result = b.apply_discount({"scrap": 100}, 0.15)
    assert result["scrap"] == 85


def test_lab_discount_rate_zero_if_lab_not_built():
    assert b.lab_discount_rate({}, LAB_LEVELS) == 0.0
    assert b.lab_discount_rate({"lab": 0}, LAB_LEVELS) == 0.0


def test_lab_discount_rate_returns_level_discount():
    assert b.lab_discount_rate({"lab": 2}, LAB_LEVELS) == 0.10


def test_lab_discount_rate_excludes_lab_upgrading_itself():
    assert b.lab_discount_rate({"lab": 3}, LAB_LEVELS, exclude_key="lab") == 0.0


def test_lab_discount_rate_applies_to_other_buildings():
    assert b.lab_discount_rate({"lab": 3}, LAB_LEVELS, exclude_key="armory") == 0.15


def test_craft_discount_rate_combines_event_and_lab():
    rate = b.craft_discount_rate({"lab": 1}, LAB_LEVELS, event_discount=0.05)
    assert rate == 0.10  # 0.05 event + 0.05 lab


def test_craft_discount_rate_capped_at_35_percent():
    rate = b.craft_discount_rate(
        {"lab": 3}, LAB_LEVELS, event_discount=0.5, cap=0.35
    )
    assert rate == 0.35


def test_compute_heal_normal():
    healed, new_hp = b.compute_heal(current_hp=50, heal_amount=20)
    assert healed == 20
    assert new_hp == 70


def test_compute_heal_capped_at_max_hp():
    healed, new_hp = b.compute_heal(current_hp=90, heal_amount=50)
    assert healed == 10
    assert new_hp == 100


def test_compute_heal_with_bonus():
    healed, new_hp = b.compute_heal(current_hp=50, heal_amount=10, heal_bonus=5)
    assert healed == 15
    assert new_hp == 65


def test_compute_heal_never_negative_at_full_hp():
    healed, new_hp = b.compute_heal(current_hp=100, heal_amount=20)
    assert healed == 0
    assert new_hp == 100


def test_halve_remaining_seconds():
    assert b.halve_remaining_seconds(100) == 50
    assert b.halve_remaining_seconds(0) == 0
