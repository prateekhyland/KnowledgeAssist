"""Parse Javadoc-generated HTML into class/method-level chunks.

Discovery walks the whole Javadoc site (overview -> package-summary -> class pages)
via a scoped breadth-first crawl. Parsing works across Javadoc versions by first
trying to split a class page into its member (method/field) detail sections, and
falling back to chunking the cleaned page text.
"""
from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .chunk import Chunk, split_text
from .crawl import AuthType, crawl_site

# Javadoc navigation / index pages that carry no real API content.
_SKIP = {
    "index-all.html", "allclasses-index.html", "allpackages-index.html",
    "overview-tree.html", "deprecated-list.html", "help-doc.html",
    "constant-values.html", "serialized-form.html", "search.html",
    "allclasses-frame.html", "allclasses-noframe.html", "overview-frame.html",
    "package-tree.html", "package-frame.html", "package-use.html",
    "class-use.html",
}


def _skip_page(url: str) -> bool:
    fname = urlparse(url).path.rsplit("/", 1)[-1]
    if fname in _SKIP:
        return True
    if fname.endswith("-use.html") or fname.endswith("-tree.html"):
        return True
    if fname.startswith("package-frame"):
        return True
    return False


def _clean(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        tag.decompose()


def _parse_page(url: str, html: str, kb_id: str) -> list[Chunk]:
    soup = BeautifulSoup(html, "lxml")
    _clean(soup)

    title = soup.title.string.strip() if (soup.title and soup.title.string) else ""
    h1 = soup.find(["h1", "h2"])
    class_name = h1.get_text(strip=True) if h1 else title

    chunks: list[Chunk] = []

    # Modern Javadoc: member detail sections (methods, fields, constructors).
    details = soup.select("section.detail") or soup.select("li.blockList ul.blockList")
    for sec in details:
        text = sec.get_text("\n", strip=True)
        if len(text) < 20:
            continue
        heading = sec.find(["h2", "h3", "h4"])
        member = heading.get_text(strip=True) if heading else class_name
        for piece in split_text(text):
            chunks.append(
                Chunk(
                    kb_id=kb_id,
                    api_set="javadoc",
                    source_url=url,
                    title=f"{class_name} - {member}",
                    content=piece,
                    metadata={"class": class_name, "member": member},
                )
            )

    # Class/package description + fallback: chunk the whole cleaned page text.
    body = soup.find("main") or soup.body or soup
    full_text = body.get_text("\n")
    full_text = "\n".join(ln.strip() for ln in full_text.splitlines() if ln.strip())
    for piece in split_text(full_text):
        chunks.append(
            Chunk(
                kb_id=kb_id,
                api_set="javadoc",
                source_url=url,
                title=class_name or title,
                content=piece,
                metadata={"class": class_name},
            )
        )
    return chunks


def parse(
    url: str,
    kb_id: str,
    max_pages: int = 2000,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[Chunk]:
    base_path = urlparse(url).path.rstrip("/")
    include = [f"{base_path}/**"]
    chunks: list[Chunk] = []
    for page_url, html in crawl_site(
        url,
        include,
        max_pages,
        headers=headers,
        auth=auth,
    ):
        if _skip_page(page_url):
            continue
        chunks.extend(_parse_page(page_url, html, kb_id))
    return chunks
