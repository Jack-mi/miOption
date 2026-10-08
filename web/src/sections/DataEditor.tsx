/* 数据源编辑器：改 7 个字段，POST /api/recompute 当场重算走势 + 合成。
   重算在 api 侧做（确定性，不碰 LLM、不取数），这里只发输入、画结果。 */
import { useState } from "react";
import { bi } from "../i18n";
import { api, RecomputeResult, Workbench } from "../lib/api";
import { fmtSigned } from "../lib/format";
import { AgreementBadge, DirLabel, EnsembleTrack, ToneBadge } from "../components/ui";
import { Boundary } from "../components/Boundary";

const EDITABLE = [
  { id: "quote", label: "报价", step: 0.01, unit: "USD",
    hint: "改了价格会直接影响走势的技术面得分与所有结构的下单腿行权价",
    impact: ["trend", "chain", "menu"] },
  { id: "sma5", label: "5 日均线", step: 0.01, unit: "USD",
    hint: "走势引擎的第一分：价格在均线之上还是之下", impact: ["trend"] },
  { id: "sma20", label: "20 日均线", step: 0.01, unit: "USD",
    hint: "仅用于图表参照，不参与打分", impact: ["display"] },
  { id: "flow", label: "资金净额", step: 1, unit: "USD",
    hint: "走势引擎的第二分：正负决定加减分", impact: ["trend"] },
  { id: "rsi14", label: "RSI 14", step: 0.1, unit: "",
    hint: "展示用，规则引擎不读", impact: ["display"] },
  { id: "iv30", label: "30 日隐含波动率", step: 0.005, unit: "",
    hint: "影响期权链的 IV 展示与波动率视图判断", impact: ["chain", "volatility"] },
  { id: "earningsGap", label: "距下次财报天数", step: 1, unit: "天",
    hint: "小于财报窗口天数时会禁止 short-vol 结构", impact: ["risk"] },
] as const;

