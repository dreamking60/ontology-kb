/* 银行概念知识库 · AI 助手 — SPA (vanilla JS, no build step) */
"use strict";

/* ------------------------------------------------------------------ utils */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function apiJSON(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* noop */ }
    throw new Error(detail);
  }
  return res.json();
}

/* minimal markdown (headings, bold, inline code, fenced code, lists, links) */
function md(src) {
  let text = esc(src).replace(/\r\n/g, "\n");
  const blocks = [];
  text = text.replace(/```([\s\S]*?)```/g, (_, code) => {
    blocks.push(`<pre><code>${code.trim()}</code></pre>`);
    return `\u0000B${blocks.length - 1}\u0000`;
  });
  const lines = text.split("\n");
  let html = "";
  let listType = null;
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.trim() === "") { closeList(); continue; }
    let m = line.match(/^(\#{1,3})\s+(.*)$/);
    if (m) { closeList(); const lvl = m[1].length; const tag = lvl === 1 ? "h1" : lvl === 2 ? "h2" : "h3";
      html += `<${tag}>${inline(m[2])}</${tag}>`; continue; }
    m = line.match(/^[-*]\s+(.*)$/);
    if (m) { if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
      html += `<li>${inline(m[1])}</li>`; continue; }
    m = line.match(/^\d+\.\s+(.*)$/);
    if (m) { if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
      html += `<li>${inline(m[1])}</li>`; continue; }
    closeList();
    html += `<p>${inline(line)}</p>`;
  }
  closeList();
  html = html.replace(/\u0000B(\d+)\u0000/g, (_, i) => blocks[Number(i)]);
  return html;
}
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

/* ------------------------------------------------------------------ state */
const state = {
  route: "chat",
  messages: [], // {role, content, mode, citations, trace}
  agentMode: false,
  busy: false,
};
const SUGGESTIONS = [
  "什么是大额存单？",
  "定期存款和活期存款有什么区别？",
  "哪些示例产品受存款保险保障？它们的期限分别是多少？",
  "信用贷款和住房贷款有什么区别？",
];

/* ------------------------------------------------------------ sidebar bits */
async function refreshStatus() {
  try {
    const cfg = await apiJSON("/api/config");
    const card = $("#llm-status-card");
    const dot = $(".status-dot", card);
    const label = $(".status-text", card);
    if (cfg.configured) {
      card.dataset.mode = "configured";
      label.textContent = `LLM 已配置 · ${cfg.model || "model"}`;
      dot.title = `端点 ${cfg.base_url}`;
    } else {
      card.dataset.mode = "none";
      label.textContent = "未配置 LLM · 摘要模式（fallback）";
      dot.title = "回答将使用知识库确定性摘要";
    }
    return cfg;
  } catch (_) {
    $("#llm-status-card").dataset.mode = "unknown";
    $(".status-text", $("#llm-status-card")).textContent = "状态获取失败";
    return null;
  }
}
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("kb-theme", t); } catch (_) { /* noop */ }
}
function initShell() {
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(next);
  });
  try {
    const saved = localStorage.getItem("kb-theme");
    if (saved) setTheme(saved);
  } catch (_) { /* noop */ }
  $("#llm-status-card").addEventListener("click", () => { location.hash = "#/settings"; });
  fetch("/api/health").then((r) => r.json()).then((h) => {
    $("#kb-stats").textContent = `三元组 ${h.triples || "?"}`;
  }).catch(() => { $("#kb-stats").textContent = "知识库不可用"; });
}

