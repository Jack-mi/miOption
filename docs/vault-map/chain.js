(() => {
  const params = new URLSearchParams(location.search);
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

  const root = document.querySelector("#chain");
  if (!root) return;

  const statusEl = root.querySelector(".chain-status");
  const form = root.querySelector(".chain-form");
  const input = root.querySelector('input[name="q"]');
  const equityEl = root.querySelector(".chain-equity");
  const tabsEl = root.querySelector(".chain-tabs");
  const tableEl = root.querySelector(".chain-table-wrap");
  const drawer = document.querySelector(".chain-drawer");
  const drawerBody = drawer.querySelector(".chain-drawer-body");
  const buttons = root.querySelectorAll("[data-act]");

  let apiBase = null;
  let busy = false;
  let pack = null;
  let expiry = "";

  function setStatus(text, state) {
    statusEl.textContent = text;
    statusEl.dataset.state = state || "";
  }

  function pick(obj, keys) {
    if (!obj) return null;
    for (const key of keys) {
      const value = obj[key];
      if (value != null && value !== "") return value;
    }
    return null;
  }

  function num(value) {
    if (value == null || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function money(value, digits = 2) {
    const n = num(value);
    if (n == null) return "—";
    return n.toFixed(digits);
  }

  function compact(value) {
    const n = num(value);
    if (n == null) return "—";
    const abs = Math.abs(n);
    if (abs >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
    return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
  }

  function chgClass(value) {
    const n = num(value);
    if (n == null || n === 0) return "";
    return n > 0 ? "up" : "down";
  }

  function resolveSymbol(raw) {
    const text = String(raw || "").trim();
    if (!text) return "";
    const key = text.toLowerCase().replace(/\s+/g, "");
    if (ALIASES[key]) return ALIASES[key];
    if (ALIASES[text]) return ALIASES[text];
    const compactText = text.replace(/\s+/g, "").toUpperCase();
    if (compactText.includes(".")) {
      const [market, ticker] = compactText.split(".", 2);
      if (market && ticker) return `${market}.${ticker}`;
    }
    if (/^[A-Z0-9]+$/.test(compactText)) return `US.${compactText}`;
    return compactText;
  }

  function currentCode() {
    return resolveSymbol(input.value) || resolveSymbol(params.get("q")) || "";
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

  function sourceLabel(source) {
    if (source === "futu") return "OpenD 行情快照";
    if (source === "mock") return "模拟行情（非真实价格）";
    return String(source);
  }

  function shortDate(value) {
    const text = String(value || "");
    return text.length >= 10 ? text.slice(5, 10) : text;
  }

  function statusFromPack(data) {
    if (!data || data.empty) return ["未拉过该标的。输入代码后点「拉取」。", "down"];
    const cov = data.coverage || {};
    const expiries = data.expiries || [];
    const bits = [
      sourceLabel(data.source),
      data.pulled_at || "—",
      `${data.count || 0} 张`,
      `${expiries.length} 个到期`,
    ];
    if (cov.window_end) bits.push(`窗口至 ${shortDate(cov.window_end)}`);
    if (cov.listed_last) bits.push(`已上市至 ${shortDate(cov.listed_last)}`);
    const next = Array.isArray(cov.next_beyond) ? cov.next_beyond[0] : cov.next_beyond;
    if (next) bits.push(`下一档 ${shortDate(next)} 超出窗口`);
    if (!data.count) return [`${bits.join(" · ")} · 链为空`, "down"];
    if (data.stale) return [`${bits.join(" · ")} · 快照已过期，请重新拉取`, "down"];
    const greeks = (data.contracts || []).filter((c) => c.delta != null || c.iv != null).length;
    if (!greeks) return [`${bits.join(" · ")} · 无 Greeks / 可能无 OPRA`, "down"];
    return [bits.join(" · "), "up"];
  }

  function metric(label, value) {
    const wrap = document.createElement("div");
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    wrap.append(dt, dd);
    return wrap;
  }

  function kv(obj) {
    const dl = document.createElement("dl");
    dl.className = "chain-kv";
    const keys = Object.keys(obj || {}).sort();
    for (const key of keys) {
      const dt = document.createElement("dt");
      dt.textContent = key;
      const dd = document.createElement("dd");
      const value = obj[key];
      dd.textContent = value != null && typeof value === "object" ? JSON.stringify(value) : String(value);
      dl.append(dt, dd);
    }
    return dl;
  }

  function renderEquity(data) {
    equityEl.replaceChildren();
    if (!data || data.empty || !data.equity) {
      equityEl.hidden = true;
      return;
    }
    equityEl.hidden = false;
    const eq = data.equity;
    const last = pick(eq, ["last_price", "last"]);
    const change = pick(eq, ["change_val", "change_price", "change"]);
    const rate = pick(eq, ["change_rate"]);
    const head = document.createElement("div");
    head.className = "chain-equity-head";
    const name = document.createElement("strong");
    name.textContent = `${data.underlying}  ${pick(eq, ["name"]) || ""}`.trim();
    const lastEl = document.createElement("span");
    lastEl.className = "chain-last";
    lastEl.textContent = money(last);
    const chg = document.createElement("span");
    chg.className = `chain-chg ${chgClass(change)}`;
    const rateText = rate == null ? "" : `  ${Number(rate).toFixed(2)}%`;
    chg.textContent = `${change == null ? "—" : (Number(change) > 0 ? "+" : "") + money(change)}${rateText}`;
    head.append(name, lastEl, chg);

    const metrics = document.createElement("dl");
    metrics.className = "chain-metrics";
    metrics.append(
      metric("买一", money(pick(eq, ["bid_price", "bid"]))),
      metric("卖一", money(pick(eq, ["ask_price", "ask"]))),
      metric("量", compact(pick(eq, ["volume"]))),
      metric("额", compact(pick(eq, ["turnover"]))),
      metric("市值", compact(pick(eq, ["total_market_val", "market_val", "total_market_capitalization"]))),
      metric("PE", money(pick(eq, ["pe_ratio", "pe_ttm_ratio", "pe"]), 2)),
      metric("52周高", money(pick(eq, ["highest52weeks_price", "highest_52weeks_price", "high_price"]))),
      metric("52周低", money(pick(eq, ["lowest52weeks_price", "lowest_52weeks_price", "low_price"]))),
    );

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `全部字段 · ${Object.keys(eq).length}`;
    details.append(summary, kv(eq));
    equityEl.append(head, metrics, details);
  }

  function atmStrike(strikes, spot) {
    const last = num(spot);
    if (last == null || !strikes.length) return null;
    return strikes.reduce((best, row) => {
      const cur = Math.abs(row.strike - last);
      const prev = Math.abs(best.strike - last);
      return cur < prev ? row : best;
    }).strike;
  }

  function cell(contract, field, digits) {
    const td = document.createElement("td");
    if (!contract) {
      td.textContent = "—";
      return td;
    }
    td.dataset.code = contract.code;
    const value = contract[field];
    td.textContent = money(value, digits);
    if (field === "delta") {
      const n = num(value);
      if (n != null && n !== 0) td.className = n > 0 ? "num-up" : "num-down";
    }
    return td;
  }

  function renderTabs(data) {
    tabsEl.replaceChildren();
    const expiries = data && data.expiries ? data.expiries : [];
    if (!expiries.length) return;
    if (!expiries.includes(expiry)) expiry = expiries[0];
    for (const exp of expiries) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = exp.slice(5);
      btn.dataset.expiry = exp;
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", exp === expiry ? "true" : "false");
      btn.addEventListener("click", () => {
        expiry = exp;
        renderTable(pack);
        for (const other of tabsEl.querySelectorAll("button")) {
          other.setAttribute("aria-selected", other.dataset.expiry === expiry ? "true" : "false");
        }
      });
      tabsEl.append(btn);
    }
  }

  function renderTable(data) {
    tableEl.replaceChildren();
    if (!data || data.empty) {
      const p = document.createElement("p");
      p.className = "chain-empty";
      p.textContent = currentCode() ? "库里没有当前快照。点「拉取」从 OpenD 写入 SQLite。" : "指定标的后拉取或刷新。";
      tableEl.append(p);
      return;
    }
    if (!data.count) {
      const p = document.createElement("p");
      p.className = "chain-empty";
      p.textContent = "该窗口期权链为空。";
      tableEl.append(p);
      return;
    }
    const group = (data.chain || []).find((item) => item.expiry === expiry) || data.chain[0];
    if (!group) return;
    const spot = pick(data.equity || {}, ["last_price", "last"]);
    const atm = atmStrike(group.strikes, spot);
    const table = document.createElement("table");
    table.className = "chain-grid";
    table.innerHTML = `<thead><tr>
      <th>买</th><th>卖</th><th>最新</th><th>Δ</th><th>IV</th>
      <th class="strike">执行价</th>
      <th>买</th><th>卖</th><th>最新</th><th>Δ</th><th>IV</th>
    </tr></thead>`;
    const tbody = document.createElement("tbody");
    const callHead = document.createElement("tr");
    callHead.innerHTML = `<th colspan="5">CALL</th><th class="strike"></th><th colspan="5">PUT</th>`;
    tbody.append(callHead);
    for (const row of group.strikes) {
      const tr = document.createElement("tr");
      if (atm != null && row.strike === atm) tr.className = "atm";
      tr.append(
        cell(row.call, "bid", 2),
        cell(row.call, "ask", 2),
        cell(row.call, "last", 2),
        cell(row.call, "delta", 3),
        cell(row.call, "iv", 2),
      );
      const strike = document.createElement("td");
      strike.className = "strike";
      strike.textContent = money(row.strike, 2);
      tr.append(strike);
      tr.append(
        cell(row.put, "bid", 2),
        cell(row.put, "ask", 2),
        cell(row.put, "last", 2),
        cell(row.put, "delta", 3),
        cell(row.put, "iv", 2),
      );
      tbody.append(tr);
    }
    table.append(tbody);
    table.addEventListener("click", (event) => {
      const td = event.target.closest("td[data-code]");
      if (!td) return;
      openDrawer(td.dataset.code);
    });
    tableEl.append(table);
    requestAnimationFrame(() => {
      tableEl.querySelector("tr.atm")?.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
  }

  function closeDrawer() {
    drawer.hidden = true;
    document.body.classList.remove("chain-drawer-open");
  }

  async function openDrawer(code) {
    const q = currentCode();
    const fromPack = (pack && pack.contracts || []).find((c) => c.code === code) || {};
    drawer.hidden = false;
    document.body.classList.add("chain-drawer-open");
    drawerBody.replaceChildren();
    const title = document.createElement("p");
    title.textContent = code;
    drawerBody.append(title);
    try {
      const detail = await request(`/api/chain/contract?q=${encodeURIComponent(q)}&code=${encodeURIComponent(code)}`);
      renderDetail({ ...fromPack, ...detail });
    } catch (err) {
      renderDetail(fromPack);
      const p = document.createElement("p");
      p.textContent = err.message || String(err);
      drawerBody.append(p);
    }
  }

  function renderDetail(row) {
    drawerBody.replaceChildren();
    const head = document.createElement("p");
    head.textContent = `${row.code || ""}  ${row.option_type || ""}  ${row.expiry || ""}`;
    const greeks = document.createElement("dl");
    greeks.className = "chain-metrics";
    greeks.append(
      metric("Delta", money(row.delta, 4)),
      metric("Gamma", money(row.gamma, 4)),
      metric("Vega", money(row.vega, 4)),
      metric("Theta", money(row.theta, 4)),
      metric("Rho", money(row.rho, 4)),
      metric("IV", money(row.iv, 2)),
      metric("溢价", money(row.premium, 4)),
      metric("OI", compact(row.oi)),
      metric("DTE", money(row.dte, 0)),
      metric("买", money(row.bid)),
      metric("卖", money(row.ask)),
      metric("最新", money(row.last)),
      metric("买量", compact(row.bid_vol)),
      metric("卖量", compact(row.ask_vol)),
      metric("执行价", money(row.strike)),
    );
    drawerBody.append(head, greeks);
    if (row.extra && Object.keys(row.extra).length) {
      const h = document.createElement("h4");
      h.textContent = "其余字段";
      drawerBody.append(h, kv(row.extra));
    }
  }

  function render(data) {
    pack = data;
    const [text, state] = statusFromPack(data);
    setStatus(text, state);
    renderEquity(data);
    renderTabs(data);
    renderTable(data);
  }

  async function load() {
    const q = currentCode();
    if (!q) {
      pack = null;
      setStatus("指定标的后点「拉取」或「刷新」。", "down");
      equityEl.hidden = true;
      equityEl.replaceChildren();
      tabsEl.replaceChildren();
      tableEl.replaceChildren();
      const p = document.createElement("p");
      p.className = "chain-empty";
      p.textContent = "指定标的后拉取或刷新。";
      tableEl.append(p);
      return;
    }
    const data = await request(`/api/chain?q=${encodeURIComponent(q)}`);
    render(data);
  }

  async function pull() {
    const q = currentCode();
    if (!q) {
      setStatus("先输入标的。", "down");
      return;
    }
    setStatus(`正在从 OpenD 拉取 ${q}…`, "");
    const data = await request("/api/chain/pull", {
      method: "POST",
      body: JSON.stringify({ underlyings: q, days: 60 }),
    });
    render(data);
  }

  function setBusy(on) {
    busy = on;
    for (const btn of buttons) btn.disabled = on;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await pull();
    } catch (err) {
      setStatus(err.message || String(err), "down");
    } finally {
      setBusy(false);
    }
  });

  root.querySelector('[data-act="refresh"]').addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    try {
      await load();
    } catch (err) {
      setStatus(err.message || String(err), "down");
    } finally {
      setBusy(false);
    }
  });

  drawer.querySelector(".chain-drawer-close").addEventListener("click", closeDrawer);

  const preset = params.get("q");
  if (preset) input.value = preset;

  (async () => {
    apiBase = await resolveBase();
    if (apiBase == null) {
      setStatus("连不上本机 H5。先跑 runtime/scripts/serve_h5.py。", "down");
      return;
    }
    if (!input.value) input.value = "BIDU";
    try {
      await load();
    } catch (err) {
      setStatus(err.message || String(err), "down");
    }
  })();
})();
