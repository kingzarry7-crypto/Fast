"""Explainable Gmail priority helpers for King Zarry AI."""
from __future__ import annotations

import re
from typing import Any


def classify_email(message: dict[str, Any]) -> dict[str, str]:
    """Classify based on provider data and explain the classification."""
    subject = str(message.get("subject") or "")
    sender = str(message.get("from") or message.get("sender") or "")
    snippet = str(message.get("snippet") or message.get("summary") or "")
    text = f"{subject} {sender} {snippet}".lower()

    if re.search(r"\b(security alert|suspicious sign.?in|account compromised|password reset|verify your account|unauthorized access|fraud alert|payment failed|legal notice)\b", text, re.I):
        return {"priority": "high", "reason": "Security warning or potentially time-sensitive issue"}
    if re.search(r"\b(urgent|action required|immediate action|final notice|overdue|past due|deadline today|due today|expires today|interview invitation|job offer|offer letter)\b", text, re.I):
        return {"priority": "high", "reason": "Urgent wording, deadline, or important opportunity"}
    if re.search(r"\b(please reply|please respond|let me know|action needed|needs your approval|meeting invitation|interview|invoice|receipt|application update|order confirmation|delivery issue|appointment)\b", text, re.I):
        return {"priority": "medium", "reason": "Requests a response or concerns a practical task"}
    if re.search(r"\b(unsubscribe|newsletter|weekly digest|sale ends|special offer|limited-time offer|marketing|promotion|promotional)\b", text, re.I) or re.search(r"\b(no.?reply|newsletter|marketing|promotions|mailer-daemon)\b", sender, re.I):
        return {"priority": "low", "reason": "Newsletter, promotional content, or routine automated sender"}
    return {"priority": "medium", "reason": "New message; review may be useful"}


def summarize_email(message: dict[str, Any], limit: int = 220) -> str:
    """Use only Gmail's actual preview; do not invent missing content."""
    snippet = re.sub(r"\s+", " ", str(message.get("snippet") or "")).strip()
    if not snippet:
        return "Gmail did not provide a preview; open the message to inspect its contents."
    if len(snippet) > limit:
        return snippet[: max(0, limit - 1)].rstrip() + "…"
    return snippet


def enrich_email(message: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(message)
    triage = classify_email(enriched)
    enriched["priority"] = triage["priority"]
    enriched["priority_reason"] = triage["reason"]
    enriched["summary"] = summarize_email(enriched)
    enriched["suggested_action"] = {
        "high": "Review this message now; confirm before taking any external action.",
        "medium": "Review the message and reply or follow up if needed.",
        "low": "Include it in the routine summary; no immediate action suggested.",
    }[triage["priority"]]
    return enriched


def format_email_alert(message: dict[str, Any]) -> str:
    """Format a concise alert for a real new Gmail message."""
    priority = str(message.get("priority") or "medium").upper()
    sender = str(message.get("from") or message.get("sender") or "Unknown sender")
    subject = str(message.get("subject") or "(no subject)")
    reason = str(message.get("priority_reason") or "New message")
    summary = str(message.get("summary") or summarize_email(message))
    action = str(message.get("suggested_action") or "Review if needed.")
    return (
        f"📧 {priority} PRIORITY EMAIL\n"
        f"From: {sender[:240]}\n"
        f"Subject: {subject[:240]}\n"
        f"Why: {reason}\n"
        f"Summary: {summary}\n"
        f"Suggested next step: {action}\n"
        "KZ has not replied, forwarded, deleted, or modified this email."
    )


def format_email_digest(messages: list[dict[str, Any]]) -> str:
    """Group low-priority messages into a bounded digest."""
    if not messages:
        return "No routine emails to summarize."
    lines = [f"📬 Gmail routine summary — {len(messages)} email(s)"]
    for item in messages[:5]:
        sender = str(item.get("from") or item.get("sender") or "Unknown sender")[:100]
        subject = str(item.get("subject") or "(no subject)")[:140]
        lines.append(f"• {subject} — {sender}")
    if len(messages) > 5:
        lines.append(f"Plus {len(messages) - 5} more routine email(s). Ask KZ to show them when needed.")
    return "\n".join(lines)
