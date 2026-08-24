"""
main.py — FastAPI application for the ParcelPilot Internal Support Agent.

Endpoints:
  GET  /health   — Lightweight health check (no startup dependency)
  POST /chat    — SSE streaming chat with the agent
  POST /confirm — Execute or cancel a pending state-changing action
  GET  /proactive — Proactive issues sweep for the sidebar panel
  GET  /*       — Static files (frontend/dist)
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse


from backend.agent import run_agent
from backend.confirmation_gate import confirm as gate_confirm, cancel as gate_cancel
from backend.data_loader import load_data, DataStore
from backend.key_manager import key_pool
from backend.tools.data_lookup import lookup as data_lookup_fn
from backend.vector_store import init_vector_store, _get_model
from backend._showcase_html import get_showcase_html as _get_showcase_html


# Load .env if present (override=True so uploaded .env updates runtime env)
load_dotenv(override=True)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE         = Path(__file__).parent
_PROJECT_ROOT = _HERE.parent
SOURCES_DIR   = _PROJECT_ROOT / "sources"
XLSX_PATH     = SOURCES_DIR / "ParcelPilot_Assessment_Data.xlsx"
ESCALATIONS_PATH = _PROJECT_ROOT / "data" / "escalations.jsonl"


# ── Application state (populated at startup) ──────────────────────────────────
_collection: Any = None
_data_store: DataStore | None = None
pending_actions: dict[str, Any] = {}   # session_id → pending action payload

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="ParcelPilot Internal Support Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "null"],  # "null" covers file:// origin (local HTML files)
    allow_origin_regex=r".*",     # catch-all for any origin including file://
    allow_credentials=False,      # credentials=True is incompatible with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _async_init() -> None:
    global _collection, _data_store
    try:
        # Pre-warm embedding model in a thread (avoids httpx event-loop conflict)
        await asyncio.to_thread(_get_model)

        # Load structured data
        logger.info("Loading structured data from %s …", XLSX_PATH)
        _data_store = load_data(XLSX_PATH)
        logger.info(
            "DataStore ready: %d accounts, %d orders, %d tickets",
            len(_data_store.accounts),
            len(_data_store.orders),
            len(_data_store.tickets),
        )

        # Build vector store
        logger.info("Initialising vector store from %s …", SOURCES_DIR)
        _collection = init_vector_store(SOURCES_DIR)
        logger.info("Vector store ready: %d chunks", _collection.count())

        # Start background key health worker and initial non-blocking probe
        asyncio.create_task(key_pool.start_background_monitor(interval_seconds=30.0))
        asyncio.create_task(key_pool.check_all_keys_health())
    except Exception as e:
        logger.error("Async background initialization error: %s", e)


@app.on_event("startup")
async def startup() -> None:
    # Ensure escalations log file exists
    ESCALATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ESCALATIONS_PATH.exists():
        ESCALATIONS_PATH.touch()

    # Launch background state loader so server binds port and answers /health immediately
    asyncio.create_task(_async_init())




# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str
    role: str       # "support_agent" | "csm"
    user_name: str


class ConfirmRequest(BaseModel):
    session_id: str
    confirm: bool
    payload: dict | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat_endpoint(req: ChatRequest) -> EventSourceResponse:
    """Stream agent responses as SSE events."""
    assert _collection is not None, "Vector store not initialised"
    assert _data_store is not None, "DataStore not initialised"

    async def event_generator():
        async for event_str in run_agent(
            message=req.message,
            session_id=req.session_id,
            role=req.role,
            user_name=req.user_name,
            collection=_collection,
            data_store=_data_store,
            pending_actions=pending_actions,
        ):
            # event_str is already formatted as "event: X\ndata: {...}\n\n"
            # Parse and re-yield in sse_starlette format
            lines = event_str.strip().split("\n")
            event_type = "message"
            data_str = ""
            for line in lines:
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data_str = line[6:]
            yield {"event": event_type, "data": data_str}

    return EventSourceResponse(event_generator())


@app.post("/confirm")
async def confirm_endpoint(req: ConfirmRequest) -> dict:
    """Execute or cancel a pending state-changing action."""
    if req.confirm:
        if not req.payload:
            return {"status": "error", "message": "payload required when confirm=true"}
        result = gate_confirm(req.session_id, req.payload, pending_actions)
        return {"status": "created", "escalation_id": result["escalation_id"]}
    else:
        gate_cancel(req.session_id, pending_actions)
        return {"status": "cancelled"}


@app.get("/health")
async def health_endpoint() -> dict:
    """Lightweight health check — no dependency on startup state."""
    return {"status": "ok"}


@app.get("/keys/health")
@app.get("/api/keys")
async def keys_health_endpoint() -> dict:
    """Return real-time health status, load distribution, and cooldowns for all Groq API keys."""
    return key_pool.get_status_report()


@app.post("/keys/health/check")
async def keys_health_check_step_function() -> dict:
    """
    On-demand step function to immediately probe the health of all keys concurrently
    and return the updated health report.
    """
    check_results = await key_pool.check_all_keys_health()
    report = key_pool.get_status_report()
    report["check_results"] = check_results
    return report





@app.get("/proactive")
async def proactive_endpoint() -> dict:
    """Return the proactive issue sweep for the sidebar panel."""
    assert _data_store is not None, "DataStore not initialised"
    result = data_lookup_fn(
        query_type="proactive_sweep",
        filters={},
        current_user_role="support_agent",   # sweep is role-agnostic (no CSM-only fields in sweep)
        data_store=_data_store,
    )
    return {
        "items": result["results"],
        "snapshot_time": result["snapshot_time"],
    }


# ── Root / UI routes — always serve PRODUCT_SHOWCASE.html ────────────────────
# IMPORTANT: The HTML is patched at runtime in Python to fix the renderSidebar
# onclick bug (broken JSON.stringify interpolation), so this works regardless
# of which version of PRODUCT_SHOWCASE.html is baked into the container image.



def _load_patched_showcase() -> str:
    """Read PRODUCT_SHOWCASE.html and patch any broken onclick handlers."""
    showcase_path = _PROJECT_ROOT / "PRODUCT_SHOWCASE.html"
    if not showcase_path.exists():
        # Last-resort fallback: check frontend/dist
        for fallback in [
            _PROJECT_ROOT / "frontend" / "dist" / "index.html",
            _PROJECT_ROOT / "frontend" / "public" / "showcase.html",
        ]:
            if fallback.exists():
                showcase_path = fallback
                break
        else:
            return "<h1>ParcelPilot Agent</h1>"

    html = showcase_path.read_text(encoding="utf-8")

    # ── Patch 1: Fix broken sidebar onclick string-interpolation ──────────────
    # OLD (broken):  onclick="fill(${JSON.stringify(q)})"
    # NEW (safe):    data-q attribute + addEventListener in renderSidebar
    if 'onclick="fill(${JSON.stringify(q)})"' in html:
        # Replace the entire renderSidebar function with a safe DOM-based version
        old_fn = '''function renderSidebar(items, ts) {
  const sc = document.getElementById('sb-scroll');
  const ct = document.getElementById('sb-count');
  const ft = document.getElementById('sb-foot');
  ct.textContent = items.length || '0';
  if (ts) ft.textContent = 'Snapshot ' + ts.replace('T',' ').slice(0,16) + ' IST';
  if (!items.length) {
    sc.innerHTML = '<div style="padding:20px 6px;font-size:11px;color:#a8a29e;text-align:center">✓ No active issues</div>';
    return;
  }
  const grps = {};
  items.forEach(i => { (grps[i.category] = grps[i.category] || []).push(i); });
  let h = '';
  for (const [cat, arr] of Object.entries(grps)) {
    const c = CAT[cat] || { icon: '•', color: '#a8a29e' };
    h += `<div class="sb-group">
      <div class="sb-group-label" style="color:${c.color}">${c.icon}&ensp;${cat}</div>`;
    arr.forEach(it => {
      const q = it.suggested_query || `Tell me about ${it.ticket_ids.join(', ')}`;
      h += `<div class="sb-item" onclick="fill(${JSON.stringify(q)})">
        <div class="sb-item-id">${it.ticket_ids.join(', ')} — ${it.account_name}</div>
        <div class="sb-item-desc">${it.recommended_action}</div>
      </div>`;
    });
    h += '</div>';
  }
  sc.innerHTML = h;
}'''
        new_fn = '''function renderSidebar(items, ts) {
  const sc = document.getElementById('sb-scroll');
  const ct = document.getElementById('sb-count');
  const ft = document.getElementById('sb-foot');
  ct.textContent = items.length || '0';
  if (ts) ft.textContent = 'Snapshot ' + ts.replace('T',' ').slice(0,16) + ' IST';
  if (!items.length) {
    sc.innerHTML = '<div style="padding:20px 6px;font-size:11px;color:#a8a29e;text-align:center">\\u2713 No active issues</div>';
    return;
  }
  sc.innerHTML = '';
  const grps = {};
  items.forEach(i => { (grps[i.category] = grps[i.category] || []).push(i); });
  for (const [cat, arr] of Object.entries(grps)) {
    const c = CAT[cat] || { icon: '\\u2022', color: '#a8a29e' };
    const grpEl = document.createElement('div');
    grpEl.className = 'sb-group';
    const lbl = document.createElement('div');
    lbl.className = 'sb-group-label';
    lbl.style.color = c.color;
    lbl.textContent = c.icon + '\\u2002' + cat;
    grpEl.appendChild(lbl);
    arr.forEach(it => {
      const q = it.suggested_query || 'Tell me about ' + it.ticket_ids.join(', ');
      const itemEl = document.createElement('div');
      itemEl.className = 'sb-item';
      itemEl.style.cursor = 'pointer';
      const idDiv = document.createElement('div');
      idDiv.className = 'sb-item-id';
      idDiv.textContent = it.ticket_ids.join(', ') + ' \\u2014 ' + it.account_name;
      const descDiv = document.createElement('div');
      descDiv.className = 'sb-item-desc';
      descDiv.textContent = it.recommended_action;
      itemEl.appendChild(idDiv);
      itemEl.appendChild(descDiv);
      itemEl.addEventListener('click', function() { fill(q); });
      grpEl.appendChild(itemEl);
    });
    sc.appendChild(grpEl);
  }
}'''
        html = html.replace(old_fn, new_fn)
        logger.info("Patched renderSidebar onclick in served HTML")

    return html


@app.get("/")
async def root_ui():
    # Primary: serve from embedded Python constant (immune to file-cache issues)
    # Falls back to runtime file patch if constant unavailable
    try:
        return HTMLResponse(content=_get_showcase_html())
    except Exception:
        return HTMLResponse(content=_load_patched_showcase())


@app.get("/showcase")
async def showcase_patched():
    """Serve fixed PRODUCT_SHOWCASE.html (embedded as Python constant)."""
    try:
        return HTMLResponse(content=_get_showcase_html())
    except Exception:
        return HTMLResponse(content=_load_patched_showcase())
