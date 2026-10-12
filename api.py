import json
"""
KING ZARRY AI - WEB API
WEB ONLY - Secure Neon authentication and web chat

- Uses Neon PostgreSQL via DATABASE_URL
- Never touches Telegram SQLite databases
- Never instantiates Memory() for web requests
- Uses secure scrypt password hashing
- Uses hashed session tokens in web_sessions
- Uses HttpOnly session cookies
- Protects /api/chat with authentication
- Uses a web-only memory adapter for AIEngine
- NEW: Injects live market data for BTC/ETH/SOL/XAU/UNI
- NEW: Supports image upload via base64 in /api/chat
- FIXED: WebMemoryAdapter.add_message now writes to web_messages (matches get_history)
"""

import os
import re
import hmac
import base64
import hashlib
import secrets
import asyncio
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import uvicorn

try:
    from kitty_api import router as kitty_api_router
except Exception as _kitty_api_import_error:
    kitty_api_router = None
    logging.getLogger("king_zarry_api").exception("Kitty V3 API unavailable: %s", type(_kitty_api_import_error).__name__)

from ai_engine import AIEngine

try:
    from connector_api import router as connector_api_router
except Exception as _connector_api_import_error:
    connector_api_router = None
    logging.getLogger("king_zarry_api").exception(
        "Official connector API unavailable: %s", type(_connector_api_import_error).__name__
    )

try:
    from google_connector import router as google_connector_router
except Exception as _google_connector_import_error:
    google_connector_router = None
    logging.getLogger("king_zarry_api").exception(
        "Google connector API unavailable: %s", type(_google_connector_import_error).__name__
    )

try:
    from plugin_registry import router as plugin_registry_router
except Exception as _plugin_registry_import_error:
    plugin_registry_router = None
    logging.getLogger("king_zarry_api").exception(
        "Plugin registry unavailable: %s", type(_plugin_registry_import_error).__name__
    )

try:
    from fiverr_api import router as fiverr_api_router
except Exception as _fiverr_api_import_error:
    fiverr_api_router = None
    logging.getLogger("king_zarry_api").exception(
        "Fiverr Agent API unavailable: %s: %s",
        type(_fiverr_api_import_error).__name__,
        _fiverr_api_import_error,
    )
from database import (
    get_db_cursor,
    is_database_configured,
    check_database_health,
)

try:
    from neon_memory import NeonMemory
except Exception:
    NeonMemory = None

# External Agent Action Gateway is additive: existing Signal/Intelligence/Chat flows remain unchanged.
try:
    from agent_action_gateway import (
        connector_status as _connector_status,
        account_snapshot as _account_snapshot,
        create_action as _create_action,
        approve_action as _approve_action,
        list_actions as _list_actions,
    )
except Exception as _action_import_error:
    _connector_status = _account_snapshot = _create_action = _approve_action = _list_actions = None
    logging.getLogger("king_zarry_api").warning(
        "Action Gateway unavailable: %s", type(_action_import_error).__name__
    )

logger = logging.getLogger("kingzarry_api")

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="KingZarry AI Web API",
    version="1.0.0",
)

# ============================================================
# CONFIGURATION
# ============================================================

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    os.getenv("FRONTEND_ORIGIN", "https://fast.kingzarry7.workers.dev"),
).strip().rstrip("/")
# Ignore a stale Vercel URL left in Railway variables: Cloudflare is the
# production frontend and the backend must not redirect users back to Vercel.
if ".vercel.app" in FRONTEND_URL.lower():
    FRONTEND_URL = "https://fast.kingzarry7.workers.dev"

SESSION_COOKIE_NAME = "king_zarry_web_session"

try:
    SESSION_DAYS = max(
        1,
        min(
            int(os.getenv("WEB_SESSION_DAYS", "30")),
            365,
        ),
    )
except Exception:
    SESSION_DAYS = 30

