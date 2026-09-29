"""
King Zarry AI - lightweight automatic memory learner.

This module intentionally does not call an LLM. It extracts durable, user-stated
preferences/facts in the background so normal replies stay fast and API usage stays low.
It never stores obvious credentials/secrets.
"""
import re
import logging

logger = logging.getLogger("auto_learning")

_SECRET_RE = re.compile(
    r"(api[_ -]?key|password|passwd|secret|token|authorization|bearer|private key|seed phrase|mnemonic)",
    re.IGNORECASE,
)

_ASSET_MAP = {
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "solana": "SOL",
    "sol": "SOL",
    "gold": "XAU/USD",
    "xau": "XAU/USD",
    "silver": "XAG/USD",
    "xag": "XAG/USD",
    "forex": "Forex",
}

_TIMEFRAME_RE = re.compile(r"\b(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\b", re.I)


def _clean(value: str, max_len: int = 180) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" .,!?:;\"'")
    return value[:max_len].strip()


def _asset_mentions(text: str):
    found = []
    low = text.lower()
    for key, value in _ASSET_MAP.items():
        if re.search(rf"\b{re.escape(key)}\b", low) and value not in found:
            found.append(value)
    return found


def _timeframe(text: str):
    m = _TIMEFRAME_RE.search(text)
    if not m:
        return None
    n, unit = m.group(1), m.group(2).lower()
    unit = {"min": "m", "mins": "m", "minute": "m", "minutes": "m",
            "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
            "day": "d", "days": "d"}.get(unit, unit)
    return f"{n}{unit}"


def learn_from_message(memory, user_id: str, message: str) -> int:
    """Extract a small set of durable facts/preferences from a user message."""
    if not memory or not message:
        return 0
    text = _clean(message, 500)
    if len(text) < 4 or text.startswith("/") or _SECRET_RE.search(text):
        return 0

    learned = 0
    low = text.lower()

    def add(fact, category="general"):
        nonlocal learned
        fact = _clean(fact)
        if len(fact) < 3 or len(fact) > 180:
            return
        try:
            if memory.add_fact(user_id, fact, category=category, source="auto"):
                learned += 1
        except Exception as exc:
            logger.debug("Auto-memory fact save failed: %s", type(exc).__name__)

    # Identity / naming.
    for pattern in (
        r"\bmy name is\s+(.+)",
        r"\bcall me\s+(.+)",
        r"\byou can call me\s+(.+)",
    ):
        m = re.search(pattern, text, re.I)
        if m:
            name = _clean(m.group(1), 80)
            if name and not _SECRET_RE.search(name):
                try:
                    memory.update_user_profile(user_id, preferred_name=name)
                    learned += 1
                except Exception:
                    pass
            break

    # Durable preference statements.
    patterns = [
        (r"\bi prefer\s+(.+)", "preference"),
        (r"\bmy preferred\s+(.+)", "preference"),
        (r"\bi like\s+(.+)", "preference"),
        (r"\bi usually use\s+(.+)", "preference"),
        (r"\bi use\s+(.+)", "preference"),
        (r"\bmy favorite\s+(.+)", "preference"),
    ]
    for pattern, category in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = _clean(m.group(1))
            if value and len(value.split()) <= 25:
                add(f"User preference: {value}", category)
                break

    # Trading-specific durable preferences.
    assets = _asset_mentions(text)
    if assets and any(k in low for k in ("i trade", "i mainly trade", "i mostly trade", "my favorite market", "my preferred market")):
        try:
            existing = memory.get_trading_preferences(user_id) or {}
            old = existing.get("preferred_assets") or ""
            merged = [x.strip() for x in re.split(r"[,/|]", old) if x.strip()]
            for asset in assets:
                if asset not in merged:
                    merged.append(asset)
            memory.save_trading_preferences(user_id, preferred_assets=", ".join(merged))
            learned += 1
        except Exception:
            pass

    tf = _timeframe(text)
    if tf and any(k in low for k in ("timeframe", "time frame", "i trade on", "i use")):
        try:
            memory.save_trading_preferences(user_id, preferred_timeframe=tf)
            learned += 1
        except Exception:
            pass

    if any(k in low for k in ("low risk", "conservative risk", "risk averse")):
        try:
            memory.save_trading_preferences(user_id, risk_preference="low/conservative")
            learned += 1
        except Exception:
            pass
    elif any(k in low for k in ("high risk", "aggressive risk", "aggressive trader")):
        try:
            memory.save_trading_preferences(user_id, risk_preference="high/aggressive")
            learned += 1
        except Exception:
            pass

    # Explicit long-term facts.
    for pattern, category in (
        (r"\bi am from\s+(.+)", "location"),
        (r"\bi live in\s+(.+)", "location"),
        (r"\bi work as\s+(.+)", "work"),
        (r"\bi am a\s+(.+)", "profile"),
        (r"\bi'm a\s+(.+)", "profile"),
    ):
        m = re.search(pattern, text, re.I)
        if m:
            value = _clean(m.group(1), 100)
            if value and len(value.split()) <= 15:
                add(f"User said: {value}", category)
                break

    return learned
