"""Intent isolation for iterative email-draft conversations.

This module is deliberately dependency-free so its safety rules can be tested
without making provider calls or touching connected accounts.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


_ACTIVE_DRAFT_MARKERS = (
    r"\bemail\s+draft\b",
    r"\bpending\s+email\s+draft\b",
    r"\bsubject\s*:",
    r"\bto\s*:\s*[^\s@]+@[^\s@]+",
    r"\bapproval[- ]ready\s+email\b",
)
_REVISION_MARKERS = (
    r"\b(add|include|update|revise|rewrite|change|edit|expand|shorten|improve)\b",
    r"\b(specific|details|detail|correct|correction|source\s+link|verified\s+source)\b",
    r"\b(send\s+it|send\s+the\s+email|is\s+this\s+correct|paste\s+the\s+proposal)\b",
)


def is_email_draft_followup(prompt: str, history: Iterable[dict[str, Any]] | None) -> bool:
    """Return True for revision/approval turns that refer to an active email draft."""
    current = str(prompt or "").strip()
    if not current:
        return False

    recent = list(history or [])[-8:]
    context_text = "\n".join(
        str(item.get("content") or "")
        for item in recent
        if isinstance(item, dict)
    )
    has_active_draft = any(
        re.search(marker, context_text, re.IGNORECASE | re.DOTALL)
        for marker in _ACTIVE_DRAFT_MARKERS
    )
    if not has_active_draft:
        return False

    # A short follow-up should remain attached to the draft. A new complete
    # question or a clearly different task stays on the normal chat path.
    if any(re.search(marker, current, re.IGNORECASE) for marker in _REVISION_MARKERS):
        return len(current) <= 240
    return False


EMAIL_DRAFT_REVISION_INSTRUCTIONS = """EMAIL DRAFT REVISION SAFETY:
- Treat short revision requests as edits to the current email draft, not as a request to create a new reply email.
- Keep the recipient, subject, and approved purpose unchanged unless the user explicitly asks to change them.
- Never invent release notes, product capabilities, performance improvements, or other factual update details.
- Use only facts supplied by the user or facts explicitly verified from an authoritative source that directly matches this product and release.
- Do not run broad web searches for vague revision requests such as "add specific update details" or "request a verified source link". If the exact release details or authoritative source are unavailable, say so and ask for the official changelog or release URL.
- Keep any research notes and source links outside the email body. Never append generic search-result links to the email draft.
- If the user says "send it", do not send from a text-generation response. Use the existing exact-draft approval flow and verify the actual sent message before claiming success.
- If the send result is ambiguous or unverified, do not retry automatically because the first attempt may already have been sent."""


def should_suppress_web_research_for_email_draft(is_email_context: bool) -> bool:
    """Broad web research is suppressed while revising an active email draft."""
    return bool(is_email_context)
