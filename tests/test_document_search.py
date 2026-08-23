"""
test_document_search.py — unit tests for backend/tools/document_search.py (task 4.2)
"""
import pytest
from backend.tools.document_search import search


def test_returns_correct_keys(collection):
    result = search("cancellation fee", collection)
    assert "chunks" in result
    assert "conflict_detected" in result
    assert "winning_source" in result


def test_chunk_has_required_fields(collection):
    result = search("SLA response targets", collection)
    for chunk in result["chunks"]:
        assert set(chunk.keys()) >= {"filename", "page", "status", "text"}


def test_no_deprecated_in_results(collection):
    """search() must never return a chunk from the deprecated policy."""
    result = search("P1 P2 response time severity", collection)
    for chunk in result["chunks"]:
        assert "02_Support_Policy" not in chunk["filename"], \
            f"DEPRECATED chunk leaked: {chunk['filename']}"


def test_conflict_detected_false_for_unambiguous_query(collection):
    """A query targeting a single doc should report no conflict."""
    # Ask specifically about the Northstar agreement with account_id boost
    result = search("Northstar cancellation fee waiver BOOKED", collection, account_id="ACCT-001")
    # With the agreement boosted to top, its chunks dominate — conflict may or may not fire
    # What must hold: if only one source is returned, conflict_detected must be False
    sources = {c["filename"] for c in result["chunks"]}
    if len(sources) == 1:
        assert result["conflict_detected"] is False


def test_agreement_wins_conflict_over_policy(collection):
    """When agreement chunks and policy chunks conflict, winning_source should be the agreement."""
    result = search("cancellation fee after 30 minutes booked shipment", collection, account_id="ACCT-001")
    sources = {c["filename"] for c in result["chunks"]}
    if "05_Northstar_Logistics_Enterprise_Agreement.pdf" in sources and len(sources) > 1:
        assert result["winning_source"] == "05_Northstar_Logistics_Enterprise_Agreement.pdf", \
            f"Agreement should win conflict, got: {result['winning_source']}"


def test_all_returned_chunks_are_current_or_active(collection):
    """All chunks returned must have status CURRENT or ACTIVE — never DEPRECATED."""
    result = search("pickup service credit calculation", collection)
    for chunk in result["chunks"]:
        assert chunk["status"] in ("CURRENT", "ACTIVE"), \
            f"Unexpected status {chunk['status']} in chunk from {chunk['filename']}"
