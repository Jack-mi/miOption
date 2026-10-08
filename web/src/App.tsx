/* 应用外壳：顶栏导航 / 标的切换 / 账户菜单（含偏好设置）/ 证据抽屉 / 数据加载。 */
import { useCallback, useEffect, useState } from "react";
import i18n, { bi } from "./i18n";
import { api, SellerCard, StrategyNote, TickerInfo, WatchRow, Workbench, toWorkbench } from "./lib/api";
import { usePrefs } from "./lib/state";
import { HealthBar, ToneBadge } from "./components/ui";
import { Boundary } from "./components/Boundary";
import { Landing } from "./pages/Landing";
import { WatchPage } from "./pages/WatchPage";
import { WikiPage } from "./pages/WikiPage";
import { StageAxis, STAGES, TickerHeader } from "./sections/TickerHeader";
import { DataLayer } from "./sections/DataLayer";
import { SignalsSection } from "./sections/SignalsSection";
import { ChainMenuSection } from "./sections/ChainMenuSection";
import { ReportSection } from "./sections/ReportSection";
import { EvidenceDrawer } from "./drawer/EvidenceDrawer";

const VALID_SCREENS = ["home", "main", "watch", "wiki"];

export default function App() {
  const [prefs, setPref] = usePrefs();
  const screen = VALID_SCREENS.includes(prefs.screen) ? prefs.screen : "home";

  /* 语言切换：改 i18n 实例并整树重挂（key=lang），保证没有残留旧语言节点 */
  useEffect(() => {
    if (i18n.language !== prefs.lang) i18n.changeLanguage(prefs.lang);
  }, [prefs.lang]);

  /* 主题应用 */
  useEffect(() => {
    const el = document.documentElement;
    el.setAttribute("data-dir", prefs.direction);
    el.setAttribute("data-theme", prefs.theme);
    el.setAttribute("data-density", prefs.density);
    if (prefs.accent && prefs.accent !== "auto") el.setAttribute("data-accent", prefs.accent);
    else el.removeAttribute("data-accent");
  }, [prefs.direction, prefs.theme, prefs.density, prefs.accent]);

  /* ---------- 数据 ---------- */
  const [tickers, setTickers] = useState<TickerInfo[]>([]);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  useEffect(() => {
    api.tickers()
      .then((d) => setTickers(d.tickers))
      .catch((e) => setLoadErr(String(e && e.message || e)));
  }, []);

  const ticker = tickers.some((t) => t.ticker === prefs.ticker)
    ? prefs.ticker
    : (tickers.find((t) => t.hasLedger) || tickers[0] || { ticker: prefs.ticker }).ticker;

  const [wb, setWb] = useState<Workbench | null>(null);
  const [wbErr, setWbErr] = useState<string | null>(null);
  useEffect(() => {
    if (screen !== "main" || !ticker) return;
    let alive = true;
    setWb(null);
    setWbErr(null);
    api.console(ticker)
      .then((d) => { if (alive) setWb(toWorkbench(d)); })
      .catch((e) => { if (alive) setWbErr(String(e && e.message || e)); });
    return () => { alive = false; };
  }, [screen, ticker]);

  const [watchRows, setWatchRows] = useState<WatchRow[]>([]);
  const [cardsByTicker, setCardsByTicker] = useState<Record<string, SellerCard[]>>({});
  const [verdicts, setVerdicts] = useState<Record<string, string | null>>({});
  useEffect(() => {
    if (screen !== "watch") return;
    api.watchlist()
      .then((d) => {
        setWatchRows(d.rows);
        d.rows.forEach((r) => {
          api.cards(r.ticker).then((cd) => {
            setCardsByTicker((s) => ({ ...s, [r.ticker]: cd.cards }));
            setVerdicts((s) => {
              const next = { ...s };
              cd.cards.forEach((c) => { next[c.id] = c.verdict; });
              return next;
            });
          }).catch(() => undefined);
        });
      })
      .catch((e) => setLoadErr(String(e && e.message || e)));
  }, [screen]);

  const [strategies, setStrategies] = useState<StrategyNote[]>([]);
  useEffect(() => {
    if (screen !== "wiki") return;
    api.strategies().then((d) => setStrategies(d.strategies)).catch(() => undefined);
  }, [screen]);

  const onVerdict = useCallback((cardId: string, verdict: string | null) => {
    setVerdicts((s) => ({ ...s, [cardId]: verdict }));
    api.verdict(cardId, verdict).catch((e) => {
      console.error("[miOption] verdict failed:", e);
    });
  }, []);

  /* ---------- 导航与抽屉 ---------- */
  const setScreen = (v: string) => { setPref("screen", v); try { window.scrollTo({ top: 0 }); } catch { /* noop */ } };
  const openEvidence = (tab: string) => { setPref("drawer", true); setPref("drawerTab", tab || "cov"); };
  const openTicker = (tk: string) => { setPref("ticker", tk); setScreen("main"); };

  /* 下拉共用一个开关：同时只开一个 */
  const [menu, setMenu] = useState<string | null>(null);
  useEffect(() => {
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, []);

  /* 阶段轴滚动高亮（requestAnimationFrame 节流；不用 scrollIntoView） */
  const [activeStage, setActiveStage] = useState("s0");
  const [menuFilter, setMenuFilter] = useState("all");
  useEffect(() => {
    if (screen !== "main") return undefined;
    let raf: number | null = null;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = null;
        const off = 140;
        let cur = STAGES[0].id;
        STAGES.forEach((s) => {
          const el = document.getElementById(s.id);
          if (el && el.getBoundingClientRect().top <= off) cur = s.id;
        });
        setActiveStage(cur);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [screen, ticker]);

  const goStage = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    const y = el.getBoundingClientRect().top + window.scrollY - 104;
    window.scrollTo({ top: Math.max(0, y) });
  };

  const navLabel = screen === "home" ? bi("首页", "Home") : null;
  const NAV = [
    { key: "main", label: bi("投研决策台", "Research Console") },
    { key: "watch", label: bi("观察清单", "Watchlist") },
    { key: "wiki", label: bi("策略百科库", "Strategy Library") },
  ];

  return (
    <Boundary key={prefs.lang}>
      <header className="topbar">
        <button className="brand" onClick={() => setScreen("home")} title={bi("回首页", "Home")}>
          <span className="brand-mark">miOption</span>
        </button>

        <nav className="nav" aria-label="主导航">
          {navLabel ? (
            <button className="nav-item" aria-current="page">{navLabel}</button>
          ) : null}
          {NAV.map((s) => (
            <button className="nav-item" key={s.key}
              aria-current={screen === s.key ? "page" : undefined}
              onClick={() => setScreen(s.key)}>
              {s.label}
            </button>
          ))}
        </nav>

        <div className="topbar-right">
          <button className="btn" style={{ padding: "4px 10px" }} onClick={() => openEvidence(prefs.drawerTab)}
            title={bi("证据", "Evidence")}>
            <span className="mono" style={{ fontSize: 11 }}>⌗</span> {bi("证据", "Evidence")}
          </button>

          {screen === "main" ? (
            <div className="acct" onClick={(e) => e.stopPropagation()}>
              <button className="tk-btn" onClick={() => setMenu(menu === "tk" ? null : "tk")}
                aria-expanded={menu === "tk"}>
                <span className="session-dot" data-open="1" />
                <span className="mono">{ticker}</span>
                <span className="mono" style={{ color: "var(--ink-4)", fontSize: 9 }}>▾</span>
              </button>
              {menu === "tk" ? (
                <TickerMenu list={tickers} cur={ticker}
                  onPick={(tk) => { openTicker(tk); setMenu(null); }} />
              ) : null}
            </div>
          ) : null}

          <div className="acct" onClick={(e) => e.stopPropagation()}>
            <button className="acct-btn" onClick={() => setMenu(menu === "acct" ? null : "acct")}
              aria-expanded={menu === "acct"} title={bi("我的", "Account")}>
              <span className="acct-av">{bi("粟", "S")}</span>
              <span style={{ fontSize: 12 }}>{bi("我的", "Account")}</span>
              <span className="mono" style={{ color: "var(--ink-4)", fontSize: 9 }}>▾</span>
            </button>
            {menu === "acct" ? (
              <AccountMenu prefs={prefs} setPref={setPref}
                onGo={(k) => {
                  setMenu(null);
                  if (k === "watch") setScreen("watch");
                  else if (k === "ledger") openEvidence("risk");
                  else openEvidence("cov");
                }} />
            ) : null}
          </div>
        </div>
      </header>

      {loadErr ? (
        <div className="page" style={{ paddingTop: 20 }}>
          <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}>
            <b>{bi("后端连不上", "API unavailable")}</b>
            <span className="mono" style={{ fontSize: 10.5 }}>
              {loadErr} — {bi("请先启动 api：.venv-sc/bin/python -m uvicorn api.main:app --port 8000",
                "start the api first: .venv-sc/bin/python -m uvicorn api.main:app --port 8000")}
            </span>
          </div>
        </div>
      ) : null}

      {screen === "home" ? <Landing onEnter={setScreen} /> : null}

      {screen === "main" && wb ? (
        <HealthBar sources={wb.sources} chain={wb.chain} account={wb.risk.account_equity}
          asOf={wb.asOf} onOpenLedger={() => openEvidence("cov")} />
      ) : null}

      {screen === "main" ? (
        wbErr ? (
          <div className="page" style={{ paddingTop: 20 }}>
            <div className="caveat" style={{ borderStyle: "solid", borderColor: "var(--neg)" }}>
              <b>{bi("决策台数据取不到", "Console data unavailable")}</b>
              <span className="mono" style={{ fontSize: 10.5 }}>{wbErr}</span>
            </div>
          </div>
        ) : !wb ? (
          <div className="page" style={{ paddingTop: 40, color: "var(--ink-4)", fontSize: 12 }}>…</div>
        ) : (
          <div className="page page-wide" key={ticker}>
            <div className="workbench">
              <StageAxis active={activeStage} onGo={goStage} />
              <div style={{ minWidth: 0 }}>
                <span id="s0" />
                <Boundary><TickerHeader t={wb} /></Boundary>
                <Boundary><DataLayer t={wb} onOpenLedger={() => openEvidence("cov")} /></Boundary>
                <Boundary><SignalsSection t={wb} /></Boundary>
                <Boundary><ChainMenuSection t={wb} menuFilter={menuFilter} setMenuFilter={setMenuFilter} /></Boundary>
                <Boundary><ReportSection t={wb} /></Boundary>
              </div>
            </div>
          </div>
        )
      ) : null}

      {screen === "watch" ? (
        <WatchPage rows={watchRows} cardsByTicker={cardsByTicker}
          verdicts={verdicts} onVerdict={onVerdict}
          onOpenEvidence={openEvidence} onOpenWorkbench={openTicker} />
      ) : null}
      {screen === "wiki" ? <WikiPage items={strategies} /> : null}

      <EvidenceDrawer open={!!prefs.drawer} tab={prefs.drawerTab}
        onTab={(v) => setPref("drawerTab", v)}
        onClose={() => setPref("drawer", false)}
        tickers={tickers} focusTicker={ticker} />
    </Boundary>
  );
}