/* ---------------------------------------------------------------- routing */
function route() {
  const hash = location.hash.replace(/^#\//, "") || "chat";
  state.route = hash.split("?")[0];
  $$("#nav .nav-item").forEach((a) =>
    a.classList.toggle("active", a.dataset.route === state.route));
  const view = $("#view");
  view.scrollTop = 0;
  if (state.route === "chat") return renderChat(view);
  if (state.route === "explore") return renderExplore(view);
  if (state.route === "reason") return renderReason(view);
  if (state.route === "settings") return renderSettings(view);
  view.innerHTML = "";
  renderChat(view);
}

/* ---------------------------------------------------------------- chat view */
let chatComposer = null;
function renderChat(view) {
  view.className = "page-chat";
  view.innerHTML = `
    <div class="chat-head">
      <h1>AI 对话</h1>
      <p>基于金融本体知识库的问答助手 —— 回答只引用收录的概念，附模式与来源。</p>
      <div class="toolbar">
        <div class="seg" id="mode-seg">
          <button data-mode="0" class="active">标准问答</button>
          <button data-mode="1">🤖 Agent 工具模式</button>
        </div>
      </div>
    </div>
    <div class="chat-scroll" id="chat-scroll">
      <div class="chat-col" id="chat-col"></div>
    </div>
    <div class="composer-wrap">
      <div class="composer">
        <textarea id="chat-input" rows="1" placeholder="问知识库… 例如：大额存单和定期存款有什么区别？"></textarea>
        <button class="send-btn" id="chat-send" title="发送">➤</button>
      </div>
      <div class="hintline">↵ 发送 · Agent 模式下 LLM 可自主调用知识库工具（只读），未配置 LLM 时自动使用检索摘要。</div>
    </div>`;
  state.messages = [];
  $$("#mode-seg button").forEach((b) => b.addEventListener("click", () => {
    state.agentMode = b.dataset.mode === "1";
    $$("#mode-seg button").forEach((x) => x.classList.toggle("active", x === b));
  }));
  chatComposer = $("#chat-input");
  const sendBtn = $("#chat-send");
  const send = () => {
    const q = chatComposer.value.trim();
    if (!q || state.busy) return;
    chatComposer.value = "";
    autoGrow();
    addUserBubble(q);
    runAnswer(q);
  };
  sendBtn.addEventListener("click", send);
  chatComposer.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  chatComposer.addEventListener("input", autoGrow);
  if (state.messages.length === 0) showEmpty();
  chatComposer.focus();
}
function autoGrow() {
  chatComposer.style.height = "auto";
  chatComposer.style.height = Math.min(chatComposer.scrollHeight, 160) + "px";
}
function showEmpty() {
  const col = $("#chat-col");
  col.innerHTML = `<div class="empty-state">
    <div class="big">👋</div>
    <p>你好，我是<b>银行概念知识库</b>的 AI 助手。<br/>试试下面的问题，或直接输入你的问题。</p>
    <div class="suggest"></div>
  </div>`;
  const box = $(".suggest", col);
  SUGGESTIONS.forEach((s) => {
    const b = el("button", null, s);
    b.addEventListener("click", () => {
      chatComposer.value = s;
      autoGrow();
      const ev = new Event("input", { bubbles: true });
      chatComposer.dispatchEvent(ev);
      const send = $("#chat-send");
      if (send) send.click();
    });
    box.appendChild(b);
  });
}
function scrollBottom() {
  const sc = $("#chat-scroll");
  if (sc) sc.scrollTop = sc.scrollHeight;
}
function addUserBubble(q) {
  const empty = $("#chat-col .empty-state");
  if (empty) empty.remove();
  const col = $("#chat-col");
  const wrap = el("div", "msg user");
  wrap.appendChild(el("div", "avatar", "🧑"));
  const bub = el("div", "bubble");
  bub.innerHTML = md(q);
  wrap.appendChild(bub);
  col.appendChild(wrap);
  scrollBottom();
}
function addAssistantSlot() {
  const col = $("#chat-col");
  const wrap = el("div", "msg assistant");
  wrap.appendChild(el("div", "avatar", "🤖"));
  const side = el("div", "msg-side");
  const bub = el("div", "bubble");
  bub.innerHTML = `<span class="typing"><i></i><i></i><i></i></span>`;
  const meta = el("div", "msg-meta");
  const traceZone = el("div", "trace-zone");
  side.appendChild(bub);
  side.appendChild(meta);
  side.appendChild(traceZone);
  wrap.appendChild(side);
  col.appendChild(wrap);
  scrollBottom();
  return { wrap, bub, meta, traceZone };
}
function setBadge(meta, mode) {
  const labels = { agent: "🤖 Agent", llm: "🟢 LLM", fallback: "🟡 检索摘要" };
  let badge = $(".mode-badge", meta);
  if (!badge) { badge = el("span", "mode-badge"); meta.prepend(badge); }
  badge.className = `mode-badge m-${mode}`;
  badge.textContent = labels[mode] || mode;
}

/* stream + events */
function handleStreamEvent(evt, ctx) {
  if (evt.type === "meta") {
    if (evt.mode) setBadge(ctx.meta, evt.mode);
  } else if (evt.type === "mode") {
    setBadge(ctx.meta, evt.mode);
  } else if (evt.type === "delta") {
    ctx.bub.innerHTML = md(ctx.raw + evt.text);
    ctx.raw += evt.text;
    scrollBottom();
  } else if (evt.type === "step") {
    const panel = ctx.tracePanel || (() => {
      const holder = el("div", "trace-panel");
      ctx.traceZone.appendChild(holder);
      ctx.tracePanel = holder;
      return holder;
    })();
    const row = el("div", "trace-step");
    row.appendChild(el("div", "ts-head", `第 ${evt.step} 步 · ${evt.tool}`));
    if (evt.summary) row.appendChild(el("div", "ts-summary", evt.summary));
    panel.appendChild(row);
    scrollBottom();
  } else if (evt.type === "citations") {
    if (evt.citations && evt.citations.length) {
      const chips = el("div", "chips");
      evt.citations.forEach((c) => {
        const chip = el("span", "chip", `📎 ${c.label}`);
        chip.addEventListener("click", () => { location.hash = `#/explore?id=${encodeURIComponent(c.id)}`; });
        chips.appendChild(chip);
      });
      ctx.meta.appendChild(chips);
      scrollBottom();
    }
  } else if (evt.type === "done") {
    if (evt.mode) setBadge(ctx.meta, evt.mode);
    if (ctx.tracePanel) {
      const det = el("details");
      det.appendChild(el("summary", "trace-toggle", `🧩 工具执行轨迹`));
      const panel = ctx.tracePanel;
      ctx.traceZone.removeChild(panel);
      det.appendChild(panel);
      ctx.traceZone.appendChild(det);
    }
  }
}
async function runAnswer(q) {
  state.busy = true;
  const sendBtn = $("#chat-send");
  if (sendBtn) sendBtn.disabled = true;
  const ctx = addAssistantSlot();
  ctx.raw = "";
  const endpoint = state.agentMode ? "/api/agent/chat/stream" : "/api/chat/stream";
  try {
    await postStream(endpoint, { question: q, history: [] }, (evt) => handleStreamEvent(evt, ctx));
  } catch (err) {
    ctx.bub.innerHTML = md(`⚠️ 请求失败：${esc(err.message)}\n\n请检查后端（make api）或前往设置确认 LLM 配置。`);
    setBadge(ctx.meta, "fallback");
  } finally {
    state.busy = false;
    if (sendBtn) sendBtn.disabled = false;
    chatComposer && chatComposer.focus();
    scrollBottom();
  }
}
async function postStream(path, payload, onEvent) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* noop */ }
    throw new Error(detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const lines = block.split("\n");
      let evtType = "message";
      const dataLines = [];
      lines.forEach((ln) => {
        if (ln.startsWith("event:")) evtType = ln.slice(6).trim();
        else if (ln.startsWith("data:")) dataLines.push(ln.slice(5).trim());
      });
      const data = dataLines.join("\n");
      if (!data) continue;
      let evt = { type: evtType };
      try { evt = { ...JSON.parse(data), type: evtType }; } catch (_) { /* keep */ }
      onEvent(evt);
    }
  }
}

