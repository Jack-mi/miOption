"""SEC EDGAR。美股申报和财报披露日。不要 key，要 User-Agent。"""

from __future__ import annotations

from datetime import date


def user_agent(contact: str) -> dict[str, str]:
    who = contact or "mioption-data@localhost"
    return {"User-Agent": f"mioption data {who}", "Accept-Encoding": "gzip, deflate"}


def cik_for(tickers: dict, symbol: str) -> str | None:
    want = symbol.upper()
    rows = tickers.values() if isinstance(tickers, dict) else tickers
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("ticker") or "").upper() == want:
            return str(row.get("cik_str") or "").zfill(10)
    return None


def latest_revenue(facts: dict) -> tuple[float, str, str] | None:
    """返回 (值, 期间, 结束日 ISO)。只要年报 USD。"""
    node = (
        ((facts.get("facts") or {}).get("us-gaap") or {}).get("Revenues")
        or ((facts.get("facts") or {}).get("us-gaap") or {}).get("RevenueFromContractWithCustomerExcludingAssessedTax")
        or {}
    )
    units = (node.get("units") or {}).get("USD") or []
    annual = [
        row for row in units
        if row.get("form") in {"10-K", "20-F"} and row.get("val") is not None and row.get("end")
    ]
    if not annual:
        return None
    row = max(annual, key=lambda item: item["end"])
    end = str(row["end"])[:10]
    period = f"FY{end[:4]}"
    return float(row["val"]), period, end


def _annual_usd(facts: dict, names: tuple[str, ...]) -> tuple[float, str] | None:
    gaap = ((facts.get("facts") or {}).get("us-gaap") or {})
    for name in names:
        units = ((gaap.get(name) or {}).get("units") or {}).get("USD") or []
        annual = [
            row for row in units
            if row.get("form") in {"10-K", "20-F"} and row.get("val") is not None and row.get("end")
        ]
        if not annual:
            continue
        row = max(annual, key=lambda item: item["end"])
        end = str(row["end"])[:10]
        return float(row["val"]), f"FY{end[:4]}"
    return None


def derived_ratios(facts: dict) -> dict[str, tuple[float, str]]:
    """从年报 XBRL 算出 ROE、自由现金流、利息覆盖。缺组成项就不算。"""
    income = _annual_usd(facts, ("NetIncomeLoss",))
    equity = _annual_usd(facts, ("StockholdersEquity",))
    operating_cash = _annual_usd(facts, ("NetCashProvidedByUsedInOperatingActivities",))
    capex = _annual_usd(facts, ("PaymentsToAcquirePropertyPlantAndEquipment",))
    operating = _annual_usd(facts, ("OperatingIncomeLoss",))
    interest = _annual_usd(facts, ("InterestExpense",))
    out: dict[str, tuple[float, str]] = {}
    if income and equity and equity[0]:
        out["roe"] = (income[0] / equity[0], income[1])
    if operating_cash and capex:
        out["free_cash_flow"] = (operating_cash[0] - abs(capex[0]), operating_cash[1])
    if operating and interest and interest[0]:
        out["interest_coverage"] = (operating[0] / abs(interest[0]), operating[1])
    return out


def latest_primary(submissions: dict, forms: set[str]) -> dict | None:
    recent = (submissions.get("filings") or {}).get("recent") or {}
    names = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accessions = recent.get("accessionNumber") or []
    docs = recent.get("primaryDocument") or []
    best = None
    for i, form in enumerate(names):
        if form not in forms or i >= len(dates) or i >= len(accessions) or i >= len(docs):
            continue
        if not docs[i]:
            continue
        filed = str(dates[i])[:10]
        if best is None or filed > best["filed"]:
            best = {
                "form": form,
                "filed": filed,
                "accession": str(accessions[i]),
                "document": str(docs[i]),
            }
    return best


def archive_url(cik: str, accession: str, document: str) -> str:
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{document}"


def _plain(html: str) -> str:
    import re
    from html.parser import HTMLParser

    class _Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = _Text()
    parser.feed(html or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _between(text: str, start: str, end: str, limit: int = 800) -> str | None:
    import re
    found = re.search(start, text, re.I)
    if not found:
        return None
    rest = text[found.end():]
    stop = re.search(end, rest, re.I)
    chunk = (rest[:stop.start()] if stop else rest).strip()
    if len(chunk) < 40:
        return None
    return chunk[:limit]


def excerpts_from_10k(html: str) -> dict[str, str]:
    text = _plain(html)
    out = {}
    business = _between(text, r"Item\s+1[\.\s]+Business", r"Item\s+1A[\.\s]")
    risk = _between(text, r"Item\s+1A[\.\s]+Risk Factors", r"Item\s+1B[\.\s]|Item\s+2[\.\s]")
    competition = _between(
        text,
        r"\bCompetition\b",
        r"Item\s+1A[\.\s]|Seasonality|Intellectual Property|Research and Development",
    )
    if business:
        out["business"] = business
    if competition:
        out["competition"] = competition
    if risk:
        out["risk_factors"] = risk
    return out


def excerpts_from_proxy(html: str) -> dict[str, str]:
    text = _plain(html)
    governance = _between(text, r"Corporate Governance", r"Executive Compensation|Security Ownership")
    if not governance:
        return {}
    return {"governance": governance}


def latest_filing_date(submissions: dict) -> date | None:
    recent = (submissions.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    found = [
        dates[i] for i, form in enumerate(forms)
        if form in {"10-K", "10-Q", "20-F"} and i < len(dates)
    ]
    if not found:
        return None
    return date.fromisoformat(max(found)[:10])
