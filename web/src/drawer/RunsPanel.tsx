/* 运行台账：引擎三态 + 耗时 + agent 表 + 一致性/信号闸/复核 + 宏观层 */
import { useEffect, useState } from "react";
import { bi } from "../i18n";
import { api, RunLedgerResponse, TickerInfo } from "../lib/api";
import { nf, fmtNum } from "../lib/format";
import { AgreementBadge, ToneBadge } from "../components/ui";

export function RunsPanel({ tickers, focusTicker }: { tickers: TickerInfo[]; focusTicker: string }) {
  const [tkFocus, setTkFocus] = useState(focusTicker);
  const [data, setData] = useState<RunLedgerResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    api.runs(tkFocus)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(String(e && e.message || e)); });
    return () => { alive = false; };
  }, [tkFocus]);

  return (
    <div>
      <div className="seg seg-lite" style={{ marginBottom: 12 }}>
        {tickers.map((t) => (
          <button key={t.ticker} aria-pressed={tkFocus === t.ticker} onClick={() => setTkFocus(t.ticker)}>
            {t.ticker.replace("US.", "").replace("HK.", "")}
          </button>
        ))}
      </div>

      {err ? <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}><b>runs</b><span>{err}</span></div>
        : !data ? <div style={{ fontSize: 11, color: "var(--ink-4)" }}>…</div>
        : !data.hasLedger ? (
          <div className="caveat">
            <b>{bi("无台账", "No ledger")}</b>
            <span>{bi("台账里没有这只标的的运行记录。", "No run record for this underlying in the ledger.")}</span>
          </div>
        ) : (
          <>
            <div className="grid g4" style={{ marginBottom: 13 }}>
              {(["trend", "research", "value"] as const).map((k) => {
                const v = (data.engines || {})[k] || "abstain";
                return (
                  <div className="panel panel-pad" key={k}>
                    <div className="eyebrow" style={{ marginBottom: 5 }}>{k}</div>
                    <span className="badge" data-tone={v === "ok" ? "pos" : v === "opinion" ? "warn" : "neg"}
                      data-stop={v === "abstain" ? "1" : undefined}>
                      {v === "abstain" ? bi("■ 弃权", "■ abstain") : v}
                    </span>
                  </div>
                );
              })}
              <div className="panel panel-pad">
                <div className="eyebrow" style={{ marginBottom: 5 }}>{bi("耗时", "elapsed")}</div>
                <div className="mono" style={{ fontSize: 18 }}>{data.elapsed_sec != null ? data.elapsed_sec + "s" : "—"}</div>
              </div>
            </div>

            <table className="tbl">
              <thead>
                <tr><th>agent</th><th>thread_id</th><th className="r">input</th><th className="r">output</th></tr>
              </thead>
              <tbody>
                {(data.agents || []).map((x, i) => (
                  <tr key={i}>
                    <td className="mono">{x.agent}</td>
                    <td className="mono" style={{ color: "var(--ink-3)" }}>{x.thread_id || "—"}</td>
                    <td className="r mono">{x.input_tokens != null ? nf.format(x.input_tokens) : (x.model ? "model: " + x.model : "—")}</td>
                    <td className="r mono">{x.output_tokens != null ? nf.format(x.output_tokens) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="grid g2" style={{ marginTop: 14 }}>
              <div>
                <div className="eyebrow" style={{ marginBottom: 6 }}>{bi("一致性 · 信号闸 · 动作", "Agreement · gate · action")}</div>
                <div className="gap-list">
                  <div className="gap-item" style={{ alignItems: "center" }}>
                    <AgreementBadge value={(data.ensemble || {}).agreement || "insufficient_data"} />
                  </div>
                  <div className="gap-item" style={{ alignItems: "center" }}>
                    {(data.signal_gate || {}).approved
                      ? <ToneBadge tone="pos">{bi("信号闸通过", "Gate passed")}</ToneBadge>
                      : <ToneBadge tone="neg" stop>{bi("信号闸阻断", "Gate blocked")}</ToneBadge>}
                    <span className="mono" style={{ marginLeft: 7 }}>action = {data.action || "—"}</span>
                  </div>
                  {(((data.signal_gate || {}).vetoes) || []).map((v: string, i: number) => (
                    <div className="gap-item" key={i} style={{ color: "var(--neg)", fontSize: 10.5 }}>{v}</div>
                  ))}
                </div>
              </div>
              <div>
                <div className="eyebrow" style={{ marginBottom: 6 }}>{bi("复核 findings", "Review findings")}</div>
                <div className="gap-list">
                  {(data.review && (data.review.findings || []).length)
                    ? data.review.findings.map((f: string, i: number) => (
                      <div className="gap-item" key={i} style={{ color: "var(--warn)" }}>{f}</div>
                    ))
                    : <div className="gap-item" style={{ color: "var(--pos)" }}>{bi("完成既定机械检查，无 findings", "Mechanical checks completed, no findings")}</div>}
                  <div className="gap-item" style={{ color: "var(--ink-4)", fontSize: 10 }}>
                    {bi("复核完成表示既定检查完成，不表示全面交易验证。",
                      "A completed review means the defined checks ran, not a full trading validation.")}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 14 }}>
              <div className="eyebrow" style={{ marginBottom: 7 }}>
                {bi("宏观共享层 · macro_latest", "Macro shared layer · macro_latest")}
              </div>
              {(data.macro || []).length ? (
                <table className="tbl">
                  <thead>
                    <tr><th>{bi("序列", "Series")}</th><th className="r">{bi("最新", "Latest")}</th><th>as_of</th></tr>
                  </thead>
                  <tbody>
                    {data.macro!.map((m: any, i: number) => (
                      <tr key={i}>
                        <td className="mono">{m.series}</td>
                        <td className="r mono">{m.value != null ? fmtNum(m.value, 2) : "—"}</td>
                        <td className="mono" style={{ color: "var(--ink-3)" }}>{m.as_of}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ fontSize: 11, color: "var(--ink-4)" }}>
                  {bi("本轮宏观层为空（refresh 失败或未跑）。", "Macro layer is empty this round (refresh failed or not run).")}
                </div>
              )}
            </div>
          </>
        )}
    </div>
  );
}
