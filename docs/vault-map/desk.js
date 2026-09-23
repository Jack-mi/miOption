(() => {
  const params = new URLSearchParams(location.search);
  const NAMES = {
    bull_put_spread: "Bull Put Spread",
    bear_call_spread: "Bear Call Spread",
  };
  const ALIASES = {
    nvidia: "US.NVDA",
    nvda: "US.NVDA",
    spy: "US.SPY",
    qqq: "US.QQQ",
    aapl: "US.AAPL",
    apple: "US.AAPL",
    tsla: "US.TSLA",
    tesla: "US.TSLA",
    amd: "US.AMD",
    meta: "US.META",
    facebook: "US.META",
    bidu: "US.BIDU",
    baidu: "US.BIDU",
    百度: "US.BIDU",
  };
  const VERDICTS = [
    ["adopt", "采纳"],
    ["watch", "观察"],
    ["reject", "拒绝"],
  ];

  const root = document.querySelector("#desk");
  if (!root) return;

  const statusEl = root.querySelector(".desk-status");
  const listEl = root.querySelector(".desk-cards");
  const eventsEl = root.querySelector(".desk-event-list");
  const form = root.querySelector(".desk-form");
  const input = root.querySelector('input[name="underlyings"]');
  const filterBar = root.querySelector(".desk-filters");
  const buttons = root.querySelectorAll("[data-act]");

  let apiBase = null;
  let busy = false;
  let cards = [];
  let events = [];
  let filter = "all";
  let snapshot = {};

  function setStatus(text, state) {
    statusEl.textContent = text;
    statusEl.dataset.state = state || "";
  }

  function money(n) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    return Number(n).toFixed(2);
  }

  function resolveSymbol(raw) {
    const text = String(raw || "").trim();
    if (!text) return "";
    const key = text.toLowerCase().replace(/\s+/g, "");
    if (ALIASES[key]) return ALIASES[key];
    const compact = text.replace(/\s+/g, "").toUpperCase();
    if (compact.includes(".")) {
      const [market, ticker] = compact.split(".", 2);
      if (market && ticker) return `${market}.${ticker}`;
    }
    if (/^[A-Z0-9]+$/.test(compact)) return `US.${compact}`;
    return compact;
  }

  function resolveQuery(raw) {
    return String(raw || "")
      .split(/[,;\s]+/)
      .map(resolveSymbol)
      .filter(Boolean)
      .filter((code, i, all) => all.indexOf(code) === i);
  }

  function wantedCodes() {
    const raw = input.value.trim();
    if (!raw) return null;
    const codes = resolveQuery(raw);
    return codes.length ? codes : null;
  }

  function displayName(code) {
    const c = String(code || "");
    return c.startsWith("US.") ? c.slice(3) : c;
  }

  async function request(path, options = {}) {
    if (apiBase == null) throw new Error("no api");
    const res = await fetch(`${apiBase}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
    const text = await res.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { message: text };
      }
    }
    if (!res.ok) {
      throw new Error((data && (data.error || data.message)) || res.statusText);
    }
    return data;
  }

  async function resolveBase() {
    const override = (params.get("api") || localStorage.getItem("mioption.sellerApi") || "").replace(/\/$/, "");
    const candidates = [];
    if (override) candidates.push(override);
    if (location.protocol !== "file:") candidates.push("");
    candidates.push(location.origin);
    for (const base of candidates) {
      try {
        const res = await fetch(`${base}/api/health`, { headers: { Accept: "application/json" } });
        if (!res.ok) continue;
        const data = await res.json();
        if (data && data.service === "mioption-h5") return base;
      } catch {
        /* try next */
      }
    }
    return null;
  }

  function markLabel(card) {
    if (card.verdict === "adopt") return "采纳";
    if (card.verdict === "watch") return "观察";
    if (card.verdict === "reject") return "拒绝";
    return card.status || "signal";
  }

  function visible(card) {
    const wanted = wantedCodes();
    if (wanted && !wanted.includes(String(card.underlying || "").toUpperCase())) return false;
    if (filter === "all") return true;
    if (filter === "tracked") return card.status === "tracked" || card.verdict === "adopt";
    if (filter === "signal") return card.status === "signal";
    if (filter === "settled") return card.status === "settled";
    return card.structure_id === filter;
  }

  function renderCards() {
    listEl.replaceChildren();
    const shown = cards.filter(visible);
    if (!shown.length) {
      const empty = document.createElement("p");
      empty.className = "desk-empty";
      empty.textContent = wantedCodes()
        ? "当前搜索没有匹配卡片。点「扫描」只扫输入的标的。"
        : cards.length
          ? "当前筛选没有卡片。"
          : "还没有卡片。输入 nvidia 后点「扫描」。";
      listEl.appendChild(empty);
      return;
    }
    for (const card of shown) {
      const row = document.createElement("article");
      row.className = "desk-card";
      row.dataset.structure = card.structure_id;
      row.dataset.status = card.status || "";
      row.dataset.underlying = card.underlying || "";
      const head = document.createElement("div");
      head.className = "desk-card-head";
      const name = document.createElement("p");
      name.className = "desk-card-name";
      name.textContent = `${displayName(card.underlying)} · ${NAMES[card.structure_id] || card.structure_id}`;
      const meta = document.createElement("div");
      meta.className = "desk-card-meta";
      const kind = document.createElement("span");
      kind.className = "mark";
      kind.dataset.pl = "num";
      kind.textContent = markLabel(card);
      meta.appendChild(kind);
      const actions = document.createElement("div");
      actions.className = "desk-verdicts";
      for (const [value, label] of VERDICTS) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = label;
        btn.disabled = busy;
        btn.setAttribute("aria-pressed", card.verdict === value ? "true" : "false");
        btn.addEventListener("click", () => {
          if (card.verdict === value) verdict(card.id, "clear");
          else verdict(card.id, value);
        });
        actions.appendChild(btn);
      }
      meta.appendChild(actions);
      head.append(name, meta);
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "盈亏细节";
      const body = document.createElement("div");
      body.className = "desk-card-body";
      const intro = document.createElement("p");
      intro.textContent = `${card.underlying} · 卖 ${card.short.strike} ${money(card.short.bid)}/${money(card.short.ask)} · 买 ${card.long.strike} ${money(card.long.bid)}/${money(card.long.ask)} · ${card.expiry} · DTE ${card.dte} · 保守权利金 ${money(card.credit)}`;
      const wiki = document.createElement("p");
      const link = document.createElement("a");
      link.href = `/api/wiki/page?path=${encodeURIComponent(card.wiki_path)}`;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = `笔记 ${card.wiki_path}`;
      wiki.appendChild(link);
      const dl = document.createElement("dl");
      dl.className = "desk-metrics";
      const metrics = [
        ["权利金", money(card.credit)],
        ["最多赚", money(card.max_profit)],
        ["最多亏", money(card.max_loss)],
        ["打平", money(card.breakeven)],
        ["标记盈亏", money(card.mark_pnl)],
      ];
      for (const [label, value] of metrics) {
        const wrap = document.createElement("div");
        const dt = document.createElement("dt");
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.textContent = value;
        if (label === "最多赚") dd.className = "up";
        if (label === "最多亏") dd.className = "down";
        if (label === "标记盈亏") {
          const n = Number(card.mark_pnl);
          if (n > 0) dd.className = "up";
          if (n < 0) dd.className = "down";
        }
        wrap.append(dt, dd);
        dl.appendChild(wrap);
      }
      const note = document.createElement("p");
      note.className = "meta";
      note.textContent = `来源 ${card.quote_source || "unknown"} · ${card.quoted_at || "时间未知"} · 裁决只记本地档案，不会下单。`;
      body.append(intro, wiki, dl, note);
      details.append(summary, body);
      row.append(head, details);
      listEl.appendChild(row);
    }
  }

  function renderEvents() {
    eventsEl.replaceChildren();
    const wanted = wantedCodes();
    const latest = events
      .filter((ev) => !wanted || wanted.some((code) => String(ev.card_id || "").startsWith(code)))
      .slice(-12)
      .reverse();
    if (!latest.length) {
      const li = document.createElement("li");
      li.textContent = "还没有保护 / 止盈 / 结算事件。";
      eventsEl.appendChild(li);
      return;
    }
    for (const ev of latest) {
      const li = document.createElement("li");
      const kind = ev.kind || "event";
      const id = ev.card_id || "";
      li.textContent = `${kind} · ${id}${ev.place_order ? " · 试图下单（本页不会）" : " · 仅提醒"}`;
      eventsEl.appendChild(li);
    }
  }

  function sourceLabel(data) {
    if (data.quote_source === "futu") return "OpenD 行情快照";
    if (data.quote_source === "mock") return "模拟行情（非真实价格）";
    return `来源 ${data.quote_source || "unknown"}（请检查卡片时间）`;
  }

  function applySnapshot(data) {
    snapshot = data;
    cards = data.cards || [];
    events = data.events || [];
    const q = wantedCodes();
    const extra = q ? ` · ${q.join(", ")}` : "";
    setStatus(`${sourceLabel(data)} · ${cards.filter(visible).length} 张卡${extra} · 本页不下单`, data.mock ? "down" : "up");
    renderCards();
    renderEvents();
  }

  function listPath() {
    const q = input.value.trim();
    return q ? `/api/seller?q=${encodeURIComponent(q)}` : "/api/seller";
  }

  async function refresh() {
    const data = await request(listPath());
    applySnapshot(data);
  }

  async function withBusy(fn) {
    if (busy) return;
    busy = true;
    buttons.forEach((el) => {
      el.disabled = true;
    });
    try {
      await fn();
    } catch (err) {
      setStatus(`失败：${err.message}`, "down");
    } finally {
      busy = false;
      buttons.forEach((el) => {
        el.disabled = false;
      });
      renderCards();
    }
  }

  async function scan() {
    await withBusy(async () => {
      const names = input.value.trim();
      if (!names) {
        setStatus("先输入标的，例如 nvidia", "down");
        return;
      }
      const data = await request("/api/seller/scan", {
        method: "POST",
        body: JSON.stringify({ underlyings: names }),
      });
      if (data.watchlist && data.watchlist.some((code) => !resolveQuery(names).includes(code))) {
        throw new Error("scan returned extra symbols");
      }
      await refresh();
      if (data.errors && Object.keys(data.errors).length) {
        setStatus(`扫描部分失败：${JSON.stringify(data.errors)}`, "down");
      }
    });
  }

  async function monitor() {
    await withBusy(async () => {
      const data = await request("/api/seller/monitor", { method: "POST", body: "{}" });
      if (data.place_order) throw new Error("monitor claimed it would place an order");
      await refresh();
      if (data.errors && Object.keys(data.errors).length) {
        setStatus(`跟踪部分失败：${JSON.stringify(data.errors)}`, "down");
      }
    });
  }

  async function verdict(cardId, value) {
    await withBusy(async () => {
      await request("/api/seller/verdict", {
        method: "POST",
        body: JSON.stringify({ card_id: cardId, verdict: value }),
      });
      await refresh();
    });
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    scan();
  });

  input.addEventListener("input", () => {
    renderCards();
    renderEvents();
    if (statusEl.dataset.state === "up") {
      const src = sourceLabel(snapshot);
      const q = wantedCodes();
      const extra = q ? ` · ${q.join(", ")}` : "";
      setStatus(`${src} · ${cards.filter(visible).length} 张卡${extra} · 本页不下单`, "up");
    }
  });

  root.querySelector('[data-act="refresh"]').addEventListener("click", () => withBusy(refresh));
  root.querySelector('[data-act="monitor"]').addEventListener("click", monitor);

  filterBar.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-filter]");
    if (!btn) return;
    filter = btn.dataset.filter;
    filterBar.querySelectorAll("button").forEach((el) => {
      el.setAttribute("aria-pressed", el === btn ? "true" : "false");
    });
    renderCards();
  });

  (async () => {
    apiBase = await resolveBase();
    if (apiBase == null) {
      setStatus("未连上本机研究台。在仓库运行：python runtime/scripts/serve_h5.py", "down");
      return;
    }
    try {
      await refresh();
    } catch (err) {
      setStatus(`已找到服务但读卡失败：${err.message}`, "down");
    }
  })();
})();
