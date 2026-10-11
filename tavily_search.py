"""
👑 KING ZARRY AI - Tavily Web Search Integration
Shared module for Telegram + Discord + AIEngine
Uses TAVILY_API_KEY env var, official tavily-python SDK
Credit-conserving: only search when current web info genuinely needed
"""
import os
import re
import logging
import time
import requests
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse, parse_qs
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("tavily_search")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"tvly-[A-Za-z0-9]{10,}", "tvly-***REDACTED***", text)
    return text

TAVILY_API_KEY = clean_env_str(os.getenv("TAVILY_API_KEY"))
TAVILY_MAX_RESULTS = int(clean_env_str(os.getenv("TAVILY_MAX_RESULTS"), "5") or "5")
TAVILY_TIMEOUT = int(clean_env_str(os.getenv("TAVILY_TIMEOUT"), "15") or "15")

# Simple in-memory cache to avoid duplicate searches in short time (conserve credits)
_search_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL = 300  # 5 minutes

def _get_cache_key(query: str, search_depth: str, max_results: int) -> str:
    return f"{query.lower().strip()}|{search_depth}|{max_results}"

def _get_cached(query: str, search_depth: str, max_results: int) -> Optional[Dict[str, Any]]:
    key = _get_cache_key(query, search_depth, max_results)
    entry = _search_cache.get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < CACHE_TTL:
            return data
        else:
            del _search_cache[key]
    return None

def _set_cache(query: str, search_depth: str, max_results: int, data: Dict[str, Any]):
    key = _get_cache_key(query, search_depth, max_results)
    _search_cache[key] = (time.time(), data)
    if len(_search_cache) > 100:
        oldest = sorted(_search_cache.items(), key=lambda x: x[1][0])[0][0]
        del _search_cache[oldest]

