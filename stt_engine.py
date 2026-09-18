"""
👑 KING ZARRY AI - Speech-to-Text Engine
Shared by Telegram and Discord
Provider abstraction: Groq Whisper (primary) -> OpenAI Whisper fallback
Keeps main AI chain OPENROUTER → GROQ → GEMINI untouched - STT is isolated
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

STT_API_KEY = clean_env_str(os.getenv("STT_API_KEY"))
STT_PROVIDER = clean_env_str(os.getenv("STT_PROVIDER"), "groq").lower()  # groq | openai
GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
OPENAI_API_KEY = clean_env_str(os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))

# Prefer Groq if available, as project already uses Groq
def _get_provider():
    # Explicit env overrides
    if STT_PROVIDER in ["groq", "openai"]:
        if STT_PROVIDER == "groq" and (GROQ_API_KEY or STT_API_KEY):
            return "groq"
        if STT_PROVIDER == "openai" and (OPENAI_API_KEY or STT_API_KEY):
            return "openai"
    # Auto-detect
    if GROQ_API_KEY or (STT_API_KEY and STT_PROVIDER == "groq"):
        return "groq"
    if OPENAI_API_KEY:
        return "openai"
    # Fallback to groq if any key exists
    if GROQ_API_KEY:
        return "groq"
    return "groq"  # default, will error clearly if no key

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    return text

def transcribe_file(file_path: str, filename: Optional[str] = None) -> Optional[str]:
    """
    Synchronous transcription - call via asyncio.to_thread()
    file_path: path to audio file (ogg, mp3, m4a, wav, etc)
    Returns transcription text or None
    """
    if not os.path.exists(file_path):
        logger.warning(f"STT file not found: {file_path}")
        return None
    
    file_size = os.path.getsize(file_path)
    logger.info(f"STT processing file: {filename or os.path.basename(file_path)} size={file_size} bytes")
    if file_size > 15 * 1024 * 1024:
        logger.warning(f"STT file too large: {file_size} bytes")
        return None
    if file_size < 100:
        logger.warning(f"STT file too small/invalid: {file_size} bytes")
        return None

    provider = _get_provider()
    api_key = STT_API_KEY or (GROQ_API_KEY if provider == "groq" else OPENAI_API_KEY)

    if not api_key:
        logger.error("STT: No API key found. Set GROQ_API_KEY or STT_API_KEY or OPENAI_API_KEY")
        return None

    try:
        if provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            # Groq Whisper supports: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
            # Telegram voice is OGG/Opus - Groq supports ogg directly, no conversion needed
            # Fix: pass file object directly with correct tuple format, remove forced language for auto-detect
            fname = filename or os.path.basename(file_path)
            with open(file_path, "rb") as audio_file:
                file_bytes = audio_file.read()
            logger.info(f"STT sending to Groq: {fname} {len(file_bytes)} bytes")
            # Groq SDK expects file as (filename, bytes) tuple - include content-type hint if possible
            transcription = client.audio.transcriptions.create(
                file=(fname, file_bytes),
                model="whisper-large-v3",
                response_format="text",
                # language removed for auto-detect - Telegram voices may be multilingual
            )
            # transcription may be str or object
            text = transcription if isinstance(transcription, str) else getattr(transcription, 'text', str(transcription))
            text = text.strip() if text else None
            if text:
                logger.info(f"STT Groq success: {len(text)} chars")
                return text
            else:
                logger.warning(f"STT Groq returned empty transcription for {fname}")
                return None
        else:  # openai
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            with open(file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            text = transcription if isinstance(transcription, str) else getattr(transcription, 'text', str(transcription))
            text = text.strip() if text else None
            if text:
                logger.info(f"STT OpenAI success: {len(text)} chars")
                return text
            logger.warning(f"STT OpenAI returned empty for {filename}")
            return None
    except Exception as e:
        err_msg = _redact(str(e))
        logger.error(f"STT {provider} failed: {err_msg}")
        # Try fallback to other provider if first fails
        try:
            if provider == "groq" and OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
                logger.info("STT trying OpenAI fallback")
                from openai import OpenAI
                client = OpenAI(api_key=OPENAI_API_KEY)
                with open(file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                text = transcription if isinstance(transcription, str) else getattr(transcription, 'text', str(transcription))
                return text.strip() if text else None
        except Exception as fallback_e:
            logger.error(f"STT fallback failed: {_redact(str(fallback_e))}")
        return None

def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.ogg") -> Optional[str]:
    """Helper for in-memory bytes - writes temp file safely"""
    if not audio_bytes or len(audio_bytes) < 100:
        return None
    if len(audio_bytes) > 15 * 1024 * 1024:
        logger.warning(f"STT bytes too large: {len(audio_bytes)}")
        return None
    temp_path = None
    try:
        suffix = os.path.splitext(filename)[1] or ".ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name
        return transcribe_file(temp_path, filename=filename)
    except Exception as e:
        logger.error(f"STT transcribe_bytes error: {_redact(str(e))}")
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

# For health checks
def provider_status():
    provider = _get_provider()
    has_key = bool(STT_API_KEY or GROQ_API_KEY or OPENAI_API_KEY)
    return {"provider": provider, "has_key": has_key, "groq_key": bool(GROQ_API_KEY), "stt_key": bool(STT_API_KEY), "openai_key": bool(OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"))}
