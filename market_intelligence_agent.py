"""
KING ZARRY AI — Market Intelligence Agent

A separate intelligence layer from the existing signal Agent.
It scans the approved delivery universe, reads market structure/news/macro context,
then produces a non-trading intelligence brief. It must never manufacture prices
or turn an intelligence brief into a BUY/SELL/entry/SL/TP recommendation.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("king_zarry_market_intel")

INTELLIGENCE_SYMBOLS = [
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XAU/USD",
    "UNI/USD",
]

_ASSET_NAMES = {
    "BTC/USD": "Bitcoin",
    "ETH/USD": "Ethereum",
    "SOL/USD": "Solana",
    "XAU/USD": "Gold",
    "UNI/USD": "Uniswap",
}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _upper(value: Any, default: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text or default


def _market_regime(snapshot: Dict[str, Any]) -> str:
    trend = _upper(snapshot.get("trend"))
    structure = _upper(snapshot.get("structure"))
    volatility = _upper(snapshot.get("volatility"))

    if trend in {"BULLISH", "BEARISH"} and structure in {"BULLISH", "BEARISH"}:
        base = f"{trend} trend / {structure} structure"
    elif trend in {"BULLISH", "BEARISH"}:
        base = f"{trend} trend"
    elif structure in {"BULLISH", "BEARISH"}:
        base = f"{structure} structure"
    else:
        base = "mixed / unclear structure"

    if volatility in {"HIGH", "EXTREME"}:
        base += f" / {volatility.lower()} volatility"
    return base


def _market_snapshot(symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "name": _ASSET_NAMES.get(symbol, symbol),
        "price": data.get("price"),
        "trend": _upper(data.get("trend")),
        "structure": _upper(data.get("structure")),
        "volatility": _upper(data.get("volatility")),
        "rsi": data.get("rsi"),
        "confidence": data.get("confidence"),
        "strength": data.get("strength"),
        "news_risk": _upper(data.get("news_risk"), "LOW"),
        "regime": _market_regime(data),
        "data_ok": bool(data.get("data_ok", True)) and not data.get("error"),
        "reason": str(data.get("reason") or data.get("error") or "")[:180],
    }


def _news_snapshot(symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    headlines = data.get("headlines") or []
    events = data.get("events") or []
    return {
        "symbol": symbol,
        "risk": _upper(data.get("risk") or data.get("news_risk"), "LOW"),
        "summary": str(data.get("summary") or "")[:280],
        "headlines": [
            {
                "title": str(h.get("title") or "")[:180],
                "source": str(h.get("source") or "")[:80],
                "url": str(h.get("url") or h.get("link") or "")[:400],
            }
            for h in headlines[:4]
            if isinstance(h, dict)
        ],
        "events": [
            {
                "event": str(e.get("event") or e.get("name") or "")[:160],
                "time": str(e.get("time") or e.get("date") or "")[:80],
                "impact": _upper(e.get("impact") or e.get("importance"), "UNKNOWN"),
                "currency": str(e.get("currency") or "")[:20],
            }
            for e in events[:6]
            if isinstance(e, dict)
        ],
    }


def _global_headline_snapshot(items: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in (items or [])[:8]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "title": str(item.get("title") or item.get("headline") or "")[:180],
                "source": str(item.get("source") or item.get("provider") or "")[:80],
                "url": str(item.get("url") or item.get("link") or "")[:400],
            }
        )
    return out


def _event_snapshot(items: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in (items or [])[:10]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "event": str(item.get("event") or item.get("name") or "")[:160],
                "time": str(item.get("time") or item.get("date") or "")[:80],
                "impact": _upper(item.get("impact") or item.get("importance"), "UNKNOWN"),
                "currency": str(item.get("currency") or "")[:20],
                "country": str(item.get("country") or "")[:60],
            }
        )
    return out


def _cross_market_read(markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    readable = [m for m in markets if m.get("data_ok")]
    trends = [_upper(m.get("trend")) for m in readable]
    structures = [_upper(m.get("structure")) for m in readable]
    risks = [_upper(m.get("news_risk"), "LOW") for m in readable]

    trend_counts = {
        "bullish": sum(1 for x in trends if x == "BULLISH"),
        "bearish": sum(1 for x in trends if x == "BEARISH"),
        "mixed": sum(1 for x in trends if x not in {"BULLISH", "BEARISH"}),
    }
    structure_counts = {
        "bullish": sum(1 for x in structures if x == "BULLISH"),
        "bearish": sum(1 for x in structures if x == "BEARISH"),
        "mixed": sum(1 for x in structures if x not in {"BULLISH", "BEARISH"}),
    }

    high_risk_assets = [
        str(m.get("symbol"))
        for m in readable
        if _upper(m.get("news_risk"), "LOW") in {"HIGH", "EXTREME"}
    ]

    crypto = [m for m in readable if str(m.get("symbol")) in {"BTC/USD", "ETH/USD", "SOL/USD", "UNI/USD"}]
    crypto_bull = sum(1 for m in crypto if _upper(m.get("trend")) == "BULLISH")
    crypto_bear = sum(1 for m in crypto if _upper(m.get("trend")) == "BEARISH")

    if crypto and crypto_bull == len(crypto):
        crypto_regime = "broad crypto bullish alignment"
    elif crypto and crypto_bear == len(crypto):
        crypto_regime = "broad crypto bearish alignment"
    elif crypto:
        crypto_regime = "mixed crypto alignment"
    else:
        crypto_regime = "crypto data unavailable"

    return {
        "trend_counts": trend_counts,
        "structure_counts": structure_counts,
        "high_news_risk_assets": high_risk_assets,
        "crypto_regime": crypto_regime,
        "risk_assets_count": len(high_risk_assets),
        "assets_with_data": len(readable),
        "assets_requested": len(INTELLIGENCE_SYMBOLS),
    }


def _deterministic_assessment(
    markets: List[Dict[str, Any]],
    news: List[Dict[str, Any]],
    macro_events: List[Dict[str, str]],
    cross: Dict[str, Any],
) -> str:
    lines = [
        "MARKET REGIME",
        f"Crypto: {cross.get('crypto_regime', 'unknown')}.",
        (
            "Across the five tracked assets: "
            f"{cross['trend_counts']['bullish']} bullish trend, "
            f"{cross['trend_counts']['bearish']} bearish trend, "
            f"{cross['trend_counts']['mixed']} mixed/unclear."
        ),
        (
            "Structure: "
            f"{cross['structure_counts']['bullish']} bullish, "
            f"{cross['structure_counts']['bearish']} bearish, "
            f"{cross['structure_counts']['mixed']} mixed/unclear."
        ),
    ]

    risky = cross.get("high_news_risk_assets") or []
    if risky:
        lines.append("RISK RADAR: " + ", ".join(risky) + " currently carries HIGH/EXTREME news risk.")
    else:
        lines.append("RISK RADAR: no tracked asset currently reports HIGH/EXTREME news risk.")

    notable = [n for n in news if n.get("summary")]
    if notable:
        lines.append("NEWS: " + " ".join(str(n["summary"])[:220] for n in notable[:3]))

    high_events = [e for e in macro_events if str(e.get("impact")).upper() in {"HIGH", "VERY HIGH", "EXTREME", "3", "RED"}]
    if high_events:
        lines.append(
            "MACRO CALENDAR: "
            + "; ".join(
                f"{e.get('event')} ({e.get('currency') or 'global'})"
                for e in high_events[:4]
            )
        )
    else:
        lines.append("MACRO CALENDAR: no high-impact event was returned by the configured calendar.")

    lines.append("This intelligence layer describes conditions; it does not issue trade entries, stops or targets.")
    return "\n".join(lines)


def _ai_synthesis(context: Dict[str, Any]) -> str:
    """Use the application's provider failover chain for a second-pass narrative."""
    try:
        from ai_engine import AIEngine, clean_ai_response

        prompt = (
            "You are the KING ZARRY MARKET INTELLIGENCE AGENT. "
            "Synthesize the supplied live application data into a concise market-intelligence brief. "
            "This is NOT a trading signal request. Do NOT output BUY, SELL, WAIT, entries, stop-losses, "
            "take-profits, price targets, or trading instructions. Do not invent missing data. "
            "Focus on regime, cross-asset alignment/divergence, macro catalysts, headline themes, "
            "volatility/risk conditions, and what facts should be watched next. "
            "State uncertainty explicitly when data is missing. "
            "Use plain language and compact sections: REGIME, CATALYSTS, CROSS-MARKET, RISK RADAR, WATCH NEXT.\n\n"
            "LIVE DATA (application-supplied; do not override it with invented facts):\n"
            + json.dumps(context, ensure_ascii=False, default=str)[:24000]
        )
        engine = AIEngine(memory=None)
        result = engine.ask("market-intelligence-agent", prompt)
        result = clean_ai_response(result or "")
        forbidden = ("entry", "stop loss", "take profit", "price target", "BUY", "SELL")
        if result and not any(token.lower() in result.lower() for token in forbidden):
            return result[:6000]
    except Exception as exc:
        logger.info("Market intelligence AI synthesis unavailable: %s", type(exc).__name__)
    return ""


