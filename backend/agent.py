"""
agent.py — Hand-rolled tool-router loop for the ParcelPilot Internal Support Agent.

No LangChain, no agent framework. This is a plain Python async generator that:
  1. Sends the user message + tool schemas to Groq
  2. Dispatches each tool_call to the matching Python function
  3. Streams SSE events back to the frontend
  4. Routes 'escalate' calls through the confirmation gate (never executes directly)

Model: openai/gpt-oss-120b (primary), openai/gpt-oss-20b (rate-limit fallback)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator

import chromadb
from groq import AsyncGroq, RateLimitError

from backend.confirmation_gate import intercept as gate_intercept
from backend.data_loader import DataStore, SNAPSHOT_TIME
from backend.tools.data_lookup import lookup as data_lookup_fn
from backend.tools.document_search import search as doc_search_fn

logger = logging.getLogger(__name__)

from backend.key_manager import key_pool, KeyHealthInfo

# ── Model config ──────────────────────────────────────────────────────────────
PRIMARY_MODEL  = "openai/gpt-oss-20b"    # Fast model available on this Groq account
FALLBACK_MODEL = "openai/gpt-oss-120b"   # Heavy fallback model

# ── API Key Pool & Dynamic Key Rotator (backed by key_manager) ────────────────
def _get_all_groq_keys() -> list[str]:
    """Retrieve all distinct valid Groq API keys from environment."""
    return [k.api_key for k in key_pool._keys]

def get_current_client() -> tuple[AsyncGroq, str]:
    """Return an active healthy AsyncGroq client and its masked key identifier."""
    client, info = key_pool.get_healthy_client()
    return client, f"key #{info.key_index} ({info.masked_key})"

def rotate_to_next_key() -> tuple[AsyncGroq, str]:
    """Rotate to the next API key in the pool."""
    client, info = key_pool.get_healthy_client()
    logger.warning("🔄 Groq key rotated — using %s (Total pool: %d keys)", info.masked_key, key_pool.total_keys)
    return client, f"key #{info.key_index} ({info.masked_key})"


# ── Tool schemas (registered with Groq function-calling API) ──────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "document_search",
            "description": (
                "Search ParcelPilot policy documents, SOPs, customer agreements, and product docs. "
                "Use this to answer policy questions, check contract terms, or look up SOP rules. "
                "Always call this with an account_id when the question is account-specific."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language search query",
                    },
                    "account_id": {
                        "type": ["string", "null"],
                        "description": "Account ID (e.g. ACCT-001) if the query is account-specific; null otherwise",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "data_lookup",
            "description": (
                "Query the structured ParcelPilot database: accounts, orders, tickets. "
                "Also computes SLA breach status (query_type=sla_check), "
                "service credit eligibility (query_type=credit_calc), "
                "and a proactive sweep of all open issues (query_type=proactive_sweep)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["account", "order", "ticket", "sla_check", "credit_calc", "proactive_sweep"],
                        "description": "Type of query to run",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Key-value filters e.g. {account_id: 'ACCT-001'} or {order_id: 'ORD-1001'} or {ticket_id: 'TKT-505'}",
                    },
                    "current_user_role": {
                        "type": "string",
                        "enum": ["support_agent", "csm"],
                        "description": "Active session role — determines which fields are returned",
                    },
                },
                "required": ["query_type", "current_user_role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate",
            "description": (
                "Create a formal escalation record for a ticket. "
                "IMPORTANT: This action requires explicit user confirmation before execution. "
                "Use when: P1 incident detected, SLA already breached, source conflict unresolvable, "
                "or credit > INR 1000 requires manager approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id":   {"type": "string", "description": "Ticket ID (e.g. TKT-505)"},
                    "account_id":  {"type": "string", "description": "Account ID (e.g. ACCT-004)"},
                    "severity":    {"type": "string", "enum": ["P1", "P2", "P3"]},
                    "reason":      {"type": "string", "description": "Plain-language reason for escalation"},
                    "assigned_to": {"type": "string", "description": "Staff member to assign escalation to"},
                    "created_by":  {"type": "string", "description": "Current user name and role"},
                    "summary":     {"type": "string", "description": "Full context summary"},
                },
                "required": ["ticket_id", "account_id", "severity", "reason", "assigned_to", "created_by", "summary"],
            },
        },
    },
]

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are ParcelPilot's internal support agent (B2B logistics). Help staff investigate issues and act on data.

NOW: {SNAPSHOT_TIME.isoformat()}

== SOURCE HIERARCHY (highest→lowest) ==
1. Signed customer agreement for the named account:
   - ACCT-001 Northstar: 05_Northstar_Logistics_Enterprise_Agreement.pdf
   - ACCT-002 LumenWorks: 06_LumenWorks_Service_Agreement.pdf
   - ACCT-003 Beacon / ACCT-004 Axis: standard policy only
2. 01_Support_Policy_v3_CURRENT.pdf (effective 1 May 2026)
3. 03_Cancellation_and_Service_Credit_SOP_v4.pdf, 04_Product_Operations_Guide_and_Known_Issues.pdf
4. Historical tickets (context ONLY — may be wrong)

NEVER cite 02_Support_Policy_v2_DEPRECATED.pdf — it is superseded by v3.

== RULES ==
- Cite docs as [filename, p.N] and data as [table: key]
- Re-derive from current sources; historical resolutions may be wrong (TKT-450: Northstar cancellation fee WRONG; TKT-451: LumenWorks row limit WRONG)
- No-guess: if absent from sources, say so. Never fabricate.
- Escalate on: P1 incident, breached SLA, unresolvable source conflict, credit > INR 1000 (requires approval)
- escalate tool always needs user confirmation first
- NEVER apply one account's terms to another account"""


