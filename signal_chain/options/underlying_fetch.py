"""标的快照编排：Futu 报价/日线为主，失败时按字段降级 yfinance。

资金流、基本面、新闻本轮只占位，不取数。覆盖账本只写状态与来源，不写价格。

手工探测:
  .venv-sc/bin/python -m signal_chain.options.underlying_fetch --tickers US.AAPL,HK.00700
"""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..config import REPO_ROOT, RUNTIME_VENV_PY, NormTicker, Settings
from ..schema.underlying import (
    DailyBar,
    FieldMeta,
    KlineField,
    QuoteField,
    TechnicalField,
    UnderlyingSnapshot,
)

_BRIDGE_TIMEOUT = 45
_TZ = {"US": "America/New_York", "HK": "Asia/Hong_Kong"}
_CCY = {"US": "USD", "HK": "HKD"}
# 日 K 在收盘前往往停在上一交易日。超过 4 个自然日视为过期，避免把旧价当成今日日线。
_KLINE_LAG_DAYS = 4


def coverage_entry(snapshot: UnderlyingSnapshot, sources: list | None = None) -> dict[str, Any]:
    """脱敏账本：状态、来源、时点、错误。不含价格和指标值。"""

    def meta(m: FieldMeta) -> dict[str, Any]:
        return {
            "status": m.status,
            "source": m.source,
            "as_of": m.as_of.isoformat() if m.as_of else None,
            "fetched_at": m.fetched_at.isoformat() if m.fetched_at else None,
            "timezone": m.timezone,
            "error": m.error,
            "period": m.period,
        }

    entry = {
        "ticker": snapshot.ticker,
        "market": snapshot.market,
        "currency": snapshot.currency,
        "as_of": snapshot.as_of.isoformat(),
        "quote": meta(snapshot.quote.meta),
        "kline": {
            **meta(snapshot.kline.meta),
            "adjusted": snapshot.kline.adjusted,
            "bar_count": len(snapshot.kline.bars),
        },
        "technical": {
            **meta(snapshot.technical.meta),
            "indicator_names": sorted(snapshot.technical.indicators),
        },
        "capital_flow": meta(snapshot.capital_flow),
        "fundamentals": meta(snapshot.fundamentals),
        "news": meta(snapshot.news),
        "earnings_source": snapshot.earnings_source,
    }
    if sources:
        entry["sources"] = [
            {"id": s.id, "field": s.field, "state": s.state, "note": s.note}
            for s in sources
        ]
    return entry


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _quote_field(
    raw: dict | None,
    *,
    source: str | None,
    trade_date: date,
    fetched_at: datetime,
    tz: str,
    currency: str,
    prior_error: str | None,
) -> QuoteField:
    last = None if raw is None else raw.get("last")
    session = _as_date(None if raw is None else raw.get("session_date"))
    err = prior_error if raw is None else (raw.get("error") or prior_error)
    if last is None or session is None:
        return QuoteField(
            meta=FieldMeta(
                status="missing", source=source, fetched_at=fetched_at, timezone=tz,
                error=err or "无报价",
            ),
            currency=currency,  # type: ignore[arg-type]
        )
    if session != trade_date:
        return QuoteField(
            meta=FieldMeta(
                status="stale", source=source, as_of=session, fetched_at=fetched_at,
                timezone=tz,
                error=f"报价交易日 {session.isoformat()} 不是运行日 {trade_date.isoformat()}",
            ),
            currency=currency,  # type: ignore[arg-type]
        )
    return QuoteField(
        meta=FieldMeta(
            status="available", source=source, as_of=session, fetched_at=fetched_at,
            timezone=tz,
        ),
        currency=currency,  # type: ignore[arg-type]
        last=float(last),
    )


def _kline_field(
    raw: dict | None,
    *,
    source: str | None,
    trade_date: date,
    fetched_at: datetime,
    tz: str,
    prior_error: str | None,
) -> KlineField:
    err = prior_error if raw is None else (raw.get("error") or prior_error)
    bars_raw = [] if raw is None else (raw.get("bars") or [])
    parsed: list[DailyBar] = []
    for row in bars_raw:
        session = _as_date(row.get("trade_date"))
        close = row.get("close")
        if session is None or close is None or row.get("open") is None:
            continue
        parsed.append(DailyBar(
            trade_date=session,
            open=float(row["open"]),
            high=float(row["high"]) if row.get("high") is not None else float(row["open"]),
            low=float(row["low"]) if row.get("low") is not None else float(row["open"]),
            close=float(close),
            volume=None if row.get("volume") is None else float(row["volume"]),
        ))
    parsed.sort(key=lambda b: b.trade_date)
    adjusted = None if raw is None else raw.get("adjusted")
    if not parsed:
        return KlineField(
            meta=FieldMeta(
                status="missing", source=source, fetched_at=fetched_at, timezone=tz,
                error=err or "无日线",
            ),
            adjusted=adjusted,
        )
    last = parsed[-1].trade_date
    lag = (trade_date - last).days
    if last > trade_date or lag > _KLINE_LAG_DAYS:
        return KlineField(
            meta=FieldMeta(
                status="stale", source=source, as_of=last, fetched_at=fetched_at, timezone=tz,
                error=f"日线最后交易日 {last.isoformat()} 距运行日 {trade_date.isoformat()} 超过 {_KLINE_LAG_DAYS} 天",
            ),
            adjusted=adjusted,
        )
    return KlineField(
        meta=FieldMeta(
            status="available", source=source, as_of=last, fetched_at=fetched_at, timezone=tz,
        ),
        adjusted=bool(adjusted),
        bars=parsed,
    )


