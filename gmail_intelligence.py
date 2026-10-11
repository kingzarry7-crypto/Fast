"""Deterministic Gmail triage helpers used by King Zarry AI monitoring.

Classification is deliberately explainable and conservative. It does not act on
messages; it only labels and summarizes the provider data returned by Gmail.
"""
from __future__ import annotations

import re
from typing import Any

_HIGH_PATTERNS = (
    (r"\\b(security alert|suspicious sign.?in|account compromised|password reset|verify your account|unauthorized access)\\b",
     "Security or account-access warning"),
    (r"\\b(urgent|action required|immediate action|final notice|overdue|past due|deadline today|due today|expires today)\\b",
     "Urgent wording or a near-term deadline"),
    (r"\\b(interview invitation|job offer|offer letter|contract offer|payment failed|fraud alert|legal notice)\\b",
     "Potentially time-sensitive opportunity or issue"),
)
_MEDIUM_PATTERNS = (
    (r"\\b(please reply|please respond|let me know|action needed|needs your approval|meeting invitation|interview|invoice|receipt|application update|order confirmation|delivery issue|appointment)\\b",
     "Requests a response or concerns a practical task"),
)
_LOW_PATTERNS = (
    (r"\\b(unsubscribe|newsletter|weekly digest|sale ends|special offer|limited-time offer|marketing|promotion|promotional)\\b",
     "Newsletter or promotional content"),
)
_LOW_SENDERS = (r"no.?reply", r"newsletter", r"marketing", r"promotions", r"mailer-daemon")


def classify_email(message: dict[str, Any]) -> dict[str, str]:
    """Return priority and a human-readable reason based on available email fields."""
    subject = str(message.get("subject") or "")
    sender = str(message.get("from") or message.get("sender") or "")
    snippet = str(message.get("snippet") or message.get("summary") or "")
    content = f"{subject} {sender} {snippet}".lower()

    for pattern, reason in _HIGH_PATTERNS:
        if re.search(pattern, content, re.I):
            return {"priority": "high", "reason": reason}

    # Marketing/newsletter evidence should not override explicit action requests.
    for pattern, reason in _MEDIUM_PATTERNS:
        if re.search(pattern, content, re.I):
            return {"priority": "medium", "reason": reason}

    for pattern, reason in _LOW_PATTERNS:
        if re.search(pattern, content, re.I):
            return {"priority": "low", "reason": reason}
    if any(re.search(pattern, sender, re.I) for pattern in _LOW_SENDERS):
        return {"priority": "low", "reason": "Automated newsletter or routine sender"}

    return {"priority": "medium", "reason": "New message; review may be useful"}


def summarize_email(message: dict[str, Any], limit: int = 220) -> str:
    """Summarize only the provider snippet; never invent missing message content."""
    snippet = re.sub(r"\\s+", " ", str(message.get("snippet") or "")).strip()
    if not snippet:
        return "Gmail did not provide a preview; open the message to inspect its contents."
    if len(snippet) > limit:
        return snippet[: max(0, limit - 1)].rstrip() + "…"
    return snippet


def enrich_email(message: dict[str, Any]) -> dict[str, Any]:
    """Return provider message fields plus explainable triage fields."""
    enriched = dict(message)
    triage = classify_email(enriched)
    enriched["priority"] = triage["priority"]
    enriched["priority_reason"] = triage["reason"]
    enriched["summary"] = summarize_email(enriched)
    if triage["priority"] == "high":
        enriched["suggested_action"] = "Review this message now; confirm before taking any external action."
    elif triage["priority"] == "medium":
        enriched["suggested_action"] = "Review the message and reply or follow up if needed."
    else:
        enriched["suggested_action"] = "Include it in the routine summary; no immediate action suggested."
    return enriched


def format_email_alert(message: dict[str, Any]) -> str:
    """Format one triaged email as a concise cross-platform plain-text alert."""
    priority = str(message.get("priority") or "medium").upper()
    sender = str(message.get("from") or message.get("sender") or "Unknown sender")
    subject = str(message.get("subject") or "(no subject)")
    reason = str(message.get("priority_reason") or "New message")
    summary = str(message.get("summary") or summarize_email(message))
    action = str(message.get("suggested_action") or "Review if needed.")
    return (
        f"📧 {priority} PRIORITY EMAIL\\n"
        f"From: {sender[:240]}\\n"
        f"Subject: {subject[:240]}\\n"
        f"Why: {reason}\\n"
        f"Summary: {summary}\\n"
        f"Suggested next step: {action}\\n"
        "KZ has not replied, forwarded, deleted, or modified this email."
    )


def format_email_digest(messages: list[dict[str, Any]]) -> str:
    """Group routine messages into one short digest instead of individual alerts."""
    if not messages:
        return "No routine emails to summarize."
    lines = [f"📬 Gmail routine summary — {len(messages)} email(s)"]
    for message in messages[:5]:
        sender = str(message.get("from") or message.get("sender") or "Unknown sender")[:100]
        subject = str(message.get("subject") or "(no subject)")[:140]
        lines.append(f"• {subject} — {sender}")
    if len(messages) > 5:
        lines.append(f"Plus {len(messages) - 5} more routine email(s). Ask KZ to show them when needed.")
    return "\\n".join(lines)
