"""Storage facade. Selects the vector-store backend from configuration.

VECTOR_STORE=pgvector -> app.db  (PostgreSQL + pgvector)
VECTOR_STORE=local    -> app.localstore  (NumPy file, no server required)
"""
from __future__ import annotations

from .config import get_settings

if get_settings().vector_store == "local":
    from . import localstore as _backend
else:
    from . import db as _backend

ensure_schema = _backend.ensure_schema
clear_kb = _backend.clear_kb
insert_chunks = _backend.insert_chunks
search = _backend.search
list_knowledge_bases = _backend.list_knowledge_bases
