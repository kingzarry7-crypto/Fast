"""
KING ZARRY AI - WEB API BOUNDARY
WEB ONLY - First safe foundation step
- Uses Neon PostgreSQL via DATABASE_URL (database.py)
- Never touches Telegram SQLite (king_zarry_memory.db)
- Never instantiates Memory() for web requests
- Wraps synchronous AIEngine.ask() via asyncio.to_thread
"""

import os
import re
import uuid
import asyncio
import logging
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Actual existing class - verified via inspection
from ai_engine import AIEngine

# Web DB layer - root-level database.py (actual repo structure: Fast/database.py)
# This module connects ONLY to Neon PostgreSQL via DATABASE_URL
from database import get_db_cursor, is_database_configured

logger = logging.getLogger("king_zarry_api")

app = FastAPI(title="KingZarry AI Mobile API - Web Boundary")

# ==============================
# Request model - keep compatible
# ==============================
class ChatRequest(BaseModel):
    user_id: str
    message: str

# ==============================
# Helpers - UUID validation, redaction
# ==============================
def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    return text[:500]

# ==============================
# WEB-ONLY Memory Adapter
# Satisfies only methods AIEngine.ask() actually calls:
# - get_history(user_id, limit)
# - get_trading_context(user_id)
# - get_facts(user_id, limit)
# - count(user_id)
# - add_message(user_id, role, content)
# Uses Neon tables: web_ai_memories, web_conversations, web_messages
# Never uses king_zarry_memory.db
# ==============================
class WebMemoryAdapter:
    """
    Minimal adapter for web users.
    Uses Neon PostgreSQL web_* tables via get_db_cursor.
    Does NOT instantiate memory.py Memory().
    """

    def __init__(self, web_user_id: str):
        # web_user_id is UUID string from web_users.id
        self.web_user_id = web_user_id

    # Called by AIEngine._load_memory_history
    def get_history(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        if get_db_cursor is None:
            return []
        try:
            limit = max(1, min(int(limit), 50))
            with get_db_cursor(commit=False) as cur:
                # Fetch from web_messages joined to web_conversations for this web user
                cur.execute("""
                    SELECT m.role, m.content, m.created_at
                    FROM web_messages m
                    JOIN web_conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = %s
                    ORDER BY m.created_at DESC
                    LIMIT %s
                """, (self.web_user_id, limit))
                rows = cur.fetchall()
                # rows may be RealDictRow
                result = []
                for r in rows:
                    try:
                        role = r["role"] if isinstance(r, dict) else r[0]
                        content = r["content"] if isinstance(r, dict) else r[1]
                        created = r["created_at"] if isinstance(r, dict) else r[2]
                    except Exception:
                        # fallback tuple access
                        try:
                            role, content = r[0], r[1]
                            created = r[2] if len(r) > 2 else ""
                        except Exception:
                            continue
                    result.append({"role": str(role), "content": str(content), "created_at": str(created)})
                return result
        except Exception as e:
            logger.warning(f"WebMemoryAdapter.get_history failed: {type(e).__name__}")
            return []

    # Called by AIEngine._load_persistent_context
    def get_trading_context(self, user_id: str) -> str:
        # Web has web_user_settings.trading_preferences JSONB, but keep minimal for now
        # Return empty to avoid breaking, could be enhanced later
        if get_db_cursor is None:
            return ""
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT trading_preferences FROM web_user_settings
                    WHERE user_id = %s
                """, (self.web_user_id,))
                row = cur.fetchone()
                if row:
                    prefs = row["trading_preferences"] if isinstance(row, dict) else row[0]
                    if prefs:
                        # prefs is JSONB dict
                        if isinstance(prefs, dict):
                            lines = [f"{k}: {v}" for k, v in prefs.items() if v]
                            return "\n".join(lines)[:1000]
                        return str(prefs)[:1000]
                return ""
        except Exception:
            return ""

    def get_facts(self, user_id: str, limit: int = 20) -> List[Dict[str, str]]:
        # Web uses web_ai_memories with memory_type='fact' or 'preference'
        if get_db_cursor is None:
            return []
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT content, memory_type, created_at
                    FROM web_ai_memories
                    WHERE user_id = %s AND memory_type IN ('fact','preference')
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (self.web_user_id, max(1, min(int(limit), 50))))
                rows = cur.fetchall()
                facts = []
                for r in rows:
                    try:
                        content = r["content"] if isinstance(r, dict) else r[0]
                        mtype = r["memory_type"] if isinstance(r, dict) else r[1]
                        facts.append({"fact": str(content), "category": str(mtype)})
                    except Exception:
                        continue
                return facts
        except Exception:
            return []

    def count(self, user_id: str = None) -> int:
        if get_db_cursor is None:
            return 0
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM web_messages m
                    JOIN web_conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = %s
                """, (self.web_user_id,))
                row = cur.fetchone()
                if row:
                    cnt = row["cnt"] if isinstance(row, dict) else row[0]
                    return int(cnt)
                return 0
        except Exception:
            return 0

    def add_message(self, user_id: str, role: str, content: str):
        # Called by AIEngine._save_memory - save to web_ai_memories to keep web memory separate
        # Do NOT write to king_zarry_memory.db
        if get_db_cursor is None:
            return
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO web_ai_memories (user_id, role, content, memory_type)
                    VALUES (%s, %s, %s, 'conversation')
                """, (self.web_user_id, str(role)[:50], str(content)[:8000]))
        except Exception as e:
            logger.warning(f"WebMemoryAdapter.add_message failed: {type(e).__name__}")

    # Additional helpers for completeness (not required by AIEngine but useful)
    def get_memory_facts_text(self, user_id: str, limit: int = 30) -> str:
        facts = self.get_facts(user_id, limit=limit)
        if not facts:
            return ""
        return "\n".join(f"- {f['fact']}" for f in facts)


# ==============================
# Web DB helpers for api.py flow
# Uses actual columns from web_database.sql
# ==============================
def _ensure_web_user(supplied_user_id: str) -> str:
    """
    Minimum safe lookup/create for web_users.
    Returns UUID string of web_users.id
    Never touches SQLite.
    """
    if get_db_cursor is None:
        raise ValueError("Web database not configured")

    supplied_user_id = str(supplied_user_id).strip()
    if not supplied_user_id:
        raise ValueError("user_id empty")

    # If supplied is UUID, try lookup by id
    if _is_valid_uuid(supplied_user_id):
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT id FROM web_users WHERE id = %s", (supplied_user_id,))
                row = cur.fetchone()
                if row:
                    uid = row["id"] if isinstance(row, dict) else row[0]
                    return str(uid)
        except Exception:
            pass
        # If UUID supplied but not found, we will create user with that exact UUID if possible
        # Else fallback to username lookup

    # Try lookup by username or email
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id FROM web_users
                WHERE username = %s OR email = %s
                LIMIT 1
            """, (supplied_user_id, supplied_user_id))
            row = cur.fetchone()
            if row:
                uid = row["id"] if isinstance(row, dict) else row[0]
                return str(uid)
    except Exception as e:
        logger.warning(f"_ensure_web_user lookup failed: {type(e).__name__}")

    # Create new web user
    try:
        with get_db_cursor(commit=True) as cur:
            # Determine email
            if "@" in supplied_user_id and "." in supplied_user_id:
                email = supplied_user_id[:255]
                username = supplied_user_id.split("@")[0][:100]
            else:
                email = f"{supplied_user_id[:100]}@web.local"[:255]
                username = supplied_user_id[:100]

            # If supplied_user_id is UUID, use it as id, else gen_random_uuid
            if _is_valid_uuid(supplied_user_id):
                cur.execute("""
                    INSERT INTO web_users (id, email, password_hash, username, display_name, account_status)
                    VALUES (%s, %s, %s, %s, %s, 'active')
                    ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username
                    RETURNING id
                """, (supplied_user_id, email, "web_placeholder_not_for_login", username, supplied_user_id[:255]))
            else:
                cur.execute("""
                    INSERT INTO web_users (email, password_hash, username, display_name, account_status)
                    VALUES (%s, %s, %s, %s, 'active')
                    ON CONFLICT (email) DO UPDATE SET username = EXCLUDED.username
                    RETURNING id
                """, (email, "web_placeholder_not_for_login", username, supplied_user_id[:255]))

            row = cur.fetchone()
            uid = row["id"] if isinstance(row, dict) else row[0]
            return str(uid)
    except Exception as e:
        logger.error(f"_ensure_web_user create failed: {type(e).__name__}")
        # Try to handle unique violation race
        try:
            with get_db_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT id FROM web_users
                    WHERE username = %s OR email = %s
                    LIMIT 1
                """, (supplied_user_id, f"{supplied_user_id[:100]}@web.local"))
                row = cur.fetchone()
                if row:
                    uid = row["id"] if isinstance(row, dict) else row[0]
                    return str(uid)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to ensure web user")


def _get_or_create_conversation(web_user_uuid: str) -> str:
    """
    Get latest conversation or create new one.
    Returns conversation UUID.
    """
    if get_db_cursor is None:
        raise ValueError("Web database not configured")
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("""
                SELECT id FROM web_conversations
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (web_user_uuid,))
            row = cur.fetchone()
            if row:
                cid = row["id"] if isinstance(row, dict) else row[0]
                return str(cid)
    except Exception:
        pass

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO web_conversations (user_id, title)
                VALUES (%s, %s)
                RETURNING id
            """, (web_user_uuid, "Web Chat"))
            row = cur.fetchone()
            cid = row["id"] if isinstance(row, dict) else row[0]
            return str(cid)
    except Exception as e:
        logger.error(f"_get_or_create_conversation failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


def _save_web_message(conversation_id: str, role: str, content: str) -> str:
    """
    Persist message to web_messages.
    Returns message id.
    """
    if get_db_cursor is None:
        return ""
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO web_messages (conversation_id, role, content)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (conversation_id, role[:50], content[:8000]))
            row = cur.fetchone()
            mid = row["id"] if isinstance(row, dict) else row[0]
            # Also bump conversation updated_at via trigger already, but ensure
            try:
                cur.execute("UPDATE web_conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
            except Exception:
                pass
            return str(mid)
    except Exception as e:
        logger.warning(f"_save_web_message failed: {type(e).__name__}")
        return ""


# ==============================
# AI Engine Singleton - WEB ONLY
# Does NOT instantiate Memory() - uses WebMemoryAdapter per request
# ==============================
# Create a single AIEngine instance without Telegram Memory
# AIEngine.__init__(memory=None) is valid - it will have memory=None initially
# We will inject WebMemoryAdapter per request via direct assignment
_web_ai_engine = None

def get_web_ai_engine():
    global _web_ai_engine
    if _web_ai_engine is None:
        # Do NOT pass Memory() - keep None for base, adapter injected per request
        _web_ai_engine = AIEngine(memory=None)
    return _web_ai_engine


# ==============================
# FastAPI Routes
# ==============================
@app.get("/")
def read_root():
    return {"status": "KingZarry AI API is active", "mode": "web", "db": "neon"}

@app.get("/health")
def health_check():
    try:
        configured = is_database_configured() if callable(is_database_configured) else False
    except Exception:
        configured = False
    return {"status": "ok", "web_db_configured": configured}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Basic validation
        user_id_raw = str(request.user_id or "").strip()
        message_raw = str(request.message or "").strip()

        if not user_id_raw:
            raise HTTPException(status_code=400, detail="user_id required")
        if not message_raw:
            raise HTTPException(status_code=400, detail="message required")
        if len(message_raw) > 4000:
            raise HTTPException(status_code=400, detail="message too long (max 4000)")

        # 1. Identify web user (Neon)
        try:
            web_user_uuid = await asyncio.to_thread(_ensure_web_user, user_id_raw)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ensure web user error: {type(e).__name__}")
            raise HTTPException(status_code=500, detail="Failed to process user")

        # 2. Get/create conversation
        try:
            conversation_id = await asyncio.to_thread(_get_or_create_conversation, web_user_uuid)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"conversation error: {type(e).__name__}")
            raise HTTPException(status_code=500, detail="Failed to process conversation")

        # 3. Save user message to web_messages
        try:
            await asyncio.to_thread(_save_web_message, conversation_id, "user", message_raw)
        except Exception as e:
            logger.warning(f"save user message failed: {type(e).__name__}")
            # non-fatal, continue

        # 4. Prepare AI engine with web-only memory adapter
        try:
            ai_engine = get_web_ai_engine()
            # Inject web memory adapter for this request (per-user)
            # AIEngine.ask uses self.memory.get_history etc. - our adapter implements those
            web_memory = WebMemoryAdapter(web_user_uuid)
            # Temporarily set memory - thread-safe via copy? AIEngine is shared, so set per call
            # To avoid race, we create a shallow copy of engine with this memory
            # Simplest: set, call, then restore - but better to create new instance per request to avoid cross-user leak
            # Since AIEngine.__init__ is cheap and stateless except memory, create per-request instance
            request_engine = AIEngine(memory=web_memory)

            # 5. Call synchronous ask() via threadpool - MUST NOT block event loop
            response_text = await asyncio.to_thread(
                request_engine.ask,
                user_id_raw,  # keep original supplied id for context, but adapter uses web UUID internally
                message_raw,
                None
            )

            if not response_text:
                response_text = "AI temporarily unavailable. Please try again."

        except Exception as e:
            logger.error(f"AI engine error: {type(e).__name__}: {_redact(str(e))}")
            raise HTTPException(status_code=500, detail="AI processing failed")

        # 6. Save assistant response to web_messages
        try:
            await asyncio.to_thread(_save_web_message, conversation_id, "assistant", response_text)
        except Exception as e:
            logger.warning(f"save assistant message failed: {type(e).__name__}")

        # Return simple backward-compatible response
        # Optionally include conversation_id without breaking contract
        return {"status": "success", "reply": response_text, "conversation_id": conversation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled /api/chat error: {type(e).__name__}")
        # Do NOT expose raw exception, keys, DATABASE_URL, stack trace
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
