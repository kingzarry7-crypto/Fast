"""Existing TTS implementation with optional environment-configured voice selection."""
from __future__ import annotations
import os
from typing import Any

TTS_VOICE_ID = os.getenv("TTS_VOICE_ID", "").strip() or None


def selected_voice_id(explicit_voice_id: str | None = None) -> str | None:
    """Return an explicit voice or configured voice without inventing provider IDs."""
    return (explicit_voice_id or TTS_VOICE_ID or None)


def safe_tts_call(generator: Any, text: str, voice_id: str | None = None) -> Any | None:
    """Call an existing generator defensively; callers can continue on provider failure."""
    try:
        selected = selected_voice_id(voice_id)
        if selected is None:
            return generator(text)
        try:
            return generator(text, voice_id=selected)
        except TypeError:
            return generator(text, selected)
    except Exception:
        return None
