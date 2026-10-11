"""Intent router for King Zarry AI's existing agents and connected-account tools.

Routes only clear market-analysis and capability/access questions. Other requests
continue through the established account_agent and AIEngine paths. It never places
orders or sends external messages; consequential actions remain approval-gated.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

_ASSETS = (
    (r"\b(?:xau(?:\s*/?\s*usd)?|gold)\b", "XAU/USD"),
    (r"\b(?:btc(?:\s*/?\s*usd)?|bitcoin)\b", "BTC/USD"),
    (r"\b(?:eth(?:ereum)?(?:\s*/?\s*usd)?)\b", "ETH/USD"),
    (r"\b(?:sol(?:ana)?(?:\s*/?\s*usd)?)\b", "SOL/USD"),
    (r"\b(?:uni(?:swap)?(?:\s*/?\s*usd)?)\b", "UNI/USD"),
)
_MARKET_ACTION = re.compile(
    r"\b(signal|signals|market|price|chart|analy[sz]e|analysis|setup|"
    r"trade setup|entry|support|resistance|trend|technical|mtf|timeframe|"
    r"buy or sell|bullish|bearish|gold forecast)\b",
    re.IGNORECASE,
)
_CAPABILITY = re.compile(
    r"\b(what can you do|what tools|what agents|what access|which accounts|"
    r"connected accounts|what is connected|what's connected|show capabilities|"
    r"your capabilities|what do you have access to|what do you need access to|"
    r"what permissions|agent status|system status)\b",
    re.IGNORECASE,
)


def _asset_for(text: str) -> Optional[str]:
    for pattern, symbol in _ASSETS:
        if re.search(pattern, text or "", re.IGNORECASE):
            return symbol
    return None


def _market_requested(text: str) -> bool:
    lower = (text or "").lower()
    if not _asset_for(lower):
        return False
    # Avoid hijacking general conversation that merely mentions an asset.
    return bool(_MARKET_ACTION.search(lower))


def _connected_accounts(user_id: str) -> list[dict[str, str]]:
    try:
        from database import get_db_cursor
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """SELECT provider, display_name, provider_account_id
                   FROM web_connected_accounts
                   WHERE user_id = %s AND revoked_at IS NULL
                   ORDER BY provider, updated_at DESC""",
                (str(user_id),),
            )
            rows = cur.fetchall() or []
        seen = set()
        result = []
        for row in rows:
            try:
                provider = str(row["provider"] or "").strip().lower()
                name = str(row["display_name"] or provider).strip()
            except Exception:
                provider = str(row[0] or "").strip().lower()
                name = str(row[1] or provider).strip()
            if provider and provider not in seen:
                seen.add(provider)
                result.append({"provider": provider, "name": name})
        return result
    except Exception:
        return []


def route_agent_request(message: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Return a handled reply for explicit agent-routing requests, otherwise None."""
    text = (message or "").strip()
    if not text:
        return None

    if _CAPABILITY.search(text):
        accounts = _connected_accounts(user_id)
        account_names = ", ".join(
            f"{item['name']} ({item['provider']})" for item in accounts
        ) or "No connected provider accounts were verified for this web user."
        reply = (
            "King Zarry AI capability and access report\n\n"
            "Market & signal agent: live price/technical-analysis functions and news-risk "
            "checks are available when the configured market-data provider responds. "
            "A failed or stale data fetch must be reported as unavailable, never guessed.\n"
            "Account/workflow agent: routes supported connected-account requests through "
            "the official connector and approval/evidence path. Email, Shopify, GitHub, "
            "and browser actions depend on their provider setup, permissions, and a verified "
            "account connection. Sending, publishing, trading, or other consequential actions "
            "must not be performed without the required approval.\n"
            "Memory/learning: existing per-user conversation memory and market-scan learning "
            "are available; this is not a claim that the model retrains itself.\n"
            "Web research: use the configured research/search tools only when they are "
            "available and return evidence.\n\n"
            f"Verified connected accounts: {account_names}\n\n"
            "If a requested job cannot proceed, I should identify the exact missing connector, "
            "permission, or configuration, explain why it is needed, and give you the next "
            "connection step. I must not claim an account is connected or a job is complete "
            "without evidence."
        )
        return {"status": "completed", "reply": reply, "provider": "capability_router"}

    if not _market_requested(text):
        return None

    symbol = _asset_for(text)
    if not symbol:
        return None
    timeframe_match = re.search(r"\b(5m|15m|30m|1h|4h|1d)\b", text, re.IGNORECASE)
    timeframe = timeframe_match.group(1).lower() if timeframe_match else "15m"

    try:
        from agent_core import tool_analyze_symbol, tool_news_risk, tool_learn
        analysis = tool_analyze_symbol(symbol, timeframe=timeframe)
        if not isinstance(analysis, dict):
            analysis = {"symbol": symbol, "signal": "WAIT", "data_ok": False,
                        "error": "analysis returned no structured result"}
        news = tool_news_risk(symbol)
        analysis["news_risk"] = news if isinstance(news, dict) else {}
        try:
            tool_learn(
                user_id=str(user_id),
                symbol=symbol,
                signal=str(analysis.get("signal") or "WAIT"),
                confidence=str(analysis.get("confidence") or ""),
                notes="Web chat routed explicit market request to market agent",
                outcome="web_chat_market_request",
                meta={"timeframe": timeframe, "data_ok": bool(analysis.get("data_ok", not analysis.get("error")))},
            )
        except Exception:
            pass

        if analysis.get("error") or analysis.get("data_ok") is False:
            detail = str(analysis.get("error") or "market provider did not confirm fresh data")
            reply = (
                f"I routed this to the Market/Signal Agent for {symbol} ({timeframe}), "
                "but it could not verify fresh market data. I will not invent a price or signal.\n"
                f"Reported issue: {detail[:240]}\n"
                "Check the configured market-data provider/API key and its quota, then ask again."
            )
            return {"status": "unavailable", "reply": reply, "provider": "market_agent",
                    "operation": "analyze_market", "target": symbol}

        def show(value: Any, fallback: str = "Not provided") -> str:
            return str(value) if value not in (None, "") else fallback

        news_risk = analysis.get("news_risk") or {}
        lines = [
            f"Market Agent report — {symbol} ({timeframe})",
            f"Signal/bias: {show(analysis.get('signal') or analysis.get('direction'), 'WAIT')}",
            f"Price: {show(analysis.get('price') or analysis.get('current_price'))}",
            f"Entry: {show(analysis.get('entry') or analysis.get('entry_zone') or analysis.get('ideal_entry'))}",
            f"Stop loss: {show(analysis.get('stop_loss') or analysis.get('sl'))}",
            f"Targets: {show(analysis.get('targets') or analysis.get('take_profits') or analysis.get('tp'))}",
            f"Confidence: {show(analysis.get('confidence'))}",
            f"Trend: {show(analysis.get('trend'))}",
            f"News risk: {show(news_risk.get('risk') or news_risk.get('level') or news_risk.get('status'))}",
        ]
        reasons = analysis.get("reasons") or []
        if isinstance(reasons, str):
            reasons = [reasons]
        if reasons:
            lines.append("Agent reasoning: " + "; ".join(str(item) for item in reasons[:5]))
        lines.extend([
            "",
            "This is an agent-generated market snapshot, not a guaranteed outcome or financial advice. "
            "If data freshness, entry, stop, or targets were not returned by the agent, they are intentionally "
            "shown as not provided. No trade was placed."
        ])
        return {"status": "completed", "reply": "\n".join(lines), "provider": "market_agent",
                "operation": "analyze_market", "target": symbol}
    except Exception as exc:
        return {
            "status": "unavailable",
            "reply": (
                f"I routed your {symbol} request to the Market/Signal Agent, but it failed safely "
                f"({type(exc).__name__}). No signal or price has been fabricated and no trade was placed. "
                "Check the market-data configuration and service logs, then retry."
            ),
            "provider": "market_agent",
            "operation": "analyze_market",
            "target": symbol,
        }
