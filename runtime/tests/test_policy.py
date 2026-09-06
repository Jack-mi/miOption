import time

import pytest

from mioption_runtime.futu.policy import GlobalControls, PolicyError, TradeEnv, TradePolicy


def test_global_controls_block_max_positions():
    c = GlobalControls(max_position_limit=1, open_positions=1)
    with pytest.raises(PolicyError) as ei:
        c.check_open()
    assert ei.value.code == "max_position_limit"


def test_real_locked_by_default():
    p = TradePolicy(env=TradeEnv.REAL, real_unlocked=False)
    with pytest.raises(PolicyError) as ei:
        p.require_simulate_or_unlocked()
    assert ei.value.code == "real_locked"


def test_rate_limit():
    p = TradePolicy(max_orders_per_30s=2)
    now = time.time()
    p.note_order(now)
    p.note_order(now)
    with pytest.raises(PolicyError) as ei:
        p.check_rate_limit(now)
    assert ei.value.code == "rate_limit"
