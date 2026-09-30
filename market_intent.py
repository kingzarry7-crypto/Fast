"""Market intent: ONLY slash commands trigger MTF signals.

Without a leading "/", messages always go to normal AI chat —
even if the user says "btc", "gold signal", "analyze eth", etc.

Slash examples that DO trigger signals:
  /btc  /eth  /sol  /xau  /gold  /signal  /signal BTC  /plan
"""
from __future__ import annotations

import re
from typing import Tuple

# Only these slash commands count as "signal mode"
_SIGNAL_SLASH_RE = re.compile(
    r"^\s*/"
    r"(?P<cmd>btc|eth|sol|xau|xag|gold|silver|bitcoin|ethereum|solana|bnb|xrp|signal|plan)"
    r"(?:\s+(?P<rest>.+))?"
    r"\s*$",
    re.IGNORECASE,
)

_TF_RE = re.compile(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", re.IGNORECASE)


def detect_market_and_timeframe(text: str) -> Tuple[str, str]:
    """Resolve symbol + timeframe from slash command text."""
    raw = (text or "").strip()
    upper = raw.upper()
    symbol = "BTC/USD"

    pairs = (
        ("XAU", "XAU/USD"),
        ("GOLD", "XAU/USD"),
        ("XAG", "XAG/USD"),
        ("SILVER", "XAG/USD"),
        ("BTC", "BTC/USD"),
        ("BITCOIN", "BTC/USD"),
        ("ETH", "ETH/USD"),
        ("ETHEREUM", "ETH/USD"),
        ("SOL", "SOL/USD"),
        ("SOLANA", "SOL/USD"),
        ("BNB", "BNB/USD"),
        ("XRP", "XRP/USD"),
    )
    m = _SIGNAL_SLASH_RE.match(raw)
    if m:
        cmd = (m.group("cmd") or "").lower()
        cmd_map = {
            "btc": "BTC/USD",
            "bitcoin": "BTC/USD",
            "eth": "ETH/USD",
            "ethereum": "ETH/USD",
            "sol": "SOL/USD",
            "solana": "SOL/USD",
            "xau": "XAU/USD",
            "gold": "XAU/USD",
            "xag": "XAG/USD",
            "silver": "XAG/USD",
            "bnb": "BNB/USD",
            "xrp": "XRP/USD",
        }
        if cmd in cmd_map:
            symbol = cmd_map[cmd]
        rest = (m.group("rest") or "").upper()
        for name, canon in pairs:
            if name in rest:
                symbol = canon
                break
    else:
        try:
            from market import resolve_trading_symbol

            symbol = resolve_trading_symbol(raw or "BTC")
        except Exception:
            for name, canon in pairs:
                if name in upper:
                    symbol = canon
                    break

    tf_m = _TF_RE.search(raw)
    timeframe = tf_m.group(1).lower() if tf_m else "15m"
    return symbol, timeframe


def detect_market_intent(text: str):
    """Return (True, symbol, tf) ONLY for slash trading commands.

    Examples:
      /btc          → signal
      /eth 1h       → signal
      /signal gold  → signal
      /plan         → signal route
      hi            → normal AI
      btc           → normal AI
      give me signal→ normal AI
      analyze eth   → normal AI
    """
    if not text:
        return False, "XAU/USD", "15m"

    stripped = text.strip()
    m = _SIGNAL_SLASH_RE.match(stripped)
    if not m:
        return False, "XAU/USD", "15m"

    symbol, timeframe = detect_market_and_timeframe(stripped)
    return True, symbol, timeframe
