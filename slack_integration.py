"""Slack Events API bridge for KING ZARRY AI.

This module is intentionally additive: it attaches a Slack Events endpoint to the
existing FastAPI app and reuses the existing AIEngine + SharedMemory stack.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import threading
import time
from typing import Any, Dict, Optional

import requests
from fastapi import Request
from fastapi.responses import JSONResponse

try:
    from shared_memory import SharedMemory
    from ai_engine import AIEngine
except Exception:
    SharedMemory = None
    AIEngine = None


SLACK_BOT_TOKEN = (os.getenv("SLACK_BOT_TOKEN") or "").strip()
SLACK_SIGNING_SECRET = (os.getenv("SLACK_SIGNING_SECRET") or "").strip()
SLACK_MAX_AGE_SECONDS = max(60, int(os.getenv("SLACK_MAX_EVENT_AGE", "300") or "300"))
SLACK_REPLY_TIMEOUT = max(5, int(os.getenv("SLACK_REPLY_TIMEOUT", "30") or "30"))
SLACK_BRIDGE_KEY = (os.getenv("KING_ZARRY_SLACK_BRIDGE_KEY") or "").strip()

_memory = None
_ai = None
_seen_events: Dict[str, float] = {}
_seen_lock = threading.Lock()


def _get_ai():
    global _memory, _ai
    if _ai is None:
        if SharedMemory is None or AIEngine is None:
            raise RuntimeError("AI engine imports are unavailable")
        memory_path = (os.getenv("MEMORY_DB_PATH") or "king_zarry_memory.db").strip()
        _memory = SharedMemory("slack", memory_path)
        _ai = AIEngine(memory=_memory)
    return _ai


def _verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    if not SLACK_SIGNING_SECRET or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > SLACK_MAX_AGE_SECONDS:
        return False
    base = b"v0:" + timestamp.encode("utf-8") + b":" + body
    digest = hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        base,
        hashlib.sha256,
    ).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature)


def _mark_event_seen(event_id: str) -> bool:
    if not event_id:
        return False
    now = time.time()
    with _seen_lock:
        expired = [key for key, seen_at in _seen_events.items() if now - seen_at > 600]
        for key in expired:
            _seen_events.pop(key, None)
        if event_id in _seen_events:
            return True
        _seen_events[event_id] = now
        return False


def _ask_ai(user_id: str, prompt: str) -> str:
    ai = _get_ai()
    response = ai.ask(user_id=str(user_id), prompt=str(prompt), image=None)
    response_text = str(response or "").strip()
    return response_text or "I’m here, but I didn’t get a usable response from the AI engine."


def _post_message(channel: str, text: str, thread_ts: Optional[str] = None) -> None:
    if not SLACK_BOT_TOKEN:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    payload: Dict[str, Any] = {"channel": channel, "text": text[:39000]}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=SLACK_REPLY_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack chat.postMessage failed: {data.get('error', 'unknown_error')}")


def _clean_prompt(text: str) -> str:
    text = re.sub(r"<@[A-Z0-9]+>", " ", text or "")
    text = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _process_event(event: Dict[str, Any]) -> None:
    channel = event.get("channel")
    user_id = event.get("user")
    if not channel or not user_id:
        return

    prompt = _clean_prompt(event.get("text", ""))
    if not prompt:
        _post_message(
            channel,
            "Hey 👑 I’m here. What do you want to work on?",
            event.get("thread_ts") or (event.get("ts") if event.get("channel_type") != "im" else None),
        )
        return

    try:
        response_text = _ask_ai(user_id=str(user_id), prompt=prompt)
        thread_ts = event.get("thread_ts")
        if event.get("channel_type") != "im" and not thread_ts:
            thread_ts = event.get("ts")
        _post_message(channel, response_text, thread_ts)
    except Exception:
        _post_message(
            channel,
            "I hit a temporary AI processing error. Please try that message again.",
            event.get("thread_ts") or (event.get("ts") if event.get("channel_type") != "im" else None),
        )


def install_slack_integration(app):
    @app.post("/api/slack/events")
    async def slack_events(request: Request):
        body = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        if not _verify_signature(body, timestamp, signature):
            return JSONResponse({"ok": False, "error": "invalid_signature"}, status_code=401)

        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

        if payload.get("type") == "url_verification":
            return JSONResponse({"challenge": payload.get("challenge", "")})

        if payload.get("type") != "event_callback":
            return JSONResponse({"ok": True})

        event_id = str(payload.get("event_id") or "")
        if _mark_event_seen(event_id):
            return JSONResponse({"ok": True, "duplicate": True})

        event = payload.get("event") or {}
        event_type = event.get("type")
        if event.get("bot_id") or event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
            return JSONResponse({"ok": True})

        should_process = (
            event_type == "app_mention"
            or (event_type == "message" and event.get("channel_type") == "im")
        )
        if should_process:
            threading.Thread(
                target=_process_event,
                args=(event,),
                daemon=True,
                name="slack-ai-event",
            ).start()

        return JSONResponse({"ok": True})

    @app.post("/api/slack/vercel")
    async def slack_vercel_bridge(request: Request):
        """Process a Slack message delivered by the Vercel Connect/Eve bridge.

        Vercel Connect owns Slack authentication and outbound posting. This
        endpoint only invokes KING ZARRY AI and returns the generated text.
        It is protected by a separate shared service key and never exposes
        Slack credentials to the Fast backend.
        """
        if not SLACK_BRIDGE_KEY:
            return JSONResponse({"ok": False, "error": "bridge_not_configured"}, status_code=503)

        supplied = (request.headers.get("X-King-Zarry-Bridge-Key") or "").strip()
        if not supplied or not hmac.compare_digest(supplied, SLACK_BRIDGE_KEY):
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)

        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

        user_id = str(payload.get("user_id") or "").strip()
        prompt = str(payload.get("prompt") or "").strip()
        if not user_id or not prompt:
            return JSONResponse({"ok": False, "error": "user_id_and_prompt_required"}, status_code=400)
        if len(prompt) > 12000:
            return JSONResponse({"ok": False, "error": "prompt_too_long"}, status_code=413)

        try:
            response_text = _ask_ai(user_id=user_id, prompt=prompt)
            return {"ok": True, "response": response_text[:39000]}
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": "ai_processing_failed", "detail": type(exc).__name__},
                status_code=500,
            )

    @app.get("/api/slack/health")
    async def slack_health():
        configured = bool(SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET)
        bridge_configured = bool(SLACK_BRIDGE_KEY)
        return {
            "ok": configured or bridge_configured,
            "legacy_events": configured,
            "vercel_connect_bridge": bridge_configured,
            "platform": "slack",
            "ai_engine": bool(AIEngine),
            "memory": bool(SharedMemory),
            "configured": configured,
        }

    print(
        "🤝 Slack bridge installed | legacy_configured="
        + str(bool(SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET))
        + " | vercel_connect_bridge="
        + str(bool(SLACK_BRIDGE_KEY)),
        flush=True,
    )
