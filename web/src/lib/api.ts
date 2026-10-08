/* API 客户端 + 视图模型适配。
   api 返回链路契约形状（FieldMeta / EngineSignal / ChainSnapshot / tier），
   这里摊平成设计稿组件消费的 workbench 形状。 */

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  tickers: () => get<{ tickers: TickerInfo[] }>("/api/tickers"),
  console: (t: string) => get<ConsoleResponse>(`/api/console/${encodeURIComponent(t)}`),
  fieldDetail: (t: string, f: string) =>
    get<{ rows: [string, unknown][]; note: string }>(`/api/console/${encodeURIComponent(t)}/field/${encodeURIComponent(f)}`),
  watchlist: () => get<{ rows: WatchRow[] }>("/api/watchlist"),
  cards: (t: string) => get<{ cards: SellerCard[] }>(`/api/tickers/${encodeURIComponent(t)}/cards`),
  verdict: (cardId: string, verdict: string | null) =>
    post<{ ok: boolean }>(`/api/cards/${encodeURIComponent(cardId)}/verdict`, { verdict }),
  coverage: (ts: string[]) =>
    get<CoverageResponse>(`/api/evidence/coverage?tickers=${ts.map(encodeURIComponent).join(",")}`),
  runs: (t: string) => get<RunLedgerResponse>(`/api/evidence/runs/${encodeURIComponent(t)}`),
  risk: (t: string) => get<RiskPanelResponse>(`/api/evidence/risk?ticker=${encodeURIComponent(t)}`),
  strategies: () => get<{ strategies: StrategyNote[] }>("/api/strategies"),
  recompute: (body: RecomputeBody) => post<RecomputeResult>("/api/recompute", body),
};

/* ---------- 响应类型 ---------- */

export interface TickerInfo { ticker: string; hasLedger: boolean; badge: string; }

export interface SourceField {
  id: string; field: string; state: string; note: string;
  source: string | null; as_of: string | null; fetched_at: string | null;
  timezone: string | null; period: string | null; error: string | null;
  market_time: string | null; preview: string | null;
}

export interface EngineSignalView {
  signal_id: string; engine: string; engineLabel: string; engine_kind: string;
  direction: string; conviction: number; data_status: string;
  reasoning: string; claims: string[]; risk_flags: string[];
  volatility_view: string; data_gaps: string[]; faces: string;
  llm_model: string | null; as_of: string | null; ticker: string; market: string;
}

export interface MenuItemView {
  name: string; nameEn: string; group: string;
  status: string; reason: string; tier: string | null;
  income: any; max_loss: number | null; vetoes: string[]; approved: boolean | null;
  expandable: boolean;
  legs: any[] | null; net_premium: number | null; max_profit: number | null;
  is_short_vol: boolean | null; notes: string | null;
  risk: { approved: boolean; vetoes: string[]; warnings: string[] } | null;
}

export interface ConsoleResponse {
  ticker: string; market: string; currency: string; asOf: string; hasLedger: boolean;
  quote: { spot: number | null; prevClose: number | null; status: string;
    source: string | null; as_of: string | null; market_time: string | null };
  technical: { sma_5?: number | null; sma_20?: number | null; rsi_14?: number | null; atr_14?: number | null };
  bars: { trade_date: string; close: number }[];
  earningsDate: string | null;
  sources: SourceField[];
  signals: Record<string, EngineSignalView>;
  ensemble: {
    agreement: string; direction: string; conviction: number; volatility_view: string;
    quality_notes: string | null; catalysts: any[]; dissent_summary: string | null;
    components: { engine: string; direction: string; conviction: number; data_status: string }[];
  };
  chain: {
    spot: number | null; rows: number; source: string; degraded: boolean;
    fetched_at: string; spot_at: string | null; expiries: string[];
    iv_by_expiry: { expiry: string; dte: number | null; atm_iv: number | null;
      spread_pct: number | null; oi: number }[];
  } | null;
  menu: MenuItemView[];
  risk: {
    signal_gate: { approved: boolean; vetoes: string[]; warnings: string[]; checked_at?: string } | null;
    account_equity: any;
    review: { ok: boolean; findings: string[] } | null;
    decision: string | null;
    limits: Record<string, any>;
  };
  report: { markdown: string; date: string } | null;
  cards: SellerCard[];
  volBasis: { iv30: number; ivRank: number; hv_latest: number | null;
    iv_hv_ratio: number | null; points: number; as_of: string; source: string } | null;
  reportStructured: string;
}

export interface SellerCard {
  id: string; ticker: string; structure: string; name: string; nameEn: string;
  expiry: string; dte: number; spot: number;
  short: any; long: any;
  credit: number; width: number; max_profit: number; max_loss: number; breakeven: number;
  return_on_risk: number | null;
  tier: string; reasons: string[]; blocking: string[];
  verdict: string | null;
  quote_source: string; quoted_at: string; created_at: string;
  historical: boolean; wiki_path: string;
}

