/**
 * config.js — runtime configuration
 *
 * Auto-detects the backend URL based on where the page is being served from:
 *   - localhost / 127.0.0.1   → local FastAPI on port 8000
 *   - railway.app domain       → same origin (FastAPI serves the HTML)
 *   - file:// (opened locally) → Railway production
 */

'use strict';

const Config = (() => {
  const h = window.location.hostname;

  let backend;
  if (h === 'localhost' || h === '127.0.0.1') {
    backend = 'http://localhost:8000';
  } else if (h.includes('railway.app') || h.includes('render.com')) {
    backend = window.location.origin;
  } else {
    // Opened as a local file — always point to Railway prod
    backend = 'https://parcelpilot-agent-production.up.railway.app';
  }

  return Object.freeze({
    BACKEND_URL: backend,
    CHAT_ENDPOINT:      backend + '/chat',
    CONFIRM_ENDPOINT:   backend + '/confirm',
    PROACTIVE_ENDPOINT: backend + '/proactive',
    PROBE_TIMEOUT_MS:   3500,
    STREAM_TIMEOUT_MS:  30000,
  });
})();
