"""
👑 KING ZARRY AI - Speech-to-Text Engine
Flow: Voice message -> OpenRouter STT (Gemini/Whisper) -> direct Groq fallback -> text -> existing AI system.
OpenRouter is used first so a bad/expired Groq key does not break Telegram voice.
"""
import os
import re
import json
import base64
import logging
import tempfile
from typing import Optional

import requests

STT_ENGINE_BUILD = "OPENROUTER-FIRST-2026-10-01"
logger = logging.getLogger("stt_engine_openrouter")


def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default


GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
STT_API_KEY = clean_env_str(os.getenv("STT_API_KEY"))
OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))

OPENROUTER_STT_URL = "https://openrouter.ai/api/v1/audio/transcriptions"

# Ordered fallback chain for speech-to-text.
# Gemini is included first, then Whisper models, then the existing direct Groq path.
OPENROUTER_STT_MODELS = [
    "google/gemini-3.5-transcribe",
    "openai/whisper-large-v3-turbo",
    "openai/whisper-large-v3",
    "openai/whisper-1",
]


def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
    text = re.sub(r"sk-or-[A-Za-z0-9\-_]{10,}", "sk-or-***REDACTED***", text, flags=re.I)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    return text


def _extract_text(transcription) -> Optional[str]:
    if transcription is None:
        return None
    if isinstance(transcription, str):
        text = transcription
    else:
        text = getattr(transcription, "text", None)
        if text is None and isinstance(transcription, dict):
            text = transcription.get("text")
    text = str(text).strip() if text else ""
    return text or None


def _audio_format(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    return ext or "ogg"


def _transcribe_openrouter(
    file_path: str,
    filename: str,
    model: str,
) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return None

    with open(file_path, "rb") as audio_file:
        audio_b64 = base64.b64encode(audio_file.read()).decode("utf-8")

    payload = {
        "model": model,
        "input_audio": {
            "data": audio_b64,
            "format": _audio_format(filename),
        },
        "language": "en",
        "temperature": 0.0,
    }

    logger.info(
        "VOICE STT request: provider=openrouter model=%s file=%s size=%s language=en",
        model,
        filename,
        os.path.getsize(file_path),
    )

    response = requests.post(
        OPENROUTER_STT_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=55,
    )

    if response.status_code >= 400:
        body = _redact(response.text[:1000])
        raise RuntimeError(
            f"OpenRouter STT HTTP {response.status_code}: {body}"
        )

    try:
        result = response.json()
    except Exception as e:
        raise RuntimeError(
            f"OpenRouter STT returned invalid JSON: {_redact(str(e))}"
        ) from e

    text = _extract_text(result)
    if text:
        logger.info(
            "VOICE STT success: provider=openrouter model=%s chars=%s",
            model,
            len(text),
        )
        return text

    logger.warning(
        "VOICE STT empty response: provider=openrouter model=%s",
        model,
    )
    return None


def _transcribe_with_model(
    client,
    file_path: str,
    filename: str,
    model: str,
) -> Optional[str]:
    file_size = os.path.getsize(file_path)
    logger.info(
        "VOICE STT request: provider=groq model=%s file=%s size=%s language=en",
        model, filename, file_size
    )
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_file.read()),
            model=model,
            language="en",
            response_format="json",
            temperature=0.0,
        )
    text = _extract_text(transcription)
    if text:
        logger.info(
            "VOICE STT success: provider=groq model=%s chars=%s",
            model,
            len(text),
        )
    else:
        logger.warning(
            "VOICE STT empty response: provider=groq model=%s response_type=%s",
            model,
            type(transcription).__name__,
        )
    return text


def _transcribe_direct_groq(
    file_path: str,
    filename: str,
) -> Optional[str]:
    api_key = STT_API_KEY or GROQ_API_KEY
    if not api_key:
        return None

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        # Preserve the previous direct-Groq fallback behavior.
        for model in ("whisper-large-v3-turbo", "whisper-large-v3"):
            try:
                text = _transcribe_with_model(
                    client, file_path, filename, model
                )
                if text:
                    return text
            except Exception as e:
                logger.warning(
                    "VOICE STT direct Groq %s attempt failed: %s",
                    model,
                    _redact(str(e)),
                )

        logger.warning("VOICE STT exhausted all direct Groq attempts")
        return None

    except Exception as e:
        logger.error(
            "VOICE STT direct Groq initialization/provider failure: %s",
            _redact(str(e)),
        )
        return None


def transcribe_file(
    file_path: str,
    filename: Optional[str] = None,
) -> Optional[str]:
    if not os.path.exists(file_path):
        logger.warning("VOICE STT failed: file not found")
        return None

    file_size = os.path.getsize(file_path)
    logger.info("VOICE STT starting: size=%s bytes", file_size)

    if file_size > 25 * 1024 * 1024:
        logger.warning("VOICE STT failed: file too large %s", file_size)
        return None
    if file_size < 100:
        logger.warning("VOICE STT failed: file too small/invalid %s", file_size)
        return None

    fname = os.path.basename(
        filename or os.path.basename(file_path) or "voice.ogg"
    )
    if not os.path.splitext(fname)[1]:
        fname += ".ogg"

    # PRIMARY PATH:
    # OpenRouter's transcription endpoint handles provider routing/failover.
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_STT_MODELS:
            try:
                text = _transcribe_openrouter(file_path, fname, model)
                if text:
                    return text
            except Exception as e:
                logger.warning(
                    "VOICE STT OpenRouter model failed: model=%s error=%s",
                    model,
                    _redact(str(e)),
                )

        logger.warning(
            "VOICE STT exhausted all OpenRouter models; trying direct Groq fallback"
        )
    else:
        logger.warning(
            "VOICE STT OPENROUTER_API_KEY not configured; trying direct Groq fallback"
        )

    # SECONDARY PATH:
    # Keep the old direct Groq fallback so existing deployments still work.
    return _transcribe_direct_groq(file_path, fname)


def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
) -> Optional[str]:
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("VOICE STT failed: bytes empty/invalid")
        return None
    if len(audio_bytes) > 25 * 1024 * 1024:
        logger.warning("VOICE STT failed: bytes too large")
        return None

    logger.info(
        "VOICE STT starting bytes: %s %s bytes",
        filename,
        len(audio_bytes),
    )
    temp_path = None
    try:
        suffix = os.path.splitext(filename)[1] or ".ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name
        return transcribe_file(temp_path, filename=filename)
    except Exception as e:
        logger.error(
            "VOICE STT transcribe_bytes error: %s",
            _redact(str(e)),
        )
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def provider_status():
    has_groq = bool(GROQ_API_KEY or STT_API_KEY)
    has_openrouter = bool(OPENROUTER_API_KEY)
    return {
        "provider": "openrouter_then_groq",
        "build": STT_ENGINE_BUILD,
        "has_key": bool(has_openrouter or has_groq),
        "groq_key": bool(GROQ_API_KEY),
        "stt_key": bool(STT_API_KEY),
        "openrouter_key": has_openrouter,
        "openai_key": False,
        "openrouter_used_for_stt": has_openrouter,
        "models": OPENROUTER_STT_MODELS + [
            "whisper-large-v3-turbo",
            "whisper-large-v3",
        ],
        "language": "en",
    }
