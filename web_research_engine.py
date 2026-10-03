"""KING ZARRY AI — multi-source web research layer.

Additive search/research module. It does not replace Tavily, GDELT, or any
existing provider. When a SearXNG endpoint is configured it can fan out across
the search engines enabled by that SearXNG instance. It can also reuse Tavily
when the existing module is available and can fetch public HTTPS result pages
for deeper source text.

Environment:
  SEARXNG_URL=https://your-searxng-instance.example
  or SEARXNG_URLS=https://instance1,https://instance2
  WEB_RESEARCH_TIMEOUT=12
  WEB_RESEARCH_MAX_RESULTS=8
  WEB_RESEARCH_MAX_PAGES=8

No API key is required by this module for SearXNG itself. A SearXNG instance
may still have its own access/rate-limit policy.
"""

import html
import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger("web_research_engine")

_TIMEOUT = max(5, int(os.getenv("WEB_RESEARCH_TIMEOUT", "12")))
_MAX_RESULTS = max(3, min(int(os.getenv("WEB_RESEARCH_MAX_RESULTS", "8")), 20))
_MAX_PAGES = max(3, min(int(os.getenv("WEB_RESEARCH_MAX_PAGES", "8")), 15))

_RESEARCH_TERMS = (
    "deep research", "deep search", "research this", "research on",
    "do a research", "detailed research", "comprehensive research",
    "thorough research", "in-depth research", "investigate", "investigation",
    "compare sources", "fact check", "fact-check", "verify this",
    "find reliable sources", "look up", "search the web", "search online",
    "latest", "today", "current", "recent", "news", "what happened",
)

