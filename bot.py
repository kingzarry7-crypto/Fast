import os
import re
import io
import asyncio
import tempfile
import base64
import sqlite3
import logging
import html
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import requests
import discord
import fal_client

from discord import app_commands, File, Embed
from dotenv import load_dotenv

from memory import Memory
from ai_engine import AIEngine
from news_engine import news_engine
import market as market_engine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("king_zarry_discord")


def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default


def _redact(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"([?&]key=)[^&\s\"']+",
        r"\1***REDACTED***",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-\.]+",
        r"\1***REDACTED***",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"sk-[A-Za-z0-9]{10,}",
        "sk-***REDACTED***",
        text,
    )
    text = re.sub(
        r"gsk_[A-Za-z0-9]{10,}",
        "gsk_***REDACTED***",
        text,
    )
    text = re.sub(
        r"xai-[A-Za-z0-9]{10,}",
        "xai-***REDACTED***",
        text,
    )

    secrets_to_redact = [
        os.getenv("DISCORD_BOT_TOKEN"),
        os.getenv("ELEVENLABS_API_KEY"),
        os.getenv("GROQ_API_KEY"),
        os.getenv("FAL_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("GEMINI_API_KEY"),
        os.getenv("XAI_API_KEY"),
        os.getenv("GROK_API_KEY"),
        os.getenv("TWELVE_DATA_API_KEY"),
        os.getenv("FINNHUB_API_KEY"),
        os.getenv("EODHD_API_KEY"),
        os.getenv("TRADING_ECONOMICS_API_KEY"),
        os.getenv("CURRENTS_API_KEY"),
        os.getenv("NEWSDATA_API_KEY"),
        os.getenv("NEWSDATA_IO_API_KEY"),
        os.getenv("NEWS_API_KEY"),
    ]

    for secret in secrets_to_redact:
        if secret and len(secret) > 8:
            text = text.replace(
                secret,
                secret[:3] + "***REDACTED***"
            )

    return text


DISCORD_BOT_TOKEN = clean_env_str(os.getenv("DISCORD_BOT_TOKEN"))

DISCORD_GUILD_ID = int(
    clean_env_str(
        os.getenv("DISCORD_GUILD_ID"),
        "1537104053207568394"
    ) or "1537104053207568394"
)

DISCORD_ADMIN_ID = int(
    clean_env_str(
        os.getenv("DISCORD_ADMIN_ID"),
        "1404253218808139807"
    ) or "1404253218808139807"
)

DATABASE_PATH = clean_env_str(
    os.getenv("DATABASE_PATH"),
    "king_zarry_memory.db"
)

MEMORY_DB_PATH = clean_env_str(
    os.getenv("MEMORY_DB_PATH"),
    "king_zarry_memory.db"
)

ELEVENLABS_API_KEY = clean_env_str(
    os.getenv("ELEVENLABS_API_KEY")
)

ELEVENLABS_VOICE_ID = clean_env_str(
    os.getenv("ELEVENLABS_VOICE_ID"),
    "hpp4J3VqNfWAUOO0d1Us"
)

ELEVENLABS_MODEL_ID = clean_env_str(
    os.getenv("ELEVENLABS_MODEL_ID")
    or os.getenv("ELEVENLABS_MODEL"),
    "eleven_v3"
)

GROQ_API_KEY = clean_env_str(
    os.getenv("GROQ_API_KEY")
)

FAL_KEY = clean_env_str(
    os.getenv("FAL_KEY")
)

GROQ_VISION_MODEL = clean_env_str(
    os.getenv("GROQ_VISION_MODEL"),
    "qwen/qwen3.6-27b"
)

GROQ_TEXT_MODEL = clean_env_str(
    os.getenv("GROQ_TEXT_MODEL"),
    "llama-3.3-70b-versatile"
)

TEXT_TO_VIDEO_MODEL = clean_env_str(
    os.getenv("TEXT_TO_VIDEO_MODEL"),
    "fal-ai/ltx-video"
)

IMAGE_TO_VIDEO_MODEL = clean_env_str(
    os.getenv("IMAGE_TO_VIDEO_MODEL"),
    "fal-ai/ltx-video/image-to-video"
)

MAX_PROMPT_LENGTH = 1500
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 24 * 1024 * 1024

ALLOWED_VIDEO_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

ALLOWED_BROADCAST_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "video/mp4",
}

PREMIUM_PLANS = {
    "monthly": {
        "days": 30,
        "price": "250 XTR"
    },
    "3month": {
        "days": 90,
        "price": "600 XTR"
    },
    "yearly": {
        "days": 365,
        "price": "2000 XTR"
    },
}

SYSTEM_VOICE_PROMPT = (
    "You are King Zarry AI, an advanced multi-platform assistant with "
    "text, vision, market analysis and creative capabilities. "
    "Keep responses concise, clear and direct. "
    "NEVER mention ElevenLabs, Discord, Telegram, or underlying tools, "
    "models or APIs. "
    "If the user asks if you can speak, talk, or send voice messages, "
    "respond naturally with: "
    "'Yes, I can talk to you! What would you like me to say?'"
)


print("\n" + "=" * 60)
print("👑 KING ZARRY AI DISCORD - UPGRADED MTF + NEWS EDITION")
print("=" * 60)
print(
    f"🔑 Discord token: "
    f"{'FOUND' if DISCORD_BOT_TOKEN else 'MISSING'}"
)
print("👑 Admin ID: configured")
print("🏠 Guild ID: configured")
print(
    f"🎙️ ElevenLabs configuration: "
    f"{'CONFIGURED' if ELEVENLABS_API_KEY else 'MISSING'} "
    f"| Model: {_redact(ELEVENLABS_MODEL_ID)}"
)
print(
    f"🧠 Groq: "
    f"{'FOUND' if GROQ_API_KEY else 'MISSING'}"
)
print(
    f"🎬 Fal.ai: "
    f"{'FOUND' if FAL_KEY else 'MISSING'}"
)
print(f"💾 DB: {DATABASE_PATH}")
print("=" * 60 + "\n")


if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN missing")


try:
    from elevenlabs.client import ElevenLabs

    eleven_client = (
        ElevenLabs(api_key=ELEVENLABS_API_KEY)
        if ELEVENLABS_API_KEY
        else None
    )
except Exception as e:
    logger.warning(
        f"ElevenLabs init failed: {_redact(str(e))}"
    )
    eleven_client = None


try:
    from groq import Groq

    groq_client = (
        Groq(api_key=GROQ_API_KEY)
        if GROQ_API_KEY
        else None
    )
except Exception:
    groq_client = None


memory = Memory(MEMORY_DB_PATH)
ai = AIEngine(memory)


def db_connect():
    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )
    conn.row_factory = sqlite3.Row
    return conn


