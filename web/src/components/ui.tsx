/* 共享 UI 原语。状态语义是产品的第一公民：
   FieldMeta.status  available | missing | unsupported | stale | unknown
   Agreement         aligned | partial | conflicted | single_source | insufficient_data
   DataStatus        actionable | opinion | insufficient_data
   收租 tier          可考虑 | 条件可考虑，开盘须重报价 | 仅观察 | 禁做
   conflicted / insufficient_data 是「停止」而不是「中性」。 */
import { bi } from "../i18n";
import { nf, fmtPct, fmtNum, fmtSigned } from "../lib/format";
import {
  statusLabels, statusLabelsEn, agreementLabels, agreementLabelsEn,
  dataStatusLabels, dataStatusLabelsEn, tierLabelsEn,
  directionLabels, directionLabelsEn,
} from "../lib/labels";

/* ---------------- 状态徽章 ---------------- */
export function FieldBadge({ state, label }: { state: string; label?: string }) {
  const text = label || bi(statusLabels[state] || state, statusLabelsEn[state] || state);
  const tone = state === "available" ? "pos" : state === "missing" ? "neg"
    : state === "stale" ? "warn" : state === "unsupported" ? "na" : "mute";
  return (
    <span className="badge" data-s={state} data-tone={tone} title={"FieldMeta.status = " + state}>
      <span className="badge-dot" />
      {text}
      {state !== "unknown" ? <span style={{ opacity: .5, marginLeft: 1 }}>{state}</span> : null}
    </span>
  );
}

export function ToneBadge({ tone, children, title, stop }: {
  tone: string; children: React.ReactNode; title?: string; stop?: boolean;
}) {
  return (
    <span className="badge" data-tone={tone} data-stop={stop ? "1" : undefined} title={title}>
      {stop ? <span className="badge-stop-glyph">■</span> : null}
      {children}
    </span>
  );
}

/* 合成一致性徽章：conflicted / insufficient_data 带停止字形与实线边框 */
export function AgreementBadge({ value, size }: { value: string; size?: number }) {
  const stop = value === "conflicted" || value === "insufficient_data";
  const tone =
    value === "aligned" ? "pos"
      : value === "partial" ? "warn"
        : value === "single_source" ? "mute"
          : "neg";
  return (
    <span
      className="badge"
      data-tone={tone}
      data-stop={stop ? "1" : undefined}
      style={size ? { fontSize: size } : undefined}
      title={"EnsembleSignal.agreement = " + value}
    >
      {stop ? <span className="badge-stop-glyph">■</span> : null}
      {bi(agreementLabels[value] || value, agreementLabelsEn[value] || value)}
      <span style={{ opacity: .55, marginLeft: 2 }}>{value}</span>
    </span>
  );
}

export function DataStatusBadge({ value }: { value: string }) {
  const tone = value === "actionable" ? "pos" : value === "opinion" ? "warn" : "neg";
  const stop = value === "insufficient_data";
  return (
    <span className="badge" data-tone={tone} data-stop={stop ? "1" : undefined}
      title={"EngineSignal.data_status = " + value}>
      {stop ? <span className="badge-stop-glyph">■</span> : null}
      {bi(dataStatusLabels[value] || value, dataStatusLabelsEn[value] || value)}
    </span>
  );
}

export function TierBadge({ tier, compact }: { tier: string; compact?: boolean }) {
  const en = tierLabelsEn[tier] || tier;
  const zh = compact && tier === "条件可考虑，开盘须重报价" ? "条件可考虑" : tier;
  return (
    <span className="tier" data-t={tier} title={"收租评级 tier = " + tier}>
      {bi(zh, en)}
    </span>
  );
}

export function DirLabel({ dir, children }: { dir: string; children?: React.ReactNode }) {
  const txt = children != null ? children : bi(directionLabels[dir] || dir, directionLabelsEn[dir] || dir);
  return <span className="dir" data-d={dir}>{txt}</span>;
}

