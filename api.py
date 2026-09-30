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
- NEW: Injects live market data for BTC/ETH/SOL/XAU
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
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import uvicorn

from ai_engine import AIEngine
from database import (
    get_db_cursor,
    is_database_configured,
    check_database_health,
)

logger = logging.getLogger("king_zarry_api")

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
    os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
).strip().rstrip("/")

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

if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
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
                cur.execute("SELECT content, memory_type, created_at FROM web_ai_memories WHERE user_id = %s AND memory_type IN ('fact','preference') ORDER BY created_at DESC LIMIT %s", (self.web_user_id, limit))
                rows = cur.fetchall()
            facts = []
            for row in rows:
                facts.append({"fact": str(_row_value(row, "content", 0)), "category": str(_row_value(row, "memory_type", 1))})
            return facts
        except Exception:
            return []

    def count(self, user_id: str = None) -> int:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT COUNT(*) AS cnt FROM web_messages m JOIN web_conversations c ON m.conversation_id = c.id WHERE c.user_id = %s", (self.web_user_id,))
                row = cur.fetchone()
            return int(_row_value(row, "cnt", 0) or 0)
        except Exception:
            return 0

    def add_message(self, user_id: str, role: str, content: str):
        """FIXED: Now writes to web_messages (same table get_history reads from)."""
        try:
            with get_db_cursor(commit=True) as cur:
                conv_id = self.conversation_id
                if conv_id:
                    cur.execute(
                        "SELECT id FROM web_conversations WHERE id = %s AND user_id = %s LIMIT 1",
                        (conv_id, self.web_user_id),
                    )
                    if not cur.fetchone():
                        conv_id = None
                if not conv_id:
                    cur.execute(
                        "SELECT id FROM web_conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                        (self.web_user_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        conv_id = str(_row_value(row, "id", 0))
                    else:
                        cur.execute(
                            "INSERT INTO web_conversations (user_id, title) VALUES (%s, 'New chat') RETURNING id",
                            (self.web_user_id,),
                        )
                        conv_id = str(_row_value(cur.fetchone(), "id", 0))
                self.conversation_id = conv_id
                cur.execute(
                    "INSERT INTO web_messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                    (conv_id, str(role)[:50], str(content)[:8000]),
                )
                cur.execute(
                    "UPDATE web_conversations SET updated_at = NOW() WHERE id = %s",
                    (conv_id,),
                )
        except Exception as exc:
            logger.warning("WebMemoryAdapter.add_message failed: %s", type(exc).__name__)

    def get_memory_facts_text(self, user_id: str, limit: int = 30) -> str:
        facts = self.get_facts(user_id, limit=limit)
        if not facts:
            return ""
        return "\n".join(f"- {item['fact']}" for item in facts)

    def add_fact(self, user_id: str, fact: str, category: str = "general", source: str = "auto") -> bool:
        """Persist a durable web memory fact for the authenticated web user."""
        if not fact:
            return False
        fact = str(fact).strip()[:500]
        memory_type = "preference" if str(category).lower() == "preference" else "fact"
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "SELECT id FROM web_ai_memories WHERE user_id = %s AND content = %s AND memory_type = %s LIMIT 1",
                    (self.web_user_id, fact, memory_type),
                )
                if cur.fetchone():
                    return False
                cur.execute(
                    "INSERT INTO web_ai_memories (user_id, role, content, memory_type) VALUES (%s, 'user', %s, %s)",
                    (self.web_user_id, fact, memory_type),
                )
            return True
        except Exception as exc:
            logger.warning("WebMemoryAdapter.add_fact failed: %s", type(exc).__name__)
            return False

    def update_user_profile(self, user_id: str, preferred_name: Optional[str] = None, **kwargs) -> bool:
        """Persist lightweight profile fields used by automatic memory learning."""
        if not preferred_name:
            return False
        name = str(preferred_name).strip()[:100]
        if not name:
            return False
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "UPDATE web_users SET display_name = %s WHERE id = %s",
                    (name, self.web_user_id),
                )
            return True
        except Exception as exc:
            logger.warning("WebMemoryAdapter.update_user_profile failed: %s", type(exc).__name__)
            return False

    def get_trading_preferences(self, user_id: str) -> Dict[str, Any]:
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT trading_preferences FROM web_user_settings WHERE user_id = %s", (self.web_user_id,))
                row = cur.fetchone()
            value = _row_value(row, "trading_preferences", 0) if row else {}
            if isinstance(value, dict):
                return value
            return json.loads(value) if value else {}
        except Exception:
            return {}

    def save_trading_preferences(self, user_id: str, preferred_assets: Optional[str] = None,
                                 preferred_timeframe: Optional[str] = None,
                                 risk_preference: Optional[str] = None, **kwargs) -> bool:
        try:
            current = self.get_trading_preferences(user_id)
            if preferred_assets is not None:
                current["preferred_assets"] = preferred_assets
            if preferred_timeframe is not None:
                current["preferred_timeframe"] = preferred_timeframe
            if risk_preference is not None:
                current["risk_preference"] = risk_preference
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO web_user_settings (user_id, trading_preferences) VALUES (%s, %s::jsonb) "
                    "ON CONFLICT (user_id) DO UPDATE SET trading_preferences = EXCLUDED.trading_preferences",
                    (self.web_user_id, json.dumps(current)),
                )
            return True
        except Exception as exc:
            logger.warning("WebMemoryAdapter.save_trading_preferences failed: %s", type(exc).__name__)
            return False

# ============================================================
# USER DATABASE
# ============================================================

def _find_user_by_email(email: str) -> Optional[Any]:
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT id, email, username, display_name, account_status, created_at, password_hash FROM web_users WHERE email = %s LIMIT 1", (email,))
        return cur.fetchone()

def _find_user_by_id(user_id: str) -> Optional[Any]:
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT id, email, username, display_name, account_status, created_at, password_hash FROM web_users WHERE id = %s LIMIT 1", (user_id,))
        return cur.fetchone()

def _create_default_user_rows(user_id: str) -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO web_user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
        cur.execute("INSERT INTO web_user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))

def _create_user(email: str, password: str, username: Optional[str], display_name: Optional[str]) -> Any:
    password_hash = _hash_password(password)
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO web_users (email, password_hash, username, display_name, account_status) VALUES (%s, %s, %s, %s, 'active') RETURNING id, email, username, display_name, account_status, created_at, password_hash", (email, password_hash, username, display_name))
        user_row = cur.fetchone()
    user_id = str(_row_value(user_row, "id", 0))
    _create_default_user_rows(user_id)
    return user_row

def _update_last_login(user_id: str) -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_users SET last_login_at = NOW() WHERE id = %s", (user_id,))

# ============================================================
# SESSION DATABASE
# ============================================================

def _create_session(user_id: str, request: Request) -> str:
    raw_token = _create_raw_session_token()
    token_hash = _hash_session_token(raw_token)
    expires_at = _session_expiry()
    client_ip = None
    if request.client:
        client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")[:2000]
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO web_sessions (user_id, token_hash, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)", (user_id, token_hash, expires_at, client_ip, user_agent))
    return raw_token

def _get_user_from_session_token(raw_token: Optional[str]) -> Optional[Any]:
    if not raw_token or len(raw_token) > 500:
        return None
    token_hash = _hash_session_token(raw_token)
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT u.id, u.email, u.username, u.display_name, u.account_status, u.created_at, u.password_hash, s.id AS session_id FROM web_sessions s JOIN web_users u ON s.user_id = u.id WHERE s.token_hash = %s AND s.revoked_at IS NULL AND s.expires_at > NOW() AND u.account_status = 'active' LIMIT 1", (token_hash,))
        row = cur.fetchone()
    if not row:
        return None
    session_id = _row_value(row, "session_id", 7)
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_sessions SET last_used_at = NOW() WHERE id = %s", (session_id,))
    except Exception:
        logger.warning("Could not update session last_used_at")
    return row

def _revoke_session(raw_token: Optional[str]) -> None:
    if not raw_token:
        return
    token_hash = _hash_session_token(raw_token)
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_sessions SET revoked_at = NOW() WHERE token_hash = %s AND revoked_at IS NULL", (token_hash,))

def _require_current_user(request: Request) -> Any:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        user_row = _get_user_from_session_token(raw_token)
    except Exception as exc:
        logger.error("Session lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Authentication service temporarily unavailable")
    if not user_row:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_row

# ============================================================
# CONVERSATIONS
# ============================================================

def _get_or_create_conversation(user_id: str, conversation_id: Optional[str] = None) -> str:
    """Return an existing conversation owned by the user, or create a new one."""
    if conversation_id:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT id FROM web_conversations WHERE id = %s AND user_id = %s LIMIT 1",
                (str(conversation_id), user_id),
            )
            row = cur.fetchone()
        if row:
            return str(_row_value(row, "id", 0))
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Prefer most recent; create if none
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            "SELECT id FROM web_conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
    if row:
        return str(_row_value(row, "id", 0))
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO web_conversations (user_id, title) VALUES (%s, %s) RETURNING id",
            (user_id, "New chat"),
        )
        row = cur.fetchone()
    return str(_row_value(row, "id", 0))


