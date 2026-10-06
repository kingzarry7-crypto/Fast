"""KING ZARRY AI — autonomous opportunity hunter.

Read-only public opportunity discovery. It classifies the source before acquisition
so KZ does not mistake a marketplace, recruiter, or job-board page for a direct client.
It never sends outreach, spends money, places trades, or claims revenue.
"""
from __future__ import annotations

import re
import time
import hashlib
from typing import Any, Dict, List
from urllib.parse import urlparse

DEFAULT_QUERIES = {
    "clients": [
        '"need a website" freelance web developer',
        '"looking for a web developer" website',
        '"hire a web developer" small business',
        '"website redesign" "web developer"',
    ],
    "jobs": [
        "remote freelance web developer project",
        "small business website development contract",
        "landing page developer freelance project",
    ],
    "saas": [
        "small business software problem opportunity SaaS",
        "business automation software opportunity",
    ],
}

PLATFORM_DOMAINS = {
    "fiverr.com", "upwork.com", "toptal.com", "freelancer.com",
    "peopleperhour.com", "guru.com", "workana.com", "contra.com",
    "linkedin.com", "indeed.com", "glassdoor.com",
}
RECRUITER_WORDS = ("recruit", "staffing", "talent", "agency", "placement", "careers")
JOB_WORDS = ("job", "jobs", "freelance", "contract", "vacancy", "position", "hiring", "developer")

def _clean(value: Any, limit: int = 700) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]

