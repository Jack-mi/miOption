"""SEC EDGAR。美股申报和财报披露日。不要 key，要 User-Agent。"""

from __future__ import annotations

import re
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


_REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "Revenues",
)


def _span_days(row: dict) -> int:
    end = str(row.get("end") or "")[:10]
    start = str(row.get("start") or "")[:10]
    if len(end) < 10 or len(start) < 10:
        return 0
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        return 0


def _full_year_usd(units: list) -> list:
    rows = []
    for row in units:
        if not isinstance(row, dict):
            continue
        if row.get("form") not in {"10-K", "20-F"} or row.get("val") is None or not row.get("end"):
            continue
        if "Q" in str(row.get("frame") or ""):
            continue
        if row.get("start") and _span_days(row) < 300:
            continue
        rows.append(row)
    return rows


def _best_annual(rows: list) -> dict | None:
    if not rows:
        return None
    return max(rows, key=lambda item: (str(item["end"]), _span_days(item)))


def latest_quarter_revenue(facts: dict) -> tuple[float, str] | None:
    """最近一份 10-Q 的单季营收。期间用报告期结束日。"""
    gaap = ((facts.get("facts") or {}).get("us-gaap") or {})
    best = None
    for name in _REVENUE_TAGS:
        units = ((gaap.get(name) or {}).get("units") or {}).get("USD") or []
        for row in units:
            if not isinstance(row, dict) or row.get("form") != "10-Q":
                continue
            if row.get("val") is None or not row.get("end") or not row.get("start"):
                continue
            days = _span_days(row)
            if days < 70 or days > 120:
                continue
            if best is None or str(row["end"]) > str(best["end"]):
                best = row
    if best is None:
        return None
    end = str(best["end"])[:10]
    return float(best["val"]), f"Q{end}"


def latest_revenue(facts: dict) -> tuple[float, str, str] | None:
    """返回 (值, 期间, 结束日 ISO)。取各营收科目里结束日最晚的全年数。"""
    gaap = ((facts.get("facts") or {}).get("us-gaap") or {})
    best = None
    for name in _REVENUE_TAGS:
        row = _best_annual(_full_year_usd(((gaap.get(name) or {}).get("units") or {}).get("USD") or []))
        if row is None:
            continue
        if best is None or str(row["end"]) > str(best["end"]):
            best = row
    if best is None:
        return None
    end = str(best["end"])[:10]
    return float(best["val"]), f"FY{end[:4]}", end


def _annual_usd(facts: dict, names: tuple[str, ...]) -> tuple[float, str] | None:
    gaap = ((facts.get("facts") or {}).get("us-gaap") or {})
    for name in names:
        row = _best_annual(_full_year_usd(((gaap.get(name) or {}).get("units") or {}).get("USD") or []))
        if row is None:
            continue
        end = str(row["end"])[:10]
        return float(row["val"]), f"FY{end[:4]}"
    return None