def _create_conversation(user_id: str, title: str = "New chat") -> dict:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO web_conversations (user_id, title) VALUES (%s, %s) RETURNING id, title, created_at, updated_at",
            (user_id, (title or "New chat")[:200]),
        )
        row = cur.fetchone()
    return {
        "id": str(_row_value(row, "id", 0)),
        "title": _row_value(row, "title", 1) or "New chat",
        "created_at": str(_row_value(row, "created_at", 2) or ""),
        "updated_at": str(_row_value(row, "updated_at", 3) or ""),
    }


def _list_conversations(user_id: str, limit: int = 50) -> list:
    limit = max(1, min(int(limit), 100))
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   (SELECT m.content FROM web_messages m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC LIMIT 1) AS last_message
            FROM web_conversations c
            WHERE c.user_id = %s
            ORDER BY c.updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall() or []
    out = []
    for row in rows:
        title = _row_value(row, "title", 1) or "Chat"
        last = _row_value(row, "last_message", 4)
        out.append({
            "id": str(_row_value(row, "id", 0)),
            "title": str(title)[:120],
            "preview": (str(last)[:120] if last else ""),
            "created_at": str(_row_value(row, "created_at", 2) or ""),
            "updated_at": str(_row_value(row, "updated_at", 3) or ""),
        })
    return out


def _get_conversation_messages(user_id: str, conversation_id: str, limit: int = 100) -> list:
    limit = max(1, min(int(limit), 200))
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            "SELECT id FROM web_conversations WHERE id = %s AND user_id = %s LIMIT 1",
            (str(conversation_id), user_id),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")
        cur.execute(
            """
            SELECT role, content, created_at
            FROM web_messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (str(conversation_id), limit),
        )
        rows = cur.fetchall() or []
    result = []
    for i, row in enumerate(rows):
        result.append({
            "id": f"msg-{i}-{_row_value(row, 'created_at', 2)}",
            "role": str(_row_value(row, "role", 0) or "assistant"),
            "content": str(_row_value(row, "content", 1) or ""),
            "created_at": str(_row_value(row, "created_at", 2) or ""),
        })
    return result


def _maybe_set_conversation_title(conversation_id: str, message: str) -> None:
    """Set title from first user message if still default."""
    title = (message or "").strip().replace("\n", " ")[:60] or "New chat"
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE web_conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s
                  AND (title IS NULL OR title IN ('Web Chat', 'New chat', ''))
                """,
                (title, str(conversation_id)),
            )
    except Exception:
        pass

def _save_web_message(conversation_id: str, role: str, content: str) -> str:
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO web_messages (conversation_id, role, content) VALUES (%s, %s, %s) RETURNING id", (conversation_id, str(role)[:50], str(content)[:8000]))
        row = cur.fetchone()
        cur.execute("UPDATE web_conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
    return str(_row_value(row, "id", 0))

# ============================================================
# MARKET DATA INJECTION (NEW)
# ============================================================

def _enrich_with_market_data(message: str) -> str:
    """
    Detect if the user is asking about a supported asset and inject
    live price data into the prompt before sending it to the AI.
    This prevents the AI from saying "I don't have live market data".
    """
    msg_lower = message.lower()
    asset = None
    if "xau" in msg_lower or "gold" in msg_lower:
        asset = "XAU/USD"
    elif "btc" in msg_lower or "bitcoin" in msg_lower:
        asset = "BTC/USD"
    elif "eth" in msg_lower or "ethereum" in msg_lower:
        asset = "ETH/USD"
    elif "sol" in msg_lower or "solana" in msg_lower:
        asset = "SOL/USD"

    if not asset:
        return message

    try:
        import market
        price = None
        if hasattr(market, "get_price"):
            price = market.get_price(asset)
        elif hasattr(market, "analyze_market"):
            analysis = market.analyze_market(asset)
            if analysis and isinstance(analysis, dict):
                price = analysis.get("price") or analysis.get("current_price")

        if price:
            return (
                f"{message}\n\n"
                f"[LIVE MARKET DATA - INJECTED BY APP]: "
                f"{asset} current price is {price}. "
                f"Use this data for your analysis. "
                f"Do NOT say you don't have live data."
            )
    except Exception as e:
        logger.warning(f"Could not fetch market data for {asset}: {e}")

    return message

# ============================================================
# AI
# ============================================================

async def _run_web_ai(
    user_id: str,
    message: str,
    image_data: Optional[Tuple[str, bytes]] = None,
    conversation_id: Optional[str] = None,
) -> str:
    """Run the AI engine with optional image data."""
    web_memory = WebMemoryAdapter(user_id, conversation_id=conversation_id)
    request_engine = AIEngine(memory=web_memory)
    response_text = await asyncio.to_thread(
        request_engine.ask,
        user_id,
        message,
        image_data,
    )
    if not response_text:
        return "AI temporarily unavailable. Please try again."
    return str(response_text)[:8000]

# ============================================================
# ROOT
# ============================================================

@app.get("/")
def read_root():
    return {"status": "KingZarry AI API is active", "mode": "web", "database": "neon", "authentication": "session_cookie"}

@app.get("/health")
def health_check():
    try:
        database_status = check_database_health()
        return {"status": "ok", "web_db_configured": is_database_configured(), "database": database_status}
    except Exception as exc:
        logger.error("Health check failed: %s", type(exc).__name__)
        return {"status": "ok", "web_db_configured": False, "database": {"status": "unavailable"}}


# ============================================================
# EMAIL VERIFICATION + PASSWORD RESET (6-digit codes)
# ============================================================
# Requires RESEND_API_KEY (https://resend.com) + EMAIL_FROM
# Without a key: codes are logged server-side only (dev fallback).

EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "15"))
RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
EMAIL_FROM = (os.getenv("EMAIL_FROM") or os.getenv("FROM_EMAIL") or "King Zarry AI <onboarding@resend.dev>").strip()
REQUIRE_EMAIL_VERIFY = (os.getenv("REQUIRE_EMAIL_VERIFY", "true") or "true").strip().lower() in (
    "1", "true", "yes", "on",
)