def _domain(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""

def classify_source(url: str, title: str = "", summary: str = "", category: str = "clients") -> Dict[str, Any]:
    domain = _domain(url)
    text = f"{title} {summary} {url}".lower()
    platform = any(domain == d or domain.endswith("." + d) for d in PLATFORM_DOMAINS)
    recruiter = any(word in text for word in RECRUITER_WORDS)
    job_signal = any(word in text for word in JOB_WORDS)
    if platform and domain == "fiverr.com":
        kind = "marketplace"
    elif platform and domain == "toptal.com":
        kind = "recruiter_platform"
    elif recruiter:
        kind = "recruiter"
    elif platform or job_signal or category == "jobs":
        kind = "job_board"
    else:
        kind = "direct_client"
    direct = kind == "direct_client"
    if direct:
        instruction = "Treat as a possible direct client; verify the person/company and active project before outreach."
    elif kind == "marketplace":
        instruction = "Treat as a marketplace listing; apply through the marketplace workflow, not as direct-client outreach."
    elif kind in {"recruiter", "recruiter_platform"}:
        instruction = "Treat as a recruiter/platform opportunity; do not claim the platform is the client."
    else:
        instruction = "Treat as a job-board listing; prepare an application for the listed role rather than a direct-client sales message."
    return {"kind": kind, "domain": domain, "direct_client": direct, "instruction": instruction}

def _score(item: Dict[str, Any], category: str) -> Dict[str, Any]:
    text = (_clean(item.get("title")) + " " + _clean(item.get("content") or item.get("page_text"), 1400)).lower()
    score, reasons = 0, []
    if any(x in text for x in ("hire", "looking for", "need a", "seeking", "wanted")):
        score += 30; reasons.append("clear demand signal")
    if any(x in text for x in ("website", "web developer", "landing page", "redesign")):
        score += 25; reasons.append("matches web-development services")
    if any(x in text for x in ("contract", "freelance", "project", "paid", "budget")):
        score += 20; reasons.append("commercial/project signal")
    if category == "saas" and any(x in text for x in ("automation", "workflow", "software", "saas")):
        score += 15; reasons.append("software/automation signal")
    if any(x in text for x in ("urgent", "asap", "deadline", "this week")):
        score += 10; reasons.append("time-sensitive signal")
    return {"score": min(score, 100), "confidence": "high" if score >= 70 else "medium" if score >= 45 else "low", "reasons": reasons[:5]}

def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen, out = set(), []
    for item in items:
        url = _clean(item.get("final_url") or item.get("url"), 1200)
        title = _clean(item.get("title"), 300).lower()
        key = hashlib.sha1((url.lower() or title).encode("utf-8")).hexdigest()
        if key not in seen:
            seen.add(key); out.append(item)
    return out

def _search(query: str, max_results: int) -> Dict[str, Any]:
    try:
        from web_research_engine import research
        result = research(query, deep=False, max_results=max_results)
        if result.get("success"):
            return result
    except Exception:
        pass
    try:
        from tavily_search import search_web
        result = search_web(query, max_results=max_results, search_depth="advanced", include_answer=False)
        if result.get("success"):
            return {"success": True, "results": result.get("results") or result.get("sources") or [], "sources": result.get("sources") or []}
    except Exception:
        pass
    return {"success": False, "results": [], "sources": []}

def hunt(user_id: str, category: str = "clients", query: str = "", max_results: int = 12) -> Dict[str, Any]:
    category = category if category in DEFAULT_QUERIES else "clients"
    queries = [_clean(query, 500)] if query.strip() else list(DEFAULT_QUERIES[category])
    rows, sources = [], []
    for q in queries[:4]:
        result = _search(q, max(3, min(max_results, 10)))
        rows.extend(result.get("results") or [])
        sources.extend(result.get("sources") or [])
        if len(rows) >= max_results * 2:
            break
    opportunities = []
    for item in _dedupe(rows):
        url = _clean(item.get("final_url") or item.get("url"), 1200)
        if not url.startswith(("https://", "http://")):
            continue
        title = _clean(item.get("title") or "Opportunity", 300)
        snippet = _clean(item.get("content") or item.get("page_text"), 1000)
        scoring = _score(item, category)
        if scoring["score"] < 25:
            continue
        source = classify_source(url, title, snippet, category)
        if category == "clients" and source["kind"] in {"job_board", "recruiter", "recruiter_platform", "marketplace"}:
            # Keep these as research findings, but do not label them direct-client leads.
            scoring["reasons"] = ["source is " + source["kind"].replace("_", " ")] + scoring["reasons"][:4]
        opportunities.append({
            "id": hashlib.sha1((url + title).encode()).hexdigest()[:12],
            "category": category, "title": title, "url": url, "domain": source["domain"],
            "summary": snippet, **scoring,
            "source_kind": source["kind"], "direct_client": source["direct_client"],
            "source_instruction": source["instruction"],
            "estimated_value": _estimate_value(category, scoring["score"]),
            "next_action": source["instruction"],
            "discovered_at": int(time.time()),
        })
    opportunities.sort(key=lambda x: (x["score"], x["confidence"]), reverse=True)
    source_map = {}
    for source in sources:
        url = _clean(source.get("url"), 1200)
        if url: source_map[url] = {"title": _clean(source.get("title") or "Source", 300), "url": url}
    return {
        "success": bool(opportunities), "category": category, "query": query or None,
        "opportunities": opportunities[:max(3, min(max_results, 30))],
        "sources": list(source_map.values())[:20], "searched_queries": queries,
        "count": min(len(opportunities), max_results),
        "disclaimer": "Public research signals only. Verify availability, terms, identity, and payment before acting. No revenue is guaranteed.",
    }

def _estimate_value(category: str, score: int) -> float:
    if category == "clients": return 80.0 if score < 60 else 180.0 if score < 80 else 350.0
    if category == "jobs": return 150.0 if score < 60 else 300.0 if score < 80 else 750.0
    return 100.0 if score < 60 else 250.0 if score < 80 else 500.0

def create_work_for_opportunity(user_id: str, opportunity: Dict[str, Any]) -> Dict[str, Any]:
    from workflow_engine import create_workflow
    title = _clean(opportunity.get("title") or "opportunity")
    url = _clean(opportunity.get("url"), 1200)
    kind = _clean(opportunity.get("source_kind") or "unknown", 80)
    goal = (
        f"Prepare an approval-ready application for this {kind} opportunity: {title}. "
        f"Source: {url}. First verify the source type and requirements. Do not contact anyone, "
        f"submit an application, spend money, or claim the source is the client. Draft the "
        f"appropriate application/proposal and wait for explicit approval."
    )
    return create_workflow(str(user_id), goal)
