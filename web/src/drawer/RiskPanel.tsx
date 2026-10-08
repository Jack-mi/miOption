/* 阈值与账户：账户敞口 + 结构送检 + 阈值参数（每个参数一句人话）+ 复核结论 */
import { useEffect, useState } from "react";
import { bi } from "../i18n";
import { api, RiskPanelResponse } from "../lib/api";
import { fmtMoney } from "../lib/format";

const LIMIT_NOTES: Record<string, [string, string]> = {
  min_open_interest: ["一条腿最少要有多少人持仓", "Minimum holders per leg"],
  max_spread_pct: ["买卖价差最多占中间价多少", "Widest bid-ask as a share of mid"],
  max_position_risk_pct: ["单个标的能亏掉账户的几成", "Share of the account one underlying may risk"],
  earnings_blackout_days: ["财报前后多少天内禁做卖出波动率", "Days around earnings when short-vol is banned"],
  ex_div_blackout_days: ["除息前后多少天内禁做卖出波动率", "Days around ex-div when short-vol is banned"],
  min_credit_risk_ratio: ["收多少钱才值得担这份风险", "Credit required against the risk taken"],
  min_conviction: ["信号多强才算数", "How strong a signal must be to count"],
  dte_min: ["合约至少多少天后到期", "Earliest expiry considered"],
  dte_max: ["合约最晚多少天内到期", "Latest expiry considered"],
  drawdown_pct: ["五日内跌多少就标急跌", "Five-session drop that flags a sell-off"],
  quote_max_age_seconds: ["报价多少秒后就算旧", "Seconds before a quote counts as old"],
  account_max_age_seconds: ["账户权益多少秒后就算旧", "Seconds before account equity counts as old"],
  iv_hv_rising_ratio: ["IV/HV 到多少算波动率上升", "IV/HV ratio that counts as rising vol"],
  widths: ["价差可以拉多宽（美元）", "Candidate spread widths"],
};

export function RiskPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<RiskPanelResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setData(null);
    api.risk(ticker)
      .then((d) => { if (alive) setData(d); })
      .catch((e) => { if (alive) setErr(String(e && e.message || e)); });
    return () => { alive = false; };
  }, [ticker]);

  if (err) return <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}><b>risk</b><span>{err}</span></div>;
  if (!data) return <div style={{ fontSize: 11, color: "var(--ink-4)" }}>…</div>;

  const lim = data.limits || {};
  const acct = data.account_equity;
  const cap = acct && lim.max_position_risk_pct != null ? lim.max_position_risk_pct * acct.value : null;
  const rows = Object.keys(LIMIT_NOTES)
    .filter((k) => lim[k] !== undefined)
    .map((k) => {
      const v = Array.isArray(lim[k]) ? lim[k].join(" / ") : String(lim[k]);
      const [zh, en] = LIMIT_NOTES[k];
      return [k, v, bi(zh, en)] as const;
    });

  return (
    <div>
      <div className="caveat" style={{ marginBottom: 16 }}>
        <b>{bi("为什么放在这里", "Why it lives here")}</b>
        <span>
          {bi("风控是决策链路里的一个环节，不是一章。信号级门禁在 02 合成块末尾，逐结构否决在 03 每条结构上。参数与账户属于诊断数据，放在抽屉里可查。",
            "The risk gate is a stage in the pipeline, not a chapter. The signal-level gate sits at the end of 02; per-structure vetoes sit on each row in 03. Parameters and account state are diagnostics, so they sit in this drawer.")}
        </span>
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="panel panel-pad">
          <div className="eyebrow" style={{ marginBottom: 8 }}>{bi("账户敞口", "Account exposure")}</div>
          {acct ? (
            <div className="gap-list">
              <div className="gap-item">
                {bi("账户权益", "Account equity")}{" "}
                <b className="mono" style={{ marginLeft: 4 }}>{fmtMoney(acct.value)}</b>
                <span className="mono" style={{ marginLeft: 6, color: "var(--ink-4)" }}>{acct.env}/{acct.currency}</span>
              </div>
              <div className="gap-item">
                {bi("单个标的亏损上限", "Max loss per underlying")}{" "}
                <b className="mono" style={{ marginLeft: 4 }}>{cap == null ? "—" : fmtMoney(cap)}</b>
              </div>
              <div className="gap-item">
                {bi("可用现金", "Available cash")}{" "}
                <b className="mono" style={{ marginLeft: 4 }}>{fmtMoney(acct.available_cash)}</b>
              </div>
              <div className="gap-item">
                {bi("读取时间", "Read at")}{" "}
                <span className="mono" style={{ marginLeft: 4, color: "var(--ink-3)" }}>{String(acct.fetched_at || "").slice(11, 19)}Z</span>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "var(--neg)" }}>
              {bi("账户权益读不到，亏损上限检查已跳过。", "Account equity unavailable; the loss-cap check was skipped.")}
            </div>
          )}
        </div>

        <div className="panel panel-pad">
          <div className="eyebrow" style={{ marginBottom: 8 }}>{bi("结构送检结果", "Structures checked")}</div>
          <div className="stats">
            <div className="stat"><dt>{bi("送检", "Checked")}</dt><dd>{data.checked}</dd></div>
            <div className="stat"><dt>{bi("通过", "Passed")}</dt><dd style={{ color: "var(--pos)" }}>{data.checked - data.vetoed.length}</dd></div>
            <div className="stat"><dt>{bi("否决", "Vetoed")}</dt><dd style={{ color: data.vetoed.length ? "var(--neg)" : undefined }}>{data.vetoed.length}</dd></div>
          </div>
          <div className="gap-list" style={{ marginTop: 11 }}>
            {data.vetoed.map((v, i) => (
              <div className="gap-item" key={i} style={{ color: "var(--neg)", fontSize: 10.5 }}>
                {v.name} — {v.vetoes.join("；")}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="eyebrow" style={{ marginBottom: 9 }}>
        {bi("阈值参数", "Thresholds")}{" "}
        <span className="mono" style={{ textTransform: "none", letterSpacing: 0 }}>config.yaml · risk</span>
      </div>
      <div className="fields" style={{ border: "var(--hair) solid var(--rule)", background: "var(--surface)" }}>
        {rows.map(([k, v, note]) => (
          <div className="field" key={k}>
            <span className="field-name mono" style={{ fontSize: 11 }}>{k}</span>
            <span className="mono" style={{ fontWeight: 500 }}>{v}</span>
            <span className="field-note">{note}</span>
          </div>
        ))}
      </div>

      <div className="caveat" style={{ marginTop: 14 }}>
        <b>{bi("复核结论", "Review outcome")}</b>
        <span>
          {data.review && data.review.ok && !(data.review.findings || []).length
            ? bi("机器检查已完成。", "Mechanical checks completed.")
            : ((data.review && data.review.findings) || []).join("；") || bi("复核未通过或无记录", "Review failed or no record")}
        </span>
      </div>
    </div>
  );
}