/* ------------------------------------------------------------- explore view */
let detailIri = null;
async function renderExplore(view) {
  view.className = "page";
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  detailIri = params.get("id") ? decodeURIComponent(params.get("id")) : null;
  view.innerHTML = `
    <div class="page-inner">
      <h1 class="page-title">概念探索</h1>
      <p class="page-sub">语义搜索 / 层级浏览 / 概念详情 —— 由同一个本体知识库驱动。</p>
      <div class="search-row">
        <input id="exp-q" placeholder="搜索概念：存款 / 定存 / 按揭 / LPR / deposit…" />
        <button id="exp-go">搜索</button>
      </div>
      <div class="card"><h3>类层级</h3><div id="exp-tree"></div></div>
      <div class="card" id="exp-results-card"><h3>搜索结果</h3><div id="exp-results"></div></div>
      <div class="card" id="exp-detail-card"><h3>概念详情</h3><div id="exp-detail"><span class="note">从左侧选择概念查看详情。</span></div></div>
    </div>`;
  const go = async () => {
    const q = $("#exp-q").value.trim();
    if (!q) return;
    const body = await apiJSON(`/api/concepts?q=${encodeURIComponent(q)}`);
    const box = $("#exp-results");
    box.innerHTML = "";
    if (!body.count) { box.appendChild(el("div", "note", "没有匹配的概念（不是错误）。")); return; }
    body.results.forEach((c) => {
      const item = el("div", "result-item");
      const title = el("div", "ri-title", c.label_zh || c.label_en);
      if (c.label_en && c.label_zh) title.textContent += `  (${c.label_en})`;
      item.appendChild(title);
      item.appendChild(el("div", "ri-sub", `${c.kind === "class" ? "类" : "示例个体"} · ${c.definition ? c.definition.slice(0, 90) : ""}`));
      item.addEventListener("click", () => showDetail(c));
      box.appendChild(item);
    });
  };
  $("#exp-go").addEventListener("click", go);
  $("#exp-q").addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  const tree = await apiJSON("/api/tree");
  renderTree($("#exp-tree"), tree.roots, 0);
  if (detailIri) {
    try {
      const d = await apiJSON(`/api/concepts/${encodeURIComponent(detailIri)}`);
      showDetail(d);
    } catch (_) { /* ignore */ }
  }
}
function renderTree(container, nodes) {
  nodes.forEach((n) => {
    const label = el("span", "tree-label", n.label_zh || n.label_en);
    if (n.label_en && n.label_zh) label.title = n.label_en;
    label.addEventListener("click", () =>
      apiJSON(`/api/concepts/${encodeURIComponent(n.id)}`).then(showDetail));
    if (n.children && n.children.length) {
      const det = el("details");
      const sum = el("summary");
      sum.appendChild(label);
      sum.appendChild(document.createTextNode(` (${n.children.length})`));
      det.appendChild(sum);
      const sub = el("div");
      renderTree(sub, n.children);
      det.appendChild(sub);
      container.appendChild(det);
    } else {
      container.appendChild(label);
    }
  });
}
function showDetail(d) {
  const box = $("#exp-detail");
  if (!box) return;
  detailIri = d.id;
  const labels = d.labels || {};
  let html = `<div class="ri-title" style="font-weight:700">${esc(labels.zh || labels.en || d.id)}`;
  if (labels.en && labels.zh) html += ` <span class="note">(${esc(labels.en)})</span>`;
  html += ` <span class="note">${d.kind === "class" ? "· 类" : "· 示例个体"}</span></div>`;
  if (d.synonyms && d.synonyms.length) html += `<div class="kv"><div class="k">同义词</div><div>${d.synonyms.map(esc).join("、")}</div></div>`;
  if (d.definition) html += `<p>${esc(d.definition)}</p>`;
  if (d.superclass) html += `<div class="kv"><div class="k">上级类</div><div>${esc(d.superclass.label)}</div></div>`;
  if (d.subclasses && d.subclasses.length)
    html += `<div class="kv"><div class="k">子类</div><div>${d.subclasses.map((s) => esc(s.label)).join("、")}</div></div>`;
  if (d.types && d.types.length)
    html += `<div class="kv"><div class="k">类型</div><div>${d.types.map((t) => esc(t.label)).join("、")}</div></div>`;
  if (d.attributes && d.attributes.length) {
    html += "<div class='kv'><div class='k'>属性</div><div><table class='tbl'><tbody>";
    d.attributes.forEach((a) => { html += `<tr><td>${esc(a.property_label)}</td><td>${esc(a.value)}</td></tr>`; });
    html += "</tbody></table></div></div>";
  }
  if (d.relationships && d.relationships.length) {
    html += "<div class='kv'><div class='k'>关系</div><div><table class='tbl'><tbody>";
    d.relationships.forEach((r) => { html += `<tr><td>${esc(r.property_label)}</td><td>→ ${esc(r.value_label)}</td></tr>`; });
    html += "</tbody></table></div></div>";
  }
  box.innerHTML = html;
}

