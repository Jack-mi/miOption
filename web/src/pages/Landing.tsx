/* 首页 · 产品介绍。点左上角 miOption 标识回来。 */
import { useState } from "react";
import { bi } from "../i18n";
import { FieldBadge } from "../components/ui";

const PIPELINE = [
  { n: "01", k: "data", t: "数据层", d: "报价、复权日线、技术、资金、财务、新闻、期权链。每个字段带 source / as_of / status。" },
  { n: "02", k: "signals", t: "三份信号", d: "走势是规则；研究与价值在密钥可用时调模型。弃权票不投票。" },
  { n: "03", k: "synth", t: "确定性合成", d: "纯代码，无 LLM。对齐、弃权、上浮、单源折扣全部可复算。" },
  { n: "04", k: "options", t: "期权结构", d: "27 个结构按合成方向筛选，只引用链上真实到期日与行权价。" },
  { n: "05", k: "risk", t: "风控闸", d: "逐腿查 OI 与价差，整体查敞口与财报窗口。算术，不是模型。" },
  { n: "06", k: "report", t: "中文简报", d: "先写数据状态，再写合成结论。不下单。" },
];

const FEATURES = [
  { t: "数据可信度是一等公民",
    d: "每个字段挂四态与来源。missing 用斜纹占位，绝不放 0；unsupported 与 missing 语气不同，不共用一个灰。",
    k: "FieldMeta" },
  { t: "分歧会拦住结论，不会被抹平",
    d: "双引擎方向异号判 conflicted，风控直接阻断；缺关键行情判 insufficient_data，结论必须写「信号不足」。",
    k: "agreement" },
  { t: "模型的影响力止于信号",
    d: "合成、筛结构、过风控、算盈亏比全部是确定性代码。LLM 只负责写说明，不碰数字。",
    k: "risk/limits.py" },
  { t: "结构只引用真实合约",
    d: "链上凑不出的腿就不生成。宁可给「做不了」的理由，也不拿空列表冒充没有机会。",
    k: "ChainSnapshot" },
];

export function Landing({ onEnter }: { onEnter: (screen: string) => void }) {
  const [hover, setHover] = useState<number | null>(null);
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-grain" aria-hidden="true" />
        <div className="hero-inner">
          <div className="hero-eyebrow">US EQUITY OPTIONS · DECISION SUPPORT</div>
          <h1 className="hero-title">
            {bi("把一只美股", "Read one US stock")}
            <br />
            {bi("读成一份", "into a ")}<span className="hero-accent">{bi("可复核", "reviewable")}</span>{bi("的结论", " conclusion")}
          </h1>
          <p className="hero-lede">
            {bi("输入标的，跑完取数 → 三份信号 → 确定性合成 → 27 个结构过风控 → 中文简报。每一段的来源、时点与失败状态都留在页面上，任何一步都能倒回去看它为什么这么判。",
              "Enter a ticker and run the full chain: fetch, three signals, deterministic ensemble, 27 structures through risk, a Chinese report. Every stage keeps its source, timestamp and failure state on the page.")}
          </p>
          <div className="hero-acts">
            <button className="hero-cta" onClick={() => onEnter("main")}>
              {bi("打开投研决策台", "Open the research console")}
            </button>
            <button className="hero-cta ghost" onClick={() => onEnter("watch")}>
              {bi("先看观察清单", "See the watchlist first")}
            </button>
          </div>
          <div className="hero-meta">
            <span>{bi("只读", "Read-only")}</span>
            <span className="dot" />
            <span>{bi("不下单", "No orders")}</span>
            <span className="dot" />
            <span>{bi("模型 deepseek-flash", "Model deepseek-flash")}</span>
          </div>
        </div>
      </section>

      <section className="land-section">
        <div className="land-head">
          <div className="eyebrow">{bi("一条链路 · 六个环节", "One pipeline · six stages")}</div>
          <h2>{bi("顺序固定，不能调换，也不能跳过", "Fixed order — no reordering, no skipping")}</h2>
        </div>
        <ol className="pipeline">
          {PIPELINE.map((p, i) => (
            <li className="pipe-item" key={p.k}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}
              data-on={hover === i ? "1" : undefined}>
              <div className="pipe-n mono">{p.n}</div>
              <div className="pipe-t">{bi(p.t, p.t)}</div>
              <div className="pipe-d">{bi(p.d, p.d)}</div>
              <div className="pipe-k mono">{p.k}</div>
            </li>
          ))}
        </ol>
      </section>

      <section className="land-section">
        <div className="land-head">
          <div className="eyebrow">{bi("四个不妥协的地方", "Four non-negotiables")}</div>
          <h2>{bi("数据质量不能被误判为成功", "Data quality is never mistaken for success")}</h2>
        </div>
        <div className="feat-grid">
          {FEATURES.map((f) => (
            <article className="feat" key={f.t}>
              <div className="feat-k mono">{f.k}</div>
              <h3>{bi(f.t, f.t)}</h3>
              <p>{bi(f.d, f.d)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="land-section">
        <div className="land-split">
          <div>
            <div className="eyebrow">{bi("四种状态 · 语气必须不同", "Four states · distinct tones")}</div>
            <h2>{bi("「没取到」和「不支持」不是一回事", "Missing and unsupported are not the same")}</h2>
            <p style={{ color: "var(--ink-2)", maxWidth: "46ch" }}>
              {bi("缺失是「该取没取到」，本轮不接入是「这个字段还没做」。两者混成一个灰，读报告的人就没法判断该不该等数据。",
                "Missing means it should have been fetched but wasn't; unsupported means the field doesn't exist yet. Merge them into one grey and the reader can't tell whether to wait for data.")}
            </p>
          </div>
          <div className="state-demo">
            {([
              ["available", "可用", "正常显示数值与实际内容"],
              ["missing", "缺失", "斜纹占位，绝不显示 0"],
              ["stale", "过期", "超过时效，不当作可用"],
              ["unsupported", "不支持", "本轮未接入，虚线紫边框"],
            ] as const).map(([s, t, d]) => (
              <div className="state-row" key={s}>
                <FieldBadge state={s} />
                <span className="state-t">{bi(t, t)}</span>
                <span className="state-d">{bi(d, d)}</span>
              </div>
            ))}
            <div className="state-row" style={{ borderTop: "var(--hair) solid var(--rule)", marginTop: 6, paddingTop: 12 }}>
              <span className="badge" data-tone="neg" data-stop="1">
                <span className="badge-stop-glyph">■</span>{bi("方向分歧", "Conflicted")}
              </span>
              <span className="state-t">conflicted</span>
              <span className="state-d">{bi("双引擎方向异号 → 风控直接阻断", "opposite signs → risk vetoes directly")}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="land-cta">
        <h2>{bi("先看一个跑完的标的", "Start with a finished run")}</h2>
        <p>{bi("打开投研决策台，看一只标的从取数到简报的完整链路。", "Open the research console and follow one underlying from fetch to report.")}</p>
        <button className="hero-cta" onClick={() => onEnter("main")}>
          {bi("进入投研决策台", "Enter the research console")}
        </button>
      </section>

      <footer className="land-foot">
        <span className="mono">miOption</span>
        <span className="mono">© 2026 miOption</span>
      </footer>
    </div>
  );
}
