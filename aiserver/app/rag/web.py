"""Fetch a URL server-side and extract its readable main text.

Pipeline: validate URL -> refuse private/internal hosts (SSRF) -> GET with manual
redirects (re-checking each hop) under a size cap -> extract the article body with
trafilatura (drops nav, ads, footers, cookie banners) -> plain text with paragraphs.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx2
import trafilatura

from app.errors import UnfetchableUrlError, UpstreamError

log = logging.getLogger(__name__)

FETCH_TIMEOUT_S = 15
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
MIN_TEXT_CHARS = 50
USER_AGENT = "KnowledgeInboxBot/0.1 (+single-user RAG demo)"
HTML_TYPES = ("text/html", "application/xhtml+xml")
TEXT_TYPES = ("text/plain", "text/markdown")


@dataclass(frozen=True, slots=True)
class FetchedPage:
    requested_url:str
    final_url:str
    content_type:str
    title:str | None
    text:str


async def _assert_public_host(url:str)->None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnfetchableUrlError(f"Only http(s) URLs are supported: {url}")

    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise UnfetchableUrlError(f"Could not resolve host '{parts.hostname}'")

    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if not ip.is_global:
            raise UnfetchableUrlError(f"Refusing to fetch non-public address {ip} for '{parts.hostname}'")


async def _download(url:str)->tuple[str, str, bytes, str]:
    """Return (final_url, content_type, body, charset). Follows redirects ourselves so every hop is checked."""
    async with httpx2.AsyncClient(timeout=FETCH_TIMEOUT_S, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await _assert_public_host(url)
            try:
                async with client.stream("GET", url) as res:
                    if res.is_redirect:
                        url = urljoin(url, res.headers["location"])
                        continue
                    if res.status_code >= 400:
                        raise UnfetchableUrlError(f"URL responded with HTTP {res.status_code}")

                    content_type = res.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type not in HTML_TYPES + TEXT_TYPES:
                        raise UnfetchableUrlError(f"Unsupported content type '{content_type or 'unknown'}' (expected HTML or plain text)")

                    body = bytearray()
                    async for part in res.aiter_bytes():
                        body.extend(part)
                        if len(body) > MAX_BYTES:
                            raise UnfetchableUrlError(f"Page is larger than {MAX_BYTES // (1024 * 1024)} MB")
                    return str(res.url), content_type, bytes(body), res.encoding or "utf-8"
            except httpx2.TimeoutException:
                raise UpstreamError(f"Timed out fetching {url} after {FETCH_TIMEOUT_S}s")
            except httpx2.HTTPError as e:
                raise UpstreamError(f"Could not fetch {url}: {e.__class__.__name__}")

    raise UnfetchableUrlError(f"Too many redirects (>{MAX_REDIRECTS})")


def _extract(html:str, url:str)->tuple[str | None, str | None]:
    text = trafilatura.extract(html, url=url, include_comments=False, include_tables=True, favor_recall=True)
    meta = trafilatura.extract_metadata(html, default_url=url)
    return (meta.title if meta else None), text


async def fetch_page(url:str)->FetchedPage:
    final_url, content_type, body, charset = await _download(url)
    raw = body.decode(charset, errors="replace")

    if content_type in TEXT_TYPES:
        title, text = None, raw
    else:
        # lxml parsing is CPU-bound; keep it off the event loop.
        title, text = await asyncio.to_thread(_extract, raw, final_url)

    if not text or len(text.strip()) < MIN_TEXT_CHARS:
        raise UnfetchableUrlError("No readable text found on the page (it may need JavaScript to render)")

    log.info("url.fetched", extra={"fields": {"url": final_url, "bytes": len(body), "text_chars": len(text)}})
    return FetchedPage(requested_url=url, final_url=final_url, content_type=content_type, title=title, text=text)
