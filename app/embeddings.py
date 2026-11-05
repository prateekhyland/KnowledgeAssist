"""Embedding + reranking. Two backends:

- sentence_transformers: local torch models (BGE embeddings + cross-encoder reranker).
- ollama: embeddings served by a local Ollama server (no torch dependency). In this
  mode there is no cross-encoder reranker, so results keep their vector-similarity order.
"""
from __future__ import annotations

from functools import lru_cache

import requests

from .config import get_settings


# ---------- sentence-transformers backend ----------

@lru_cache
def _st_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embed_model)


@lru_cache
def _st_reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(get_settings().reranker_model)


# ---------- ollama backend ----------

def _ollama_embed_call(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    resp = requests.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": settings.ollama_embed_model, "input": texts},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def _ollama_embed(texts: list[str], _max_chars: int = 6000) -> list[list[float]]:
    """Robust batch embedding. Sanitizes inputs and, if a batch fails (e.g. a
    transient 400 or one oversized item), falls back to per-item embedding with
    truncation so a single bad/edge input can't abort the whole ingestion."""
    clean = [(t[:_max_chars] if t else " ") for t in texts]
    try:
        return _ollama_embed_call(clean)
    except Exception:
        out: list[list[float]] = []
        for t in clean:
            try:
                out.append(_ollama_embed_call([t])[0])
            except Exception:
                try:
                    out.append(_ollama_embed_call([t[:2000]])[0])
                except Exception:
                    dim = len(out[0]) if out else 768
                    out.append([0.0] * dim)  # last-resort placeholder
        return out


# ---------- public API ----------

def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if get_settings().embed_backend == "ollama":
        return _ollama_embed(texts)
    model = _st_embedder()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> list[float]:
    settings = get_settings()
    if settings.embed_backend == "ollama":
        return _ollama_embed([text])[0]
    prompt = f"{settings.query_instruction} {text}".strip()
    model = _st_embedder()
    vec = model.encode([prompt], normalize_embeddings=True, show_progress_bar=False)[0]
    return vec.tolist()


def rerank(query: str, candidates: list[dict], top_n: int) -> list[dict]:
    if not candidates:
        return []
    if get_settings().embed_backend == "ollama":
        # No cross-encoder in this backend; candidates are already ordered by
        # vector similarity, so just take the top N.
        return candidates[:top_n]
    model = _st_reranker()
    pairs = [(query, c["content"]) for c in candidates]
    scores = model.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    return ranked[:top_n]
