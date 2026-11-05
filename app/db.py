"""PostgreSQL + pgvector access helpers."""
from __future__ import annotations

import json
from typing import Any, Iterable

import psycopg
from pgvector.psycopg import register_vector

from .config import get_settings


def connect() -> psycopg.Connection:
    """Open a new connection with the pgvector type adapter registered."""
    settings = get_settings()
    conn = psycopg.connect(settings.pg_dsn)
    register_vector(conn)
    return conn


def ensure_schema() -> None:
    """Create the extension + table + indexes if they do not exist."""
    settings = get_settings()
    with connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id            BIGSERIAL PRIMARY KEY,
                kb_id         TEXT NOT NULL,
                api_set       TEXT NOT NULL,
                visibility    TEXT NOT NULL DEFAULT 'public',
                source_system TEXT NOT NULL DEFAULT 'unknown',
                source_url    TEXT NOT NULL,
                title         TEXT,
                content       TEXT NOT NULL,
                metadata      JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding     VECTOR({settings.embed_dim}) NOT NULL,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        cur.execute(
            "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS visibility TEXT "
            "NOT NULL DEFAULT 'public';"
        )
        cur.execute(
            "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source_system TEXT "
            "NOT NULL DEFAULT 'unknown';"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
            "ON chunks USING hnsw (embedding vector_cosine_ops);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_kb_idx ON chunks (kb_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_api_set_idx ON chunks (api_set);")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS chunks_visibility_idx ON chunks (visibility);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS chunks_source_system_idx ON chunks (source_system);"
        )
        conn.commit()


def clear_kb(kb_id: str) -> None:
    """Remove all chunks for a knowledge base (used before a fresh re-index)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE kb_id = %s;", (kb_id,))
        conn.commit()


def insert_chunks(rows: Iterable[dict[str, Any]]) -> int:
    """Bulk-insert chunk rows. Each row: kb_id, api_set, source_url, title,
    content, metadata (dict), embedding (list[float])."""
    rows = list(rows)
    if not rows:
        return 0
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks
                (kb_id, api_set, visibility, source_system, source_url,
                 title, content, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            [
                (
                    r["kb_id"],
                    r["api_set"],
                    r.get("visibility", "public"),
                    r.get("source_system", r["api_set"]),
                    r["source_url"],
                    r.get("title"),
                    r["content"],
                    json.dumps(r.get("metadata", {})),
                    r["embedding"],
                )
                for r in rows
            ],
        )
        conn.commit()
    return len(rows)


def list_knowledge_bases() -> list[dict[str, Any]]:
    """Return distinct knowledge bases with chunk counts (for the UI filter)."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT kb_id, COUNT(*) FROM chunks GROUP BY kb_id ORDER BY kb_id;"
        )
        return [{"id": kb, "chunks": n} for kb, n in cur.fetchall()]


def search(
    embedding: list[float],
    top_k: int,
    kb_id: str | None = None,
    api_set: str | None = None,
) -> list[dict[str, Any]]:
    """Cosine-similarity search, optionally filtered by kb / api_set."""
    where = []
    params: list[Any] = [embedding]
    if kb_id:
        where.append("kb_id = %s")
        params.append(kb_id)
    if api_set:
        where.append("api_set = %s")
        params.append(api_set)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(top_k)

    sql = f"""
        SELECT id, kb_id, api_set, visibility, source_system, source_url,
               title, content, 1 - (embedding <=> %s) AS score
        FROM chunks
        {where_sql}
        ORDER BY embedding <=> %s
        LIMIT %s;
    """
    # The distance operator needs the embedding twice (SELECT + ORDER BY).
    query_params = [embedding] + params[1:-1] + [embedding, params[-1]]
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, query_params)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
