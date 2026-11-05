"""Parse generic HTML doc sites (crawl) and sitemaps into chunks."""
from __future__ import annotations

from .chunk import Chunk, split_text
from .crawl import AuthType, crawl_site, get, page_title, sitemap_urls, visible_text


def _page_to_chunks(url: str, html: str, kb_id: str, api_set: str) -> list[Chunk]:
    title = page_title(html)
    text = visible_text(html)
    return [
        Chunk(
            kb_id=kb_id,
            api_set=api_set,
            source_url=url,
            title=title,
            content=piece,
            metadata={},
        )
        for piece in split_text(text)
    ]


def parse_html(
    url: str,
    kb_id: str,
    include=None,
    max_pages: int = 200,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_url, html in crawl_site(
        url,
        include,
        max_pages,
        headers=headers,
        auth=auth,
    ):
        chunks.extend(_page_to_chunks(page_url, html, kb_id, "html"))
    return chunks


def parse_sitemap(
    url: str,
    kb_id: str,
    max_pages: int = 1000,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, page_url in enumerate(sitemap_urls(url, headers=headers, auth=auth)):
        if i >= max_pages:
            break
        try:
            resp = get(page_url, headers=headers, auth=auth)
        except Exception:
            continue
        if "html" not in resp.headers.get("Content-Type", ""):
            continue
        chunks.extend(_page_to_chunks(page_url, resp.text, kb_id, "sitemap"))
    return chunks
