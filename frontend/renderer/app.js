/**
 * E.V.A. Renderer / Frontend Logic
 *
 * Connects to the Python backend via WebSocket and drives:
 *  - State transitions (idle / listening / thinking / speaking)
 *  - Conversation transcript rendering
 *  - Webview URL loading from agent browse commands
 *  - Animated waveform
 *  - Text-input override
 */

(function () {
  "use strict";

  const WS_URL = "ws://localhost:8765";
  const RECONNECT_DELAY_MS = 2000;

  // ── DOM refs ──────────────────────────────────────────────────────────
  const messagesEl    = document.getElementById("messages");
  const textInput     = document.getElementById("text-input");
  const btnSend       = document.getElementById("btn-send");
  const btnClear      = document.getElementById("btn-clear");
  const statusLabel   = document.getElementById("status-label");
  const statusDot     = document.getElementById("status-dot");
  const urlBar        = document.getElementById("url-bar");
  const btnGo         = document.getElementById("btn-go");
  const webview       = document.getElementById("webview");
  const activityList  = document.getElementById("activity-list");
  const waveCanvas    = document.getElementById("waveform");
  const waveCtx       = waveCanvas.getContext("2d");
  const btnPin        = document.getElementById("btn-pin");
  const btnMin        = document.getElementById("btn-min");
  const btnClose      = document.getElementById("btn-close");

  // ── State ─────────────────────────────────────────────────────────────
  let ws = null;
  let currentState = "idle";
  let waveAnimId = null;
  let wavePhase = 0;

  // ── WebSocket ─────────────────────────────────────────────────────────

  function connect() {
    ws = new WebSocket(WS_URL);

    ws.addEventListener("open", () => {
      console.log("[EVA] Connected to backend");
      setStatus("connected");
    });

    ws.addEventListener("message", (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      handleBackendMessage(msg);
    });

    ws.addEventListener("close", () => {
      console.warn("[EVA] WebSocket closed – reconnecting in", RECONNECT_DELAY_MS, "ms");
      setStatus("disconnected");
      setTimeout(connect, RECONNECT_DELAY_MS);
    });

    ws.addEventListener("error", (err) => {
      console.error("[EVA] WebSocket error", err);
    });
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  // ── Message handler ───────────────────────────────────────────────────

  function handleBackendMessage(msg) {
    switch (msg.type) {
      case "state":
        setStatus(msg.value);
        break;

      case "transcript":
        appendMessage(msg.role === "user" ? "user" : "assistant", msg.text);
        break;

      case "load_url":
        navigateTo(msg.url);
        break;

      case "tool_call":
        addActivity(msg.name, msg.args);
        break;

      case "pong":
        break;

      default:
        console.debug("[EVA] Unknown message type:", msg.type);
    }
  }

  // ── Status / state ────────────────────────────────────────────────────

  const STATE_LABELS = {
    idle:         "IDLE",
    listening:    "LISTENING",
    thinking:     "PROCESSING",
    speaking:     "SPEAKING",
    connected:    "CONNECTED",
    disconnected: "OFFLINE",
  };

  function setStatus(state) {
    currentState = state;
    statusLabel.textContent = STATE_LABELS[state] || state.toUpperCase();

    // Update dot class
    statusDot.className = "dot";
    if (["listening", "thinking", "speaking"].includes(state)) {
      statusDot.classList.add(state);
    } else if (state === "idle" || state === "connected") {
      statusDot.classList.add("idle");
    }

    // Waveform animation
    if (state === "listening" || state === "speaking") {
      startWaveform();
    } else {
      stopWaveform();
    }
  }

  // ── Messages ──────────────────────────────────────────────────────────

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.classList.add("message", role === "user" ? "user" : "assistant");
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  btnClear.addEventListener("click", () => {
    messagesEl.innerHTML = "";
  });

  // ── Text input ────────────────────────────────────────────────────────

  function submitText() {
    const text = textInput.value.trim();
    if (!text) return;
    send({ type: "text_input", text });
    textInput.value = "";
  }

  btnSend.addEventListener("click", submitText);
  textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitText();
  });

  // ── Browser / webview ─────────────────────────────────────────────────

  /**
   * Validate that a URL uses only http: or https: before loading it.
   * This prevents javascript:, data:, and other dangerous schemes from being
   * loaded into the webview.
   */
  function isSafeUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === "https:" || parsed.protocol === "http:";
    } catch {
      return false;
    }
  }

  function navigateTo(url) {
    if (!isSafeUrl(url)) {
      console.warn("[EVA] Blocked unsafe URL:", url);
      return;
    }
    urlBar.value = url;
    webview.src = url;
  }

  btnGo.addEventListener("click", () => {
    let url = urlBar.value.trim();
    if (!url.startsWith("http")) url = "https://" + url;
    navigateTo(url);
  });

  urlBar.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      let url = urlBar.value.trim();
      if (!url.startsWith("http")) url = "https://" + url;
      navigateTo(url);
    }
  });

  // ── Activity feed ─────────────────────────────────────────────────────

  function addActivity(toolName, args) {
    const li = document.createElement("li");
    const nameSpan = document.createElement("span");
    nameSpan.className = "tool-name";
    nameSpan.textContent = toolName;
    li.appendChild(nameSpan);

    const argsStr = Object.entries(args || {})
      .map(([k, v]) => `${k}: ${JSON.stringify(v).slice(0, 40)}`)
      .join("\n");
    if (argsStr) {
      const argsNode = document.createTextNode(argsStr);
      li.appendChild(argsNode);
    }

    activityList.prepend(li);

    // Keep max 30 items
    while (activityList.children.length > 30) {
      activityList.removeChild(activityList.lastChild);
    }
  }

  // ── Waveform animation ────────────────────────────────────────────────

  const WAVE_COLORS = {
    listening: "#ffb347",
    speaking:  "#00c8ff",
  };

  function drawWaveframe() {
    const w = waveCanvas.width;
    const h = waveCanvas.height;
    const amplitude = currentState === "listening" ? 14 : 10;
    const color = WAVE_COLORS[currentState] || "#00c8ff";

    waveCtx.clearRect(0, 0, w, h);
    waveCtx.beginPath();
    waveCtx.strokeStyle = color;
    waveCtx.lineWidth = 1.5;
    waveCtx.shadowColor = color;
    waveCtx.shadowBlur = 6;

    for (let x = 0; x <= w; x++) {
      const t = (x / w) * Math.PI * 6 + wavePhase;
      const y = h / 2 + Math.sin(t) * amplitude * Math.sin((x / w) * Math.PI);
      if (x === 0) waveCtx.moveTo(x, y);
      else waveCtx.lineTo(x, y);
    }

    waveCtx.stroke();
    wavePhase += 0.12;
  }

  function startWaveform() {
    if (waveAnimId) return;

    function frame() {
      drawWaveframe();
      waveAnimId = requestAnimationFrame(frame);
    }
    waveAnimId = requestAnimationFrame(frame);
  }

  function stopWaveform() {
    if (waveAnimId) {
      cancelAnimationFrame(waveAnimId);
      waveAnimId = null;
    }
    waveCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);

    // Draw flat idle line
    waveCtx.beginPath();
    waveCtx.strokeStyle = "rgba(0,200,255,0.2)";
    waveCtx.lineWidth = 1;
    waveCtx.moveTo(0, waveCanvas.height / 2);
    waveCtx.lineTo(waveCanvas.width, waveCanvas.height / 2);
    waveCtx.stroke();
  }

  // ── Window controls ───────────────────────────────────────────────────

  if (window.eva) {
    btnPin.addEventListener("click", async () => {
      const pinned = await window.eva.toggleAlwaysOnTop();
      btnPin.style.color = pinned ? "#00c8ff" : "";
    });

    btnMin.addEventListener("click", () => window.eva.minimize());
    btnClose.addEventListener("click", () => window.eva.close());
  }

  // ── Init ──────────────────────────────────────────────────────────────

  stopWaveform(); // draw idle line on start
  connect();

})();