def _ensure_auth_extra_tables() -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS web_email_codes (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                purpose TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_web_email_codes_lookup
            ON web_email_codes (email, purpose, created_at DESC)
            """
        )
        # Optional column on web_users
        try:
            cur.execute(
                """
                ALTER TABLE web_users
                ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE
                """
            )
        except Exception:
            pass


def _hash_code(code: str) -> str:
    return hashlib.sha256(f"kz-code:{code}".encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _send_email_resend(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    """Send an email through Resend without exposing secrets to the client."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email not sent to %s", to_email)
        return False
    if not EMAIL_FROM:
        logger.warning("EMAIL_FROM not set — email not sent to %s", to_email)
        return False

    try:
        import urllib.error
        import urllib.request

        payload = json.dumps(
            {
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "King-Zarry-AI/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if 200 <= resp.status < 300:
                logger.info("Resend email accepted: to=%s status=%s", to_email, resp.status)
                return True
            logger.error("Resend rejected email: to=%s status=%s response=%s", to_email, resp.status, _redact(body)[:1000])
            return False
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        logger.error("Resend HTTP error: to=%s status=%s response=%s", to_email, exc.code, _redact(body)[:1000])
        return False
    except Exception as exc:
        logger.error("Resend email failed: to=%s error=%s detail=%s", to_email, type(exc).__name__, _redact(str(exc))[:500])
        return False


def _issue_email_code(email: str, purpose: str) -> str:
    """Create a 6-digit code, store hash, try to email it. Returns plaintext code."""
    _ensure_auth_extra_tables()
    email = _normalize_email(email)
    code = _generate_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=EMAIL_CODE_TTL_MINUTES)
    with get_db_cursor(commit=True) as cur:
        # Invalidate previous unused codes for same purpose
        cur.execute(
            """
            UPDATE web_email_codes
            SET used_at = NOW()
            WHERE email = %s AND purpose = %s AND used_at IS NULL
            """,
            (email, purpose),
        )
        cur.execute(
            """
            INSERT INTO web_email_codes (email, purpose, code_hash, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (email, purpose, _hash_code(code), expires),
        )

    subject = (
        "King Zarry AI — verify your email"
        if purpose == "verify"
        else "King Zarry AI — password reset code"
    )
    text = (
        f"Your code is: {code}\n\n"
        f"It expires in {EMAIL_CODE_TTL_MINUTES} minutes.\n"
        "If you did not request this, ignore this email."
    )
    html = (
        f"<p>Your King Zarry AI code:</p>"
        f"<p style='font-size:28px;letter-spacing:6px'><b>{code}</b></p>"
        f"<p>Expires in {EMAIL_CODE_TTL_MINUTES} minutes.</p>"
    )
    sent = _send_email_resend(email, subject, text, html)
    if not sent:
        # Dev visibility only — never expose in production API responses by default
        logger.info("EMAIL_CODE purpose=%s email=%s code=%s (not emailed)", purpose, email, code)
    return code


def _consume_email_code(email: str, purpose: str, code: str) -> bool:
    _ensure_auth_extra_tables()
    email = _normalize_email(email)
    code = str(code or "").strip()
    if not code or len(code) < 4:
        return False
    code_hash = _hash_code(code)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            SELECT id FROM web_email_codes
            WHERE email = %s
              AND purpose = %s
              AND code_hash = %s
              AND used_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, purpose, code_hash),
        )
        row = cur.fetchone()
        if not row:
            return False
        cid = _row_value(row, "id", 0)
        cur.execute(
            "UPDATE web_email_codes SET used_at = NOW() WHERE id = %s",
            (cid,),
        )
    return True


def _is_email_verified(user_row: Any) -> bool:
    """Best-effort: email_verified column or assume true for legacy rows if feature off."""
    if not REQUIRE_EMAIL_VERIFY:
        return True
    try:
        # index may not include email_verified; query by id
        user_id = str(_row_value(user_row, "id", 0))
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT email_verified FROM web_users WHERE id = %s LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return False
            val = _row_value(row, "email_verified", 0)
            return bool(val)
    except Exception:
        return False


def _mark_email_verified(email: str) -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE web_users
            SET email_verified = TRUE
            WHERE email = %s
            """,
            (_normalize_email(email),),
        )


def _set_password_hash(email: str, password: str) -> bool:
    ph = _hash_password(password)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE web_users SET password_hash = %s WHERE email = %s RETURNING id",
            (ph, _normalize_email(email)),
        )
        return cur.fetchone() is not None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)


