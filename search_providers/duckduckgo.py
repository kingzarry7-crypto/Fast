"""Keyless DuckDuckGo HTML search adapter used as a final fallback."""
import logging
import os
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
import requests

logger = logging.getLogger(__name__)

class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results, self.current, self.capture = [], None, None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self.current = {"title": "", "url": attrs.get("href", ""), "content": ""}
            self.capture = "title"
        elif self.current is not None and tag in ("a", "div", "span") and "result__snippet" in classes:
            self.capture = "content"
    def handle_data(self, data):
        if self.current is not None and self.capture in ("title", "content"):
            self.current[self.capture] += data
    def handle_endtag(self, tag):
        if self.current is not None and tag == "a" and self.capture == "title":
            href = self.current.get("url", "")
            if href.startswith("//"):
                href = "https:" + href
            if "duckduckgo.com/l/?" in href:
                href = parse_qs(urlparse(href).query).get("uddg", [""])[0] or href
            self.current["url"] = href
            self.results.append(self.current)
            self.current, self.capture = None, None
        elif self.capture == "content" and tag in ("div", "span"):
            self.capture = None

def search(query: str, max_results: int = 5, timeout: int = 8) -> dict:
    try:
        response = requests.get("https://html.duckduckgo.com/html/", params={"q": query},
            headers={"User-Agent": "KingZarryAI/1.0 (web search fallback)"},
            timeout=max(3, min(int(timeout), 10)))
        response.raise_for_status()
        parser = _Parser()
        parser.feed(response.text)
        results, seen = [], set()
        for item in parser.results:
            url = str(item.get("url") or "").strip()
            title = " ".join(str(item.get("title") or "").split()).strip()
            if not url.startswith(("http://", "https://")) or not title or url in seen:
                continue
            seen.add(url)
            results.append({"title": title[:200], "url": url,
                "content": " ".join(str(item.get("content") or "").split())[:800],
                "score": 0, "published_date": ""})
            if len(results) >= max(1, min(int(max_results), 10)):
                break
        if not results:
            return {"success": False, "error": "fallback_no_results", "results": [], "answer": "", "query": query, "sources": []}
        return {"success": True, "cached": False, "provider": "duckduckgo_fallback",
            "results": results, "answer": "", "query": query,
            "sources": [{"title": x["title"], "url": x["url"]} for x in results]}
    except Exception as exc:
        logger.warning("DuckDuckGo fallback failed (%s)", type(exc).__name__)
        return {"success": False, "error": "fallback_unavailable", "results": [], "answer": "", "query": query, "sources": []}