def _with_error(field, message: str):
    meta = field.meta.model_copy(update={"error": message})
    return field.model_copy(update={"meta": meta})


def _pick(primary, secondary, *, futu_error: str | None, yahoo_error: str | None):
    """主源可用则用主源；否则仅在降级源 available 时替换，并写明 Futu 失败原因。"""
    if primary.meta.status == "available":
        return primary
    if secondary.meta.status == "available":
        why = primary.meta.error or futu_error or "futu 不可用"
        return _with_error(secondary, f"Futu 未采用（{why}），已降级 yfinance")
    extra = yahoo_error or (secondary.meta.error if secondary.meta.status != "available" else None)
    if extra and primary.meta.error and extra not in primary.meta.error:
        return _with_error(primary, f"{primary.meta.error}；yfinance: {extra}")
    if primary.meta.source or primary.meta.error:
        return primary
    return secondary


def _technical(kline: KlineField, trade_date: date, fetched_at: datetime, tz: str) -> TechnicalField:
    if kline.meta.status != "available":
        return TechnicalField(meta=FieldMeta(
            status="missing" if kline.meta.status == "missing" else kline.meta.status,
            source=kline.meta.source,
            as_of=kline.meta.as_of,
            fetched_at=fetched_at,
            timezone=tz,
            error="日线不可用，不计算技术指标",
        ))
    if len(kline.bars) < 5:
        return TechnicalField(meta=FieldMeta(
            status="missing", source=kline.meta.source, as_of=kline.meta.as_of,
            fetched_at=fetched_at, timezone=tz,
            error="日线不足 5 根，无法计算 SMA5",
        ))
    sma = round(sum(b.close for b in kline.bars[-5:]) / 5, 4)
    return TechnicalField(
        meta=FieldMeta(
            status="available", source=kline.meta.source, as_of=kline.bars[-1].trade_date,
            fetched_at=fetched_at, timezone=tz,
        ),
        indicators={"sma_5": sma},
    )


def build_snapshot(
    *,
    ticker: str,
    market: str,
    trade_date: date,
    fetched_at: datetime,
    futu: dict | None = None,
    futu_error: str | None = None,
    yahoo: dict | None = None,
    yahoo_error: str | None = None,
) -> UnderlyingSnapshot:
    """把两次探测收成一份快照。过期价格清掉，不带进 available。"""
    if market not in _CCY:
        raise ValueError(f"本轮仅支持美/港标的，收到 {market}")
    tz = _TZ[market]
    currency = _CCY[market]
    futu = futu or {}
    yahoo = yahoo or {}
    quote = _pick(
        _quote_field(futu.get("quote"), source="futu" if futu else None, trade_date=trade_date,
                     fetched_at=fetched_at, tz=tz, currency=currency, prior_error=futu_error),
        _quote_field(yahoo.get("quote"), source="yfinance" if yahoo else None, trade_date=trade_date,
                     fetched_at=fetched_at, tz=tz, currency=currency, prior_error=yahoo_error),
        futu_error=futu_error, yahoo_error=yahoo_error,
    )
    kline = _pick(
        _kline_field(futu.get("kline"), source="futu" if futu else None, trade_date=trade_date,
                     fetched_at=fetched_at, tz=tz, prior_error=futu_error),
        _kline_field(yahoo.get("kline"), source="yfinance" if yahoo else None, trade_date=trade_date,
                     fetched_at=fetched_at, tz=tz, prior_error=yahoo_error),
        futu_error=futu_error, yahoo_error=yahoo_error,
    )
    return UnderlyingSnapshot(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        currency=currency,  # type: ignore[arg-type]
        as_of=trade_date,
        fetched_at=fetched_at,
        quote=quote,
        kline=kline,
        technical=_technical(kline, trade_date, fetched_at, tz),
    )