def init_subscription_db():
    conn = db_connect()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_subscriptions (
            user_id TEXT PRIMARY KEY,
            plan TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            granted_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS discord_bans (
            user_id TEXT PRIMARY KEY,
            reason TEXT,
            banned_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().isoformat()


def remember_user_sync(user_id: int, username: str):
    now = iso_now()

    conn = db_connect()

    row = conn.execute(
        "SELECT user_id FROM discord_users WHERE user_id = ?",
        (str(user_id),)
    ).fetchone()

    if row:
        conn.execute(
            """
            UPDATE discord_users
            SET username = ?, last_seen = ?
            WHERE user_id = ?
            """,
            (
                username,
                now,
                str(user_id)
            )
        )
    else:
        conn.execute(
            """
            INSERT INTO discord_users
            (user_id, username, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(user_id),
                username,
                now,
                now
            )
        )

    conn.commit()
    conn.close()


def get_subscription_sync(user_id: int):
    conn = db_connect()

    row = conn.execute(
        """
        SELECT
            user_id,
            plan,
            expires_at,
            granted_by,
            created_at
        FROM discord_subscriptions
        WHERE user_id = ?
        """,
        (str(user_id),)
    ).fetchone()

    conn.close()

    if not row:
        return None

    try:
        expires = datetime.fromisoformat(
            row["expires_at"]
        )
    except Exception:
        return None

    if expires <= utc_now():
        conn = db_connect()

        conn.execute(
            """
            DELETE FROM discord_subscriptions
            WHERE user_id = ?
            """,
            (str(user_id),)
        )

        conn.commit()
        conn.close()

        return None

    return dict(row)


def grant_subscription_sync(
    user_id: int,
    plan: str,
    granted_by: int
):
    plan = plan.lower()

    if plan not in PREMIUM_PLANS:
        raise ValueError(
            "Unknown plan. Choose: "
            + ", ".join(PREMIUM_PLANS)
        )

    current = get_subscription_sync(user_id)
    now = utc_now()

    if current:
        try:
            current_expiry = datetime.fromisoformat(
                current["expires_at"]
            )
            start = max(now, current_expiry)
        except Exception:
            start = now
    else:
        start = now

    expires = (
        start
        + timedelta(
            days=PREMIUM_PLANS[plan]["days"]
        )
    )

    conn = db_connect()

    conn.execute(
        """
        INSERT INTO discord_subscriptions
        (
            user_id,
            plan,
            expires_at,
            granted_by,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            plan=excluded.plan,
            expires_at=excluded.expires_at,
            granted_by=excluded.granted_by,
            created_at=excluded.created_at
        """,
        (
            str(user_id),
            plan,
            expires.isoformat(),
            str(granted_by),
            now.isoformat()
        )
    )

    conn.commit()
    conn.close()

    return expires


def revoke_subscription_sync(user_id: int):
    conn = db_connect()

    cur = conn.execute(
        """
        DELETE FROM discord_subscriptions
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    conn.commit()

    deleted = cur.rowcount > 0

    conn.close()

    return deleted


def is_banned_sync(user_id: int):
    conn = db_connect()

    row = conn.execute(
        """
        SELECT user_id
        FROM discord_bans
        WHERE user_id = ?
        """,
        (str(user_id),)
    ).fetchone()

    conn.close()

    return row is not None


def ban_user_sync(
    user_id: int,
    reason: str,
    banned_by: int
):
    conn = db_connect()

    conn.execute(
        """
        INSERT INTO discord_bans
        (
            user_id,
            reason,
            banned_by,
            created_at
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            reason=excluded.reason,
            banned_by=excluded.banned_by,
            created_at=excluded.created_at
        """,
        (
            str(user_id),
            reason,
            str(banned_by),
            iso_now()
        )
    )

    conn.commit()
    conn.close()


def unban_user_sync(user_id: int):
    conn = db_connect()

    cur = conn.execute(
        """
        DELETE FROM discord_bans
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    conn.commit()

    removed = cur.rowcount > 0

    conn.close()

    return removed


def get_user_count_sync():
    conn = db_connect()

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM discord_users
        """
    ).fetchone()

    conn.close()

    return int(row["count"])


def get_premium_count_sync():
    conn = db_connect()

    rows = conn.execute(
        """
        SELECT user_id, expires_at
        FROM discord_subscriptions
        """
    ).fetchall()

    conn.close()

    now = utc_now()
    count = 0

    for row in rows:
        try:
            if datetime.fromisoformat(
                row["expires_at"]
            ) > now:
                count += 1
        except Exception:
            pass

    return count


def get_banned_count_sync():
    conn = db_connect()

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM discord_bans
        """
    ).fetchone()

    conn.close()

    return int(row["count"])


def get_all_user_ids_sync():
    conn = db_connect()

    rows = conn.execute(
        """
        SELECT user_id
        FROM discord_users
        """
    ).fetchall()

    conn.close()

    return [
        int(row["user_id"])
        for row in rows
    ]


init_subscription_db()


def is_admin(user: discord.abc.User) -> bool:
    return user.id == DISCORD_ADMIN_ID


async def require_admin(
    interaction: discord.Interaction
) -> bool:

    if not is_admin(interaction.user):
        msg = "⛔ **Admin only.**"

        if interaction.response.is_done():
            await interaction.followup.send(
                msg,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                msg,
                ephemeral=True
            )

        return False

    return True


async def user_is_banned(user_id: int) -> bool:
    return await asyncio.to_thread(
        is_banned_sync,
        user_id
    )


async def ensure_not_banned(
    interaction: discord.Interaction
) -> bool:

    if await user_is_banned(
        interaction.user.id
    ):
        msg = "⛔ You are banned from King Zarry AI."

        if interaction.response.is_done():
            await interaction.followup.send(
                msg,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                msg,
                ephemeral=True
            )

        return False

    return True


async def ensure_not_banned_message(
    message: discord.Message
) -> bool:
    return not await user_is_banned(
        message.author.id
    )


async def track_user(
    user: discord.abc.User
):
    await asyncio.to_thread(
        remember_user_sync,
        user.id,
        str(user)
    )


async def is_premium(user_id: int) -> bool:
    return (
        await asyncio.to_thread(
            get_subscription_sync,
            user_id
        )
    ) is not None


# ============================================================
# CENTRALIZED TTS
# ElevenLabs primary + AriaNeural fallback
# ============================================================

def generate_elevenlabs_voice(
    text: str
) -> io.BytesIO:

    if not eleven_client:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not configured."
        )

    try:
        logger.info(
            "TTS provider: ElevenLabs | "
            f"TTS model: {_redact(ELEVENLABS_MODEL_ID)}"
        )

        audio_generator = (
            eleven_client
            .text_to_speech
            .convert(
                text=text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id=ELEVENLABS_MODEL_ID,
                output_format="mp3_44100_128",
            )
        )

        audio_bytes = b"".join(
            chunk
            for chunk in audio_generator
        )

        if not audio_bytes:
            raise RuntimeError(
                "ElevenLabs returned empty audio."
            )

    except Exception as e:
        raise RuntimeError(
            "ElevenLabs generation failed: "
            + _redact(str(e))
        )

    audio_io = io.BytesIO(audio_bytes)
    audio_io.seek(0)

    return audio_io


async def generate_edgetts_voice(
    text: str
) -> io.BytesIO:

    temp_dir = None

    try:
        import edge_tts

        temp_dir = tempfile.mkdtemp(
            prefix="king_zarry_tts_"
        )

        output_file = os.path.join(
            temp_dir,
            "voice.mp3"
        )

        communicate = edge_tts.Communicate(
            text,
            "en-US-AriaNeural"
        )

        await communicate.save(output_file)

        with open(output_file, "rb") as f:
            audio_bytes = f.read()

        if not audio_bytes:
            raise RuntimeError(
                "AriaNeural returned empty audio."
            )

        audio_io = io.BytesIO(audio_bytes)
        audio_io.seek(0)

        return audio_io

    finally:
        if temp_dir:
            try:
                import shutil

                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )
            except Exception:
                pass


async def generate_tts_audio(
    text: str
) -> tuple[io.BytesIO, str]:

    """
    Centralized TTS:

    1. ElevenLabs
    2. AriaNeural fallback

    Used by:
    - /tts
    - /voice
    - normal message voice requests
    - /say
    """

    if not text or not text.strip():
        raise RuntimeError(
            "Cannot generate voice from empty text."
        )

    try:
        if (
            eleven_client
            and ELEVENLABS_API_KEY
        ):
            audio = await asyncio.to_thread(
                generate_elevenlabs_voice,
                text
            )

            return audio, "ElevenLabs"

    except Exception as e:
        logger.warning(
            "ElevenLabs TTS failed, "
            "trying AriaNeural fallback: "
            + _redact(str(e))
        )

    try:
        audio = await generate_edgetts_voice(
            text
        )

        return audio, "AriaNeural"

    except Exception as e:
        logger.error(
            "AriaNeural fallback failed: "
            + _redact(str(e))
        )

        raise RuntimeError(
            "TTS unavailable: "
            + _redact(str(e))
        )


async def play_voice_in_channel(
    voice_client: discord.VoiceClient,
    text: str
):

    audio_stream = None

    try:
        audio_stream, provider = (
            await generate_tts_audio(text)
        )

        audio_source = discord.FFmpegPCMAudio(
            audio_stream,
            pipe=True
        )

        if voice_client.is_playing():
            voice_client.stop()

        def after_playback(error):
            if error:
                logger.error(
                    "Voice playback finished with error: "
                    + _redact(str(error))
                )
            else:
                logger.info(
                    f"Voice playback finished using {provider}."
                )

            try:
                audio_stream.close()
            except Exception:
                pass

        voice_client.play(
            audio_source,
            after=after_playback
        )

    except Exception as e:
        try:
            if audio_stream:
                audio_stream.close()
        except Exception:
            pass

        logger.error(
            "Voice playback failed: "
            + _redact(str(e))
        )

        raise


def detect_market_and_timeframe(
    text: str
):
    upper = text.upper()

    symbol = "BTC/USD"

    markets = {
        "XAU/USD": [
            "XAU/USD",
            "XAUUSD",
            "GOLD",
            "XAU"
        ],
        "BTC/USD": [
            "BTC/USD",
            "BTCUSDT",
            "BTC"
        ],
        "ETH/USD": [
            "ETH/USD",
            "ETHUSDT",
            "ETH"
        ],
        "SOL/USD": [
            "SOL/USD",
            "SOLUSDT",
            "SOL"
        ],
        "EUR/USD": [
            "EUR/USD",
            "EURUSD"
        ],
        "GBP/USD": [
            "GBP/USD",
            "GBPUSD"
        ],
    }

    for market_symbol, names in markets.items():
        if any(
            name in upper
            for name in names
        ):
            symbol = market_symbol
            break

    match = re.search(
        r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b",
        text.lower()
    )

    timeframe = (
        match.group(1)
        if match
        else "15m"
    )

    return symbol, timeframe


def safe_float(
    val,
    default=0.0
):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def build_discord_signal_embed(
    market_data: Dict[str, Any],
    news_data: Optional[
        Dict[str, Any]
    ] = None
) -> Embed:

    symbol = market_data.get(
        "symbol",
        "UNKNOWN"
    )

    signal = market_data.get(
        "signal",
        "WAIT"
    )

    mtf_bias = market_data.get(
        "mtf_bias",
        market_data.get(
            "trend",
            "NEUTRAL"
        )
    )

    mtf_score = market_data.get(
        "mtf_score",
        market_data.get(
            "strength",
            0
        )
    )

    confidence = market_data.get(
        "confidence",
        "LOW"
    )

    strength = market_data.get(
        "strength",
        0
    )

    price = safe_float(
        market_data.get(
            "price"
        )
        or market_data.get(
            "current_price"
        )
    )

    entry_low = safe_float(
        market_data.get(
            "entry_low"
        )
    )

    entry_high = safe_float(
        market_data.get(
            "entry_high"
        )
    )

    stop_loss = safe_float(
        market_data.get(
            "stop_loss"
        )
    )

    tp1 = safe_float(
        market_data.get("tp1")
    )

    tp2 = safe_float(
        market_data.get("tp2")
    )

    tp3 = safe_float(
        market_data.get("tp3")
    )

    support = safe_float(
        market_data.get("support")
    )

    resistance = safe_float(
        market_data.get("resistance")
    )

    nearest_support = safe_float(
        market_data.get(
            "nearest_support",
            support
        )
    )

    nearest_resistance = safe_float(
        market_data.get(
            "nearest_resistance",
            resistance
        )
    )

    rsi = safe_float(
        market_data.get("rsi")
    )

    ema9 = safe_float(
        market_data.get("ema9")
    )

    ema21 = safe_float(
        market_data.get("ema21")
    )

    ema50 = safe_float(
        market_data.get("ema50")
    )

    atr = safe_float(
        market_data.get("atr")
    )

    structure = market_data.get(
        "structure",
        "NEUTRAL"
    )

    timeframe_alignment = market_data.get(
        "timeframe_alignment",
        ""
    )

    entry_quality = market_data.get(
        "entry_quality",
        market_data.get(
            "entry_status",
            ""
        )
    )

    reasons = market_data.get(
        "reasons",
        market_data.get(
            "reason",
            []
        )
    )

    if isinstance(reasons, str):
        reasons = [reasons]

    news_risk = market_data.get(
        "news_risk",
        (
            news_data.get("risk", "LOW")
            if news_data
            else "LOW"
        )
    )

    h4_trend = market_data.get(
        "h4_trend",
        ""
    )

    h1_trend = market_data.get(
        "h1_trend",
        ""
    )

    m15_trend = market_data.get(
        "m15_trend",
        ""
    )

    m5_trend = market_data.get(
        "m5_trend",
        ""
    )

    plan_status = (
        market_data.get("plan_status")
        or market_data.get(
            "daily_plan_status"
        )
        or market_data.get(
            "status",
            "ACTIVE"
        )
    )

    if signal == "BUY":
        color = discord.Color.green()
        emoji = "🟢"
    elif signal == "SELL":
        color = discord.Color.red()
        emoji = "🔴"
    else:
        color = discord.Color.gold()
        emoji = "🟡"

    entry_status_map = {
        "EARLY": "🟢 EARLY",
        "GOOD ENTRY": "🟢 GOOD ENTRY",
        "ACCEPTABLE": "🟡 ACCEPTABLE",
        "LATE": "🟠 LATE",
        "EXTENDED / AVOID": "🔴 EXTENDED / AVOID",
        "MISSED": "🔴 MISSED",
        "INVALIDATED": "⚫ INVALIDATED",
    }

    entry_display = (
        entry_status_map.get(
            entry_quality.upper(),
            entry_quality
        )
        if entry_quality
        else "UNKNOWN"
    )

    title = (
        f"👑 KING ZARRY AI • "
        f"{symbol} SIGNAL"
    )

    desc = (
        f"{emoji} **{signal}** | "
        f"⏱ Execution: 15M | "
        f"{entry_display}"
    )

    embed = Embed(
        title=title,
        description=desc,
        color=color
    )

    mtf_text = (
        f"4H: {h4_trend or 'NEUTRAL'}\n"
        f"1H: {h1_trend or 'NEUTRAL'}\n"
        f"15M: {m15_trend or 'NEUTRAL'}\n"
        f"5M: {m5_trend or 'NEUTRAL'}"
    )

    embed.add_field(
        name="📊 MULTI-TIMEFRAME",
        value=mtf_text,
        inline=True
    )

    conf_text = (
        f"🔥 Confidence: {confidence} "
        f"({mtf_score}/100)\n"
        f"💪 Strength: {strength}/100\n"
        f"🧱 Alignment: "
        f"{timeframe_alignment or mtf_bias}"
    )

    embed.add_field(
        name="📈 ASSESSMENT",
        value=conf_text,
        inline=True
    )

    price_text = (
        f"💰 Price: `${price:,.2f}`\n"
        f"🎯 Entry: "
        f"`${entry_low:,.2f} - "
        f"${entry_high:,.2f}`\n"
        f"🛑 SL: `${stop_loss:,.2f}`"
    )

    embed.add_field(
        name="💵 PRICE",
        value=price_text,
        inline=False
    )

    tp_text = (
        f"TP1: `${tp1:,.2f}`\n"
        f"TP2: `${tp2:,.2f}`\n"
        f"TP3: `${tp3:,.2f}`\n"
        f"⚖️ RR: 1:{market_data.get('rr', 3.5)}"
    )

    embed.add_field(
        name="🎯 TARGETS",
        value=tp_text,
        inline=True
    )

    sr_text = (
        f"Support: `${support:,.2f}` "
        f"(nearest {nearest_support:,.2f})\n"
        f"Resistance: `${resistance:,.2f}` "
        f"(nearest {nearest_resistance:,.2f})\n"
        f"Structure: {structure}"
    )

    embed.add_field(
        name="🏗 LEVELS",
        value=sr_text,
        inline=True
    )

    ind_text = (
        f"RSI: {rsi:.1f}\n"
        f"EMA9: {ema9:,.2f}\n"
        f"EMA21: {ema21:,.2f}\n"
        f"EMA50: {ema50:,.2f}\n"
        f"ATR: {atr:,.2f}"
    )

    embed.add_field(
        name="📊 INDICATORS",
        value=ind_text,
        inline=True
    )

    news_risk_emoji = {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🟠",
        "EXTREME": "🔴",
        "UNKNOWN": "⚪",
    }.get(
        news_risk,
        "⚪"
    )

    news_val = (
        f"{news_risk_emoji} {news_risk}"
    )

    if (
        news_data
        and news_data.get("events")
    ):
        news_val += (
            f"\n📅 "
            f"{len(news_data['events'])} "
            f"events 24H"
        )

        for ev in news_data[
            "events"
        ][:2]:
            news_val += (
                f"\n• "
                f"{ev.get('event', '')[:60]}"
            )
    else:
        try:
            from news import provider_status

            status = provider_status()

            cal_avail = status.get(
                "calendar_available"
            )

            news_avail = status.get(
                "news_available"
            )

            if (
                not cal_avail
                and not news_avail
            ):
                news_val += (
                    "\n⚠️ Calendar & News: "
                    "UNAVAILABLE"
                )
            elif not cal_avail:
                news_val += (
                    "\n📅 Calendar: "
                    "UNAVAILABLE "
                    "(public fallback no cache)"
                )
            elif not news_avail:
                news_val += (
                    "\n📰 Headlines: "
                    "UNAVAILABLE"
                )
            else:
                news_val += (
                    "\n📰 No high-impact imminent"
                )

        except Exception:
            news_val += (
                "\n📰 Status: checking..."
            )

    embed.add_field(
        name="📰 NEWS RISK",
        value=news_val,
        inline=True
    )

    embed.add_field(
        name="🟢 ENTRY STATUS",
        value=entry_display,
        inline=True
    )

    if reasons:
        reason_text = "\n".join(
            f"{i + 1}. {r}"
            for i, r in enumerate(
                reasons[:5]
            )
        )

        embed.add_field(
            name="🧠 Why",
            value=reason_text[:1024],
            inline=False
        )

    embed.add_field(
        name="📋 Plan",
        value=(
            f"Status: {plan_status} | "
            f"Trading Date: "
            f"{market_data.get('trading_date', '')} | "
            f"ID: "
            f"{str(market_data.get('daily_plan_id', ''))[:8]}"
        ),
        inline=False
    )

    embed.set_footer(
        text=(
            "⚠️ Multi-timeframe analysis. "
            "Not financial advice. "
            "Use risk management."
        )
    )

    return embed


def enhance_text_prompt(
    user_prompt: str
) -> str:

    if not groq_client:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    system_prompt = (
        "You are King Zarry's professional "
        "cinematic AI video prompt engineer. "
        "Convert user's simple idea into ONE "
        "detailed, high-quality video generation "
        "prompt. Include: subject, environment, "
        "action, camera movement, lighting, "
        "atmosphere, cinematic style, realistic "
        "motion, composition. Return ONLY final "
        "prompt under 1200 chars."
    )

    completion = (
        groq_client
        .chat
        .completions
        .create(
            model=GROQ_TEXT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
    )

    result = (
        completion
        .choices[0]
        .message
        .content
    )

    if not result:
        raise RuntimeError(
            "Groq returned empty prompt."
        )

    return result.strip()


def enhance_image_prompt(
    image_bytes: bytes,
    motion_prompt: str
):

    if not groq_client:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    data_url = (
        "data:image/jpeg;base64,"
        + encoded
    )

    system_prompt = (
        "You are King Zarry's professional "
        "image-to-video prompt engineer. "
        "Analyze supplied image and requested "
        "motion. Create ONE cinematic "
        "image-to-video prompt. Preserve "
        "subject identities, faces, clothing, "
        "objects and overall composition while "
        "adding natural movement. Return ONLY "
        "final prompt under 1200 chars."
    )

    user_content = [
        {
            "type": "text",
            "text": (
                "User's requested motion:\n"
                + motion_prompt
            )
        },
        {
            "type": "image_url",
            "image_url": {
                "url": data_url
            }
        }
    ]

    completion = (
        groq_client
        .chat
        .completions
        .create(
            model=GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            temperature=0.6,
            max_tokens=600
        )
    )

    result = (
        completion
        .choices[0]
        .message
        .content
    )

    if not result:
        raise RuntimeError(
            "Groq returned empty image prompt."
        )

    return result.strip()


def generate_text_video(
    prompt: str
) -> bytes:

    if not FAL_KEY:
        raise RuntimeError(
            "FAL_KEY is not configured."
        )

    result = fal_client.subscribe(
        TEXT_TO_VIDEO_MODEL,
        arguments={
            "prompt": prompt
        }
    )

    video_url = (
        result
        .get("video", {})
        .get("url")
    )

    if not video_url:
        raise RuntimeError(
            "Fal.ai returned no video URL."
        )

    response = requests.get(
        video_url,
        timeout=120
    )

    response.raise_for_status()

    return response.content


def generate_image_video(
    image_bytes: bytes,
    prompt: str
) -> bytes:

    if not FAL_KEY:
        raise RuntimeError(
            "FAL_KEY is not configured."
        )

    image_url = fal_client.upload(
        image_bytes,
        "image/jpeg"
    )

    result = fal_client.subscribe(
        IMAGE_TO_VIDEO_MODEL,
        arguments={
            "image_url": image_url,
            "prompt": prompt
        }
    )

    video_url = (
        result
        .get("video", {})
        .get("url")
    )

    if not video_url:
        raise RuntimeError(
            "Fal.ai returned no video URL."
        )

    response = requests.get(
        video_url,
        timeout=120
    )

    response.raise_for_status()

    return response.content


def save_video(video_bytes: bytes):
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    ) as temp_file:
        temp_file.write(video_bytes)
        return temp_file.name


class KingZarryAI(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

    async def setup_hook(self):

        try:
            guild = discord.Object(
                id=DISCORD_GUILD_ID
            )

            self.tree.copy_global_to(
                guild=guild
            )

            synced = await self.tree.sync(
                guild=guild
            )

            print(
                f"✅ Synced {len(synced)} "
                f"commands to guild "
                f"{DISCORD_GUILD_ID}."
            )

        except Exception as e:
            print(
                "❌ COMMAND SYNC ERROR: "
                + _redact(repr(e))
            )

    async def on_ready(self):

        print("\n" + "=" * 60)

        print(
            "👑 KING ZARRY AI DISCORD IS ONLINE "
            "- MTF + NEWS EDITION"
        )

        print("=" * 60)

        print(
            f"🤖 Logged in as: {self.user}"
        )

        print(
            f"🆔 Bot ID: {self.user.id}"
        )

        print(
            "👑 Admin ID: configured"
        )

        print(
            "🏠 Guild ID: configured"
        )

        print(
            "💬 Message Content Intent: ENABLED"
        )

        print(
            "📸 Vision: ENABLED"
        )

        print(
            "🧠 Memory: ENABLED"
        )

        print(
            "📊 Market Engine: "
            "market.py analyze_market "
            "(daily plan + MTF + news)"
        )

        if eleven_client:
            print(
                "🎙️ ElevenLabs: ENABLED | "
                f"Model: "
                f"{_redact(ELEVENLABS_MODEL_ID)}"
            )
        else:
            print(
                "🎙️ ElevenLabs: DISABLED | "
                "AriaNeural fallback available"
            )

        print(
            f"🎬 Fal.ai: "
            f"{'ENABLED' if FAL_KEY else 'DISABLED'}"
        )

        print(
            "⭐ Premium: ENABLED "
            "(Discord Premium separate "
            "from Telegram Stars)"
        )

        print(
            "🛡️ Admin: ENABLED"
        )

        print(
            "📰 News Engine: ENABLED "
            "(news.py + provider_status)"
        )

        print("=" * 60 + "\n")

    async def on_message(
        self,
        message: discord.Message
    ):

        if message.author.bot:
            return

        if await user_is_banned(
            message.author.id
        ):
            return

        await track_user(
            message.author
        )

        content = message.content.strip()

        if self.user:
            content = (
                content
                .replace(
                    f"<@{self.user.id}>",
                    ""
                )
                .replace(
                    f"<@!{self.user.id}>",
                    ""
                )
                .strip()
            )

        images = [
            a
            for a in message.attachments
            if (
                a.content_type
                and a.content_type.startswith(
                    "image/"
                )
            )
        ]

        if not content and not images:
            return

        try:

            async with message.channel.typing():

                image_tuple = None

                if images:

                    attachment = images[0]

                    if attachment.size > MAX_IMAGE_SIZE:
                        await message.reply(
                            "❌ Image must be below 10 MB.",
                            mention_author=False
                        )
                        return

                    image_bytes = (
                        await attachment.read()
                    )

                    mime_type = (
                        attachment.content_type
                        or "image/png"
                    )

                    image_tuple = (
                        mime_type,
                        image_bytes
                    )

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            content
                        )
                    )

                    if (
                        symbol != "BTC/USD"
                        or any(
                            kw in content.upper()
                            for kw in [
                                "CHART",
                                "SIGNAL",
                                "ANALYSIS"
                            ]
                        )
                    ):
                        content = (
                            "Analyze this trading chart "
                            "screenshot. Market: "
                            f"{symbol} "
                            f"Timeframe: {timeframe}. "
                            "Only use information actually "
                            "visible in the image. "
                            "Summarize trend, "
                            "support/resistance, "
                            "patterns, EMA/RSI if visible, "
                            "possible BUY/SELL setup, "
                            "entry/SL/TP."
                        )

                    elif not content:
                        content = (
                            "Analyze this image carefully "
                            "and explain what you see."
                        )

                full_prompt = (
                    SYSTEM_VOICE_PROMPT
                    + "\n\nUser Question: "
                    + content
                )

                answer = await asyncio.to_thread(
                    ai.ask,
                    str(message.author.id),
                    full_prompt,
                    image_tuple
                )

            if not answer:
                answer = (
                    "❌ I couldn't generate a response."
                )

            voice_triggers = [
                "use voice",
                "speak",
                "send audio",
                "voice message",
                "say this",
                "can you speak",
                "female voice",
                "audio"
            ]

            wants_voice = any(
                trigger in content.lower()
                for trigger in voice_triggers
            )

            voice_file = None

            if wants_voice:

                try:
                    audio_fp, provider = (
                        await generate_tts_audio(
                            answer
                        )
                    )

                    voice_file = File(
                        fp=audio_fp,
                        filename="king_zarry_voice.mp3"
                    )

                except Exception as voice_error:

                    logger.warning(
                        "Voice generation error "
                        "(all providers failed): "
                        + _redact(
                            str(voice_error)
                        )
                    )

                    await message.reply(
                        "❌ Voice generation failed. "
                        "Both ElevenLabs and "
                        "AriaNeural fallback "
                        "are unavailable.",
                        mention_author=False
                    )

                    await send_chunks(
                        message,
                        answer
                    )

                    return

            if voice_file:

                await message.reply(
                    content=answer[:1900],
                    file=voice_file,
                    mention_author=False
                )

            else:

                await send_chunks(
                    message,
                    answer
                )

        except Exception as e:

            logger.error(
                "AI MESSAGE ERROR: "
                + _redact(repr(e))
            )

            try:

                await message.reply(
                    "❌ **King Zarry AI error**\n\n"
                    "⚠️ AI service is temporarily "
                    "busy. Please try again shortly.",
                    mention_author=False
                )

            except Exception:
                pass


client = KingZarryAI()


async def send_chunks(
    destination,
    text: str
):

    if not text:
        text = (
            "❌ King Zarry AI returned "
            "an empty response."
        )

    chunks = [
        text[i:i + 1900]
        for i in range(
            0,
            len(text),
            1900
        )
    ]

    for chunk in chunks:
        await destination.reply(
            chunk,
            mention_author=False
        )


async def send_followup_chunks(
    interaction: discord.Interaction,
    text: str
):

    if not text:
        text = (
            "❌ King Zarry AI returned "
            "an empty response."
        )

    chunks = [
        text[i:i + 1900]
        for i in range(
            0,
            len(text),
            1900
        )
    ]

    for chunk in chunks:
        await interaction.followup.send(
            chunk
        )


@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    embed = Embed(
        title="👑 KING ZARRY AI IS ONLINE",
        description=(
            "🧠 AI Agent • "
            "📊 Market Intelligence • "
            "📸 Vision • "
            "💾 Memory • "
            "🎙️ Voice • "
            "🎬 Video • "
            "⭐ Premium"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="TRADING",
        value=(
            "`/signal BTC` `/btc` "
            "`/eth` `/sol` `/xau` `/plan`"
        ),
        inline=False
    )

    embed.add_field(
        name="AI",
        value="`/ask` `/voice` `/tts`",
        inline=False
    )

    embed.add_field(
        name="NEWS",
        value="`/news` `/events`",
        inline=False
    )

    embed.add_field(
        name="PREMIUM",
        value=(
            "`/premium` `/status` - "
            "Discord Premium separate "
            "from Telegram Stars"
        ),
        inline=False
    )

    embed.add_field(
        name="VOICE",
        value="`/join` `/say` `/leave`",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@client.tree.command(
    name="help",
    description="Help for King Zarry AI"
)
async def help_cmd(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    text = (
        "👑 **KING ZARRY AI HELP**\n\n"

        "**Trading (same engine as Telegram):**\n"
        "`/signal BTC` - BTC MTF signal with daily plan\n"
        "`/btc [timeframe]` `/eth` `/sol` "
        "`/xau` `/gold [timeframe]` - "
        "Quick analysis "
        "(timeframe validated, "
        "execution daily-plan 15M)\n"
        "`/plan BTC` - Daily plan status\n"
        "`/analyze SYMBOL [timeframe]` - "
        "Custom symbol with timeframe passthrough\n\n"

        "**News:**\n"
        "`/news` - Provider status & upcoming\n"
        "`/events` - Upcoming economic events\n\n"

        "**AI:**\n"
        "`/ask` - Ask AI\n"
        "`/voice` - Voice answer with "
        "ElevenLabs + AriaNeural fallback\n"
        "`/tts TEXT` - Convert text to speech "
        "with ElevenLabs + AriaNeural fallback\n\n"

        "**Premium:**\n"
        "`/premium` - Status "
        "(Discord Premium separate "
        "from Telegram Stars)\n"
        "`/status` - Alias\n\n"

        "**Voice Channel:**\n"
        "`/join` `/say TEXT` `/leave`\n\n"

        "Engine: market.py daily plan + "
        "MTF 4H→1H→15M→5M + news_engine\n"

        "Voice: ElevenLabs + "
        "en-US-AriaNeural fallback"
    )

    await interaction.response.send_message(
        text
    )


@client.tree.command(
    name="ping",
    description="Check King Zarry AI status"
)
async def ping(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    try:

        from news import (
            provider_status as news_provider_status
        )

        p_status = news_provider_status()

        cal = (
            "✅"
            if p_status.get(
                "calendar_available"
            )
            else "❌"
        )

        news_av = (
            "✅"
            if p_status.get(
                "news_available"
            )
            else "❌"
        )

        news_line = (
            f"{cal} Calendar "
            f"{news_av} Headlines"
        )

    except Exception:
        news_line = "Checking..."

    if eleven_client:
        voice_status = (
            "ElevenLabs enabled "
            f"({ELEVENLABS_MODEL_ID}) "
            "+ AriaNeural fallback"
        )
    else:
        voice_status = (
            "AriaNeural fallback "
            "(ElevenLabs not configured)"
        )

    await interaction.response.send_message(
        f"👑 **King Zarry AI is online!**\n"
        f"🧠 AI: Connected "
        f"({ai._get_provider_order()[0]})\n"
        f"📸 Vision: Connected\n"
        f"📊 Market: market.py daily plan engine\n"
        f"📰 News: {news_line}\n"
        f"🎬 Fal.ai: "
        f"{'Connected' if FAL_KEY else 'Not configured'}\n"
        f"🎙️ Voice: {voice_status}\n"
        f"⭐ Premium: Connected "
        f"(Discord Premium separate "
        f"from Telegram Stars)\n"
        f"💾 Memory: {MEMORY_DB_PATH}"
    )


VALID_TIMEFRAMES = {
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "1d"
}


def normalize_tf(
    tf: str
) -> str:

    tf = tf.lower().strip()

    return (
        tf
        if tf in VALID_TIMEFRAMES
        else "15m"
    )


async def handle_signal(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15m",
    defer: bool = True
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    if defer:
        await interaction.response.defer()

    try:

        tf = normalize_tf(
            timeframe
        )

        market_data = (
            await asyncio.to_thread(
                market_engine.analyze_market,
                symbol,
                tf
            )
        )

        news_data = (
            await asyncio.to_thread(
                news_engine.get_news_for_asset,
                symbol
            )
        )

        embed = build_discord_signal_embed(
            market_data,
            news_data
        )

        if (
            tf
            != timeframe.lower().strip()
        ):
            embed.set_footer(
                text=(
                    f"⚠️ Requested timeframe "
                    f"'{timeframe}' normalized "
                    f"to {tf}. Execution remains "
                    f"daily-plan based. "
                    f"Not financial advice."
                )
            )

        if defer:
            await interaction.followup.send(
                embed=embed
            )
        else:
            await interaction.response.send_message(
                embed=embed
            )

    except Exception as e:

        logger.error(
            f"Signal error for "
            f"{symbol} {timeframe}: "
            + _redact(repr(e))
        )

        err_msg = (
            "⚠️ AI service is temporarily "
            "busy. Please try again shortly."
        )

        if (
            "TWELVE_DATA_API_KEY"
            in str(e)
            or "Twelve"
            in str(e)
        ):
            err_msg = (
                "❌ Market data provider "
                "unavailable. Please check "
                "TWELVE_DATA_API_KEY."
            )

        if defer:
            await interaction.followup.send(
                err_msg
            )
        else:
            await interaction.response.send_message(
                err_msg,
                ephemeral=True
            )


@client.tree.command(
    name="signal",
    description="Get MTF trading signal with daily plan"
)
@app_commands.describe(
    symbol="BTC, ETH, SOL, XAU"
)
@app_commands.choices(
    symbol=[
        app_commands.Choice(
            name="BTC/USD",
            value="BTC/USD"
        ),
        app_commands.Choice(
            name="ETH/USD",
            value="ETH/USD"
        ),
        app_commands.Choice(
            name="SOL/USD",
            value="SOL/USD"
        ),
        app_commands.Choice(
            name="XAU/USD Gold",
            value="XAU/USD"
        ),
    ]
)
async def signal_cmd(
    interaction: discord.Interaction,
    symbol: str = "BTC/USD"
):
    await handle_signal(
        interaction,
        symbol,
        "15m"
    )


@client.tree.command(
    name="btc",
    description=(
        "Analyze Bitcoin market MTF "
        "(daily plan execution 15M)"
    )
)
@app_commands.describe(
    timeframe=(
        "Valid: 1m,5m,15m,30m,1h,2h,4h,1d "
        "- passed to market engine, "
        "execution remains daily-plan 15M"
    )
)
async def btc(
    interaction: discord.Interaction,
    timeframe: str = "15m"
):
    await handle_signal(
        interaction,
        "BTC/USD",
        timeframe
    )


@client.tree.command(
    name="eth",
    description="Analyze Ethereum market MTF"
)
async def eth(
    interaction: discord.Interaction
):
    await handle_signal(
        interaction,
        "ETH/USD",
        "15m"
    )


@client.tree.command(
    name="sol",
    description="Analyze Solana market MTF"
)
async def sol(
    interaction: discord.Interaction
):
    await handle_signal(
        interaction,
        "SOL/USD",
        "15m"
    )


@client.tree.command(
    name="xau",
    description="Analyze Gold XAU/USD market MTF"
)
async def xau(
    interaction: discord.Interaction
):
    await handle_signal(
        interaction,
        "XAU/USD",
        "15m"
    )


@client.tree.command(
    name="gold",
    description=(
        "Analyze Gold market MTF "
        "(daily plan 15M)"
    )
)
@app_commands.describe(
    timeframe=(
        "Valid: 1m,5m,15m,30m,1h,2h,4h,1d "
        "- execution remains daily-plan 15M"
    )
)
async def gold(
    interaction: discord.Interaction,
    timeframe: str = "15m"
):
    await handle_signal(
        interaction,
        "XAU/USD",
        timeframe
    )


@client.tree.command(
    name="crypto",
    description=(
        "Check BTC, ETH, SOL and XAU "
        "prices (daily plan engine)"
    )
)
async def crypto(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        symbols = [
            "BTC/USD",
            "ETH/USD",
            "SOL/USD",
            "XAU/USD"
        ]

        results = []

        for sym in symbols:

            try:

                data = (
                    await asyncio.to_thread(
                        market_engine.analyze_market,
                        sym,
                        "15m"
                    )
                )

                price = safe_float(
                    data.get("price")
                )

                sig = data.get(
                    "signal",
                    "WAIT"
                )

                results.append(
                    f"**{sym}**: "
                    f"`${price:,.2f}` - "
                    f"{sig}"
                )

            except Exception as e:

                results.append(
                    f"**{sym}**: Error - "
                    f"{_redact(str(e))[:50]}"
                )

        await interaction.followup.send(
            "👑 **CRYPTO PRICES "
            "(Daily Plan Engine)**\n\n"
            + "\n".join(results)
        )

    except Exception as e:

        await interaction.followup.send(
            "❌ Price fetch failed: "
            + _redact(str(e))[:200]
        )


@client.tree.command(
    name="analyze",
    description=(
        "Analyze custom market "
        "(timeframe validated, "
        "execution daily-plan 15M)"
    )
)
@app_commands.describe(
    symbol=(
        "BTC/USD, EUR/USD, XAU/USD, etc."
    ),
    timeframe=(
        "Valid: 1m,5m,15m,30m,1h,2h,4h,1d "
        "- passed to market engine"
    )
)
async def analyze(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15m"
):

    await handle_signal(
        interaction,
        symbol.upper(),
        timeframe
    )


@client.tree.command(
    name="plan",
    description="Show daily plan for symbol"
)
@app_commands.describe(
    symbol=(
        "BTC/USD, ETH/USD, SOL/USD, XAU/USD"
    )
)
async def plan_cmd(
    interaction: discord.Interaction,
    symbol: str = "BTC/USD"
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        trading_date = (
            market_engine.get_trading_date()
        )

        plan = (
            await asyncio.to_thread(
                market_engine.get_daily_plan,
                symbol,
                trading_date
            )
        )

        if not plan:
            await interaction.followup.send(
                f"📭 No active daily plan "
                f"for {symbol} on "
                f"{trading_date}. "
                f"Use `/signal {symbol}` "
                f"to create one."
            )
            return

        embed = build_discord_signal_embed(
            plan,
            None
        )

        embed.title = (
            f"📋 DAILY PLAN • "
            f"{symbol} • {trading_date}"
        )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as e:

        await interaction.followup.send(
            "❌ Plan error: "
            + _redact(str(e))[:300]
        )


@client.tree.command(
    name="news",
    description=(
        "Check news engine status "
        "and upcoming news"
    )
)
async def news_cmd(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        from news import (
            provider_status,
            news_health
        )

        status = provider_status()
        health = news_health()

        embed = Embed(
            title="📰 KING ZARRY NEWS ENGINE",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Selected News Provider",
            value=status.get(
                "selected_news_provider",
                "AUTO"
            ),
            inline=True
        )

        embed.add_field(
            name="Selected Calendar Provider",
            value=status.get(
                "selected_calendar_provider",
                "AUTO"
            ),
            inline=True
        )

        embed.add_field(
            name="Calendar Available",
            value=(
                "✅ YES"
                if status.get(
                    "calendar_available"
                )
                else
                "❌ NO - calendar data "
                "unavailable "
                "(public fallback has no "
                "cached data)"
            ),
            inline=False
        )

        embed.add_field(
            name="Headlines Available",
            value=(
                "✅ YES"
                if status.get(
                    "news_available"
                )
                else
                "❌ NO - no headline "
                "provider configured"
            ),
            inline=False
        )

        embed.add_field(
            name="Health",
            value=(
                f"Overall: "
                f"{health.get('status')} | "
                f"Calendar: "
                f"{health.get('calendar_status')} | "
                f"Headlines: "
                f"{health.get('headline_status')}"
            ),
            inline=False
        )

        embed.add_field(
            name="Providers",
            value=(
                f"EODHD: "
                f"{status.get('eodhd')} | "
                f"TE: "
                f"{status.get('tradingeconomics')} | "
                f"Finnhub: "
                f"{status.get('finnhub')} | "
                f"Currents: "
                f"{status.get('currents')} | "
                f"NewsData: "
                f"{status.get('newsdata')}"
            ),
            inline=False
        )

        try:

            news_data = (
                await asyncio.to_thread(
                    news_engine.get_news_for_asset,
                    "BTC/USD"
                )
            )

            risk = news_data.get(
                "risk",
                "LOW"
            )

            ev_count = len(
                news_data.get(
                    "events",
                    []
                )
            )

            embed.add_field(
                name="BTC News Sample",
                value=(
                    f"Risk: {risk} | "
                    f"Events: {ev_count} | "
                    f"Headlines: "
                    f"{len(news_data.get('headlines', []))}"
                ),
                inline=False
            )

        except Exception as e:

            embed.add_field(
                name="BTC News Sample",
                value=(
                    "Error: "
                    + _redact(str(e))[:200]
                ),
                inline=False
            )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as e:

        await interaction.followup.send(
            "❌ News engine error: "
            + _redact(str(e))[:500]
        )


@client.tree.command(
    name="events",
    description="Upcoming economic events"
)
@app_commands.describe(
    hours="Hours ahead (default 24)"
)
async def events_cmd(
    interaction: discord.Interaction,
    hours: int = 24
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        from news import get_upcoming_events

        events = (
            await asyncio.to_thread(
                get_upcoming_events,
                hours
            )
        )

        if not events:

            from news import provider_status

            ps = provider_status()

            if not ps.get(
                "calendar_available"
            ):
                await interaction.followup.send(
                    "📅 **No events**\n\n"
                    "⚠️ Economic calendar "
                    "unavailable: no keyed "
                    "provider configured and "
                    "no cached ForexFactory "
                    "data. Configure "
                    "EODHD_API_KEY or "
                    "TRADING_ECONOMICS_API_KEY."
                )
            else:
                await interaction.followup.send(
                    f"📅 No high-impact events "
                    f"in next {hours}h. "
                    f"Calendar available: "
                    f"{ps.get('calendar_available')}"
                )

            return

        embed = Embed(
            title=(
                f"📅 Upcoming Events "
                f"({hours}h)"
            ),
            color=discord.Color.gold()
        )

        for ev in events[:10]:

            title = ev.get(
                "event",
                "Unknown"
            )[:100]

            time_str = ev.get(
                "time",
                ev.get(
                    "datetime",
                    ""
                )
            )[:50]

            impact = ev.get(
                "impact",
                "medium"
            )

            embed.add_field(
                name=(
                    f"{impact.upper()} - "
                    f"{time_str}"
                ),
                value=title,
                inline=False
            )

        await interaction.followup.send(
            embed=embed
        )

    except Exception as e:

        await interaction.followup.send(
            "❌ Events error: "
            + _redact(str(e))[:400]
        )


@client.tree.command(
    name="premium",
    description=(
        "Check or manage Premium "
        "(Discord Premium separate "
        "from Telegram Stars)"
    )
)
@app_commands.describe(
    user="Admin: user to grant/revoke",
    plan=(
        "Admin: monthly, 3month, "
        "yearly, or revoke"
    )
)
@app_commands.choices(
    plan=[
        app_commands.Choice(
            name="monthly - 250 XTR",
            value="monthly"
        ),
        app_commands.Choice(
            name="3 months - 600 XTR",
            value="3month"
        ),
        app_commands.Choice(
            name="yearly - 2000 XTR",
            value="yearly"
        ),
        app_commands.Choice(
            name="revoke premium",
            value="revoke"
        ),
    ]
)
async def premium(
    interaction: discord.Interaction,
    user: Optional[discord.User] = None,
    plan: Optional[
        app_commands.Choice[str]
    ] = None
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    if user is None and plan is None:

        subscription = (
            await asyncio.to_thread(
                get_subscription_sync,
                interaction.user.id
            )
        )

        if not subscription:

            await interaction.response.send_message(
                "⭐ **KING ZARRY PREMIUM**\n\n"
                "You do not currently have "
                "an active Premium subscription.\n\n"
                "Available plans:\n"
                "• Monthly: **250 XTR / 30 days**\n"
                "• 3 Months: **600 XTR / 90 days**\n"
                "• Yearly: **2000 XTR / 365 days**\n\n"
                "Discord Premium status is "
                "separate from Telegram Stars.\n"
                "Contact administrator to activate.",
                ephemeral=True
            )

            return

        expires = datetime.fromisoformat(
            subscription["expires_at"]
        )

        await interaction.response.send_message(
            "⭐ **KING ZARRY PREMIUM**\n\n"
            f"Plan: **{subscription['plan']}**\n"
            f"Expires: "
            f"**{expires:%Y-%m-%d %H:%M UTC}**\n\n"
            "✅ Premium is active.\n\n"
            "Discord Premium status is "
            "separate from Telegram Stars.",
            ephemeral=True
        )

        return

    if not await require_admin(
        interaction
    ):
        return

    if user is None or plan is None:

        await interaction.response.send_message(
            "❌ Admin usage: "
            "`/premium @user monthly`",
            ephemeral=True
        )

        return

    if plan.value == "revoke":

        removed = (
            await asyncio.to_thread(
                revoke_subscription_sync,
                user.id
            )
        )

        await interaction.response.send_message(
            (
                "🗑️ Premium revoked for "
                + user.mention
                + "."
                if removed
                else
                "ℹ️ "
                + user.mention
                + " had no active Premium."
            ),
            ephemeral=True
        )

        return

    expires = (
        await asyncio.to_thread(
            grant_subscription_sync,
            user.id,
            plan.value,
            interaction.user.id
        )
    )

    await interaction.response.send_message(
        "⭐ **PREMIUM ACTIVATED**\n\n"
        f"👤 User: {user.mention}\n"
        f"📦 Plan: **{plan.value}**\n"
        f"💳 Price: "
        f"**{PREMIUM_PLANS[plan.value]['price']}**\n"
        f"📅 Expires: "
        f"**{expires:%Y-%m-%d %H:%M UTC}**",
        ephemeral=True
    )

    try:

        await user.send(
            "👑 **KING ZARRY AI PREMIUM ACTIVATED!**\n\n"
            f"⭐ Plan: **{plan.value}**\n"
            f"📅 Expires: "
            f"**{expires:%Y-%m-%d %H:%M UTC}**\n\n"
            "Your Premium access is now active."
        )

    except discord.HTTPException:
        pass


@client.tree.command(
    name="status",
    description="Alias for premium status"
)
async def status_cmd(
    interaction: discord.Interaction
):
    await premium(interaction)


@client.tree.command(
    name="admin",
    description="Open admin panel"
)
async def admin(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    users = await asyncio.to_thread(
        get_user_count_sync
    )

    premium_users = await asyncio.to_thread(
        get_premium_count_sync
    )

    banned = await asyncio.to_thread(
        get_banned_count_sync
    )

    embed = Embed(
        title="👑 KING ZARRY AI ADMIN PANEL",
        description=(
            "🛡️ Administrator access confirmed."
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="👑 Admin ID",
        value=f"`{DISCORD_ADMIN_ID}`",
        inline=False
    )

    embed.add_field(
        name="🏠 Guild",
        value=f"`{DISCORD_GUILD_ID}`",
        inline=False
    )

    embed.add_field(
        name="👥 Users",
        value=str(users),
        inline=True
    )

    embed.add_field(
        name="⭐ Premium",
        value=str(premium_users),
        inline=True
    )

    embed.add_field(
        name="⛔ Banned",
        value=str(banned),
        inline=True
    )

    embed.add_field(
        name="🛠️ Admin Commands",
        value=(
            "`/users`\n"
            "`/broadcast`\n"
            "`/ban`\n"
            "`/unban`\n"
            "`/premium`\n"
            "`/admin`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@client.tree.command(
    name="users",
    description="View user statistics"
)
async def users(
    interaction: discord.Interaction
):

    if not await require_admin(
        interaction
    ):
        return

    total = await asyncio.to_thread(
        get_user_count_sync
    )

    premium_users = await asyncio.to_thread(
        get_premium_count_sync
    )

    banned = await asyncio.to_thread(
        get_banned_count_sync
    )

    await interaction.response.send_message(
        "👑 **KING ZARRY AI USER ANALYTICS**\n\n"
        f"👥 Total tracked users: **{total}**\n"
        f"⭐ Active Premium users: "
        f"**{premium_users}**\n"
        f"⛔ Banned users: **{banned}**\n"
        f"🏠 Guilds: **{len(client.guilds)}**",
        ephemeral=True
    )


@client.tree.command(
    name="ban",
    description="Ban a user from King Zarry AI"
)
@app_commands.describe(
    user="Discord user to ban",
    reason="Reason for the ban"
)
async def ban(
    interaction: discord.Interaction,
    user: discord.User,
    reason: str = "No reason provided"
):

    if not await require_admin(
        interaction
    ):
        return

    if user.id == DISCORD_ADMIN_ID:

        await interaction.response.send_message(
            "❌ You cannot ban the "
            "configured administrator.",
            ephemeral=True
        )

        return

    await asyncio.to_thread(
        ban_user_sync,
        user.id,
        reason,
        interaction.user.id
    )

    await interaction.response.send_message(
        "⛔ **USER BANNED**\n\n"
        f"👤 User: {user.mention}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📝 Reason: {reason}",
        ephemeral=True
    )

    try:

        await user.send(
            "⛔ You have been banned "
            "from King Zarry AI.\n\n"
            f"Reason: {reason}"
        )

    except discord.HTTPException:
        pass


@client.tree.command(
    name="unban",
    description="Remove a ban"
)
@app_commands.describe(
    user_id="Discord user ID to unban"
)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):

    if not await require_admin(
        interaction
    ):
        return

    try:
        target_id = int(user_id)

    except ValueError:

        await interaction.response.send_message(
            "❌ User ID must be a number.",
            ephemeral=True
        )

        return

    removed = await asyncio.to_thread(
        unban_user_sync,
        target_id
    )

    await interaction.response.send_message(
        (
            "✅ User `"
            + str(target_id)
            + "` has been unbanned."
            if removed
            else
            "ℹ️ User `"
            + str(target_id)
            + "` was not banned."
        ),
        ephemeral=True
    )


@client.tree.command(
    name="broadcast",
    description=(
        "Broadcast message + optional "
        "attachment to tracked users"
    )
)
@app_commands.describe(
    message="Message to send",
    attachment=(
        "Optional image/attachment "
        "to broadcast"
    )
)
async def broadcast(
    interaction: discord.Interaction,
    message: str,
    attachment: Optional[
        discord.Attachment
    ] = None
):

    if not await require_admin(
        interaction
    ):
        return

    if len(message) > 1900:

        await interaction.response.send_message(
            "❌ Broadcast must be "
            "1900 characters or less.",
            ephemeral=True
        )

        return

    broadcast_bytes = None
    broadcast_filename = None

    if attachment:

        if attachment.size > MAX_IMAGE_SIZE:

            await interaction.response.send_message(
                "❌ Attachment must be "
                "below 10 MB.",
                ephemeral=True
            )

            return

        ctype = attachment.content_type

        if (
            not ctype
            or ctype not in ALLOWED_BROADCAST_TYPES
        ):

            await interaction.response.send_message(
                "❌ Attachment type not allowed. "
                "Use PNG/JPEG/WEBP/GIF/MP4.",
                ephemeral=True
            )

            return

        try:

            broadcast_bytes = (
                await attachment.read()
            )

            broadcast_filename = (
                attachment.filename
            )

        except Exception as e:

            await interaction.response.send_message(
                "❌ Failed to read attachment: "
                + _redact(str(e))[:200],
                ephemeral=True
            )

            return

    await interaction.response.defer(
        ephemeral=True
    )

    user_ids = await asyncio.to_thread(
        get_all_user_ids_sync
    )

    sent = 0
    failed = 0

    for user_id in user_ids:

        if user_id == DISCORD_ADMIN_ID:
            continue

        try:

            user = client.get_user(
                user_id
            )

            if user is None:
                user = await client.fetch_user(
                    user_id
                )

            if await user_is_banned(
                user_id
            ):
                continue

            if broadcast_bytes:

                file_obj = discord.File(
                    io.BytesIO(
                        broadcast_bytes
                    ),
                    filename=broadcast_filename
                )

                await user.send(
                    "👑 **KING ZARRY AI ANNOUNCEMENT**\n\n"
                    + message,
                    file=file_obj
                )

            else:

                await user.send(
                    "👑 **KING ZARRY AI ANNOUNCEMENT**\n\n"
                    + message
                )

            sent += 1

            await asyncio.sleep(0.5)

        except Exception as e:

            logger.warning(
                f"Broadcast failed for "
                f"{user_id}: "
                + _redact(str(e))
            )

            failed += 1

    await interaction.followup.send(
        "📢 **BROADCAST COMPLETE**\n\n"
        f"✅ Sent: **{sent}**\n"
        f"❌ Failed: **{failed}**\n"
        f"👥 Tracked: **{len(user_ids)}**\n"
        f"📎 Attachment: "
        f"{'Yes - ' + broadcast_filename if broadcast_bytes else 'No'}",
        ephemeral=True
    )


@client.tree.command(
    name="ask",
    description="Ask King Zarry AI anything"
)
@app_commands.describe(
    question="Your question"
)
async def ask(
    interaction: discord.Interaction,
    question: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        answer = await asyncio.to_thread(
            ai.ask,
            str(interaction.user.id),
            question
        )

        await send_followup_chunks(
            interaction,
            answer
        )

    except Exception as e:

        logger.error(
            "/ask ERROR: "
            + _redact(repr(e))
        )

        await interaction.followup.send(
            "⚠️ AI service is temporarily "
            "busy. Please try again shortly."
        )


@client.tree.command(
    name="voice",
    description=(
        "Ask AI and receive voice "
        "(ElevenLabs + AriaNeural fallback)"
    )
)
@app_commands.describe(
    question="Your question"
)
async def voice_command(
    interaction: discord.Interaction,
    question: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        full_prompt = (
            SYSTEM_VOICE_PROMPT
            + "\n\nUser Question: "
            + question
        )

        answer = await asyncio.to_thread(
            ai.ask,
            str(interaction.user.id),
            full_prompt
        )

        audio_fp, provider = (
            await generate_tts_audio(
                answer
            )
        )

        discord_file = File(
            fp=audio_fp,
            filename="king_zarry_voice.mp3"
        )

        await interaction.followup.send(
            content=(
                f"🗣️ **King Zarry AI "
                f"({provider}):**\n"
                f"{answer[:1500]}"
            ),
            file=discord_file
        )

    except Exception as e:

        logger.error(
            "/voice ERROR: "
            + _redact(repr(e))
        )

        await interaction.followup.send(
            "⚠️ Voice service temporarily busy."
        )


@client.tree.command(
    name="tts",
    description=(
        "Convert text to speech with "
        "ElevenLabs + AriaNeural fallback"
    )
)
@app_commands.describe(
    text="Text to speak"
)
async def tts_cmd(
    interaction: discord.Interaction,
    text: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    try:

        audio_fp, provider = (
            await generate_tts_audio(
                text
            )
        )

        discord_file = File(
            fp=audio_fp,
            filename="king_zarry_tts.mp3"
        )

        await interaction.followup.send(
            content=(
                f"🎙️ **TTS {provider}:** "
                f"{text[:500]}"
            ),
            file=discord_file
        )

    except Exception as e2:

        await interaction.followup.send(
            "❌ TTS unavailable: "
            + _redact(str(e2))[:300]
        )


@client.tree.command(
    name="textvideo",
    description="Generate a video from text"
)
@app_commands.describe(
    prompt="Describe the video"
)
async def textvideo(
    interaction: discord.Interaction,
    prompt: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    if len(prompt.strip()) == 0:

        await interaction.response.send_message(
            "❌ Please provide a prompt.",
            ephemeral=True
        )

        return

    if len(prompt) > MAX_PROMPT_LENGTH:

        await interaction.response.send_message(
            f"❌ Prompt too long. "
            f"Max {MAX_PROMPT_LENGTH} characters.",
            ephemeral=True
        )

        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    status_msg = (
        await interaction.followup.send(
            "🧠 **Enhancing your video prompt...**"
        )
    )

    video_path = None

    try:

        enhanced_prompt = (
            await asyncio.to_thread(
                enhance_text_prompt,
                prompt.strip()
            )
        )

        await status_msg.edit(
            content=(
                "🎬 **Generating video "
                "with Fal.ai...**\n"
                "⏳ Please wait."
            )
        )

        video_bytes = (
            await asyncio.to_thread(
                generate_text_video,
                enhanced_prompt
            )
        )

        if len(video_bytes) > MAX_VIDEO_SIZE:

            await status_msg.edit(
                content=(
                    "⚠️ Generated video "
                    "exceeds Discord "
                    "upload limit."
                )
            )

            return

        video_path = save_video(
            video_bytes
        )

        file = discord.File(
            video_path,
            filename="king-zarry-video.mp4"
        )

        embed = Embed(
            title="👑 King Zarry Video",
            description=(
                "🎬 **Text → Video Complete**"
            )
        )

        embed.add_field(
            name="Enhanced Prompt",
            value=enhanced_prompt[:1000],
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            file=file
        )

        await status_msg.delete()

    except fal_client.FalClientHTTPError as err:

        if (
            getattr(
                err,
                "status_code",
                None
            ) == 403
            or "Exhausted balance"
            in str(err)
        ):

            await status_msg.edit(
                content=(
                    "⚠️ Fal.ai balance/quota "
                    "is exhausted. Chat, vision "
                    "and voice remain available."
                )
            )

        else:

            await status_msg.edit(
                content=(
                    "❌ Video error: `"
                    + _redact(str(err))[:800]
                    + "`"
                )
            )

    except Exception as error:

        logger.error(
            "Text-to-video error: "
            + _redact(repr(error))
        )

        await status_msg.edit(
            content=(
                "❌ **Generation failed.**\n`"
                + _redact(str(error))[:800]
                + "`"
            )
        )

    finally:

        if (
            video_path
            and os.path.exists(video_path)
        ):
            try:
                os.remove(video_path)
            except OSError:
                pass


@client.tree.command(
    name="imagevideo",
    description="Turn an image into a video"
)
@app_commands.describe(
    image="Upload PNG, JPEG or WebP",
    motion="Describe the desired motion"
)
async def imagevideo(
    interaction: discord.Interaction,
    image: discord.Attachment,
    motion: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    if (
        image.content_type
        not in ALLOWED_VIDEO_IMAGE_TYPES
    ):

        await interaction.response.send_message(
            "❌ Upload PNG, JPEG or WebP.",
            ephemeral=True
        )

        return

    if image.size > MAX_IMAGE_SIZE:

        await interaction.response.send_message(
            "❌ Image must be below 10 MB.",
            ephemeral=True
        )

        return

    if not motion.strip():

        await interaction.response.send_message(
            "❌ Describe the motion.",
            ephemeral=True
        )

        return

    await track_user(
        interaction.user
    )

    await interaction.response.defer()

    status_msg = (
        await interaction.followup.send(
            "📥 **Downloading and "
            "analyzing image...**"
        )
    )

    video_path = None

    try:

        image_bytes = (
            await image.read()
        )

        enhanced_prompt = (
            await asyncio.to_thread(
                enhance_image_prompt,
                image_bytes,
                motion.strip()
            )
        )

        await status_msg.edit(
            content=(
                "🎬 **Generating "
                "image-to-video...**\n"
                "⏳ Please wait."
            )
        )

        video_bytes = (
            await asyncio.to_thread(
                generate_image_video,
                image_bytes,
                enhanced_prompt
            )
        )

        if len(video_bytes) > MAX_VIDEO_SIZE:

            await status_msg.edit(
                content=(
                    "⚠️ Generated video "
                    "exceeds configured limit."
                )
            )

            return

        video_path = save_video(
            video_bytes
        )

        file = discord.File(
            video_path,
            filename="king-zarry-image-video.mp4"
        )

        embed = Embed(
            title="👑 King Zarry Video",
            description=(
                "🖼️ **Image → Video Complete**"
            )
        )

        embed.add_field(
            name="Motion Prompt",
            value=enhanced_prompt[:1000],
            inline=False
        )

        await interaction.followup.send(
            embed=embed,
            file=file
        )

        await status_msg.delete()

    except fal_client.FalClientHTTPError as err:

        if (
            getattr(
                err,
                "status_code",
                None
            ) == 403
            or "Exhausted balance"
            in str(err)
        ):

            await status_msg.edit(
                content=(
                    "⚠️ Fal.ai quota is exhausted. "
                    "Chat, vision and voice "
                    "remain available."
                )
            )

        else:

            await status_msg.edit(
                content=(
                    "❌ Video error: `"
                    + _redact(str(err))[:800]
                    + "`"
                )
            )

    except Exception as error:

        logger.error(
            "Image-to-video error: "
            + _redact(repr(error))
        )

        await status_msg.edit(
            content=(
                "❌ **Generation failed.**\n`"
                + _redact(str(error))[:800]
                + "`"
            )
        )

    finally:

        if (
            video_path
            and os.path.exists(video_path)
        ):
            try:
                os.remove(video_path)
            except OSError:
                pass


@client.tree.command(
    name="clear_memory",
    description="Clear your AI conversation memory"
)
async def clear_memory(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        await asyncio.to_thread(
            memory.clear_history,
            str(interaction.user.id)
        )

        await interaction.followup.send(
            "🧹 Your AI memory has been cleared.",
            ephemeral=True
        )

    except Exception as e:

        await interaction.followup.send(
            "❌ Memory error:\n`"
            + _redact(str(e))[:1200]
            + "`",
            ephemeral=True
        )


@client.tree.command(
    name="join",
    description="Join your current voice channel"
)
async def join(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    if not interaction.user.voice:

        await interaction.response.send_message(
            "❌ Join a voice channel first.",
            ephemeral=True
        )

        return

    channel = (
        interaction
        .user
        .voice
        .channel
    )

    if interaction.guild.voice_client:

        await interaction.guild.voice_client.move_to(
            channel
        )

    else:

        await channel.connect()

    await interaction.response.send_message(
        f"🔊 Joined **{channel.name}**."
    )


@client.tree.command(
    name="say",
    description="Speak text in your current voice channel"
)
@app_commands.describe(
    text="What King Zarry AI should say"
)
async def say(
    interaction: discord.Interaction,
    text: str
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    if not text.strip():

        await interaction.response.send_message(
            "❌ Please provide text to speak.",
            ephemeral=True
        )

        return

    await interaction.response.defer()

    voice_client = (
        interaction.guild.voice_client
    )

    if not voice_client:

        if (
            interaction.user.voice
            and interaction.user.voice.channel
        ):

            voice_client = (
                await interaction
                .user
                .voice
                .channel
                .connect()
            )

        else:

            await interaction.followup.send(
                "❌ Join a voice channel first."
            )

            return

    audio_stream = None

    try:

        audio_stream, provider = (
            await generate_tts_audio(
                text
            )
        )

        await interaction.followup.send(
            f"🎙️ **Speaking with "
            f"{provider}:** "
            f"{text[:500]}"
        )

        audio_source = discord.FFmpegPCMAudio(
            audio_stream,
            pipe=True
        )

        if voice_client.is_playing():
            voice_client.stop()

        def after_playback(error):
            if error:
                logger.error(
                    "/say playback error: "
                    + _redact(str(error))
                )
            else:
                logger.info(
                    f"/say playback finished "
                    f"using {provider}."
                )

            try:
                audio_stream.close()
            except Exception:
                pass

        voice_client.play(
            audio_source,
            after=after_playback
        )

    except Exception as e:

        try:
            if audio_stream:
                audio_stream.close()
        except Exception:
            pass

        logger.error(
            "/say voice failed: "
            + _redact(str(e))
        )

        await interaction.followup.send(
            "❌ TTS failed: "
            + _redact(str(e))[:300]
        )


@client.tree.command(
    name="leave",
    description="Leave the voice channel"
)
async def leave(
    interaction: discord.Interaction
):

    if not await ensure_not_banned(
        interaction
    ):
        return

    if interaction.guild.voice_client:

        await interaction.guild.voice_client.disconnect()

        await interaction.response.send_message(
            "👋 Disconnected from the voice channel."
        )

    else:

        await interaction.response.send_message(
            "⚠️ I am not in a voice channel.",
            ephemeral=True
        )


if __name__ == "__main__":
    client.run(
        DISCORD_BOT_TOKEN
    )
