"""
👑 KING ZARRY AI - Speech-to-Text Engine (Groq-only)
Flow: Voice message -> STT engine -> Groq API (GROQ_API_KEY) -> Whisper whisper-large-v3 -> text -> AI system
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

def transcribe_file(file_path: str, filename: Optional[str] = None) -> Optional[str]:
    if not os.path.exists(file_path):
        logger.warning("VOICE STT failed: file not found")
        return None
    file_size = os.path.getsize(file_path)
    logger.info(f"VOICE STT starting: size={file_size} bytes")
    if file_size > 15 * 1024 * 1024:
        logger.warning(f"VOICE STT failed: file too large {file_size}")
        return None
    if file_size < 100:
        logger.warning(f"VOICE STT failed: file too small/invalid {file_size}")
        return None
    api_key = _get_api_key()
    if not api_key:
        logger.error("VOICE STT failed: No GROQ_API_KEY configured")
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        fname = filename or os.path.basename(file_path)
        logger.info(f"VOICE STT provider: groq sending {fname} {file_size} bytes")
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="text",
            )
        text = transcription if isinstance(transcription, str) else getattr(transcription, 'text', str(transcription))
        text = text.strip() if text else None
        if text:
            logger.info(f"VOICE STT success: {len(text)} chars")
            return text
        else:
            logger.warning("VOICE STT returned empty")
            return None
    except Exception as e:
        logger.error(f"VOICE STT failed: {_redact(str(e))}")
        return None

def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[str]:
    if not audio_bytes or len(audio_bytes) < 100:
        logger.warning("VOICE STT failed: bytes empty/invalid")
        return None
    if len(audio_bytes) > 15 * 1024 * 1024:
        logger.warning("VOICE STT failed: bytes too large")
        return None
    logger.info(f"VOICE STT starting bytes: {filename} {len(audio_bytes)} bytes")
    temp_path = None
    try:
        suffix = os.path.splitext(filename)[1] or ".ogg"
        if not suffix:
            suffix = ".ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name
        return transcribe_file(temp_path, filename=filename)
    except Exception as e:
        logger.error(f"VOICE STT transcribe_bytes error: {_redact(str(e))}")
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
    }
