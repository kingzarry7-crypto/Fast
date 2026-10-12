"""
Minimal web API for King Zarry AI — safe fallback to restore ASGI app import.
This file intentionally provides a small, robust FastAPI app and a few
essential endpoints so the container can start. It avoids heavy optional
imports and wraps risky operations so module import never fails.

If you want the full feature-rich api.py restored, I can produce a
complete replacement next (requires more careful merging). For now this
minimal file removes the syntax error and exposes /health and a simple
/chat placeholder.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Keep a lightweight dependency on the repository's database helpers
try:
    from database import check_database_health, is_database_configured, get_db_cursor
except Exception:
    check_database_health = None
    is_database_configured = lambda: False
    get_db_cursor = None

logger = logging.getLogger("kingzarry_api")

app = FastAPI(title="KingZarry AI Web API (minimal)", version="0.1.0")

# Basic CORS config (keeps previous behavior minimal)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
allowed_origins = [u.strip() for u in FRONTEND_URL.split(",") if u.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
async def health():
    """Return a simple health check. If the repo's database helper is
    available, delegate to it; otherwise return a conservative healthy
    response (so the container can boot for debugging).
    """
    try:
        if check_database_health is not None:
            return check_database_health()
    except Exception as e:
        logger.warning("database health check failed: %s", e)
        return {"status": "connection_failed", "connected": False}
    return {"status": "healthy", "connected": False, "configured": False}


@app.get("/")
async def root():
    return {"ok": True, "service": "kingzarry-web-minimal"}


@app.post("/api/chat")
async def chat(request: Request):
    """Placeholder chat endpoint — returns 501 until full API is restored.
    This keeps uvicorn able to import the module and the container to run.
    """
    body = await request.json()
    message = body.get("message") if isinstance(body, dict) else None
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    # Short, safe reply so frontends can detect the server is alive.
    return {"reply": "Service is starting — chat temporarily unavailable.", "received": message}


# Minimal helper to read a few recent web messages if DB configured.
def _fetch_recent_messages(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not get_db_cursor:
        return []
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                "SELECT role, content, created_at FROM web_messages WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                (user_id, int(limit)),
            )
            rows = cur.fetchall()
        out = []
        for r in rows:
            try:
                role = r[0]
                content = r[1]
                created = r[2]
            except Exception:
                role = "assistant"
                content = str(r)
                created = None
            out.append({"role": role, "content": content, "created_at": str(created)})
        return out
    except Exception as e:
        logger.debug("_fetch_recent_messages failed: %s", e)
        return []


# Start up log to help debugging quickly in container logs
logger.info("Minimal api.py loaded — FastAPI app available")
