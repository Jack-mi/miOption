"""Watchlist scan → defined-risk credit vertical cards. OpenD only; no OSM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable

from ..futu.quote import OptionContract, QuoteBackend
from ..futu.quote_store import QuoteStore
from .cards import WIKI_PATHS, LegQuote, SellerCard, card_id
from .payoff import StructureId, conservative_credit, credit_vertical_payoff
from .store import SellerStore

DEFAULT_WATCHLIST = (
    "US.SPY",
    "US.QQQ",
    "US.AAPL",
    "US.TSLA",
    "US.NVDA",
    "US.AMD",
    "US.META",
    "US.BIDU",
)

# Common names people type in the H5 search box → Futu codes.
SYMBOL_ALIASES = {
    "nvidia": "US.NVDA",
    "nvda": "US.NVDA",
    "spy": "US.SPY",
    "qqq": "US.QQQ",
    "aapl": "US.AAPL",
    "apple": "US.AAPL",
    "tsla": "US.TSLA",
    "tesla": "US.TSLA",
    "amd": "US.AMD",
    "meta": "US.META",
    "facebook": "US.META",
    "bidu": "US.BIDU",
    "baidu": "US.BIDU",
    "百度": "US.BIDU",
}


def resolve_symbol(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    key = "".join(text.casefold().split())
    if key in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[key]
    compact = text.replace(" ", "").upper()
    if "." in compact:
        market, _, ticker = compact.partition(".")
        if market in ("US", "HK", "SH", "SZ") and re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", ticker):
            return f"{market}.{ticker}"
        return ""
    if re.fullmatch(r"[A-Z0-9]{1,20}", compact):
        return f"US.{compact}"
    return ""


def resolve_underlyings(raw: Iterable[str] | str | None) -> list[str]:
    if raw is None:
        return list(DEFAULT_WATCHLIST)
    if isinstance(raw, str):
        parts = [p for p in re.split(r"[,;\s]+", raw) if p.strip()]
    else:
        parts = [str(p).strip() for p in raw if str(p).strip()]
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        code = resolve_symbol(part)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


@dataclass
class ScanParams:
    dte_min: int = 5
    dte_max: int = 21
    widths: tuple[float, ...] = (5.0, 10.0)
    short_delta_abs_min: float = 0.15
    short_delta_abs_max: float = 0.35
    min_distance_pct: float = 0.03
    max_spread_vs_mid: float = 0.5
    min_credit: float = 0.15
    strike_tol: float = 0.26


def _expiry_date(raw: str) -> date:
    return date.fromisoformat(str(raw)[:10])


def _dte(expiry: str, today: date) -> int:
    return (_expiry_date(expiry) - today).days


def _leg_spread_ok(leg: OptionContract, max_spread_vs_mid: float) -> bool:
    mid = leg.mid()
    if mid <= 0:
        return False
    if leg.bid <= 0 or leg.ask <= 0:
        return False
    return (leg.ask - leg.bid) / mid <= max_spread_vs_mid


def _delta_ok(leg: OptionContract, params: ScanParams) -> bool:
    if leg.delta is None:
        return True
    mag = abs(float(leg.delta))
    return params.short_delta_abs_min <= mag <= params.short_delta_abs_max


def overlay_snapshot(contract: OptionContract, snap: dict[str, Any]) -> OptionContract:
    bid = float(snap.get("bid_price") or snap.get("bid") or contract.bid or 0)
    ask = float(snap.get("ask_price") or snap.get("ask") or contract.ask or 0)
    last = float(snap.get("last_price") or snap.get("last") or contract.last or 0)
    delta = snap.get("option_delta")
    if delta is None:
        delta = snap.get("delta", contract.delta)
    try:
        delta_f = float(delta) if delta is not None and str(delta) not in ("", "nan", "NaN") else contract.delta
    except (TypeError, ValueError):
        delta_f = contract.delta
    return OptionContract(
        code=contract.code,
        underlying=contract.underlying,
        strike=contract.strike,
        expiry=contract.expiry,
        option_type=contract.option_type,
        bid=bid,
        ask=ask,
        last=last,
        delta=delta_f,
    )


def _by_expiry_type(chain: Iterable[OptionContract]) -> dict[tuple[str, str], list[OptionContract]]:
    grouped: dict[tuple[str, str], list[OptionContract]] = {}
    for c in chain:
        key = (str(c.expiry)[:10], c.option_type)
        grouped.setdefault(key, []).append(c)
    for rows in grouped.values():
        rows.sort(key=lambda x: x.strike)
    return grouped


def credit_vertical_candidates(
    underlying: str,
    spot: float,
    chain: list[OptionContract],
    *,
    today: date | None = None,
    params: ScanParams | None = None,
) -> list[SellerCard]:
    """Pure structure picker. Tests pass a BIDU-like chain; live scan feeds OpenD quotes."""
    params = params or ScanParams()
    today = today or date.today()
    grouped = _by_expiry_type(chain)
    cards: list[SellerCard] = []
    for (exp, opt), rows in grouped.items():
        dte = _dte(exp, today)
        if dte < params.dte_min or dte > params.dte_max:
            continue
        if opt == "PUT":
            cards.extend(
                _puts(
                    underlying,
                    spot,
                    exp,
                    dte,
                    rows,
                    params,
                )
            )
        elif opt == "CALL":
            cards.extend(
                _calls(
                    underlying,
                    spot,
                    exp,
                    dte,
                    rows,
                    params,
                )
            )
    cards.sort(key=lambda c: (c.underlying, c.expiry, c.structure_id, -c.credit))
    return cards


def _match_strike(rows: list[OptionContract], target: float, tol: float) -> OptionContract | None:
    for row in rows:
        if abs(row.strike - target) <= tol:
            return row
    return None


def _build(
    *,
    structure_id: StructureId,
    underlying: str,
    spot: float,
    dte: int,
    short: OptionContract,
    long: OptionContract,
    distance_pct: float,
    passed: list[str],
) -> SellerCard | None:
    credit = conservative_credit(short_bid=short.bid, long_ask=long.ask)
    if credit < 0:
        return None
    try:
        pay = credit_vertical_payoff(
            structure_id,
            short_strike=short.strike,
            long_strike=long.strike,
            credit=credit,
        )
    except ValueError:
        return None
    cid = card_id(underlying, short.expiry, structure_id, short.strike, long.strike)
    return SellerCard(
        id=cid,
        underlying=underlying,
        structure_id=structure_id,
        wiki_path=WIKI_PATHS[structure_id],
        expiry=str(short.expiry)[:10],
        spot=spot,
        dte=dte,
        short=LegQuote(
            code=short.code,
            side="SELL",
            option_type=short.option_type,
            strike=short.strike,
            expiry=str(short.expiry)[:10],
            bid=short.bid,
            ask=short.ask,
            last=short.last,
            delta=short.delta,
        ),
        long=LegQuote(
            code=long.code,
            side="BUY",
            option_type=long.option_type,
            strike=long.strike,
            expiry=str(long.expiry)[:10],
            bid=long.bid,
            ask=long.ask,
            last=long.last,
            delta=long.delta,
        ),
        credit=credit,
        width=float(pay["width"]),
        max_profit=float(pay["max_profit"]),
        max_loss=float(pay["max_loss"]),
        breakeven=float(pay["breakeven"]),
        short_distance_pct=round(distance_pct, 4),
        passed=passed,
    )


def _puts(
    underlying: str,
    spot: float,
    exp: str,
    dte: int,
    rows: list[OptionContract],
    params: ScanParams,
) -> list[SellerCard]:
    out: list[SellerCard] = []
    for short in rows:
        if short.strike >= spot:
            continue
        distance = (spot - short.strike) / spot
        if distance < params.min_distance_pct:
            continue
        if not _delta_ok(short, params):
            continue
        if not _leg_spread_ok(short, params.max_spread_vs_mid):
            continue
        for width in params.widths:
            long = _match_strike(rows, short.strike - width, params.strike_tol)
            if long is None:
                continue
            if not _leg_spread_ok(long, params.max_spread_vs_mid):
                continue
            credit = conservative_credit(short_bid=short.bid, long_ask=long.ask)
            if credit < params.min_credit:
                continue
            passed = [
                f"dte_{dte}",
                f"otm_put_{distance:.3f}",
                f"width_{width:g}",
                f"credit_{credit}",
            ]
            if short.delta is not None:
                passed.append(f"delta_{short.delta:.3f}")
            card = _build(
                structure_id="bull_put_spread",
                underlying=underlying,
                spot=spot,
                dte=dte,
                short=short,
                long=long,
                distance_pct=distance,
                passed=passed,
            )
            if card:
                out.append(card)
    return _best_per_expiry(out)


def _calls(
    underlying: str,
    spot: float,
    exp: str,
    dte: int,
    rows: list[OptionContract],
    params: ScanParams,
) -> list[SellerCard]:
    out: list[SellerCard] = []
    for short in rows:
        if short.strike <= spot:
            continue
        distance = (short.strike - spot) / spot
        if distance < params.min_distance_pct:
            continue
        if not _delta_ok(short, params):
            continue
        if not _leg_spread_ok(short, params.max_spread_vs_mid):
            continue
        for width in params.widths:
            long = _match_strike(rows, short.strike + width, params.strike_tol)
            if long is None:
                continue
            if not _leg_spread_ok(long, params.max_spread_vs_mid):
                continue
            credit = conservative_credit(short_bid=short.bid, long_ask=long.ask)
            if credit < params.min_credit:
                continue
            passed = [
                f"dte_{dte}",
                f"otm_call_{distance:.3f}",
                f"width_{width:g}",
                f"credit_{credit}",
            ]
            if short.delta is not None:
                passed.append(f"delta_{short.delta:.3f}")
            card = _build(
                structure_id="bear_call_spread",
                underlying=underlying,
                spot=spot,
                dte=dte,
                short=short,
                long=long,
                distance_pct=distance,
                passed=passed,
            )
            if card:
                out.append(card)
    return _best_per_expiry(out)


def _best_per_expiry(cards: list[SellerCard]) -> list[SellerCard]:
    """Keep the highest credit/width ratio per structure+expiry+width."""
    best: dict[tuple[str, str, float], SellerCard] = {}
    for card in cards:
        key = (card.structure_id, card.expiry, card.width)
        prev = best.get(key)
        if prev is None or card.credit > prev.credit:
            best[key] = card
    return list(best.values())


def _spot(backend: QuoteBackend, underlying: str) -> float:
    snap = backend.snapshot(underlying)
    return float(snap.get("last_price") or snap.get("last") or 0)


def _snapshots(backend: QuoteBackend, codes: list[str]) -> dict[str, dict[str, Any]]:
    fn = getattr(backend, "snapshots", None)
    if callable(fn):
        return fn(codes)
    return {code: backend.snapshot(code) for code in codes}


def enrich_chain(backend: QuoteBackend, chain: list[OptionContract]) -> list[OptionContract]:
    if not chain:
        return chain
    if all(c.bid > 0 and c.ask > 0 for c in chain):
        return chain
    snaps = _snapshots(backend, [c.code for c in chain])
    out: list[OptionContract] = []
    for c in chain:
        snap = snaps.get(c.code) or {}
        out.append(overlay_snapshot(c, snap) if snap else c)
    return out


def contracts_from_pack(pack: dict[str, Any]) -> list[OptionContract]:
    """Turn a QuoteStore current pack into scan legs (already quoted)."""
    underlying = str(pack.get("underlying") or "")
    out: list[OptionContract] = []
    for row in pack.get("contracts") or []:
        code = str(row.get("code") or "")
        if not code:
            continue
        delta = row.get("delta")
        try:
            delta_f = float(delta) if delta is not None and str(delta) not in ("", "nan") else None
        except (TypeError, ValueError):
            delta_f = None
        out.append(
            OptionContract(
                code=code,
                underlying=underlying,
                strike=float(row.get("strike") or 0),
                expiry=str(row.get("expiry") or "")[:10],
                option_type="PUT" if "PUT" in str(row.get("option_type") or "").upper() else "CALL",
                bid=float(row.get("bid") or 0),
                ask=float(row.get("ask") or 0),
                last=float(row.get("last") or 0),
                delta=delta_f,
            )
        )
    return out


def _spot_from_pack(pack: dict[str, Any]) -> float:
    equity = pack.get("equity") or {}
    return float(equity.get("last_price") or equity.get("last") or 0)


def scan_underlying(
    backend: QuoteBackend,
    underlying: str,
    *,
    today: date | None = None,
    params: ScanParams | None = None,
    store: SellerStore | None = None,
    quote_store: QuoteStore | None = None,
) -> list[SellerCard]:
    pack = quote_store.current(underlying) if quote_store is not None else None
    if pack and pack.get("contracts"):
        if pack.get("stale"):
            raise ValueError("quote_snapshot_stale: refresh the option chain before scanning")
        spot = _spot_from_pack(pack) or _spot(backend, underlying)
        chain = contracts_from_pack(pack)
    else:
        spot = _spot(backend, underlying)
        if spot <= 0:
            return []
        chain = enrich_chain(backend, backend.option_chain(underlying))
    if spot <= 0:
        return []
    cards = credit_vertical_candidates(
        underlying,
        spot,
        chain,
        today=today,
        params=params,
    )
    for card in cards:
        card.quote_source = str(pack.get("source") or "unknown") if pack else (
            "mock" if type(backend).__name__ == "MockQuoteBackend" else "futu"
        )
        card.quoted_at = str(pack.get("pulled_at") or "") if pack else datetime.now(timezone.utc).isoformat()
    if store is not None:
        keep = {card.id for card in cards}
        for existing in store.list_cards():
            if (
                existing.underlying == underlying
                and existing.id not in keep
                and existing.status == "signal"
                and not existing.verdict
            ):
                store.delete_card(existing.id)
        for index, card in enumerate(cards):
            existing = store.get_card(card.id)
            if existing and (existing.status in ("tracked", "settled") or existing.verdict == "adopt"):
                cards[index] = existing
                continue
            if existing and existing.verdict:
                card.verdict = existing.verdict
                card.status = existing.status
                card.follow_status = existing.follow_status
            store.save_card(card)
    return cards


def scan_watchlist(
    backend: QuoteBackend,
    *,
    underlyings: Iterable[str] | None = None,
    today: date | None = None,
    params: ScanParams | None = None,
    store: SellerStore | None = None,
    quote_store: QuoteStore | None = None,
) -> dict[str, Any]:
    names = resolve_underlyings(underlyings)
    cards: list[SellerCard] = []
    errors: dict[str, str] = {}
    sources: list[str] = []
    for name in names:
        try:
            pack = quote_store.current(name) if quote_store is not None else None
            sources.append("sqlite" if pack and pack.get("contracts") else "")
            cards.extend(
                scan_underlying(
                    backend,
                    name,
                    today=today,
                    params=params,
                    store=store,
                    quote_store=quote_store,
                )
            )
        except Exception as exc:  # noqa: BLE001 — keep other names scanning
            errors[name] = str(exc)
    if sources and all(source == "sqlite" for source in sources):
        quote_source = "sqlite"
    elif any(source == "sqlite" for source in sources):
        quote_source = "mixed"
    elif type(backend).__name__ == "MockQuoteBackend":
        quote_source = "mock"
    else:
        quote_source = "futu"
    return {
        "ok": not errors,
        "watchlist": names,
        "count": len(cards),
        "cards": [c.as_dict() for c in cards],
        "errors": errors,
        "as_of": (today or date.today()).isoformat(),
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "quote_source": quote_source,
        "mock": bool(cards) and all(card.quote_source == "mock" for card in cards) if cards else quote_source == "mock",
        "sources": sorted({card.quote_source for card in cards}),
        "quoted_at": sorted({card.quoted_at for card in cards}),
        "place_order": False,
    }