export function DataEditor({ t, onClose }: { t: Workbench; onClose: () => void }) {
  const base: Record<string, number | null> = {
    quote: t.spot, sma5: t.sma5, sma20: t.sma20,
    flow: null, rsi14: t.rsi14, iv30: t.iv30,
    earningsGap: t.earningsDate
      ? Math.round((new Date(t.earningsDate).getTime() - new Date(t.asOf).getTime()) / 86400000)
      : null,
  };
  const [draft, setDraft] = useState<Record<string, number | null>>(base);
  const [rerun, setRerun] = useState<(RecomputeResult & { at: string }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const dirty = Object.keys(draft).some((k) => Number(draft[k]) !== Number(base[k]));

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const out = await api.recompute({ ticker: t.ticker, ...draft });
      setRerun({ ...out, at: new Date().toISOString().slice(11, 19) + "Z" });
    } catch (e: any) {
      setErr(String(e && e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel panel-pad" style={{ borderColor: "var(--accent)", marginBottom: "var(--gap)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
        <span className="eyebrow" style={{ color: "var(--accent)" }}>
          {bi("数据源修改 · 改完重新触发决策", "Edit data source · re-run the decision")}
        </span>
        <span style={{ fontSize: 11, color: "var(--ink-3)" }}>
          {bi("改价格或均线会改变走势引擎，进而改变合成、风控与菜单。",
            "Changing price or the moving average changes the trend engine, and through it synthesis, risk and the menu.")}
        </span>
        <button className="btn" style={{ marginLeft: "auto" }} onClick={onClose}>
          {bi("收起", "Hide")}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(292px, 1fr))", gap: 12 }}>
        {EDITABLE.map((f) => (
          <div key={f.id} style={{ border: "var(--hair) solid var(--rule)", borderRadius: "var(--radius)", padding: "11px 13px" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontSize: 12.5, fontWeight: 500 }}>{bi(f.label, f.label)}</span>
              <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{f.id}</span>
              <span className="mono" style={{ marginLeft: "auto", fontSize: 10, color: "var(--ink-4)" }}>{f.unit}</span>
            </div>
            <input
              type="number" step={f.step}
              value={draft[f.id] == null ? "" : (draft[f.id] as number)}
              placeholder={bi("缺失", "missing")}
              onChange={(e) => setDraft((s) => ({
                ...s, [f.id]: e.target.value === "" ? null : Number(e.target.value),
              }))}
              style={{
                width: "100%", marginTop: 8, padding: "6px 9px",
                border: "var(--hair) solid var(--rule-strong)", borderRadius: "var(--radius)",
                background: "var(--surface)", color: "var(--ink)",
                fontFamily: "var(--font-mono)", fontSize: 12.5, outline: "none",
              }} />
            <div style={{ marginTop: 7, fontSize: 10.5, color: "var(--ink-3)", lineHeight: 1.55 }}>
              {bi(f.hint, f.hint)}
            </div>
            <div style={{ marginTop: 6, display: "flex", gap: 4, flexWrap: "wrap" }}>
              {f.impact.map((k) => (
                <ToneBadge key={k} tone={k === "display" ? "mute" : "accent"}>{k}</ToneBadge>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 9, alignItems: "center", marginTop: 16, flexWrap: "wrap" }}>
        <button className="hero-cta" style={{ padding: "8px 18px", fontSize: 12.5 }}
          onClick={run} disabled={busy}>
          {busy ? bi("重算中…", "Recomputing…") : bi("用新数据重新跑一遍", "Re-run with the new data")}
        </button>
        {dirty ? <ToneBadge tone="warn">{bi("有未生效的修改", "Unapplied edits")}</ToneBadge> : null}
        {rerun ? (
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{rerun.at}</span>
        ) : null}
        {err ? (
          <span className="mono" style={{ fontSize: 10.5, color: "var(--neg)" }}>{err}</span>
        ) : null}
      </div>

      {rerun ? (
        <Boundary>
          <div style={{ marginTop: 16, borderTop: "var(--hair) solid var(--rule)", paddingTop: 15 }}>
            <div className="eyebrow" style={{ marginBottom: 11 }}>
              {bi("重跑结果 · 确定性部分已按新输入重算", "Re-run result · deterministic stages recomputed from the new input")}
            </div>

            <div className="grid g2">
              <div>
                <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginBottom: 6 }}>
                  {bi("走势引擎", "Trend engine")}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 11 }}>
                  <DirLabel dir={rerun.trend.direction} />
                  <span className="mono" style={{ fontSize: 17 }}>{fmtSigned(rerun.trend.conviction)}</span>
                </div>
                <div className="quote" style={{ marginTop: 9, fontSize: 12.5 }}>{rerun.trend.text}</div>
              </div>

              <div>
                <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginBottom: 6 }}>
                  {bi("合成结论", "Ensemble")}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 11, flexWrap: "wrap" }}>
                  <DirLabel dir={rerun.ensemble.direction} />
                  <span className="mono" style={{ fontSize: 17 }}>{fmtSigned(rerun.ensemble.conviction)}</span>
                  <AgreementBadge value={rerun.ensemble.agreement} />
                </div>
                <div style={{ marginTop: 9 }}>
                  <EnsembleTrack conviction={rerun.ensemble.conviction} agreement={rerun.ensemble.agreement} />
                </div>
              </div>
            </div>

            {rerun.riskNotes.length ? (
              <div className="caveat" style={{ marginTop: 14, borderStyle: "solid", borderColor: "var(--neg)", background: "var(--neg-soft)" }}>
                <b>{bi("风控影响", "Risk impact")}</b>
                <span>{rerun.riskNotes.join(" ")}</span>
              </div>
            ) : null}

            <div className="caveat" style={{ marginTop: 12 }}>
              <b>{bi("未重算的部分", "Not recomputed")}</b>
              <span>{rerun.notRecomputed.join("；")}</span>
            </div>
          </div>
        </Boundary>
      ) : null}
    </div>
  );
}
