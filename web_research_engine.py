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
        response.raise_for_status()
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
