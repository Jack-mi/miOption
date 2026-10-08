/* 全局证据抽屉：字段覆盖矩阵 / 运行台账 / 阈值与账户。Esc 关闭。 */
import { useEffect } from "react";
import { bi } from "../i18n";
import { TickerInfo } from "../lib/api";
import { Boundary } from "../components/Boundary";
import { CoveragePanel } from "./CoveragePanel";
import { RunsPanel } from "./RunsPanel";
import { RiskPanel } from "./RiskPanel";

const TABS = [
  { key: "cov", label: bi("字段覆盖", "Field coverage"), hint: "coverage.json · 不含价格" },
  { key: "runs", label: bi("运行台账", "Run ledger"), hint: "runs/{date}.json" },
  { key: "risk", label: bi("阈值与账户", "Thresholds"), hint: "config.yaml · risk" },
];

export function EvidenceDrawer({ open, tab, onTab, onClose, tickers, focusTicker }: {
  open: boolean; tab: string; onTab: (t: string) => void; onClose: () => void;
  tickers: TickerInfo[]; focusTicker: string;
}) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const active = TABS.find((x) => x.key === tab) || TABS[0];

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 150 }}>
      <div onClick={onClose}
        style={{ position: "absolute", inset: 0, background: "rgba(20,16,10,.34)" }} />
      <aside
        role="dialog" aria-label="证据与溯源"
        style={{
          position: "absolute", top: 0, right: 0, bottom: 0, width: "min(920px, 94vw)",
          background: "var(--bg)", borderLeft: "var(--hair) solid var(--rule-strong)",
          boxShadow: "-24px 0 60px -30px rgba(0,0,0,.4)",
          display: "flex", flexDirection: "column",
        }}>
        <div style={{
          padding: "14px 20px", borderBottom: "var(--hair) solid var(--rule)",
          display: "flex", alignItems: "center", gap: 14, background: "var(--surface)",
        }}>
          <div>
            <div className="eyebrow">{bi("证据层 · 这个数从哪来、可不可信", "Evidence · where each number comes from")}</div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: "var(--display-weight)" }}>
              {bi("字段覆盖与运行台账", "Field coverage & run ledger")}
            </div>
          </div>
          <div className="seg seg-lite" style={{ marginLeft: "auto" }}>
            {TABS.map((x) => (
              <button key={x.key} aria-pressed={tab === x.key} onClick={() => onTab(x.key)}>{x.label}</button>
            ))}
          </div>
          <button className="btn" onClick={onClose} style={{ padding: "5px 10px" }}>{bi("关闭 Esc", "Close Esc")}</button>
        </div>

        <div style={{ padding: "11px 20px", borderBottom: "var(--hair) solid var(--rule)", background: "var(--surface-2)",
          display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge" data-tone="mute">{active.hint}</span>
          <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-4)" }}>
            {bi("覆盖文件按运行日记字段状态，", "Coverage records field states per run, ")}
            <b>{bi("不含价格", "no prices")}</b>
          </span>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
          <Boundary>
            {tab === "cov" ? (
              <CoveragePanel tickers={tickers} focusTicker={focusTicker} />
            ) : tab === "runs" ? (
              <RunsPanel tickers={tickers} focusTicker={focusTicker} />
            ) : (
              <RiskPanel ticker={focusTicker} />
            )}
          </Boundary>
        </div>
      </aside>
    </div>
  );
}
