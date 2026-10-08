/* 观察清单：一行一只票，展开看它名下的期权策略候选（seller 卡）。
   verdict 四按钮互斥，写 api（与 CLI 同一份 seller store 真相）。 */
import { useMemo, useState } from "react";
import { bi } from "../i18n";
import { api, SellerCard, WatchRow } from "../lib/api";
import { fmtDelta, fmtNum, fmtPct, fmtSigned } from "../lib/format";
import {
  Absent, AgreementBadge, DirLabel, Legs, TierBadge, ToneBadge, Tract,
} from "../components/ui";

/* ---------------- 期权策略候选卡片 ---------------- */
function IncomeCard({ c, verdict, onVerdict }: {
  c: SellerCard; verdict: string | null | undefined;
  onVerdict: (id: string, v: string | null) => void;
}) {
  const blockR = c.blocking || [];
  return (
    <div className="rcard" style={{ minWidth: 300, maxWidth: 430, flex: "1 1 320px" }}>
      <div className="rcard-head">
        <span className="rcard-name">{c.name}</span>
        <span className="rcard-str">
          <span className="mono">{c.expiry}</span><br />
          <span className="mono">dte {c.dte}</span>
        </span>
      </div>

      <div className="rcard-legs">
        <Legs legs={[c.short, c.long]} />
      </div>

      <div className="rcard-metrics">
        <div className="rcard-metric">
          <dt>credit</dt>
          <dd style={{ color: "var(--pos)" }}>{fmtNum(c.credit)}</dd>
        </div>
        <div className="rcard-metric">
          <dt>max loss</dt>
          <dd>{c.max_loss}</dd>
        </div>
        <div className="rcard-metric">
          <dt>{bi("收益/风险", "ret/risk")}</dt>
          <dd style={{ color: (c.return_on_risk ?? 0) >= 0.1 ? "var(--pos)" : "var(--warn)" }}>
            {c.return_on_risk != null ? fmtPct(c.return_on_risk, 1) : "—"}
          </dd>
        </div>
      </div>

      <div className="rcard-reasons">
        <div style={{ marginBottom: 5 }}>
          <TierBadge tier={c.tier} compact />
        </div>
        {c.reasons.length ? c.reasons.map((r, i) => (
          <div className="reason" data-k={blockR.indexOf(r) >= 0 ? "block" : undefined} key={i}>
            <span>{blockR.indexOf(r) >= 0 ? "✕" : "△"}</span>{r}
          </div>
        )) : (
          <div className="reason" data-k="ok">
            <span>✓</span>{bi("盈亏比、持仓量、价差、财报窗口均过关", "ret/risk, OI, spread and earnings window all pass")}
          </div>
        )}
        <div className="reason" style={{ color: "var(--ink-4)", marginTop: 3 }}>
          <span>·</span>
          {bi("来源", "source")} {c.quote_source} · {bi("盘口", "quoted")} {(c.quoted_at || "").replace("T", " ").slice(0, 19)}
        </div>
      </div>

      <div className="rcard-acts">
        {([
          ["adopt", bi("采纳", "Adopt")],
          ["watch", bi("观察", "Watch")],
          ["reject", bi("拒绝", "Reject")],
          ["clear", bi("清空", "Clear")],
        ] as const).map(([k, l]) => (
          <button className="rcard-act" key={k}
            data-on={k !== "clear" && verdict === k ? "1" : undefined}
            onClick={() => onVerdict(c.id, k === "clear" ? null : (verdict === k ? null : k))}>
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---------------- 观察清单 ---------------- */
export function WatchPage({ rows, cardsByTicker, verdicts, onVerdict, onOpenEvidence, onOpenWorkbench }: {
  rows: WatchRow[];
  cardsByTicker: Record<string, SellerCard[]>;
  verdicts: Record<string, string | null>;
  onVerdict: (id: string, v: string | null) => void;
  onOpenEvidence: (tab: string) => void;
  onOpenWorkbench: (ticker: string) => void;
}) {
  const [sort, setSort] = useState("conviction");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const sorted = useMemo(() => [...rows].sort((a, b) =>
    sort === "conviction" ? Math.abs(b.conviction) - Math.abs(a.conviction)
      : sort === "cards" ? b.cards - a.cards
        : a.ticker.localeCompare(b.ticker)), [rows, sort]);

  const windows = sorted.filter((r) => r.mispriceWindow);
  const totalCards = rows.reduce((a, r) => a + r.cards, 0);
  const actionable = rows.filter((r) => r.gateApproved).length;

  return (
    <div className="page page-wide">
      <div className="page-head compact">
        <div className="eyebrow">watch · decision · options</div>
        <h1 className="page-title">{bi("观察清单", "Watchlist")}</h1>
      </div>

      <div className="panel panel-pad" style={{ marginBottom: "var(--gap)" }}>
        <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
          <span className="eyebrow">{bi("点任意一行展开它的期权策略候选", "Click a row to expand its option strategy candidates")}</span>
          <div className="stats" style={{ marginLeft: "auto" }}>
            <div className="stat"><dt>{bi("标的", "tickers")}</dt><dd>{rows.length}</dd></div>
            <div className="stat">
              <dt>{bi("信号可用", "signal ok")}</dt>
              <dd style={{ color: actionable ? "var(--pos)" : "var(--ink-3)" }}>{actionable}</dd>
            </div>
            <div className="stat"><dt>{bi("策略候选", "candidates")}</dt><dd>{totalCards}</dd></div>
          </div>
        </div>
      </div>

      {windows.length ? (
        <div className="panel panel-pad" style={{ marginBottom: "var(--gap)",
          borderColor: "var(--accent)", background: "var(--accent-soft)" }}>
          <div className="eyebrow" style={{ marginBottom: 9, color: "var(--accent)" }}>
            {bi("错价窗口候选 · iv 百分位 ≥ 55% 且信号方向可用", "Mispricing window · iv percentile ≥ 55% with a usable signal")}
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            {windows.map((w) => (
              <div key={w.ticker} style={{ flex: "0 1 300px", minWidth: 190 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                  <button className="mono" style={{ fontSize: 17, fontWeight: 500 }}
                    onClick={() => setExpanded((s) => ({ ...s, [w.ticker]: true }))}>
                    {w.ticker.replace("US.", "").replace("HK.", "")}
                  </button>
                  <DirLabel dir={w.direction} />
                </div>
                <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", marginTop: 3 }}>
                  conviction {fmtSigned(w.conviction)} · iv {w.ivRank != null ? fmtPct(w.ivRank, 0) : "—"} · iv30 {w.iv30 != null ? fmtPct(w.iv30) : "—"}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="panel">
        <div style={{ padding: "12px var(--pad)", borderBottom: "var(--hair) solid var(--rule)",
          display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span className="eyebrow">{bi("标的 → 期权策略", "Underlying → option strategies")}</span>
          <div className="seg seg-lite" style={{ marginLeft: "auto" }}>
            {([
              ["conviction", bi("按信号强度", "by conviction")],
              ["cards", bi("按候选数", "by candidates")],
              ["ticker", bi("按代码", "by ticker")],
            ] as const).map(([k, l]) => (
              <button key={k} aria-pressed={sort === k} onClick={() => setSort(k)}>{l}</button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 24 }} />
                <th style={{ minWidth: 118 }}>{bi("标的", "Ticker")}</th>
                <th className="r" style={{ minWidth: 88 }}>{bi("现价", "Price")}</th>
                <th style={{ minWidth: 196 }}>{bi("信号强度", "Signal")}</th>
                <th className="c" style={{ minWidth: 110 }}>{bi("一致性", "Agreement")}</th>
                <th className="c">{bi("波动率", "Vol")}</th>
                <th className="r">iv30</th>
                <th style={{ minWidth: 96 }}>{bi("IV 百分位", "IV pct")}</th>
                <th>{bi("下次财报", "Earnings")}</th>
                <th className="c" style={{ minWidth: 92 }}>{bi("策略候选", "Candidates")}</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => {
                const stop = r.agreement === "conflicted" || r.agreement === "insufficient_data";
                const chg = fmtDelta(r.spot, r.prevClose);
                const isOpen = !!expanded[r.ticker];
                return (
                  <WatchRowTr key={r.ticker} r={r} stop={stop} chg={chg} isOpen={isOpen}
                    cards={cardsByTicker[r.ticker]} verdicts={verdicts} onVerdict={onVerdict}
                    onToggle={() => setExpanded((s) => ({ ...s, [r.ticker]: !s[r.ticker] }))}
                    onOpenEvidence={onOpenEvidence} onOpenWorkbench={onOpenWorkbench} />
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function WatchRowTr({ r, stop, chg, isOpen, cards, verdicts, onVerdict, onToggle, onOpenEvidence, onOpenWorkbench }: {
  r: WatchRow; stop: boolean; chg: number | null; isOpen: boolean;
  cards: SellerCard[] | undefined;
  verdicts: Record<string, string | null>;
  onVerdict: (id: string, v: string | null) => void;
  onToggle: () => void;
  onOpenEvidence: (tab: string) => void;
  onOpenWorkbench: (ticker: string) => void;
}) {
  return (
    <>
      <tr data-stop={stop ? "1" : undefined} data-miss={r.spot == null ? "1" : undefined}
        onClick={onToggle} style={{ cursor: "pointer" }}>
        <td className="mono" style={{ color: "var(--ink-4)" }}>
          <span className="caret" data-open={isOpen ? "1" : undefined}>▶</span>
        </td>
        <td>
          <div className="mono" style={{ fontWeight: 500 }}>{r.ticker}</div>
          <div style={{ fontSize: 10, color: "var(--ink-4)" }}>{r.badge}</div>
        </td>
        <td className="r mono">
          {r.spot == null ? <Absent state="missing" text={bi("缺失", "missing")} /> : (
            <>
              {fmtNum(r.spot)}
              <div style={{ fontSize: 10, color: (chg ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                {chg != null ? fmtSigned(chg * 100) + "%" : ""}
              </div>
            </>
          )}
        </td>
        <td>
          <Tract rows={[{
            key: "s", label: "", conviction: r.conviction, direction: r.direction,
            status: r.agreement === "insufficient_data" ? "insufficient_data" : "actionable",
          }]} showScale={false} />
        </td>
        <td className="c"><AgreementBadge value={r.agreement} /></td>
        <td className="c">
          <ToneBadge tone={r.volatility_view === "rising" ? "neg"
            : r.volatility_view === "neutral" ? "mute" : "pos"}>
            {r.volatility_view === "rising" ? bi("上升 ↑", "rising ↑")
              : r.volatility_view === "falling" ? bi("下降 ↓", "falling ↓") : r.volatility_view}
          </ToneBadge>
        </td>
        <td className="r mono">{r.iv30 == null ? <Absent state="missing" /> : fmtPct(r.iv30)}</td>
        <td>
          {r.ivRank == null ? <Absent state="missing" /> : (
            <>
              <div className="tract-track" style={{ height: 6, marginBottom: 3 }}>
                <div className="tract-fill" data-sign="zero"
                  style={{ left: 0, width: r.ivRank * 100 + "%",
                    background: r.mispriceWindow ? "var(--accent)" : "var(--rule-strong)" }} />
              </div>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>{fmtPct(r.ivRank, 0)}</span>
              {r.mispriceWindow ? <span style={{ fontSize: 9.5, color: "var(--accent)", marginLeft: 5 }}>{bi("错价窗口", "window")}</span> : null}
            </>
          )}
        </td>
        <td className="mono" style={{ fontSize: 11, color: r.earningsDate ? "var(--ink-2)" : "var(--ink-4)" }}>
          {r.earningsDate || bi("未确认", "unconfirmed")}
        </td>
        <td className="c">
          {r.cards ? (
            <ToneBadge tone="mute">{r.cards}</ToneBadge>
          ) : (
            <span style={{ fontSize: 10, color: "var(--ink-4)" }}>{bi("无", "none")}</span>
          )}
        </td>
      </tr>

      {isOpen ? (
        <tr>
          <td colSpan={10} style={{ padding: 0, background: "var(--surface-2)" }}>
            <div style={{ padding: "16px var(--pad)" }}>
              <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
                <span className="eyebrow">{bi("期权策略候选 · 有限风险价差", "Option strategy candidates · defined-risk spreads")}</span>
                <div style={{ marginLeft: "auto", display: "flex", gap: 7 }}>
                  <button className="btn" style={{ padding: "3px 9px" }}
                    onClick={(e) => { e.stopPropagation(); onOpenWorkbench(r.ticker); }}>
                    {bi("在决策台打开", "Open in console")} {r.ticker.replace("US.", "").replace("HK.", "")} →
                  </button>
                  <button className="btn" style={{ padding: "3px 9px" }}
                    onClick={(e) => { e.stopPropagation(); onOpenEvidence("cov"); }}>
                    {bi("字段覆盖", "Field coverage")}
                  </button>
                </div>
              </div>

              {!cards ? (
                <div style={{ fontSize: 11, color: "var(--ink-4)" }}>…</div>
              ) : cards.length ? (
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
                  {cards.map((c) => (
                    <IncomeCard key={c.id} c={c} verdict={verdicts[c.id]} onVerdict={onVerdict} />
                  ))}
                </div>
              ) : !r.gateApproved && r.hasLedger ? (
                <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}>
                  <b>{bi("不生成结构", "No structures")}</b>
                  <span>{r.gateVetoes.join("；")}{bi("——信号闸未过，不生成候选结构。", " — the signal gate did not pass, so no candidates are generated.")}</span>
                </div>
              ) : (
                <div className="caveat">
                  <b>{bi("无候选", "No candidates")}</b>
                  <span>
                    {bi("信号可用，但链上凑不出同时满足持仓量、价差与盈亏比门槛的双边合约。日历 / 对角类结构需要同执行价的近远两月同时挂单，实际很难凑齐。",
                      "The signal is usable, but the chain cannot pair contracts that satisfy OI, spread and ret/risk gates at once. Calendar / diagonal structures need the same strike quoted in two months simultaneously, which is rare in practice.")}
                  </span>
                </div>
              )}

              <div style={{ marginTop: 13, display: "flex", gap: 18, flexWrap: "wrap",
                fontSize: 10, color: "var(--ink-4)", fontFamily: "var(--font-mono)" }}>
                <span>{bi("卖 bid / 买 ask，用保守权利金", "sell at bid / buy at ask, conservative credit")}</span>
                <span>{bi("历史卡片一律降级为「仅观察」", "historical cards always degrade to watch-only")}</span>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
