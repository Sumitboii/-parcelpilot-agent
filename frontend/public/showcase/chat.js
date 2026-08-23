/**
 * chat.js — message rendering, SSE stream handling, confirmation card
 */

'use strict';

/* ── DOM refs (cached once) ─────────────────── */
const MsgList   = () => document.getElementById('message-list');
const Thinking  = () => document.getElementById('thinking');
const EmptyEl   = () => document.getElementById('empty-state');

/* ────────────────────────────────────────────
   TEXT FORMATTING
   ──────────────────────────────────────────── */

/**
 * Convert plain-text agent response to safe HTML with:
 *   **bold**, [doc citations], [table: key] citations, newlines → <p>
 */
function formatAgentText(raw) {
  let s = escHtml(raw);

  // **bold**
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // [filename.pdf, p.N §M] → citation span
  s = s.replace(
    /\[([^\]]+?\.pdf[^\]]*)\]/gi,
    '<span class="citation" title="$1">$1</span>'
  );

  // [table: key] → citation span
  s = s.replace(
    /\[(accounts|orders|tickets):\s*([^\]]+)\]/gi,
    '<span class="citation" title="$1: $2">$1: $2</span>'
  );

  // paragraph breaks
  s = s.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');

  return '<p>' + s + '</p>';
}

/* ────────────────────────────────────────────
   MESSAGE INSERTION HELPERS
   ──────────────────────────────────────────── */

/** Remove the empty-state placeholder if present */
function removeEmpty() {
  const e = EmptyEl();
  if (e) e.remove();
}

/** Scroll the message list to the bottom */
function scrollBottom() {
  const el = MsgList();
  requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

/**
 * Add a user or assistant message bubble.
 * Returns the bubble element so tokens can be appended incrementally.
 */
function addBubble(side, cssModifier) {
  removeEmpty();
  const list = MsgList();
  const row  = document.createElement('div');
  row.className = `msg-row msg-row--${side}`;

  const bubble = document.createElement('div');
  bubble.className = `bubble bubble--${cssModifier || side} animate-msg`;
  row.appendChild(bubble);
  list.appendChild(row);
  scrollBottom();
  return bubble;
}

/**
 * Add a row of tool-use chips above the answer.
 * Returns the row element so chips can be appended one by one.
 */
function addToolRow() {
  removeEmpty();
  const list = MsgList();
  const row  = document.createElement('div');
  row.className = 'tool-chip-row';
  list.appendChild(row);
  scrollBottom();
  return row;
}

/**
 * Append a single tool chip to an existing tool row.
 */
function appendToolChip(row, toolName) {
  const ICONS = { document_search: '🔍', data_lookup: '📊', escalate: '⚡' };
  const chip  = document.createElement('span');
  chip.className = 'tool-chip tool-chip--active';
  chip.innerHTML = `<span class="tool-chip__icon">${ICONS[toolName] || '🔧'}</span>${escHtml(toolName)}`;
  row.appendChild(chip);
  scrollBottom();
}

/**
 * Insert a confirmation card (not a bubble) into the message list.
 */
function addConfirmCard(display, payload, isLive) {
  removeEmpty();
  const list = MsgList();
  const wrap = document.createElement('div');
  wrap.className = 'confirm-wrap animate-card';

  /* ── Build fields HTML ── */
  let fieldsHtml = '';
  for (const [k, v] of Object.entries(display || {})) {
    fieldsHtml += `
      <div class="confirm-card__row">
        <span class="confirm-card__key">${escHtml(k)}</span>
        <span class="confirm-card__val">${escHtml(String(v ?? ''))}</span>
      </div>`;
  }

  wrap.innerHTML = `
    <div class="confirm-card">
      <div class="confirm-card__label">⚡ Confirm Action</div>
      <div class="confirm-card__fields">${fieldsHtml}</div>
      <div class="confirm-card__btns">
        <button class="btn-confirm"        id="cc-ok">Confirm</button>
        <button class="btn-cancel-confirm" id="cc-cancel">Cancel</button>
      </div>
      <div class="confirm-card__result" id="cc-result"></div>
    </div>`;

  list.appendChild(wrap);
  scrollBottom();

  /* ── Wire buttons ── */
  const ok     = wrap.querySelector('#cc-ok');
  const cancel = wrap.querySelector('#cc-cancel');
  const result = wrap.querySelector('#cc-result');

  ok.addEventListener('click', async () => {
    ok.disabled = cancel.disabled = true;
    ok.textContent = 'Creating…';

    if (isLive) {
      try {
        const res  = await fetch(Config.CONFIRM_ENDPOINT, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ session_id: AppState.sessionId, confirm: true, payload }),
        });
        const data = await res.json();
        showResult(result, 'ok',
          '✓ Escalation created: ' + (data.escalation_id || 'ESC-' + Date.now()));
        ok.textContent = '✓ Confirmed';
      } catch (err) {
        ok.disabled = cancel.disabled = false;
        ok.textContent = 'Confirm';
        showResult(result, 'error', '✗ Error: ' + err.message);
      }
    } else {
      // Demo mode — simulate success
      showResult(result, 'ok', '✓ Escalation created: ESC-20260816-0001 (demo)');
      ok.textContent = '✓ Confirmed';
    }
  });

  cancel.addEventListener('click', async () => {
    ok.disabled = cancel.disabled = true;
    if (isLive) {
      await fetch(Config.CONFIRM_ENDPOINT, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ session_id: AppState.sessionId, confirm: false }),
      }).catch(() => {});
    }
    showResult(result, 'cancel', 'Action cancelled.');
    cancel.textContent = 'Cancelled';
  });
}

