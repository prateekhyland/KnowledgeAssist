-- KnowledgeAssist schema (PostgreSQL + pgvector)
-- The embedding dimension (1024) matches BAAI/bge-large-en-v1.5.
-- If you change EMBED_MODEL/EMBED_DIM, recreate the table with the new dimension.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    kb_id         TEXT         NOT NULL,
    api_set       TEXT         NOT NULL,          -- openapi | javadoc | html | sitemap | markdown
    visibility    TEXT         NOT NULL DEFAULT 'public',
    source_system TEXT         NOT NULL DEFAULT 'unknown',
    source_url    TEXT         NOT NULL,
    title         TEXT,
    content       TEXT         NOT NULL,
    metadata      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    embedding     VECTOR(1024) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Approximate nearest-neighbour index (cosine distance).
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_kb_idx            ON chunks (kb_id);
CREATE INDEX IF NOT EXISTS chunks_api_set_idx       ON chunks (api_set);
CREATE INDEX IF NOT EXISTS chunks_visibility_idx    ON chunks (visibility);
CREATE INDEX IF NOT EXISTS chunks_source_system_idx ON chunks (source_system);
