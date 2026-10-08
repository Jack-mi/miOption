/* 03 期权链与结构：链快照 + 结构菜单 */
import { bi } from "../i18n";
import { Section } from "../components/ui";
import { ChainSection } from "./ChainSection";
import { MenuBody } from "./MenuBody";
import type { Workbench } from "../lib/api";

export function ChainMenuSection({ t, menuFilter, setMenuFilter }: {
  t: Workbench; menuFilter: string; setMenuFilter: (v: string) => void;
}) {
  const menu = t.menu || [];
  const counts: Record<string, number> = { fit: 0, unfit: 0, impossible: 0 };
  menu.forEach((x) => { counts[x.status] = (counts[x.status] || 0) + 1; });

  return (
    <Section id="s3" idx="03" title={bi("期权链与结构", "Chain and structures")}
      sub="ChainSnapshot · render_menu()"
      meta={<>
        {bi("富途主源，失败降级 Cboe 延迟链", "Futu primary, falls back to the Cboe delayed chain")}<br />
        {bi("结构只能引用链上真实到期日 / 行权价 / 合约代码",
          "Structures may only cite real expiries / strikes / contract codes from the chain")}
      </>}>

      <ChainSection t={t} />

      <div className="panel panel-pad" style={{ marginTop: "var(--gap)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 14 }}>
          <span className="eyebrow" style={{ marginBottom: 0 }}>
            {bi("结构菜单 · 27 个结构", "Structure menu · 27 structures")}
          </span>
          <div className="seg seg-lite" style={{ marginLeft: "auto" }}>
            {([
              ["all", bi("全部", "All") + " " + menu.length],
              ["fit", bi("适合", "Fit") + " " + (counts.fit || 0)],
              ["unfit", bi("不适合", "Unfit") + " " + (counts.unfit || 0)],
              ["impossible", bi("做不了", "Impossible") + " " + (counts.impossible || 0)],
            ] as const).map(([k, l]) => (
              <button key={k} aria-pressed={menuFilter === k} onClick={() => setMenuFilter(k)}>{l}</button>
            ))}
          </div>
        </div>
        <MenuBody t={t} filter={menuFilter || "all"} />
      </div>
    </Section>
  );
}
