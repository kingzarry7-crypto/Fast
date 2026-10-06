"""Persistent owner/professional profile for KZ client acquisition.

The profile is user-scoped and stored in the existing web_user_profiles.preferences
JSONB field. It contains identity/business copy only; never store API keys,
passwords, session tokens, or provider credentials here.
"""
from __future__ import annotations

import json
import re
import threading
from typing import Any, Dict

_FIELDS = (
    "display_name",
    "professional_title",
    "business_name",
    "contact_email",
    "website",
    "portfolio_url",
    "services",
    "starting_price",
    "currency",
    "tone",
)
_LOCK = threading.RLock()
_MEMORY: Dict[str, Dict[str, Any]] = {}


def _clean(value: Any, limit: int = 800) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _uid(user_id: Any) -> str:
    return _clean(user_id, 120)


def _normalise(raw: Any) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    out = {key: _clean(raw.get(key), 1200 if key == "services" else 800) for key in _FIELDS}
    out["starting_price"] = _clean(raw.get("starting_price"), 40)
    out["currency"] = _clean(raw.get("currency") or "USD", 10).upper()
    out["tone"] = _clean(raw.get("tone") or "professional", 40).lower()
    return out


def _db_get(user_id: str) -> Dict[str, Any]:
    try:
        from database import get_db_cursor
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT display_name, preferences FROM web_user_profiles WHERE user_id=%s",
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return {}
        display_name = row[0] if not isinstance(row, dict) else row.get("display_name")
        prefs = row[1] if not isinstance(row, dict) else row.get("preferences")
        if isinstance(prefs, str):
            prefs = json.loads(prefs or "{}")
        profile = (prefs or {}).get("professional_profile") if isinstance(prefs, dict) else {}
        profile = dict(profile or {})
        if not profile.get("display_name") and display_name:
            profile["display_name"] = display_name
        return _normalise(profile)
    except Exception:
        return {}


def get_profile(user_id: Any) -> Dict[str, Any]:
    uid = _uid(user_id)
    if not uid:
        return _normalise({})
    with _LOCK:
        db = _db_get(uid)
        if db:
            _MEMORY[uid] = db
            return db
        return dict(_MEMORY.get(uid) or _normalise({}))


def save_profile(user_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    uid = _uid(user_id)
    if not uid:
        raise ValueError("user_id is required")
    current = get_profile(uid)
    merged = dict(current)
    for key in _FIELDS:
        if key in data:
            merged[key] = data[key]
    merged = _normalise(merged)
    if not merged["display_name"]:
        raise ValueError("Your name/display name is required before client outreach.")
    if merged["contact_email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", merged["contact_email"]):
        raise ValueError("contact_email is not a valid email address.")
    with _LOCK:
        try:
            from database import get_db_cursor
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO web_user_profiles (user_id, display_name, preferences)
                    VALUES (%s, %s, %s::jsonb)
                    ON CONFLICT (user_id) DO UPDATE SET
                        display_name=EXCLUDED.display_name,
                        preferences=COALESCE(web_user_profiles.preferences,'{}'::jsonb)
                            || EXCLUDED.preferences,
                        updated_at=NOW()
                    """,
                    (
                        uid,
                        merged["display_name"],
                        json.dumps({"professional_profile": merged}),
                    ),
                )
        except Exception:
            _MEMORY[uid] = merged
            return merged
        _MEMORY[uid] = merged
    return merged


def profile_ready(profile: Dict[str, Any]) -> Dict[str, Any]:
    profile = _normalise(profile)
    missing = []
    for key, label in (
        ("display_name", "your name"),
        ("professional_title", "your professional title"),
        ("services", "your services"),
    ):
        if not profile.get(key):
            missing.append(label)
    return {"ready": not missing, "missing": missing}
