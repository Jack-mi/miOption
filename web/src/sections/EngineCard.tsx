/* 三份信号引擎卡：头部（名称 + id + 状态徽章）→ 主体（方向/把握/引文/主张/缺失/风险）→ 脚注 */
import { bi } from "../i18n";
import { fmtSigned } from "../lib/format";
import { DataStatusBadge, DirLabel, Quote } from "../components/ui";
import type { EngineSignalView } from "../lib/api";

export function EngineCard({ s }: { s: EngineSignalView }) {
  const abstain = s.data_status === "insufficient_data";
  return (
    <div className="panel engine-card">
      <div className="engine-card-head">
        <span className="engine-name">{s.engineLabel}</span>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{s.engine}</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <DataStatusBadge value={s.data_status} />
        </div>
      </div>

      <div className="engine-body">
        <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
          {abstain ? (
            <span className="badge" data-tone="neg" data-stop="1">
              <span className="badge-stop-glyph">■</span>{bi("弃权 · 不投票", "Abstained")}
            </span>
          ) : (
            <>
              <DirLabel dir={s.direction} />
              <span className="mono" style={{ fontSize: 21, color: "var(--ink)" }}>
                {fmtSigned(s.conviction)}
              </span>
              <span style={{ fontSize: 11, color: "var(--ink-4)" }}>conviction</span>
            </>
          )}
          <span style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-4)" }}>
            {bi("波动率视图", "vol view")} {s.volatility_view}
          </span>
        </div>

        <Quote>{s.reasoning || bi("（没有正文）", "(no body)")}</Quote>

        {s.claims && s.claims.length ? (
          <div>
            <div className="eyebrow" style={{ marginBottom: 5 }}>{bi("被接受的财务主张 · claims", "Accepted claims")}</div>
            <div className="gap-list">
              {s.claims.map((c, i) => (
                <div className="gap-item" key={i} style={{ fontFamily: "var(--font-mono)", fontSize: 10.5 }}>{c}</div>
              ))}
            </div>
          </div>
        ) : null}

        {s.data_gaps && s.data_gaps.length ? (
          <div>
            <div className="eyebrow" style={{ marginBottom: 5 }}>{bi("缺失与降级 · data_gaps", "Gaps · data_gaps")}</div>
            <div className="gap-list">
              {s.data_gaps.map((g, i) => <div className="gap-item" key={i}>{g}</div>)}
            </div>
          </div>
        ) : null}

        {s.risk_flags && s.risk_flags.length ? (
          <div>
            <div className="eyebrow" style={{ marginBottom: 5 }}>{bi("风险标记", "Risk flags")}</div>
            <div className="gap-list">
              {s.risk_flags.map((g, i) => <div className="gap-item" key={i} style={{ color: "var(--warn)" }}>{g}</div>)}
            </div>
          </div>
        ) : null}
      </div>

      <div className="engine-foot">
        <span>{s.engine_kind}</span>
        <span className="mono">{s.llm_model || "llm_model: null"}</span>
        <span className="mono">{s.signal_id}</span>
      </div>
    </div>
  );
}
