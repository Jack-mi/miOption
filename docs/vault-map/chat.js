(() => {
  const DEFAULT_URL = "http://127.0.0.1:4096";
  const SAFE_TOOLS = ["wiki_query", "futu_probe", "futu_quote_chain", "seller_list_cards"];
  let GO_MODEL = { providerID: "opencode-go", modelID: "deepseek-v4-flash" };

  const root = document.querySelector("#chat");
  if (!root) return;

  const params = new URLSearchParams(location.search);
  let base = DEFAULT_URL;
  let directory = "";

  const log = root.querySelector(".chat-log");
  const emptyEl = root.querySelector(".gpt-empty");
  const statusEl = root.querySelector(".chat-status");
  const form = root.querySelector(".chat-form");
  const input = form.querySelector("textarea");
  const send = form.querySelector("button[type=submit]");
  const listEl = root.querySelector(".gpt-sessions");
  const titleEl = root.querySelector(".gpt-title");
  const toggle = root.querySelector(".gpt-rail-toggle");

  let sessionId = params.get("id") || "";
  let eventAbort = null;
  let busy = false;
  let sessions = [];
  const parts = new Map();
  const messageRoles = new Map();

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function qs(path) {
    const join = path.includes("?") ? "&" : "?";
    return `${base}${path}${join}directory=${directory}`;
  }

  function asList(data) {
    if (Array.isArray(data)) return data;
    if (!data || typeof data !== "object") return [];
    return data.data || data.sessions || data.messages || data.items || [];
  }

  function sessionKey(item) {
    return String((item && (item.id || item.sessionID || (item.info && item.info.id))) || "");
  }

  function sessionTitle(item) {
    return String((item && (item.title || item.slug || (item.info && item.info.title))) || "新对话");
  }

  async function api(path, options = {}) {
    const res = await fetch(qs(path), {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
    if (res.status === 204) return null;
    const text = await res.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
    if (!res.ok) {
      const msg = (data && (data.message || data.error || data.name)) || res.statusText;
      throw new Error(String(msg));
    }
    return data;
  }

  function showThread(hasMessages) {
    emptyEl.hidden = hasMessages;
    log.hidden = !hasMessages;
  }

  function bubbleUser(text) {
    showThread(true);
    const wrap = document.createElement("article");
    wrap.className = "chat-msg chat-msg--user";
    wrap.innerHTML = `<div class="chat-bubble"></div>`;
    wrap.querySelector(".chat-bubble").textContent = text;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function assistantRoot(messageID) {
    showThread(true);
    let el = log.querySelector(`[data-message="${messageID}"]`);
    if (!el) {
      el = document.createElement("article");
      el.className = "chat-msg chat-msg--assistant";
      el.dataset.message = messageID;
      log.appendChild(el);
    }
    return el;
  }

  function ensurePart(part) {
    const rootEl = assistantRoot(part.messageID);
    let node = rootEl.querySelector(`[data-part="${part.id}"]`);
    if (node) return node;
    if (part.type === "reasoning") {
      node = document.createElement("details");
      node.className = "chat-reason";
      node.open = false;
      node.innerHTML = `<summary>推理</summary><pre></pre>`;
    } else if (part.type === "tool") {
      node = document.createElement("details");
      node.className = "chat-tool";
      node.innerHTML = `<summary><strong></strong></summary><pre class="chat-tool-in"></pre><pre class="chat-tool-out"></pre>`;
    } else if (part.type === "text") {
      node = document.createElement("div");
      node.className = "chat-text";
    } else {
      return null;
    }
    node.dataset.part = part.id;
    rootEl.appendChild(node);
    return node;
  }

  function renderPart(part, delta) {
    parts.set(part.id, part);
    const node = ensurePart(part);
    if (!node) return;
    if (part.type === "reasoning") {
      const pre = node.querySelector("pre");
      pre.textContent = part.text || (pre.textContent + (delta || ""));
    } else if (part.type === "text") {
      node.textContent = part.text || (node.textContent + (delta || ""));
    } else if (part.type === "tool") {
      const state = part.state || {};
      node.dataset.status = state.status || "";
      node.querySelector("strong").textContent = `${part.tool || "tool"} · ${state.status || ""}`;
      node.querySelector(".chat-tool-in").textContent = JSON.stringify(state.input || {}, null, 2);
      const out = state.output || state.error || "";
      node.querySelector(".chat-tool-out").textContent = typeof out === "string" ? out : JSON.stringify(out, null, 2);
    }
    log.scrollTop = log.scrollHeight;
  }

  function showError(message) {
    showThread(true);
    const el = document.createElement("p");
    el.className = "chat-error";
    el.textContent = message;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
  }

  function permBlob(perm) {
    const bits = [
      perm.permission,
      perm.action,
      perm.title,
      perm.type,
      perm.pattern,
      ...(perm.patterns || []),
      ...(perm.resources || []),
      JSON.stringify(perm.metadata || {}),
    ];
    return bits.filter(Boolean).join(" ");
  }

  function showPermission(perm) {
    if (!perm || !perm.id) return;
    const existing = log.querySelector(`[data-perm="${perm.id}"]`);
    if (existing) return;
    showThread(true);
    const el = document.createElement("div");
    el.className = "chat-perm";
    el.dataset.perm = perm.id;
    el.innerHTML = `<p></p><button type="button" data-act="once">允许一次</button><button type="button" data-act="reject">拒绝</button>`;
    el.querySelector("p").textContent = permBlob(perm) || "需要许可";
    el.addEventListener("click", (ev) => {
      const act = ev.target && ev.target.dataset && ev.target.dataset.act;
      if (!act) return;
      replyPermission(perm, act);
      el.remove();
    });
    log.appendChild(el);
  }

  async function replyPermission(perm, response) {
    try {
      const path = perm.action
        ? `/api/session/${perm.sessionID}/permission/${perm.id}/reply`
        : `/permission/${perm.id}/reply`;
      await api(path, {
        method: "POST",
        body: JSON.stringify({ reply: response }),
      });
    } catch (err) {
      showError(`许可失败：${err.message}`);
    }
  }

  function handleEvent(evt) {
    if (!evt || !evt.type) return;
    const payload = evt.properties || evt.data || {};
    if (evt.type === "message.updated" && payload.info) {
      const info = payload.info;
      if (info.sessionID !== sessionId) return;
      messageRoles.set(info.id, info.role);
      if (info.role === "user") log.querySelector(`[data-message="${info.id}"]`)?.remove();
      return;
    }
    if (evt.type === "message.part.delta") {
      if (payload.sessionID !== sessionId) return;
      const part = parts.get(payload.partID);
      if (part && payload.field === "text") {
        part.text = (part.text || "") + (payload.delta || "");
        renderPart(part);
      }
      return;
    }
    if (evt.type === "message.part.updated" && payload.part) {
      const part = payload.part;
      if (!sessionId || (part.sessionID && part.sessionID !== sessionId)) return;
      if (messageRoles.get(part.messageID) === "user") return;
      renderPart(part, payload.delta);
      return;
    }
    if (
      evt.type === "permission.asked" ||
      evt.type === "permission.updated" ||
      evt.type === "permission.v2.asked"
    ) {
      if (sessionId && payload.sessionID && payload.sessionID !== sessionId) return;
      showPermission(payload);
      return;
    }
    if (evt.type === "session.error") {
      if (sessionId && payload.sessionID && payload.sessionID !== sessionId) return;
      const err = payload.error || payload;
      const msg = (err && err.data && err.data.message) || (err && err.message) || JSON.stringify(err);
      showError(String(msg));
      busy = false;
      send.disabled = false;
      return;
    }
    if (evt.type === "session.idle" || (evt.type === "session.status" && payload.status?.type === "idle")) {
      if (!sessionId || payload.sessionID === sessionId) {
        busy = false;
        send.disabled = false;
        setStatus(`OpenCode · ${GO_MODEL.modelID}`);
        refreshSessions();
      }
    }
  }

  async function listen() {
    if (eventAbort) eventAbort.abort();
    eventAbort = new AbortController();
    try {
      const res = await fetch(qs("/event"), {
        headers: { Accept: "text/event-stream" },
        signal: eventAbort.signal,
      });
      if (!res.ok || !res.body) throw new Error(`event ${res.status}`);
      setStatus(`OpenCode · ${GO_MODEL.modelID}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const frames = buf.split("\n\n");
        buf = frames.pop();
        for (const frame of frames) {
          const data = frame
            .split("\n")
            .filter((line) => line.startsWith("data:"))
            .map((line) => line.slice(5).trim())
            .join("\n");
          if (!data) continue;
          try {
            handleEvent(JSON.parse(data));
          } catch {
            /* ignore */
          }
        }
      }
      if (!eventAbort.signal.aborted) setStatus("事件流已结束，请刷新恢复连接。");
    } catch (err) {
      if (err.name === "AbortError") return;
      setStatus("事件流断开。确认 OpenCode 已加 --cors " + location.origin);
    }
  }

  async function health() {
    try {
      const data = await api("/global/health");
      const version = (data && data.version) || "";
      setStatus(version ? `OpenCode ${version} · ${GO_MODEL.modelID}` : `OpenCode · ${base}`);
      return true;
    } catch {
      setStatus(`未连上 ${base}。在仓库根运行：opencode serve --port 4096 --cors ${location.origin}`);
      return false;
    }
  }

  function renderSessions() {
    listEl.replaceChildren();
    for (const item of sessions) {
      const id = sessionKey(item);
      if (!id) continue;
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = sessionTitle(item);
      btn.dataset.id = id;
      if (id === sessionId) btn.setAttribute("aria-current", "true");
      btn.addEventListener("click", () => selectSession(id));
      li.append(btn);
      listEl.append(li);
    }
  }

  async function refreshSessions() {
    try {
      sessions = asList(await api("/session")).filter((item) => item.title?.startsWith("miOption"));
    } catch {
      sessions = sessions.filter((item) => sessionKey(item));
    }
    renderSessions();
  }

  function setTitle(text) {
    titleEl.textContent = text || "新对话";
  }

  async function loadMessages(id) {
    log.replaceChildren();
    parts.clear();
    messageRoles.clear();
    const msgs = asList(await api(`/session/${id}/message`));
    for (const msg of msgs) {
      const info = msg.info || msg;
      const role = info.role || msg.role;
      messageRoles.set(info.id, role);
      const msgParts = msg.parts || [];
      if (role === "user") {
        const text = msgParts
          .filter((part) => part.type === "text")
          .map((part) => part.text || "")
          .join("\n");
        if (text) bubbleUser(text);
      } else {
        for (const part of msgParts) renderPart(part);
      }
    }
    showThread(log.childElementCount > 0);
  }

  async function selectSession(id) {
    sessionId = id;
    const current = sessions.find((item) => sessionKey(item) === id);
    setTitle(current ? sessionTitle(current) : "对话");
    const url = new URL(location.href);
    url.searchParams.set("id", id);
    history.replaceState({}, "", url);
    renderSessions();
    root.classList.remove("rail-open");
    try {
      await loadMessages(id);
      const statuses = await api("/session/status");
      busy = Boolean(statuses?.[id] && statuses[id].type !== "idle");
      send.disabled = busy;
      const permissions = asList(await api("/permission"));
      permissions.filter((permission) => permission.sessionID === id).forEach(showPermission);
    } catch (err) {
      showError(err.message || String(err));
    }
  }

  function newChat() {
    busy = false;
    send.disabled = false;
    sessionId = "";
    parts.clear();
    messageRoles.clear();
    log.replaceChildren();
    showThread(false);
    setTitle("新对话");
    const url = new URL(location.href);
    url.searchParams.delete("id");
    history.replaceState({}, "", url);
    renderSessions();
    root.classList.remove("rail-open");
    input.focus();
  }

  async function ensureSession() {
    if (sessionId) {
      return sessionId;
    }
    const created = await api("/session", {
      method: "POST",
      body: JSON.stringify({
        title: "miOption research",
        model: { id: GO_MODEL.modelID, providerID: GO_MODEL.providerID },
        permission: [
          { permission: "*", pattern: "*", action: "deny" },
          ...SAFE_TOOLS.map((name) => ({ permission: `mioption_${name}`, pattern: "*", action: "allow" })),
          ...["seller_scan", "seller_verdict", "seller_monitor_tick"].map((name) => ({ permission: `mioption_${name}`, pattern: "*", action: "ask" })),
        ],
      }),
    });
    sessionId = created.id || created.sessionID || (created.data && created.data.id);
    if (!sessionId) throw new Error("OpenCode 未返回 session id");
    const url = new URL(location.href);
    url.searchParams.set("id", sessionId);
    history.replaceState({}, "", url);
    await refreshSessions();
    const current = sessions.find((item) => sessionKey(item) === sessionId);
    setTitle(current ? sessionTitle(current) : "新对话");
    return sessionId;
  }

  async function sendPrompt(text) {
    const ok = await health();
    if (!ok) {
      showError(`OpenCode 未在 ${base} 监听。`);
      return;
    }
    try {
      const id = await ensureSession();
      bubbleUser(text);
      busy = true;
      send.disabled = true;
      await api(`/session/${id}/prompt_async`, {
        method: "POST",
        body: JSON.stringify({
          model: { providerID: GO_MODEL.providerID, modelID: GO_MODEL.modelID },
          system:
            "You are miOption's research assistant. Answer in the user's language. For option strategy questions, call mioption_wiki_query, using English strategy names when helpful; use returned content and cite page_path. For cards use mioption seller tools. Ask before changing a verdict. Use no other tools. Never place any orders, including simulated orders. Never edit files. Do not invent prices, payoff evidence or realized P/L. An empty scan is a valid result. State quote sources and timestamps when available.",
          parts: [{ type: "text", text }],
        }),
      });
    } catch (err) {
      busy = false;
      send.disabled = false;
      showError(err.message);
    }
  }

  root.querySelector('[data-act="new"]').addEventListener("click", newChat);
  toggle.addEventListener("click", () => {
    const open = root.classList.toggle("rail-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;
    input.value = "";
    input.style.height = "auto";
    sendPrompt(text);
  });

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      form.requestSubmit();
    }
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });

  (async () => {
    try {
      const response = await fetch("/api/config");
      if (!response.ok) throw new Error("workbench config unavailable");
      const config = await response.json();
      base = (params.get("opencode") || config.opencode_url).replace(/\/$/, "");
      directory = encodeURIComponent(config.workspace);
      GO_MODEL = config.model;
    } catch (error) {
      setStatus(`请从 miOption 工作台打开此页：${error.message}`);
      return;
    }
    const ok = await health();
    if (ok) {
      listen();
      await refreshSessions();
    }
    if (sessionId) {
      try {
        await selectSession(sessionId);
      } catch (err) {
        showError(err.message || String(err));
      }
    } else {
      showThread(false);
      input.focus();
    }
  })();
})();
