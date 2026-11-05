"""Parse Markdown files (remote URL or local path) into chunks."""
from __future__ import annotations

from pathlib import Path

from .chunk import Chunk, split_text
from .crawl import AuthType, fetch_text


def _read(
    url: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return fetch_text(url, headers=headers, auth=auth)
    return Path(url).read_text(encoding="utf-8")


def parse(
    url: str,
    kb_id: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[Chunk]:
    text = _read(url, headers=headers, auth=auth)
    # Use the first heading as a title if present.
    title = ""
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break
    return [
        Chunk(
            kb_id=kb_id,
            api_set="markdown",
            source_url=url,
            title=title or url,
            content=piece,
            metadata={},
        )
        for piece in split_text(text)
    ]