@app.post("/api/auth/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    email = _normalize_email(payload.email)
    username = _normalize_username(payload.username)
    display_name = _safe_display_name(payload.display_name, email.split("@")[0])
    try:
        await asyncio.to_thread(_ensure_auth_extra_tables)
        existing_email = await asyncio.to_thread(_find_user_by_email, email)
        if existing_email:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        if username:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT id FROM web_users WHERE username = %s LIMIT 1", (username,))
                existing_username = cur.fetchone()
            if existing_username:
                raise HTTPException(status_code=409, detail="This username is already taken")
        user_row = await asyncio.to_thread(_create_user, email, payload.password, username, display_name)
        user_id = str(_row_value(user_row, "id", 0))
        # New signups start unverified when feature is on
        if REQUIRE_EMAIL_VERIFY:
            try:
                with get_db_cursor(commit=True) as cur:
                    cur.execute(
                        "UPDATE web_users SET email_verified = FALSE WHERE id = %s",
                        (user_id,),
                    )
            except Exception:
                pass

        # Email verification gate
        if REQUIRE_EMAIL_VERIFY:
            code = await asyncio.to_thread(_issue_email_code, email, "verify")
            result = {
                "status": "success",
                "message": "Account created. Enter the 6-digit code we sent to your email.",
                "requires_verification": True,
                "email": email,
            }
            # Dev only: surface code when Resend is not configured
            if not RESEND_API_KEY:
                result["dev_code"] = code
                result["message"] += " (RESEND_API_KEY missing — code also in Railway logs / dev_code)"
            return result

        raw_token = await asyncio.to_thread(_create_session, user_id, request)
        _set_session_cookie(response, raw_token)
        await asyncio.to_thread(_mark_email_verified, email)
        return {
            "status": "success",
            "message": "Account created successfully",
            "user": _user_public_data(user_row),
            "requires_verification": False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Registration failed: %s: %s", type(exc).__name__, _redact(str(exc)))
        raise HTTPException(status_code=500, detail="Could not create account")

@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    email = _normalize_email(payload.email)
    try:
        user_row = await asyncio.to_thread(_find_user_by_email, email)
        if not user_row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        stored_password_hash = _row_value(user_row, "password_hash", 6)
        password_valid = await asyncio.to_thread(_verify_password, payload.password, stored_password_hash)
        if not password_valid:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        account_status = str(_row_value(user_row, "account_status", 4) or "active").lower()
        if account_status == "banned":
            raise HTTPException(status_code=403, detail="This account has been banned")
        if account_status == "suspended":
            raise HTTPException(status_code=403, detail="This account is suspended")
        if account_status != "active":
            raise HTTPException(status_code=403, detail="This account is not active")
        if REQUIRE_EMAIL_VERIFY and not await asyncio.to_thread(_is_email_verified, user_row):
            raise HTTPException(
                status_code=403,
                detail="Email not verified. Check your inbox for the code, or use resend.",
            )
        user_id = str(_row_value(user_row, "id", 0))
        await asyncio.to_thread(_update_last_login, user_id)
        raw_token = await asyncio.to_thread(_create_session, user_id, request)
        _set_session_cookie(response, raw_token)
        return {"status": "success", "message": "Login successful", "user": _user_public_data(user_row)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not log in")

@app.get("/api/auth/me")
async def current_user(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user = _user_public_data(user_row)
    # Do not let billing overwrite admin unlimited VIP
    if user.get("is_admin"):
        user["is_subscribed"] = True
        user["plan"] = user.get("plan") or "admin"
    else:
        try:
            from web_billing import get_web_subscription
            sub = get_web_subscription(str(user.get("id") or ""))
            user["is_subscribed"] = bool(sub.get("is_subscribed"))
            user["plan"] = sub.get("plan")
            user["subscription_expires_at"] = sub.get("expires_at")
        except Exception:
            user.setdefault("is_subscribed", False)
            user.setdefault("plan", None)
            user.setdefault("subscription_expires_at", None)
    return {"status": "success", "user": user}


@app.post("/api/auth/verify-email")
async def verify_email(payload: VerifyEmailRequest, request: Request, response: Response):
    email = _normalize_email(payload.email)
    ok = await asyncio.to_thread(_consume_email_code, email, "verify", payload.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    user_row = await asyncio.to_thread(_find_user_by_email, email)
    if not user_row:
        raise HTTPException(status_code=404, detail="Account not found")
    await asyncio.to_thread(_mark_email_verified, email)
    user_id = str(_row_value(user_row, "id", 0))
    raw_token = await asyncio.to_thread(_create_session, user_id, request)
    _set_session_cookie(response, raw_token)
    return {
        "status": "success",
        "message": "Email verified. You are logged in.",
        "user": _user_public_data(user_row),
    }


@app.post("/api/auth/resend-code")
async def resend_code(payload: ResendCodeRequest):
    email = _normalize_email(payload.email)
    user_row = await asyncio.to_thread(_find_user_by_email, email)
    # Always generic message to avoid email enumeration
    result = {
        "status": "success",
        "message": "If that email is registered and needs verification, a new code was sent.",
    }
    if user_row and REQUIRE_EMAIL_VERIFY and not await asyncio.to_thread(_is_email_verified, user_row):
        code = await asyncio.to_thread(_issue_email_code, email, "verify")
        if not RESEND_API_KEY:
            result["dev_code"] = code
    return result


@app.post("/api/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    email = _normalize_email(payload.email)
    result = {
        "status": "success",
        "message": "If an account exists for that email, a reset code was sent.",
    }
    user_row = await asyncio.to_thread(_find_user_by_email, email)
    if user_row:
        code = await asyncio.to_thread(_issue_email_code, email, "reset")
        if not RESEND_API_KEY:
            result["dev_code"] = code
    return result


@app.post("/api/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    email = _normalize_email(payload.email)
    ok = await asyncio.to_thread(_consume_email_code, email, "reset", payload.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    user_row = await asyncio.to_thread(_find_user_by_email, email)
    if not user_row:
        raise HTTPException(status_code=404, detail="Account not found")
    updated = await asyncio.to_thread(_set_password_hash, email, payload.new_password)
    if not updated:
        raise HTTPException(status_code=500, detail="Could not update password")
    # Revoke sessions so old devices must re-login
    user_id = str(_row_value(user_row, "id", 0))
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE web_sessions SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL",
                (user_id,),
            )
    except Exception:
        pass
    return {"status": "success", "message": "Password updated. You can log in now."}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        await asyncio.to_thread(_revoke_session, raw_token)
    except Exception as exc:
        logger.warning("Logout session revoke failed: %s", type(exc).__name__)
    _clear_session_cookie(response)
    return {"status": "success", "message": "Logged out successfully"}

@app.post("/api/chat")
async def chat_endpoint(request: Request, chat: ChatRequest):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = str(_row_value(user_row, "id", 0))
    message = str(chat.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # NEW: Decode image if provided
    image_data = None
    if chat.image_base64:
        try:
            img_bytes = base64.b64decode(chat.image_base64)
            image_data = (chat.image_mime or "image/jpeg", img_bytes)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # NEW: Inject live market data if the message mentions a supported asset
    enriched_message = _enrich_with_market_data(message)

    try:
        conv_id = (chat.conversation_id or "").strip() or None
        conversation_id = await asyncio.to_thread(
            _get_or_create_conversation, user_id, conv_id
        )
        await asyncio.to_thread(_maybe_set_conversation_title, conversation_id, message)
        # NOTE: Do NOT call _save_web_message here. The AIEngine's WebMemoryAdapter
        # now handles saving both user and assistant messages to web_messages.
        response_text = await _run_web_ai(user_id, enriched_message, image_data, conversation_id)
        return {"status": "success", "reply": response_text, "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Web chat failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="AI processing failed")



@app.get("/api/conversations")
async def list_conversations(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = str(_row_value(user_row, "id", 0))
    try:
        items = await asyncio.to_thread(_list_conversations, user_id)
        return {"status": "success", "conversations": items}
    except Exception as exc:
        logger.error("list conversations failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load conversations")


@app.post("/api/conversations")
async def create_conversation(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = str(_row_value(user_row, "id", 0))
    try:
        conv = await asyncio.to_thread(_create_conversation, user_id, "New chat")
        return {"status": "success", "conversation": conv}
    except Exception as exc:
        logger.error("create conversation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not create conversation")


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = str(_row_value(user_row, "id", 0))
    try:
        messages = await asyncio.to_thread(
            _get_conversation_messages, user_id, conversation_id
        )
        return {"status": "success", "conversation_id": conversation_id, "messages": messages}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get messages failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load messages")


# ============================================================
# WEB BILLING (Stripe) + ADMIN
# ============================================================

STRIPE_SECRET_KEY = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
STRIPE_WEBHOOK_SECRET = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
# Paystack (preferred for NG / web VIP when set)
PAYSTACK_SECRET_KEY = (os.getenv("PAYSTACK_SECRET_KEY") or "").strip()
PAYSTACK_PUBLIC_KEY = (os.getenv("PAYSTACK_PUBLIC_KEY") or "").strip()
# Amounts: if PAYSTACK_SECRET_KEY set, plan amounts are KOBO (NGN*100). Else Stripe cents (USD).
def _parse_admin_emails() -> set:
    """Build admin email set from ADMIN_EMAILS + ADMIN_EMAIL (strip spaces/quotes)."""
    raw = ",".join(
        [
            os.getenv("ADMIN_EMAILS") or "",
            os.getenv("ADMIN_EMAIL") or "",
        ]
    )
    out = set()
    for part in raw.split(","):
        e = part.strip().strip(chr(34)+chr(39)).lower()
        if e and "@" in e:
            out.add(e)
    return out


ADMIN_EMAILS = _parse_admin_emails()
# Optional second factor for /admin ONLY (NOT your website login password unless you choose that)
ADMIN_PASSWORD = (os.getenv("ADMIN_PASSWORD") or "").strip().strip(chr(34) + chr(39))
ADMIN_SESSION_COOKIE = "kz_admin_session"
ADMIN_SESSION_DAYS = 7

# Plan amounts: Paystack = KOBO (default NGN); Stripe = USD cents if no Paystack
def _plan_amount(env_paystack: str, env_stripe: str, default_kobo: int, default_cents: int) -> int:
    if (os.getenv("PAYSTACK_SECRET_KEY") or "").strip():
        return int(os.getenv(env_paystack) or os.getenv(env_stripe) or default_kobo)
    return int(os.getenv(env_stripe) or default_cents)

# Defaults: ₦15,000 / ₦40,000 / ₦150,000 (kobo) OR $9.99 / $24.99 / $79.99 (cents)
_AMOUNT_MONTHLY = _plan_amount("PAYSTACK_AMOUNT_MONTHLY", "STRIPE_AMOUNT_MONTHLY", 1500000, 999)
_AMOUNT_QUARTERLY = _plan_amount("PAYSTACK_AMOUNT_QUARTERLY", "STRIPE_AMOUNT_QUARTERLY", 4000000, 2499)
_AMOUNT_YEARLY = _plan_amount("PAYSTACK_AMOUNT_YEARLY", "STRIPE_AMOUNT_YEARLY", 15000000, 7999)
STRIPE_AMOUNT_MONTHLY = _AMOUNT_MONTHLY
STRIPE_AMOUNT_QUARTERLY = _AMOUNT_QUARTERLY
STRIPE_AMOUNT_YEARLY = _AMOUNT_YEARLY

WEB_PLAN_CATALOG = {
    "monthly": {"name": "Monthly VIP", "days": 30, "amount": _AMOUNT_MONTHLY},
    "quarterly": {"name": "90-Day VIP", "days": 90, "amount": _AMOUNT_QUARTERLY},
    "3month": {"name": "90-Day VIP", "days": 90, "amount": _AMOUNT_QUARTERLY},
    "yearly": {"name": "Yearly VIP", "days": 365, "amount": _AMOUNT_YEARLY},
}
BILLING_PROVIDER = "paystack" if PAYSTACK_SECRET_KEY else ("stripe" if STRIPE_SECRET_KEY else "none")
BILLING_CURRENCY = "NGN" if PAYSTACK_SECRET_KEY else "USD"


def _ensure_billing_tables() -> None:
    """Idempotent schema for web subscriptions / Stripe events."""
    if not is_database_configured():
        return
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_subscriptions (
                    user_id TEXT PRIMARY KEY,
                    plan TEXT,
                    is_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT,
                    expires_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_payments (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT,
                    email TEXT,
                    plan TEXT,
                    amount_cents INTEGER,
                    currency TEXT DEFAULT 'usd',
                    stripe_session_id TEXT,
                    stripe_payment_intent TEXT,
                    status TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

            # Migrate older web_subscriptions missing is_subscribed
            try:
                cur.execute(
                    """
                    ALTER TABLE web_subscriptions
                    ADD COLUMN IF NOT EXISTS is_subscribed BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE web_subscriptions
                    ADD COLUMN IF NOT EXISTS plan TEXT
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE web_subscriptions
                    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE web_subscriptions
                    ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE web_subscriptions
                    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT
                    """
                )
            except Exception as mig_exc:
                logger.warning("web_subscriptions migrate: %s", type(mig_exc).__name__)
    except Exception as exc:
        logger.warning("ensure billing tables failed: %s", type(exc).__name__)


def _get_web_subscription(user_id: str) -> Dict[str, Any]:
    out = {"is_subscribed": False, "plan": None, "expires_at": None}
    if not user_id or not is_database_configured():
        return out
    try:
        _ensure_billing_tables()
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT plan, is_subscribed, expires_at
                FROM web_subscriptions
                WHERE user_id = %s
                LIMIT 1
                """,
                (str(user_id),),
            )
            row = cur.fetchone()
        if not row:
            return out
        plan = _row_value(row, "plan", 0)
        is_sub = _row_value(row, "is_subscribed", 1)
        exp = _row_value(row, "expires_at", 2)
        active = bool(is_sub)
        if exp is not None:
            try:
                if hasattr(exp, "tzinfo") and exp.tzinfo is None:
                    exp_aware = exp.replace(tzinfo=timezone.utc)
                else:
                    exp_aware = exp
                if exp_aware < datetime.now(timezone.utc):
                    active = False
            except Exception:
                pass
        out["is_subscribed"] = active
        out["plan"] = plan
        out["expires_at"] = str(exp) if exp is not None else None
        return out
    except Exception as exc:
        logger.warning("get web subscription failed: %s", type(exc).__name__)
        return out


def _activate_web_subscription(
    user_id: str,
    plan: str,
    days: int,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> None:
    _ensure_billing_tables()
    expires = datetime.now(timezone.utc) + timedelta(days=max(1, days))
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_subscriptions (
                user_id, plan, is_subscribed, stripe_customer_id,
                stripe_subscription_id, expires_at, updated_at
            ) VALUES (%s, %s, TRUE, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                is_subscribed = TRUE,
                stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, web_subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, web_subscriptions.stripe_subscription_id),
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            """,
            (
                str(user_id),
                plan,
                stripe_customer_id,
                stripe_subscription_id,
                expires,
            ),
        )


def _record_web_payment(
    user_id: str,
    email: str,
    plan: str,
    amount_cents: int,
    session_id: str,
    payment_intent: Optional[str],
    status: str,
    currency: Optional[str] = None,
) -> None:
    _ensure_billing_tables()
    cur_code = (currency or BILLING_CURRENCY or "usd").lower()
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_payments (
                user_id, email, plan, amount_cents, currency,
                stripe_session_id, stripe_payment_intent, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(user_id),
                email,
                plan,
                amount_cents,
                cur_code,
                session_id,
                payment_intent,
                status,
            ),
        )


def _is_admin_email(email: Optional[str]) -> bool:
    if not email or not ADMIN_EMAILS:
        return False
    return str(email).strip().lower() in ADMIN_EMAILS


def _admin_password_configured() -> bool:
    return bool(ADMIN_PASSWORD)


def _admin_session_token() -> str:
    """Deterministic token derived from ADMIN_PASSWORD (not the password itself)."""
    if not ADMIN_PASSWORD:
        return ""
    return hashlib.sha256(f"kz-admin:{ADMIN_PASSWORD}".encode("utf-8")).hexdigest()


def _has_valid_admin_session(request: Request) -> bool:
    if not ADMIN_PASSWORD:
        return True  # no password gate
    expected = _admin_session_token()
    got = (request.cookies.get(ADMIN_SESSION_COOKIE) or "").strip()
    if not got or not expected:
        return False
    return hmac.compare_digest(got, expected)


def _require_admin(request: Request):
    """Logged-in user email must be in ADMIN_EMAILS; optional ADMIN_PASSWORD session."""
    user_row = _require_current_user(request)
    email = str(_row_value(user_row, "email", "") or "").strip().lower()
    if not _is_admin_email(email):
        raise HTTPException(
            status_code=403,
            detail="Admin access denied. Set ADMIN_EMAIL or ADMIN_EMAILS on Railway to your login email.",
        )
    if ADMIN_PASSWORD and not _has_valid_admin_session(request):
        raise HTTPException(
            status_code=403,
            detail="Admin password required",
        )
    return user_row, email


class CheckoutRequest(BaseModel):
    plan: str = Field(..., min_length=2, max_length=32)


@app.post("/api/billing/create-checkout-session")
async def create_checkout_session(payload: CheckoutRequest, request: Request):
    """Start web VIP payment. Prefers Paystack when PAYSTACK_SECRET_KEY is set; else Stripe."""
    if not PAYSTACK_SECRET_KEY and not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Set PAYSTACK_SECRET_KEY (or STRIPE_SECRET_KEY) on Railway.",
        )
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = str(_row_value(user_row, "id", 0))
    email = str(_row_value(user_row, "email", 1) or "")
    plan_key = (payload.plan or "").strip().lower()
    if plan_key not in WEB_PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid plan")
    plan = WEB_PLAN_CATALOG[plan_key]
    success_url = f"{FRONTEND_URL.rstrip('/')}/settings?checkout=success&plan={plan_key}"
    cancel_url = f"{FRONTEND_URL.rstrip('/')}/pricing?checkout=cancel"

    def _create_paystack():
        import json as _json
        amount = int(plan["amount"])
        body = {
            "email": email or f"user{user_id}@kingzarryai.online",
            "amount": amount,
            "currency": "NGN",
            "callback_url": success_url,
            "metadata": {
                "user_id": str(user_id),
                "plan": plan_key,
                "days": int(plan["days"]),
                "cancel_url": cancel_url,
            },
        }
        r = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            data=_json.dumps(body),
            timeout=30,
        )
        data = r.json() if r.content else {}
        if r.status_code >= 400 or not data.get("status"):
            msg = (data.get("message") if isinstance(data, dict) else None) or r.text[:200]
            raise RuntimeError(f"Paystack initialize failed: {msg}")
        d = data.get("data") or {}
        return {
            "status": "success",
            "provider": "paystack",
            "url": d.get("authorization_url"),
            "session_id": d.get("reference"),
            "access_code": d.get("access_code"),
            "public_key": PAYSTACK_PUBLIC_KEY or None,
        }

    def _create_stripe():
        try:
            import stripe
        except ImportError as e:
            raise RuntimeError("stripe package not installed") from e
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="payment",
            customer_email=email or None,
            line_items=[
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(plan["amount"]),
                        "product_data": {
                            "name": plan["name"],
                            "description": f"King Zarry AI VIP — {plan['days']} days",
                        },
                    },
                }
            ],
            success_url=success_url + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            client_reference_id=str(user_id),
            metadata={
                "user_id": str(user_id),
                "plan": plan_key,
                "days": str(plan["days"]),
            },
        )
        return {
            "status": "success",
            "provider": "stripe",
            "url": session.url,
            "session_id": session.id,
        }

    def _create():
        if PAYSTACK_SECRET_KEY:
            return _create_paystack()
        return _create_stripe()

    try:
        return await asyncio.to_thread(_create)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("checkout create failed: %s: %s", type(exc).__name__, _redact(str(exc)))
        raise HTTPException(status_code=500, detail="Could not start checkout")


@app.get("/api/billing/config")
async def billing_config():
    """Public pricing metadata for the frontend."""
    return {
        "status": "success",
        "provider": BILLING_PROVIDER,
        "currency": BILLING_CURRENCY,
        "configured": BILLING_PROVIDER != "none",
        "plans": {
            k: {
                "name": v["name"],
                "days": v["days"],
                "amount": v["amount"],
                "amount_major": round(v["amount"] / 100, 2),
            }
            for k, v in WEB_PLAN_CATALOG.items()
            if k != "3month"
        },
    }


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    def _handle():
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            # Dev fallback — prefer setting STRIPE_WEBHOOK_SECRET in production
            event = stripe.Event.construct_from(
                __import__("json").loads(payload.decode("utf-8")),
                STRIPE_SECRET_KEY,
            )
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            meta = session.get("metadata") or {}
            user_id = meta.get("user_id") or session.get("client_reference_id")
            plan = (meta.get("plan") or "monthly").lower()
            days = int(meta.get("days") or WEB_PLAN_CATALOG.get(plan, {}).get("days", 30))
            email = session.get("customer_details", {}).get("email") or session.get("customer_email") or ""
            amount = int(session.get("amount_total") or 0)
            if user_id:
                _activate_web_subscription(
                    str(user_id),
                    plan,
                    days,
                    stripe_customer_id=session.get("customer"),
                    stripe_subscription_id=session.get("subscription"),
                )
                _record_web_payment(
                    str(user_id),
                    email,
                    plan,
                    amount,
                    session.get("id") or "",
                    session.get("payment_intent"),
                    "paid",
                )
        return {"received": True}

    try:
        return await asyncio.to_thread(_handle)
    except Exception as exc:
        logger.error("Stripe webhook error: %s: %s", type(exc).__name__, _redact(str(exc)))
        raise HTTPException(status_code=400, detail="Webhook error")



@app.post("/api/billing/paystack-webhook")
async def paystack_webhook(request: Request):
    """Paystack event webhook — enable charge.success in dashboard."""
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Paystack not configured")
    payload = await request.body()
    # Optional signature: x-paystack-signature = HMAC SHA512 of body with secret
    sig = (request.headers.get("x-paystack-signature") or "").strip()
    if sig:
        import hashlib as _hashlib
        import hmac as _hmac
        expected = _hmac.new(
            PAYSTACK_SECRET_KEY.encode("utf-8"),
            payload,
            _hashlib.sha512,
        ).hexdigest()
        if not _hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    def _handle():
        import json as _json
        event = _json.loads(payload.decode("utf-8") or "{}")
        etype = event.get("event") or event.get("type") or ""
        data = event.get("data") or {}
        if etype in ("charge.success", "paymentrequest.success"):
            meta = data.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            user_id = meta.get("user_id") or meta.get("userId")
            plan = (meta.get("plan") or "monthly").lower()
            days = int(meta.get("days") or WEB_PLAN_CATALOG.get(plan, {}).get("days", 30))
            email = data.get("customer", {}).get("email") if isinstance(data.get("customer"), dict) else ""
            if not email:
                email = data.get("email") or ""
            amount = int(data.get("amount") or 0)
            reference = data.get("reference") or data.get("id") or ""
            status = (data.get("status") or "").lower()
            if status and status not in ("success", "successful", "paid"):
                return {"received": True, "ignored": status}
            if user_id:
                _activate_web_subscription(
                    str(user_id),
                    plan,
                    days,
                    stripe_customer_id=None,
                    stripe_subscription_id=str(reference) if reference else None,
                )
                _record_web_payment(
                    str(user_id),
                    str(email),
                    plan,
                    amount,
                    str(reference),
                    str(data.get("id") or ""),
                    "paid",
                    currency="ngn",
                )
                logger.info("Paystack VIP activated user=%s plan=%s ref=%s", user_id, plan, reference)
        return {"received": True}

    try:
        return await asyncio.to_thread(_handle)
    except Exception as exc:
        logger.error("Paystack webhook error: %s: %s", type(exc).__name__, _redact(str(exc)))
        raise HTTPException(status_code=400, detail="Webhook error")


class AdminUnlockRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@app.get("/api/admin/me")
async def admin_me(request: Request):
    """Tell the frontend if the logged-in user is an admin (server-side env check)."""
    user_row = await asyncio.to_thread(_require_current_user, request)
    email = str(_row_value(user_row, "email", 1) or "").strip().lower()
    is_admin = _is_admin_email(email)
    password_ok = _has_valid_admin_session(request) if ADMIN_PASSWORD else True
    return {
        "status": "success",
        "is_admin": is_admin,
        "email": email,
        "requires_password": bool(ADMIN_PASSWORD) and is_admin and not password_ok,
        "admin_emails_configured": bool(ADMIN_EMAILS),
        "admin_email_count": len(ADMIN_EMAILS),
        "hint": (
            None
            if is_admin
            else (
                "No ADMIN_EMAIL/ADMIN_EMAILS on Railway"
                if not ADMIN_EMAILS
                else "Logged-in email does not match ADMIN_EMAIL on Railway (must be exact)"
            )
        ),
    }


@app.post("/api/admin/unlock")
async def admin_unlock(request: Request, body: AdminUnlockRequest, response: Response):
    """Verify ADMIN_PASSWORD from Railway env and set admin session cookie."""
    user_row = await asyncio.to_thread(_require_current_user, request)
    email = str(_row_value(user_row, "email", 1) or "").strip().lower()
    if not _is_admin_email(email):
        raise HTTPException(status_code=403, detail="Admin access required")
    if not ADMIN_PASSWORD:
        return {"status": "success", "message": "No admin password configured"}
    if not hmac.compare_digest(body.password.strip(), ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    token = _admin_session_token()
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ADMIN_SESSION_DAYS * 24 * 3600,
        path="/",
    )
    return {"status": "success", "message": "Admin unlocked"}



class AdminUserStatusRequest(BaseModel):
    status: str = Field(min_length=3, max_length=20)  # active | suspended | banned


def _set_user_account_status(user_id: str, status: str) -> Optional[Dict[str, Any]]:
    status = status.strip().lower()
    if status not in ("active", "suspended", "banned"):
        raise ValueError("invalid status")
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE web_users
            SET account_status = %s
            WHERE id = %s
            RETURNING id, email, username, account_status, created_at, last_login_at
            """,
            (status, str(user_id)),
        )
        row = cur.fetchone()
        if not row:
            return None
        # Kill sessions when suspending/banning
        if status in ("suspended", "banned"):
            try:
                cur.execute(
                    """
                    UPDATE web_sessions
                    SET revoked_at = NOW()
                    WHERE user_id = %s AND revoked_at IS NULL
                    """,
                    (str(user_id),),
                )
            except Exception:
                pass
        return {
            "id": str(_row_value(row, "id", 0) or ""),
            "email": _row_value(row, "email", 1),
            "username": _row_value(row, "username", 2),
            "account_status": _row_value(row, "account_status", 3),
            "created_at": str(_row_value(row, "created_at", 4) or ""),
            "last_login_at": str(_row_value(row, "last_login_at", 5) or ""),
        }


@app.post("/api/admin/users/{user_id}/status")
async def admin_set_user_status(
    request: Request,
    user_id: str,
    body: AdminUserStatusRequest,
):
    """Suspend, ban, or reactivate a web user. Revokes sessions on suspend/ban."""
    admin_row, admin_email = await asyncio.to_thread(_require_admin, request)
    admin_id = str(_row_value(admin_row, "id", 0) or "")
    target = str(user_id or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="user_id required")
    if target == admin_id:
        raise HTTPException(status_code=400, detail="You cannot change your own account status")

    status = (body.status or "").strip().lower()
    if status not in ("active", "suspended", "banned"):
        raise HTTPException(
            status_code=400,
            detail="status must be active, suspended, or banned",
        )

    try:
        updated = await asyncio.to_thread(_set_user_account_status, target, status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    except Exception as exc:
        logger.error("admin set status failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not update user status")

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    logger.info(
        "admin %s set user %s status=%s",
        admin_email,
        updated.get("email"),
        status,
    )
    return {"status": "success", "user": updated}


@app.get("/api/admin/users")
async def admin_list_users(request: Request, limit: int = 50):
    """List recent web users for moderation."""
    await asyncio.to_thread(_require_admin, request)
    limit = max(1, min(int(limit or 50), 100))

    def _load():
        users = []
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT id, email, username, account_status, created_at, last_login_at
                FROM web_users
                ORDER BY created_at DESC NULLS LAST
                LIMIT %s
                """,
                (limit,),
            )
            for r in cur.fetchall() or []:
                users.append(
                    {
                        "id": str(_row_value(r, "id", 0) or ""),
                        "email": _row_value(r, "email", 1),
                        "username": _row_value(r, "username", 2),
                        "account_status": _row_value(r, "account_status", 3),
                        "created_at": str(_row_value(r, "created_at", 4) or ""),
                        "last_login_at": str(_row_value(r, "last_login_at", 5) or ""),
                    }
                )
        return users

    try:
        users = await asyncio.to_thread(_load)
        return {"status": "success", "users": users}
    except Exception as exc:
        logger.error("admin list users: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not list users")


@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    user_row, email = await asyncio.to_thread(_require_admin, request)
    _ = email

    def _safe_count(cur, sql: str, params=()):
        try:
            cur.execute(sql, params)
            row = cur.fetchone()
            return int(_row_value(row, "c", 0) or 0)
        except Exception as e:
            logger.warning("admin count failed: %s", type(e).__name__)
            return 0

    def _load():
        try:
            _ensure_billing_tables()
        except Exception:
            pass

        out = {
            "status": "success",
            "admin_email": str(email),
            "users_total": 0,
            "users_active_7d": 0,
            "users_active_30d": 0,
            "users_new_7d": 0,
            "sessions_active": 0,
            "conversations_total": 0,
            "messages_total": 0,
            "messages_24h": 0,
            "active_subscribers": 0,
            "payments_count": 0,
            "revenue_cents": 0,
            "revenue_usd": 0.0,
            "recent_users": [],
            "recent_payments": [],
        }

        try:
            with get_db_cursor(commit=False) as cur:
                out["users_total"] = _safe_count(
                    cur, "SELECT COUNT(*) AS c FROM web_users"
                )
                out["users_active_7d"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_users
                    WHERE last_login_at IS NOT NULL
                      AND last_login_at > NOW() - INTERVAL '7 days'
                    """,
                )
                out["users_active_30d"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_users
                    WHERE last_login_at IS NOT NULL
                      AND last_login_at > NOW() - INTERVAL '30 days'
                    """,
                )
                out["users_new_7d"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_users
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    """,
                )
                out["sessions_active"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_sessions
                    WHERE revoked_at IS NULL AND expires_at > NOW()
                    """,
                )
                out["conversations_total"] = _safe_count(
                    cur, "SELECT COUNT(*) AS c FROM web_conversations"
                )
                out["messages_total"] = _safe_count(
                    cur, "SELECT COUNT(*) AS c FROM web_messages"
                )
                out["messages_24h"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_messages
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    """,
                )

                # Billing
                out["active_subscribers"] = _safe_count(
                    cur,
                    """
                    SELECT COUNT(*) AS c FROM web_subscriptions
                    WHERE is_subscribed IS TRUE
                      AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                )
                try:
                    cur.execute(
                        """
                        SELECT COUNT(*) AS c,
                               COALESCE(SUM(amount_cents), 0) AS s
                        FROM web_payments WHERE status = 'paid'
                        """
                    )
                    pay = cur.fetchone()
                    out["payments_count"] = int(_row_value(pay, "c", 0) or 0)
                    out["revenue_cents"] = int(_row_value(pay, "s", 1) or 0)
                    out["revenue_usd"] = round(out["revenue_cents"] / 100.0, 2)
                except Exception:
                    pass

                try:
                    cur.execute(
                        """
                        SELECT id, email, username, account_status, created_at, last_login_at
                        FROM web_users
                        ORDER BY created_at DESC NULLS LAST
                        LIMIT 30
                        """
                    )
                    for r in cur.fetchall() or []:
                        out["recent_users"].append(
                            {
                                "id": str(_row_value(r, "id", 0) or ""),
                                "email": _row_value(r, "email", 1),
                                "username": _row_value(r, "username", 2),
                                "account_status": _row_value(r, "account_status", 3),
                                "created_at": str(_row_value(r, "created_at", 4) or ""),
                                "last_login_at": str(_row_value(r, "last_login_at", 5) or ""),
                            }
                        )
                except Exception as e:
                    logger.warning("recent users: %s", type(e).__name__)

                try:
                    cur.execute(
                        """
                        SELECT email, plan, amount_cents, status, created_at
                        FROM web_payments
                        ORDER BY created_at DESC NULLS LAST
                        LIMIT 50
                        """
                    )
                    for r in cur.fetchall() or []:
                        out["recent_payments"].append(
                            {
                                "email": _row_value(r, "email", 0),
                                "plan": _row_value(r, "plan", 1),
                                "amount_cents": _row_value(r, "amount_cents", 2),
                                "status": _row_value(r, "status", 3),
                                "created_at": str(_row_value(r, "created_at", 4) or ""),
                            }
                        )
                except Exception:
                    pass
        except Exception as exc:
            logger.error("admin stats db: %s", type(exc).__name__)

        return out

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("admin stats failed: %s", type(exc).__name__)
        return {
            "status": "success",
            "users_total": 0,
            "active_subscribers": 0,
            "payments_count": 0,
            "revenue_cents": 0,
            "revenue_usd": 0.0,
            "recent_users": [],
            "recent_payments": [],
            "note": "Partial data unavailable",
        }


# Prefer modular billing if present (remote-friendly install)
try:
    from web_billing import install_billing, get_web_subscription as _gws
    # only install if routes not already registered
    if not any(getattr(r, "path", None) == "/api/billing/create-checkout-session" for r in app.routes):
        install_billing(app, row_value=_row_value, require_user=_require_current_user, redact=_redact)
except Exception as _exc:
    logger.warning("web_billing install skipped: %s", type(_exc).__name__)


# ============================================================
# WEB TTS (ElevenLabs)
# ============================================================

class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    style: Optional[str] = "human"  # slow | normal | human | fast
    voice: Optional[str] = "bella"  # bella | male


# Default ElevenLabs voice IDs (override via env)
# Bella (female): hpp4J3VqNfWAUOO0d1Us  — same default as ai_engine / bot
# Adam (male):    pNInz6obpgDQGcFmaJgB
_DEFAULT_VOICE_BELLA = "hpp4J3VqNfWAUOO0d1Us"
_DEFAULT_VOICE_MALE = "pNInz6obpgDQGcFmaJgB"


def _resolve_elevenlabs_voice_id(voice: str = "bella") -> str:
    v = (voice or "bella").strip().lower()
    if v in ("male", "man", "adam", "guy"):
        return (
            os.getenv("ELEVENLABS_VOICE_ID_MALE")
            or os.getenv("ELEVENLABS_MALE_VOICE_ID")
            or _DEFAULT_VOICE_MALE
        ).strip()
    # bella / female / default
    return (
        os.getenv("ELEVENLABS_VOICE_ID_BELLA")
        or os.getenv("ELEVENLABS_VOICE_ID")
        or _DEFAULT_VOICE_BELLA
    ).strip()


def _elevenlabs_tts_bytes(text: str, style: str = "human", voice: str = "bella") -> bytes:
    """Generate MP3 via ElevenLabs (Bella or male). Raises HTTPException on failure."""
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="ElevenLabs not configured")
    voice_id = _resolve_elevenlabs_voice_id(voice)
    model_id = (
        os.getenv("ELEVENLABS_MODEL_ID")
        or os.getenv("ELEVENLABS_MODEL")
        or "eleven_multilingual_v2"
    ).strip()
    speed_map = {"slow": 0.8, "normal": 1.0, "human": 0.95, "fast": 1.15}
    speed = speed_map.get((style or "human").lower(), 0.95)
    clean = " ".join(str(text).split())[:2000]
    if not clean:
        raise HTTPException(status_code=400, detail="Text empty")

    import urllib.request
    import json as _json

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": clean,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
            "style": 0.35 if style == "human" else 0.2,
            "use_speaker_boost": True,
            "speed": speed,
        },
    }

    req = urllib.request.Request(
        url,
        data=_json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
            if not data:
                raise HTTPException(status_code=502, detail="Empty TTS audio")
            return data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("ElevenLabs TTS failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="TTS generation failed")


@app.post("/api/tts")
async def tts_endpoint(request: Request, body: TtsRequest):
    """Authenticated web TTS — ElevenLabs Bella or male voice, returns audio/mpeg."""
    await asyncio.to_thread(_require_current_user, request)
    style = (body.style or "human").lower()
    if style not in ("slow", "normal", "human", "fast"):
        style = "human"
    voice = (body.voice or "bella").lower()
    if voice not in ("bella", "female", "male", "man", "adam", "guy"):
        voice = "bella"
    audio = await asyncio.to_thread(
        _elevenlabs_tts_bytes, body.text, style, voice
    )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline; filename=kz-voice.mp3",
        },
    )





# ============================================================
# MARKETS / SIGNALS / NEWS (web)
# ============================================================

DEFAULT_WEB_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD"]


def _safe_analyze(symbol: str, timeframe: str = "15m") -> Dict[str, Any]:
    try:
        from market import analyze_market

        data = analyze_market(symbol, timeframe=timeframe)
        if not isinstance(data, dict):
            return {"symbol": symbol, "error": "no_data", "signal": "WAIT"}
        # Trim huge payloads
        out = {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": data.get("price") or data.get("current_price"),
            "signal": (
                data.get("signal")
                or data.get("direction")
                or data.get("mtf_signal")
                or data.get("bias")
                or "WAIT"
            ),
            "trend": data.get("trend") or data.get("mtf_bias") or data.get("htf_trend"),
            "confidence": data.get("confidence"),
            "strength": data.get("strength") or data.get("setup_strength") or data.get("mtf_strength"),
            "rsi": data.get("rsi"),
            "support": data.get("support") or data.get("nearest_support"),
            "resistance": data.get("resistance") or data.get("nearest_resistance"),
            "entry": data.get("entry") or data.get("entry_zone") or data.get("ideal_entry"),
            "stop_loss": data.get("stop_loss") or data.get("sl"),
            "tp1": data.get("tp1"),
            "tp2": data.get("tp2"),
            "tp3": data.get("tp3"),
            "reasons": (data.get("reasons") or data.get("notes") or [])[:8],
            "mtf": data.get("mtf") or data.get("mtf_summary"),
            "structure": data.get("structure"),
            "volatility": data.get("volatility"),
        }
        return out
    except Exception as e:
        logger.warning("analyze %s failed: %s", symbol, type(e).__name__)
        return {"symbol": symbol, "error": type(e).__name__, "signal": "WAIT"}


def _safe_news(symbol: str) -> Dict[str, Any]:
    try:
        from market import get_news_risk_safe

        return get_news_risk_safe(symbol) or {}
    except Exception as e:
        return {"news_risk": "UNKNOWN", "error": type(e).__name__}


@app.get("/api/markets")
async def markets_overview(request: Request):
    """Snapshot for BTC/ETH/SOL/XAU — requires login."""
    await asyncio.to_thread(_require_current_user, request)

    def _load():
        rows = []
        for sym in DEFAULT_WEB_SYMBOLS:
            a = _safe_analyze(sym, "15m")
            n = _safe_news(sym)
            a["news"] = n
            rows.append(a)
        return {"status": "success", "symbols": rows, "count": len(rows)}

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("markets overview: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Markets unavailable")


@app.get("/api/markets/{symbol:path}")
async def market_detail(request: Request, symbol: str, timeframe: str = "15m"):
    await asyncio.to_thread(_require_current_user, request)
    sym = symbol.replace("-", "/").upper()
    if "/" not in sym and len(sym) <= 6:
        # BTC -> BTC/USD, XAU -> XAU/USD
        if sym in ("XAU", "GOLD"):
            sym = "XAU/USD"
        else:
            sym = f"{sym}/USD"

    def _load():
        a = _safe_analyze(sym, timeframe or "15m")
        a["news"] = _safe_news(sym)
        return {"status": "success", "market": a}

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("market detail: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Market detail failed")


@app.get("/api/signals")
async def signals_overview(request: Request):
    """Trading signals package (same symbols, signal-focused)."""
    await asyncio.to_thread(_require_current_user, request)

    def _load():
        signals = []
        for sym in DEFAULT_WEB_SYMBOLS:
            a = _safe_analyze(sym, "15m")
            signals.append(
                {
                    "symbol": sym,
                    "signal": a.get("signal"),
                    "price": a.get("price"),
                    "confidence": a.get("confidence"),
                    "trend": a.get("trend"),
                    "entry": a.get("entry"),
                    "stop_loss": a.get("stop_loss"),
                    "tp1": a.get("tp1"),
                    "tp2": a.get("tp2"),
                    "tp3": a.get("tp3"),
                    "rsi": a.get("rsi"),
                    "support": a.get("support"),
                    "resistance": a.get("resistance"),
                    "reasons": a.get("reasons") or [],
                    "error": a.get("error"),
                }
            )
        actionable = [
            s
            for s in signals
            if str(s.get("signal") or "").upper() in ("BUY", "SELL")
        ]
        return {
            "status": "success",
            "signals": signals,
            "actionable_count": len(actionable),
            "disclaimer": "Not financial advice. Trading involves risk.",
        }

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("signals: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Signals unavailable")


@app.get("/api/news")
async def news_overview(request: Request):
    """News risk + headlines per major asset."""
    await asyncio.to_thread(_require_current_user, request)

    def _load():
        items = []
        for sym in DEFAULT_WEB_SYMBOLS:
            n = _safe_news(sym)
            items.append({"symbol": sym, **n})
        # Optional global headlines from news.py
        global_headlines = []
        try:
            from news import get_global_news

            raw = get_global_news()
            if isinstance(raw, list):
                global_headlines = raw[:15]
            elif isinstance(raw, dict):
                global_headlines = (raw.get("headlines") or raw.get("items") or [])[:15]
        except Exception:
            pass
        return {
            "status": "success",
            "assets": items,
            "global_headlines": global_headlines,
            "disclaimer": "News is informational only. Not financial advice.",
        }

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("news: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="News unavailable")




def _require_web_vip(user_row) -> str:
    """Logged-in user must be active web VIP or admin email. Returns user_id."""
    user_id = str(_row_value(user_row, "id", 0))
    email = str(_row_value(user_row, "email", "") or "").strip().lower()
    if _is_admin_email(email):
        return user_id
    sub = _get_web_subscription(user_id)
    if not bool(sub.get("is_subscribed")):
        raise HTTPException(
            status_code=403,
            detail="VIP subscription required for the web agent. Upgrade on the pricing page.",
        )
    return user_id


# ============================================================
# AGENT (Phase 1) — planner, morning brief, job log, auto-learn
# ============================================================

class AgentGoalRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class AgentApproveRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=80)


@app.get("/api/agent/status")
async def agent_status_endpoint(request: Request):
    """Agent capability status. Features require VIP (except this probe)."""
    vip = False
    try:
        user_row = await asyncio.to_thread(_require_current_user, request)
        try:
            await asyncio.to_thread(_require_web_vip, user_row)
            vip = True
        except HTTPException:
            vip = False
    except HTTPException:
        pass
    try:
        from agent_core import agent_status, init_agent_db

        await asyncio.to_thread(init_agent_db)
        return {
            "status": "ok",
            "vip_required": True,
            "vip_active": vip,
            **agent_status(),
        }
    except ImportError as exc:
        logger.error("agent_core import failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Agent unavailable: agent_core.py missing on server",
        )
    except Exception as exc:
        logger.error("agent status failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Agent unavailable: {type(exc).__name__}",
        )


@app.post("/api/agent/run")
async def agent_run_endpoint(request: Request, body: AgentGoalRequest):
    """Run planner for a user goal (safe tools auto-run; risky need approval). VIP only."""
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import plan_and_run

        result = await asyncio.to_thread(plan_and_run, body.goal, user_id, True)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error("agent run failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Agent run failed")


@app.post("/api/agent/morning-brief")
async def agent_morning_brief_endpoint(request: Request):
    """Generate overnight market watch + morning signals (BTC/ETH/SOL/XAU). VIP only."""
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import build_morning_brief

        brief = await asyncio.to_thread(build_morning_brief, None, user_id)
        return {"status": "success", "brief": brief}
    except Exception as exc:
        logger.error("morning brief failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Morning brief failed")


@app.get("/api/agent/morning-brief/latest")
async def agent_latest_brief_endpoint(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import get_latest_morning_brief

        brief = await asyncio.to_thread(get_latest_morning_brief, user_id)
        if not brief:
            return {"status": "empty", "brief": None}
        return {"status": "success", "brief": brief}
    except Exception as exc:
        logger.error("latest brief failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load brief")


@app.get("/api/agent/jobs")
async def agent_list_jobs_endpoint(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import list_jobs

        jobs = await asyncio.to_thread(list_jobs, user_id, 40)
        return {"status": "success", "jobs": jobs}
    except Exception as exc:
        logger.error("list jobs failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not list jobs")


@app.post("/api/agent/jobs/approve")
async def agent_approve_job_endpoint(request: Request, body: AgentApproveRequest):
    user_row = await asyncio.to_thread(_require_current_user, request)
    _ = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import approve_job, get_job

        job = await asyncio.to_thread(approve_job, body.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"status": "success", "job": job}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("approve job failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not approve job")


@app.get("/api/agent/learning")
async def agent_learning_endpoint(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    user_id = await asyncio.to_thread(_require_web_vip, user_row)
    try:
        from agent_core import recent_learning

        items = await asyncio.to_thread(recent_learning, user_id, 30)
        return {"status": "success", "learning": items}
    except Exception as exc:
        logger.error("learning list failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load learning")


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
