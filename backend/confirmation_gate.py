"""
confirmation_gate.py — Single, centralised confirmation gate for all state-changing actions.

Every state-changing tool (currently only `escalate`) MUST route through this gate.
The gate intercepts the tool call, returns a pending_confirmation SSE payload to the
frontend, and only executes the tool after the user explicitly confirms.

There is exactly ONE implementation of this gate — never per-tool.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.tools import escalate as escalate_tool

logger = logging.getLogger(__name__)


def intercept(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Intercept a state-changing tool call and return a pending_confirmation payload.
    Does NOT execute the tool.

    Returns the payload to be sent as an SSE 'pending_confirmation' event.
    """
    display = _build_display(tool_name, payload)

    pending = {
        "type":    "pending_confirmation",
        "action":  tool_name,
        "display": display,
        "payload": payload,
    }

    logger.info(
        "Confirmation required for action '%s' on ticket %s",
        tool_name,
        payload.get("ticket_id", "unknown"),
    )

    return pending


def confirm(
    session_id: str,
    payload: dict[str, Any],
    pending_actions: dict[str, Any],
) -> dict[str, Any]:
    """
    Called by POST /confirm when user clicks Confirm.
    Removes the pending action from the session store and executes the tool.
    """
    pending_actions.pop(session_id, None)
    return escalate_tool.execute(payload)


def cancel(session_id: str, pending_actions: dict[str, Any]) -> None:
    """
    Called by POST /confirm when user clicks Cancel.
    Removes the pending action without writing anything.
    """
    pending_actions.pop(session_id, None)
    logger.info("Escalation cancelled for session %s", session_id)


def _build_display(tool_name: str, payload: dict[str, Any]) -> dict[str, str]:
    """Build the human-readable display fields for the ConfirmationCard."""
    if tool_name == "escalate":
        return {
            "Action":      "Create Escalation",
            "Ticket":      payload.get("ticket_id", ""),
            "Account":     payload.get("account_id", ""),
            "Severity":    payload.get("severity", ""),
            "Assigned to": payload.get("assigned_to", ""),
            "Reason":      payload.get("reason", ""),
            "Created by":  payload.get("created_by", ""),
        }
    # Future state-changing tools: add display builders here
    return {k: str(v) for k, v in payload.items()}
