"""Normal-chat vs signal-mode detection (shared by AIEngine / web).

Rule: only slash trading commands leave casual mode.
Any free-text message (even "btc signal") stays normal AI conversation.
"""
import re

# Only these slash commands are treated as explicit trading mode
_SIGNAL_SLASH_RE = re.compile(
    r"^\s*/"
    r"(btc|eth|sol|xau|xag|gold|silver|bitcoin|ethereum|solana|bnb|xrp|signal|plan|alert)"
    r"\b",
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
    """Default normal chat. Only /btc /signal /plan etc. force non-casual."""
    t = (text or "").strip()
    if not t:
        return True
    # Slash trading command → NOT casual (signal / plan path)
    if _SIGNAL_SLASH_RE.match(t):
        return False
    # Any other slash command → still casual for the AI (help, status, etc.)
    if t.startswith("/"):
        return True
    if is_simple_greeting(t):
        return True
    # Free text always casual — AI can still talk about markets in words,
    # but bot will not auto-run the MTF signal pipeline.
    return True
