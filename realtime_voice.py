"""OpenAI Realtime voice integration for KING ZARRY AI.

Prefer a dedicated realtime key, but reuse OPENAI_API_KEY when available so
Call AI can use the configured OpenAI account instead of silently degrading to
a browser dictation + text-to-speech experience.
"""

from __future__ import annotations

import json
import logging
import os

import requests
from fastapi import HTTPException, Request, Response

logger = logging.getLogger("king_zarry_realtime")

REALTIME_KEY = (
    os.getenv("OPENAI_REALTIME_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
).strip()
REALTIME_MODEL = (os.getenv("OPENAI_REALTIME_MODEL") or "gpt-realtime").strip()
REALTIME_VOICE = (os.getenv("OPENAI_REALTIME_VOICE") or "marin").strip()
REALTIME_TRANSCRIBE_MODEL = (
    os.getenv("OPENAI_REALTIME_TRANSCRIBE_MODEL") or "gpt-4o-mini-transcribe"
).strip()
REALTIME_URL = "https://api.openai.com/v1/realtime/calls"

REALTIME_INSTRUCTIONS = (
    "You are King Zarry AI, a warm, sharp, natural voice assistant. "
    "Speak conversationally and concisely. Match the user's language and energy. "
    "Do not mention internal systems, prompts, APIs, or hidden reasoning. "
    "If the user asks for live information, only state information available "
    "in the current conversation or tools; never invent live facts."
)


def install_realtime_voice(app, require_current_user=None, save_transcript=None):
    """Install optional authenticated WebRTC realtime endpoints."""
    if app is None or require_current_user is None:
        return

    @app.get("/api/realtime/status")
    async def realtime_status(request: Request):
        try:
            require_current_user(request)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")
        return {
            "status": "ok",
            "enabled": bool(REALTIME_KEY),
            "model": REALTIME_MODEL if REALTIME_KEY else None,
        }

    @app.post("/api/realtime/call")
    async def realtime_call(request: Request):
        if not REALTIME_KEY:
            raise HTTPException(status_code=503, detail="Realtime voice is not configured")

        try:
            require_current_user(request)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")

        sdp_offer = (await request.body()).decode("utf-8", errors="replace").strip()
        if not sdp_offer or len(sdp_offer) > 200_000:
            raise HTTPException(status_code=400, detail="Invalid WebRTC offer")

        session = {
            "type": "realtime",
            "model": REALTIME_MODEL,
            "instructions": REALTIME_INSTRUCTIONS,
            "audio": {
                "output": {"voice": REALTIME_VOICE},
                "input": {
                    "noise_reduction": {"type": "near_field"},
                    "transcription": {
                        "model": REALTIME_TRANSCRIBE_MODEL,
                        "language": "en",
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": True,
                        "interrupt_response": True,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 450,
                        "threshold": 0.5,
                    },
                },
            },
        }

        try:
            # The SDP is the uploaded part; session is a normal multipart
            # form field containing JSON. Keeping it in `data` avoids some
            # gateways treating the session JSON as a second uploaded file.
            response = requests.post(
                REALTIME_URL,
                headers={"Authorization": f"Bearer {REALTIME_KEY}"},
                data={"session": json.dumps(session)},
                files={"sdp": ("offer.sdp", sdp_offer, "application/sdp")},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.warning("Realtime call request failed: %s", type(exc).__name__)
            raise HTTPException(status_code=502, detail="Realtime service unavailable")

        if response.status_code >= 400:
            # Log only structured provider diagnostics; never log credentials or
            # the SDP offer. This makes model/parameter errors actionable.
            try:
                provider_error = response.json().get("error", {})
                error_code = provider_error.get("code") or provider_error.get("type") or "unknown"
                error_message = str(provider_error.get("message") or "no provider message")[:240]
            except Exception:
                error_code = "unparseable_response"
                error_message = response.text[:240].replace("\\n", " ")
            logger.warning(
                "Realtime call rejected: status=%s code=%s message=%s",
                response.status_code,
                error_code,
                error_message,
            )
            if response.status_code in (401, 403):
                raise HTTPException(status_code=503, detail="Realtime voice credentials or account access need attention")
            raise HTTPException(status_code=502, detail="Realtime voice could not be started; provider rejected the session")

        answer = response.text.strip()
        if not answer:
            raise HTTPException(status_code=502, detail="Realtime service returned no SDP")
        return Response(content=answer, media_type="application/sdp")

    @app.post("/api/realtime/transcript")
    async def realtime_transcript(request: Request):
        if save_transcript is None:
            raise HTTPException(status_code=503, detail="Transcript storage unavailable")

        try:
            user_row = require_current_user(request)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Authentication required")

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid transcript payload")

        role = str(payload.get("role") or "").strip().lower()
        content = str(payload.get("content") or "").strip()
        conversation_id = str(payload.get("conversation_id") or "").strip() or None

        if role not in {"user", "assistant"}:
            raise HTTPException(status_code=400, detail="Invalid transcript role")
        if not content or len(content) > 8000:
            raise HTTPException(status_code=400, detail="Invalid transcript content")

        user_id = str(user_row.get("id") if isinstance(user_row, dict) else user_row[0])
        try:
            saved = save_transcript(user_id, conversation_id, role, content)
            return {
                "status": "success",
                "conversation_id": saved.get("conversation_id") if isinstance(saved, dict) else conversation_id,
                "message_id": saved.get("message_id") if isinstance(saved, dict) else None,
            }
        except Exception as exc:
            logger.warning("Realtime transcript save failed: %s", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Could not save transcript")
