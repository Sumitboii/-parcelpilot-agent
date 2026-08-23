/**
 * sidebar.js — proactive issues panel logic
 */

'use strict';

const CATEGORY_CONFIG = {
  'SLA Breach':      { icon: '🚨', color: 'var(--color-red)' },
  'Approaching SLA': { icon: '⏰', color: 'var(--color-amber)' },
  'P1/P2 Open':      { icon: '🔴', color: 'var(--color-red)' },
  'Account Cluster': { icon: '👥', color: 'var(--color-purple)' },
  'KI-Linked':       { icon: '🐛', color: 'var(--color-amber)' },
};

/**
 * Load proactive data from the backend.
 * Falls back to demo data if the backend is unreachable.
 * @param {boolean} isLive
 */
async function loadSidebar(isLive) {
  if (!isLive) {
    renderSidebar(DEMO_SIDEBAR_ITEMS, DEMO_SNAPSHOT_TIME);
    return;
  }

  try {
    const res  = await fetchWithTimeout(Config.PROACTIVE_ENDPOINT, {}, Config.PROBE_TIMEOUT_MS);
    const data = await res.json();
    renderSidebar(data.items || [], data.snapshot_time || '');
  } catch (e) {
    renderSidebar(DEMO_SIDEBAR_ITEMS, DEMO_SNAPSHOT_TIME);
  }
}

/**
 * Render sidebar with grouped issue items.
 * @param {Array}  items
 * @param {string} snapshotTime  ISO-8601 string
 */
function renderSidebar(items, snapshotTime) {
  const scroll = document.getElementById('sidebar-scroll');
  const countEl= document.getElementById('sidebar-count');
  const footEl = document.getElementById('sidebar-footer');

  // Count badge
  countEl.textContent = items.length || '0';
  countEl.classList.toggle('empty', !items.length);

  // Footer timestamp
  if (snapshotTime) {
    const ts = snapshotTime.replace('T', ' ').slice(0, 16) + ' IST';
    footEl.textContent = 'Snapshot: ' + ts;
  }

  // Empty state
  if (!items.length) {
    scroll.innerHTML = '<div class="sidebar-empty">✓ No active issues</div>';
    return;
  }

  // Group by category (preserve insertion order)
  const groups = new Map();
  items.forEach(item => {
    if (!groups.has(item.category)) groups.set(item.category, []);
    groups.get(item.category).push(item);
  });

  let html = '';
  let groupIndex = 0;

  for (const [cat, catItems] of groups) {
    const cfg = CATEGORY_CONFIG[cat] || { icon: '•', color: 'var(--color-text-muted)' };

    html += `<div class="issue-group animate-slide delay-${Math.min(groupIndex + 1, 5)}">`;
    html += `<div class="issue-group-label" style="color:${cfg.color}">${cfg.icon}&ensp;${escHtml(cat)}</div>`;

    catItems.forEach(item => {
      const ids    = item.ticket_ids.join(', ');
      const name   = item.account_name;
      const query  = item.suggested_query || `Tell me about ${ids}`;

      html += `<div class="issue-item" data-query="${escAttr(query)}" role="button" tabindex="0"
        aria-label="Prefill query for ${escAttr(ids)}">
        <div class="issue-item-id">${escHtml(ids)} &mdash; ${escHtml(name)}</div>
        <div class="issue-item-desc">${escHtml(item.recommended_action)}</div>
      </div>`;
    });

    html += '</div>';
    groupIndex++;
  }

  scroll.innerHTML = html;

  // Attach click & keyboard handlers
  scroll.querySelectorAll('.issue-item').forEach(el => {
    const q = el.dataset.query;
    el.addEventListener('click', () => prefillInput(q));
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); prefillInput(q); }
    });
  });
}
