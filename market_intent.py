"""Telegram market-intent routing: signals only when explicitly requested."""
from __future__ import annotations

import re
from typing import Tuple


def detect_market_and_timeframe(text: str) -> Tuple[str, str]:
    """Resolve any crypto (Binance) / gold / forex (Twelve) from user text."""
    try:
        from market import resolve_trading_symbol

        symbol = resolve_trading_symbol(text or "BTC")
    except Exception:
        symbol = "BTC/USD"
        upper = (text or "").upper()
        for name, canon in (
            ("GOLD", "XAU/USD"),
            ("XAU", "XAU/USD"),
            ("BTC", "BTC/USD"),
            ("ETH", "ETH/USD"),
            ("SOL", "SOL/USD"),
        ):
            if name in upper:
                symbol = canon
                break
    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", (text or "").lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe


def detect_market_intent(text: str):
    """Only route to full MTF signal when user clearly asks for a market call.

    Normal chat must go to AIEngine. Background agent auto-push does not use this.
    """
    if not text:
        return False, "XAU/USD", "15m"
    upper = text.upper()
    lower = text.lower().strip()
    stripped = text.strip()

    try:
        from casual_mode import is_casual_chat

        if is_casual_chat(stripped):
            return False, "XAU/USD", "15m"
    except Exception:
        pass

    chat_only = [
        "how are you",
        "who are you",
        "what can you do",
        "what are you",
        "what you doing",
        "thank",
        "thanks",
        "hello",
        "hi ",
        "hey ",
        "good morning",
        "good night",
        "love you",
        "i wanna ask",
        "i want to ask",
        "can i ask",
        "ask you something",
        "ask you somthing",
        "just asking",
        "question for you",
        "are you there",
        "you there",
        "help me with",
        "explain to me",
        "tell me about yourself",
        "miss you",
        "what's up",
        "whats up",
    ]
    if any(p in lower for p in chat_only) and not any(
        k in upper for k in ("SIGNAL", "CHART", "ENTRY", "SETUP", "MTF")
    ):
        if "signal" not in lower and "chart" not in lower and "analysis" not in lower:
            return False, "XAU/USD", "15m"

    intent_keywords = [
        "analy",
        "signal",
        "chart",
        "setup",
        "entry",
        "stop loss",
        "take profit",
        "forecast",
        "predict",
        "outlook",
        "bias",
        "direction",
        "support",
        "resist",
        "tp1",
        "tp2",
        "tp3",
        "sl ",
        " rr",
        "should i buy",
        "should i sell",
        "long or short",
        "buy or sell",
        "what is the signal",
        "what's the signal",
        "whats the signal",
        "give me signal",
        "show signal",
        "send signal",
        "market analysis",
        "price action",
        "mtf",
        "multi time",
        "multi-time",
    ]
    has_intent = any(kw in lower for kw in intent_keywords)

    # Pure ticker only: "BTC", "eth 15m", "gold" — not "is sol up"
    pure_ticker = bool(
        re.fullmatch(
            r"\s*(btc|eth|sol|xau|xag|gold|silver|bitcoin|ethereum|solana|bnb|xrp)"
            r"(\s+(1m|5m|15m|30m|1h|2h|4h|1d))?\s*",
            lower,
        )
    )

    if not has_intent and not pure_ticker:
        return False, "XAU/USD", "15m"

    symbol, timeframe = detect_market_and_timeframe(text)
    return True, symbol, timeframe
