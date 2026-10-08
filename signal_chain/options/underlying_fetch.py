"""标的快照编排：Futu 报价/日线为主。失败时由数据层降级 FMP。

资金流、基本面、新闻本轮只占位，不取数。覆盖账本只写状态与来源，不写价格。

手工探测:
  .venv-sc/bin/python -m signal_chain.options.underlying_fetch --tickers US.AAPL,HK.00700
"""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..config import REPO_ROOT, require_runtime_python, NormTicker, Settings
from ..sessions import align_futu_quote, session_for
from ..schema.underlying import (
    DailyBar,
    DividendEvent,
    DividendField,
    FieldMeta,
    KlineField,
    QuoteField,
    TechnicalField,
    UnderlyingSnapshot,
    VolBasisField,
)

_BRIDGE_TIMEOUT = 45
_TZ = {"US": "America/New_York", "HK": "Asia/Hong_Kong"}
_CCY = {"US": "USD", "HK": "HKD"}


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
            "market_time": m.market_time,
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
        "dividends": {
            **meta(snapshot.dividends.meta),
            "next_ex_date": (snapshot.dividends.next_ex_date.isoformat()
                             if snapshot.dividends.next_ex_date else None),
            "item_count": len(snapshot.dividends.items),
        },
        "vol_basis": {
            **meta(snapshot.vol_basis.meta),
            "has_ratio": snapshot.vol_basis.ratio is not None,
        },
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
    observed_at = raw.get("observed_at") if source == "futu" and raw else None
    if observed_at:
        try:
            fetched_at = datetime.fromisoformat(observed_at)
        except (TypeError, ValueError):
            pass
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
                error=f"报价交易日 {session.isoformat()} 不是这场交易 {trade_date.isoformat()}",
            ),
            currency=currency,  # type: ignore[arg-type]
        )
    return QuoteField(
        meta=FieldMeta(
            status="available", source=source, as_of=session, fetched_at=fetched_at,
            market_time=raw.get("update_time") if raw else None,
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
    if last != trade_date:
        return KlineField(
            meta=FieldMeta(
                status="stale", source=source, as_of=last, fetched_at=fetched_at, timezone=tz,
                error=f"日线最后交易日 {last.isoformat()} 不是这场交易 {trade_date.isoformat()}",
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


def _hk_fundamentals_field(raw: dict | None, fetched_at: datetime, tz: str) -> FieldMeta:
    if not raw or raw.get("error") or not raw.get("period") or not raw.get("as_of"):
        return FieldMeta(
            status="missing", source="futu_financials", fetched_at=fetched_at,
            timezone=tz, error=(raw or {}).get("error") or "Futu 无财务报表",
        )
    return FieldMeta(
        status="available", source="futu_financials",
        as_of=date.fromisoformat(str(raw["as_of"])[:10]), fetched_at=fetched_at,
        timezone=tz, period=str(raw["period"]),
    )


def _futu_dividends_field(raw: dict | None, session: date, fetched_at: datetime,
                          tz: str) -> DividendField:
    """派息记录。空列表是"没有派息"，跟取数失败要分开写。"""
    raw = raw or {}
    items = []
    for row in raw.get("items") or []:
        ex_date = _as_date(row.get("ex_date"))
        if ex_date is None:
            continue
        items.append(DividendEvent(
            ex_date=ex_date,
            record_date=_as_date(row.get("record_date")),
            payable_date=_as_date(row.get("payable_date")),
            pub_date=_as_date(row.get("pub_date")),
            statement=row.get("statement"),
        ))
    if raw.get("error"):
        return DividendField(meta=FieldMeta(
            status="missing", source="futu_dividends", fetched_at=fetched_at, timezone=tz,
            error=str(raw["error"])[:400],
        ))
    if not items:
        return DividendField(meta=FieldMeta(
            status="missing", source="futu_dividends", as_of=session, fetched_at=fetched_at,
            timezone=tz, error="无派息记录",
        ))
    upcoming = [item.ex_date for item in items if item.ex_date >= session]
    return DividendField(
        meta=FieldMeta(
            status="available", source="futu_dividends", as_of=session,
            fetched_at=fetched_at, timezone=tz,
        ),
        items=items,
        next_ex_date=min(upcoming) if upcoming else None,
    )


def _futu_vol_basis_field(raw: dict | None, session: date, fetched_at: datetime,
                          tz: str) -> VolBasisField:
    raw = raw or {}
    if raw.get("error") or raw.get("ratio") is None:
        return VolBasisField(meta=FieldMeta(
            status="missing", source="futu_vol_basis", fetched_at=fetched_at, timezone=tz,
            error=str(raw.get("error") or "无 IV/HV 基准")[:400],
        ))
    as_of = _as_date(raw.get("as_of")) or session
    return VolBasisField(
        meta=FieldMeta(
            status="available", source="futu_vol_basis", as_of=as_of,
            fetched_at=fetched_at, timezone=tz,
        ),
        iv_latest=raw.get("iv_latest"),
        hv_latest=raw.get("hv_latest"),
        iv_rank=raw.get("iv_rank"),
        hv_rank=raw.get("hv_rank"),
        ratio=raw.get("ratio"),
    )


def _futu_news_field(raw: list | None, session: date, fetched_at: datetime, tz: str) -> tuple[FieldMeta, str | None]:
    rows = [row for row in (raw or []) if row.get("title")]
    if not rows:
        return FieldMeta(
            status="missing", source="futu_news", as_of=session, fetched_at=fetched_at,
            timezone=tz, error="Futu 无新闻",
        ), None
    dates = [row.get("published") for row in rows if row.get("published")]
    as_of = date.fromisoformat(max(dates)[:10]) if dates else session
    text = "\n".join(f"{row['title']}（{row.get('source') or 'futu_news'}）" for row in rows)
    return FieldMeta(
        status="available", source="futu_news", as_of=as_of, fetched_at=fetched_at,
        timezone=tz,
    ), text


def _pick(primary, secondary, *, futu_error: str | None, fallback_error: str | None):
    """主源可用则用主源；否则仅在降级源 available 时替换，并写明 Futu 失败原因。"""
    if primary.meta.status == "available":
        return primary
    if secondary.meta.status == "available":
        why = primary.meta.error or futu_error or "futu 不可用"
        label = secondary.meta.source or "降级源"
        return _with_error(secondary, f"Futu 未采用（{why}），已降级 {label}")
    extra = fallback_error or (secondary.meta.error if secondary.meta.status != "available" else None)
    if extra and primary.meta.error and extra not in primary.meta.error:
        return _with_error(primary, f"{primary.meta.error}；降级: {extra}")
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
    fallback: dict | None = None,
    fallback_error: str | None = None,
    fallback_source: str = "fmp",
    kline_session: date | None = None,
) -> UnderlyingSnapshot:
    """把富途探测和可选降级源收成一份快照。as_of 是这场交易日，不是运行日。"""
    if market not in _CCY:
        raise ValueError(f"本轮仅支持美/港标的，收到 {market}")
    session = session_for(market, trade_date, now=fetched_at)
    tz = _TZ[market]
    currency = _CCY[market]
    futu = align_futu_quote(futu) if market == "US" else futu
    if market == "HK" and futu:
        futu = align_futu_quote(futu, market="HK")
    futu = futu or {}
    fallback = fallback or {}
    quote = _pick(
        _quote_field(futu.get("quote"), source="futu" if futu else None, trade_date=session,
                     fetched_at=fetched_at, tz=tz, currency=currency, prior_error=futu_error),
        _quote_field(fallback.get("quote"), source=fallback_source if fallback else None, trade_date=session,
                     fetched_at=fetched_at, tz=tz, currency=currency, prior_error=fallback_error),
        futu_error=futu_error, fallback_error=fallback_error,
    )
    kline = _pick(
        _kline_field(futu.get("kline"), source="futu" if futu else None, trade_date=kline_session or session,
                     fetched_at=fetched_at, tz=tz, prior_error=futu_error),
        _kline_field(fallback.get("kline"), source=fallback_source if fallback else None, trade_date=kline_session or session,
                     fetched_at=fetched_at, tz=tz, prior_error=fallback_error),
        futu_error=futu_error, fallback_error=fallback_error,
    )
    fundamentals = (
        _hk_fundamentals_field(futu.get("financials"), fetched_at, tz)
        if market == "HK" else FieldMeta(status="unsupported", error="本轮不接入基本面")
    )
    news_meta, news_text = (
        _futu_news_field(futu.get("news"), session, fetched_at, tz)
        if market == "HK" else (FieldMeta(status="unsupported", error="本轮不接入新闻"), None)
    )
    return UnderlyingSnapshot(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        currency=currency,  # type: ignore[arg-type]
        as_of=session,
        fetched_at=fetched_at,
        quote=quote,
        kline=kline,
        technical=_technical(kline, kline_session or session, fetched_at, tz),
        fundamentals=fundamentals,
        news=news_meta,
        dividends=_futu_dividends_field(futu.get("dividends"), session, fetched_at, tz),
        vol_basis=_futu_vol_basis_field(futu.get("vol_basis"), session, fetched_at, tz),
    )


def _json_line(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if line.strip().startswith("{"):
            return json.loads(line)
    return None


def probe_futu(t: NormTicker, trade_date: date, settings: Settings,
               history_start: date | None = None) -> tuple[dict | None, str | None]:
    cfg = settings.chain
    try:
        runtime_py = require_runtime_python()
    except FileNotFoundError as exc:
        return None, str(exc)
    cmd = [
        str(runtime_py), "-m", "signal_chain.options.underlying_bridge",
        t.futu_format, trade_date.isoformat(),
        str(cfg["futu_opend_host"]), str(cfg["futu_opend_port"]),
        "--scan-days", str(cfg.get("dividends_scan_days", 60)),
    ]
    if history_start is not None:
        cmd.append(history_start.isoformat())
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


def _futu_field_fresh(payload: dict | None, session: date, kind: str) -> bool:
    if not payload:
        return False
    day = session.isoformat()
    if kind == "quote":
        quote = payload.get("quote") or {}
        return quote.get("last") is not None and str(quote.get("session_date") or "")[:10] == day
    bars = (payload.get("kline") or {}).get("bars") or []
    dates = [str(b.get("trade_date") or "")[:10] for b in bars if b.get("trade_date")]
    return bool(dates) and max(dates) == day


def fetch_underlying(t: NormTicker, trade_date: date, settings: Settings) -> UnderlyingSnapshot:
    """只读探测。OpenD 失败留下状态，不把失败记成可用。"""
    if t.market not in _CCY:
        raise ValueError(f"本轮仅支持美/港标的，收到 {t.canonical}")
    fetched_at = datetime.now(timezone.utc)
    futu, futu_error = probe_futu(t, trade_date, settings)
    return build_snapshot(
        ticker=t.canonical,
        market=t.market,
        trade_date=trade_date,
        fetched_at=fetched_at,
        futu=futu,
        futu_error=futu_error,
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
