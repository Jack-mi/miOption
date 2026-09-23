"""yfinance 期权链（美股降级源 + IV 数据源）。免费、有延迟，不作主源。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ..schema import ChainSnapshot, OptionRow


def _f(v):
    try:
        f = float(v)
        return f if f == f else None  # NaN -> None
    except (TypeError, ValueError):
        return None


def _i(v):
    f = _f(v)
    return None if f is None else int(f)


def fetch_chain_yfinance(ta_ticker: str, market: str, canonical: str,
                         window_days: int = 60) -> ChainSnapshot:
    import yfinance as yf

    t = yf.Ticker(ta_ticker)
    today = date.today()
    horizon = today + timedelta(days=window_days)
    expiries = [
        e for e in t.options
        if today <= datetime.strptime(e, "%Y-%m-%d").date() <= horizon
    ]
    if not expiries:
        raise RuntimeError(f"yfinance: {ta_ticker} 在 {window_days} 天内无期权到期日")

    spot = None
    try:
        spot = float(t.fast_info["last_price"])
    except Exception:
        pass

    rows: list[OptionRow] = []
    for exp in expiries:
        chain = t.option_chain(exp)
        for df, opt_type in ((chain.calls, "CALL"), (chain.puts, "PUT")):
            for _, r in df.iterrows():
                rows.append(OptionRow(
                    code=str(r.get("contractSymbol", "")),
                    strike=float(r["strike"]),
                    expiry=datetime.strptime(exp, "%Y-%m-%d").date(),
                    option_type=opt_type,  # type: ignore[arg-type]
                    bid=_f(r.get("bid")),
                    ask=_f(r.get("ask")),
                    last=_f(r.get("lastPrice")),
                    iv=_f(r.get("impliedVolatility")),
                    delta=None,
                    open_interest=_i(r.get("openInterest")),
                    volume=_i(r.get("volume")),
                ))

    return ChainSnapshot(
        ticker=canonical,
        market=market,  # type: ignore[arg-type]
        as_of=today,
        fetched_at=datetime.now(timezone.utc),
        source="yfinance",
        spot=spot,
        rows=rows,
        degraded=False,
        notes="yfinance 降级源：数据有延迟，仅供交叉验证",
    )