def build_market_intelligence(
    focus: Optional[str] = None,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """Build a real-data intelligence report for the five approved markets."""
    focus_norm = str(focus or "").strip().upper()
    if focus_norm:
        aliases = {
            "BTC": "BTC/USD",
            "ETH": "ETH/USD",
            "SOL": "SOL/USD",
            "XAU": "XAU/USD",
            "GOLD": "XAU/USD",
            "UNI": "UNI/USD",
        }
        focus_norm = aliases.get(focus_norm, focus_norm)
        if focus_norm not in INTELLIGENCE_SYMBOLS:
            raise ValueError("Focus must be BTC, ETH, SOL, XAU or UNI.")

    symbols = [focus_norm] if focus_norm else list(INTELLIGENCE_SYMBOLS)

    from agent_core import tool_analyze_symbol
    from news_engine import news_engine

    markets: Dict[str, Dict[str, Any]] = {}
    news: Dict[str, Dict[str, Any]] = {}

    def fetch_one(symbol: str) -> Dict[str, Any]:
        try:
            market = tool_analyze_symbol(symbol, "15m")
        except Exception as exc:
            market = {"symbol": symbol, "signal": "WAIT", "error": type(exc).__name__, "data_ok": False}
        try:
            asset_news = news_engine.get_news_for_asset(symbol) or {}
        except Exception as exc:
            asset_news = {"symbol": symbol, "risk": "UNKNOWN", "error": type(exc).__name__}
        return {
            "symbol": symbol,
            "market": _market_snapshot(symbol, market if isinstance(market, dict) else {}),
            "news": _news_snapshot(symbol, asset_news if isinstance(asset_news, dict) else {}),
        }

    with ThreadPoolExecutor(max_workers=min(5, len(symbols) or 1)) as pool:
        futures = [pool.submit(fetch_one, symbol) for symbol in symbols]
        for future in as_completed(futures):
            item = future.result()
            markets[item["symbol"]] = item["market"]
            news[item["symbol"]] = item["news"]

    market_list = [markets[s] for s in symbols if s in markets]
    news_list = [news[s] for s in symbols if s in news]

    try:
        global_news = _global_headline_snapshot(news_engine.get_global_news(limit=8))
    except Exception:
        global_news = []

    try:
        macro_events = _event_snapshot(news_engine.get_upcoming_events(24))
    except Exception:
        macro_events = []

    crypto_vision: Dict[str, Any] = {}
    try:
        from ai_engine import AIEngine
        crypto_vision = AIEngine(memory=None).crypto_vision_intelligence() or {}
    except Exception:
        crypto_vision = {}

    cross = _cross_market_read(market_list)

    context = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "focus": focus_norm or "ALL",
        "markets": market_list,
        "asset_news": news_list,
        "global_headlines": global_news,
        "macro_events": macro_events,
        "cross_market": cross,
        "crypto_intelligence_available": bool(crypto_vision),
    }

    deterministic = _deterministic_assessment(market_list, news_list, macro_events, cross)
    narrative = _ai_synthesis(context) if use_ai else ""
    if not narrative:
        narrative = deterministic

    return {
        "status": "success",
        "agent": "market_intelligence",
        "generated_at": context["generated_at"],
        "focus": focus_norm or None,
        "symbols": symbols,
        "markets": market_list,
        "asset_news": news_list,
        "global_headlines": global_news,
        "macro_events": macro_events,
        "cross_market": cross,
        "crypto_intelligence_available": bool(crypto_vision),
        "assessment": deterministic,
        "narrative": narrative,
    }