# ── Rate-limit backoff stream helper with Dynamic Key Health & Rotation ────────

async def _create_groq_stream(
    messages: list[dict],
    tools: list[dict] | None,
    model: str,
) -> Any:
    """
    Create Groq streaming completion with automatic key health selection and instant failover.
    Zero latency: Picks an in-memory healthy key (LRU balanced) immediately.
    On 429 rate limit: Marks key with cooldown and immediately steps to the next available healthy key.
    """
    excluded_keys: set[str] = set()
    max_attempts = max(key_pool.total_keys * 2, 8)
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        client, key_info = key_pool.get_healthy_client(exclude_keys=excluded_keys)
        t0 = asyncio.get_event_loop().time()
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": 2048,
                "temperature": 0.3,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            stream_result = await client.chat.completions.create(**kwargs)
            latency_ms = (asyncio.get_event_loop().time() - t0) * 1000.0
            key_pool.mark_success(key_info.api_key, latency_ms=latency_ms)
            return stream_result
        except RateLimitError as exc:
            last_exc = exc
            excluded_keys.add(key_info.api_key)
            key_pool.mark_rate_limited(key_info.api_key, error_msg=str(exc))
            # If all discovered keys have been tried in this request attempt, sleep briefly
            if len(excluded_keys) >= key_pool.total_keys:
                logger.warning("All %d Groq API keys rate-limited in pool — brief pause 1.5s...", key_pool.total_keys)
                excluded_keys.clear()
                await asyncio.sleep(1.5)
        except Exception as exc:
            key_pool.mark_error(key_info.api_key, str(exc))
            raise
    raise last_exc  # type: ignore[misc]



# ── Main agent loop ───────────────────────────────────────────────────────────

