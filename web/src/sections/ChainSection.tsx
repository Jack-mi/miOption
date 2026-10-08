/* 03 上半：链快照。四个指标格 + 到期日 IV 表；链缺失时红框说明。 */
import { bi } from "../i18n";
import { nf, fmtPct, fmtNum } from "../lib/format";
import { ToneBadge } from "../components/ui";
import type { Workbench } from "../lib/api";

export function ChainSection({ t }: { t: Workbench }) {
  const c = t.chain;
  return (
    <div className="panel panel-pad">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <span className="eyebrow" style={{ marginBottom: 0, color: "var(--accent)" }}>
          {bi("期权链 · ChainSnapshot", "Option chain · ChainSnapshot")}
        </span>
        {c ? (
          <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
            <ToneBadge tone={c.degraded ? "warn" : "pos"}>
              {c.degraded ? bi("已降级", "Degraded") : bi("未降级", "Not degraded")}
            </ToneBadge>
            <ToneBadge tone="mute">source: {c.source}</ToneBadge>
          </div>
        ) : null}
      </div>

      {!c ? (
        <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)", background: "var(--neg-soft)" }}>
          <b>{bi("期权链缺失", "Option chain missing")}</b>
          <span>
            {bi("没有链快照，结构只能给出「做不了」——不拿空列表冒充无机会。",
              "Without a chain snapshot every structure reports impossible — an empty list is never passed off as no opportunity.")}
          </span>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 0, flexWrap: "wrap", border: "var(--hair) solid var(--rule)", marginBottom: 14 }}>
            {([
              ["spot", fmtNum(c.spot), bi("报价级联统一 spot", "unified spot")],
              [bi("行数", "Rows"), nf.format(c.rows), "OptionRow"],
              [bi("到期日", "Expiries"), String(c.expiries.length), c.expiries.join(" · ")],
              [bi("抓取时刻", "Fetched"), String(c.fetched_at || "").slice(11, 19) + "Z", String(c.fetched_at || "").slice(0, 10)],
            ] as const).map(([k, v, note]) => (
              <div className="health-cell" key={k} style={{ flexDirection: "column", alignItems: "flex-start", gap: 2, padding: "11px 18px", borderRight: "var(--hair) solid var(--rule)" }}>
                <span className="health-key">{k}</span>
                <b style={{ fontSize: 15 }}>{v}</b>
                <span style={{ fontSize: 10, color: "var(--ink-4)", whiteSpace: "normal", maxWidth: 240 }}>{note}</span>
              </div>
            ))}
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th>{bi("到期日", "Expiry")}</th><th className="r">dte</th><th className="r">atm_iv</th>
                <th className="r">{bi("价差中值", "Spread (mid)")}</th>
                <th className="r">{bi("持仓量", "Open interest")}</th>
                <th>{bi("IV 相对位置", "IV position")}</th>
              </tr>
            </thead>
            <tbody>
              {c.iv_by_expiry.map((r) => {
                const ivs = c.iv_by_expiry.map((x) => x.atm_iv).filter((x): x is number => x != null);
                const maxIv = ivs.length ? Math.max(...ivs) : 1;
                return (
                  <tr key={r.expiry}>
                    <td className="mono">{r.expiry}</td>
                    <td className="r mono">{r.dte == null ? "—" : r.dte}</td>
                    <td className="r mono">{r.atm_iv == null ? "—" : fmtPct(r.atm_iv)}</td>
                    <td className="r mono">{r.spread_pct == null ? "—" : fmtPct(r.spread_pct)}</td>
                    <td className="r mono">{nf.format(r.oi)}</td>
                    <td>
                      {r.atm_iv != null ? (
                        <div className="tract-track" style={{ height: 10, width: 120 }}>
                          <div className="tract-fill" style={{ left: 0, width: (r.atm_iv / maxIv) * 100 + "%", background: "var(--accent)", opacity: .6 }} />
                        </div>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
