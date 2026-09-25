"""富途菜单上的 27 个结构。先给结论，过关的才从链上选合约。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..risk.limits import check_proposal
from .glossary import strategy_blurb
from ..schema import (
    ChainSnapshot,
    Direction,
    EnsembleSignal,
    OptionRow,
    RiskDecision,
    StrategyLeg,
    StrategyProposal,
)

_MULT = 100  # ponytail: 美股一张 100 股。港股乘数不猜，选合约直接做不了。
_MIN_DTE = 7

_BULL = {Direction.BUY, Direction.STRONG_BUY}
_BEAR = {Direction.SELL, Direction.STRONG_SELL}
_UNLIMITED = {"short_straddle", "short_strangle"}
_CREDIT = {"bull_put", "bear_call", "iron_condor", "iron_butterfly"}


@dataclass(frozen=True)
class Template:
    name: str
    bias: str  # bull / bear / neutral
    vol: str  # long / short / none
    shape: str
    needs_shares: bool = False
    naked: bool = False
    cash_secured: bool = False
    no_formula: bool = False


@dataclass
class MenuVerdict:
    name: str
    status: str  # fit / unfit / impossible
    reason: str
    proposal: StrategyProposal | None = None
    risk: RiskDecision | None = None


CATALOG: tuple[Template, ...] = (
    Template("买入看涨", "bull", "long", "long_call"),
    Template("买入看跌", "bear", "long", "long_put"),
    Template("裸卖看涨", "bear", "short", "naked", naked=True),
    Template("裸卖看跌", "bull", "short", "naked", naked=True),
    Template("保护性认沽", "bull", "long", "none", needs_shares=True),
    Template("牛市看涨价差", "bull", "none", "bull_call"),
    Template("牛市认沽价差", "bull", "short", "bull_put"),
    Template("熊市看涨价差", "bear", "short", "bear_call"),
    Template("熊市认沽价差", "bear", "none", "bear_put"),
    Template("备兑看涨", "bull", "short", "none", needs_shares=True),
    Template("现金担保认沽", "bull", "short", "cash_put", cash_secured=True),
    Template("领口", "bull", "none", "none", needs_shares=True),
    Template("买入跨式", "neutral", "long", "straddle"),
    Template("卖出跨式", "neutral", "short", "short_straddle"),
    Template("买入宽跨", "neutral", "long", "strangle"),
    Template("卖出宽跨", "neutral", "short", "short_strangle"),
    Template("带式", "bull", "long", "strap"),
    Template("条式", "bear", "long", "strip"),
    Template("认购日历价差", "neutral", "long", "calendar_call"),
    Template("认沽日历价差", "neutral", "long", "calendar_put"),
    Template("对角认购价差", "bull", "none", "none", no_formula=True),
    Template("买入认购蝶式", "neutral", "short", "butterfly_call"),
    Template("买入认沽蝶式", "neutral", "short", "butterfly_put"),
    Template("买入认购鹰式", "neutral", "short", "condor_call"),
    Template("买入认沽鹰式", "neutral", "short", "condor_put"),
    Template("卖出铁蝶", "neutral", "short", "iron_butterfly"),
    Template("卖出铁鹰", "neutral", "short", "iron_condor"),
)


def _bias_ok(bias: str, direction: Direction) -> bool:
    if bias == "neutral":
        return direction == Direction.NEUTRAL
    if bias == "bull":
        return direction in _BULL
    return direction in _BEAR


def _dir_word(direction: Direction) -> str:
    if direction in _BULL:
        return "看多"
    if direction in _BEAR:
        return "看空"
    return "中性"


def _quoted(chain: ChainSnapshot, expiry: date, opt: str) -> list[OptionRow]:
    out = []
    for r in chain.rows:
        if r.expiry != expiry or r.option_type != opt:
            continue
        if r.bid and r.ask and r.bid > 0 and r.ask > 0:
            out.append(r)
    return out


def _live_expiries(chain: ChainSnapshot, as_of: date) -> list[date]:
    cutoff = as_of + timedelta(days=_MIN_DTE)
    good = []
    for exp in chain.expiries():
        if exp < cutoff:
            continue
        if _quoted(chain, exp, "CALL") and _quoted(chain, exp, "PUT"):
            good.append(exp)
    return good


def _at(rows: list[OptionRow], strike: float) -> OptionRow | None:
    for r in rows:
        if r.strike == strike:
            return r
    return None


def _strikes(rows: list[OptionRow]) -> list[float]:
    return sorted({r.strike for r in rows})


def _closest(strikes: list[float], spot: float) -> float | None:
    if not strikes:
        return None
    return min(strikes, key=lambda s: (abs(s - spot), s))


def _window(strikes: list[float], spot: float, n: int) -> list[float] | None:
    if len(strikes) < n:
        return None
    best, best_d = None, None
    for i in range(len(strikes) - n + 1):
        w = strikes[i:i + n]
        d = abs(w[(n - 1) // 2] - spot)
        if best_d is None or d < best_d:
            best, best_d = w, d
    return best


def _leg(row: OptionRow | None, side: str, qty: int = 1) -> StrategyLeg | None:
    if row is None:
        return None
    return StrategyLeg(
        code=row.code, option_type=row.option_type, strike=row.strike,
        expiry=row.expiry, side=side, quantity=qty,
    )


def _pair(rows: list[OptionRow], spot: float) -> tuple[OptionRow, OptionRow] | None:
    ks = _strikes(rows)
    k = _closest(ks, spot)
    if k is None:
        return None
    hi = next((s for s in ks if s > k), None)
    lo = next((s for s in reversed(ks) if s < k), None)
    other = hi if hi is not None else lo
    if other is None:
        return None
    a, b = _at(rows, k), _at(rows, other)
    if a is None or b is None:
        return None
    low, high = (a, b) if a.strike < b.strike else (b, a)
    return low, high


def _shared(calls: list[OptionRow], puts: list[OptionRow], spot: float):
    common = set(_strikes(calls)) & set(_strikes(puts))
    k = _closest(sorted(common), spot)
    if k is None:
        return None
    return _at(calls, k), _at(puts, k)


def _wings(calls, puts, spot):
    body = _shared(calls, puts, spot)
    if body is None:
        return None
    call, put = body
    up = next((s for s in _strikes(calls) if s > call.strike), None)
    dn = next((s for s in reversed(_strikes(puts)) if s < put.strike), None)
    if up is None or dn is None:
        return None
    return call, put, _at(calls, up), _at(puts, dn)


def _outside(strikes: list[float], spot: float, n: int, above: bool) -> list[float] | None:
    pool = [s for s in strikes if s > spot] if above else [s for s in strikes if s < spot]
    if len(pool) < n:
        return None
    return pool[:n] if above else pool[-n:]


def _cash(legs: list[StrategyLeg], by_code: dict[str, OptionRow]) -> float | None:
    total = 0.0
    for leg in legs:
        mid = by_code[leg.code].mid
        if mid is None:
            return None
        total += (mid if leg.side == "sell" else -mid) * leg.quantity
    return total


def _max_loss(shape: str, legs: list[StrategyLeg], net: float | None) -> float | None:
    if net is None or shape in _UNLIMITED:
        return None
    if shape == "cash_put":
        return round((legs[0].strike - max(net, 0)) * _MULT, 2)
    if shape in _CREDIT:
        if shape in {"iron_condor", "iron_butterfly"}:
            calls = [lg.strike for lg in legs if lg.option_type == "CALL"]
            puts = [lg.strike for lg in legs if lg.option_type == "PUT"]
            width = max(abs(calls[0] - calls[1]), abs(puts[0] - puts[1]))
        else:
            width = abs(legs[0].strike - legs[1].strike)
        return round((width - max(net, 0)) * _MULT, 2)
    return round(abs(min(net, 0)) * _MULT, 2)


def _finish(name: str, thesis: str, shape: str, short_vol: bool,
            legs: list[StrategyLeg], chain: ChainSnapshot) -> StrategyProposal | None:
    if not legs or any(lg is None for lg in legs):
        return None
    by_code = {r.code: r for r in chain.rows}
    if any(lg.code not in by_code for lg in legs):
        return None
    net = _cash(legs, by_code)
    return StrategyProposal(
        name=name, thesis=thesis, legs=legs,
        max_loss=_max_loss(shape, legs, net),
        net_premium=None if net is None else round(net * _MULT, 2),
        is_short_vol=short_vol,
    )


def _build(t: Template, chain: ChainSnapshot, as_of: date) -> StrategyProposal | None:
    spot = chain.spot
    if spot is None:
        return None
    exps = _live_expiries(chain, as_of)
    if not exps:
        return None
    exp = exps[0]
    calls, puts = _quoted(chain, exp, "CALL"), _quoted(chain, exp, "PUT")
    shape = t.shape
    thesis = "方向与波动率都过了菜单。"
    short = t.vol == "short"

    if shape == "long_call":
        k = _closest(_strikes(calls), spot)
        row = _at(calls, k) if k is not None else None
        legs = [_leg(row, "buy")] if row else []
    elif shape == "long_put":
        k = _closest(_strikes(puts), spot)
        row = _at(puts, k) if k is not None else None
        legs = [_leg(row, "buy")] if row else []
    elif shape == "cash_put":
        k = _closest(_strikes(puts), spot)
        row = _at(puts, k) if k is not None else None
        legs = [_leg(row, "sell")] if row else []
    elif shape == "bull_call":
        pair = _pair(calls, spot)
        legs = [_leg(pair[0], "buy"), _leg(pair[1], "sell")] if pair else []
    elif shape == "bear_put":
        pair = _pair(puts, spot)
        legs = [_leg(pair[1], "buy"), _leg(pair[0], "sell")] if pair else []
    elif shape == "bull_put":
        pair = _pair(puts, spot)
        legs = [_leg(pair[1], "sell"), _leg(pair[0], "buy")] if pair else []
    elif shape == "bear_call":
        pair = _pair(calls, spot)
        legs = [_leg(pair[0], "sell"), _leg(pair[1], "buy")] if pair else []
    elif shape in {"straddle", "short_straddle", "strap", "strip"}:
        shared = _shared(calls, puts, spot)
        if not shared:
            return None
        call, put = shared
        side = "sell" if shape == "short_straddle" else "buy"
        if shape == "strap":
            legs = [_leg(call, "buy", 2), _leg(put, "buy")]
        elif shape == "strip":
            legs = [_leg(put, "buy", 2), _leg(call, "buy")]
        else:
            legs = [_leg(call, side), _leg(put, side)]
    elif shape in {"strangle", "short_strangle"}:
        up = _outside(_strikes(calls), spot, 1, True)
        dn = _outside(_strikes(puts), spot, 1, False)
        if not up or not dn:
            return None
        side = "sell" if shape == "short_strangle" else "buy"
        legs = [_leg(_at(calls, up[0]), side), _leg(_at(puts, dn[0]), side)]
    elif shape in {"butterfly_call", "condor_call"}:
        n = 3 if shape == "butterfly_call" else 4
        w = _window(_strikes(calls), spot, n)
        if not w:
            return None
        rows = [_at(calls, s) for s in w]
        if shape == "butterfly_call":
            legs = [_leg(rows[0], "buy"), _leg(rows[1], "sell", 2), _leg(rows[2], "buy")]
        else:
            legs = [_leg(rows[0], "buy"), _leg(rows[1], "sell"),
                    _leg(rows[2], "sell"), _leg(rows[3], "buy")]
    elif shape in {"butterfly_put", "condor_put"}:
        n = 3 if shape == "butterfly_put" else 4
        w = _window(_strikes(puts), spot, n)
        if not w:
            return None
        rows = [_at(puts, s) for s in w]
        if shape == "butterfly_put":
            legs = [_leg(rows[0], "buy"), _leg(rows[1], "sell", 2), _leg(rows[2], "buy")]
        else:
            legs = [_leg(rows[0], "buy"), _leg(rows[1], "sell"),
                    _leg(rows[2], "sell"), _leg(rows[3], "buy")]
    elif shape == "iron_butterfly":
        wings = _wings(calls, puts, spot)
        if not wings:
            return None
        call, put, cup, pdn = wings
        legs = [_leg(call, "sell"), _leg(put, "sell"), _leg(cup, "buy"), _leg(pdn, "buy")]
    elif shape == "iron_condor":
        up = _outside(_strikes(calls), spot, 2, True)
        dn = _outside(_strikes(puts), spot, 2, False)
        if not up or not dn:
            return None
        legs = [
            _leg(_at(puts, dn[1]), "sell"), _leg(_at(puts, dn[0]), "buy"),
            _leg(_at(calls, up[0]), "sell"), _leg(_at(calls, up[1]), "buy"),
        ]
    elif shape in {"calendar_call", "calendar_put"}:
        opt = "CALL" if shape == "calendar_call" else "PUT"
        legs = _calendar(chain, exps, spot, opt)
        if not legs:
            return None
    else:
        return None
    return _finish(t.name, thesis, shape, short, legs, chain)


def _calendar(chain, exps, spot, opt) -> list[StrategyLeg] | None:
    for i, near in enumerate(exps):
        near_rows = _quoted(chain, near, opt)
        for far in exps[i + 1:]:
            far_rows = _quoted(chain, far, opt)
            common = set(_strikes(near_rows)) & set(_strikes(far_rows))
            k = _closest(sorted(common), spot)
            if k is None:
                continue
            return [_leg(_at(near_rows, k), "sell"), _leg(_at(far_rows, k), "buy")]
    return None


def _vol_reason(t: Template, ensemble: EnsembleSignal, today: date, blackout: int) -> str | None:
    if t.vol != "short":
        return None
    parts = []
    if ensemble.volatility_view == "rising":
        parts.append("这个结构做空波动率，合成波动率视图是上升。")
    for c in ensemble.catalysts:
        if c.type == "earnings" and c.expected_date:
            gap = (c.expected_date - today).days
            if 0 <= gap <= blackout:
                parts.append(
                    f"这个结构做空波动率，引擎自述财报日 {c.expected_date} 在 {gap} 天内。"
                    "该日期不是富途事实。"
                )
            break
    return "".join(parts) or None


def _cash_reason(chain: ChainSnapshot | None, equity: float | None) -> str | None:
    if chain is None or chain.spot is None:
        return "没有现价，无法确认能担保 100 股。"
    need = chain.spot * _MULT
    if equity is None:
        return "没有账户现金记录，无法确认能担保 100 股。"
    if equity < need:
        return f"现金 {equity:.0f} 不够买下 100 股（现价 {chain.spot:.2f}）。"
    return None


def _screen_one(
    t: Template,
    ensemble: EnsembleSignal,
    chain: ChainSnapshot | None,
    *,
    equity: float | None,
    today: date,
    blackout: int,
    holds_shares: bool,
) -> tuple[str, str]:
    if t.no_formula:
        return "impossible", "没有单一盈亏公式。"
    if t.naked:
        return "impossible", "禁止裸卖。"
    if t.needs_shares and not holds_shares:
        return "impossible", "没有正股持仓记录。"
    if not _bias_ok(t.bias, ensemble.direction):
        need = {"bull": "看多", "bear": "看空", "neutral": "中性"}[t.bias]
        return "unfit", f"合成是{_dir_word(ensemble.direction)}，这个结构要{need}。"
    blocked = _vol_reason(t, ensemble, today, blackout)
    if blocked:
        return "unfit", blocked
    if t.cash_secured:
        cash = _cash_reason(chain, equity)
        if cash:
            return "impossible", cash
    return "fit", "方向与波动率都过了菜单。"


def screen_menu(
    ensemble: EnsembleSignal,
    chain: ChainSnapshot | None,
    *,
    account_equity: float | None = None,
    equity_currency: str | None = None,
    earnings_blackout_days: int = 10,
    min_open_interest: int = 100,
    max_spread_pct: float = 0.10,
    max_position_risk_pct: float = 0.05,
    holds_shares: bool = False,
    today: date | None = None,
) -> list[MenuVerdict]:
    today = today or ensemble.as_of
    out: list[MenuVerdict] = []
    for t in CATALOG:
        status, reason = _screen_one(
            t, ensemble, chain, equity=account_equity, today=today,
            blackout=earnings_blackout_days, holds_shares=holds_shares,
        )
        proposal, risk = None, None
        if status == "fit" and ensemble.market != "US":
            status, reason = "impossible", "港股本轮不按未知乘数选合约。"
        elif status == "fit" and (chain is None or chain.spot is None):
            status, reason = "impossible", "没有期权链，选不了合约。"
        elif status == "fit":
            proposal = _build(t, chain, today)
            if proposal is None:
                status, reason = "impossible", "链上凑不齐可报价的合约。"
            else:
                risk = check_proposal(
                    proposal, ensemble, chain,
                    earnings_blackout_days=earnings_blackout_days,
                    min_open_interest=min_open_interest,
                    max_spread_pct=max_spread_pct,
                    account_equity=account_equity,
                    equity_currency=equity_currency,
                    max_position_risk_pct=max_position_risk_pct,
                    today=today,
                )
                if t.shape in _UNLIMITED:
                    vetoes = [*risk.vetoes, "最大亏损无上限"]
                    risk = risk.model_copy(update={"approved": False, "vetoes": vetoes})
        out.append(MenuVerdict(t.name, status, reason, proposal, risk))
    return out


def render_menu(verdicts: list[MenuVerdict]) -> str:
    lines = ["## 结构菜单", ""]
    label = {"fit": "适合", "unfit": "不适合", "impossible": "做不了"}
    for v in verdicts:
        extra = ""
        if v.proposal:
            legs = "，".join(f"{lg.side} {lg.code} K={lg.strike}" for lg in v.proposal.legs)
            loss = "算不出" if v.proposal.max_loss is None else f"{v.proposal.max_loss:.0f}"
            extra = f"合约 {legs}。最大亏损 {loss}。"
            if v.risk and v.risk.vetoes:
                extra += "风控否决：" + "；".join(v.risk.vetoes) + "。"
            elif v.risk and v.risk.approved:
                extra += "风控通过。"
        note = strategy_blurb(v.name)
        gloss = f" 说明：{note}" if note else ""
        lines.append(f"- {label[v.status]} · {v.name}。{v.reason}{extra}{gloss}")
    return "\n".join(lines) + "\n"


def apply_user_bias(ensemble: EnsembleSignal, bias: str | None) -> EnsembleSignal:
    """用户看法只用于重筛菜单，不改原来的合成方向。"""
    mapped = {"bull": Direction.BUY, "bear": Direction.SELL, "neutral": Direction.NEUTRAL}
    if bias not in mapped:
        return ensemble
    return ensemble.model_copy(update={"direction": mapped[bias]})


def decision_action(verdicts: list[MenuVerdict]) -> str:
    ok = [v.name for v in verdicts if v.risk and v.risk.approved]
    if not ok:
        return "观望"
    return "可考虑 " + "、".join(ok)
