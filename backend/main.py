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
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse


from backend.agent import run_agent
from backend.confirmation_gate import confirm as gate_confirm, cancel as gate_cancel
from backend.data_loader import load_data, DataStore
from backend.key_manager import key_pool
from backend.tools.data_lookup import lookup as data_lookup_fn
from backend.vector_store import init_vector_store


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


@app.on_event("startup")
async def startup() -> None:
    global _collection, _data_store

    # Ensure escalations log file exists
    ESCALATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ESCALATIONS_PATH.exists():
        ESCALATIONS_PATH.touch()

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



@app.get("/showcase")
async def showcase_endpoint():
    """Serve PRODUCT_SHOWCASE.html directly (avoids file:// CORS issues)."""
    from fastapi.responses import FileResponse
    showcase_path = _PROJECT_ROOT / "PRODUCT_SHOWCASE.html"
    if showcase_path.exists():
        return FileResponse(str(showcase_path), media_type="text/html")
    return {"error": "showcase not found"}


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
# We serve PRODUCT_SHOWCASE.html directly rather than mounting frontend/dist,
# so Railway always gets the latest file instead of a cached stale build artifact.

@app.get("/")
async def root_ui():
    showcase_path = _PROJECT_ROOT / "PRODUCT_SHOWCASE.html"
    if showcase_path.exists():
        return FileResponse(str(showcase_path), media_type="text/html")
    return {"status": "ok", "app": "ParcelPilot Agent Backend"}
