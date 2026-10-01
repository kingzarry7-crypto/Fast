"""
KING ZARRY AI — Market Intelligence Agent.

Separate from the Signal Agent:
- scans the five approved delivery markets
- combines market regime, macro calendar, headlines and crypto intelligence
- produces descriptive market context, not a BUY/SELL signal
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("king_zarry_intelligence")

INTELLIGENCE_SYMBOLS = [
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XAU/USD",
    "UNI/USD",
]


def _clean(value: Any, limit: int = 220) -> str:
    text = str(value or "").strip().replace("\n", " ")
    return text[:limit]


def _headline_items(news: Dict[str, Any], limit: int = 3) -> List[Dict[str, str]]:
    items = []
    for item in (news.get("headlines") or [])[:limit]:
        if not isinstance(item, dict):
            continue
        items.append({
            "title": _clean(item.get("title"), 180),
            "source": _clean(item.get("source"), 80),
            "url": _clean(item.get("url") or item.get("link"), 500),
        })
    return items


def _asset_snapshot(data: Dict[str, Any], news: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "symbol": data.get("symbol"),
        "price": data.get("price"),
        "signal": str(data.get("signal") or "WAIT").upper(),
        "trend": _clean(data.get("trend")),
        "structure": _clean(data.get("structure")),
        "confidence": data.get("confidence"),
        "strength": data.get("strength"),
        "rsi": data.get("rsi"),
        "volatility": _clean(data.get("volatility")),
        "news_risk": _clean(news.get("risk") or news.get("news_risk") or "UNKNOWN"),
        "headlines": _headline_items(news),
    }


async def _analyze(symbol: str) -> Dict[str, Any]:
    from agent_core import tool_analyze_symbol
    from news_engine import news_engine

    market, news = await asyncio.gather(
        asyncio.to_thread(tool_analyze_symbol, symbol, "15m"),
        asyncio.to_thread(news_engine.get_news_for_asset, symbol),
    )
    return _asset_snapshot(market or {}, news or {})


async def build_market_intelligence() -> Dict[str, Any]:
    """Build a fresh intelligence snapshot from real application data."""
    from news import get_economic_events
    from ai_engine import get_crypto_vision_intelligence

    assets = await asyncio.gather(*[_analyze(s) for s in INTELLIGENCE_SYMBOLS], return_exceptions=True)

    clean_assets = []
    errors = []
    for symbol, item in zip(INTELLIGENCE_SYMBOLS, assets):
        if isinstance(item, Exception):
            errors.append(f"{symbol}: {type(item).__name__}")
            clean_assets.append({
                "symbol": symbol,
                "signal": "WAIT",
                "news_risk": "UNKNOWN",
                "error": type(item).__name__,
            })
        else:
            clean_assets.append(item)

    try:
        events = await asyncio.to_thread(get_economic_events, 2)
    except Exception as exc:
        events = []
        errors.append(f"calendar: {type(exc).__name__}")

    high_events = []
    for event in events[:30]:
        if not isinstance(event, dict):
            continue
        impact = str(event.get("impact") or event.get("importance") or "").upper()
        if impact in {"HIGH", "VERY HIGH", "EXTREME", "3", "RED"}:
            high_events.append({
                "event": _clean(event.get("event"), 160),
                "currency": _clean(event.get("currency"), 20),
                "time": _clean(event.get("time"), 80),
                "impact": impact,
            })

    try:
        crypto = await asyncio.to_thread(get_crypto_vision_intelligence)
        if not isinstance(crypto, dict):
            crypto = {}
    except Exception as exc:
        crypto = {}
        errors.append(f"crypto_intelligence: {type(exc).__name__}")

    return {
        "status": "success",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markets": clean_assets,
        "macro": {"high_impact_events": high_events[:12], "event_count": len(events)},
        "crypto_intelligence": {
            "sentiment": crypto.get("sentiment"),
            "fear_greed": crypto.get("fear_greed"),
            "narratives": (crypto.get("narratives") or [])[:8],
            "whales": (crypto.get("whales") or [])[:8],
            "breaking": (crypto.get("breaking") or [])[:8],
        },
        "errors": errors,
        "note": "Intelligence summarizes current conditions. It does not create or push trade signals.",
    }


def format_market_intelligence(data: Dict[str, Any]) -> str:
    lines = [
        "🤖 KING ZARRY MARKET INTELLIGENCE",
        "",
        f"Updated: {_clean(data.get('generated_at'), 40)}",
        "",
    ]

    for market in data.get("markets", []):
        symbol = market.get("symbol", "?")
        lines.append(
            f"• {symbol}: {market.get('trend') or 'UNKNOWN'} | "
            f"structure={market.get('structure') or 'UNKNOWN'} | "
            f"news={market.get('news_risk') or 'UNKNOWN'}"
        )
        headlines = market.get("headlines") or []
        if headlines:
            lines.append(f"  News: {_clean(headlines[0].get('title'), 150)}")

    events = (data.get("macro") or {}).get("high_impact_events") or []
    lines.extend(["", f"📅 High-impact macro events: {len(events)}"])
    for event in events[:5]:
        lines.append(
            f"• {event.get('event')} | {event.get('currency') or '-'} | "
            f"{event.get('impact') or '-'} | {event.get('time') or '-'}"
        )

    crypto = data.get("crypto_intelligence") or {}
    sentiment = crypto.get("sentiment")
    if sentiment:
        lines.extend(["", f"🧠 Crypto sentiment: {_clean(sentiment, 180)}"])

    fg = crypto.get("fear_greed")
    if isinstance(fg, dict):
        lines.append(
            f"Fear & Greed: {fg.get('value') or fg.get('score') or '?'} "
            f"({fg.get('classification') or fg.get('label') or ''})"
        )

    narratives = crypto.get("narratives") or []
    if narratives:
        lines.append("Narratives:")
        for item in narratives[:5]:
            if isinstance(item, dict):
                lines.append(f"• {_clean(item.get('theme') or item.get('name') or item)}")

    lines.extend(["", "This is market intelligence, not a trade signal."])
    return "\n".join(lines)


def get_market_intelligence() -> Dict[str, Any]:
    """Synchronous wrapper for Telegram/API callers."""
    return asyncio.run(build_market_intelligence())
