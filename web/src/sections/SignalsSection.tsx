/* 02 信号与合成：对比条 + 三张引擎卡 + 合成块 */
import { bi } from "../i18n";
import { Section, Tract } from "../components/ui";
import { EngineCard } from "./EngineCard";
import { SynthBlock } from "./SynthBlock";
import type { Workbench } from "../lib/api";

const ORDER = ["trend", "research", "value"] as const;

export function SignalsSection({ t }: { t: Workbench }) {
  const rows = ORDER.map((k) => {
    const s = t.signals[k];
    return { key: k, engine: k, label: s.engineLabel, conviction: s.conviction, direction: s.direction, status: s.data_status };
  });
  return (
    <Section id="s2" idx="02" title={bi("信号与合成", "Signals & ensemble")} sub="trend · research · value → combine.py"
      meta={<>
        {bi("弃权票不投票；合成不改写这三份的方向", "Abstentions do not vote; the ensemble never rewrites the three signals")}<br />
        {bi("合成是确定性代码，无 LLM", "Ensemble is deterministic code, no LLM")}
      </>}>

      <div className="panel panel-pad" style={{ marginBottom: "var(--gap)" }}>
        <div className="eyebrow" style={{ marginBottom: 11 }}>
          {bi("信号强度对比 · conviction（−1 ~ +1）", "Signal strength · conviction (−1 ~ +1)")}
        </div>
        <Tract rows={rows} />
        <div className="caveat" style={{ marginTop: 14 }}>
          <b>{bi("注意", "Note")}</b>
          <span>
            {bi("走势只计两分：价格在 5 日均线之上/下、资金净额正/负，两项同向直接给 ±1。",
              "Trend scores two points only: price vs the 5-day MA and the sign of net flow; aligned inputs give ±1.")}
            {" "}
            {bi("若为 insufficient_data 则整票弃权，不得回退成有效票。",
              "insufficient_data means the whole vote abstains and never falls back to a valid vote.")}
          </span>
        </div>
      </div>

      <div className="grid g3">
        {ORDER.map((k) => <EngineCard key={k} s={t.signals[k]} />)}
      </div>

      <SynthBlock t={t} />
    </Section>
  );
}
