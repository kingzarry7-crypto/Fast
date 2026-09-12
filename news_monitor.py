"""Existing news monitor helpers with a read-only, process-local context cache."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

_market_context: dict[str, dict[str, Any]] = {}


def cache_market_context(symbol: str, context: dict[str, Any]) -> None:
    """Store the latest monitor result; callers own refresh/scheduling."""
    _market_context[symbol.upper()] = {"context": context, "refreshed_at": datetime.now(timezone.utc).isoformat()}


def get_recent_market_context(symbol: str, max_age_seconds: int = 1800) -> dict[str, Any]:
    """Return cached news context without starting a monitor or network request."""
    record = _market_context.get(symbol.upper())
    if not record:
        return {"available": False, "stale": True, "symbol": symbol, "context": None, "refreshed_at": None}
    try:
        refreshed = datetime.fromisoformat(record["refreshed_at"])
        age = (datetime.now(timezone.utc) - refreshed).total_seconds()
    except (KeyError, TypeError, ValueError):
        age = max_age_seconds + 1
    return {"available": age <= max_age_seconds, "stale": age > max_age_seconds, "symbol": symbol, "context": record.get("context"), "refreshed_at": record.get("refreshed_at")}
