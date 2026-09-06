(() => {
  const DEFAULT_URL = "http://127.0.0.1:4096";
  const WORKSPACE = "/Users/miller/Projects/miOption";
  const AUTO_ALLOW = /wiki_query|futu_probe|futu_quote_chain/;
  const GO_MODEL = { providerID: "opencode-go", modelID: "deepseek-v4-flash" };

  const params = new URLSearchParams(location.search);
  const base = (params.get("opencode") || localStorage.getItem("mioption.opencode") || DEFAULT_URL).replace(/\/$/, "");
  const directory = encodeURIComponent(WORKSPACE);

  const launch = document.querySelector(".chat-launch");
  const panel = document.querySelector(".chat-panel");
  const log = document.querySelector(".chat-log");
  const statusEl = document.querySelector(".chat-status");
  const form = document.querySelector(".chat-form");
  const input = form.querySelector("textarea");
  const send = form.querySelector("button[type=submit]");
  const close = document.querySelector(".chat-close");

  let sessionId = null;
  let eventAbort = null;
  let busy = false;
  const parts = new Map();

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function qs(path) {
    const join = path.includes("?") ? "&" : "?";
    return `${base}${path}${join}directory=${directory}`;
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

  function bubbleUser(text) {
    const wrap = document.createElement("article");
    wrap.className = "chat-msg chat-msg--user";
    wrap.innerHTML = `<div class="chat-bubble"></div>`;
    wrap.querySelector(".chat-bubble").textContent = text;
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function assistantRoot(messageID) {
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
    const root = assistantRoot(part.messageID);
    let node = root.querySelector(`[data-part="${part.id}"]`);
    if (node) return node;
    if (part.type === "reasoning") {
      node = document.createElement("details");
      node.className = "chat-reason";
      node.open = true;
      node.innerHTML = `<summary>推理</summary><pre></pre>`;
    } else if (part.type === "tool") {
      node = document.createElement("div");
      node.className = "chat-tool";
      node.innerHTML = `<strong></strong><pre class="chat-tool-in"></pre><pre class="chat-tool-out"></pre>`;
    } else if (part.type === "text") {
      node = document.createElement("div");
      node.className = "chat-text";
    } else {
      return null;
    }
    node.dataset.part = part.id;
    root.appendChild(node);
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
    if (AUTO_ALLOW.test(permBlob(perm))) {
      replyPermission(perm, "once");
      return;
    }
    const el = document.createElement("div");
    el.className = "chat-perm";
    el.dataset.perm = perm.id;
    el.innerHTML = `<p></p><button type="button" data-act="once">允许一次</button><button type="button" data-act="reject">拒绝</button>`;
    el.querySelector("p").textContent = perm.title || perm.permission || perm.action || perm.type || "需要许可";
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
      await api(`/session/${perm.sessionID}/permissions/${perm.id}`, {
        method: "POST",
        body: JSON.stringify({ response }),
      });
    } catch (err) {
      showError(`许可失败：${err.message}`);
    }
  }

  function handleEvent(evt) {
    if (!evt || !evt.type) return;
    const payload = evt.properties || evt.data || {};
    if (evt.type === "message.part.updated" && payload.part) {
      const part = payload.part;
      if (!sessionId || (part.sessionID && part.sessionID !== sessionId)) return;
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
    if (evt.type === "session.idle") {
      if (!sessionId || payload.sessionID === sessionId) {
        busy = false;
        send.disabled = false;
        setStatus(`OpenCode · ${GO_MODEL.modelID}`);
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

  async function bindGoModel(id) {
    const bound = { id: GO_MODEL.modelID, providerID: GO_MODEL.providerID };
    try {
      await api(`/api/session/${id}/model`, {
        method: "POST",
        body: JSON.stringify({ model: bound }),
      });
    } catch {
      /* 1.18 prompt_async still carries model; create already set it */
    }
  }

  async function ensureSession() {
    if (sessionId) {
      await bindGoModel(sessionId);
      return sessionId;
    }
    const created = await api("/session", {
      method: "POST",
      body: JSON.stringify({
        title: "vault-map",
        model: { id: GO_MODEL.modelID, providerID: GO_MODEL.providerID },
      }),
    });
    sessionId = created.id || created.sessionID || (created.data && created.data.id);
    if (!sessionId) throw new Error("OpenCode 未返回 session id");
    const got = (created.model && (created.model.id || created.model.modelID)) || "";
    if (got !== GO_MODEL.modelID) await bindGoModel(sessionId);
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
      listen();
      bubbleUser(text);
      busy = true;
      send.disabled = true;
      await api(`/session/${id}/prompt_async`, {
        method: "POST",
        body: JSON.stringify({
          model: { providerID: GO_MODEL.providerID, modelID: GO_MODEL.modelID },
          tools: {
            write: false,
            edit: false,
            bash: false,
            apply_patch: false,
          },
          system:
            "For option strategy questions, call MCP wiki_query or mioption_wiki_query. Cite the returned page_path. Do not invent P/L numbers. Do not edit files.",
          parts: [{ type: "text", text }],
        }),
      });
    } catch (err) {
      busy = false;
      send.disabled = false;
      showError(err.message);
    }
  }

  function openPanel() {
    panel.hidden = false;
    launch.setAttribute("aria-expanded", "true");
    health();
    listen();
    input.focus();
  }

  function closePanel() {
    panel.hidden = true;
    launch.setAttribute("aria-expanded", "false");
  }

  launch.addEventListener("click", () => {
    if (panel.hidden) openPanel();
    else closePanel();
  });
  close.addEventListener("click", closePanel);

  document.querySelectorAll('a[href="#chat-panel"]').forEach((link) => {
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      openPanel();
    });
  });
  if (location.hash === "#chat-panel") openPanel();

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;
    input.value = "";
    sendPrompt(text);
  });

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      form.requestSubmit();
    }
  });

  health();
})();
