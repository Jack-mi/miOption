"""除息闸：short-vol 在除息窗口内到期要否决，非 short-vol 只告警。"""

from datetime import date, timedelta

from signal_chain.risk.limits import check_proposal
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
EX_DIV = D0 + timedelta(days=3)


def _ensemble(*, catalysts=None, vol="neutral"):
    return EnsembleSignal(
        ticker="US.KO", market="US", as_of=D0, components=[],
        agreement="aligned", direction=Direction.BUY, conviction=0.6,
        catalysts=catalysts or [], volatility_view=vol,
    )


def _chain():
    expiry = D0 + timedelta(days=30)
    return ChainSnapshot(
        ticker="US.KO", market="US", as_of=D0, source="futu", spot=70.0,
        rows=[OptionRow(
            code="US.KO260101P65000", strike=65.0, expiry=expiry, option_type="PUT",
            bid=1.0, ask=1.05, open_interest=500, volume=10, iv=0.25,
            fetched_at=D0.isoformat(), quoted_at=D0.isoformat(),
        )],
    )


def _proposal(*, short_vol=True, expiry_offset=4):
    return StrategyProposal(
        name="cash_secured_put",
        thesis="收租",
        legs=[StrategyLeg(
            code="US.KO260101P65000", option_type="PUT", strike=65.0,
            expiry=EX_DIV + timedelta(days=expiry_offset), side="sell",
        )],
        is_short_vol=short_vol,
    )


def _dividend_catalyst():
    return Catalyst(type="dividend", expected_date=EX_DIV, description="除息 0.5 USD")


def test_short_vol_vetoed_when_leg_expires_just_after_ex_div():
    decision = check_proposal(
        _proposal(), _ensemble(catalysts=[_dividend_catalyst()]), _chain(),
        today=D0, ex_div_blackout_days=5,
    )
    assert not decision.approved
    assert any("除息" in v for v in decision.vetoes)


def test_long_vol_only_warns():
    decision = check_proposal(
        _proposal(short_vol=False), _ensemble(catalysts=[_dividend_catalyst()]), _chain(),
        today=D0, ex_div_blackout_days=5,
    )
    assert decision.approved
    assert any("除息" in w for w in decision.warnings)
    assert not any("除息" in v for v in decision.vetoes)


def test_expiry_far_from_ex_div_is_allowed():
    decision = check_proposal(
        _proposal(expiry_offset=20), _ensemble(catalysts=[_dividend_catalyst()]), _chain(),
        today=D0, ex_div_blackout_days=5,
    )
    assert decision.approved
    assert not any("除息" in v for v in decision.vetoes)


def test_past_ex_div_is_ignored():
    past = Catalyst(type="dividend", expected_date=D0 - timedelta(days=2), description="已除息")
    decision = check_proposal(
        _proposal(), _ensemble(catalysts=[past]), _chain(),
        today=D0, ex_div_blackout_days=5,
    )
    assert decision.approved


def test_window_zero_turns_the_gate_off():
    decision = check_proposal(
        _proposal(), _ensemble(catalysts=[_dividend_catalyst()]), _chain(),
        today=D0, ex_div_blackout_days=0,
    )
    assert decision.approved
    assert not any("除息" in w for w in decision.warnings)
