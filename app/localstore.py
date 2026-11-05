"""File-backed vector store using NumPy. No external server required.

Used when VECTOR_STORE=local. Persists all chunks + embeddings to a single pickle
file and does brute-force cosine search in memory (fine for docs-sized corpora).
"""
from __future__ import annotations

import os
import pickle
import threading
from collections import Counter
from typing import Any, Iterable

import numpy as np

from .config import get_settings

_LOCK = threading.Lock()
_FIELDS = (
    "kb_id",
    "api_set",
    "visibility",
    "source_system",
    "source_url",
    "title",
    "content",
    "metadata",
)


def _path() -> str:
    return get_settings().local_store_path


def _load() -> dict[str, Any]:
    p = _path()
    if os.path.exists(p):
        with open(p, "rb") as fh:
            return pickle.load(fh)
    return {"rows": [], "vecs": None}


def _save(data: dict[str, Any]) -> None:
    p = _path()
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, "wb") as fh:
        pickle.dump(data, fh)


def ensure_schema() -> None:
    d = os.path.dirname(_path())
    if d:
        os.makedirs(d, exist_ok=True)


def clear_kb(kb_id: str) -> None:
    with _LOCK:
        data = _load()
        keep = [i for i, r in enumerate(data["rows"]) if r["kb_id"] != kb_id]
        data["rows"] = [data["rows"][i] for i in keep]
        if data["vecs"] is not None and len(data["vecs"]):
            data["vecs"] = data["vecs"][keep] if keep else None
        _save(data)


def insert_chunks(rows: Iterable[dict[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    with _LOCK:
        data = _load()
        new_vecs = np.asarray([r["embedding"] for r in rows], dtype=np.float32)
        for r in rows:
            if "visibility" not in r:
                r["visibility"] = "public"
            if "source_system" not in r:
                r["source_system"] = r.get("api_set", "unknown")
        data["rows"].extend({k: r.get(k) for k in _FIELDS} for r in rows)
        if data["vecs"] is None or len(data["vecs"]) == 0:
            data["vecs"] = new_vecs
        else:
            data["vecs"] = np.vstack([data["vecs"], new_vecs])
        _save(data)
    return len(rows)


def list_knowledge_bases() -> list[dict[str, Any]]:
    data = _load()
    counts = Counter(r["kb_id"] for r in data["rows"])
    return [{"id": k, "chunks": n} for k, n in sorted(counts.items())]


def search(
    embedding: list[float],
    top_k: int,
    kb_id: str | None = None,
    api_set: str | None = None,
) -> list[dict[str, Any]]:
    data = _load()
    rows, vecs = data["rows"], data["vecs"]
    if not rows or vecs is None or len(vecs) == 0:
        return []

    idx = [
        i
        for i, r in enumerate(rows)
        if (kb_id is None or r["kb_id"] == kb_id)
        and (api_set is None or r["api_set"] == api_set)
    ]
    if not idx:
        return []

    q = np.asarray(embedding, dtype=np.float32)
    q = q / (np.linalg.norm(q) + 1e-9)
    sub = vecs[idx]
    sub = sub / (np.linalg.norm(sub, axis=1, keepdims=True) + 1e-9)
    sims = sub @ q

    order = np.argsort(-sims)[:top_k]
    out = []
    for o in order:
        r = dict(rows[idx[o]])
        r["score"] = float(sims[o])
        out.append(r)
    return out