_FLOW_SERIES = {
    "net_income": ("NetIncomeLoss",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",),
    "buybacks": ("PaymentsForRepurchaseOfCommonStock",),
}
_STOCK_SERIES = {
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "long_term_debt": ("LongTermDebtNoncurrent", "LongTermDebt"),
}
_HISTORY_YEARS = 10


def _units(facts: dict, namespace: str, name: str, unit: str) -> list:
    return (
        (((facts.get("facts") or {}).get(namespace) or {}).get(name) or {})
        .get("units", {})
        .get(unit)
        or []
    )


def _instant_annual(units: list) -> list:
    rows = []
    for row in units:
        if not isinstance(row, dict):
            continue
        if row.get("form") not in {"10-K", "20-F"} or row.get("val") is None or not row.get("end"):
            continue
        if row.get("start"):
            continue
        rows.append(row)
    return rows


def _by_year(rows: list, limit: int = _HISTORY_YEARS) -> list[dict]:
    chosen: dict[str, dict] = {}
    for row in rows:
        end = str(row.get("end") or "")[:10]
        if len(end) < 10:
            continue
        year = end[:4]
        prev = chosen.get(year)
        if prev is None or end > str(prev.get("end")):
            chosen[year] = row
    years = sorted(chosen, reverse=True)[:limit]
    return [chosen[year] for year in years]


def _tagged_years(facts: dict, names: tuple[str, ...], *, flow: bool) -> list[dict]:
    found: dict[str, dict] = {}
    for name in names:
        units = _units(facts, "us-gaap", name, "USD")
        rows = _full_year_usd(units) if flow else _instant_annual(units) or _full_year_usd(units)
        for row in _by_year(rows, limit=40):
            year = str(row["end"])[:4]
            if year not in found:
                found[year] = row
    return _by_year(list(found.values()))


def _fact_row(metric: str, row: dict) -> tuple[str, str, float, str]:
    end = str(row["end"])[:10]
    filed = str(row.get("filed") or "")[:10]
    return metric, f"FY{end[:4]}", float(row["val"]), filed


def annual_history(facts: dict) -> list[tuple[str, str, float, str]]:
    """近十年年报。每项是科目、FY、数值、申报日。同一财年只留一行。"""
    out: list[tuple[str, str, float, str]] = []
    revenue_years: dict[str, dict] = {}
    for name in _REVENUE_TAGS:
        for row in _by_year(_full_year_usd(_units(facts, "us-gaap", name, "USD")), limit=40):
            year = str(row["end"])[:4]
            if year not in revenue_years:
                revenue_years[year] = row
    for row in _by_year(list(revenue_years.values())):
        out.append(_fact_row("revenue", row))
    flows: dict[str, dict[str, float]] = {}
    for metric, names in _FLOW_SERIES.items():
        rows = _tagged_years(facts, names, flow=True)
        flows[metric] = {str(row["end"])[:4]: float(row["val"]) for row in rows}
        out.extend(_fact_row(metric, row) for row in rows)
    for metric, names in _STOCK_SERIES.items():
        out.extend(_fact_row(metric, row) for row in _tagged_years(facts, names, flow=False))
    for row in _by_year(_instant_annual(_units(facts, "dei", "EntityCommonStockSharesOutstanding", "shares"))):
        out.append(_fact_row("shares_outstanding", row))
    for row in _by_year(_full_year_usd(_units(
        facts, "us-gaap", "CommonStockDividendsPerShareDeclared", "USD/shares",
    ))):
        out.append(_fact_row("dividends_per_share", row))
    income = flows.get("operating_cash_flow") or {}
    capex = flows.get("capex") or {}
    for year in sorted(set(income) & set(capex), reverse=True)[:_HISTORY_YEARS]:
        out.append(("free_cash_flow", f"FY{year}", income[year] - abs(capex[year]), ""))
    return out


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


_ITEM_RE = re.compile(r"\bItem\s+(1A|1B|1C|1|2)\b", re.I)
_COMPETITION_FLOOR = 2000
# ponytail: 每节最多留 2 万字。再长的 Item 1 对决策包也是同一段开头。
_SECTION_CAP = 20000


_CROSSREF = {"of", "in", "to", "under", "above", "and", "or", "the", "this", "that", "hereto", "herein"}


def _item_marks(text: str) -> list[tuple[int, str, int]]:
    marks = []
    for match in _ITEM_RE.finditer(text):
        rest = text[match.end():match.end() + 24].lstrip(" .:")
        word = re.split(r"\s+", rest, maxsplit=1)[0].lower().strip(".,")
        if word in _CROSSREF:
            continue
        marks.append((match.start(), match.group(1).upper(), match.end()))
    return marks


def _longest_item(text: str, start: str, ends: set[str]) -> str | None:
    marks = _item_marks(text)
    best = None
    for index, (pos, code, end) in enumerate(marks):
        if code != start:
            continue
        nxt = next((marks[j] for j in range(index + 1, len(marks)) if marks[j][1] in ends), None)
        if nxt is None:
            continue
        chunk = text[end:nxt[0]].strip()
        if best is None or len(chunk) > len(best):
            best = chunk
    if not best or len(best) < 40:
        return None
    return best


def _competition(business: str) -> tuple[str, str] | None:
    found = re.search(r"\bCompetition\b", business, re.I)
    if not found:
        return None
    rest = business[found.end():]
    stop = re.search(
        r"(?:^|\.\s+)(Seasonality|Human Capital|Intellectual Property|Research and Development)\b",
        rest,
    )
    chunk = (rest[:stop.start()] if stop else rest).strip()
    if len(chunk) < 40:
        return None
    quality = "extraction_suspect" if len(chunk) < _COMPETITION_FLOOR else ""
    return chunk[:_SECTION_CAP], quality


def excerpts_from_10k(html: str) -> dict[str, tuple[str, str]]:
    """按 Item 编号切。同一编号取最长的那一截，目录里的短行不会赢。"""
    text = _plain(html)
    out: dict[str, tuple[str, str]] = {}
    business = _longest_item(text, "1", {"1A"})
    if business:
        out["business"] = (business[:_SECTION_CAP], "")
        competition = _competition(business)
        if competition:
            out["competition"] = competition
    risk = _longest_item(text, "1A", {"1B", "1C", "2"})
    if risk:
        out["risk_factors"] = (risk, "")
    return out


def risk_excerpt(text: str, summary: str = "") -> tuple[str, str]:
    """全文长度写在标记里。有摘要就只把摘要交给后面的模型。"""
    full = len(text)
    if summary.strip():
        return summary.strip(), f"summary full={full}"
    if full <= _SECTION_CAP:
        return text, ""
    return text[:_SECTION_CAP], f"full={full}"


def _between(text: str, start: str, end: str) -> str | None:
    found = re.search(start, text, re.I)
    if not found:
        return None
    rest = text[found.end():]
    stop = re.search(end, rest, re.I)
    chunk = (rest[:stop.start()] if stop else rest).strip()
    if len(chunk) < 40:
        return None
    return chunk[:_SECTION_CAP]


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
