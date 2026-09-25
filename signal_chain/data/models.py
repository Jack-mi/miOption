from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..schema import ChainSnapshot
from ..schema.underlying import UnderlyingSnapshot


@dataclass(frozen=True)
class SourceRow:
    id: str
    field: str
    state: str  # used / missing / unsupported / skipped
    note: str = ""


@dataclass
class MacroPoint:
    series: str
    as_of: date
    value: float
    source: str = "alphavantage"


@dataclass
class SocialItem:
    source: str
    text: str


@dataclass
class EventOdds:
    slug: str
    outcome: str
    price: float


@dataclass
class Fact:
    source: str
    metric: str
    period: str
    value: float


@dataclass
class Ratio:
    metric: str
    value: float
    period: str
    source: str


@dataclass
class FilingExcerpt:
    section: str
    text: str
    source: str
    as_of: date | None = None


@dataclass
class MarketData:
    snapshot: UnderlyingSnapshot
    chain: ChainSnapshot | None = None
    chain_error: str | None = None
    macro: list[MacroPoint] = field(default_factory=list)
    social: list[SocialItem] = field(default_factory=list)
    events: list[EventOdds] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    sources: list[SourceRow] = field(default_factory=list)
    flow_net: float | None = None
    news_text: str | None = None
    ratios: list[Ratio] = field(default_factory=list)
    excerpts: list[FilingExcerpt] = field(default_factory=list)
