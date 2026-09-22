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

    return {
        "id": str(
            _row_value(row, "id", 0)
        ),
        "email": _row_value(
            row,
            "email",
            1,
        ),
        "username": _row_value(
            row,
            "username",
            2,
        ),
        "display_name": _row_value(
            row,
            "display_name",
            3,
        ),
        "account_status": _row_value(
            row,
            "account_status",
            4,
        ),
        "created_at": str(
            _row_value(
                row,
                "created_at",
                5,
            )
        ),
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
    def __init__(self, web_user_id: str):
        self.web_user_id = str(web_user_id)

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
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (self.web_user_id, limit),
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
                # Get or create the user's most recent conversation
                cur.execute(
                    "SELECT id FROM web_conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (self.web_user_id,),
                )
                row = cur.fetchone()
                if row:
                    conv_id = str(_row_value(row, "id", 0))
                else:
                    cur.execute(
                        "INSERT INTO web_conversations (user_id, title) VALUES (%s, 'Web Chat') RETURNING id",
                        (self.web_user_id,),
                    )
                    conv_id = str(_row_value(cur.fetchone(), "id", 0))

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

def _get_or_create_conversation(user_id: str) -> str:
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT id FROM web_conversations WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1", (user_id,))
        row = cur.fetchone()
    if row:
        return str(_row_value(row, "id", 0))
    with get_db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO web_conversations (user_id, title) VALUES (%s, %s) RETURNING id", (user_id, "Web Chat"))
        row = cur.fetchone()
    return str(_row_value(row, "id", 0))

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

async def _run_web_ai(user_id: str, message: str, image_data: Optional[Tuple[str, bytes]] = None) -> str:
    """Run the AI engine with optional image data."""
    web_memory = WebMemoryAdapter(user_id)
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
    return {"status": "success", "user": _user_public_data(user_row)}

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
        conversation_id = await asyncio.to_thread(_get_or_create_conversation, user_id)
        # NOTE: Do NOT call _save_web_message here. The AIEngine's WebMemoryAdapter
        # now handles saving both user and assistant messages to web_messages.
        response_text = await _run_web_ai(user_id, enriched_message, image_data)
        return {"status": "success", "reply": response_text, "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Web chat failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="AI processing failed")

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