function showResult(el, type, text) {
  el.textContent = text;
  el.className   = `confirm-card__result visible confirm-card__result--${type}`;
}

/* ────────────────────────────────────────────
   LIVE SSE STREAM
   ──────────────────────────────────────────── */

/**
 * Send a message to the live backend and stream the SSE response.
 * @param {string} query
 */
async function streamLive(query) {
  let toolRow      = null;
  let assistBubble = null;
  let assistText   = '';

  try {
    const res = await fetchWithTimeout(Config.CHAT_ENDPOINT, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        message:    query,
        session_id: AppState.sessionId,
        role:       AppState.role,
        user_name:  AppState.userName,
      }),
    }, Config.STREAM_TIMEOUT_MS);

    if (!res.ok) {
      addBubble('assistant', 'error').innerHTML =
        `<p>⚠ Backend returned HTTP ${res.status}</p>`;
      return;
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    outer: while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        let evtType = 'message';
        let dataStr = '';

        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) evtType = line.slice(7).trim();
          else if (line.startsWith('data: '))  dataStr = line.slice(6);
        }

        let data = {};
        try { data = JSON.parse(dataStr); } catch {}

        switch (evtType) {
          case 'tool_chip':
            if (!toolRow) toolRow = addToolRow();
            appendToolChip(toolRow, data.tool || dataStr);
            break;

          case 'token':
            if (!assistBubble) assistBubble = addBubble('assistant', 'assistant');
            assistText += (data.text || '');
            assistBubble.innerHTML = formatAgentText(assistText);
            scrollBottom();
            break;

          case 'pending_confirmation':
            addConfirmCard(data.display || {}, data.payload || data, true);
            break;

          case 'error':
            addBubble('assistant', 'error').innerHTML =
              '<p>⚠ ' + escHtml(data.message || dataStr) + '</p>';
            break;

          case 'done':
            break outer;
        }
      }
    }

  } catch (err) {
    // Network error — fall back to demo
    AppState.liveMode = false;
    setConnectionStatus(false);
    document.getElementById('demo-banner').classList.add('visible');
    await streamDemo(query);
  }
}

/* ────────────────────────────────────────────
   DEMO STREAM
   ──────────────────────────────────────────── */

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Play back a demo scenario generator with simulated streaming.
 * @param {string} query
 */
async function streamDemo(query) {
  const key = matchDemoScenario(query);
  const gen = DEMO_RESPONSES[key](query);

  let toolRow      = null;
  let assistBubble = null;

  for await (const ev of gen) {
    switch (ev.type) {

      case 'tool': {
        if (!toolRow) toolRow = addToolRow();
        appendToolChip(toolRow, ev.name);
        await sleep(260);
        break;
      }

      case 'text': {
        assistBubble = addBubble('assistant', 'assistant');
        const words  = ev.content.split(' ');
        let   acc    = '';
        for (let i = 0; i < words.length; i++) {
          acc += words[i] + (i < words.length - 1 ? ' ' : '');
          assistBubble.innerHTML = formatAgentText(acc);
          scrollBottom();
          await sleep(16);
        }
        break;
      }

      case 'confirm': {
        addConfirmCard(ev.display, ev.payload, false);
        break;
      }
    }
  }
}

/* ────────────────────────────────────────────
   MAIN SEND ENTRY POINT
   ──────────────────────────────────────────── */

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const query = input.value.trim();
  if (!query || AppState.busy) return;

  input.value = '';
  resizeTextarea(input);
  setBusy(true);

  // Render user bubble
  addBubble('user', 'user').innerHTML = '<p>' + escHtml(query) + '</p>';

  // Stream response
  if (AppState.liveMode) {
    await streamLive(query);
  } else {
    await streamDemo(query);
  }

  setBusy(false);
}
