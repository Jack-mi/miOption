"""Shared, read-only US credit-vertical eligibility. No order authority."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from .payoff import conservative_credit, credit_vertical_payoff

EASTERN = ZoneInfo("America/New_York")
DEFAULTS = {
    "dte_min": 4, "dte_max": 60, "widths": (2.5, 5.0, 10.0, 20.0),
    "min_credit_risk_ratio": 0.10, "min_open_interest": 100,
    "max_spread_pct": 0.10, "max_position_risk_pct": 0.05,
    "earnings_blackout_days": 10, "drawdown_pct": 0.10, "min_conviction": 0.4,
    "quote_max_age_seconds": 60, "account_max_age_seconds": 300,
}


def market_time(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=EASTERN) if parsed.tzinfo is None else parsed.astimezone(EASTERN)
    except (TypeError, ValueError, OverflowError):
        return None


def _sessions(now: datetime):
    import exchange_calendars as xcals
    import pandas as pd

    calendar = xcals.get_calendar("XNYS")
    clock = market_time(now)
    session = pd.Timestamp(clock.date())
    if not calendar.is_session(session):
        session = calendar.date_to_session(session, direction="previous")
    market_open = calendar.session_open(session).to_pydatetime().astimezone(EASTERN)
    market_close = calendar.session_close(session).to_pydatetime().astimezone(EASTERN)
    return calendar, session, market_open, market_close


def _session_time(spot_at, short_at, long_at, now, source, config):
    stamps = [market_time(value) for value in (spot_at, short_at, long_at)]
    if source != "futu" or any(stamp is None for stamp in stamps):
        return "仅观察", ["延迟源或缺少逐腿/标的市场时间"]
    observed = [stamp for stamp in stamps if stamp is not None]
    if max(observed) - min(observed) > timedelta(seconds=config["quote_max_age_seconds"]):
        return "仅观察", ["标的与两腿报价不同步"]
    clock = market_time(now)
    if clock is None or any(stamp > clock for stamp in observed):
        return "仅观察", ["报价时间无效"]
    calendar, session, market_open, market_close = _sessions(now)
    if market_open <= clock < market_close:
        if all(stamp.date() == clock.date() and
               market_open <= stamp <= clock and
               clock - stamp <= timedelta(seconds=config["quote_max_age_seconds"]) for stamp in observed):
            return "可考虑", []
        return "仅观察", ["盘中报价超过时效"]
    if clock < market_close:
        session = calendar.previous_session(session)
        market_close = calendar.session_close(session).to_pydatetime().astimezone(EASTERN)
    if clock - market_close <= timedelta(days=3) and all(
        market_close - timedelta(minutes=5) <= stamp <= market_close
        for stamp in observed
    ):
        return "条件可考虑，开盘须重报价", []
    return "仅观察", ["非交易时段无可核验的收盘盘口"]


def drawdown_warning(closes: list[tuple[date, float]], now: datetime, pct: float) -> bool:
    """Only completed sessions; hold the flag until three non-new-low closes."""
    clock = market_time(now)
    if clock is None:
        return True
    calendar, _session, _open, market_close = _sessions(now)
    finished = sorted(((day, price) for day, price in closes if
                      calendar.is_session(day) and (day < clock.date() or
                      (day == clock.date() and clock >= market_close))), key=lambda item: item[0])
    expected = calendar.date_to_session(clock.date(), direction="previous")
    if clock < market_close:
        expected = calendar.previous_session(expected)
    if not finished or finished[-1][0] != expected.date():
        return True
    if len(finished) < 6:
        return True
    recent = calendar.sessions_window(expected, -6)
    if [day for day, _price in finished[-6:]] != [day.date() for day in recent]:
        return True
    prices = [price for _, price in finished]
    last_trigger = next((end for end in range(len(prices) - 1, 4, -1)
                         if prices[end] <= prices[end - 5] * (1 - pct)), None)
    if last_trigger is None:
        return False
    low = min(prices[:last_trigger + 1])
    stable = 0
    for price in prices[last_trigger + 1:]:
        if price < low:
            stable = 0
        else:
            stable += 1
        low = min(low, price)
    return stable < 3


def evaluate(
    short: dict, long: dict, *, spot: float, spot_at: str | None,
    source: str, now: datetime, account: dict | None, closes: list[tuple[date, float]],
    earnings: date | None, signal_ok: bool, review_ok: bool = True,
    complete: bool = True, config: dict | None = None,
    fetched_at: str | None = None,
    spot_fetched_at: str | None = None,
) -> dict:
    cfg = {**DEFAULTS, **(config or {})}
    reasons: list[str] = []
    blocking: list[str] = []
    opt = short.get("option_type")
    expiry = short.get("expiry")
    if isinstance(expiry, str):
        expiry = date.fromisoformat(expiry[:10])
    if isinstance(long.get("expiry"), str):
        long_expiry = date.fromisoformat(long["expiry"][:10])
    else:
        long_expiry = long.get("expiry")
    if opt not in ("PUT", "CALL") or opt != long.get("option_type") or expiry != long_expiry:
        blocking.append("不是同到期同类型价差")
    short_strike, long_strike = float(short.get("strike") or 0), float(long.get("strike") or 0)
    if not isfinite(short_strike) or not isfinite(long_strike):
        blocking.append("行权价无效")
    if not spot or not isfinite(spot) or spot <= 0:
        blocking.append("标的报价无效")
    if opt == "PUT" and not (long_strike < short_strike < spot):
        blocking.append("Put 价差行权价顺序或虚值条件不符")
    if opt == "CALL" and not (spot < short_strike < long_strike):
        blocking.append("Call 价差行权价顺序或虚值条件不符")
    bid, ask = float(short.get("bid") or 0), float(long.get("ask") or 0)
    credit = conservative_credit(short_bid=bid, long_ask=ask) if isfinite(bid) and isfinite(ask) else 0
    if not short.get("code") or not long.get("code") or short.get("code") == long.get("code"):
        blocking.append("合约代码缺失或重复")
    for leg in (short, long):
        if leg.get("contract_size") is None:
            reasons.append("合约乘数未知，按 100 股仅供研究估算")
        elif leg["contract_size"] != 100:
            blocking.append("非标准 100 股合约，不能使用本损益公式")
    if credit <= 0:
        blocking.append("保守买卖盘无法收到净权利金")
    for leg in (short, long):
        leg_bid, leg_ask = float(leg.get("bid") or 0), float(leg.get("ask") or 0)
        if not isfinite(leg_bid) or not isfinite(leg_ask) or leg_bid <= 0 or leg_ask <= 0 or leg_bid > leg_ask:
            blocking.append(f"{leg.get('code')} 无有效双边盘口")
        elif (leg_ask - leg_bid) / ((leg_ask + leg_bid) / 2) > cfg["max_spread_pct"]:
            reasons.append(f"{leg.get('code')} 买卖价差过宽")
        oi = leg.get("open_interest")
        if oi is None or oi < cfg["min_open_interest"]:
            reasons.append(f"{leg.get('code')} OI 不足或未知")
    payoff = None
    if not blocking:
        payoff = credit_vertical_payoff(
            "bull_put_spread" if opt == "PUT" else "bear_call_spread",
            short_strike=short_strike, long_strike=long_strike, credit=credit,
        )
        if payoff["max_loss"] <= 0:
            blocking.append("价差风险无法计算")
            payoff = None
        elif payoff["max_profit"] / payoff["max_loss"] < cfg["min_credit_risk_ratio"]:
            reasons.append(f"保守收益/最大亏损低于 {cfg['min_credit_risk_ratio']:.0%}")
    clock = market_time(now)
    if clock is None or expiry is None or not cfg["dte_min"] <= (expiry - clock.date()).days <= cfg["dte_max"]:
        blocking.append("到期日不在配置窗口内")
    tier, time_reasons = _session_time(spot_at, short.get("quoted_at"), long.get("quoted_at"), now, source, cfg)
    reasons.extend(time_reasons)
    for label, stamp_value in (("标的", spot_fetched_at), ("盘口", fetched_at), ("卖腿", short.get("fetched_at")),
                               ("买腿", long.get("fetched_at"))):
        fetched = market_time(stamp_value)
        if fetched is None or clock is None or fetched > clock or (
            tier == "可考虑" and clock - fetched > timedelta(seconds=cfg["quote_max_age_seconds"])
        ):
            reasons.append(f"{label}获取时间缺失或过期")
    if not complete:
        reasons.append("期权链未完整获取")
    if not signal_ok:
        reasons.append("信号不支持收租")
    if not review_ok:
        reasons.append("复核未通过")
    if earnings is None:
        reasons.append("财报日期未确认或缺失")
    elif clock and earnings < clock.date():
        reasons.append("下一次财报日期未确认")
    elif clock and clock.date() >= earnings - timedelta(days=cfg["earnings_blackout_days"]):
        reasons.append("进入预期财报缓冲窗口")
    if drawdown_warning(closes, now, cfg["drawdown_pct"]):
        reasons.append("五日急跌或缺少足够完成日线/恢复证据")
    stamp = market_time((account or {}).get("fetched_at"))
    try:
        equity = float((account or {}).get("value"))
    except (TypeError, ValueError):
        equity = float("nan")
    if not account or account.get("env") != "REAL" or account.get("currency") != "USD" or stamp is None or clock is None or not timedelta(0) <= clock - stamp <= timedelta(seconds=cfg["account_max_age_seconds"]):
        reasons.append("美元真实账户状态缺失或过期")
    elif account.get("available_cash_usd") is None or not isinstance(account.get("positions"), list):
        reasons.append("可用现金或正股持仓未核验")
    elif not isfinite(equity) or equity <= 0 or (payoff and payoff["max_loss"] >
                                                 equity * cfg["max_position_risk_pct"]):
        reasons.append("最大亏损超过账户敞口上限或账户权益未知")
    if blocking:
        tier = "禁做"
    elif reasons:
        tier = "仅观察"
    return {"tier": tier, "reasons": list(dict.fromkeys([*blocking, *reasons])),
            "credit": credit * 100, "max_loss": None if not payoff else payoff["max_loss"],
            "max_profit": None if not payoff else payoff["max_profit"],
            "breakeven": None if not payoff else payoff["breakeven"],
            "return_on_risk": None if not payoff or payoff["max_loss"] <= 0 else payoff["max_profit"] / payoff["max_loss"],
            "quote_at": [spot_at, short.get("quoted_at"), long.get("quoted_at")],
            "fetched_at": [fetched_at, short.get("fetched_at"), long.get("fetched_at")],
            "account_at": (account or {}).get("fetched_at")}


def candidates(rows: list[dict], spot: float, now: datetime, config: dict | None = None) -> list[tuple[dict, dict]]:
    cfg = {**DEFAULTS, **(config or {})}
    by_group: dict[tuple[date, str], list[dict]] = {}
    if not isfinite(spot) or spot <= 0 or market_time(now) is None:
        return []
    for row in rows:
        try:
            exp = row.get("expiry")
            exp = date.fromisoformat(exp[:10]) if isinstance(exp, str) else exp
            strike = float(row["strike"])
        except (KeyError, TypeError, ValueError):
            continue
        if (not isinstance(exp, date) or not isfinite(strike) or
                row.get("option_type") not in ("PUT", "CALL") or
                not cfg["dte_min"] <= (exp - market_time(now).date()).days <= cfg["dte_max"]):
            continue
        by_group.setdefault((exp, row["option_type"]), []).append(row)
    out = []
    for (_exp, opt), contracts in by_group.items():
        indexed = {float(row["strike"]): row for row in contracts}
        for strike, short in indexed.items():
            if (opt == "PUT" and strike >= spot) or (opt == "CALL" and strike <= spot):
                continue
            for width in cfg["widths"]:
                long = indexed.get(strike - width if opt == "PUT" else strike + width)
                if long:
                    out.append((short, long))
    return out