class _SearchHTMLParser(HTMLParser):
    """Small parser for SearXNG HTML when an instance disables format=json."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: List[Dict[str, Any]] = []
        self._in_article = False
        self._depth = 0
        self._current: Dict[str, Any] = {}
        self._capture_title = False
        self._capture_content = False
        self._parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = set(str(attrs_dict.get("class") or "").split())
        if tag.lower() == "article" and ("result" in classes or "result-default" in classes):
            self._in_article = True
            self._depth = 1
            self._current = {}
            self._parts = []
            return
        if not self._in_article:
            return
        if tag.lower() == "a" and not self._current.get("url"):
            href = str(attrs_dict.get("href") or "").strip()
            if href.startswith(("http://", "https://")):
                self._current["url"] = href
                self._capture_title = True
        if tag.lower() == "p":
            self._capture_content = True

    def handle_endtag(self, tag):
        if not self._in_article:
            return
        if tag.lower() == "a" and self._capture_title:
            self._capture_title = False
        if tag.lower() == "p":
            self._capture_content = False
        if tag.lower() == "article":
            title = re.sub(r"\s+", " ", str(self._current.get("title") or "")).strip()
            content = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            url = str(self._current.get("url") or "").strip()
            if url:
                self.results.append({
                    "title": title or "Untitled",
                    "url": url,
                    "content": content,
                    "engine": "searxng-html",
                    "source": "SearXNG",
                })
            self._in_article = False
            self._depth = 0

    def handle_data(self, data):
        if not self._in_article:
            return
        value = html.unescape(data or "")
        if self._capture_title:
            self._current["title"] = (self._current.get("title") or "") + " " + value
        if self._capture_content:
            self._parts.append(value)


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self._SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            value = re.sub(r"\s+", " ", html.unescape(data or "")).strip()
            if value:
                self.parts.append(value)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def _env_urls() -> List[str]:
    raw = os.getenv("SEARXNG_URLS") or os.getenv("SEARXNG_URL") or ""
    urls = []
    for item in raw.split(","):
        item = item.strip().rstrip("/")
        if not item:
            continue
        parsed = urlparse(item)
        if parsed.scheme == "https" and parsed.netloc:
            urls.append(item)
    return list(dict.fromkeys(urls))


def is_configured() -> bool:
    return bool(_env_urls())


def extract_urls(text: str) -> List[str]:
    """Return explicit public http(s) URLs pasted into a user message."""
    raw = re.findall(r"https?://[^\s<>'\"\)\]]+", str(text or ""), flags=re.IGNORECASE)
    urls = []
    for value in raw:
        value = value.rstrip(".,;:!?")
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            continue
        # Refuse localhost/private-network targets to avoid SSRF.
        host = (parsed.hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "::1"} or host.startswith(("10.", "192.168.", "169.254.")):
            continue
        if host.startswith("172."):
            try:
                if 16 <= int(host.split(".")[1]) <= 31:
                    continue
            except Exception:
                pass
        urls.append(value)
    return list(dict.fromkeys(urls))[:5]


def fetch_url(url: str, max_chars: int = 18000) -> Dict[str, Any]:
    """Fetch one explicit public URL and extract readable page text."""
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return {"success": False, "url": url, "error": "Invalid public URL"}

    try:
        response = requests.get(
            str(url).strip(),
            headers={
                "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf",
                "User-Agent": "KingZarryAI/1.0 (+public-page-reader)",
            },
            timeout=_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        final = urlparse(response.url)
        if final.scheme not in ("http", "https") or not final.netloc:
            return {"success": False, "url": url, "error": "Unsafe redirect"}

        content_type = (response.headers.get("content-type") or "").lower()
        if "html" in content_type or "xhtml" in content_type:
            parser = _TextExtractor()
            parser.feed(response.text[:2_000_000])
            page_text = parser.text()
        elif "text/" in content_type:
            page_text = re.sub(r"\s+", " ", response.text).strip()
        else:
            return {
                "success": False,
                "url": url,
                "final_url": response.url,
                "error": f"Unsupported page type: {content_type or 'unknown'}",
            }

        page_text = page_text[:max(1000, min(int(max_chars), 30000))]
        if not page_text:
            return {"success": False, "url": url, "final_url": response.url, "error": "No readable text found"}

        return {
            "success": True,
            "url": url,
            "final_url": response.url,
            "content_type": content_type,
            "content": page_text,
        }
    except Exception as exc:
        logger.warning("Direct URL fetch failed: %s", type(exc).__name__)
        return {"success": False, "url": url, "error": "Could not read this public URL"}


def format_url_context(pages: List[Dict[str, Any]], max_chars: int = 30000) -> str:
    chunks = []
    used = 0
    for idx, page in enumerate(pages, 1):
        if not page.get("success"):
            continue
        url = str(page.get("final_url") or page.get("url") or "").strip()
        content = str(page.get("content") or "").strip()
        block = f"PAGE {idx}: {url}\nCONTENT:\n{content}"
        if used + len(block) > max_chars:
            break
        chunks.append(block)
        used += len(block)
    if not chunks:
        return ""
    return "--- DIRECT URL PAGE CONTENT ---\n" + "\n\n".join(chunks) + "\n--- END DIRECT URL PAGE CONTENT ---\n\n"


def should_research(prompt: str) -> bool:
    low = str(prompt or "").strip().lower()
    if not low:
        return False
    if any(term in low for term in _RESEARCH_TERMS):
        return True
    # Questions that are clearly asking for live/current information.
    return bool(re.search(r"\b(latest|today|now|currently|as of|this week|this month)\b", low))


def _query_variants(prompt: str, deep: bool) -> List[str]:
    base = re.sub(r"\s+", " ", str(prompt or "")).strip()[:500]
    if not base:
        return []
    queries = [base]
    if deep:
        queries.extend([
            base + " official sources",
            base + " recent news",
            base + " analysis evidence",
        ])
    return list(dict.fromkeys(q.strip() for q in queries if q.strip()))[:4]


def _search_instance(base_url: str, query: str, max_results: int, time_range: str = "") -> List[Dict[str, Any]]:
    try:
        response = requests.get(
            base_url + "/search",
            params={
                "q": query,
                "format": "json",
                "language": "en",
                "safesearch": 1,
                **({"time_range": time_range} if time_range else {}),
            },
            headers={"Accept": "application/json", "User-Agent": "KingZarryAI/1.0"},
            timeout=_TIMEOUT,
        )
        if response.ok:
            try:
                payload = response.json()
                rows = payload.get("results") or []
                out = []
                for row in rows[:max_results]:
                    url = str(row.get("url") or "").strip()
                    if not url or urlparse(url).scheme not in ("http", "https"):
                        continue
                    out.append({
                        "title": re.sub(r"\s+", " ", str(row.get("title") or "Untitled")).strip(),
                        "url": url,
                        "content": re.sub(r"\s+", " ", str(row.get("content") or "")).strip(),
                        "engine": str(row.get("engine") or "searxng"),
                        "source": "SearXNG",
                    })
                return out
            except Exception:
                pass

        # Some public instances intentionally disable JSON output.
        html_response = requests.get(
            base_url + "/search",
            params={
                "q": query,
                "language": "en",
                "safesearch": 1,
                **({"time_range": time_range} if time_range else {}),
            },
            headers={"Accept": "text/html", "User-Agent": "KingZarryAI/1.0"},
            timeout=_TIMEOUT,
        )
        html_response.raise_for_status()
        parser = _SearchHTMLParser()
        parser.feed(html_response.text[:2_000_000])
        return parser.results[:max_results]
    except Exception as exc:
        logger.warning("SearXNG search failed for %s: %s", base_url, type(exc).__name__)
        return []


def _fetch_page(item: Dict[str, Any]) -> Dict[str, Any]:
    url = str(item.get("url") or "")
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return item
        response = requests.get(
            url,
            headers={"Accept": "text/html,application/xhtml+xml", "User-Agent": "KingZarryAI/1.0"},
            timeout=_TIMEOUT,
            allow_redirects=True,
        )
        content_type = (response.headers.get("content-type") or "").lower()
        if response.status_code >= 400 or ("html" not in content_type and "text/" not in content_type):
            return item
        parser = _TextExtractor()
        parser.feed(response.text[:1_500_000])
        text = parser.text()
        if text:
            item = dict(item)
            item["page_text"] = text[:7000]
            item["final_url"] = response.url
        return item
    except Exception:
        return item


def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for item in items:
        url = str(item.get("final_url") or item.get("url") or "").strip()
        key = re.sub(r"^https?://", "", url, flags=re.I).rstrip("/").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def research(query: str, deep: bool = False, max_results: int = None) -> Dict[str, Any]:
    """Run multi-query SearXNG research and fetch the strongest public pages."""
    instances = _env_urls()
    if not instances:
        return {"success": False, "configured": False, "results": [], "sources": [], "error": "SEARXNG_URL is not configured"}

    limit = max(3, min(int(max_results or _MAX_RESULTS), 20))
    variants = _query_variants(query, deep)
    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(4, len(instances) * max(1, len(variants)))) as pool:
        futures = [
            pool.submit(_search_instance, instance, q, max(3, min(limit, 8)),
                        "month" if deep else "")
            for instance in instances for q in variants
        ]
        for future in as_completed(futures):
            try:
                rows.extend(future.result())
            except Exception:
                pass

    rows = _dedupe(rows)[:limit * (2 if deep else 1)]
    fetch_targets = rows[:_MAX_PAGES if deep else min(5, _MAX_PAGES)]
    with ThreadPoolExecutor(max_workers=min(6, len(fetch_targets) or 1)) as pool:
        futures = [pool.submit(_fetch_page, item) for item in fetch_targets]
        fetched = []
        for future in as_completed(futures):
            try:
                fetched.append(future.result())
            except Exception:
                pass

    # Preserve search ranking as much as possible.
    by_url = {str(x.get("url")): x for x in fetched}
    final_rows = [by_url.get(str(x.get("url")), x) for x in rows]
    final_rows = final_rows[:limit]
    sources = [
        {
            "title": x.get("title") or "Source",
            "url": x.get("final_url") or x.get("url"),
        }
        for x in final_rows
        if x.get("url")
    ]
    return {
        "success": bool(final_rows),
        "configured": True,
        "results": final_rows,
        "sources": sources,
        "query": query,
        "deep": deep,
        "instances": len(instances),
    }


def format_for_ai(result: Dict[str, Any], max_chars: int = 24000) -> str:
    if not result.get("success"):
        return ""
    chunks = []
    used = 0
    for idx, item in enumerate(result.get("results", []), 1):
        title = str(item.get("title") or "Source").strip()
        url = str(item.get("final_url") or item.get("url") or "").strip()
        snippet = str(item.get("page_text") or item.get("content") or "").strip()
        snippet = snippet[:5000]
        block = f"SOURCE {idx}: {title}\\nURL: {url}\\nCONTENT: {snippet}"
        if used + len(block) > max_chars:
            break
        chunks.append(block)
        used += len(block)
    if not chunks:
        return ""
    return (
        "--- MULTI-SOURCE WEB RESEARCH ---\\n"
        + "\\n\\n".join(chunks)
        + "\\n--- END MULTI-SOURCE WEB RESEARCH ---"
    )


def sources_footer(sources: List[Dict[str, str]], limit: int = 8) -> str:
    if not sources:
        return ""
    lines = ["\\n\\n**Sources:**"]
    seen = set()
    for source in sources[:limit]:
        title = str(source.get("title") or "Source").strip()
        url = str(source.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        lines.append(f"- [{title}]({url})")
    return "\\n".join(lines)
