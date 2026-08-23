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

# ── Model config ──────────────────────────────────────────────────────────────
PRIMARY_MODEL  = "llama-3.3-70b-versatile"    # Ultra-fast (~300 tps, high intelligence)
FALLBACK_MODEL = "llama-3.1-8b-instant"       # Lightning fallback (~1,000 tps)

# ── API Key Pool & Dynamic Key Rotator ────────────────────────────────────────
_current_key_idx: int = 0
_clients: dict[str, AsyncGroq] = {}

def _get_all_groq_keys() -> list[str]:
    """Retrieve all distinct valid Groq API keys from environment."""
    keys: list[str] = []
    env_keys = os.environ.get("GROQ_API_KEYS", "") or os.environ.get("GROQ_API_KEY", "")
    for k in env_keys.split(","):
        k = k.strip()
        if k and k not in keys:
            keys.append(k)
    backup_env = os.environ.get("BACKUP_GROQ_API_KEYS", "")
    for k in backup_env.split(","):
        k = k.strip()
        if k and k not in keys:
            keys.append(k)
    return keys

def get_current_client() -> tuple[AsyncGroq, str]:
    """Return the currently active AsyncGroq client and its masked key identifier."""
    global _current_key_idx
    keys = _get_all_groq_keys()
    if not keys:
        raise RuntimeError("No Groq API keys configured")
    idx = _current_key_idx % len(keys)
    key = keys[idx]
    if key not in _clients:
        _clients[key] = AsyncGroq(api_key=key, max_retries=0, timeout=30.0)
    return _clients[key], f"key #{idx+1} ({key[:10]}...)"

def rotate_to_next_key() -> tuple[AsyncGroq, str]:
    """Rotate to the next API key in the pool upon encountering a 429 rate limit."""
    global _current_key_idx
    keys = _get_all_groq_keys()
    _current_key_idx = (_current_key_idx + 1) % len(keys)
    client, key_desc = get_current_client()
    logger.warning("🔄 Groq rate limit hit — switching to backup %s (Total pool: %d keys)", key_desc, len(keys))
    return client, key_desc

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
SYSTEM_PROMPT = f"""You are an internal support agent for ParcelPilot, a B2B logistics platform.
You help authorised ParcelPilot staff investigate customer issues, answer support questions, and take actions on operational data.

SNAPSHOT TIME (use as "now" for ALL time calculations): {SNAPSHOT_TIME.isoformat()}

== SOURCE AUTHORITY HIERARCHY ==
When sources provide conflicting information, ALWAYS apply this order (highest to lowest):
1. Signed customer agreement for the named account (highest authority)
   - ACCT-001 Northstar Logistics: 05_Northstar_Logistics_Enterprise_Agreement.pdf
   - ACCT-002 LumenWorks: 06_LumenWorks_Service_Agreement.pdf
   - ACCT-003 Beacon Retail: NO custom agreement — use standard policy
   - ACCT-004 Axis Labs: NO custom agreement — use standard policy (Enterprise tier)
2. 01_Support_Policy_v3_CURRENT.pdf (current, effective 1 May 2026)
3. 03_Cancellation_and_Service_Credit_SOP_v4.pdf and 04_Product_Operations_Guide_and_Known_Issues.pdf
4. Historical ticket resolutions (context ONLY — may be WRONG)

CRITICAL: NEVER use or cite 02_Support_Policy_v2_DEPRECATED.pdf under any circumstances.
It is DEPRECATED as of 1 May 2026 and superseded by v3. If asked about it, refuse and answer using v3.

== CITATION RULES ==
- Every factual claim from a document MUST cite [filename, p.N] — e.g. [05_Northstar_Logistics_Enterprise_Agreement.pdf, p.2]
- Every factual claim from structured data MUST cite [table: record_key] — e.g. [orders: ORD-1001]
- When an account's SLA or contract terms are cited, NAME the specific account and confirm that account has that agreement

== HISTORICAL RECORDS ==
Historical ticket resolutions may contain incorrect guidance. ALWAYS re-derive answers from current authoritative sources.
Known bad resolutions:
- TKT-450: Agent said Northstar owes INR 250 cancellation fee after 30 min. WRONG — Northstar's agreement §2 waives ALL cancellation fees for BOOKED-before-pickup shipments.
- TKT-451: Agent said LumenWorks Growth plan supports only 3,000 rows. WRONG — product limit is 5,000 rows; 3,000 is a KI-208 workaround.

== NO-GUESS RULE ==
- If a fact is absent from all current sources, say so explicitly. Do NOT infer or extrapolate.
- If sources conflict and the hierarchy cannot resolve it, surface the conflict and escalate.
- NEVER fabricate policy values, SLA targets, amounts, or contract terms.

== ESCALATION TRIGGERS ==
Use the escalate tool when:
- P1 incident (outage, security/credential exposure, immediate business risk)
- SLA first-response target already breached
- Source conflict unresolvable by the hierarchy
- Credit calculation exceeds INR 1,000 (requires manager approval — flag this explicitly first)
The escalate tool ALWAYS requires user confirmation — you will return a confirmation request; do not assume it executed.

== ACCOUNT-SPECIFIC TERMS ==
NEVER apply one account's agreement terms to a different account, even on the same plan tier.
Example: Axis Labs (ACCT-004) is Enterprise but has NO custom agreement. Its P1 SLA is 30 minutes from Policy v3 §3 — NOT Northstar's contractual 15 minutes."""


# ── Rate-limit backoff stream helper with Dynamic Key Rotation ───────────────

async def _create_groq_stream(
    messages: list[dict],
    tools: list[dict] | None,
    model: str,
) -> Any:
    """
    Create Groq streaming completion with automatic key rotation on 429 rate limits.
    Cycles through all configured backup API keys before sleeping.
    """
    keys = _get_all_groq_keys()
    max_attempts = max(len(keys) * 2, 8)
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        client, key_desc = get_current_client()
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": 4096,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            return await client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            last_exc = exc
            # Immediately rotate to the next backup key in the pool
            rotate_to_next_key()
            # If we completed a full cycle across all backup keys, pause briefly
            if (attempt + 1) % len(keys) == 0:
                logger.warning("All %d Groq API keys rate-limited — waiting 2.0s...", len(keys))
                await asyncio.sleep(2.0)
        except Exception:
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

