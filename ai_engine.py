# ai_engine.py — bootstrap restore + normal-chat default
# Loads last known-good engine, then overrides casual detection so normal
# messages ("hi", "what are you doing") are NOT forced into signal mode.

import re
import urllib.request

_GOOD_URL = (
    "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/"
    "f814fb1811b1193eddc7aa5129d087145a9de0fa/ai_engine.py"
)

_src = urllib.request.urlopen(_GOOD_URL, timeout=60).read().decode("utf-8")
exec(compile(_src, "ai_engine_restored.py", "exec"), globals())

# --- Override: default to normal chat; signals only when explicitly requested ---
try:
    from casual_mode import is_casual_chat as _is_casual_chat, is_simple_greeting as _is_simple_greeting
except Exception:
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

    def _is_simple_greeting(text: str) -> bool:
        t = re.sub(r"[\s.!?,]+$", "", (text or "").strip().lower())
        return bool(
            re.fullmatch(
                r"(hi|hey|hello|he|hiya|yo|sup|howdy|good\s+(morning|afternoon|evening|night))",
                t,
                flags=re.IGNORECASE,
            )
        )

    def _is_casual_chat(text: str, has_image: bool = False, needs_web: bool = False) -> bool:
        t = (text or "").strip()
        if not t:
            return False
        if t.startswith("/"):
            if re.match(r"^/(btc|eth|sol|xau|gold|signal|plan|alert)\b", t, re.I):
                return False
            return True
        if _is_simple_greeting(t):
            return True
        if _EXPLICIT_TRADING_PATTERN.search(t):
            return False
        return True
