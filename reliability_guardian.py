"""Layer 13 — Self-Healing & Reliability Guardian.

Observes worker failures and applies conservative recovery decisions.
It never approves consequential work or retries red-risk external actions.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict

_STATE = {"runs": 0, "failures": 0, "recoveries": 0, "last_error": None, "last_recovery": None}


def record_success() -> None:
    _STATE["runs"] += 1


def record_failure(error: Exception, *, risk: str = "green", attempts: int = 1) -> Dict[str, Any]:
    _STATE["runs"] += 1
    _STATE["failures"] += 1
    _STATE["last_error"] = type(error).__name__
    # Safe/idempotent workflow work may be retried; consequential work is surfaced.
    retryable = str(risk).lower() == "green" and attempts < 3
    decision = "retry" if retryable else "surface"
    if retryable:
        _STATE["recoveries"] += 1
        _STATE["last_recovery"] = datetime.now(timezone.utc).isoformat()
    return {"decision": decision, "retryable": retryable, "attempts": attempts, "error": type(error).__name__}


def snapshot() -> Dict[str, Any]:
    return dict(_STATE, policy="retry safe green work up to 3 attempts; surface yellow/red failures; never auto-approve")


def stale_workflow_action(status: str, age_minutes: int) -> str:
    if status == "waiting_for_approval":
        return "notify_approval"
    if status in {"approved", "executing", "researching", "verifying"} and age_minutes >= 30:
        return "resume_safe_or_surface"
    return "none"
