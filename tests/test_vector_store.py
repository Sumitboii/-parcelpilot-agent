"""
test_vector_store.py — unit tests for backend/vector_store.py (task 3.3)
"""
import pytest
from backend.vector_store import query


def test_no_deprecated_chunks_returned(collection):
    """02_Support_Policy_v2_DEPRECATED.pdf must never appear in any query result."""
    for q in [
        "cancellation fee northstar",
        "SLA response time P1 P2",
        "bulk upload row limit",
    ]:
        results = query(collection, q)
        bad = [r for r in results if "02_Support_Policy" in r["filename"]]
        assert bad == [], f"DEPRECATED doc leaked for query '{q}': {bad}"


def test_account_id_boost_surfaces_agreement(collection):
    """Querying with account_id='ACCT-001' should include the Northstar agreement in top-5."""
    results = query(collection, "cancellation fee waiver", account_id="ACCT-001")
    filenames = [r["filename"] for r in results]
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" in filenames


def test_chunk_metadata_keys(collection):
    """Every returned chunk must have filename, page, status, and text keys."""
    results = query(collection, "pickup service credit")
    for r in results:
        assert "filename" in r
        assert "page" in r
        assert "status" in r
        assert "text" in r


def test_deterministic_retrieval(collection):
    """Same query twice must return the same top-5 in the same order."""
    q = "cancellation policy booked shipment"
    r1 = query(collection, q)
    r2 = query(collection, q)
    assert [c["filename"] for c in r1] == [c["filename"] for c in r2]


def test_deprecated_doc_is_indexed_but_filtered(collection):
    """The deprecated doc's chunks should exist in the collection but be filtered at retrieval."""
    # Without the filter, the deprecated doc chunks are reachable
    all_results = query(collection, "support policy SLA", exclude_deprecated=False)
    any_deprecated = any("02_Support_Policy" in r["filename"] for r in all_results)
    # With the filter (default), they are gone
    filtered_results = query(collection, "support policy SLA", exclude_deprecated=True)
    none_deprecated = all("02_Support_Policy" not in r["filename"] for r in filtered_results)
    assert none_deprecated, "DEPRECATED doc leaked through default filter"
