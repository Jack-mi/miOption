/* 字段覆盖矩阵：行 = 字段，列 = 标的 */
import { useEffect, useState } from "react";
import { bi } from "../i18n";
import { api, CoverageResponse, TickerInfo } from "../lib/api";

export function CoveragePanel({ tickers, focusTicker }: { tickers: TickerInfo[]; focusTicker: string }) {
  const [data, setData] = useState<CoverageResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const tks = tickers.map((t) => t.ticker);

  useEffect(() => {
    let alive = true;
    api.coverage(tks)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(String(e && e.message || e)); });
    return () => { alive = false; };
  }, [tks.join(",")]);

  if (err) return <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}><b>coverage</b><span>{err}</span></div>;
  if (!data) return <div style={{ fontSize: 11, color: "var(--ink-4)" }}>…</div>;

  const glyph = (s: string) => s === "available" ? "●" : s === "missing" ? "✕"
    : s === "unsupported" ? "—" : s === "stale" ? "◐" : "·";

  return (
    <div>
      <div className="caveat" style={{ marginBottom: 16 }}>
        <b>{bi("这一屏回答什么", "What this answers")}</b>
        <span>
          {bi("今天这次跑，每个字段真的取到了吗。missing = 该取没取到；unsupported = 本轮不接入；无记录 = 台账里没有这只标的。",
            "Did every field actually get fetched in this run. missing = should have been fetched; unsupported = not wired this round; no record = the underlying has no ledger entry.")}
        </span>
      </div>

      <div style={{ overflowX: "auto", border: "var(--hair) solid var(--rule)", background: "var(--surface)" }}>
        <table className="matrix">
          <thead>
            <tr>
              <th style={{ minWidth: 132 }}>{bi("字段", "Field")}</th>
              {data.tickers.map((k) => (
                <th key={k} className="mono" style={{ textAlign: "center", minWidth: 74 }}>
                  {k.replace("US.", "").replace("HK.", "")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.fields.map((f) => (
              <tr key={f.id}>
                <td>
                  {f.name}
                  <span className="mono" style={{ color: "var(--ink-4)", fontSize: 9.5, marginLeft: 7 }}>{f.id}</span>
                </td>
                {data.tickers.map((k) => {
                  const st = (data.matrix[k] || {})[f.id] || "unknown";
                  const isFocus = k === focusTicker;
                  return (
                    <td key={k} className="cell-s" data-s={st === "unknown" ? undefined : st}
                      title={k + " / " + f.id + " = " + st}>
                      {glyph(st)}
                      {isFocus ? (
                        <span style={{ fontSize: 8.5, marginLeft: 4, opacity: .8 }}>
                          {st === "available" ? "avail" : st === "unsupported" ? "n/a" : st.slice(0, 4)}
                        </span>
                      ) : null}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 10, fontSize: 10.5, color: "var(--ink-3)", lineHeight: 1.7 }}>
        <b>●</b> available（{bi("可用，带内容", "with content")}）&nbsp;·&nbsp;
        <b style={{ color: "var(--neg)" }}>✕</b> missing（{bi("该取没取到", "should have been fetched")}，<b>{bi("不是 0", "never 0")}</b>）&nbsp;·&nbsp;
        <b style={{ color: "var(--na)" }}>—</b> unsupported（{bi("本轮不接入", "not wired this round")}）&nbsp;·&nbsp;
        <b style={{ color: "var(--warn)" }}>◐</b> stale（{bi("过期", "stale")}）&nbsp;·&nbsp;
        <b className="mono">·</b> {bi("无记录", "no record")}
      </div>
    </div>
  );
}
