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
    sub = _get_web_subscription(user_id)
    return {
        "id": user_id,
        "email": _row_value(row, "email", 1),
        "username": _row_value(row, "username", 2),
        "display_name": _row_value(row, "display_name", 3),
        "account_status": _row_value(row, "account_status", 4),
        "created_at": str(_row_value(row, "created_at", 5)),
        "is_subscribed": bool(sub.get("is_subscribed")),
        "plan": sub.get("plan"),
        "subscription_expires_at": sub.get("expires_at"),
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

@app.post("/api/auth/register")
async def register(payload: RegisterRequest, request: Request, response: Response):
    email = _normalize_email(payload.email)
    username = _normalize_username(payload.username)
    display_name = _safe_display_name(payload.display_name, email.split("@")[0])
    try:
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
        raw_token = await asyncio.to_thread(_create_session, user_id, request)
        _set_session_cookie(response, raw_token)
        return {"status": "success", "message": "Account created successfully", "user": _user_public_data(user_row)}
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
        account_status = _row_value(user_row, "account_status", 4)
        if account_status != "active":
            raise HTTPException(status_code=403, detail="This account is not active")
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
ADMIN_EMAILS = {
    e.strip().lower()
    for e in (os.getenv("ADMIN_EMAILS") or os.getenv("ADMIN_EMAIL") or "").split(",")
    if e.strip()
}

# USD amounts in cents for Checkout (override via env)
STRIPE_AMOUNT_MONTHLY = int(os.getenv("STRIPE_AMOUNT_MONTHLY", "999"))
STRIPE_AMOUNT_QUARTERLY = int(os.getenv("STRIPE_AMOUNT_QUARTERLY", "2499"))
STRIPE_AMOUNT_YEARLY = int(os.getenv("STRIPE_AMOUNT_YEARLY", "7999"))

WEB_PLAN_CATALOG = {
    "monthly": {"name": "Monthly VIP", "days": 30, "amount": STRIPE_AMOUNT_MONTHLY},
    "quarterly": {"name": "90-Day VIP", "days": 90, "amount": STRIPE_AMOUNT_QUARTERLY},
    "3month": {"name": "90-Day VIP", "days": 90, "amount": STRIPE_AMOUNT_QUARTERLY},
    "yearly": {"name": "Yearly VIP", "days": 365, "amount": STRIPE_AMOUNT_YEARLY},
}


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
) -> None:
    _ensure_billing_tables()
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_payments (
                user_id, email, plan, amount_cents, currency,
                stripe_session_id, stripe_payment_intent, status
            ) VALUES (%s, %s, %s, %s, 'usd', %s, %s, %s)
            """,
            (
                str(user_id),
                email,
                plan,
                amount_cents,
                session_id,
                payment_intent,
                status,
            ),
        )


def _is_admin_email(email: Optional[str]) -> bool:
    if not email or not ADMIN_EMAILS:
        return False
    return str(email).strip().lower() in ADMIN_EMAILS


class CheckoutRequest(BaseModel):
    plan: str = Field(..., min_length=2, max_length=32)


@app.post("/api/billing/create-checkout-session")
async def create_checkout_session(payload: CheckoutRequest, request: Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured. Set STRIPE_SECRET_KEY on the API server.",
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

    def _create():
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
                        "unit_amount": plan["amount"],
                        "product_data": {
                            "name": f"King Zarry AI — {plan['name']}",
                            "description": f"{plan['days']} days VIP web access",
                        },
                    },
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user_id,
                "plan": plan_key,
                "days": str(plan["days"]),
            },
            client_reference_id=user_id,
        )
        return session

    try:
        session = await asyncio.to_thread(_create)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Stripe checkout failed: %s: %s", type(exc).__name__, _redact(str(exc)))
        raise HTTPException(status_code=500, detail="Could not start Stripe checkout")
    return {
        "status": "success",
        "checkout_url": session.url,
        "session_id": session.id,
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


@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    user_row = await asyncio.to_thread(_require_current_user, request)
    email = str(_row_value(user_row, "email", 1) or "")
    if not _is_admin_email(email):
        raise HTTPException(status_code=403, detail="Admin access required")
    _ensure_billing_tables()

    def _load():
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM web_subscriptions
                WHERE is_subscribed = TRUE
                  AND (expires_at IS NULL OR expires_at > NOW())
                """
            )
            active = _row_value(cur.fetchone(), "c", 0) or 0
            cur.execute("SELECT COUNT(*) AS c, COALESCE(SUM(amount_cents),0) AS s FROM web_payments WHERE status = 'paid'")
            pay = cur.fetchone()
            payments = _row_value(pay, "c", 0) or 0
            revenue_cents = _row_value(pay, "s", 1) or 0
            cur.execute(
                """
                SELECT email, plan, amount_cents, status, created_at
                FROM web_payments
                ORDER BY created_at DESC
                LIMIT 50
                """
            )
            rows = cur.fetchall() or []
        recent = []
        for r in rows:
            recent.append(
                {
                    "email": _row_value(r, "email", 0),
                    "plan": _row_value(r, "plan", 1),
                    "amount_cents": _row_value(r, "amount_cents", 2),
                    "status": _row_value(r, "status", 3),
                    "created_at": str(_row_value(r, "created_at", 4)),
                }
            )
        return {
            "status": "success",
            "active_subscribers": int(active),
            "payments_count": int(payments),
            "revenue_cents": int(revenue_cents),
            "revenue_usd": round(int(revenue_cents) / 100.0, 2),
            "recent_payments": recent,
        }

    try:
        return await asyncio.to_thread(_load)
    except Exception as exc:
        logger.error("admin stats failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load admin stats")



# Prefer modular billing if present (remote-friendly install)
try:
    from web_billing import install_billing, get_web_subscription as _gws
    # only install if routes not already registered
    if not any(getattr(r, "path", None) == "/api/billing/create-checkout-session" for r in app.routes):
        install_billing(app, row_value=_row_value, require_user=_require_current_user, redact=_redact)
except Exception as _exc:
    logger.warning("web_billing install skipped: %s", type(_exc).__name__)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
