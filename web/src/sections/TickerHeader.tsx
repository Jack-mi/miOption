/* 00 标的总览 + 左侧 sticky 阶段轴 */
import { bi } from "../i18n";
import { fmtNum, fmtSigned, fmtDelta, fmtPct } from "../lib/format";
import { Absent, Spark } from "../components/ui";
import type { Workbench } from "../lib/api";

export const STAGES = [
  { id: "s0", n: "00", name: "标的总览" },
  { id: "s1", n: "01", name: "数据层" },
  { id: "s2", n: "02", name: "信号与合成" },
  { id: "s3", n: "03", name: "期权链与结构" },
  { id: "s4", n: "04", name: "中文简报" },
];

export function StageAxis({ active, onGo }: { active: string; onGo: (id: string) => void }) {
  return (
    <nav className="stage-axis" aria-label="链路阶段">
      <div className="eyebrow" style={{ marginBottom: 10 }}>signal_chain</div>
      <ul className="stage-axis-list">
        {STAGES.map((s) => (
          <li key={s.id}>
            <a className="stage-axis-item" href={"#" + s.id} data-active={active === s.id ? "1" : undefined}
              onClick={(e) => { e.preventDefault(); onGo(s.id); }}>
              <span className="stage-axis-idx">{s.n}</span>
              <span>{bi(s.name, s.name)}</span>
            </a>
          </li>
        ))}
      </ul>
      <div style={{ marginTop: 22, paddingTop: 14, borderTop: "var(--hair) solid var(--rule)" }}>
        <div className="eyebrow" style={{ marginBottom: 7 }}>{bi("链路顺序固定", "Fixed order")}</div>
        <p style={{ margin: 0, fontSize: 11, color: "var(--ink-3)", lineHeight: 1.6 }}>
          {bi("data → decision → review → 简报。不能调换，也不能跳过。工具层没有下单能力。",
            "data → decision → review → report. The order is fixed and no stage can be skipped. The toolchain cannot place orders.")}
        </p>
      </div>
    </nav>
  );
}

export function TickerHeader({ t }: { t: Workbench }) {
  const chg = t.spot != null && t.prevClose != null ? t.spot - t.prevClose : null;
  const chgPct = fmtDelta(t.spot, t.prevClose);
  const missing = t.spot == null;
  return (
    <div className="panel panel-pad" style={{ marginBottom: "var(--gap)" }} id="s0-anchor">
      <div style={{ display: "flex", flexWrap: "wrap", gap: 30, alignItems: "flex-start" }}>
        <div style={{ minWidth: 230 }}>
          <div className="eyebrow">{bi("标的 · underlying", "Underlying")}</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 5 }}>
            <span className="mono" style={{ fontSize: 27, fontWeight: 500, letterSpacing: "-.01em" }}>{t.ticker}</span>
            <span style={{ color: "var(--ink-3)", fontSize: 13 }}>{bi(t.nameZh + " · " + t.name, t.name)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 8 }}>
            {missing ? (
              <>
                <span className="hatch" style={{ fontSize: 15, padding: "2px 8px" }}>{bi("报价缺失", "Quote missing")}</span>
                <span style={{ fontSize: 11, color: "var(--ink-3)" }}>
                  {bi("非 available 报价不得携带价格", "A non-available quote never carries a price")}
                </span>
              </>
            ) : (
              <>
                <span className="mono" style={{ fontSize: 31, lineHeight: 1 }}>{fmtNum(t.spot)}</span>
                <span className="mono" style={{ fontSize: 14, color: (chg ?? 0) >= 0 ? "var(--pos)" : "var(--neg)" }}>
                  {fmtSigned(chg)} ({chgPct != null ? fmtSigned(chgPct * 100) + "%" : "—"})
                </span>
                <span style={{ fontSize: 11, color: "var(--ink-4)" }}>{t.currency}</span>
              </>
            )}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 260 }}>
          <div className="eyebrow" style={{ marginBottom: 7 }}>{bi("技术面 · 由日线推导", "Technicals · from daily bars")}</div>
          <div className="stats">
            {([
              { k: "sma_5", v: t.sma5, d: 2 },
              { k: "sma_20", v: t.sma20, d: 2 },
              { k: "rsi_14", v: t.rsi14, d: 1 },
              { k: "atr_14", v: t.atr14, d: 2 },
            ] as const).map((x) => (
              <div className="stat" key={x.k}>
                <dt>{x.k}</dt>
                <dd>
                  {x.v == null ? <Absent state="missing" text={bi("缺失", "missing")} /> : fmtNum(x.v, x.d)}
                  {x.v != null && t.spot != null && x.k === "sma_5" ? (
                    <small style={{ color: t.spot > x.v ? "var(--pos)" : "var(--neg)" }}>
                      {t.spot > x.v ? bi("价格在上", "above") : bi("价格在下", "below")}
                    </small>
                  ) : null}
                </dd>
              </div>
            ))}
          </div>
        </div>

        <div style={{ minWidth: 250 }}>
          <div className="eyebrow" style={{ marginBottom: 7 }}>{bi("期权链 · 行情", "Option chain")}</div>
          <div className="stats">
            <div className="stat">
              <dt>atm_iv</dt>
              <dd>{t.atmIv != null ? fmtPct(t.atmIv) : <Absent state="missing" />}</dd>
            </div>
            <div className="stat">
              <dt>{bi("iv 百分位", "iv percentile")}</dt>
              <dd>{t.ivPercentile != null ? fmtPct(t.ivPercentile, 0) : <Absent state="missing" />}</dd>
            </div>
            <div className="stat">
              <dt>{bi("下次财报", "next earnings")}</dt>
              <dd style={{ fontSize: 14, paddingTop: 4 }}>
                {t.earningsDate || <Absent state="missing" text={bi("未确认", "unconfirmed")} />}
              </dd>
            </div>
          </div>
          {t.earningsSource ? (
            <div style={{ fontSize: 10.5, color: "var(--ink-4)", marginTop: 2 }}>
              {bi("来源：", "Source: ")}{t.earningsSource}
            </div>
          ) : null}
        </div>
      </div>

      <hr className="rule" style={{ margin: "18px 0 14px" }} />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 300px", gap: 26, alignItems: "end" }}>
        <div>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            {bi("60 个交易日收盘价 · 5 日均线 · 支撑阻力", "60-session closes · 5-day MA · support/resistance")}
          </div>
          <Spark bars={t.bars} sma5={t.sma5} sma20={t.sma20}
            support={t.support} resistance={t.resistance} spot={t.spot}
            height={78} showAxis />
        </div>
        <div>
          <div className="eyebrow" style={{ marginBottom: 8 }}>{bi("价格地图 · price_map", "Price map")}</div>
          <table style={{ width: "100%", fontSize: 11.5, borderCollapse: "collapse" }}>
            <tbody>
              {([
                ["resistance", t.resistance, bi("阻力", "resistance")],
                ["target", t.target, bi("目标", "target")],
                ["invalid_below", t.invalidBelow, bi("观点失效位", "invalid below")],
                ["support", t.support, bi("支撑", "support")],
              ] as const).map(([k, v, label]) => (
                <tr key={k}>
                  <td className="mono" style={{ padding: "3px 0", color: "var(--ink-4)", fontSize: 10 }}>{k}</td>
                  <td style={{ padding: "3px 0", color: "var(--ink-3)" }}>{label}</td>
                  <td className="mono" style={{ padding: "3px 0", textAlign: "right" }}>
                    {v == null ? <Absent state="missing" /> : fmtNum(v)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