IS_PRODUCTION = (
    os.getenv("ENVIRONMENT", "").lower() == "production"
    or os.getenv("RAILWAY_ENVIRONMENT", "").lower() == "production"
)

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in FRONTEND_URL.split(",")
    if origin.strip()
]

# Keep the current production frontend hosts accepted even if Railway still
# has an older FRONTEND_URL value. This is additive; it does not expose
# credentials or bypass the authenticated session checks.
for _origin in (
    "https://kingzarry.bid",
    "https://www.kingzarry.bid",
    "https://app.kingzarry.bid",
    "https://fast.kingzarry7.workers.dev",
):
    if _origin not in allowed_origins:
        allowed_origins.append(_origin)

if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

if fiverr_api_router is not None:
    app.include_router(fiverr_api_router)

if connector_api_router is not None:
    app.include_router(connector_api_router)

if google_connector_router is not None:
    app.include_router(google_connector_router)

if plugin_registry_router is not None:
    app.include_router(plugin_registry_router)

if kitty_api_router is not None:
    app.include_router(kitty_api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Fiverr-Agent-Key",
    ],
)

# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=255,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )
    # Optional: continue a specific conversation (new chat = omit or null)
    conversation_id: Optional[str] = None
    # NEW: Optional image upload support via base64
    image_base64: Optional[str] = None
    image_mime: Optional[str] = "image/jpeg"

# ============================================================
# GENERAL HELPERS
# ============================================================

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(
        r"([?&]key=)[^&\s\"']+",
        r"\1***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-.]+",
        r"\1***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"sk-[A-Za-z0-9]{10,}",
        "sk-***REDACTED***",
        text,
    )
    return text[:500]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return str(email).strip().lower()


def _normalize_username(
    username: Optional[str],
) -> Optional[str]:

    if username is None:
        return None

    value = str(username).strip().lower()

    if not value:
        return None

    if not re.fullmatch(
        r"[a-z0-9_]{3,100}",
        value,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Username must contain only lowercase "
                "letters, numbers, and underscores."
            ),
        )

    return value


def _safe_display_name(
    display_name: Optional[str],
    fallback: str,
) -> str:

    value = str(display_name or "").strip()

    if not value:
        value = fallback

    return value[:255]


def _row_value(
    row: Any,
    key: str,
    index: int = 0,
) -> Any:

    if row is None:
        return None

    if isinstance(row, dict):
        return row.get(key)

    try:
        return row[index]
    except Exception:
        return None


def _user_public_data(row: Any) -> Dict[str, Any]:
    user_id = str(_row_value(row, "id", 0))
    email = str(_row_value(row, "email", 1) or "").strip().lower()
    sub = _get_web_subscription(user_id)
    is_sub = bool(sub.get("is_subscribed"))
    plan = sub.get("plan")
    expires = sub.get("expires_at")
    is_admin = False
    try:
        is_admin = bool(email) and _is_admin_email(email)
    except NameError:
        # ADMIN helpers defined later in module — resolve from env directly
        raw = ",".join(
            [os.getenv("ADMIN_EMAILS") or "", os.getenv("ADMIN_EMAIL") or ""]
        )
        admins = {
            p.strip().strip(chr(34) + chr(39)).lower()
            for p in raw.split(",")
            if p.strip() and "@" in p
        }
        is_admin = email in admins
    if is_admin:
        is_sub = True
        plan = plan or "admin"
    return {
        "id": user_id,
        "email": _row_value(row, "email", 1),
        "username": _row_value(row, "username", 2),
        "display_name": _row_value(row, "display_name", 3),
        "account_status": _row_value(row, "account_status", 4),
        "created_at": str(_row_value(row, "created_at", 5)),
        "is_subscribed": is_sub,
        "plan": plan,
        "subscription_expires_at": expires,
        "is_admin": is_admin,
    }

# ============================================================
# PASSWORD HASHING
# ============================================================

