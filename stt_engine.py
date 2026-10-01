"""
👑 KING ZARRY AI - Speech-to-Text Engine (Groq-only)
Flow: Voice message -> STT engine -> Groq API (GROQ_API_KEY) -> Whisper -> text -> AI system
This is Groq (G-R-O-Q), NOT xAI Grok.
No OpenAI dependency.
"""
import os
import re
import logging
import tempfile
from typing import Optional

logger = logging.getLogger("stt_engine")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
STT_API_KEY = clean_env_str(os.getenv("STT_API_KEY"))

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
    text = re.sub(r"sk-or-[A-Za-z0-9\-_]{10,}", "sk-or-***REDACTED***", text, flags=re.I)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    return text

def _get_api_key() -> Optional[str]:
    return STT_API_KEY or GROQ_API_KEY or None

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

def _transcribe_with_model(client, file_path: str, filename: str, model: str) -> Optional[str]:
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
        logger.info("VOICE STT success: model=%s chars=%s", model, len(text))
    else:
        logger.warning("VOICE STT empty response: model=%s response_type=%s", model, type(transcription).__name__)
    return text

def transcribe_file(file_path: str, filename: Optional[str] = None) -> Optional[str]:
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

    api_key = _get_api_key()
    if not api_key:
        logger.error("VOICE STT failed: No GROQ_API_KEY or STT_API_KEY configured")
        return None

    fname = os.path.basename(filename or os.path.basename(file_path) or "voice.ogg")
    if not os.path.splitext(fname)[1]:
        fname += ".ogg"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        # Fast path: Groq's Whisper Large V3 Turbo is designed for fast multilingual STT.
        try:
            text = _transcribe_with_model(
                client, file_path, fname, "whisper-large-v3-turbo"
            )
            if text:
                return text
        except Exception as e:
            logger.warning(
                "VOICE STT turbo attempt failed: %s",
                _redact(str(e))
            )

        # Accuracy fallback: retry the same audio with full Whisper Large V3.
        try:
            text = _transcribe_with_model(
                client, file_path, fname, "whisper-large-v3"
            )
            if text:
                return text
        except Exception as e:
            logger.error(
                "VOICE STT full Whisper fallback failed: %s",
                _redact(str(e))
            )

        logger.warning("VOICE STT exhausted all Groq transcription attempts")
        return None

    except Exception as e:
        logger.error("VOICE STT initialization/provider failure: %s", _redact(str(e)))
        return None

def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[str]:
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("VOICE STT failed: bytes empty/invalid")
        return None
    if len(audio_bytes) > 25 * 1024 * 1024:
        logger.warning("VOICE STT failed: bytes too large")
        return None

    logger.info("VOICE STT starting bytes: %s %s bytes", filename, len(audio_bytes))
    temp_path = None
    try:
        suffix = os.path.splitext(filename)[1] or ".ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name
        return transcribe_file(temp_path, filename=filename)
    except Exception as e:
        logger.error("VOICE STT transcribe_bytes error: %s", _redact(str(e)))
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def provider_status():
    has_groq = bool(GROQ_API_KEY or STT_API_KEY)
    return {
        "provider": "groq",
        "has_key": has_groq,
        "groq_key": bool(GROQ_API_KEY),
        "stt_key": bool(STT_API_KEY),
        "openai_key": False,
        "openrouter_used_for_stt": False,
        "models": ["whisper-large-v3-turbo", "whisper-large-v3"],
        "language": "en",
    }
