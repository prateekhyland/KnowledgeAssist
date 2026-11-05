"""HTTP fetching + link discovery helpers."""
from __future__ import annotations

import fnmatch
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "KnowledgeAssist-ingest/1.0"


AuthType = tuple[str, str] | None


def _request_headers(extra_headers: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def get(
    url: str,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> requests.Response:
    resp = requests.get(
        url,
        headers=_request_headers(headers),
        auth=auth,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp


def fetch_text(
    url: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> str:
    return get(url, headers=headers, auth=auth).text


def _matches(path: str, patterns: list[str] | None) -> bool:
    if not patterns:
        return True
    for pat in patterns:
        # Treat "**" like "*" for simple glob matching on the URL path.
        if fnmatch.fnmatch(path, pat.replace("**", "*")):
            return True
    return False


def visible_text(html: str) -> str:
    """Strip chrome (nav/script/style) and return readable text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="main") or soup.body or soup
    text = main.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def crawl_site(
    start_url: str,
    include: list[str] | None,
    max_pages: int = 200,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[tuple[str, str]]:
    """Breadth-first crawl within the same host + include patterns.
    Returns a list of (url, html)."""
    start = urlparse(start_url)
    seen: set[str] = set()
    queue: list[str] = [start_url]
    results: list[tuple[str, str]] = []

    while queue and len(results) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = get(url, headers=headers, auth=auth)
        except requests.RequestException:
            continue
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype:
            continue
        html = resp.text
        results.append((url, html))

        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"]).split("#")[0]
            p = urlparse(nxt)
            if p.scheme not in ("http", "https"):
                continue
            if p.netloc != start.netloc:
                continue
            if not _matches(p.path, include):
                continue
            if nxt not in seen:
                queue.append(nxt)
    return results


def sitemap_urls(
    sitemap_url: str,
    headers: dict[str, str] | None = None,
    auth: AuthType = None,
) -> list[str]:
    xml = fetch_text(sitemap_url, headers=headers, auth=auth)
    soup = BeautifulSoup(xml, "xml")
    return [loc.get_text(strip=True) for loc in soup.find_all("loc")]
