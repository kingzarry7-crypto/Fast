"""Existing news integration plus conservative asset-relevance helpers."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

HIGH_IMPACT_TERMS = ("cpi", "nfp", "fomc", "interest rate", "rate decision", "gdp", "pce", "unemployment", "central bank", "geopolitical", "regulatory")
ASSET_TERMS = {"BTC": ("bitcoin", "btc", "crypto"), "ETH": ("ethereum", "eth"), "SOL": ("solana", "sol"), "XAU/USD": ("gold", "xau", "federal reserve", "dollar")}


def get_relevant_market_news(symbol: str, articles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Normalize already-fetched news; never invent an event when the provider is unavailable."""
    if not articles:
        return {"available": False, "symbol": symbol, "items": [], "high_risk": False, "refreshed_at": None, "reason": "Current news is unavailable."}
    terms = ASSET_TERMS.get(symbol.upper(), (symbol.lower(),))
    items = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        relevant = any(term.lower() in text for term in terms)
        high_risk = any(term in text for term in HIGH_IMPACT_TERMS)
        if relevant or high_risk:
            items.append({"headline": article.get("title"), "source": article.get("source"), "timestamp": article.get("published_at") or article.get("timestamp"), "affected_asset": symbol, "relevance": "high" if relevant else "medium", "potential_market_impact": "high-risk" if high_risk else "context", "high_risk_event": high_risk, "fact": article.get("title") or article.get("description")})
    return {"available": True, "symbol": symbol, "items": items, "high_risk": any(item["high_risk_event"] for item in items), "refreshed_at": datetime.now(timezone.utc).isoformat()}