/* ------------------------------------------------------------- reason view */
async function renderReason(view) {
  view.className = "page";
  view.innerHTML = `
    <div class="page-inner">
      <h1 class="page-title">推理演示</h1>
      <p class="page-sub">OWL2-RL 类层级推理 + 演示规则，每条事实带溯源，且不会修改数据。</p>
      <button class="btn btn-primary" id="reason-run">▶ 运行推理演示</button>
      <div id="reason-out" style="margin-top:16px"></div>
    </div>`;
  $("#reason-run").addEventListener("click", async (e) => {
    e.target.disabled = true;
    const out = $("#reason-out");
    out.innerHTML = `<span class="note">运行中…（HermiT 一致性见设置旁的 make check-consistency）</span>`;
    try {
      const d = await apiJSON("/api/reasoning/demo", { method: "POST", body: "{}" });
      let html = `<div class="card">
        <table class="tbl"><tbody>
        <tr><th>声明的类型事实</th><td>${d.asserted_type_facts.length}</td></tr>
        <tr><th>推理得到的类型</th><td>${d.inferred_type_facts.length}</td></tr>
        <tr><th>规则推导事实</th><td>${d.rule_derived_facts.length}</td></tr>
        <tr><th>数据未被修改</th><td>${d.store_unchanged.unchanged}（前后各 ${d.store_unchanged.triples_before} 条）</td></tr>
        <tr><th>一致性</th><td>${esc(d.consistency.status)} · ${esc(d.consistency.checked_by)}</td></tr>
        </tbody></table></div>`;
      if (d.inferred_type_facts.length) {
        html += `<div class="card"><h3>推理得到的类型（inferred）</h3><table class="tbl"><thead><tr><th>个体</th><th>类型</th><th>说明</th></tr></thead><tbody>`;
        d.inferred_type_facts.forEach((f) => {
          html += `<tr><td>${esc(f.subject_label)}</td><td>${esc(f.object_label)}</td><td class="note">${esc(f.explanation || "")}</td></tr>`;
        });
        html += "</tbody></table></div>";
      }
      if (d.rule_derived_facts.length) {
        html += `<div class="card"><h3>规则推导（rule-derived）</h3>`;
        d.rule_derived_facts.forEach((f) => {
          html += `<div class="kv"><div class="k">${esc(f.subject_label)}</div><div>→ rdf:type → <b>${esc(f.object_label)}</b><br/><span class="note">${esc(f.rule.text)}</span></div></div>`;
        });
        html += "</div>";
      }
      out.innerHTML = html;
    } catch (err) {
      out.innerHTML = `<div class="note" style="color:var(--err)">失败：${esc(err.message)}</div>`;
    } finally {
      e.target.disabled = false;
    }
  });
}

