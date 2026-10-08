/* 策略百科库：27 张策略笔记，引用层，不参与决策。 */
import { useMemo, useState } from "react";
import { bi } from "../i18n";
import { groupLabels, groupLabelsEn } from "../lib/labels";
import { ToneBadge } from "../components/ui";
import type { StrategyNote } from "../lib/api";

export function WikiPage({ items }: { items: StrategyNote[] }) {
  const [q, setQ] = useState("");
  const [g, setG] = useState("all");

  const groups = ["all", "bull", "bear", "neutral", "hedge"];
  const shown = useMemo(() => {
    const key = q.trim().toLowerCase();
    return items.filter((w) => (g === "all" || w.group === g) &&
      (!key || w.name.includes(key) || w.en.toLowerCase().includes(key) || w.file.toLowerCase().includes(key)));
  }, [items, q, g]);

  return (
    <div className="page page-wide">
      <div className="page-head">
        <div className="eyebrow">knowledge/wiki/strategies · {items.length} 张笔记</div>
        <h1 className="page-title">{bi("策略百科库", "Strategy Library")}</h1>
      </div>

      <div className="panel panel-pad" style={{ marginBottom: "var(--gap)" }}>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
          <div className="search">
            <span className="mono" style={{ color: "var(--ink-4)", fontSize: 11 }}>⌕</span>
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder={bi("搜索中文名 / 英文名 / 文件名", "Search Chinese / English / file name")}
              aria-label="搜索策略" />
          </div>
          <div className="seg seg-lite">
            {groups.map((k) => (
              <button key={k} aria-pressed={g === k} onClick={() => setG(k)}>
                {k === "all" ? `${bi("全部", "All")} ${items.length}` : bi(groupLabels[k], groupLabelsEn[k])}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", fontSize: 11, color: "var(--ink-3)" }}>
            {bi("显示", "Showing")} <b className="mono">{shown.length}</b> / {items.length} {bi("张笔记", "notes")}
          </div>
        </div>
      </div>

      <div className="wiki-grid">
        {shown.map((w) => (
          <article className="wiki-card" key={w.file}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <h4>{w.name}</h4>
              <ToneBadge tone={w.group === "bull" ? "pos" : w.group === "bear" ? "neg"
                : w.group === "hedge" ? "na" : "warn"}>
                {bi(groupLabels[w.group], groupLabelsEn[w.group])}
              </ToneBadge>
            </div>
            <div className="file">{w.en} · {w.file}</div>
            <p>{w.blurb}</p>
            <div className="wiki-meta">
              <ToneBadge tone="mute">{w.market}</ToneBadge>
              <ToneBadge tone="mute">{bi("风险", "risk")} {w.risk}</ToneBadge>
              <ToneBadge tone="mute">{w.greeks}</ToneBadge>
            </div>
          </article>
        ))}
      </div>
      {!shown.length ? (
        <div className="panel panel-pad" style={{ color: "var(--ink-3)" }}>
          {bi("没有匹配的笔记。", "No matching notes.")}
        </div>
      ) : null}
    </div>
  );
}
