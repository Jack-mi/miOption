/* 合成块：方向 + 五档刻度 + 投票账目 + 规则落点 + 分歧质量 + 账户敞口 + 信号级门禁 */
import { bi } from "../i18n";
import { fmtMoney, fmtPct, fmtSigned } from "../lib/format";
import {
  AgreementBadge, DirLabel, EnsembleTrack, Quote, ToneBadge,
} from "../components/ui";
import type { Workbench } from "../lib/api";

const ORDER = ["trend", "research", "value"] as const;

export function SynthBlock({ t }: { t: Workbench }) {
  const e = t.ensemble;
  const stop = e.agreement === "conflicted" || e.agreement === "insufficient_data";
  const approved = t.risk.signal_gate.approved;
  const sigs = ORDER.map((k) => t.signals[k]);
  const acct = t.risk.account_equity;
  const lim = t.risk.limits;
  const cap = acct && lim.max_position_risk_pct != null ? lim.max_position_risk_pct * acct.value : null;

  return (
    <div className="panel panel-pad" style={{ marginTop: "var(--gap)" }}>
      <div className="eyebrow" style={{ marginBottom: 12, color: "var(--accent)" }}>
        {bi("合成结论 · combine.py", "Ensemble result · combine.py")}{" "}
        <span className="mono" style={{ textTransform: "none", letterSpacing: 0, color: "var(--ink-4)" }}>
          {bi("纯确定性代码，无 LLM", "pure deterministic code, no LLM")}
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 26, alignItems: "flex-start" }}>
        <div style={{ minWidth: 200 }}>
          <div className="eyebrow">{bi("合成方向", "Direction")}</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 4 }}>
            <span className="mono" style={{ fontSize: 30, lineHeight: 1.1,
              color: e.direction.indexOf("buy") >= 0 ? "var(--pos)"
                : e.direction.indexOf("sell") >= 0 ? "var(--neg)" : "var(--ink-2)" }}>
              {fmtSigned(e.conviction, 4)}
            </span>
            <DirLabel dir={e.direction} />
          </div>
          <div style={{ marginTop: 9, display: "flex", gap: 6, flexWrap: "wrap" }}>
            <AgreementBadge value={e.agreement} />
            <ToneBadge tone="mute" title="EnsembleSignal.volatility_view">
              {bi("波动率", "vol")} {e.volatility_view}
            </ToneBadge>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 320 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            {bi("刻度位置（−1 强烈看空 ~ +1 强烈看多）", "Scale (−1 strong sell ~ +1 strong buy)")}
          </div>
          <EnsembleTrack conviction={e.conviction} agreement={e.agreement} />
          <div style={{ marginTop: 14 }}>
            <div className="eyebrow" style={{ marginBottom: 5 }}>{bi("合成说明", "Notes")}</div>
            <Quote>{e.quality_notes || bi("（无合成说明）", "(no synthesis notes)")}</Quote>
          </div>
        </div>
      </div>

      <hr className="rule" style={{ margin: "20px 0 16px" }} />

      <div className="grid g3">
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>{bi("投票账目 · 谁投了谁弃了", "Ballot · who voted, who abstained")}</div>
          <table className="tbl">
            <thead>
              <tr>
                <th>{bi("引擎", "Engine")}</th><th className="c">{bi("方向", "Dir")}</th>
                <th className="r">conviction</th><th className="c">{bi("投票", "Vote")}</th>
              </tr>
            </thead>
            <tbody>
              {sigs.map((s) => {
                const ab = s.data_status === "insufficient_data";
                return (
                  <tr key={s.engine} data-miss={ab ? "1" : undefined}>
                    <td>{s.engineLabel}</td>
                    <td className="c"><DirLabel dir={s.direction} /></td>
                    <td className="r mono">{fmtSigned(s.conviction)}</td>
                    <td className="c">
                      {ab ? <ToneBadge tone="neg" stop>{bi("弃权", "Abstained")}</ToneBadge>
                        : <ToneBadge tone="pos">{bi("计入", "Counted")}</ToneBadge>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>{bi("合成规则落点", "Rule landing")}</div>
          <div className="gap-list">
            <div className="gap-item">
              {bi("一致性判定", "Agreement")} <b className="mono" style={{ marginLeft: 4 }}>{e.agreement}</b>
            </div>
            <div className="gap-item">
              {bi("conviction 取投票者简单平均", "conviction = mean of voters")}
              <b className="mono" style={{ marginLeft: 4 }}>{fmtSigned(e.conviction, 4)}</b>
            </div>
            <div className="gap-item">
              {e.agreement === "aligned"
                ? <>{bi("同向且档位差 ≤ 1", "aligned, tier gap <= 1")}<b className="mono" style={{ marginLeft: 4 }}>{bi("×1.2 上浮已应用", "×1.2 boost applied")}</b></>
                : <>{bi("非 aligned", "not aligned")}<b className="mono" style={{ marginLeft: 4 }}>{bi("不做 ×1.2 上浮", "no ×1.2 boost")}</b></>}
            </div>
            <div className="gap-item">
              {e.agreement === "single_source"
                ? <>{bi("仅一票", "single voter")}<b className="mono" style={{ marginLeft: 4 }}>{bi("×0.7 单源折扣已应用", "×0.7 discount applied")}</b></>
                : <>{bi("投票数 ≥ 2", "voters >= 2")}<b className="mono" style={{ marginLeft: 4 }}>{bi("不施加 ×0.7 单源折扣", "no ×0.7 discount")}</b></>}
            </div>
          </div>

          <div className="eyebrow" style={{ margin: "14px 0 6px" }}>{bi("催化事件 · catalysts", "Catalysts")}</div>
          <div className="gap-list">
            {(e.catalysts || []).length ? e.catalysts.map((c: any, i: number) => (
              <div className="gap-item" key={i}>
                <span className="mono" style={{ color: "var(--accent)" }}>{c.expected_date}</span>
                {c.description}
              </div>
            )) : (
              <div className="gap-item" style={{ color: "var(--ink-4)" }}>{bi("无", "None")}</div>
            )}
          </div>
        </div>

        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>{bi("分歧与质量", "Dissent and quality")}</div>
          {e.dissent_summary ? <Quote>{e.dissent_summary}</Quote> : null}
          {e.quality_notes ? (
            <div className="gap-list" style={{ marginTop: 10 }}>
              {e.quality_notes.split(" | ").map((n, i) => (
                <div className="gap-item" key={i}>{n}</div>
              ))}
            </div>
          ) : null}

          {acct ? (
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: "var(--hair) solid var(--rule)" }}>
              <div className="eyebrow" style={{ marginBottom: 7 }}>
                {bi("账户敞口上限", "Account exposure cap")}
              </div>
              <div className="gap-list">
                <div className="gap-item">
                  {bi("账户权益", "Account equity")}{" "}
                  <b className="mono" style={{ marginLeft: 4 }}>{fmtMoney(acct.value)}</b>
                  <span className="mono" style={{ marginLeft: 6, color: "var(--ink-4)" }}>{acct.env}/{acct.currency}</span>
                </div>
                <div className="gap-item">
                  {bi("单个标的亏损上限", "Max loss per underlying")}{" "}
                  <b className="mono" style={{ marginLeft: 4 }}>{cap == null ? "—" : fmtMoney(cap)}</b>
                  {lim.max_position_risk_pct != null ? (
                    <span className="mono" style={{ marginLeft: 5, color: "var(--ink-4)" }}>{fmtPct(lim.max_position_risk_pct, 0)}</span>
                  ) : null}
                </div>
              </div>
            </div>
          ) : (
            <div className="caveat" style={{ marginTop: 14, borderStyle: "solid", borderColor: "var(--warn)", background: "var(--warn-soft)" }}>
              <b>{bi("告警", "Warning")}</b>
              <span>{bi("账户权益读不到，亏损上限检查已跳过。", "Account equity unavailable; the loss-cap check was skipped.")}</span>
            </div>
          )}
        </div>
      </div>

      <div
        className="caveat"
        style={{
          marginTop: 18, borderStyle: "solid",
          borderColor: stop ? "var(--neg)" : "var(--rule-strong)",
          background: stop ? "var(--neg-soft)" : undefined,
        }}>
        <b>{bi("信号级门禁", "Signal-level gate")}</b>
        <span>
          {approved ? (
            <>
              {bi("通过。合成方向", "Passed. Direction")} <span className="mono">{e.direction}</span>，
              {bi("一致性", "agreement")} <span className="mono">{e.agreement}</span>，
              {bi("未触发 conflicted 阻断。", "no conflicted block.")}
            </>
          ) : (
            <>
              <span style={{ color: "var(--neg)" }}>{bi("不通过", "Blocked")}</span>：
              {(t.risk.signal_gate.vetoes || []).join("；") || bi("信号闸未通过", "signal gate did not pass")}
            </>
          )}
        </span>
      </div>
    </div>
  );
}