/* ------------------------------------------------------------ settings view */
async function renderSettings(view) {
  view.className = "page";
  view.innerHTML = `
    <div class="page-inner">
      <h1 class="page-title">设置 · LLM API</h1>
      <p class="page-sub">配置 OpenAI 兼容的对话接口（DeepSeek / OpenAI / 通义 / 本地 Ollama 等均可）。未配置时问答自动使用<b>知识库检索摘要</b>（mode=fallback），功能完整不报错。</p>
      <div class="card">
        <div class="config-state" id="cfg-state"></div>
        <div class="form-row">
          <label>Base URL（OpenAI 兼容端点）</label>
          <input id="cfg-url" placeholder="https://api.deepseek.com/v1" autocomplete="off" />
        </div>
        <div class="form-row">
          <label>API Key</label>
          <input id="cfg-key" type="password" placeholder="sk-…" autocomplete="off" />
        </div>
        <div class="form-row">
          <label>Model</label>
          <input id="cfg-model" placeholder="deepseek-chat" autocomplete="off" />
        </div>
        <button class="btn btn-primary" id="cfg-save">保存并应用</button>
        <button class="btn btn-danger" id="cfg-clear">清除配置</button>
        <div id="cfg-msg" style="margin-top:10px"></div>
      </div>
      <div class="card">
        <h3>说明</h3>
        <ul class="note">
          <li>配置仅保存在<b>服务进程内存</b>，不会写入磁盘；接口读取时掩码返回，密钥不会回显或进日志。</li>
          <li>重启服务后需要重新配置，或在启动前用 <code class="inl">export BANKING_KB_LLM_BASE_URL / _API_KEY / _MODEL</code> 持久化（见 <code class="inl">.env.example</code>）。</li>
          <li>模型不支持工具调用时，Agent 模式会自动退化为普通 LLM 回答；调用失败同样自动降级为摘要。</li>
        </ul>
      </div>
    </div>`;
  const cfg = await refreshStatus();
  const renderState = () => {
    const box = $("#cfg-state");
    if (cfg && cfg.configured) {
      box.innerHTML = `<span class="ok-text">● LLM 已配置</span><span class="note">来源：${cfg.source === "env" ? "环境变量" : "页面设置"}</span>`;
    } else {
      box.innerHTML = `<span class="warn-text">● 未配置 LLM</span><span class="note">→ 将使用确定性检索摘要回答（mode=fallback），仍可正常提问。</span>`;
    }
  };
  renderState();
  if (cfg) {
    $("#cfg-url").value = cfg.base_url || "";
    $("#cfg-model").value = cfg.model || "";
    $("#cfg-key").placeholder = cfg.key_present ? "••••••（已设置，留空则保持不变）" : "sk-…";
  }
  const msg = (t, cls) => { const m = $("#cfg-msg"); m.textContent = t; m.className = cls || ""; };
  $("#cfg-save").addEventListener("click", async () => {
    const url = $("#cfg-url").value.trim();
    const model = $("#cfg-model").value.trim();
    let key = $("#cfg-key").value.trim();
    if (!url || !model) { msg("Base URL 与 Model 必填。", "warn-text"); return; }
    if (!key && cfg && cfg.key_present) key = "keep";
    if (!key) { msg("请填写 API Key（或先清除配置）。", "warn-text"); return; }
    try {
      if (key === "keep" && cfg) {
        /* fetch masked presence only — cannot re-read key; ask user to re-enter */
        msg("为保证安全不保留明文密钥：请重新输入 API Key 后保存。", "warn-text");
        return;
      }
      const next = await apiJSON("/api/config", {
        method: "POST",
        body: JSON.stringify({ base_url: url, api_key: key, model }),
      });
      Object.assign(cfg, next);
      msg("已保存并应用 ✓ 现在开始回答将使用 LLM（支持流式）。", "ok-text");
      $("#cfg-key").value = "";
      renderState();
      await refreshStatus();
    } catch (err) {
      msg("保存失败：" + err.message, "warn-text");
    }
  });
  $("#cfg-clear").addEventListener("click", async () => {
    try {
      const next = await apiJSON("/api/config", { method: "DELETE" });
      Object.assign(cfg, next);
      msg("已清除运行时配置（若设了环境变量，仍以环境变量为准）。", "warn-text");
      renderState();
      await refreshStatus();
    } catch (err) {
      msg("清除失败：" + err.message, "warn-text");
    }
  });
}

/* ------------------------------------------------------------------ boot */
window.addEventListener("hashchange", route);
initShell();
refreshStatus().then(route);
