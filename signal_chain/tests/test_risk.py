"""风控闸：conflicted 否决 / 财报窗口 short-vol / 流动性 / 敞口。"""

from datetime import date, timedelta

from signal_chain.risk.limits import check_proposal, check_signal
from signal_chain.schema import (
    Catalyst,
    ChainSnapshot,
    Direction,
    EnsembleSignal,
    OptionRow,
    StrategyLeg,
    StrategyProposal,
)

D0 = date(2026, 9, 23)


def _ensemble(agreement="aligned", vol="neutral", catalysts=None):
    return EnsembleSignal(
        ticker="US.AAPL", market="US", as_of=D0, components=[],
        agreement=agreement, direction=Direction.BUY, conviction=0.6,
        volatility_view=vol, catalysts=catalysts or [],
    )


def _chain():
    rows = [
        OptionRow(code="A", strike=95, expiry=D0 + timedelta(days=30),
                  option_type="PUT", bid=1.0, ask=1.1, open_interest=500, iv=0.3),
        OptionRow(code="B", strike=90, expiry=D0 + timedelta(days=30),
                  option_type="PUT", bid=0.5, ask=0.55, open_interest=300, iv=0.32),
    ]
    return ChainSnapshot(ticker="US.AAPL", market="US", as_of=D0,
                         source="futu", spot=100.0, rows=rows)


def _spread(short_vol=True):
    return StrategyProposal(
        name="bull_put_spread", thesis="t",
        legs=[
            StrategyLeg(code="A", option_type="PUT", strike=95,
                        expiry=D0 + timedelta(days=30), side="sell"),
            StrategyLeg(code="B", option_type="PUT", strike=90,
                        expiry=D0 + timedelta(days=30), side="buy"),
        ],
        max_loss=450.0, is_short_vol=short_vol,
    )


def test_conflicted_veto():
    d = check_signal(_ensemble(agreement="conflicted"))
    assert not d.approved and d.vetoes


def test_earnings_window_short_vol_veto():
    cat = [Catalyst(type="earnings", expected_date=D0 + timedelta(days=5),
                    description="Q3")]
    d = check_proposal(_spread(), _ensemble(catalysts=cat), _chain())
    assert any("财报窗口" in v for v in d.vetoes)


def test_rising_vol_short_vol_veto():
    d = check_proposal(_spread(), _ensemble(vol="rising"), _chain())
    assert any("short-vol" in v for v in d.vetoes)


def test_liquidity_veto():
    chain = _chain()
    chain.rows[0].open_interest = 10  # 低于 100
    d = check_proposal(_spread(), _ensemble(), chain)
    assert any("OI=10" in v for v in d.vetoes)


def test_equity_exposure():
    d = check_proposal(_spread(), _ensemble(), _chain(),
                       account_equity=5000.0, equity_currency="USD",
                       max_position_risk_pct=0.05)
    assert any("上限" in v for v in d.vetoes)  # 450 > 250


def test_clean_pass():
    d = check_proposal(_spread(), _ensemble(), _chain(),
                       account_equity=100000.0, equity_currency="USD")
    assert d.approved
