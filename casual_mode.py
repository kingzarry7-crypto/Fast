"""Normal-chat vs signal-mode detection (shared by AIEngine)."""
import re

_EXPLICIT_TRADING_PATTERN = re.compile(
    r"(?:"
    r"\b(signal|signals)\b|"
    r"\b(entry(\s+zone)?|stop\s*loss|\bsl\b|take\s*profit|\btp[123]?\b)\b|"
    r"\b(mtf|multi[- ]?timeframe)\b|"
    r"\b(analyze|analysis|analyse)\s+(btc|eth|sol|xau|gold|bitcoin|ethereum|solana|the\s+market|this\s+chart)\b|"
    r"\b(buy|sell)\s+(btc|eth|sol|xau|gold|bitcoin|ethereum|solana)\b|"
    r"\b(long|short)\s+(setup|bias|on)\b|"
    r"^\s*/?(btc|eth|sol|xau|gold|signal|plan)\b|"
    r"\b(trade\s+plan|one[- ]?day\s+plan|daily\s+plan)\b|"
    r"\b(price\s+alert|set\s+alert|alert\s+me)\b"
    r")",
    re.IGNORECASE,
)


def is_simple_greeting(text: str) -> bool:
    t = re.sub(r"[\s.!?,]+$", "", (text or "").strip().lower())
    return bool(
        re.fullmatch(
            r"(hi|hey|hello|he|hiya|yo|sup|howdy|good\s+(morning|afternoon|evening|night))",
            t,
            flags=re.IGNORECASE,
        )
    )


def is_casual_chat(text: str, has_image: bool = False, needs_web: bool = False) -> bool:
    """Default normal chat; signal mode only on explicit trading request."""
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("/"):
        if re.match(r"^/(btc|eth|sol|xau|gold|signal|plan|alert)\b", t, re.I):
            return False
        return True
    if is_simple_greeting(t):
        return True
    if _EXPLICIT_TRADING_PATTERN.search(t):
        return False
    return True
