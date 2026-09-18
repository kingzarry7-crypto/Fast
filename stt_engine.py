"""
👑 KING ZARRY AI - Speech-to-Text Engine

Shared by Telegram and Discord.

STT provider:
    Groq Whisper

Important:
    This module is completely separate from the main AI chain.

Main AI chain remains:
    OpenRouter → Groq → Gemini

Environment:
    GROQ_API_KEY

Optional:
    STT_API_KEY
    STT_PROVIDER=groq

No OpenAI/OpenRouter key is used for STT.
"""

import os
import re
import logging
import tempfile
from typing import Optional


logger = logging.getLogger("stt_engine")


# ============================================================
# ENVIRONMENT HELPERS
# ============================================================

def clean_env_str(value, default: str = "") -> str:
    """Clean environment-variable strings safely."""
    if not value:
        return default

    value = re.sub(
        r"[\u200b\u200c\u200d\u2060\ufeff]",
        "",
        str(value),
    ).strip()

    return value if value else default


GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))

# Optional dedicated STT key.
# If not provided, the existing GROQ_API_KEY is used.
STT_API_KEY = clean_env_str(os.getenv("STT_API_KEY"))

# STT is intentionally Groq-only.
STT_PROVIDER = clean_env_str(
    os.getenv("STT_PROVIDER"),
    "groq",
).lower()


# ============================================================
# LIMITS
# ============================================================

MAX_AUDIO_SIZE = 15 * 1024 * 1024  # 15 MB
MIN_AUDIO_SIZE = 100


# ============================================================
# SECURITY
# ============================================================

def _redact(text: str) -> str:
    """Remove common API-key patterns from log messages."""
    if not text:
        return ""

    text = re.sub(
        r"sk-[A-Za-z0-9_-]{10,}",
        "sk-***REDACTED***",
        text,
    )

    text = re.sub(
        r"gsk_[A-Za-z0-9_-]{10,}",
        "gsk_***REDACTED***",
        text,
    )

    text = re.sub(
        r"xai-[A-Za-z0-9_-]{10,}",
        "xai-***REDACTED***",
        text,
    )

    text = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-.]+",
        r"\1***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )

    return text


# ============================================================
# PROVIDER
# ============================================================

def _get_provider() -> str:
    """
    Return the configured STT provider.

    KING ZARRY AI currently uses Groq Whisper for STT.
    """

    # Keep the provider name configurable for future expansion,
    # but only Groq is currently supported by this module.
    if STT_PROVIDER != "groq":
        logger.warning(
            "Unsupported STT_PROVIDER=%s. Using Groq Whisper.",
            _redact(STT_PROVIDER),
        )

    return "groq"


def _get_api_key() -> Optional[str]:
    """
    Get the STT API key.

    Priority:
        1. STT_API_KEY
        2. GROQ_API_KEY
    """

    return STT_API_KEY or GROQ_API_KEY or None


# ============================================================
# TRANSCRIPTION
# ============================================================

def transcribe_file(
    file_path: str,
    filename: Optional[str] = None,
) -> Optional[str]:
    """
    Transcribe an audio file using Groq Whisper.

    This function is synchronous and should be called through:

        await asyncio.to_thread(transcribe_file, ...)

    Supported formats include common audio formats such as:

        ogg
        mp3
        mp4
        m4a
        wav
        webm
        flac

    Returns:
        Transcribed text, or None if transcription fails.
    """

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file_path:
        logger.warning("STT file path is empty.")
        return None

    if not os.path.isfile(file_path):
        logger.warning("STT file not found.")
        return None

    try:
        file_size = os.path.getsize(file_path)
    except OSError as exc:
        logger.error(
            "STT could not read file size: %s",
            _redact(str(exc)),
        )
        return None

    if file_size < MIN_AUDIO_SIZE:
        logger.warning(
            "STT audio file is too small: %s bytes",
            file_size,
        )
        return None

    if file_size > MAX_AUDIO_SIZE:
        logger.warning(
            "STT audio file is too large: %s bytes",
            file_size,
        )
        return None

    # --------------------------------------------------------
    # API key
    # --------------------------------------------------------

    api_key = _get_api_key()

    if not api_key:
        logger.error(
            "STT unavailable: GROQ_API_KEY or STT_API_KEY is not configured."
        )
        return None

    provider = _get_provider()

    if provider != "groq":
        logger.error("STT provider is unavailable.")
        return None

    # --------------------------------------------------------
    # Groq Whisper
    # --------------------------------------------------------

    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        safe_filename = (
            os.path.basename(filename)
            if filename
            else os.path.basename(file_path)
        )

        if not safe_filename:
            safe_filename = "audio.ogg"

        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(
                    safe_filename,
                    audio_file.read(),
                ),
                model="whisper-large-v3",
                response_format="text",
                # No language parameter.
                # Whisper automatically detects the language.
            )

        # Groq may return a string or an object containing .text.
        if isinstance(transcription, str):
            text = transcription
        else:
            text = getattr(
                transcription,
                "text",
                None,
            )

        if not text:
            logger.warning("STT returned empty transcription.")
            return None

        text = str(text).strip()

        if not text:
            logger.warning("STT returned blank transcription.")
            return None

        logger.info(
            "STT Groq success: %s characters",
            len(text),
        )

        return text

    except ImportError:
        logger.error(
            "Groq package is not installed. Add 'groq' to requirements.txt."
        )
        return None

    except Exception as exc:
        logger.error(
            "STT Groq transcription failed: %s",
            _redact(str(exc)),
        )
        return None


# ============================================================
# BYTES → TRANSCRIPTION
# ============================================================

def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
) -> Optional[str]:
    """
    Transcribe in-memory audio bytes safely.

    A temporary file is created, sent to Groq Whisper,
    then deleted automatically.
    """

    if not audio_bytes:
        return None

    if len(audio_bytes) < MIN_AUDIO_SIZE:
        logger.warning("STT audio bytes are too small.")
        return None

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        logger.warning(
            "STT audio bytes are too large: %s bytes",
            len(audio_bytes),
        )
        return None

    temp_path = None

    try:
        # Prevent strange filenames from becoming part of the temp path.
        safe_filename = os.path.basename(filename or "audio.ogg")

        extension = os.path.splitext(safe_filename)[1].lower()

        if not extension:
            extension = ".ogg"

        # Keep the extension limited to a reasonable value.
        if len(extension) > 10:
            extension = ".ogg"

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=extension,
        ) as temp_file:

            temp_file.write(audio_bytes)
            temp_file.flush()

            temp_path = temp_file.name

        return transcribe_file(
            temp_path,
            filename=safe_filename,
        )

    except Exception as exc:
        logger.error(
            "STT transcribe_bytes failed: %s",
            _redact(str(exc)),
        )
        return None

    finally:
        if temp_path:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError as exc:
                logger.warning(
                    "STT temporary-file cleanup failed: %s",
                    _redact(str(exc)),
                )


# ============================================================
# HEALTH STATUS
# ============================================================

def provider_status() -> dict:
    """
    Return non-secret STT health information.

    Never returns the actual API key.
    """

    provider = _get_provider()
    has_key = bool(_get_api_key())

    return {
        "provider": provider,
        "has_key": has_key,
        "groq_key": bool(GROQ_API_KEY),
        "stt_key": bool(STT_API_KEY),
    }


# ============================================================
# MODULE HEALTH CHECK
# ============================================================

def is_available() -> bool:
    """
    Return True when a Groq/STT key is configured.
    """

    return bool(_get_api_key())
