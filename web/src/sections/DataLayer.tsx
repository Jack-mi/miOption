/* 01 数据层：18 字段网格 + 惰性字段详情 + 数据源编辑器 */
import { useState } from "react";
import { bi } from "../i18n";
import { FieldBadge, Section } from "../components/ui";
import { Boundary } from "../components/Boundary";
import { FieldInspector } from "./FieldInspector";
import { DataEditor } from "./DataEditor";
import type { Workbench } from "../lib/api";

export function DataLayer({ t, onOpenLedger }: { t: Workbench; onOpenLedger: () => void }) {
  const counts: Record<string, number> = { available: 0, missing: 0, unsupported: 0, stale: 0, unknown: 0 };
  t.sources.forEach((s) => { counts[s.state] = (counts[s.state] || 0) + 1; });
  const order = ["available", "missing", "stale", "unsupported", "unknown"];
  const sorted = [...t.sources].sort((a, b) =>
    order.indexOf(a.state) - order.indexOf(b.state) || a.field.localeCompare(b.field));
  const noLedger = counts.unknown > 0;
  const [openId, setOpenId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const openField = openId ? sorted.find((s) => s.id === openId) : null;

  return (
    <Section
      id="s1" idx="01" title={bi("数据层", "Data layer")} sub={`FieldMeta · ${t.sources.length} 个字段`}
      meta={<>
        {bi("报价与日线是硬门禁；技术指标不单独否决", "Quote and daily bars are hard gates; technicals never veto on their own")}<br />
        <span className="mono">{t.asOf} · America/New_York</span>
      </>}
      right={
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {(["available", "missing", "unsupported", "stale"] as const).map((k) => counts[k] ? (
            <FieldBadge key={k} state={k} label={`${k === "available" ? bi("可用", "avail") : k === "missing" ? bi("缺失", "missing") : k === "unsupported" ? bi("不支持", "n/a") : bi("过期", "stale")} ${counts[k]}`} />
          ) : null)}
          <button className="btn" data-v={editing ? "primary" : undefined}
            onClick={() => setEditing((v) => !v)}>
            <span className="mono" style={{ fontSize: 11 }}>✎</span>
            {bi("修改数据源", "Edit data source")}
          </button>
        </div>
      }>

      {noLedger ? (
        <div className="caveat" style={{ marginBottom: 12, borderStyle: "solid",
          borderColor: "var(--warn)", background: "var(--warn-soft)" }}>
          <b>{bi("这只标的还没有台账", "No ledger for this underlying")}</b>
          <span>
            {bi(`台账里没有 ${t.ticker} 的运行记录，所以这些字段的状态是「无记录」，不是取数失败。「没有记录」和「取数失败」是两件事。`,
              `There is no run record for ${t.ticker} in the ledger, so these fields read "no record" — not a failed fetch. "No record" and "fetch failed" are different things.`)}
          </span>
        </div>
      ) : null}

      {editing ? <DataEditor t={t} onClose={() => setEditing(false)} /> : null}

      <div className="panel">
        <div style={{ padding: "11px var(--pad)", borderBottom: "var(--hair) solid var(--rule)",
          display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: "var(--ink-2)" }}>
            {bi("点任意字段看它自己的取值、来源与约束。",
              "Click any field for its own values, source and constraints.")}
          </span>
          <button className="btn" style={{ marginLeft: "auto" }} onClick={onOpenLedger}>
            {bi("全量台账与覆盖矩阵 →", "Full ledger & coverage matrix →")}
          </button>
        </div>
        <div className="fields">
          {sorted.map((s) => (
            <button className="field" key={s.id} data-state={s.state}
              data-open={openId === s.id ? "1" : undefined}
              onClick={() => setOpenId((v) => (v === s.id ? null : s.id))}
              style={{ textAlign: "left", width: "100%" }}>
              <span className="caret" data-open={openId === s.id ? "1" : undefined}
                style={{ marginRight: 6, opacity: .5 }}>▶</span>
              <span className="field-name">{s.field}</span>
              <FieldBadge state={s.state} />
              <span className="field-note" style={{ maxWidth: "56%" }}>
                {s.state === "available" ? s.preview : s.note}
              </span>
            </button>
          ))}
        </div>
        {openField ? (
          <div style={{ border: "var(--hair) solid var(--rule-strong)", borderTop: 0 }}>
            <Boundary>
              <FieldInspector s={openField} ticker={t.ticker} />
            </Boundary>
          </div>
        ) : null}
      </div>

      <div className="caveat" style={{ marginTop: 12 }}>
        <b>{bi("缺失的后果", "Effect of a gap")}</b>
        <span>
          <span className="mono">资金流 missing</span>
          {bi(" → 走势引擎少一分（资金面），只剩均线一条。",
            " → the trend engine loses one point (flow), leaving only the moving average.")}
          <span className="mono">报价 / 日线 missing</span>
          {bi(" → 该引擎整票弃权，不拿缺数票凑合成。",
            " → that engine abstains entirely; a vote is never padded with missing data.")}
        </span>
      </div>
    </Section>
  );
}
