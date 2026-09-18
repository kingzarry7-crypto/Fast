"""
👑 KING ZARRY AI - Speech-to-Text Engine
Shared by Telegram and Discord
Provider abstraction:
    Groq Whisper (primary) -> OpenAI Whisper fallback
IMPORTANT:
    STT is completely isolated from the main AI provider chain.
Main AI chain remains:
    OPENROUTER → GROQ → GEMINI
STT chain:
    GROQ WHISPER → OPENAI WHISPER
OPENROUTER_API_KEY is NEVER used for STT.
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
    v = re.sub(
        r"[\u200b\u200c\u200d\u2060\ufeff]",
        "",
        str(v),
    ).strip()
    return v if v else default
# ============================================================
# ENVIRONMENT
# ============================================================
STT_API_KEY = clean_env_str(os.getenv("STT_API_KEY"))
STT_PROVIDER = clean_env_str(
    os.getenv("STT_PROVIDER"),
    "groq",
).lower()
# Dedicated STT/API keys only.
GROQ_API_KEY = clean_env_str(
    os.getenv("GROQ_API_KEY")
)
OPENAI_API_KEY = clean_env_str(
    os.getenv("OPENAI_API_KEY")
)
# IMPORTANT:
# OPENROUTER_API_KEY is intentionally NOT used here.
# STT must never send an OpenRouter key to the OpenAI SDK.
# ============================================================
# PROVIDER SELECTION
# ============================================================
def _get_provider():
    """
    Select the STT provider.
    Priority:
        1. Explicit STT_PROVIDER when the required key exists.
        2. Groq when available.
        3. OpenAI when available.
        4. Default to Groq so missing configuration fails clearly.
    OPENROUTER is never considered an STT provider.
    """
    # Explicit Groq selection
    if STT_PROVIDER == "groq":
        if GROQ_API_KEY or STT_API_KEY:
            return "groq"
    # Explicit OpenAI selection
    if STT_PROVIDER == "openai":
        if OPENAI_API_KEY or STT_API_KEY:
            return "openai"
    # Automatic fallback/selection
    if GROQ_API_KEY:
        return "groq"
    if OPENAI_API_KEY:
        return "openai"
    # Keep Groq as the default so errors remain clear.
    return "groq"
def _get_api_key(provider: str) -> str:
    """
    Return the correct API key for the selected STT provider.
    STT_API_KEY is treated as a generic dedicated STT key.
    Otherwise use the provider-specific key.
    NEVER use OPENROUTER_API_KEY here.
    """
    if STT_API_KEY:
        return STT_API_KEY
    if provider == "groq":
        return GROQ_API_KEY
    if provider == "openai":
        return OPENAI_API_KEY
    return ""
# ============================================================
# SECRET REDACTION
# ============================================================
def _redact(text: str) -> str:
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
        flags=re.I,
    )
    return text
# ============================================================
# GROQ TRANSCRIPTION
# ============================================================
def _transcribe_groq(
    file_path: str,
    filename: Optional[str],
    api_key: str,
) -> Optional[str]:
    from groq import Groq
    client = Groq(api_key=api_key)
    fname = filename or os.path.basename(file_path)
    with open(file_path, "rb") as audio_file:
        file_bytes = audio_file.read()
    logger.info(
        f"STT sending to Groq: {fname} {len(file_bytes)} bytes"
    )
    # Groq Whisper supports Telegram's OGG/Opus format.
    transcription = client.audio.transcriptions.create(
        file=(fname, file_bytes),
        model="whisper-large-v3",
        response_format="text",
    )
    if isinstance(transcription, str):
        text = transcription
    else:
        text = getattr(
            transcription,
            "text",
            str(transcription),
        )
    text = text.strip() if text else None
    if text:
        logger.info(
            f"STT Groq success: {len(text)} chars"
        )
        return text
    logger.warning(
        f"STT Groq returned empty transcription for {fname}"
    )
    return None
# ============================================================
# OPENAI TRANSCRIPTION
# ============================================================
def _transcribe_openai(
    file_path: str,
    filename: Optional[str],
    api_key: str,
) -> Optional[str]:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    fname = filename or os.path.basename(file_path)
    logger.info(
        f"STT sending to OpenAI: {fname}"
    )
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text",
        )
    if isinstance(transcription, str):
        text = transcription
    else:
        text = getattr(
            transcription,
            "text",
            str(transcription),
        )
    text = text.strip() if text else None
    if text:
        logger.info(
            f"STT OpenAI success: {len(text)} chars"
        )
        return text
    logger.warning(
        f"STT OpenAI returned empty for {fname}"
    )
    return None
# ============================================================
# MAIN FILE TRANSCRIPTION
# ============================================================
def transcribe_file(
    file_path: str,
    filename: Optional[str] = None,
) -> Optional[str]:
    """
    Synchronous transcription.
    Call from async code using:
        await asyncio.to_thread(
            transcribe_file,
            file_path,
            filename
        )
    Supported audio formats include:
        ogg, opus, mp3, m4a, wav, webm, mp4
    Returns:
        Transcription text or None.
    """
    if not file_path:
        logger.warning("STT file path is empty")
        return None
    if not os.path.exists(file_path):
        logger.warning(
            f"STT file not found: {file_path}"
        )
        return None
    try:
        file_size = os.path.getsize(file_path)
    except Exception as e:
        logger.warning(
            f"STT could not read file size: {_redact(str(e))}"
        )
        return None
    fname = filename or os.path.basename(file_path)
    logger.info(
        f"STT processing file: {fname} "
        f"size={file_size} bytes"
    )
    # 15 MB maximum
    if file_size > 15 * 1024 * 1024:
        logger.warning(
            f"STT file too large: {file_size} bytes"
        )
        return None
    # Reject obviously invalid/empty files
    if file_size < 100:
        logger.warning(
            f"STT file too small/invalid: {file_size} bytes"
        )
        return None
    provider = _get_provider()
    api_key = _get_api_key(provider)
    if not api_key:
        logger.error(
            "STT: No API key configured for "
            f"provider={provider}. "
            "Set GROQ_API_KEY, OPENAI_API_KEY, "
            "or dedicated STT_API_KEY."
        )
        return None
    # ========================================================
    # PRIMARY PROVIDER
    # ========================================================
    try:
        if provider == "groq":
            text = _transcribe_groq(
                file_path,
                filename,
                api_key,
            )
        elif provider == "openai":
            text = _transcribe_openai(
                file_path,
                filename,
                api_key,
            )
        else:
            logger.error(
                f"STT unsupported provider: {provider}"
            )
            return None
        if text:
            return text
        logger.warning(
            f"STT {provider} returned no transcription"
        )
    except Exception as e:
        logger.error(
            f"STT {provider} failed: {_redact(str(e))}"
        )
    # ========================================================
    # OPENAI FALLBACK
    # ========================================================
    # Only Groq -> OpenAI fallback.
    #
    # IMPORTANT:
    # This uses ONLY OPENAI_API_KEY.
    # OPENROUTER_API_KEY can NEVER reach this code.
    if provider == "groq" and OPENAI_API_KEY:
        try:
            logger.info(
                "STT trying OpenAI Whisper fallback"
            )
            text = _transcribe_openai(
                file_path,
                filename,
                OPENAI_API_KEY,
            )
            if text:
                return text
            logger.warning(
                "STT OpenAI fallback returned empty transcription"
            )
        except Exception as e:
            logger.error(
                f"STT OpenAI fallback failed: "
                f"{_redact(str(e))}"
            )
    return None
# ============================================================
# BYTES TRANSCRIPTION
# ============================================================
def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.ogg",
) -> Optional[str]:
    """
    Transcribe in-memory audio bytes safely.
    Used by Telegram/Discord handlers when they download
    an audio file into memory.
    Temporary files are always removed.
    """
    if not audio_bytes:
        logger.warning(
            "STT received empty audio bytes"
        )
        return None
    if len(audio_bytes) < 100:
        logger.warning(
            f"STT audio too small: {len(audio_bytes)} bytes"
        )
        return None
    if len(audio_bytes) > 15 * 1024 * 1024:
        logger.warning(
            f"STT bytes too large: {len(audio_bytes)}"
        )
        return None
    temp_path = None
    try:
        # Preserve the incoming extension when possible.
        suffix = os.path.splitext(
            filename or ""
        )[1]
        if not suffix:
            suffix = ".ogg"
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as tf:
            tf.write(audio_bytes)
            temp_path = tf.name
        logger.info(
            f"STT temporary audio created: "
            f"{os.path.basename(temp_path)}"
        )
        return transcribe_file(
            temp_path,
            filename=filename,
        )
    except Exception as e:
        logger.error(
            f"STT transcribe_bytes error: "
            f"{_redact(str(e))}"
        )
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.debug(
                    f"STT temp cleanup failed: "
                    f"{_redact(str(e))}"
                )
# ============================================================
# HEALTH STATUS
# ============================================================
def provider_status():
    """
    Return safe STT configuration status.
    Does not expose API keys.
    """
    provider = _get_provider()
    return {
        "provider": provider,
        "has_key": bool(
            STT_API_KEY
            or GROQ_API_KEY
            or OPENAI_API_KEY
        ),
        "groq_key": bool(GROQ_API_KEY),
        "stt_key": bool(STT_API_KEY),
        "openai_key": bool(OPENAI_API_KEY),
        "openrouter_used_for_stt": False,
    }
# ============================================================
# AVAILABILITY HELPER
# ============================================================
def is_available() -> bool:
    """
    Return True when at least one legitimate STT
    provider key is configured.
    """
    return bool(
        STT_API_KEY
        or GROQ_API_KEY
        or OPENAI_API_KEY
    )
