/* 04 中文简报：面板内嵌一张「纸」。
   正文是 api 按固定大纲用台账数据确定性生成的全中文简报（reportStructured）；
   原始 reporter 文件 reports/{date}/{ticker}.md 不改写，仅作留痕。 */
import ReactMarkdown from "react-markdown";
import { bi } from "../i18n";
import { Section, ToneBadge } from "../components/ui";
import type { Workbench } from "../lib/api";

export function ReportSection({ t }: { t: Workbench }) {
  return (
    <Section id="s4" idx="04" title={bi("中文简报", "Chinese report")}
      sub={t.report ? `reports/${t.report.date}/${t.ticker}.md` : bi("台账生成", "from ledger")}
      meta={<>
        {bi("按固定大纲由台账数据确定性生成", "generated deterministically from the ledger on a fixed outline")}<br />
        {bi("简报不改写三份信号的方向与缺失", "the report never rewrites signal direction or gaps")}
      </>}
      right={<ToneBadge tone="mute">{bi("确定性生成", "deterministic")}</ToneBadge>}>
      <div className="panel panel-pad">
        <div className="panel" style={{ padding: "32px 38px", background: "var(--bg)" }}>
          <article className="report">
            <div className="stamp">
              {bi("台账", "ledger")} / {t.asOf} / {t.ticker} &nbsp;·&nbsp; {bi("只读", "read-only")} &nbsp;·&nbsp; {bi("不下单", "no orders")}
            </div>
            <ReactMarkdown>{t.reportStructured}</ReactMarkdown>
          </article>
        </div>

        <div className="grid g2" style={{ marginTop: "var(--gap)" }}>
          <div className="caveat">
            <b>fallback</b>
            <span>
              {bi("reporter agent 失败时，落到确定性简报：仍写出走势、合成和结构菜单。不会因为没有模型就吞掉已经确定的部分。",
                "When the reporter agent fails, a deterministic report is written: trend, ensemble and the menu still ship. Deterministic parts are never swallowed by a missing model.")}
            </span>
          </div>
          <div className="caveat">
            <b>{bi("禁止改写", "No rewriting")}</b>
            <span>
              {bi("简报不得把 insufficient_data 写成方向结论，不得把单源行情写成双源互证，也不得把引擎报告里的指标写成行情事实。",
                "The report must not turn insufficient_data into a directional call, must not present single-source quotes as cross-verified, and must not present engine-reported indicators as market facts.")}
            </span>
          </div>
        </div>
      </div>
    </Section>
  );
}
