"""Chunk data model and text-splitting helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    kb_id: str
    api_set: str          # openapi | javadoc | html | sitemap | markdown
    source_url: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_row(self) -> dict[str, Any]:
        return {
            "kb_id": self.kb_id,
            "api_set": self.api_set,
            "source_url": self.source_url,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
        }


def split_text(text: str, max_chars: int = 1400, overlap: int = 200) -> list[str]:
    """Paragraph-aware splitter. Keeps chunks under ~max_chars with a little overlap."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # Hard-split an oversized paragraph.
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), max_chars - overlap):
                chunks.append(para[i : i + max_chars])
            continue
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            chunks.append(current)
            # start next chunk with a small tail overlap for context continuity
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)
    return chunks