def _fallback_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Keyless backup search using DuckDuckGo HTML. Never returns fabricated results."""
    class _ResultsParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.results = []
            self.current = None
            self.capture = None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            classes = set((attrs.get("class") or "").split())
            if tag == "a" and "result__a" in classes:
                self.current = {"title": "", "url": attrs.get("href", ""), "content": ""}
                self.capture = "title"
            elif self.current is not None and tag in ("a", "div", "span") and ("result__snippet" in classes):
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
                    target = parse_qs(urlparse(href).query).get("uddg", [""])[0]
                    href = target or href
                self.current["url"] = href
                self.results.append(self.current)
                self.current = None
                self.capture = None
            elif self.capture == "content" and tag in ("div", "span"):
                self.capture = None

    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "KingZarryAI/1.0 (web search fallback)"},
            timeout=min(max(TAVILY_TIMEOUT, 3), 10),
        )
        response.raise_for_status()
        parser = _ResultsParser()
        parser.feed(response.text)
        results = []
        seen = set()
        for item in parser.results:
            url = item.get("url", "").strip()
            title = " ".join(item.get("title", "").split()).strip()
            if not url.startswith(("http://", "https://")) or not title or url in seen:
                continue
            seen.add(url)
            results.append({
                "title": title[:200],
                "url": url,
                "content": " ".join(item.get("content", "").split())[:800],
                "score": 0,
                "published_date": "",
            })
            if len(results) >= max(1, min(max_results, 10)):
                break
        if not results:
            return {"success": False, "error": "fallback_no_results", "results": [], "answer": "", "query": query, "sources": []}
        output = {
            "success": True,
            "cached": False,
            "provider": "duckduckgo_fallback",
            "results": results,
            "answer": "",
            "query": query,
            "sources": [{"title": item["title"], "url": item["url"]} for item in results],
        }
        logger.warning("Search fallback succeeded for '%s' with %s results", query[:60], len(results))
        return output
    except Exception as exc:
        logger.warning("Search fallback failed for '%s': %s", query[:60], _redact(str(exc)))
        return {"success": False, "error": "fallback_unavailable", "results": [], "answer": "", "query": query, "sources": []}


def _try_fallback(query: str, max_results: int, original_error: str) -> Dict[str, Any]:
    result = _fallback_search(query, max_results=max_results)
    if result.get("success") and result.get("results"):
        _set_cache(query, "fallback", max_results, result)
        return result
    result["primary_error"] = original_error
    return result


def is_tavily_configured() -> bool:
    return bool(TAVILY_API_KEY)

def get_client():
    if not is_tavily_configured():
        return None
    try:
        from tavily import TavilyClient
        return TavilyClient(api_key=TAVILY_API_KEY)
    except Exception as e:
        logger.warning(f"Tavily SDK import failed: {_redact(str(e))}")
        return None

def should_trigger_tavily(user_text: str) -> bool:
    """
    Credit-conserving decision: only trigger for queries that need current web info
    Returns False for greetings, jokes, simple chat
    NOTE: Does NOT check if Tavily is configured - caller should check is_tavily_configured() separately
    This allows testing trigger logic even without API key
    """
    if not user_text:
        return False
    text = user_text.lower().strip()
    if len(text) < 3:
        return False

    no_trigger_patterns = [
        r"^\s*hello\b", r"^\s*hi\b", r"^\s*hey\b", r"^\s*how are you",
        r"^\s*tell me a joke", r"^\s*joke\b", r"^\s*thanks\b", r"^\s*thank you",
        r"^\s*good morning", r"^\s*good night", r"^\s*bye\b",
        r"^\s*/start", r"^\s*/help", r"^\s*/btc", r"^\s*/eth", r"^\s*/sol", r"^\s*/xau", r"^\s*/signal", r"^\s*/plan", r"^\s*/alert", r"^\s*/notify",
    ]
    for pat in no_trigger_patterns:
        if re.search(pat, text):
            if not any(k in text for k in ["news", "latest", "today", "happening", "why", "moving", "search", "research", "regulation", "fed", "fomc", "breaking"]):
                return False

    trigger_keywords = [
        "latest", "today", "right now", "current", "breaking", "just happened",
        "what happened", "why is", "why are", "why did", "moving today", "moving now",
        "news", "happening", "update", "announcement", "regulation", "fed", "fomc",
        "powell", "sec", "etf", "halving", "inflation", "cpi", "nfp", "rate cut", "rate hike",
        "search the web", "search for", "research", "look up", "find latest",
    ]
    market_terms = ["btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xau", "gold", "crypto", "dollar", "usd"]

    if any(k in text for k in ["search the web", "search for the latest", "research the latest", "look up latest", "browse web"]):
        return True

    has_trigger = any(k in text for k in trigger_keywords)
    if not has_trigger:
        return False

    if "news" in text or "latest" in text or "today" in text or "breaking" in text or "happening" in text:
        return True

    if has_trigger and any(m in text for m in market_terms):
        return True

    return has_trigger

def search_web(query: str, max_results: int = 5, search_depth: str = "basic", include_answer: bool = True, include_domains: Optional[List[str]] = None) -> Dict[str, Any]:
    if not is_tavily_configured():
        return _try_fallback(query, max_results, "Tavily not configured")

    cached = _get_cached(query, search_depth, max_results)
    if cached:
        logger.info(f"Tavily cache hit for: {query[:60]}")
        cached_result = dict(cached)
        cached_result["cached"] = True
        return cached_result

    client = get_client()
    if not client:
        return _try_fallback(query, max_results, "Tavily client init failed")

    try:
        kwargs = {
            "query": query,
            "max_results": min(max_results, 10),
            "search_depth": search_depth,
            "include_answer": include_answer,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains

        resp = client.search(**kwargs)

        results = resp.get("results", []) if isinstance(resp, dict) else []
        answer = resp.get("answer", "") if isinstance(resp, dict) else ""
        query_used = resp.get("query", query) if isinstance(resp, dict) else query

        normalized = []
        for r in results[:max_results]:
            if not isinstance(r, dict):
                continue
            normalized.append({
                "title": r.get("title", "")[:200],
                "url": r.get("url", ""),
                "content": r.get("content", "")[:800],
                "score": r.get("score", 0),
                "published_date": r.get("published_date", ""),
            })

        output = {
            "success": True,
            "cached": False,
            "results": normalized,
            "answer": answer[:1500] if answer else "",
            "query": query_used,
            "sources": [{"title": x["title"], "url": x["url"]} for x in normalized],
        }
        _set_cache(query, search_depth, max_results, output)
        logger.info(f"Tavily search success: '{query[:60]}' -> {len(normalized)} results")
        return output

    except Exception as e:
        err_msg = _redact(str(e))
        logger.warning(f"Tavily search failed for '{query[:60]}': {err_msg}")
        low = err_msg.lower()
        # Tavily uses 432 for the account's configured plan limit and 433 for
        # the pay-as-you-go cap. Distinguish these from transient rate limits so
        # the caller can report the real action needed instead of retrying blindly.
        if "432" in low or "plan limit exceeded" in low or "usage limit" in low:
            error_code = "plan_limit_exceeded"
        elif "433" in low or "pay-as-you-go limit" in low:
            error_code = "payg_limit_exceeded"
        elif "429" in low or "rate limit" in low or "too many" in low:
            error_code = "rate_limit"
        else:
            error_code = "search_failed"
        return _try_fallback(query, max_results, error_code)

def extract_url(url: str, query: Optional[str] = None) -> Dict[str, Any]:
    if not is_tavily_configured() or not url:
        return {"success": False, "content": "", "url": url}
    client = get_client()
    if not client:
        return {"success": False, "content": "", "url": url}
    try:
        resp = client.extract(urls=[url], query=query, extract_depth="basic")
        results = resp.get("results", []) if isinstance(resp, dict) else []
        if results:
            first = results[0]
            return {"success": True, "content": first.get("content", "")[:3000], "url": url, "title": first.get("title", "")}
        return {"success": False, "content": "", "url": url}
    except Exception as e:
        logger.warning(f"Tavily extract failed for {url}: {_redact(str(e))}")
        return {"success": False, "content": "", "url": url}

def format_for_ai(search_result: Dict[str, Any], max_content_chars: int = 3000) -> str:
    if not search_result.get("success") or not search_result.get("results"):
        return ""
    parts = []
    if search_result.get("answer"):
        parts.append(f"TAVILY SUMMARY: {search_result['answer']}")
    parts.append("\nWEB SOURCES:")
    total_chars = len("\n".join(parts))
    for idx, r in enumerate(search_result["results"][:5], 1):
        entry = f"{idx}. {r.get('title','')}\n   URL: {r.get('url','')}\n   Content: {r.get('content','')[:400]}"
        if total_chars + len(entry) > max_content_chars:
            break
        parts.append(entry)
        total_chars += len(entry)
    return "\n".join(parts)

def provider_status() -> Dict[str, Any]:
    return {
        "configured": is_tavily_configured(),
        "has_key": bool(TAVILY_API_KEY),
        "max_results_default": TAVILY_MAX_RESULTS,
        "timeout": TAVILY_TIMEOUT,
        "cache_size": len(_search_cache),
    }
