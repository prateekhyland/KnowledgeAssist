-- Migration: add visibility/source_system support for mixed public-private docs.
-- Safe to run multiple times.

ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'public';

ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS source_system TEXT NOT NULL DEFAULT 'unknown';

UPDATE chunks
SET visibility = COALESCE(NULLIF(visibility, ''), 'public');

UPDATE chunks
SET source_system = COALESCE(NULLIF(source_system, ''), api_set, 'unknown');

CREATE INDEX IF NOT EXISTS chunks_visibility_idx
    ON chunks (visibility);

CREATE INDEX IF NOT EXISTS chunks_source_system_idx
    ON chunks (source_system);
