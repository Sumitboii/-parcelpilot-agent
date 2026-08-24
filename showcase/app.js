/**
 * app.js — application bootstrap, state, shared utilities
 * Loaded last so it can reference functions from all other scripts.
 */

'use strict';

/* ────────────────────────────────────────────
   APPLICATION STATE
   ──────────────────────────────────────────── */
const AppState = {
  sessionId: generateUUID(),
  role:      'support_agent',
  userName:  'Rohit',
  liveMode:  false,
  busy:      false,
};

/* ────────────────────────────────────────────
   UTILITIES (shared across all modules)
   ──────────────────────────────────────────── */

/** Escape HTML special characters */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Escape for use in HTML attribute values */
function escAttr(str) {
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** fetch with a timeout, rejects with AbortError on expiry */
function fetchWithTimeout(url, opts, ms) {
  const ctrl = new AbortController();
  const tid  = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { ...opts, signal: ctrl.signal })
    .finally(() => clearTimeout(tid));
}

/** RFC-4122 v4 UUID */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 3) | 8).toString(16);
  });
}

/** Prefill the chat input and auto-send query */
function prefillInput(text, autoSend = true) {
  const el = document.getElementById('msg-input');
  el.value = text;
  resizeTextarea(el);
  if (autoSend && typeof sendMessage === 'function' && !AppState.busy) {
    sendMessage();
  } else {
    el.focus();
  }
}

// Alias used by suggestion chips in HTML
function prefill(text) { prefillInput(text, true); }


/** Auto-resize textarea height */
function resizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 110) + 'px';
}

/** Show / hide busy state (disables input + send, shows thinking dots) */
function setBusy(on) {
  AppState.busy = on;
  const btn     = document.getElementById('send-btn');
  const inp     = document.getElementById('msg-input');
  const think   = document.getElementById('thinking');

  btn.disabled  = on;
  inp.disabled  = on;
  think.classList.toggle('visible', on);
}

/** Toast notification */
function showToast(msg, durationMs = 2400) {
  const el  = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), durationMs);
}

/** Update the connection status indicator in the topbar */
function setConnectionStatus(online) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  dot.classList.toggle('online', online);
  text.textContent = online ? 'Connected' : 'Demo mode';
}

/* ────────────────────────────────────────────
   ROLE CHANGE
   ──────────────────────────────────────────── */
function changeRole(value) {
  const [role, ...nameParts] = value.split('|');
  AppState.role      = role;
  AppState.userName  = nameParts.join('|');
  AppState.sessionId = generateUUID();

  // Reset message list to empty state
  const list = document.getElementById('message-list');
  list.innerHTML = `
    <div id="empty-state">
      <div class="empty-glyph">◎</div>
      <h2 class="empty-title">Ask anything about ParcelPilot</h2>
      <p class="empty-sub">Policies, orders, tickets, and contracts — every answer cited to the exact source and page.</p>
      <div class="suggestion-row" id="suggestion-row">
        <button class="suggestion-chip" onclick="prefill('Can Northstar cancel ORD-1001 without a fee?')">Northstar cancellation</button>
        <button class="suggestion-chip" onclick="prefill('What should I do about TKT-505?')">TKT-505 API key</button>
        <button class="suggestion-chip" onclick="prefill('Is ORD-2002 eligible for a service credit?')">LumenWorks credit</button>
        <button class="suggestion-chip" onclick="prefill('LumenWorks 4200-row CSV fails to upload')">Bulk upload limit</button>
        <button class="suggestion-chip" onclick="prefill('TKT-504 shows BOOKED but driver already picked up')">SwiftShip delay</button>
      </div>
    </div>`;

  showToast('Signed in as ' + AppState.userName);
}

/* ────────────────────────────────────────────
   INPUT HANDLERS
   ──────────────────────────────────────────── */
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

/* ────────────────────────────────────────────
   BOOT
   ──────────────────────────────────────────── */
async function boot() {
  // Probe backend
  try {
    const res = await fetchWithTimeout(Config.PROACTIVE_ENDPOINT, {}, Config.PROBE_TIMEOUT_MS);
    if (res.ok) {
      AppState.liveMode = true;
      setConnectionStatus(true);
      document.getElementById('demo-banner').classList.remove('visible');
      const data = await res.json();
      renderSidebar(data.items || [], data.snapshot_time || '');
      return;
    }
  } catch (_) {}

  // Backend unreachable → demo mode
  setConnectionStatus(false);
  document.getElementById('demo-banner').classList.add('visible');
  renderSidebar(DEMO_SIDEBAR_ITEMS, DEMO_SNAPSHOT_TIME);
}

/* ── Wire up input events on DOMContentLoaded ── */
document.addEventListener('DOMContentLoaded', () => {
  const inp  = document.getElementById('msg-input');
  const btn  = document.getElementById('send-btn');
  const role = document.getElementById('role-select');

  inp.addEventListener('keydown',  handleKey);
  inp.addEventListener('input',    () => resizeTextarea(inp));
  btn.addEventListener('click',    sendMessage);
  role.addEventListener('change',  e => changeRole(e.target.value));

  inp.focus();
  boot();
});
