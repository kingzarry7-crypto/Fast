"""Real per-user Settings control plane for the web app.

The Settings page uses this module for persistent Neon-backed chat behavior.
The module is additive: if Neon/settings storage is unavailable, existing chat
continues unchanged rather than failing.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from fastapi import Request, HTTPException

logger = logging.getLogger("kz_web_settings")

DEFAULTS = {
    "signalsOnly": True,
    "humanReplies": True,
    "rememberPreferences": True,
    "riskReminder": True,
}


def _user_id(row, row_value=None) -> str:
    if row_value is not None:
        try:
            value = row_value(row, "id", 0)
            if value is not None:
                return str(value)
        except Exception:
            pass
    if isinstance(row, dict):
        return str(row.get("id") or "")
    try:
        return str(row[0])
    except Exception:
        return ""


def _normalise(raw: Any) -> Dict[str, bool]:
    out = dict(DEFAULTS)
    if isinstance(raw, dict):
        for key in DEFAULTS:
            if isinstance(raw.get(key), bool):
                out[key] = raw[key]
    return out


def _read_settings(user_id: str, get_db_cursor) -> Dict[str, bool]:
    if not user_id or get_db_cursor is None:
        return dict(DEFAULTS)
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_user_settings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL UNIQUE REFERENCES web_users(id) ON DELETE CASCADE,
                    ai_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
                    trading_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                    notification_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                    interface_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                "SELECT ai_settings FROM web_user_settings WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return dict(DEFAULTS)
        value = row[0] if not isinstance(row, dict) else row.get("ai_settings")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = {}
        if isinstance(value, dict):
            return _normalise(value.get("chat_behavior"))
    except Exception as exc:
        logger.warning("Settings read skipped: %s", type(exc).__name__)
    return dict(DEFAULTS)


def _write_settings(user_id: str, preferences: Dict[str, bool], get_db_cursor) -> Dict[str, bool]:
    if not user_id or get_db_cursor is None:
        raise RuntimeError("settings storage unavailable")
    payload = json.dumps({"chat_behavior": preferences})
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS web_user_settings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL UNIQUE REFERENCES web_users(id) ON DELETE CASCADE,
                ai_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
                trading_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                notification_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                interface_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            INSERT INTO web_user_settings (user_id, ai_settings)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (user_id) DO UPDATE SET
                ai_settings = COALESCE(web_user_settings.ai_settings, '{}'::jsonb)
                    || EXCLUDED.ai_settings,
                updated_at = NOW()
            """,
            (user_id, payload),
        )
    return preferences


def install_web_settings(
    app,
    *,
    require_current_user,
    get_db_cursor,
    row_value=None,
):
    if app is None or require_current_user is None:
        raise RuntimeError("web settings requires app and auth")

    @app.get("/api/settings/preferences")
    def get_settings(request: Request):
        row = require_current_user(request)
        uid = _user_id(row, row_value)
        if not uid:
            raise HTTPException(status_code=401, detail="Authenticated user id unavailable")
        return {"status": "ok", "preferences": _read_settings(uid, get_db_cursor)}

    @app.post("/api/settings/preferences")
    async def save_settings(request: Request):
        row = require_current_user(request)
        uid = _user_id(row, row_value)
        if not uid:
            raise HTTPException(status_code=401, detail="Authenticated user id unavailable")
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Settings object required")

        current = _read_settings(uid, get_db_cursor)
        next_values = dict(current)
        for key in DEFAULTS:
            if key in body:
                if not isinstance(body[key], bool):
                    raise HTTPException(status_code=400, detail=f"{key} must be boolean")
                next_values[key] = body[key]

        try:
            saved = _write_settings(uid, next_values, get_db_cursor)
        except Exception as exc:
            logger.exception("Settings write failed")
            raise HTTPException(status_code=503, detail="Settings storage is unavailable") from exc
        return {"status": "ok", "preferences": saved}


def install_ai_settings_behavior(get_db_cursor):
    """Apply saved chat behavior to every AIEngine instance without replacing AIEngine."""
    try:
        import ai_engine
    except Exception as exc:
        logger.warning("AI settings behavior skipped: %s", type(exc).__name__)
        return

    if getattr(ai_engine.AIEngine, "_kz_settings_behavior_installed", False):
        return

    original_context = ai_engine.AIEngine._load_persistent_context
    original_save = ai_engine.AIEngine._save_memory

    def load_context_with_settings(self, user_id):
        base = original_context(self, user_id)
        uid = str(user_id or "")
        if uid.startswith("web:"):
            uid = uid[4:]
        prefs = _read_settings(uid, get_db_cursor)
        directives = [
            "",
            "--- SAVED CHAT BEHAVIOR SETTINGS ---",
        ]
        if prefs["signalsOnly"]:
            directives.append(
                "Only provide trading signals, entries, stop-loss/take-profit setups or market trade ideas when the user clearly asks for them."
            )
        else:
            directives.append(
                "The user allows proactive market/trading commentary when it is genuinely relevant. Do not force a signal into unrelated conversation."
            )
        if prefs["humanReplies"]:
            directives.append(
                "Use the configured warm, natural, human-style King Zarry voice."
            )
        else:
            directives.append(
                "Use a neutral professional assistant tone instead of the warm close-friend style."
            )
        if prefs["riskReminder"]:
            directives.append(
                "When you provide a trade setup, include the app's short risk reminder."
            )
        else:
            directives.append(
                "Do not add the optional short risk-reminder line under trade signals; still communicate material uncertainty and risk honestly."
            )
        directives.append(
            "The Remember my preferences setting is "
            + ("ON: durable user-stated preferences may be learned." if prefs["rememberPreferences"] else "OFF: do not extract new durable preferences from this user's messages.")
        )
        directives.append("--- END SAVED CHAT BEHAVIOR SETTINGS ---")
        extra = "\n".join(directives)
        return (base + "\n\n" + extra).strip() if base else extra.strip()

    def save_memory_with_setting(self, user_id, prompt, response):
        if not self.memory:
            return
        try:
            self.memory.add_message(user_id, "user", prompt)
            self.memory.add_message(user_id, "assistant", response)
            uid = str(user_id or "")
            if uid.startswith("web:"):
                uid = uid[4:]
            prefs = _read_settings(uid, get_db_cursor)
            if not prefs["rememberPreferences"]:
                return
            try:
                from auto_learning import learn_from_message
                learned = learn_from_message(self.memory, str(user_id), str(prompt))
                if learned:
                    logger.info("Auto-learning saved %s durable item(s) for %s", learned, user_id)
            except Exception as learn_exc:
                logger.debug("Auto-learning skipped: %s", type(learn_exc).__name__)
        except Exception as exc:
            logger.warning("Memory save failed for %s: %s", str(user_id)[:8], type(exc).__name__)

    ai_engine.AIEngine._load_persistent_context = load_context_with_settings
    ai_engine.AIEngine._save_memory = save_memory_with_setting
    ai_engine.AIEngine._kz_settings_behavior_installed = True
    logger.info("REAL_SETTINGS_AI_BEHAVIOR_INSTALLED")
