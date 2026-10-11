"""Serper Google Search API adapter. Optional: requires SERPER_API_KEY."""
import os
import re
import logging
import requests

logger = logging.getLogger(__name__)

def search(query: str, max_results: int = 5) -> dict:
    key = (os.getenv("SERPER_API_KEY") or "").strip()
    if not key:
        return {"success": False, "error": "not_configured", "results": [], "sources": [], "query": query}
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": max(1, min(int(max_results), 10))},
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            timeout=max(3, min(int(os.getenv("WEB_RESEARCH_TIMEOUT", "8")), 12)),
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("organic") or []
        results, seen = [], set()
        for row in rows:
            url = str(row.get("link") or "").strip()
            title = re.sub(r"\s+", " ", str(row.get("title") or "")).strip()
            if not url.startswith(("https://", "http://")) or not title or url in seen:
                continue
            seen.add(url)
            results.append({"title": title[:200], "url": url, "content": re.sub(r"\s+", " ", str(row.get("snippet") or "")).strip()[:800], "score": 0, "published_date": str(row.get("date") or "")})
            if len(results) >= max(1, min(int(max_results), 10)):
                break
        if not results:
            return {"success": False, "error": "no_results", "results": [], "sources": [], "query": query}
        return {"success": True, "cached": False, "provider": "serper", "results": results, "answer": "", "query": query, "sources": [{"title": x["title"], "url": x["url"]} for x in results]}
    except Exception as exc:
        logger.warning("Serper provider failed (%s)", type(exc).__name__)
        return {"success": False, "error": "provider_unavailable", "results": [], "sources": [], "query": query}
