"""
document_search.py — Tool 1: retrieve cited chunks from the ChromaDB vector store.

Source-authority hierarchy (from 01_Support_Policy_v3_CURRENT.pdf §1):
  1. Signed customer agreement (ACTIVE, account-specific)
  2. Current support policy v3 (CURRENT)
  3. Current SOP v4 / Product Operations Guide (CURRENT)
  4. Historical tickets (never indexed — context only)

02_Support_Policy_v2_DEPRECATED.pdf is NEVER returned by any query.
"""
from __future__ import annotations

import logging
from typing import Any

import chromadb

from backend import vector_store as vs

logger = logging.getLogger(__name__)

# Authority order for conflict resolution (lower index = higher authority)
_AUTHORITY_ORDER = [
    # Level 1: signed customer agreements
    "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "06_LumenWorks_Service_Agreement.pdf",
    # Level 2: current support policy
    "01_Support_Policy_v3_CURRENT.pdf",
    # Level 3: current SOPs and product docs
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
    "04_Product_Operations_Guide_and_Known_Issues.pdf",
    # Level 4: historical/deprecated — should never appear in results
    "02_Support_Policy_v2_DEPRECATED.pdf",
]


def _authority_rank(filename: str) -> int:
    """Lower rank = higher authority. Unknown files get rank 99."""
    try:
        return _AUTHORITY_ORDER.index(filename)
    except ValueError:
        return 99


def search(
    query: str,
    collection: chromadb.Collection,
    account_id: str | None = None,
    k: int = 5,
) -> dict[str, Any]:
    """
    Retrieve top-k relevant chunks for a query, filtered to CURRENT/ACTIVE only.

    Parameters
    ----------
    query       : Natural-language search query
    collection  : Pre-built ChromaDB collection from vector_store.init_vector_store()
    account_id  : If provided, boosts agreement chunks for that account to the top
    k           : Number of chunks to return (default 5)

    Returns
    -------
    {
        "chunks": [{"filename", "page", "status", "text"}, ...],
        "conflict_detected": bool,
        "winning_source": str | None,
    }
    """
    # Retrieve from vector store (already filters DEPRECATED at query time)
    raw_chunks = vs.query(
        collection=collection,
        query_text=query,
        k=k,
        account_id=account_id,
        exclude_deprecated=True,
    )

    # Strip internal fields (distance, account_id) before returning to agent
    chunks = [
        {
            "filename": c["filename"],
            "page":     c["page"],
            "status":   c["status"],
            "text":     c["text"],
        }
        for c in raw_chunks
    ]

    # Paranoia check: ensure no DEPRECATED chunk slipped through
    for chunk in chunks:
        if chunk["filename"] == "02_Support_Policy_v2_DEPRECATED.pdf":
            logger.error(
                "DEPRECATED document surfaced in search results — removing. "
                "This should never happen; check vector_store filters."
            )
    chunks = [c for c in chunks if c["filename"] != "02_Support_Policy_v2_DEPRECATED.pdf"]

    # Conflict detection: if chunks from different authority levels address the same
    # topic, the highest-authority source wins.
    conflict_detected, winning_source = _detect_conflict(chunks)

    return {
        "chunks":           chunks,
        "conflict_detected": conflict_detected,
        "winning_source":   winning_source,
    }


def _detect_conflict(chunks: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """
    Detect if multiple sources are present and identify the highest-authority one.

    A conflict is flagged when chunks from more than one distinct document are
    returned for the same query — the agent must then apply the hierarchy to
    decide which source governs.

    Returns (conflict_detected: bool, winning_source: str | None).
    """
    if not chunks:
        return False, None

    unique_sources = list({c["filename"] for c in chunks})

    if len(unique_sources) <= 1:
        return False, unique_sources[0] if unique_sources else None

    # Multiple sources present — find the highest-authority one
    winning_source = min(unique_sources, key=_authority_rank)
    conflict_detected = True

    logger.debug(
        "Conflict detected: %d sources. Winner: %s",
        len(unique_sources),
        winning_source,
    )

    return conflict_detected, winning_source
