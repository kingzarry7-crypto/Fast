"""SearXNG adapter plus optional paid-provider failover orchestration."""
import os
import re
import logging
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

def _call_optional(module_name, query, max_results):
    try:
        if module_name == "brave":
            from search_providers import brave
            result = brave.search(query, max_results=max_results)
        else:
            from search_providers import serper
            result = serper.search(query, max_results=max_results)
        if result.get("success") and result.get("results"):
            logger.info("Search provider succeeded: %s", result.get("provider", module_name))
            return result
    except Exception as exc:
        logger.warning("%s search provider unavailable (%s)", module_name, type(exc).__name__)
    return None

def search(query: str, max_results: int = 5) -> dict:
    # Ordered after Tavily: Brave -> Serper -> SearXNG instances.
    for module_name in ("brave", "serper"):
        result = _call_optional(module_name, query, max_results)
        if result:
            return result

    raw = os.getenv("SEARXNG_URLS") or os.getenv("SEARXNG_URL") or ""
    urls = []
    for value in raw.split(","):
        value = value.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme == "https" and parsed.netloc and parsed.hostname:
            urls.append(value)
    if not urls:
        return {"success": False, "error": "not_configured", "results": [], "sources": [], "query": query}
    timeout = max(3, min(int(os.getenv("WEB_RESEARCH_TIMEOUT", "8")), 12))
    for base in dict.fromkeys(urls):
        try:
            response = requests.get(
                base + "/search",
                params={"q": query, "format": "json", "language": "en", "safesearch": 1},
                headers={"Accept": "application/json", "User-Agent": "KingZarryAI/1.0"},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("results") or []
            results, seen = [], set()
            for row in rows:
                url = str(row.get("url") or "").strip()
                title = re.sub(r"\\s+", " ", str(row.get("title") or "")).strip()
                if not url.startswith(("https://", "http://")) or not title or url in seen:
                    continue
                seen.add(url)
                results.append({"title": title[:200], "url": url, "content": re.sub(r"\\s+", " ", str(row.get("content") or "")).strip()[:800], "score": 0, "published_date": ""})
                if len(results) >= max(1, min(int(max_results), 10)):
                    break
            if results:
                return {"success": True, "cached": False, "provider": "searxng", "results": results, "answer": "", "query": query, "sources": [{"title": x["title"], "url": x["url"]} for x in results]}
        except Exception as exc:
            logger.warning("SearXNG instance failed (%s)", type(exc).__name__)
    return {"success": False, "error": "searxng_unavailable", "results": [], "sources": [], "query": query}
