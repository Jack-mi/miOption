"""中性且波动率上升时，菜单先给结论，过关的才用链上合约。"""

from datetime import date, timedelta

from signal_chain.options.strategy_menu import CATALOG, apply_user_bias, render_menu, screen_menu, MenuVerdict
from signal_chain.schema import ChainSnapshot, Direction, EnsembleSignal, OptionRow

D0 = date(2026, 9, 23)


def test_neutral_rising_keeps_straddle_and_drops_the_rest():
    assert len(CATALOG) == 27
    exp = D0 + timedelta(days=14)
    chain = ChainSnapshot(
        ticker="US.AAPL", market="US", as_of=D0, source="futu", spot=340.0,
        rows=[
            OptionRow(code="C340", strike=340, expiry=exp, option_type="CALL",
                      bid=5.0, ask=5.2, open_interest=500),
            OptionRow(code="P340", strike=340, expiry=exp, option_type="PUT",
                      bid=4.0, ask=4.2, open_interest=500),
            OptionRow(code="C350", strike=350, expiry=exp, option_type="CALL",
                      bid=2.0, ask=2.2, open_interest=400),
            OptionRow(code="P330", strike=330, expiry=exp, option_type="PUT",
                      bid=2.0, ask=2.2, open_interest=400),
        ],
    )
    ensemble = EnsembleSignal(
        ticker="US.AAPL", market="US", as_of=D0, components=[],
        agreement="partial", direction=Direction.NEUTRAL, conviction=0.13,
        volatility_view="rising",
    )
    by_name = {v.name: v for v in screen_menu(
        ensemble, chain, account_equity=100_000, today=D0,
    )}
    assert by_name["裸卖看涨"].status == "impossible"
    assert by_name["牛市看涨价差"].status == "unfit"
    straddle = by_name["买入跨式"]
    assert straddle.status == "fit"
    assert {lg.code for lg in straddle.proposal.legs} <= {"C340", "P340"}
    assert "风控" not in straddle.reason
    text = render_menu([MenuVerdict("买入看涨", "unfit", "方向不合。", None, None)])
    assert "Participate in an expected rise" in text


def test_user_bias_does_not_rewrite_ensemble():
    ensemble = EnsembleSignal(
        ticker="US.AAPL", market="US", as_of=D0, components=[],
        agreement="aligned", direction=Direction.BUY, conviction=0.5,
    )
    viewed = apply_user_bias(ensemble, "bear")
    assert ensemble.direction == Direction.BUY
    assert viewed.direction == Direction.SELL
