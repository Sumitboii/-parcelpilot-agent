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
    Semantic conflict detection: compare chunks from different authority levels
    using TF-IDF cosine similarity to determine if they genuinely address the
    same topic with potentially contradictory information.

    A conflict is flagged when:
    1. Chunks from more than one distinct document are present, AND
    2. At least one cross-source chunk pair has cosine similarity >= 0.25
       (i.e. they are semantically related, not just incidentally co-retrieved).

    Falls back to presence-based detection if sklearn is unavailable.

    Returns (conflict_detected: bool, winning_source: str | None).
    """
    if not chunks:
        return False, None

    unique_sources = list({c["filename"] for c in chunks})

    if len(unique_sources) <= 1:
        return False, unique_sources[0] if unique_sources else None

    # ── Semantic similarity check ────────────────────────────────────────────
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        texts    = [c["text"] for c in chunks]
        sources  = [c["filename"] for c in chunks]

        vectorizer = TfidfVectorizer(stop_words="english", max_features=512)
        tfidf = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf)

        # Check if any pair from DIFFERENT sources has similarity >= threshold
        SIMILARITY_THRESHOLD = 0.25
        conflict_detected = False
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                if sources[i] != sources[j] and sim_matrix[i, j] >= SIMILARITY_THRESHOLD:
                    conflict_detected = True
                    logger.debug(
                        "Semantic conflict: '%s' vs '%s' similarity=%.3f",
                        sources[i], sources[j], sim_matrix[i, j],
                    )
                    break
            if conflict_detected:
                break

    except ImportError:
        # sklearn not available — fall back to presence-based detection
        logger.debug("sklearn unavailable — using presence-based conflict detection")
        conflict_detected = True  # multiple sources = assume conflict

    # ── Authority resolution ─────────────────────────────────────────────────
    winning_source = min(unique_sources, key=_authority_rank)

    if conflict_detected:
        logger.debug(
            "Conflict detected: %d sources. Winner: %s",
            len(unique_sources),
            winning_source,
        )

    return conflict_detected, winning_source
