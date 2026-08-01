from bot_pkg.services import alliance_service as a

CARTEL_LEVELS = {
    1: {"water_bonus": 0.0, "score_bonus": 0, "upgrade_cost": 100},
    2: {"water_bonus": 0.05, "score_bonus": 5, "upgrade_cost": 300},
    3: {"water_bonus": 0.10, "score_bonus": 10, "upgrade_cost": 0},
}
MAX_LEVEL = 3


# ---------------------------------------------------------------------
# Cartel level
# ---------------------------------------------------------------------


def test_cartel_level_clamps_to_1_minimum():
    assert a.cartel_level(0, MAX_LEVEL) == 1
    assert a.cartel_level(-5, MAX_LEVEL) == 1


def test_cartel_level_clamps_to_max():
    assert a.cartel_level(99, MAX_LEVEL) == MAX_LEVEL


def test_cartel_level_normal():
    assert a.cartel_level(2, MAX_LEVEL) == 2


def test_cartel_level_data_returns_correct_tier():
    assert a.cartel_level_data(2, CARTEL_LEVELS)["water_bonus"] == 0.05


def test_cartel_level_data_falls_back_to_level_1():
    assert a.cartel_level_data(99, CARTEL_LEVELS) == CARTEL_LEVELS[1]


def test_cartel_next_upgrade_cost_normal():
    assert a.cartel_next_upgrade_cost(1, MAX_LEVEL, CARTEL_LEVELS) == 300


def test_cartel_next_upgrade_cost_zero_when_maxed():
    assert a.cartel_next_upgrade_cost(3, MAX_LEVEL, CARTEL_LEVELS) == 0


# ---------------------------------------------------------------------
# Water tax split
# ---------------------------------------------------------------------


def test_split_water_tax_basic():
    net, tax, bonus = a.split_water_tax(1000, tax_rate=0.06, bonus_rate=0.04)
    assert net == 940  # 1000 - 60 tax
    assert tax == 60
    assert bonus == 40


def test_split_water_tax_zero_gross():
    assert a.split_water_tax(0, 0.06, 0.04) == (0, 0, 0)


def test_split_water_tax_never_negative_gross():
    net, tax, bonus = a.split_water_tax(-50, 0.06, 0.04)
    assert net == 0
    assert tax == 0
    assert bonus == 0


# ---------------------------------------------------------------------
# Pool distribution
# ---------------------------------------------------------------------


def test_distribute_pool_zero_pool_does_nothing():
    assert a.distribute_pool(0, 5, 0.25) == (0, 0, 0)


def test_distribute_pool_no_other_members_goes_entirely_to_vault():
    each, distributed, vault_add = a.distribute_pool(100, 0, 0.25)
    assert each == 0
    assert distributed == 0
    assert vault_add == 100


def test_distribute_pool_splits_evenly():
    # pool=100, rate=0.25 -> distributed=25, 5 members -> 5 each
    each, distributed, vault_add = a.distribute_pool(100, 5, 0.25)
    assert each == 5
    assert distributed == 25
    assert vault_add == 75  # the un-distributed 75% of the pool


def test_distribute_pool_remainder_falls_back_to_vault():
    # pool=100, rate=0.25 -> distributed=25, 3 members -> 25//3=8 each, 24 actual
    each, distributed, vault_add = a.distribute_pool(100, 3, 0.25)
    assert each == 8
    assert distributed == 24
    assert vault_add == 76  # 75 (undistributed) + 1 (division remainder)


def test_distribute_pool_gives_at_least_1_each_when_something_is_distributed():
    # pool=10, rate=0.25 -> distributed=2, 5 members -> 2//5=0, but each member
    # still gets at least 1 (costing more than "distributed" nominally allows)
    each, distributed, vault_add = a.distribute_pool(10, 5, 0.25)
    assert each == 1
    assert distributed == 5
    assert vault_add == 5


def test_distribute_pool_conserves_total():
    # actual_distributed + vault_add must always equal the original pool
    for pool in (1, 7, 50, 100, 999):
        for members in (0, 1, 3, 7, 20):
            each, distributed, vault_add = a.distribute_pool(pool, members, 0.25)
            assert distributed + vault_add == pool