def format_market_intelligence(report: Dict[str, Any]) -> str:
    focus = report.get("focus") or "ALL FIVE MARKETS"
    lines = [
        "🤖 <b>KING ZARRY MARKET INTELLIGENCE</b>",
        f"Focus: <b>{str(focus)}</b>",
        f"Updated: <b>{str(report.get('generated_at') or '')}</b>",
        "",
    ]

    narrative = str(report.get("narrative") or "").strip()
    if narrative:
        # The narrative has already been safety-filtered in _ai_synthesis.
        lines.append(narrative[:6000])
        lines.append("")

    lines.extend(
        [
            "<b>ASSET SNAPSHOT</b>",
        ]
    )
    for item in (report.get("markets") or [])[:5]:
        lines.append(
            f"• <b>{item.get('symbol')}</b> — "
            f"{item.get('regime', 'unknown')} | "
            f"News: {item.get('news_risk', 'UNKNOWN')}"
        )

    events = report.get("macro_events") or []
    if events:
        lines.append("")
        lines.append("<b>MACRO NEXT 24H</b>")
        for event in events[:5]:
            lines.append(
                f"• {str(event.get('event') or '')[:100]} — "
                f"{str(event.get('impact') or 'UNKNOWN')} "
                f"{str(event.get('currency') or '')}"
            )

    lines.append("")
    lines.append("<i>Intelligence only — this agent does not issue trade entries or targets.</i>")
    return "\n".join(lines)[:9000]
