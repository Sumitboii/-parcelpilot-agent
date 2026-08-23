"""
escalate.py — Tool 3: create a mocked escalation record.

IMPORTANT: This tool MUST NEVER be called directly by the agent loop.
Every call routes through confirmation_gate.py first.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.data_loader import SNAPSHOT_TIME

logger = logging.getLogger(__name__)

DEFAULT_ESCALATIONS_PATH = Path("data/escalations.jsonl")


def _get_next_sequence(escalations_path: Path) -> int:
    """Count existing lines in escalations.jsonl to derive the next sequence number."""
    if not escalations_path.exists():
        escalations_path.parent.mkdir(parents=True, exist_ok=True)
        escalations_path.touch()
        return 1
    with escalations_path.open("r") as f:
        count = sum(1 for line in f if line.strip())
    return count + 1


def execute(
    payload: dict[str, Any],
    escalations_path: Path = DEFAULT_ESCALATIONS_PATH,
) -> dict[str, Any]:
    """
    Append one escalation record to escalations.jsonl.
    Called ONLY by confirmation_gate.confirm() — never directly.

    Returns {escalation_id, status, record}.
    """
    seq           = _get_next_sequence(escalations_path)
    date_str      = SNAPSHOT_TIME.strftime("%Y%m%d")
    escalation_id = f"ESC-{date_str}-{seq:04d}"

    record: dict[str, Any] = {
        "id":          escalation_id,
        "timestamp":   SNAPSHOT_TIME.isoformat(),
        "ticket_id":   payload.get("ticket_id", ""),
        "account_id":  payload.get("account_id", ""),
        "severity":    payload.get("severity", "P3"),
        "reason":      payload.get("reason", ""),
        "assigned_to": payload.get("assigned_to", ""),
        "created_by":  payload.get("created_by", ""),
        "summary":     payload.get("summary", ""),
    }

    with escalations_path.open("a") as f:
        f.write(json.dumps(record) + "\n")

    logger.info("Escalation created: %s", escalation_id)
    return {"escalation_id": escalation_id, "status": "created", "record": record}