export interface WatchRow {
  ticker: string; hasLedger: boolean; badge: string;
  spot: number | null; prevClose: number | null; currency: string;
  direction: string; conviction: number; agreement: string; volatility_view: string;
  iv30: number | null; ivRank: number | null; earningsDate: string | null;
  cards: number; gateApproved: boolean; gateVetoes: string[];
  usable: boolean; mispriceWindow: boolean;
}

export interface CoverageResponse {
  date: string;
  fields: { id: string; name: string }[];
  tickers: string[];
  matrix: Record<string, Record<string, string>>;
}

export interface RunLedgerResponse {
  date: string; ticker: string; hasLedger: boolean;
  engines?: Record<string, string>; elapsed_sec?: number; updated_at?: string;
  agents?: { agent: string; thread_id: string | null; input_tokens?: number | null;
    output_tokens?: number | null; model?: string }[];
  ensemble?: any; signal_gate?: any; action?: string; review?: any;
  macro?: any[]; data_layer?: any[];
}

export interface RiskPanelResponse {
  ticker: string; limits: Record<string, any>; account_equity: any;
  checked: number; vetoed: { name: string; vetoes: string[] }[]; review: any; signal_gate: any;
}

export interface StrategyNote {
  name: string; en: string; file: string; group: string;
  blurb: string; market: string; risk: string; greeks: string;
}

export interface RecomputeBody {
  ticker: string; quote?: number | null; sma5?: number | null; sma20?: number | null;
  flow?: number | null; rsi14?: number | null; iv30?: number | null; earningsGap?: number | null;
}

export interface RecomputeResult {
  trend: { direction: string; conviction: number; text: string };
  ensemble: { agreement: string; direction: string; conviction: number; notes: string };
  riskNotes: string[];
  notRecomputed: string[];
  limits: { earnings_blackout_days: number; min_conviction: number };
}

/* ---------- 视图模型适配：ConsoleResponse -> 设计稿 workbench 形状 ---------- */

const TICKER_NAMES: Record<string, [string, string]> = {
  "US.AAPL": ["苹果", "Apple"],
  "US.COST": ["好市多", "Costco"],
  "HK.09992": ["泡泡玛特", "Pop Mart"],
  "HK.03690": ["美团", "Meituan"],
};

export function toWorkbench(c: ConsoleResponse) {
  const [nameZh, name] = TICKER_NAMES[c.ticker] || [c.ticker, c.ticker];
  const tech = c.technical || {};
  const atmIv = c.chain && c.chain.iv_by_expiry.length
    ? nearestIv(c.chain.iv_by_expiry, 30) : null;
  return {
    ticker: c.ticker,
    nameZh, name,
    market: c.market,
    currency: c.currency,
    asOf: c.asOf,
    hasLedger: c.hasLedger,
    spot: c.quote.spot,
    prevClose: c.quote.prevClose,
    quoteStatus: c.quote.status,
    sma5: tech.sma_5 ?? null,
    sma20: tech.sma_20 ?? null,
    rsi14: tech.rsi_14 ?? null,
    atr14: tech.atr_14 ?? null,
    support: null as number | null,
    resistance: null as number | null,
    target: null as number | null,
    invalidBelow: null as number | null,
    iv30: c.volBasis?.iv30 ?? null,
    ivPercentile: c.volBasis?.ivRank ?? null,
    atmIv,
    earningsDate: c.earningsDate,
    earningsSource: null as string | null,
    bars: c.bars.map((b) => ({ trade_date: b.trade_date, close: b.close })),
    sources: c.sources,
    signals: c.signals,
    ensemble: c.ensemble,
    chain: c.chain,
    menu: c.menu.map((m) => ({
      name: m.name,
      nameEn: m.nameEn,
      group: m.group,
      status: m.status,
      reason: m.reason,
      proposal: m.expandable && m.legs ? {
        name: m.nameEn,
        legs: m.legs,
        net_premium: m.net_premium,
        max_loss: m.max_loss,
        max_profit: m.max_profit,
        is_short_vol: m.is_short_vol,
        notes: m.notes,
      } : null,
      decision: m.risk ? m.risk
        : (m.approved !== null || (m.vetoes && m.vetoes.length)
          ? { approved: !!m.approved, vetoes: m.vetoes || [], warnings: [] }
          : null),
      tier: m.tier,
      income: m.income,
    })),
    opportunities: c.cards,
    risk: {
      signal_gate: c.risk.signal_gate || { approved: false, vetoes: [], warnings: [] },
      review: c.risk.review || { ok: false, findings: [] },
      account_equity: c.risk.account_equity,
      action: c.risk.decision,
      limits: c.risk.limits,
    },
    report: c.report,
    reportStructured: c.reportStructured,
  };
}

export type Workbench = ReturnType<typeof toWorkbench>;

function nearestIv(rows: { dte: number | null; atm_iv: number | null }[], target: number): number | null {
  let best: number | null = null;
  let bestDist = Infinity;
  for (const r of rows) {
    if (r.atm_iv == null || r.dte == null) continue;
    const d = Math.abs(r.dte - target);
    if (d < bestDist) { bestDist = d; best = r.atm_iv; }
  }
  return best;
}