def _hash_password(password: str) -> str:

    if not password:
        raise ValueError(
            "Password cannot be empty"
        )

    salt = secrets.token_bytes(16)

    n = 16384
    r = 8
    p = 1

    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=64,
    )

    salt_text = base64.urlsafe_b64encode(
        salt
    ).decode("ascii")

    hash_text = base64.urlsafe_b64encode(
        derived_key
    ).decode("ascii")

    return (
        f"scrypt${n}${r}${p}"
        f"${salt_text}${hash_text}"
    )


def _verify_password(
    password: str,
    stored_hash: str,
) -> bool:

    try:
        parts = str(
            stored_hash
        ).split("$")

        if len(parts) != 6:
            return False

        (
            algorithm,
            n_text,
            r_text,
            p_text,
            salt_text,
            hash_text,
        ) = parts

        if algorithm != "scrypt":
            return False

        n = int(n_text)
        r = int(r_text)
        p = int(p_text)

        salt = base64.urlsafe_b64decode(
            salt_text.encode("ascii")
        )

        expected_hash = (
            base64.urlsafe_b64decode(
                hash_text.encode("ascii")
            )
        )

        actual_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected_hash),
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash,
        )

    except Exception:
        return False

# ============================================================
# SESSION HELPERS
# ============================================================

def _create_raw_session_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_session_token(
    raw_token: str,
) -> str:
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def _session_expiry() -> datetime:
    return (
        _utc_now()
        + timedelta(days=SESSION_DAYS)
    )


def _set_session_cookie(
    response: Response,
    raw_token: str,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        expires=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True if IS_PRODUCTION else False,
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )


def _clear_session_cookie(
    response: Response,
) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=True if IS_PRODUCTION else False,
        samesite="none" if IS_PRODUCTION else "lax",
        path="/",
    )

# ============================================================
# WEB-ONLY MEMORY ADAPTER
# ============================================================

class WebMemoryAdapter:
    def __init__(self, web_user_id: str, conversation_id: Optional[str] = None):
        self.web_user_id = str(web_user_id)
        self.conversation_id = str(conversation_id) if conversation_id else None
        self.shared = None
        try:
            if NeonMemory and os.getenv("DATABASE_URL"):
                self.shared = NeonMemory()
        except Exception as exc:
            logger.warning("Shared Neon memory unavailable for web: %s", type(exc).__name__)

    def get_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        try:
            limit = max(1, min(int(limit), 50))
            with get_db_cursor(commit=False) as cur:
                cur.execute(
                    """
                    SELECT m.role, m.content, m.created_at
                    FROM web_messages m
                    JOIN web_conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = %s
                      AND (%s IS NULL OR m.conversation_id = %s)
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (self.web_user_id, self.conversation_id, self.conversation_id, limit),
                )
                rows = cur.fetchall()
            result = []
            for row in reversed(rows):
                result.append({
                    "role": str(_row_value(row, "role", 0)),
                    "content": str(_row_value(row, "content", 1)),
                    "created_at": str(_row_value(row, "created_at", 2)),
                })
            return result
        except Exception as exc:
            logger.warning("WebMemoryAdapter.get_history failed: %s", type(exc).__name__)
            return []

    def get_trading_context(self, user_id: str) -> str:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT trading_preferences FROM web_user_settings WHERE user_id = %s", (self.web_user_id,))
                row = cur.fetchone()
            if not row:
                return ""
            preferences = _row_value(row, "trading_preferences", 0)
            if not preferences:
                return ""
            if isinstance(preferences, dict):
                lines = [f"{key}: {value}" for key, value in preferences.items() if value]
                return "\n".join(lines)[:1000]
            return str(preferences)[:1000]
        except Exception:
            return ""

    def get_facts(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        try:
            limit = max(1, min(int(limit), 50))
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT content, memory_type, created_at FROM web_ai_memories WHERE user_id = %s AND memory_type IN ('fact','preference') ORDER BY created_at DESC LIMIT %s", (self.web[...],
