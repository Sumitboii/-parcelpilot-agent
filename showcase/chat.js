/**
 * chat.js — message rendering, SSE stream handling, confirmation card
 */

'use strict';

/* ── DOM refs (cached once) ─────────────────── */
const MsgList   = () => document.getElementById('message-list');
const Thinking  = () => document.getElementById('thinking');
const EmptyEl   = () => document.getElementById('empty-state');

function escHtml(s) {
  return String(s || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function fmtInlineText(s) {
  // 1. Bracketed Citations with 【 ... 】 -> [ ... ]
  s = s.replace(/【(.*?)】/g, '[$1]');
  
  // 2. Structured data citations [table: key]
  s = s.replace(/\[(orders|accounts|tickets|credit_calc|sla_check):\s*([^\]]+)\]/gi, '<span class="citation" title="$1: $2">$1: $2</span>');
  
  // 3. Bracketed PDF citations [01_Support_Policy_v3_CURRENT.pdf, p.1]
  s = s.replace(/\[([a-zA-Z0-9_\-]+\.pdf[^\]]*)\]/gi, '<span class="citation" title="$1">$1</span>');
  
  // 4. Unbracketed PDF citations
  s = s.replace(/(?<!["'>\w])(\b\d{2}_[a-zA-Z0-9_\-]+\.pdf(?:,?\s*(?:p(?:age|\.)?\s*\d+|§\s*\d+[^,;\n<)]*))?)/gi, (match, cit) => {
    if (!cit || cit.includes('<span')) return match;
    return `<span class="citation" title="${cit.trim()}">${cit.trim()}</span>`;
  });

  // 5. Bold **text**
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // 6. Italic *text* or _text_
  s = s.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
  
  // 7. Inline code `code`
  s = s.replace(/`([^`]+)`/g, '<code class="prose-code">$1</code>');
  
  // 8. Entity tags: TKT-505, ACCT-004, ORD-1001, KI-208
  s = s.replace(/\b(TKT-\d+|ACCT-\d+|ORD-\d+|KI-\d+)\b/g, '<span class="badge-code">$1</span>');
  
  return s;
}

function formatAgentText(raw) {
  if (!raw) return '';
  raw = raw.replace(/\u202f/g, ' ').replace(/\u00a0/g, ' ').replace(/\u2011/g, '-');
  const lines = raw.split(/\r?\n/);
  const out = [];
  
  let inTable = false;
  let tableRows = [];
  let inUl = false;
  let inOl = false;
  let inQuote = false;
  let quoteLines = [];
  
  function flushTable() {
    if (!inTable || tableRows.length === 0) { inTable = false; return; }
    let html = '<div class="table-wrap"><table class="prose-table">';
    let bodyRows = tableRows;
    if (tableRows.length >= 2 && /^\s*\|?\s*[-:]+[-| :]*\|?\s*$/.test(tableRows[1])) {
      const headers = tableRows[0].replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      html += '<thead><tr>' + headers.map(h => `<th>${fmtInlineText(escHtml(h))}</th>`).join('') + '</tr></thead>';
      bodyRows = tableRows.slice(2);
    }
    html += '<tbody>';
    for (const r of bodyRows) {
      const cells = r.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      html += '<tr>' + cells.map(c => `<td>${fmtInlineText(escHtml(c))}</td>`).join('') + '</tr>';
    }
    html += '</tbody></table></div>';
    out.push(html);
    tableRows = [];
    inTable = false;
  }
  
  function flushList() {
    if (inUl) { out.push('</ul>'); inUl = false; }
    if (inOl) { out.push('</ol>'); inOl = false; }
  }
  
  function flushQuote() {
    if (inQuote) {
      out.push(`<blockquote class="prose-quote">${fmtInlineText(escHtml(quoteLines.join(' ')))}</blockquote>`);
      inQuote = false;
      quoteLines = [];
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();
    
    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushTable(); flushList(); flushQuote();
      out.push('<hr class="prose-hr"/>');
      continue;
    }
    
    if (trimmed.includes('|') && (trimmed.startsWith('|') || /\w+\s*\|/.test(trimmed))) {
      flushList(); flushQuote();
      inTable = true;
      tableRows.push(trimmed);
      continue;
    } else if (inTable) {
      flushTable();
    }
    
    if (trimmed.startsWith('>')) {
      flushTable(); flushList();
      inQuote = true;
      quoteLines.push(trimmed.replace(/^>\s*/, ''));
      continue;
    } else if (inQuote) {
      flushQuote();
    }
    
    const hMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (hMatch) {
      flushTable(); flushList(); flushQuote();
      const lvl = Math.min(hMatch[1].length + 2, 6);
      out.push(`<h${lvl} class="prose-h">${fmtInlineText(escHtml(hMatch[2]))}</h${lvl}>`);
      continue;
    }
    
    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (olMatch) {
      flushTable();
      if (inUl) flushList();
      if (!inOl) { out.push('<ol class="prose-ol">'); inOl = true; }
      out.push(`<li>${fmtInlineText(escHtml(olMatch[2]))}</li>`);
      continue;
    }
    
    const ulMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    if (ulMatch) {
      flushTable();
      if (inOl) flushList();
      if (!inUl) { out.push('<ul class="prose-ul">'); inUl = true; }
      out.push(`<li>${fmtInlineText(escHtml(ulMatch[1]))}</li>`);
      continue;
    }
    
    if (!trimmed) {
      flushTable(); flushList(); flushQuote();
      continue;
    }
    
    flushTable(); flushList(); flushQuote();
    out.push(`<p class="prose-p">${fmtInlineText(escHtml(trimmed))}</p>`);
  }
  
  flushTable(); flushList(); flushQuote();
  return out.join('');
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
    renderNextQueryOptions(query);

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
  renderNextQueryOptions(query);
}

function renderNextQueryOptions(lastQuery) {
  const lq = (lastQuery || '').toLowerCase();
  let suggestions = [];
  
  if (lq.includes('northstar') || lq.includes('ord-1001') || lq.includes('cancel')) {
    suggestions = [
      { primary: true, label: '⚡ Next: Investigate TKT-505 API Key Exposure (P1)', q: 'What should I do about TKT-505?' },
      { primary: false, label: '💰 Next: Calculate ORD-2002 Service Credit', q: 'Is ORD-2002 eligible for a service credit?' },
      { primary: false, label: '⏱️ Next: What are Northstar Agreement SLAs?', q: 'What are Northstar Logistics SLA terms in their agreement?' }
    ];
  } else if (lq.includes('tkt-505') || lq.includes('api key') || lq.includes('credential') || lq.includes('axis')) {
    suggestions = [
      { primary: true, label: '⚡ Next: Escalate TKT-505 Immediately (P1)', q: 'Please escalate ticket TKT-505 immediately as a P1 incident.' },
      { primary: false, label: '🐛 Next: Check LumenWorks Bulk CSV Upload Bug', q: 'LumenWorks 4200-row CSV fails to upload' },
      { primary: false, label: '📋 Next: What is Axis Labs SLA Policy?', q: 'What is the P1 response SLA for Axis Labs (ACCT-004)?' }
    ];
  } else if (lq.includes('lumenworks') || lq.includes('ord-2002') || lq.includes('credit')) {
    suggestions = [
      { primary: true, label: '🚚 Next: Check SwiftShip Webhook Delay (TKT-504)', q: 'TKT-504 shows BOOKED but driver already picked up' },
      { primary: false, label: '🚨 Next: Run Proactive Issue Sweep', q: 'Run a proactive sweep of all open tickets and SLA breaches.' },
      { primary: false, label: '💰 Next: Calculate Service Credit on INR 15,000 Order', q: 'Calculate service credit for a 6-hour delay on a 15000 INR shipment for Beacon Retail.' }
    ];
  } else if (lq.includes('bulk') || lq.includes('csv') || lq.includes('upload') || lq.includes('ki-208')) {
    suggestions = [
      { primary: true, label: '🚚 Next: Check SwiftShip Webhook Delay (TKT-504)', q: 'TKT-504 shows BOOKED but driver already picked up' },
      { primary: false, label: '📋 Next: Can Northstar Cancel ORD-1001 Without Fee?', q: 'Can Northstar cancel ORD-1001 without a fee?' },
      { primary: false, label: '📄 Next: Check Support Policy v2 Deprecation', q: 'What does Support Policy v2 say about standard cancellation fees?' }
    ];
  } else if (lq.includes('swiftship') || lq.includes('tkt-504') || lq.includes('ki-211')) {
    suggestions = [
      { primary: true, label: '🚨 Next: Check Axis Labs P1 SLA Breach (TKT-505)', q: 'What should I do about TKT-505?' },
      { primary: false, label: '🔒 Next: Check Account RBAC Access (ACCT-001)', q: 'Show me the account profile for ACCT-001' },
      { primary: false, label: '📄 Next: Check Support Policy v2 Deprecation', q: 'What does Support Policy v2 say about standard cancellation fees?' }
    ];
  } else {
    suggestions = [
      { primary: true, label: '📋 Next: Can Northstar cancel ORD-1001 without fee?', q: 'Can Northstar cancel ORD-1001 without a fee?' },
      { primary: false, label: '🚨 Next: What should I do about TKT-505?', q: 'What should I do about TKT-505?' },
      { primary: false, label: '💰 Next: Is ORD-2002 eligible for a service credit?', q: 'Is ORD-2002 eligible for a service credit?' }
    ];
  }

  // Remove old next query containers
  document.querySelectorAll('.next-query-wrap').forEach(w => w.remove());

  const list = MsgList();
  const wrap = document.createElement('div');
  wrap.className = 'next-query-wrap';
  
  const title = document.createElement('div');
  title.className = 'next-query-title';
  title.textContent = '👉 Next Query to Solve (Click button to run):';
  wrap.appendChild(title);

  const chipsContainer = document.createElement('div');
  chipsContainer.className = 'next-query-chips';

  suggestions.forEach(s => {
    const btn = document.createElement('button');
    btn.className = `next-chip ${s.primary ? 'primary' : ''}`;
    btn.textContent = s.label;
    btn.addEventListener('click', () => runDirectly(s.q));
    chipsContainer.appendChild(btn);
  });

  wrap.appendChild(chipsContainer);
  list.appendChild(wrap);
  scrollBottom();
}


function runDirectly(q) {
  if (AppState.busy) return;
  const el = document.getElementById('msg-input');
  if (el) el.value = q;
  sendMessage();
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