def _json_line(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.strip().startswith("{"):
            return json.loads(line)
    return None


def probe_futu(t: NormTicker, trade_date: date, settings: Settings) -> tuple[dict | None, str | None]:
    cfg = settings.chain
    cmd = [
        str(RUNTIME_VENV_PY), "-m", "signal_chain.options.underlying_bridge",
        t.futu_format, trade_date.isoformat(),
        str(cfg["futu_opend_host"]), str(cfg["futu_opend_port"]),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_BRIDGE_TIMEOUT, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return None, "futu 探测超时"
    payload = _json_line(proc.stdout)
    if proc.returncode != 0:
        err = (payload or {}).get("error") or proc.stderr.strip()[:400] or f"rc={proc.returncode}"
        return None, f"futu: {err}"
    if payload is None:
        return None, f"futu 无 JSON 输出: {proc.stderr.strip()[:200]}"
    return payload, None


def probe_yahoo(t: NormTicker, trade_date: date) -> tuple[dict | None, str | None]:
    try:
        import yfinance as yf
        from zoneinfo import ZoneInfo

        hist = yf.Ticker(t.ta_format).history(
            start=trade_date - timedelta(days=120),
            end=trade_date + timedelta(days=1),
            interval="1d",
            auto_adjust=True,
        )
    except Exception as exc:
        return None, str(exc)[:400]
    if hist is None or hist.empty:
        return None, f"yfinance: {t.ta_format} 无日线"
    idx = hist.index
    tz = ZoneInfo(_TZ[t.market])
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert(tz)
    bars = []
    for ts, row in zip(idx, hist.itertuples(index=False)):
        session = ts.date()
        if session > trade_date:
            continue
        close = getattr(row, "Close", None)
        open_ = getattr(row, "Open", None)
        if close is None or open_ is None:
            continue
        try:
            close_f = float(close)
            open_f = float(open_)
        except (TypeError, ValueError):
            continue
        if close_f != close_f or open_f != open_f:
            continue
        high = getattr(row, "High", open_f)
        low = getattr(row, "Low", open_f)
        volume = getattr(row, "Volume", None)
        bars.append({
            "trade_date": session.isoformat(),
            "open": open_f,
            "high": float(high),
            "low": float(low),
            "close": close_f,
            "volume": None if volume is None else float(volume),
        })
    if not bars:
        return None, f"yfinance: {t.ta_format} 无有效日线"
    last = bars[-1]
    return {
        "quote": {"last": last["close"], "session_date": last["trade_date"], "error": None},
        "kline": {"adjusted": True, "bars": bars, "error": None},
    }, None


def _futu_field_fresh(payload: dict | None, trade_date: date, kind: str) -> bool:
    if not payload:
        return False
    day = trade_date.isoformat()
    if kind == "quote":
        quote = payload.get("quote") or {}
        return quote.get("last") is not None and quote.get("session_date") == day
    bars = (payload.get("kline") or {}).get("bars") or []
    dates = [b.get("trade_date") for b in bars if b.get("trade_date")]
    if not dates:
        return False
    last = date.fromisoformat(max(dates))
    lag = (trade_date - last).days
    return last <= trade_date and lag <= _KLINE_LAG_DAYS


def fetch_underlying(t: NormTicker, trade_date: date, settings: Settings) -> UnderlyingSnapshot:
    """只读探测。OpenD 或 Yahoo 失败都留下状态，不把失败记成可用。"""
    if t.market not in _CCY:
        raise ValueError(f"本轮仅支持美/港标的，收到 {t.canonical}")
    fetched_at = datetime.now(timezone.utc)
    futu, futu_error = probe_futu(t, trade_date, settings)
    yahoo, yahoo_error = (None, None)
    if not _futu_field_fresh(futu, trade_date, "quote") or not _futu_field_fresh(futu, trade_date, "kline"):
        yahoo, yahoo_error = probe_yahoo(t, trade_date)
    return build_snapshot(
        ticker=t.canonical,
        market=t.market,
        trade_date=trade_date,
        fetched_at=fetched_at,
        futu=futu,
        futu_error=futu_error,
        yahoo=yahoo,
        yahoo_error=yahoo_error,
    )


def main() -> None:
    import argparse

    from ..config import load_settings, parse_ticker
    from ..storage import write_coverage

    parser = argparse.ArgumentParser(description="只读探测报价与日线，并写脱敏覆盖账本")
    parser.add_argument("--tickers", default="US.AAPL,HK.00700")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    settings = load_settings()
    trade_date = date.fromisoformat(args.date)
    for text in args.tickers.split(","):
        t = parse_ticker(text)
        snap = fetch_underlying(t, trade_date, settings)
        path = write_coverage(trade_date, t.canonical, snap)
        entry = coverage_entry(snap)
        print(
            f"{t.canonical} quote={entry['quote']['status']} "
            f"kline={entry['kline']['status']} technical={entry['technical']['status']} "
            f"-> {path}"
        )


if __name__ == "__main__":
    main()
