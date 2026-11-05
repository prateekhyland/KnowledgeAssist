"""Retrieval pipeline: embed query -> vector search -> drop noise -> rerank."""
from __future__ import annotations

from typing import Any

from . import embeddings
from . import store as db
from .config import get_settings

# Javadoc cross-reference pages ("Uses of X") list references to a type instead of
# documenting it. They slip past the ingest-time skip list because their filename is
# just the class name, so they are filtered here by their containing directory.
_NAV_URL_MARKERS = ("/class-use/", "/package-use.html")

# Multiplier applied to top_k so filtering still leaves a full pool to rerank.
_OVERFETCH = 3


def _is_nav_page(url: str | None) -> bool:
    return any(marker in (url or "") for marker in _NAV_URL_MARKERS)


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop chunks whose text repeats a higher-scoring chunk.

    Member sections are also indexed as part of their whole-page chunk, and an
    interface's docs are repeated on its implementing classes, so the raw hits
    contain both exact copies and substrings of each other.
    """
    kept: list[dict[str, Any]] = []
    kept_texts: list[str] = []
    for cand in candidates:
        text = " ".join((cand.get("content") or "").split())
        if not text:
            continue
        if any(text in other or other in text for other in kept_texts):
            continue
        kept.append(cand)
        kept_texts.append(text)
    return kept


def has_private_context(sources: list[dict[str, Any]]) -> bool:
    """Return True if any selected source is tagged private."""
    return any((s.get("visibility") or "public").lower() == "private" for s in sources)


def retrieve(question: str, kb_id: str | None = None, api_set: str | None = None) -> list[dict]:
    """Return the top reranked documentation chunks for a question."""
    settings = get_settings()
    query_vec = embeddings.embed_query(question)
    candidates = db.search(
        embedding=query_vec,
        top_k=settings.retrieve_top_k * _OVERFETCH,
        kb_id=kb_id,
        api_set=api_set,
    )
    if not candidates:
        return []

    filtered = _dedupe([c for c in candidates if not _is_nav_page(c.get("source_url"))])
    # Never let filtering turn a usable result set into no answer at all.
    candidates = (filtered or candidates)[: settings.retrieve_top_k]
    return embeddings.rerank(question, candidates, settings.rerank_top_n)
