"""
test_escalate_and_gate.py — unit tests for escalate.py and confirmation_gate.py (task 6.3)
"""
import json
import tempfile
import pytest
from pathlib import Path

from backend.tools.escalate import execute, _get_next_sequence
from backend.confirmation_gate import intercept, confirm, cancel
from backend.data_loader import SNAPSHOT_TIME


_PAYLOAD = {
    "ticket_id": "TKT-501",
    "account_id": "ACCT-001",
    "severity": "P1",
    "reason": "Complete shipment creation failure",
    "assigned_to": "Rohit",
    "created_by": "Priya Mehta (csm)",
    "summary": "Every user at Northstar gets HTTP 500",
}


# ── escalate.execute ──────────────────────────────────────────────────────────

def test_execute_writes_valid_jsonl():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    execute(_PAYLOAD.copy(), tmp)
    line = json.loads(tmp.read_text().strip())
    assert line["ticket_id"] == "TKT-501"
    assert line["account_id"] == "ACCT-001"
    assert line["severity"] == "P1"
    assert line["created_by"] == "Priya Mehta (csm)"


def test_execute_generates_correct_id_format():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    result = execute(_PAYLOAD.copy(), tmp)
    assert result["escalation_id"].startswith("ESC-20260816-")
    assert result["status"] == "created"


def test_execute_uses_snapshot_time():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    result = execute(_PAYLOAD.copy(), tmp)
    assert "2026-08-16" in result["record"]["timestamp"]


def test_sequence_increments():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    r1 = execute(_PAYLOAD.copy(), tmp)
    r2 = execute(_PAYLOAD.copy(), tmp)
    seq1 = int(r1["escalation_id"].split("-")[-1])
    seq2 = int(r2["escalation_id"].split("-")[-1])
    assert seq2 == seq1 + 1


def test_execute_creates_file_if_missing():
    tmp = Path(tempfile.mktemp(suffix=".jsonl"))
    assert not tmp.exists()
    execute(_PAYLOAD.copy(), tmp)
    assert tmp.exists()


# ── confirmation_gate.intercept ────────────────────────────────────────────────

def test_intercept_does_not_write_to_file():
    """intercept() must NOT call escalate.execute() — pure interception only."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    original_size = tmp.stat().st_size
    intercept("escalate", _PAYLOAD.copy())
    assert tmp.stat().st_size == original_size, "intercept() must not write to escalations file"


def test_intercept_returns_pending_confirmation_type():
    result = intercept("escalate", _PAYLOAD.copy())
    assert result["type"] == "pending_confirmation"
    assert result["action"] == "escalate"


def test_intercept_display_has_required_fields():
    result = intercept("escalate", _PAYLOAD.copy())
    display = result["display"]
    assert "Action" in display
    assert "Ticket" in display
    assert "Severity" in display


def test_intercept_payload_preserved():
    result = intercept("escalate", _PAYLOAD.copy())
    assert result["payload"]["ticket_id"] == "TKT-501"


# ── confirmation_gate.cancel ───────────────────────────────────────────────────

def test_cancel_removes_pending_action():
    pending_actions = {"sess-1": {"some": "pending"}}
    cancel("sess-1", pending_actions)
    assert "sess-1" not in pending_actions


def test_cancel_does_not_write_anything():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        tmp = Path(f.name)
    original_content = tmp.read_text()
    cancel("sess-1", {"sess-1": {"some": "pending"}})
    assert tmp.read_text() == original_content


# ── confirmation_gate.confirm ──────────────────────────────────────────────────

def test_confirm_calls_execute_exactly_once():
    """confirm() must call escalate_tool.execute exactly once and return its result."""
    from unittest.mock import patch as _patch, MagicMock
    mock_result = {"escalation_id": "ESC-20260816-0001", "status": "created", "record": {}}
    pending_actions = {"sess-1": {"payload": _PAYLOAD.copy()}}
    with _patch("backend.confirmation_gate.escalate_tool.execute", return_value=mock_result) as mock_exec:
        result = confirm("sess-1", _PAYLOAD.copy(), pending_actions)
    mock_exec.assert_called_once()
    assert result["status"] == "created"
    assert result["escalation_id"] == "ESC-20260816-0001"


def test_confirm_removes_session_from_pending():
    from unittest.mock import patch as _patch
    mock_result = {"escalation_id": "ESC-20260816-0002", "status": "created", "record": {}}
    pending_actions = {"sess-2": {"payload": _PAYLOAD.copy()}}
    with _patch("backend.confirmation_gate.escalate_tool.execute", return_value=mock_result):
        confirm("sess-2", _PAYLOAD.copy(), pending_actions)
    assert "sess-2" not in pending_actions