/* ---------- 标的切换下拉 ---------- */
function TickerMenu({ list, cur, onPick }: {
  list: TickerInfo[]; cur: string; onPick: (t: string) => void;
}) {
  return (
    <div className="menu-pop tk-menu">
      <div className="menu-head">
        <b>{bi("选择标的", "Select underlying")}</b>
        <span>{bi("不同标的结论不同", "conclusions differ per ticker")}</span>
      </div>
      {list.map((w) => {
        const ok = w.badge === "信号可用" || w.badge === "单源";
        return (
          <button className="tk-row" key={w.ticker} data-cur={w.ticker === cur ? "1" : undefined}
            onClick={() => onPick(w.ticker)}>
            <span className="mono" style={{ fontWeight: 500 }}>{w.ticker}</span>
            <span style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{w.hasLedger ? "" : bi("无台账", "no ledger")}</span>
            {w.badge === "报价缺失" ? (
              <span className="hatch" style={{ fontSize: 10 }}>{bi("报价缺失", "no quote")}</span>
            ) : (
              <ToneBadge tone={ok ? "pos" : "neg"} stop={!ok}>{bi(w.badge, w.badge)}</ToneBadge>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ---------- 账户菜单（含偏好设置） ---------- */
function AccountMenu({ prefs, setPref, onGo }: {
  prefs: ReturnType<typeof usePrefs>[0];
  setPref: ReturnType<typeof usePrefs>[1];
  onGo: (k: string) => void;
}) {
  return (
    <div className="menu-pop">
      <div className="menu-head">
        <b>{bi("小粟", "Researcher")}</b>
        <span>@research · {bi("自用 · 单机部署", "personal · single-node")}</span>
      </div>
      <button className="menu-item-btn" onClick={() => onGo("profile")}>
        {bi("个人资料", "Profile")}<span className="mono">account</span>
      </button>
      <button className="menu-item-btn" onClick={() => onGo("watch")}>
        {bi("我的观察清单", "My watchlist")}<span className="mono">watch</span>
      </button>
      <button className="menu-item-btn" onClick={() => onGo("ledger")}>
        {bi("风险闸参数", "Risk gate config")}<span className="mono">config</span>
      </button>
      <div style={{ borderTop: "var(--hair) solid var(--rule)", margin: "6px 0", paddingTop: 8 }}>
        <div className="eyebrow" style={{ padding: "0 12px 6px" }}>{bi("偏好设置", "Preferences")}</div>
        <PrefRow label={bi("语言", "Language")} value={prefs.lang}
          options={[["zh", "中文"], ["en", "English"]]} onChange={(v) => setPref("lang", v)} />
        <PrefRow label={bi("方向", "Direction")} value={prefs.direction}
          options={[["paper", "A 纸本"], ["desk", "B 内部台"], ["hunt", "C 猎场"]]} onChange={(v) => setPref("direction", v)} />
        <PrefRow label={bi("明暗", "Theme")} value={prefs.theme}
          options={[["light", bi("浅色", "Light")], ["dark", bi("深色", "Dark")]]} onChange={(v) => setPref("theme", v)} />
        <PrefRow label={bi("强调色", "Accent")} value={prefs.accent}
          options={[["auto", bi("跟随方向", "Auto")], ["clay", bi("绛红", "Clay")], ["indigo", bi("群青", "Indigo")],
            ["amber", bi("琥珀", "Amber")], ["teal", bi("松绿", "Teal")]]} onChange={(v) => setPref("accent", v)} />
        <PrefRow label={bi("密度", "Density")} value={prefs.density}
          options={[["compact", bi("紧凑", "Compact")], ["regular", bi("常规", "Regular")], ["airy", bi("舒展", "Airy")]]}
          onChange={(v) => setPref("density", v)} />
      </div>
      <button className="menu-item-btn" onClick={() => onGo("about")}>
        {bi("关于与限制", "About & limits")}<span className="mono">{bi("只读", "read-only")}</span>
      </button>
      <button className="menu-item-btn" onClick={() => onGo("signout")}>
        {bi("退出登录", "Sign out")}
      </button>
    </div>
  );
}

function PrefRow({ label, value, options, onChange }: {
  label: string; value: string; options: [string, string][]; onChange: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 12px" }}>
      <span style={{ fontSize: 11, color: "var(--ink-3)", minWidth: 44 }}>{label}</span>
      <div className="seg seg-lite">
        {options.map(([v, l]) => (
          <button key={v} aria-pressed={value === v}
            onClick={(e) => { e.stopPropagation(); onChange(v); }}>{l}</button>
        ))}
      </div>
    </div>
  );
}
