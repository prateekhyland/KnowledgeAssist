/*
 * KnowledgeAssist embeddable widget.
 * Add to any page with a single line (it derives the API base from its own <script> src):
 *   <script src="http://YOUR-SERVER:8000/widget.js"></script>
 * Optional override if the API lives elsewhere:
 *   <script src=".../widget.js" data-api="http://api-host:8000"></script>
 * Optional: pin answers to one doc set when the URL doesn't reveal it:
 *   <script src=".../widget.js" data-kb="jcscc"></script>
 */
(function () {
  "use strict";

  var me = document.currentScript;
  var API_BASE = (me && me.getAttribute("data-api")) ||
    (me ? new URL(me.src).origin : window.location.origin);

  var APP_NAME = "KnowledgeAssist";
  // Doc set (knowledge base) this widget is embedded in. An explicit data-kb wins;
  // otherwise it is detected from the host page URL's first path segment
  // (e.g. /jcscc/... -> "jcscc") once we know which knowledge bases exist.
  // null => search across all docs.
  var KB_ID = (me && me.getAttribute("data-kb")) || null;
  var PAGE_SEGMENT = (window.location.pathname.split("/").filter(Boolean)[0] || "");

  // ---------- styles ----------
  // Rendered inside a shadow root, so these never leak out; :host blocks the host
  // page's inherited styles from leaking in.
  var css = "" +
    ":host{all:initial}" +
    ".ka-btn,.ka-panel,.ka-panel *{box-sizing:border-box}" +
    ".ka-btn{position:fixed;right:24px;bottom:24px;width:56px;height:56px;border-radius:50%;" +
    "background:#2b6cb0;color:#fff;border:none;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);" +
    "font-size:24px;z-index:2147483000;" +
    "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}" +
    ".ka-panel{position:fixed;right:24px;bottom:92px;width:380px;max-width:calc(100vw - 32px);" +
    "height:560px;max-height:calc(100vh - 120px);background:#fff;border-radius:12px;display:none;" +
    "flex-direction:column;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.3);z-index:2147483000;" +
    "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}" +
    ".ka-panel.ka-open{display:flex}" +
    ".ka-head{background:#2b6cb0;color:#fff;padding:12px 16px;font-weight:600;display:flex;" +
    "justify-content:space-between;align-items:center}" +
    ".ka-head span{cursor:pointer;opacity:.85}" +
    ".ka-msgs{flex:1;overflow-y:auto;padding:14px;background:#f7fafc}" +
    ".ka-msg{margin:0 0 12px;padding:10px 12px;border-radius:10px;font-size:14px;line-height:1.5;" +
    "white-space:normal;word-wrap:break-word}" +
    ".ka-user{background:#2b6cb0;color:#fff;margin-left:40px}" +
    ".ka-bot{background:#fff;border:1px solid #e2e8f0;color:#1a202c;margin-right:20px}" +
    ".ka-bot pre{background:#1a202c;color:#e2e8f0;padding:10px;border:0;border-radius:8px;" +
    "overflow-x:auto;margin:8px 0;font-size:12.5px;line-height:1.45;white-space:pre;" +
    "font-family:Consolas,Monaco,'Courier New',monospace;text-decoration:none}" +
    ".ka-bot code{background:#edf2f7;color:#1a202c;padding:1px 4px;border:0;border-radius:4px;" +
    "font-size:12.5px;font-family:Consolas,Monaco,'Courier New',monospace;text-decoration:none}" +
    ".ka-bot pre code{background:none;color:inherit;padding:0;border-radius:0;font-size:inherit}" +
    ".ka-bot a{color:#2b6cb0}" +
    ".ka-src{font-size:12px;color:#4a5568;margin-top:8px;border-top:1px dashed #cbd5e0;padding-top:6px}" +
    ".ka-src a{color:#2b6cb0;text-decoration:none}" +
    ".ka-foot{display:flex;border-top:1px solid #e2e8f0;padding:8px}" +
    ".ka-foot input{flex:1;border:1px solid #cbd5e0;border-radius:8px;padding:9px 10px;font-size:14px;" +
    "outline:none}" +
    ".ka-foot button{margin-left:8px;background:#2b6cb0;color:#fff;border:none;border-radius:8px;" +
    "padding:0 14px;cursor:pointer}" +
    ".ka-typing{color:#718096;font-style:italic;font-size:13px}";

  // Render into a shadow root so the host page's stylesheet (Javadoc, Bootstrap,
  // Enunciate, ...) cannot restyle the chat UI. Falls back to a plain div on
  // browsers without shadow DOM.
  var mount = document.createElement("div");
  document.body.appendChild(mount);
  var root = mount.attachShadow ? mount.attachShadow({ mode: "open" }) : mount;

  var style = document.createElement("style");
  style.textContent = css;
  root.appendChild(style);

  // ---------- DOM ----------
  var btn = el("button", "ka-btn", "\uD83D\uDCAC");
  var panel = el("div", "ka-panel");
  panel.innerHTML =
    '<div class="ka-head"><div class="ka-title"></div><span class="ka-close">\u2715</span></div>' +
    '<div class="ka-msgs"></div>' +
    '<div class="ka-foot"><input type="text" placeholder="Ask about the API docs..." />' +
    '<button class="ka-send">Send</button></div>';
  root.appendChild(btn);
  root.appendChild(panel);

  var msgs = panel.querySelector(".ka-msgs");
  var input = panel.querySelector("input");
  var sendBtn = panel.querySelector(".ka-send");
  panel.querySelector(".ka-title").textContent = APP_NAME;

  fetch(API_BASE + "/config").then(function (r) { return r.json(); })
    .then(function (c) {
      if (c && c.app_name) {
        APP_NAME = c.app_name;
        panel.querySelector(".ka-title").textContent = APP_NAME;
      }
      // Scope to the current doc set if this page's path segment matches a KB id.
      if (!KB_ID && c && c.knowledge_bases) {
        var ids = c.knowledge_bases.map(function (k) { return k.id; });
        if (ids.indexOf(PAGE_SEGMENT) !== -1) KB_ID = PAGE_SEGMENT;
      }
    }).catch(function () {});

  btn.onclick = function () {
    panel.classList.toggle("ka-open");
    if (panel.classList.contains("ka-open")) input.focus();
  };
  panel.querySelector(".ka-close").onclick = function () {
    panel.classList.remove("ka-open");
  };
  sendBtn.onclick = send;
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") send();
  });

  greet();

  function greet() {
    addBot("Hi! I'm **" + APP_NAME + "**. Ask me anything about the API docs, or ask " +
      "me to write a sample using the API.");
  }

  function send() {
    var q = input.value.trim();
    if (!q) return;
    input.value = "";
    addUser(q);
    var bot = addBot("");
    bot.querySelector(".ka-content").innerHTML = '<span class="ka-typing">Thinking...</span>';
    stream(q, bot);
  }

  function stream(question, botEl) {
    var content = botEl.querySelector(".ka-content");
    var answer = "";
    var sources = [];
    var payload = { question: question, stream: true };
    if (KB_ID) payload.kb_id = KB_ID;
    fetch(API_BASE + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (resp) {
      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";
      function pump() {
        return reader.read().then(function (res) {
          if (res.done) { finalize(); return; }
          buffer += decoder.decode(res.value, { stream: true });
          var parts = buffer.split("\n\n");
          buffer = parts.pop();
          parts.forEach(function (p) {
            var line = p.replace(/^data: /, "").trim();
            if (!line) return;
            var evt;
            try { evt = JSON.parse(line); } catch (e) { return; }
            if (evt.type === "sources") sources = evt.sources || [];
            else if (evt.type === "token") {
              answer += evt.text;
              content.innerHTML = md(answer);
              msgs.scrollTop = msgs.scrollHeight;
            }
          });
          return pump();
        });
      }
      function finalize() {
        content.innerHTML = md(answer || "(no answer)");
        if (sources.length) botEl.appendChild(renderSources(sources));
        msgs.scrollTop = msgs.scrollHeight;
      }
      return pump();
    }).catch(function (err) {
      content.textContent = "Error: " + err.message;
    });
  }

  function renderSources(sources) {
    var d = document.createElement("div");
    d.className = "ka-src";
    var html = "<strong>Sources</strong><br>";
    sources.forEach(function (s) {
      var label = s.title || s.url || ("source " + s.n);
      html += "[" + s.n + "] " + (s.url
        ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(label) + "</a>"
        : esc(label)) + "<br>";
    });
    d.innerHTML = html;
    return d;
  }

  // ---------- helpers ----------
  function addUser(text) { return append("ka-user", esc(text)); }
  function addBot(markdown) {
    var m = document.createElement("div");
    m.className = "ka-msg ka-bot";
    m.innerHTML = '<div class="ka-content">' + md(markdown) + "</div>";
    msgs.appendChild(m);
    msgs.scrollTop = msgs.scrollHeight;
    return m;
  }
  function append(cls, html) {
    var m = document.createElement("div");
    m.className = "ka-msg " + cls;
    m.innerHTML = html;
    msgs.appendChild(m);
    msgs.scrollTop = msgs.scrollHeight;
    return m;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }
  function esc(s) {
    return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  // Tiny, safe-ish Markdown renderer (code fences, inline code, bold, headings,
  // links, breaks).
  function md(text) {
    if (!text) return "";
    var codeBlocks = [];
    text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, function (_, lang, code) {
      codeBlocks.push("<pre><code>" + esc(code) + "</code></pre>");
      return "\u0000CB" + (codeBlocks.length - 1) + "\u0000";
    });
    text = esc(text);
    text = text.replace(/`([^`]+)`/g, function (_, c) { return "<code>" + c + "</code>"; });
    text = text.replace(/^#{1,6}\s+(.+)$/gm, "<strong>$1</strong>");
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>');
    text = text.replace(/\n/g, "<br>");
    text = text.replace(/\u0000CB(\d+)\u0000/g, function (_, i) { return codeBlocks[i]; });
    return text;
  }
})();
