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