async def run_agent(
    message: str,
    session_id: str,
    role: str,
    user_name: str,
    collection: chromadb.Collection,
    data_store: DataStore,
    pending_actions: dict[str, Any],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    High-performance tool-router agent loop with real-time SSE token streaming
    and multi-key load balancing.
    Yields SSE-formatted event strings.
    """
    model = PRIMARY_MODEL

    # If this session has repeatedly exhausted retries, switch to fallback
    _exhaustion_counts: dict[str, int] = getattr(run_agent, "_exhaustion_counts", {})
    if _exhaustion_counts.get(session_id, 0) >= 2:
        model = FALLBACK_MODEL

    # Build message history
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    # Discard any stale pending action for this session on a new message
    pending_actions.pop(session_id, None)

    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        stream = None
        try:
            stream = await _create_groq_stream(messages, TOOL_SCHEMAS, model)
        except RateLimitError:
            counts: dict[str, int] = getattr(run_agent, "_exhaustion_counts", {})
            counts[session_id] = counts.get(session_id, 0) + 1
            run_agent._exhaustion_counts = counts  # type: ignore[attr-defined]

            if model == PRIMARY_MODEL:
                logger.warning("Primary model %s rate-limited; trying fallback %s", model, FALLBACK_MODEL)
                model = FALLBACK_MODEL
                try:
                    stream = await _create_groq_stream(messages, TOOL_SCHEMAS, model)
                except Exception:
                    yield _sse("error", {"message": "AI model is temporarily busy. Please retry in a moment."})
                    yield _sse("done", {})
                    return
            else:
                yield _sse("error", {"message": "AI model is temporarily busy. Please retry in a moment."})
                yield _sse("done", {})
                return
        except Exception as exc:
            logger.exception("Unexpected error creating Groq stream: %s", exc)
            yield _sse("error", {"message": "An unexpected error occurred. Please retry."})
            yield _sse("done", {})
            return

        # ── Consume stream ────────────────────────────────────────────────────
        tool_calls_dict: dict[int, dict[str, Any]] = {}
        has_content = False

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # Accumulate tool calls if model decided to call functions
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {
                            "id": tc.id or "",
                            "name": (tc.function.name if tc.function and tc.function.name else ""),
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_dict[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_dict[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_dict[idx]["arguments"] += tc.function.arguments

            # Direct real-time streaming of tokens to the client
            if delta.content:
                has_content = True
                yield _sse("token", {"text": delta.content})

        # If no tool calls were made, the final answer was already streamed
        if not tool_calls_dict:
            yield _sse("done", {})
            return

        # Format tool calls for message history
        ordered_tool_calls = [tool_calls_dict[k] for k in sorted(tool_calls_dict.keys())]
        formatted_tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": tc["arguments"],
                },
            }
            for tc in ordered_tool_calls
        ]

        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": formatted_tool_calls,
        })

        # ── Execute tools concurrently in parallel worker threads ─────────────
        # 1. Emit all tool chips immediately to the UI
        for tc in ordered_tool_calls:
            yield _sse("tool_chip", {"tool": tc["name"]})

        # Check for escalate (confirmation gate)
        escalate_call = next((tc for tc in ordered_tool_calls if tc["name"] == "escalate"), None)
        if escalate_call:
            try:
                args = json.loads(escalate_call["arguments"])
            except Exception:
                args = {}
            args.setdefault("created_by", f"{user_name} ({role})")
            pending = gate_intercept("escalate", args)
            pending_actions[session_id] = pending
            yield _sse("pending_confirmation", pending)
            yield _sse("done", {})
            return   # Stop loop — waiting for user confirmation

        # Run non-blocking concurrent tool executions
        async def _run_single_tool(tc: dict[str, Any]) -> tuple[str, str]:
            t_name = tc["name"]
            try:
                t_args = json.loads(tc["arguments"])
            except Exception:
                t_args = {}

            if t_name == "document_search":
                res = await asyncio.to_thread(
                    doc_search_fn,
                    query=t_args.get("query", ""),
                    collection=collection,
                    account_id=t_args.get("account_id"),
                )
            elif t_name == "data_lookup":
                res = await asyncio.to_thread(
                    data_lookup_fn,
                    query_type=t_args.get("query_type", "ticket"),
                    filters=t_args.get("filters", {}),
                    current_user_role=role,
                    data_store=data_store,
                )
            else:
                res = {"error": f"Unknown tool: {t_name}"}

            return tc["id"], json.dumps(res, default=str)

        tool_results = await asyncio.gather(*[_run_single_tool(tc) for tc in ordered_tool_calls])

        for tc_id, content in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": content,
            })

    yield _sse("error", {
        "message": "Agent loop exceeded maximum iterations. Please rephrase your question."
    })
    yield _sse("done", {})


# ── SSE formatter ─────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