/* 缺失字段：用斜纹占位，绝不放 0 */
export function Absent({ state, text }: { state: string; text?: string }) {
  if (state === "unsupported")
    return <span className="hatch hatch-na" title="FieldMeta.status = unsupported">{text || bi("不支持", "Unsupported")}</span>;
  if (state === "missing")
    return <span className="hatch" title="FieldMeta.status = missing">{text || bi("缺失", "Missing")}</span>;
  if (state === "stale")
    return <span className="hatch" style={{ color: "var(--warn)" }} title="FieldMeta.status = stale">{text || bi("过期", "Stale")}</span>;
  if (state === "unknown")
    return <span className="badge" data-tone="mute">{text || bi("无记录", "No record")}</span>;
  return null;
}

/* ---------------- 顶部数据健康度汇总条 ---------------- */
export function HealthBar({ sources, chain, account, asOf, onOpenLedger }: {
  sources: { state: string }[];
  chain: { source: string; rows: number; degraded: boolean } | null;
  account: { env: string; value: number } | null;
  asOf: string;
  onOpenLedger?: () => void;
}) {
  const counts: Record<string, number> = { available: 0, missing: 0, unsupported: 0, stale: 0 };
  sources.forEach((s) => { counts[s.state] = (counts[s.state] || 0) + 1; });
  const cells = [
    { key: "asof", label: "as_of", value: asOf, tone: null as string | null },
    { key: "available", label: bi("可用", "available"), value: String(counts.available), tone: null },
    { key: "missing", label: bi("缺失", "missing"), value: String(counts.missing),
      tone: counts.missing ? "neg" : null },
    { key: "unsupported", label: bi("不支持", "n/a"), value: String(counts.unsupported), tone: "na" },
    { key: "stale", label: bi("过期", "stale"), value: String(counts.stale),
      tone: counts.stale ? "warn" : null },
    { key: "chain", label: bi("期权链", "chain"),
      value: chain ? `${chain.source} · ${chain.rows} 行` : bi("缺失", "missing"),
      tone: chain ? (chain.degraded ? "warn" : null) : "neg" },
    { key: "account", label: bi("账户", "account"),
      value: account ? `${account.env} · ${fmtMoneyShort(account.value)}` : bi("缺失", "missing"),
      tone: account ? null : "warn" },
  ];
  return (
    <div className="healthbar">
      {cells.map((c) => (
        <div className="health-cell" key={c.key} data-tone={c.tone || undefined}>
          <span className="health-key">{c.label}</span>
          <b>{c.value}</b>
        </div>
      ))}
      <div className="health-spacer" />
      <div className="health-cell" style={{ borderRight: 0 }}>
        <span className="health-key">{bi("只读 · 不下单", "read-only · no orders")}</span>
        <b>place_order: false</b>
      </div>
      {onOpenLedger ? (
        <div className="health-cell">
          <button className="btn" style={{ padding: "3px 9px" }} onClick={onOpenLedger}>
            {bi("证据抽屉 →", "Evidence →")}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function fmtMoneyShort(v: number): string {
  return "$" + nf.format(Math.round(v));
}

/* ---------------- 区块 ---------------- */
export function Section({ id, idx, title, sub, meta, children, right }: {
  id: string; idx?: string; title: React.ReactNode; sub?: React.ReactNode;
  meta?: React.ReactNode; children: React.ReactNode; right?: React.ReactNode;
}) {
  return (
    <section className="section" id={id}>
      <div className="section-head">
        {idx ? <span className="section-idx">{idx}</span> : null}
        <h2 className="section-title">
          {title}
          {sub ? <small>{sub}</small> : null}
        </h2>
        {right ? <div style={{ marginLeft: "auto" }}>{right}</div> : null}
        {meta ? <div className="section-meta">{meta}</div> : null}
      </div>
      {children}
    </section>
  );
}

/* ---------------- 信号强度对比条 ---------------- */
export interface TractRow {
  key: string; engine?: string; label: string;
  conviction: number; direction: string; status: string; title?: string;
}

export function Tract({ rows, showScale = true }: { rows: TractRow[]; showScale?: boolean }) {
  return (
    <div className="tract">
      {rows.map((r) => {
        const abstain = r.status === "insufficient_data";
        const v = abstain ? 0 : r.conviction;
        const sign = v > 0.02 ? "pos" : v < -0.02 ? "neg" : "zero";
        const w = Math.min(Math.abs(v), 1) * 50;
        const left = v >= 0 ? 50 : 50 - w;
        return (
          <div className="tract-row" key={r.key || r.engine}>
            <div className="tract-label">{r.label}</div>
            <div className="tract-track" title={r.title || (r.label + " conviction " + v)}>
              <div className="tract-zero" />
              {abstain ? (
                <div className="tract-fill" data-abstain="1"
                  style={{ left: "50%", width: "100%" }} />
              ) : (
                Math.abs(v) > 0.005 ? (
                  <div className="tract-fill" data-sign={sign}
                    style={{ left: left + "%", width: w + "%" }} />
                ) : null
              )}
            </div>
            <div className="tract-val">
              {abstain ? <span style={{ color: "var(--ink-3)" }}>{bi("弃权 · 不投票", "abstained")}</span>
                : <>{fmtSigned(v)} <span style={{ color: "var(--ink-4)" }}>{directionLabels[r.direction]}</span></>}
            </div>
          </div>
        );
      })}
      {showScale ? (
        <div className="tract-scale">
          <span />
          <span><span>−1</span><span>0</span><span>+1</span></span>
          <span />
        </div>
      ) : null}
    </div>
  );
}

/* 合成刻度条：五档带 + 指针 */
export function EnsembleTrack({ conviction, agreement }: { conviction: number; agreement: string }) {
  const stop = agreement === "conflicted" || agreement === "insufficient_data";
  const v = Math.max(-1, Math.min(1, conviction));
  const left = ((v + 1) / 2) * 100;
  const bands = [
    { from: -1, to: -0.6, label: "强烈看空" },
    { from: -0.6, to: -0.2, label: "看空" },
    { from: -0.2, to: 0.2, label: "中性" },
    { from: 0.2, to: 0.6, label: "看多" },
    { from: 0.6, to: 1, label: "强烈看多" },
  ];
  return (
    <div>
      <div className="ens-track">
        {bands.map((b) => (
          <div className="ens-band" key={b.label}
            style={{ left: ((b.from + 1) / 2) * 100 + "%", width: ((b.to - b.from) / 2) * 100 + "%" }}
            title={b.label + "  " + b.from + " ~ " + b.to} />
        ))}
        <div className="ens-marker" data-stop={stop ? "1" : undefined} style={{ left: `calc(${left}% - 1.5px)` }} />
      </div>
      <div className="ens-ticks">
        {[-1, -0.6, -0.2, 0.2, 0.6, 1].map((t) => (
          <span key={t} style={{ left: ((t + 1) / 2) * 100 + "%" }}>{t}</span>
        ))}
      </div>
    </div>
  );
}

/* ---------------- 迷你 K 线（收盘价折线 + 均线 + 支撑阻力） ---------------- */
export function Spark({ bars, sma5, sma20, support, resistance, spot, height = 34, showAxis = false }: {
  bars: { close: number }[]; sma5?: number | null; sma20?: number | null;
  support?: number | null; resistance?: number | null; spot?: number | null;
  height?: number; showAxis?: boolean;
}) {
  if (!bars || bars.length < 2) {
    return (
      <div className="chart-box" style={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Absent state="missing" text={bi("没有日线", "No daily bars")} />
      </div>
    );
  }
  const w = 100, h = height;
  const closes = bars.map((b) => b.close);
  const extras = [sma5, sma20, support, resistance, spot].filter((x): x is number => x != null);
  const all = closes.concat(extras);
  const min = Math.min(...all), max = Math.max(...all);
  const span = max - min || 1;
  const X = (i: number) => (i / (bars.length - 1)) * w;
  const Y = (v: number) => h - ((v - min) / span) * (h - 4) - 2;
  const path = closes.map((c, i) => (i ? "L" : "M") + X(i).toFixed(2) + " " + Y(c).toFixed(2)).join(" ");
  const ma5 = closes.map((_, i) => {
    const s = closes.slice(Math.max(0, i - 4), i + 1);
    return s.reduce((a, b) => a + b, 0) / s.length;
  });
  const ma5path = ma5.map((c, i) => (i ? "L" : "M") + X(i).toFixed(2) + " " + Y(c).toFixed(2)).join(" ");
  const up = closes[closes.length - 1] >= closes[0];
  const stroke = up ? "var(--pos)" : "var(--neg)";
  return (
    <div className="chart-box">
      <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
        style={{ height }} aria-label="收盘价折线">
        {resistance != null ? (
          <line x1="0" x2={w} y1={Y(resistance)} y2={Y(resistance)}
            className="svg-line" strokeWidth=".35" strokeDasharray="2 2" />
        ) : null}
        {support != null ? (
          <line x1="0" x2={w} y1={Y(support)} y2={Y(support)}
            className="svg-line" strokeWidth=".35" strokeDasharray="2 2" />
        ) : null}
        <path d={ma5path} fill="none" stroke="var(--ink-4)" strokeWidth=".5"
          strokeDasharray="1.5 1.5" vectorEffect="non-scaling-stroke" />
        <path d={path} fill="none" stroke={stroke} strokeWidth="1.1"
          vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
        {spot != null ? <circle cx={X(bars.length - 1)} cy={Y(spot)} r="1.6" className="svg-ink" /> : null}
      </svg>
      {showAxis && resistance != null ? (
        <div className="chart-axis" style={{ top: Y(resistance) }}>
          <span>{bi("阻力", "resistance")} {fmtNum(resistance)}</span>
        </div>
      ) : null}
      {showAxis && support != null ? (
        <div className="chart-axis" style={{ top: Y(support) }}>
          <span>{bi("支撑", "support")} {fmtNum(support)}</span>
        </div>
      ) : null}
    </div>
  );
}

/* ---------------- 损益图（payoff，由 legs 推导） ---------------- */
export function Payoff({ proposal, spot, width = 320, height = 132 }: {
  proposal: any; spot: number | null; width?: number; height?: number;
}) {
  const legs = proposal.legs as any[];
  const allK = legs.map((l) => l.strike as number);
  const lo = Math.min(...allK) * 0.9, hi = Math.max(...allK) * 1.1;
  const pad = 16;
  const W = width, H = height;
  const N = 90;
  const P = (S: number) => {
    let v = 0;
    legs.forEach((l) => {
      const isCall = l.option_type === "CALL";
      const intrinsic = isCall ? Math.max(0, S - l.strike) : Math.max(0, l.strike - S);
      const dir = l.side === "buy" ? 1 : -1;
      v += dir * intrinsic * 100 * (l.quantity || 1);
    });
    v += (proposal.net_premium || 0) * 100;
    return v;
  };
  const samples: { S: number; v: number }[] = [];
  for (let i = 0; i <= N; i++) {
    const S = lo + ((hi - lo) * i) / N;
    samples.push({ S, v: P(S) });
  }
  const vs = samples.map((s) => s.v);
  const vMin = Math.min(...vs, proposal.max_loss != null ? -proposal.max_loss : 0) * 1.12;
  const vMax = Math.max(...vs, proposal.max_profit != null ? proposal.max_profit : 0) * 1.12;
  const X = (S: number) => pad + ((S - lo) / (hi - lo)) * (W - pad * 2);
  const Y = (v: number) => H - pad - ((v - vMin) / (vMax - vMin || 1)) * (H - pad * 2);
  const d = samples.map((s, i) => (i ? "L" : "M") + X(s.S).toFixed(2) + " " + Y(s.v).toFixed(2)).join(" ");
  const y0 = Y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}
      aria-label="到期损益图（由结构腿推导）">
      <line className="svg-line" x1={pad - 6} x2={W - pad + 6} y1={y0} y2={y0} strokeWidth=".7" />
      {allK.map((k) => (
        <line key={k} x1={X(k)} x2={X(k)} y1={pad - 8} y2={H - pad + 4}
          stroke="var(--rule)" strokeWidth=".7" strokeDasharray="2 3" />
      ))}
      {spot != null ? (
        <line className="svg-acc" x1={X(spot)} x2={X(spot)} y1={pad - 8} y2={H - pad + 4}
          strokeWidth="1" fill="none" />
      ) : null}
      <path d={`${d} L ${X(hi)} ${y0} L ${X(lo)} ${y0} Z`} fill="var(--accent)" opacity=".07" />
      <path className="svg-ink" d={d} fill="none" strokeWidth="1.5" strokeLinejoin="round" />
      <text className="svg-mono svg-dim" x={pad} y={H - 3} fontSize="8">{lo.toFixed(0)}</text>
      <text className="svg-mono svg-dim" x={W - pad} y={H - 3} textAnchor="end" fontSize="8">{hi.toFixed(0)}</text>
      {spot != null ? (
        <text className="svg-mono svg-acc" x={X(spot)} y={pad + 2} textAnchor="middle" fontSize="8">
          spot {spot.toFixed(0)}
        </text>
      ) : null}
      {proposal.max_loss != null ? (
        <text className="svg-mono svg-neg" x={pad} y={Y(-proposal.max_loss) + 3} fontSize="8">
          max loss −{proposal.max_loss}
        </text>
      ) : null}
      {proposal.max_profit != null ? (
        <text className="svg-mono svg-pos" x={W - pad} y={Y(proposal.max_profit) - 3} textAnchor="end"
          fontSize="8">
          max profit +{proposal.max_profit}
        </text>
      ) : null}
    </svg>
  );
}

/* ---------------- 腿列表 ---------------- */
export function Legs({ legs }: { legs: any[] }) {
  return (
    <div className="legs">
      {legs.map((l) => {
        const oi = l.open_interest != null ? l.open_interest : l.oi;
        // 腿方向大小写无关：菜单 legs 用小写 buy/sell，收租卡片来自 FutuLegQuote 用大写
        const side = String(l.side || "").toLowerCase();
        const isBuy = side === "buy";
        return (
          <div className="leg" key={l.code + l.side}>
            <span className="leg-side" data-s={side}>
              {isBuy ? bi("买入", "BUY") : bi("卖出", "SELL")}
            </span>
            <span className="leg-main">
              <span className="leg-strike">
                {l.option_type === "CALL" ? bi("认购", "CALL") : bi("认沽", "PUT")}
                {" "}K={fmtNum(l.strike, l.strike % 1 ? 1 : 0)}
                {l.expiry ? <span className="leg-exp">{" · "}{l.expiry}</span> : null}
              </span>
              <span className="leg-quote">
                {l.bid != null ? <>bid {fmtNum(l.bid)} / ask {fmtNum(l.ask)}</> : null}
                {oi != null ? <> {" · "}OI {nf.format(oi)}</> : null}
                {l.iv != null ? <> {" · "}IV {fmtPct(l.iv)}</> : null}
                {l.delta != null ? <> {" · "}Δ {fmtNum(l.delta, 3)}</> : null}
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ---------------- 引用块 ---------------- */
export function Quote({ children }: { children: React.ReactNode }) {
  return <div className="quote">{children}</div>;
}
