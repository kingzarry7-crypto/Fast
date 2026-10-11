"""Unified natural-language router for KING ZARRY Work control.

The router is intentionally conservative. It only claims a message as Work when
there is a clear work/approval signal, so normal conversation stays on the AI path.
"""
from __future__ import annotations
import re
from typing import Any

_APPROVE_RE = re.compile(r"^\s*(?:kz\s+)?(?:please\s+)?approve\s+(?:work\s+)?([0-9a-f-]{8,})\s*$", re.I)
_REJECT_RE = re.compile(r"^\s*(?:kz\s+)?(?:please\s+)?(?:reject|deny|cancel)\s+(?:work\s+)?([0-9a-f-]{8,})\s*$", re.I)
_STATUS_RE = re.compile(r"^\s*(?:kz\s+)?(?:show\s+)?(?:work\s+)?(?:status|progress)\s+(?:of\s+)?([0-9a-f-]{8,})\s*$", re.I)

_WORK_PREFIX_RE = re.compile(
    r"^\s*(?:kz|king\s+zarry|kingzarry)\s*[,!:;-]\s*"
    r"(?:please\s+)?(?P<goal>.+?)\s*$",
    re.I,
)

_WORK_PHRASES = (
    "get this done",
    "get this done for me",
    "do this for me",
    "do everything yourself",
    "do everything for me",
    "fix everything yourself",
    "fix everything for me",
    "handle everything yourself",
    "handle everything for me",
    "handle this for me",
    "work on this for me",
    "take care of this",
    "start working on",
    "work on",
    "find me",
    "find some clients",
    "find clients",
    "find freelance",
    "find opportunities",
    "make me money",
    "help me make money",
    "make money for me",
    "get me clients",
    "build this for me",
    "launch this for me",
    "fix this for me",
    "research this for me",
    "prepare this for me",
    "automate this for me",
    "keep working on this",
    "continue this for me",
    "finish this for me",
    "take over this task",
    "handle the whole thing",
    "manage this for me",
    "keep going on this",
)

def parse(text: str) -> dict[str, Any] | None:
    """Return {kind, workflow_id?, goal?} or None for normal AI chat."""
    value = str(text or "").strip()
    if not value:
        return None

    m = _APPROVE_RE.match(value)
    if m:
        return {"kind": "approve", "workflow_id": m.group(1)}
    m = _REJECT_RE.match(value)
    if m:
        return {"kind": "reject", "workflow_id": m.group(1)}
    m = _STATUS_RE.match(value)
    if m:
        return {"kind": "status", "workflow_id": m.group(1)}

    m = _WORK_PREFIX_RE.match(value)
    if m:
        goal = m.group("goal").strip()
        if goal and len(goal) <= 4000:
            return {"kind": "create", "goal": goal}

    low = value.lower()
    if any(phrase in low for phrase in _WORK_PHRASES):
        return {"kind": "create", "goal": value[:4000]}

    return None
