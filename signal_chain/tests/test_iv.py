"""IV 派生规则。"""

from datetime import date, timedelta

from signal_chain.options.iv import derive_volatility_view
from signal_chain.schema import (
    Catalyst,
    ChainSnapshot,
    Direction,
    EnsembleSignal,
    OptionRow,
)
from signal_chain.schema.underlying import FieldMeta, VolBasisField

D0 = date(2026, 9, 23)


def _sig(catalysts=None):
    return EnsembleSignal(
        ticker="US.AAPL", market="US", as_of=D0, components=[],
        agreement="aligned", direction=Direction.BUY, conviction=0.5,
        catalysts=catalysts or [],
    )


def _chain(front_iv, back_iv):
    rows = []
    for exp, iv in ((D0 + timedelta(days=20), front_iv),
                    (D0 + timedelta(days=50), back_iv)):
        rows.append(OptionRow(code=f"X{exp}", strike=100, expiry=exp,
                              option_type="CALL", iv=iv))
    return ChainSnapshot(ticker="US.AAPL", market="US", as_of=D0,
                         source="futu", spot=100.0, rows=rows)


def test_event_window_rising():
    sig = _sig([Catalyst(type="earnings", expected_date=D0 + timedelta(days=7),
                         description="Q3")])
    assert derive_volatility_view(sig, _chain(0.3, 0.3), today=D0) == "rising"


def test_term_inversion_rising():
    assert derive_volatility_view(_sig(), _chain(0.40, 0.30), today=D0) == "rising"


def test_term_steep_falling():
    assert derive_volatility_view(_sig(), _chain(0.20, 0.30), today=D0) == "falling"


def test_flat_neutral():
    assert derive_volatility_view(_sig(), _chain(0.30, 0.31), today=D0) == "neutral"


def test_no_chain_unknown():
    assert derive_volatility_view(_sig(), None, today=D0) == "unknown"


def _basis(ratio):
    return VolBasisField(
        meta=FieldMeta(status="available", source="futu_vol_basis",
                       as_of=D0, fetched_at=None),
        iv_latest=30.0, hv_latest=30.0 / ratio, ratio=ratio,
    )


def test_rich_iv_vs_hv_rising_when_term_flat():
    assert derive_volatility_view(
        _sig(), _chain(0.30, 0.31), today=D0, vol_basis=_basis(1.3),
    ) == "rising"


def test_cheap_iv_vs_hv_falling_when_term_flat():
    assert derive_volatility_view(
        _sig(), _chain(0.30, 0.31), today=D0, vol_basis=_basis(0.8),
    ) == "falling"


def test_basis_near_one_stays_neutral():
    assert derive_volatility_view(
        _sig(), _chain(0.30, 0.31), today=D0, vol_basis=_basis(1.05),
    ) == "neutral"


def test_term_structure_outranks_basis():
    """近远月倒挂是更硬的证据，不能被 HV 基准翻掉。"""
    assert derive_volatility_view(
        _sig(), _chain(0.40, 0.30), today=D0, vol_basis=_basis(0.8),
    ) == "rising"
    assert derive_volatility_view(
        _sig(), _chain(0.20, 0.30), today=D0, vol_basis=_basis(1.3),
    ) == "falling"


def test_dividend_catalyst_is_not_a_vol_event():
    """除息由 risk 的 ex_div_blackout_days 管，不能顺带把 short-vol 全否掉。"""
    sig = _sig([Catalyst(type="dividend", expected_date=D0 + timedelta(days=3),
                         description="除息")])
    assert derive_volatility_view(sig, _chain(0.30, 0.31), today=D0) == "neutral"
    assert derive_volatility_view(sig, _chain(0.30, 0.31), today=D0,
                                  vol_basis=_basis(1.3)) == "rising"


def test_basis_rescues_unknown_without_chain():
    assert derive_volatility_view(_sig(), None, today=D0, vol_basis=_basis(1.3)) == "rising"
    assert derive_volatility_view(_sig(), None, today=D0, vol_basis=_basis(0.8)) == "falling"
    assert derive_volatility_view(_sig(), None, today=D0, vol_basis=_basis(1.0)) == "unknown"


def test_threshold_zero_disables_basis():
    assert derive_volatility_view(
        _sig(), None, today=D0, vol_basis=_basis(2.0), iv_hv_rising_ratio=0,
    ) == "unknown"
