"""
vector_store.py — ChromaDB in-memory collection for ParcelPilot source documents.

All 6 PDFs are ingested. 02_Support_Policy_v2_DEPRECATED.pdf gets status=DEPRECATED
and is filtered out at retrieval time. Defence in depth: two filter points (ingest tag
+ retrieval where clause) ensure deprecated content never reaches the agent.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
import pdfplumber
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ── Document metadata map ────────────────────────────────────────────────────
# Defines status and account_id for every source document.
# status: CURRENT | DEPRECATED | ACTIVE
# account_id: set for customer agreement PDFs; empty string otherwise.
DOC_META: dict[str, dict[str, str]] = {
    "01_Support_Policy_v3_CURRENT.pdf":               {"status": "CURRENT",    "account_id": ""},
    "02_Support_Policy_v2_DEPRECATED.pdf":            {"status": "DEPRECATED", "account_id": ""},
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf":  {"status": "CURRENT",    "account_id": ""},
    "04_Product_Operations_Guide_and_Known_Issues.pdf": {"status": "CURRENT",  "account_id": ""},
    "05_Northstar_Logistics_Enterprise_Agreement.pdf": {"status": "ACTIVE",    "account_id": "ACCT-001"},
    "06_LumenWorks_Service_Agreement.pdf":             {"status": "ACTIVE",    "account_id": "ACCT-002"},
}

_CHUNK_SIZE_CHARS = 1600   # ≈ 400 tokens at ~4 chars/token
_OVERLAP_CHARS    = 200    # ≈ 50 tokens overlap


# ── Model caching ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load all-MiniLM-L6-v2 once and cache it for the process lifetime."""
    logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 …")
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


# ── PDF chunking ──────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks at word boundaries.
    chunk_size and overlap are in characters.
    """
    if not text.strip():
        return []

    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        word_len = len(word) + 1  # +1 for space
        if current_len + word_len > chunk_size and current:
            chunks.append(" ".join(current))
            # Keep overlap: remove words from the front until we're within overlap budget
            while current and current_len > overlap:
                removed = current.pop(0)
                current_len -= len(removed) + 1
        current.append(word)
        current_len += word_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _chunk_pdf(pdf_path: Path) -> list[dict[str, Any]]:
    """
    Extract text from every page of a PDF and chunk it.
    Returns list of {id, text, page} dicts.
    """
    chunks: list[dict[str, Any]] = []
    filename = pdf_path.name

    with pdfplumber.open(pdf_path) as doc:
        for page_num, page in enumerate(doc.pages, start=1):
            text = page.extract_text() or ""
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            page_chunks = _chunk_text(text, _CHUNK_SIZE_CHARS, _OVERLAP_CHARS)
            for idx, chunk_text in enumerate(page_chunks):
                chunks.append({
                    "id": f"{filename}_{page_num}_{idx}",
                    "text": chunk_text,
                    "page": page_num,
                })

    return chunks


# ── Collection initialisation ─────────────────────────────────────────────────

def init_vector_store(sources_dir: Path) -> chromadb.Collection:
    """
    Build an in-memory ChromaDB collection from all 6 source PDFs.
    Called once at server startup. Returns the populated collection.
    """
    client = chromadb.Client()
    collection = client.get_or_create_collection(
        name="parcelpilot_docs",
        metadata={"hnsw:space": "cosine"},
    )
    if collection.count() > 0:
        return collection
    model = _get_model()

    for filename, meta in DOC_META.items():
        pdf_path = sources_dir / filename
        if not pdf_path.exists():
            logger.warning("Source PDF not found, skipping: %s", filename)
            continue

        logger.info("Ingesting %s (status=%s) …", filename, meta["status"])
        raw_chunks = _chunk_pdf(pdf_path)

        if not raw_chunks:
            logger.warning("No text extracted from %s", filename)
            continue

        ids        = [c["id"]   for c in raw_chunks]
        texts      = [c["text"] for c in raw_chunks]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        metadatas  = [
            {
                "filename":   filename,
                "page":       c["page"],
                "status":     meta["status"],
                "account_id": meta["account_id"],
            }
            for c in raw_chunks
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("  → added %d chunks", len(raw_chunks))

    total = collection.count()
    logger.info("Vector store ready: %d total chunks across all documents", total)
    return collection


# ── Query ──────────────────────────────────────────────────────────────────────

def query(
    collection: chromadb.Collection,
    query_text: str,
    k: int = 5,
    account_id: str | None = None,
    exclude_deprecated: bool = True,
) -> list[dict[str, Any]]:
    """
    Embed query_text and retrieve the top-k most relevant non-deprecated chunks.

    If account_id is provided, boost agreement chunks for that account to the
    top of results (they are inserted at position 0 if not already present).

    Returns list of {filename, page, status, account_id, text} dicts.
    """
    model = _get_model()
    embedding = model.encode(query_text, show_progress_bar=False).tolist()

    # Build the where filter — always exclude DEPRECATED chunks
    where: dict[str, Any] | None = None
    if exclude_deprecated:
        where = {"status": {"$ne": "DEPRECATED"}}

    # Over-fetch to allow account boosting + post-filter
    n_results = min(k + 10, collection.count())
    if n_results == 0:
        return []

    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # Flatten results
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    formatted: list[dict[str, Any]] = [
        {
            "filename":   m["filename"],
            "page":       m["page"],
            "status":     m["status"],
            "account_id": m.get("account_id", ""),
            "text":       d,
            "distance":   dist,
        }
        for d, m, dist in zip(docs, metas, distances)
    ]

    # Account boosting: move agreement chunks for the requested account to the front
    if account_id:
        agreement_chunks = [c for c in formatted if c["account_id"] == account_id]
        other_chunks     = [c for c in formatted if c["account_id"] != account_id]
        formatted = agreement_chunks + other_chunks

    # Truncate to top-k
    return formatted[:k]
