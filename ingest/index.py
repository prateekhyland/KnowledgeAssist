"""Ingestion orchestrator: read sources.yaml, parse, embed, and load into pgvector.

Usage:
    python -m ingest.index                 # index every knowledge base
    python -m ingest.index --kb default    # index a single knowledge base
    python -m ingest.index --sources path/to/sources.yaml
"""
from __future__ import annotations

import argparse
import sys

from app import store as db
from app.embeddings import embed_passages

from . import parse_html, parse_javadoc, parse_markdown, parse_openapi
from .auth import resolve_request_auth
from .chunk import Chunk
from .config import load_sources

EMBED_BATCH = 64


def _parse_source(src: dict, kb_id: str) -> list[Chunk]:
    stype = src.get("type")
    url = src.get("url")
    if not url:
        print(f"  ! skipping source with no url: {src}")
        return []
    print(f"  - {stype}: {url}")
    visibility = (src.get("visibility") or "public").strip().lower()
    source_system = (src.get("source_system") or stype or "unknown").strip().lower()
    auth_ref = src.get("auth_ref")

    try:
        headers, auth = resolve_request_auth(src)
        if auth_ref:
            print(f"    using credential reference: {auth_ref}")

        if stype == "openapi":
            chunks = parse_openapi.parse(url, kb_id, headers=headers, auth=auth)
        elif stype == "javadoc":
            chunks = parse_javadoc.parse(
                url,
                kb_id,
                max_pages=src.get("max_pages", 500),
                headers=headers,
                auth=auth,
            )
        elif stype == "html":
            chunks = parse_html.parse_html(
                url,
                kb_id,
                include=src.get("include"),
                max_pages=src.get("max_pages", 200),
                headers=headers,
                auth=auth,
            )
        elif stype == "sitemap":
            chunks = parse_html.parse_sitemap(
                url,
                kb_id,
                max_pages=src.get("max_pages", 1000),
                headers=headers,
                auth=auth,
            )
        elif stype == "markdown":
            chunks = parse_markdown.parse(url, kb_id, headers=headers, auth=auth)
        else:
            print(f"  ! unknown source type: {stype}")
            return []
    except Exception as exc:  # keep going on a single bad source
        print(f"  ! error parsing {url}: {exc}")
        return []

    for chunk in chunks:
        chunk.metadata["visibility"] = visibility
        chunk.metadata["source_system"] = source_system
        if auth_ref:
            chunk.metadata["auth_ref"] = auth_ref
    return chunks


def _embed_and_store(chunks: list[Chunk]) -> int:
    stored = 0
    for i in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[i : i + EMBED_BATCH]
        vectors = embed_passages([c.content for c in batch])
        rows = []
        for c, vec in zip(batch, vectors):
            row = c.as_row()
            row["embedding"] = vec
            row["visibility"] = c.metadata.get("visibility", "public")
            row["source_system"] = c.metadata.get("source_system", c.api_set)
            rows.append(row)
        stored += db.insert_chunks(rows)
        print(f"    stored {stored}/{len(chunks)} chunks", end="\r")
    print()
    return stored


def index_kb(kb: dict) -> None:
    kb_id = kb["id"]
    print(f"\n=== Knowledge base: {kb_id} ({kb.get('label', '')}) ===")
    print(f"Clearing existing chunks for '{kb_id}'...")
    db.clear_kb(kb_id)

    all_chunks: list[Chunk] = []
    for src in kb.get("sources", []):
        all_chunks.extend(_parse_source(src, kb_id))

    print(f"Parsed {len(all_chunks)} chunks. Embedding + storing...")
    total = _embed_and_store(all_chunks)
    print(f"Done: {total} chunks indexed for '{kb_id}'.")


def main() -> int:
    ap = argparse.ArgumentParser(description="KnowledgeAssist document ingestion")
    ap.add_argument("--kb", help="Only index this knowledge base id")
    ap.add_argument("--sources", help="Path to sources.yaml")
    args = ap.parse_args()

    db.ensure_schema()
    kbs = load_sources(args.sources)
    if args.kb:
        kbs = [k for k in kbs if k.get("id") == args.kb]
        if not kbs:
            print(f"No knowledge base with id '{args.kb}' found.")
            return 1

    for kb in kbs:
        index_kb(kb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
