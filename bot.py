import os
import re
import io
import asyncio
import tempfile
import base64
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
import discord
import fal_client

from discord import app_commands, File
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from groq import Groq
from fal_client import FalClientHTTPError

from memory import Memory
from ai_engine import AIEngine
from market import get_price, analyze_market
from voice import speak


# ==========================================================
# 👑 KING ZARRY AI - DISCORD BOT
# AI + VISION + VOICE + VIDEO + TRADING + ADMIN + PREMIUM
# ==========================================================

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Your server and Discord account
DISCORD_GUILD_ID = int(
    os.getenv("DISCORD_GUILD_ID", "1537104053207568394")
)
DISCORD_ADMIN_ID = int(
    os.getenv("DISCORD_ADMIN_ID", "1404253218808139807")
)

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "king_zarry_memory.db"
)

# AI / Voice / Video
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_flash_v2_5"
)
ELEVENLABS_VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "21m00Tcm4TlvDq8ikWAM"
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")

GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "qwen/qwen3.6-27b"
)
GROQ_TEXT_MODEL = os.getenv(
    "GROQ_TEXT_MODEL",
    "llama-3.3-70b-versatile"
)

TEXT_TO_VIDEO_MODEL = os.getenv(
    "TEXT_TO_VIDEO_MODEL",
    "fal-ai/ltx-video"
)
IMAGE_TO_VIDEO_MODEL = os.getenv(
    "IMAGE_TO_VIDEO_MODEL",
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

# Premium plans. These are admin-managed subscriptions.
PREMIUM_PLANS = {
    "monthly": {
        "days": 30,
        "price": "250 XTR",
    },
    "3month": {
        "days": 90,
        "price": "600 XTR",
    },
    "yearly": {
        "days": 365,
        "price": "2000 XTR",
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


# ==========================================================
# STARTUP / CONFIG
# ==========================================================

print()
print("=" * 60)
print("👑 KING ZARRY AI DISCORD")
print("=" * 60)

print(
    "🔑 Discord token:",
    "FOUND" if DISCORD_BOT_TOKEN else "MISSING"
)
print(
    "👑 Admin ID:",
    DISCORD_ADMIN_ID
)
print(
    "🏠 Guild ID:",
    DISCORD_GUILD_ID
)
print(
    "🎙️ ElevenLabs API Key:",
    "FOUND" if ELEVENLABS_API_KEY else "MISSING"
)
print(
    "🧠 Groq API Key:",
    "FOUND" if GROQ_API_KEY else "MISSING"
)
print(
    "🎬 Fal.ai Key:",
    "FOUND" if FAL_KEY else "MISSING"
)
print(
    "💾 Database:",
    DATABASE_PATH
)
print("=" * 60)

if not DISCORD_BOT_TOKEN:
    raise RuntimeError(
        "❌ DISCORD_BOT_TOKEN is missing from environment variables."
    )


# ==========================================================
# API CLIENTS
# ==========================================================

eleven_client = (
    ElevenLabs(api_key=ELEVENLABS_API_KEY)
    if ELEVENLABS_API_KEY
    else None
)

groq_client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY
    else None
)


# ==========================================================
# MEMORY + AI ENGINE
# ==========================================================

memory = Memory(DATABASE_PATH)
ai = AIEngine(memory)


# ==========================================================
# SUBSCRIPTION DATABASE
# ==========================================================

db_lock = asyncio.Lock()


def db_connect():
    conn = sqlite3.connect(DATABASE_PATH)
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
            (username, now, str(user_id))
        )
    else:
        conn.execute(
            """
            INSERT INTO discord_users
            (user_id, username, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            """,
            (str(user_id), username, now, now)
        )

    conn.commit()
    conn.close()


def get_subscription_sync(user_id: int):
    conn = db_connect()
    row = conn.execute(
        """
        SELECT user_id, plan, expires_at, granted_by, created_at
        FROM discord_subscriptions
        WHERE user_id = ?
        """,
        (str(user_id),)
    ).fetchone()
    conn.close()

    if not row:
        return None

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except Exception:
        return None

    if expires <= utc_now():
        conn = db_connect()
        conn.execute(
            "DELETE FROM discord_subscriptions WHERE user_id = ?",
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
            f"Unknown plan. Choose: {', '.join(PREMIUM_PLANS)}"
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

    expires = start + timedelta(
        days=PREMIUM_PLANS[plan]["days"]
    )

    conn = db_connect()
    conn.execute(
        """
        INSERT INTO discord_subscriptions
        (user_id, plan, expires_at, granted_by, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            plan = excluded.plan,
            expires_at = excluded.expires_at,
            granted_by = excluded.granted_by,
            created_at = excluded.created_at
        """,
        (
            str(user_id),
            plan,
            expires.isoformat(),
            str(granted_by),
            now.isoformat(),
        )
    )
    conn.commit()
    conn.close()

    return expires


def revoke_subscription_sync(user_id: int):
    conn = db_connect()
    cur = conn.execute(
        "DELETE FROM discord_subscriptions WHERE user_id = ?",
        (str(user_id),)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def is_banned_sync(user_id: int):
    conn = db_connect()
    row = conn.execute(
        "SELECT user_id FROM discord_bans WHERE user_id = ?",
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
        (user_id, reason, banned_by, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            reason = excluded.reason,
            banned_by = excluded.banned_by,
            created_at = excluded.created_at
        """,
        (
            str(user_id),
            reason,
            str(banned_by),
            iso_now(),
        )
    )
    conn.commit()
    conn.close()


def unban_user_sync(user_id: int):
    conn = db_connect()
    cur = conn.execute(
        "DELETE FROM discord_bans WHERE user_id = ?",
        (str(user_id),)
    )
    conn.commit()
    removed = cur.rowcount > 0
    conn.close()
    return removed


def get_user_count_sync():
    conn = db_connect()
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM discord_users"
    ).fetchone()
    conn.close()
    return int(row["count"])


def get_premium_count_sync():
    conn = db_connect()
    rows = conn.execute(
        "SELECT user_id, expires_at FROM discord_subscriptions"
    ).fetchall()
    conn.close()

    now = utc_now()
    count = 0

    for row in rows:
        try:
            if datetime.fromisoformat(row["expires_at"]) > now:
                count += 1
        except Exception:
            pass

    return count


def get_banned_count_sync():
    conn = db_connect()
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM discord_bans"
    ).fetchone()
    conn.close()
    return int(row["count"])


def get_all_user_ids_sync():
    conn = db_connect()
    rows = conn.execute(
        "SELECT user_id FROM discord_users"
    ).fetchall()
    conn.close()

    return [int(row["user_id"]) for row in rows]


init_subscription_db()


# ==========================================================
# ADMIN / ACCESS HELPERS
# ==========================================================

def is_admin(user: discord.abc.User) -> bool:
    return user.id == DISCORD_ADMIN_ID


async def require_admin(interaction: discord.Interaction) -> bool:
    if not is_admin(interaction.user):
        if interaction.response.is_done():
            await interaction.followup.send(
                "⛔ **Admin only.**",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⛔ **Admin only.**",
                ephemeral=True
            )
        return False

    return True


async def user_is_banned(user_id: int) -> bool:
    return await asyncio.to_thread(
        is_banned_sync,
        user_id
    )


async def track_user(user: discord.abc.User):
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


# ==========================================================
# VOICE
# ==========================================================

def generate_elevenlabs_voice(text: str) -> io.BytesIO:
    if not eleven_client:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not configured."
        )

    try:
        audio_generator = (
            eleven_client.text_to_speech.convert(
                text=text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id=ELEVENLABS_MODEL_ID,
                output_format="mp3_44100_128",
            )
        )

        audio_bytes = b"".join(
            chunk for chunk in audio_generator
        )

    except Exception as e:
        raise RuntimeError(
            f"ElevenLabs generation failed: {e}"
        )

    audio_io = io.BytesIO(audio_bytes)
    audio_io.seek(0)
    return audio_io


async def play_voice_in_channel(
    voice_client: discord.VoiceClient,
    text: str
):
    try:
        audio_stream = await asyncio.to_thread(
            generate_elevenlabs_voice,
            text
        )

        audio_source = discord.FFmpegPCMAudio(
            audio_stream,
            pipe=True
        )

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(
            audio_source,
            after=lambda e: print(
                f"🎙️ Finished playing voice: {e}"
            ) if e else None
        )

    except Exception as e:
        print(
            "⚠️ ElevenLabs voice error, "
            f"falling back: {e}"
        )
        await speak(voice_client, text)


# ==========================================================
# MARKET HELPERS
# ==========================================================

def detect_market_and_timeframe(text: str):
    upper = text.upper()

    symbol = "UNKNOWN"

    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "GOLD"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"],
        "EUR/USD": ["EUR/USD", "EURUSD"],
        "GBP/USD": ["GBP/USD", "GBPUSD"],
    }

    for market_symbol, names in markets.items():
        if any(name in upper for name in names):
            symbol = market_symbol
            break

    match = re.search(
        r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b",
        text.lower()
    )

    timeframe = match.group(1) if match else "15m"

    return symbol, timeframe


def build_chart_prompt(symbol: str, timeframe: str):
    return f"""
Analyze this trading chart screenshot.

Market: {symbol}
Timeframe: {timeframe}

Only use information actually visible in the image.

Inspect and summarize:
1. Overall trend and market structure
2. Support and resistance
3. Candlestick patterns
4. EMA/RSI indicators if visible
5. Possible BUY or SELL setup
6. Entry, invalidation/stop loss and take-profit areas

Do not claim certainty or guaranteed profit.
Format the answer clearly.
"""


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def format_market(data: dict, title: str):
    symbol = data.get("symbol", "UNKNOWN")
    timeframe = data.get("timeframe", "15m")
    signal = data.get("signal", "NEUTRAL")
    trend = data.get("trend", "NEUTRAL")

    price = safe_float(data.get("price"))
    support = safe_float(data.get("support"))
    resistance = safe_float(data.get("resistance"))
    ema9 = safe_float(data.get("ema9"))
    ema21 = safe_float(data.get("ema21"))
    ema50 = safe_float(data.get("ema50"))
    rsi = safe_float(data.get("rsi"))

    stop_loss = safe_float(data.get("stop_loss"))
    tp1 = safe_float(data.get("tp1"))
    tp2 = safe_float(data.get("tp2"))

    return (
        f"👑 **{title}**\n\n"
        f"📊 Market: **{symbol}**\n"
        f"⏱ Timeframe: **{timeframe}**\n\n"
        f"🎯 Signal: **{signal}**\n"
        f"📈 Trend: **{trend}**\n\n"
        f"💰 Price: `${price:,.5f}`\n\n"
        f"🔴 Stop Loss: `${stop_loss:,.5f}`\n"
        f"🎯 TP 1: `${tp1:,.5f}`\n"
        f"🎯 TP 2: `${tp2:,.5f}`\n\n"
        f"🟢 Support: `${support:,.5f}`\n"
        f"🔴 Resistance: `${resistance:,.5f}`\n\n"
        f"EMA 9: `${ema9:,.5f}`\n"
        f"EMA 21: `${ema21:,.5f}`\n"
        f"EMA 50: `${ema50:,.5f}`\n"
        f"RSI: **{rsi:.2f}**\n\n"
        "⚠️ Educational analysis only. "
        "No guaranteed profit."
    )


# ==========================================================
# VIDEO HELPERS
# ==========================================================

def enhance_text_prompt(user_prompt: str) -> str:
    if not groq_client:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    system_prompt = """
You are King Zarry's professional cinematic AI video
prompt engineer.

Convert the user's simple idea into ONE detailed,
high-quality video generation prompt.

Include:
subject, environment, action, camera movement,
lighting, atmosphere, cinematic style, realistic motion,
composition.

Return ONLY the final prompt.
Keep it under 1200 characters.
"""

    completion = groq_client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            },
        ],
        temperature=0.7,
        max_tokens=500,
    )

    result = completion.choices[0].message.content

    if not result:
        raise RuntimeError(
            "Groq returned an empty prompt."
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

    system_prompt = """
You are King Zarry's professional image-to-video
prompt engineer.

Analyze the supplied image and requested motion.
Create ONE cinematic image-to-video prompt.

Preserve subject identities, faces, clothing,
objects and overall composition while adding natural
movement.

Return ONLY the final prompt under 1200 characters.
"""

    user_content = [
        {
            "type": "text",
            "text": (
                "User's requested motion:\n"
                + motion_prompt
            ),
        },
        {
            "type": "image_url",
            "image_url": {
                "url": data_url
            },
        },
    ]

    completion = groq_client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            },
        ],
        temperature=0.6,
        max_tokens=600,
    )

    result = completion.choices[0].message.content

    if not result:
        raise RuntimeError(
            "Groq returned an empty image prompt."
        )

    return result.strip()


def generate_text_video(prompt: str) -> bytes:
    if not FAL_KEY:
        raise RuntimeError(
            "FAL_KEY is not configured."
        )

    # fal_client reads FAL_KEY from the environment.
    result = fal_client.subscribe(
        TEXT_TO_VIDEO_MODEL,
        arguments={
            "prompt": prompt
        }
    )

    video_url = (
        result.get("video", {})
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
            "prompt": prompt,
        }
    )

    video_url = (
        result.get("video", {})
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


# ==========================================================
# DISCORD CLIENT
# ==========================================================

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
                f"✅ Synced {len(synced)} commands "
                f"to guild {DISCORD_GUILD_ID}."
            )

        except Exception as e:
            print(
                "❌ COMMAND SYNC ERROR:",
                repr(e)
            )

    async def on_ready(self):
        print()
        print("=" * 60)
        print("👑 KING ZARRY AI IS ONLINE")
        print("=" * 60)
        print(f"🤖 Logged in as: {self.user}")
        print(f"🆔 Bot ID: {self.user.id}")
        print(f"👑 Admin ID: {DISCORD_ADMIN_ID}")
        print(f"🏠 Guild ID: {DISCORD_GUILD_ID}")
        print("💬 Normal messages: ENABLED (Message Content Intent)")
        print("📸 Vision: ENABLED")
        print("🧠 Memory: ENABLED")
        print("📊 Market analysis: ENABLED")
        print(
            "🎙️ ElevenLabs:",
            "ENABLED" if eleven_client else "DISABLED"
        )
        print(
            "🎬 Fal.ai:",
            "ENABLED" if FAL_KEY else "DISABLED"
        )
        print("⭐ Premium system: ENABLED")
        print("🛡️ Admin panel: ENABLED")
        print("=" * 60)
        print("🚀 KING ZARRY AI READY")
        print("=" * 60)
        print()

    async def on_message(
        self,
        message: discord.Message
    ):
        if message.author.bot:
            return

        if await user_is_banned(message.author.id):
            return

        await track_user(message.author)

        content = message.content.strip()

        if self.user:
            content = content.replace(
                f"<@{self.user.id}>",
                ""
            )
            content = content.replace(
                f"<@!{self.user.id}>",
                ""
            )
            content = content.strip()

        images = [
            attachment
            for attachment in message.attachments
            if (
                attachment.content_type
                and attachment.content_type.startswith(
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
                        symbol != "UNKNOWN"
                        or any(
                            kw in content.upper()
                            for kw in [
                                "CHART",
                                "SIGNAL",
                                "ANALYSIS",
                            ]
                        )
                    ):
                        content = build_chart_prompt(
                            symbol,
                            timeframe
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
                "audio",
            ]

            wants_voice = any(
                trigger in content.lower()
                for trigger in voice_triggers
            )

            voice_file = None

            if wants_voice and eleven_client:
                try:
                    audio_fp = await asyncio.to_thread(
                        generate_elevenlabs_voice,
                        answer
                    )

                    voice_file = File(
                        fp=audio_fp,
                        filename="king_zarry_voice.mp3"
                    )

                except Exception as voice_error:
                    print(
                        "⚠️ Voice generation error:",
                        voice_error
                    )

            if voice_file:
                await message.reply(
                    content=answer,
                    file=voice_file,
                    mention_author=False
                )
            else:
                await send_chunks(
                    message,
                    answer
                )

        except Exception as e:
            print(
                "\n❌ AI MESSAGE ERROR:",
                repr(e),
                "\n"
            )

            try:
                await message.reply(
                    "❌ **King Zarry AI error**\n\n"
                    f"`{str(e)[:1500]}`",
                    mention_author=False
                )
            except Exception as reply_error:
                print(
                    "❌ Could not send error reply:",
                    repr(reply_error)
                )


client = KingZarryAI()


# ==========================================================
# MESSAGE HELPERS
# ==========================================================

async def send_chunks(destination, text: str):
    if not text:
        text = (
            "❌ King Zarry AI returned "
            "an empty response."
        )

    chunks = [
        text[i:i + 1900]
        for i in range(0, len(text), 1900)
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
        for i in range(0, len(text), 1900)
    ]

    for chunk in chunks:
        await interaction.followup.send(
            chunk
        )


# ==========================================================
# BASIC COMMANDS
# ==========================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(interaction: discord.Interaction):

    if await user_is_banned(interaction.user.id):
        await interaction.response.send_message(
            "⛔ You are banned from King Zarry AI.",
            ephemeral=True
        )
        return

    await track_user(interaction.user)

    await interaction.response.send_message(
        "👑 **KING ZARRY AI IS ONLINE**\n\n"
        "🧠 AI Agent\n"
        "📊 Market Intelligence\n"
        "📸 Vision\n"
        "💾 Memory\n"
        "🎙️ Voice\n"
        "🎬 Video Generation\n"
        "⭐ Premium System\n\n"
        "**COMMANDS**\n"
        "`/ask` Ask the AI\n"
        "`/voice` AI voice response\n"
        "`/textvideo` Text → Video\n"
        "`/imagevideo` Image → Video\n"
        "`/btc` Bitcoin analysis\n"
        "`/gold` Gold analysis\n"
        "`/crypto` Crypto prices\n"
        "`/analyze` Market analysis\n"
        "`/premium` Premium status\n"
        "`/clear_memory` Clear memory\n"
        "`/join` Join voice\n"
        "`/say` Speak in voice\n"
        "`/leave` Leave voice\n"
        "`/ping` Bot status"
    )


@client.tree.command(
    name="ping",
    description="Check King Zarry AI status"
)
async def ping(interaction: discord.Interaction):
    await track_user(interaction.user)

    await interaction.response.send_message(
        "👑 **King Zarry AI is online!**\n"
        "🧠 AI: Connected\n"
        "📸 Vision: Connected\n"
        "🎬 Fal.ai: "
        + ("Connected" if FAL_KEY else "Not configured")
        + "\n🎙️ Voice: "
        + ("Connected" if eleven_client else "Not configured")
        + "\n⭐ Premium: Connected"
    )


# ==========================================================
# PREMIUM
# ==========================================================

@client.tree.command(
    name="premium",
    description="Check or manage King Zarry AI Premium"
)
@app_commands.describe(
    user="Admin: user to grant/revoke",
    plan="Admin: monthly, 3month, yearly, or revoke"
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
    plan: Optional[app_commands.Choice[str]] = None
):
    await track_user(interaction.user)

    # Normal user: show own premium status
    if user is None and plan is None:
        subscription = await asyncio.to_thread(
            get_subscription_sync,
            interaction.user.id
        )

        if not subscription:
            await interaction.response.send_message(
                "⭐ **KING ZARRY PREMIUM**\n\n"
                "You do not currently have an active "
                "Premium subscription.\n\n"
                "Available plans:\n"
                "• Monthly: **250 XTR / 30 days**\n"
                "• 3 Months: **600 XTR / 90 days**\n"
                "• Yearly: **2000 XTR / 365 days**\n\n"
                "Contact the administrator to activate "
                "your subscription.",
                ephemeral=True
            )
            return

        expires = datetime.fromisoformat(
            subscription["expires_at"]
        )

        await interaction.response.send_message(
            "⭐ **KING ZARRY PREMIUM**\n\n"
            f"Plan: **{subscription['plan']}**\n"
            f"Expires: **{expires:%Y-%m-%d %H:%M UTC}**\n\n"
            "✅ Premium is active.",
            ephemeral=True
        )
        return

    # Management requires admin
    if not await require_admin(interaction):
        return

    if user is None or plan is None:
        await interaction.response.send_message(
            "❌ Admin usage: `/premium @user monthly`",
            ephemeral=True
        )
        return

    if plan.value == "revoke":
        removed = await asyncio.to_thread(
            revoke_subscription_sync,
            user.id
        )

        await interaction.response.send_message(
            (
                f"🗑️ Premium revoked for {user.mention}."
                if removed
                else f"ℹ️ {user.mention} had no active Premium."
            ),
            ephemeral=True
        )
        return

    expires = await asyncio.to_thread(
        grant_subscription_sync,
        user.id,
        plan.value,
        interaction.user.id
    )

    await interaction.response.send_message(
        "⭐ **PREMIUM ACTIVATED**\n\n"
        f"👤 User: {user.mention}\n"
        f"📦 Plan: **{plan.value}**\n"
        f"💳 Price: **{PREMIUM_PLANS[plan.value]['price']}**\n"
        f"📅 Expires: **{expires:%Y-%m-%d %H:%M UTC}**",
        ephemeral=True
    )

    try:
        await user.send(
            "👑 **KING ZARRY AI PREMIUM ACTIVATED!**\n\n"
            f"⭐ Plan: **{plan.value}**\n"
            f"📅 Expires: **{expires:%Y-%m-%d %H:%M UTC}**\n\n"
            "Your Premium access is now active."
        )
    except discord.HTTPException:
        pass


# ==========================================================
# ADMIN PANEL
# ==========================================================

@client.tree.command(
    name="admin",
    description="Open the King Zarry AI admin panel"
)
async def admin(interaction: discord.Interaction):

    if not await require_admin(interaction):
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

    embed = discord.Embed(
        title="👑 KING ZARRY AI ADMIN PANEL",
        description=(
            "🛡️ **Administrator access confirmed.**"
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


# ==========================================================
# /USERS
# ==========================================================

@client.tree.command(
    name="users",
    description="View King Zarry AI user statistics"
)
async def users(interaction: discord.Interaction):

    if not await require_admin(interaction):
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
        f"⭐ Active Premium users: **{premium_users}**\n"
        f"⛔ Banned users: **{banned}**\n"
        f"🏠 Guilds: **{len(client.guilds)}**",
        ephemeral=True
    )


# ==========================================================
# /BAN
# ==========================================================

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

    if not await require_admin(interaction):
        return

    if user.id == DISCORD_ADMIN_ID:
        await interaction.response.send_message(
            "❌ You cannot ban the configured administrator.",
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
        "⛔ **USER BANNED FROM KING ZARRY AI**\n\n"
        f"👤 User: {user.mention}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📝 Reason: {reason}",
        ephemeral=True
    )

    try:
        await user.send(
            "⛔ You have been banned from "
            "King Zarry AI.\n\n"
            f"Reason: {reason}"
        )
    except discord.HTTPException:
        pass


# ==========================================================
# /UNBAN
# ==========================================================

@client.tree.command(
    name="unban",
    description="Remove a King Zarry AI application ban"
)
@app_commands.describe(
    user_id="Discord user ID to unban"
)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):

    if not await require_admin(interaction):
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

    if removed:
        await interaction.response.send_message(
            f"✅ User `{target_id}` has been unbanned.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ User `{target_id}` was not banned.",
            ephemeral=True
        )


# ==========================================================
# /BROADCAST
# ==========================================================

@client.tree.command(
    name="broadcast",
    description="Broadcast a message to tracked King Zarry users"
)
@app_commands.describe(
    message="Message to send to users"
)
async def broadcast(
    interaction: discord.Interaction,
    message: str
):

    if not await require_admin(interaction):
        return

    if len(message) > 1900:
        await interaction.response.send_message(
            "❌ Broadcast must be 1900 characters or less.",
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
            user = client.get_user(user_id)

            if user is None:
                user = await client.fetch_user(
                    user_id
                )

            if await user_is_banned(user_id):
                continue

            await user.send(
                "👑 **KING ZARRY AI ANNOUNCEMENT**\n\n"
                + message
            )

            sent += 1

            # Prevent an aggressive burst of DMs.
            await asyncio.sleep(0.5)

        except Exception as e:
            print(
                f"⚠️ Broadcast failed for {user_id}: {e}"
            )
            failed += 1

    await interaction.followup.send(
        "📢 **BROADCAST COMPLETE**\n\n"
        f"✅ Sent: **{sent}**\n"
        f"❌ Failed: **{failed}**\n"
        f"👥 Tracked: **{len(user_ids)}**",
        ephemeral=True
    )


# ==========================================================
# /ASK
# ==========================================================

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

    if await user_is_banned(interaction.user.id):
        await interaction.response.send_message(
            "⛔ You are banned from King Zarry AI.",
            ephemeral=True
        )
        return

    await track_user(interaction.user)
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
        print("❌ /ask ERROR:", repr(e))
        await interaction.followup.send(
            f"❌ AI error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /VOICE
# ==========================================================

@client.tree.command(
    name="voice",
    description="Ask King Zarry AI and receive voice"
)
@app_commands.describe(
    question="Your question"
)
async def voice_command(
    interaction: discord.Interaction,
    question: str
):

    if await user_is_banned(interaction.user.id):
        await interaction.response.send_message(
            "⛔ You are banned.",
            ephemeral=True
        )
        return

    await track_user(interaction.user)
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

        if eleven_client:
            audio_fp = await asyncio.to_thread(
                generate_elevenlabs_voice,
                answer
            )

            discord_file = File(
                fp=audio_fp,
                filename="king_zarry_voice.mp3"
            )

            await interaction.followup.send(
                content=(
                    "🗣️ **King Zarry AI:**\n"
                    + answer
                ),
                file=discord_file
            )
        else:
            await interaction.followup.send(
                "🗣️ **King Zarry AI:**\n"
                + answer
                + "\n\n"
                "⚠️ Voice is not configured."
            )

    except Exception as e:
        print(
            "❌ /voice ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Voice error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /TEXTVIDEO
# ==========================================================

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

    if len(prompt.strip()) == 0:
        await interaction.response.send_message(
            "❌ Please provide a prompt.",
            ephemeral=True
        )
        return

    if len(prompt) > MAX_PROMPT_LENGTH:
        await interaction.response.send_message(
            f"❌ Prompt too long. Max {MAX_PROMPT_LENGTH} characters.",
            ephemeral=True
        )
        return

    await track_user(interaction.user)
    await interaction.response.defer()

    status_msg = await interaction.followup.send(
        "🧠 **Enhancing your video prompt...**"
    )

    video_path = None

    try:
        enhanced_prompt = await asyncio.to_thread(
            enhance_text_prompt,
            prompt.strip()
        )

        await status_msg.edit(
            content=(
                "🎬 **Generating video with Fal.ai...**\n"
                "⏳ Please wait."
            )
        )

        video_bytes = await asyncio.to_thread(
            generate_text_video,
            enhanced_prompt
        )

        if len(video_bytes) > MAX_VIDEO_SIZE:
            await status_msg.edit(
                content=(
                    "⚠️ Generated video exceeds the "
                    "configured Discord upload limit."
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

        embed = discord.Embed(
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

    except FalClientHTTPError as err:

        if (
            getattr(err, "status_code", None) == 403
            or "Exhausted balance" in str(err)
        ):
            await status_msg.edit(
                content=(
                    "⚠️ Fal.ai balance/quota is exhausted. "
                    "Chat, vision and voice remain available."
                )
            )
        else:
            await status_msg.edit(
                content=(
                    f"❌ Video error: "
                    f"`{str(err)[:800]}`"
                )
            )

    except Exception as error:
        print(
            "❌ Text-to-video error:",
            repr(error)
        )

        await status_msg.edit(
            content=(
                "❌ **Generation failed.**\n"
                f"`{str(error)[:800]}`"
            )
        )

    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


# ==========================================================
# /IMAGEVIDEO
# ==========================================================

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

    if image.content_type not in ALLOWED_VIDEO_IMAGE_TYPES:
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

    await track_user(interaction.user)
    await interaction.response.defer()

    status_msg = await interaction.followup.send(
        "📥 **Downloading and analyzing image...**"
    )

    video_path = None

    try:
        image_bytes = await image.read()

        enhanced_prompt = await asyncio.to_thread(
            enhance_image_prompt,
            image_bytes,
            motion.strip()
        )

        await status_msg.edit(
            content=(
                "🎬 **Generating image-to-video...**\n"
                "⏳ Please wait."
            )
        )

        video_bytes = await asyncio.to_thread(
            generate_image_video,
            image_bytes,
            enhanced_prompt
        )

        if len(video_bytes) > MAX_VIDEO_SIZE:
            await status_msg.edit(
                content=(
                    "⚠️ Generated video exceeds "
                    "the configured limit."
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

        embed = discord.Embed(
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

    except FalClientHTTPError as err:

        if (
            getattr(err, "status_code", None) == 403
            or "Exhausted balance" in str(err)
        ):
            await status_msg.edit(
                content=(
                    "⚠️ Fal.ai quota is exhausted. "
                    "Chat, vision and voice remain available."
                )
            )
        else:
            await status_msg.edit(
                content=(
                    f"❌ Video error: "
                    f"`{str(err)[:800]}`"
                )
            )

    except Exception as error:
        print(
            "❌ Image-to-video error:",
            repr(error)
        )

        await status_msg.edit(
            content=(
                "❌ **Generation failed.**\n"
                f"`{str(error)[:800]}`"
            )
        )

    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


# ==========================================================
# MARKET COMMANDS
# ==========================================================

@client.tree.command(
    name="btc",
    description="Analyze Bitcoin market"
)
@app_commands.describe(
    timeframe="15m, 1h, 4h, etc."
)
async def btc(
    interaction: discord.Interaction,
    timeframe: str = "15m"
):

    await track_user(interaction.user)
    await interaction.response.defer()

    try:
        data = await asyncio.to_thread(
            analyze_market,
            "BTC/USD",
            timeframe
        )

        await interaction.followup.send(
            format_market(
                data,
                "Bitcoin Market Analysis"
            )
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Market analysis failed:\n"
            f"`{str(e)[:1200]}`"
        )


@client.tree.command(
    name="gold",
    description="Analyze Gold market"
)
@app_commands.describe(
    timeframe="15m, 1h, 4h, etc."
)
async def gold(
    interaction: discord.Interaction,
    timeframe: str = "15m"
):

    await track_user(interaction.user)
    await interaction.response.defer()

    try:
        data = await asyncio.to_thread(
            analyze_market,
            "XAU/USD",
            timeframe
        )

        await interaction.followup.send(
            format_market(
                data,
                "Gold Market Analysis"
            )
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Gold analysis failed:\n"
            f"`{str(e)[:1200]}`"
        )


@client.tree.command(
    name="crypto",
    description="Check BTC, ETH and SOL prices"
)
async def crypto(interaction: discord.Interaction):

    await track_user(interaction.user)
    await interaction.response.defer()

    try:
        symbols = [
            "BTC/USD",
            "ETH/USD",
            "SOL/USD"
        ]

        results = []

        for symbol in symbols:
            price = await asyncio.to_thread(
                get_price,
                symbol
            )

            results.append(
                f"**{symbol}**: "
                f"`${safe_float(price):,.2f}`"
            )

        await interaction.followup.send(
            "👑 **CRYPTO PRICES**\n\n"
            + "\n".join(results)
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Price fetch failed:\n"
            f"`{str(e)[:1200]}`"
        )


@client.tree.command(
    name="analyze",
    description="Analyze a custom market"
)
@app_commands.describe(
    symbol="BTC/USD, EUR/USD, XAU/USD, etc.",
    timeframe="15m, 1h, 4h, etc."
)
async def analyze(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15m"
):

    await track_user(interaction.user)
    await interaction.response.defer()

    try:
        data = await asyncio.to_thread(
            analyze_market,
            symbol.upper(),
            timeframe
        )

        await interaction.followup.send(
            format_market(
                data,
                f"{symbol.upper()} Analysis"
            )
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Analysis failed:\n"
            f"`{str(e)[:1200]}`"
        )


# ==========================================================
# MEMORY
# ==========================================================

@client.tree.command(
    name="clear_memory",
    description="Clear your AI conversation memory"
)
async def clear_memory(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    try:
        await asyncio.to_thread(
            memory.clear_history,
            str(interaction.user.id)
        )

        await interaction.followup.send(
            "🧠 Your AI memory has been cleared.",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"❌ Memory error:\n"
            f"`{str(e)[:1200]}`",
            ephemeral=True
        )


# ==========================================================
# VOICE CHANNEL COMMANDS
# ==========================================================

@client.tree.command(
    name="join",
    description="Join your current voice channel"
)
async def join(interaction: discord.Interaction):

    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ Join a voice channel first.",
            ephemeral=True
        )
        return

    channel = interaction.user.voice.channel

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

    await interaction.response.defer()

    voice_client = interaction.guild.voice_client

    if not voice_client:

        if (
            interaction.user.voice
            and interaction.user.voice.channel
        ):
            voice_client = await (
                interaction.user.voice.channel.connect()
            )
        else:
            await interaction.followup.send(
                "❌ Join a voice channel first."
            )
            return

    await interaction.followup.send(
        f"🎙️ **Speaking:** {text}"
    )

    await play_voice_in_channel(
        voice_client,
        text
    )


@client.tree.command(
    name="leave",
    description="Leave the voice channel"
)
async def leave(interaction: discord.Interaction):

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


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
