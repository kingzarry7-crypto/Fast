print("🇳🇬 DISCORDBOT-V3-LOADED 🇳🇬", flush=True)

import os
import re
import io
import sys
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

# Shared personal price alerts (same table as Telegram)
try:
    from price_alerts import (
        normalize_alert_symbol as shared_normalize_symbol,
        parse_alert_request as shared_parse_alert,
        create_price_alert as shared_create_alert,
        get_user_price_alerts as shared_get_alerts,
        cancel_user_alert as shared_cancel_alert,
        cancel_all_user_alerts as shared_cancel_all,
        get_all_active_price_alerts as shared_get_all_active,
        get_current_price_for_alert as shared_get_price,
        check_alert_triggered_v2 as shared_check_triggered,
        ensure_price_alerts_table as shared_ensure_table,
    )
except Exception as e:
    shared_normalize_symbol = None
    shared_parse_alert = None
    shared_create_alert = None
    shared_get_alerts = None
    shared_cancel_alert = None
    shared_cancel_all = None
    shared_get_all_active = None
    shared_get_price = None
    shared_check_triggered = None
    shared_ensure_table = None

load_dotenv()

# ============================================================
# LOGGING — stdout (Railway-safe) + silence noisy libraries
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger("king_zarry_discord")

# STT Engine - shared with Telegram (after logger)
try:
    import stt_engine
    try:
        logger.info(f"🎙️ STT Engine loaded: {stt_engine.provider_status()}")
    except Exception:
        pass
except Exception as e:
    stt_engine = None
    try:
        logger.warning(f"STT Engine import failed: {e}")
    except Exception:
        pass

# Tavily - shared web search (after logger)
try:
    import tavily_search
    try:
        if tavily_search.is_tavily_configured():
            logger.info(f"🌐 Tavily loaded: {tavily_search.provider_status()}")
        else:
            logger.info("ℹ️ Tavily not configured in Discord - continuing without web search")
    except Exception:
        pass
except Exception as e:
    tavily_search = None
    try:
        logger.warning(f"Tavily import failed in Discord: {e}")
    except Exception:
        pass

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.I)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
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
        os.getenv("AGNES_API_KEY"),
    ]
    for secret in secrets_to_redact:
        if secret and len(secret) > 8:
            text = text.replace(secret, secret[:3] + "***REDACTED***")
    return text

DISCORD_BOT_TOKEN = clean_env_str(os.getenv("DISCORD_BOT_TOKEN"))
DISCORD_GUILD_ID = int(clean_env_str(os.getenv("DISCORD_GUILD_ID"), "1537104053207568394") or "1537104053207568394")
DISCORD_ADMIN_ID = int(clean_env_str(os.getenv("DISCORD_ADMIN_ID"), "1404253218808139807") or "1404253218808139807")

# FIX 2: shares king_zarry.db with bot.py so price_alerts updates hit the right table
DATABASE_PATH = clean_env_str(os.getenv("DATABASE_PATH"), "king_zarry.db")
MEMORY_DB_PATH = clean_env_str(os.getenv("MEMORY_DB_PATH"), "king_zarry_memory.db")

ELEVENLABS_API_KEY = clean_env_str(os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = clean_env_str(os.getenv("ELEVENLABS_VOICE_ID"), "hpp4J3VqNfWAUOO0d1Us")
ELEVENLABS_MODEL_ID = clean_env_str(os.getenv("ELEVENLABS_MODEL_ID") or os.getenv("ELEVENLABS_MODEL"), "eleven_v3")

GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
FAL_KEY = clean_env_str(os.getenv("FAL_KEY"))

# FIX 3: valid Groq vision model default
GROQ_VISION_MODEL = clean_env_str(os.getenv("GROQ_VISION_MODEL"), "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_TEXT_MODEL = clean_env_str(os.getenv("GROQ_TEXT_MODEL"), "llama-3.3-70b-versatile")

TEXT_TO_VIDEO_MODEL = clean_env_str(os.getenv("TEXT_TO_VIDEO_MODEL"), "fal-ai/ltx-video")
IMAGE_TO_VIDEO_MODEL = clean_env_str(os.getenv("IMAGE_TO_VIDEO_MODEL"), "fal-ai/ltx-video/image-to-video")

MAX_PROMPT_LENGTH = 1500
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 24 * 1024 * 1024
ALLOWED_VIDEO_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

PREMIUM_PLANS = {
    "monthly": {"days": 30, "price": "250 XTR"},
    "3month": {"days": 90, "price": "600 XTR"},
    "yearly": {"days": 365, "price": "2000 XTR"},
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

# ============================================================
# 🎨 MEDIA REQUEST DETECTION (runs before market intent)
# ============================================================
_MEDIA_VERB_PATTERN = re.compile(
    r"\b("
    r"draw|sketch|render|illustrate|paint|"
    r"generate\s+(?:an?\s+|the\s+|me\s+(?:an?\s+)?)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"create\s+(?:an?\s+|the\s+|me\s+(?:an?\s+)?)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"make\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"animate|"
    r"edit\s+(?:this|the|my)\s+(?:image|photo|picture)|"
    r"remove\s+(?:the\s+)?background|"
    r"make\s+(?:this|it)\s+look|"
    r"turn\s+(?:this|it)\s+into|"
    r"image\s+to\s+video|"
    r"text\s+to\s+video|"
    r"video\s+of|clip\s+of|animation\s+of|"
    r"image\s+of|picture\s+of|photo\s+of|artwork\s+of|art\s+of|portrait\s+of|"
    r"style\s+transfer|"
    r"img2img"
    r")\b",
    re.IGNORECASE,
)

def _looks_like_media_request(text: str) -> bool:
    if not text:
        return False
    return bool(_MEDIA_VERB_PATTERN.search(text))

# ============================================================
# FIX 4: Enhanced boot log (Agnes + AceData + GDELT + CryptoVision)
# ============================================================
print("\n" + "="*60, flush=True)
print("👑 KING ZARRY AI DISCORD - UPGRADED MTF + NEWS + AGNES MEDIA EDITION", flush=True)
print("="*60, flush=True)
print(f"🔑 Discord token: {'FOUND' if DISCORD_BOT_TOKEN else 'MISSING'}", flush=True)
print(f"🎙️ ElevenLabs: {'ENABLED' if ELEVENLABS_API_KEY else 'MISSING'}", flush=True)
print(f"🧠 Groq: {'FOUND' if GROQ_API_KEY else 'MISSING'}", flush=True)
print(f"🎬 Fal.ai: {'FOUND' if FAL_KEY else 'MISSING'}", flush=True)

try:
    from ai_engine import (
        AGNES_API_KEY as _AGNES_KEY,
        AGNES_IMAGE_MODEL as _AGNES_IMG,
        AGNES_VIDEO_MODEL as _AGNES_VID,
        ACEDATA_API_KEY as _ACEDATA_KEY,
        ACEDATA_IMAGE_MODEL as _ACEDATA_IMG,
        ACEDATA_VIDEO_MODEL as _ACEDATA_VID,
    )
    if _AGNES_KEY:
        print(f"🎨 Agnes AI (primary): ENABLED | image={_AGNES_IMG} video={_AGNES_VID}", flush=True)
    else:
        print("🎨 Agnes AI (primary): DISABLED (set AGNES_API_KEY)", flush=True)
    if _ACEDATA_KEY:
        print(f"🎬 AceData Cloud (fallback): ENABLED | image={_ACEDATA_IMG} video={_ACEDATA_VID}", flush=True)
    else:
        print("🎬 AceData Cloud (fallback): DISABLED (set ACEDATA_API_KEY)", flush=True)
except Exception as _e:
    print(f"ℹ️ Media provider status skipped: {_e}", flush=True)

try:
    from ai_engine import GDELT_DOC_API_URL as _GDELT_URL, CRYPTOVISION_BASE_URL as _CV_URL
    print(f"🌍 GDELT 2.0 DOC API: ENABLED | {_GDELT_URL}", flush=True)
    print(f"📰 Crypto Vision: ENABLED | {_CV_URL}", flush=True)
except Exception as _e:
    print(f"ℹ️ Intel provider status skipped: {_e}", flush=True)

print(f"💾 DB: {DATABASE_PATH}", flush=True)
print(f"🧠 Memory DB: {MEMORY_DB_PATH}", flush=True)
print("="*60 + "\n", flush=True)

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN missing")

try:
    from elevenlabs.client import ElevenLabs
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
except Exception as e:
    logger.warning(f"ElevenLabs init failed: {_redact(str(e))}")
    eleven_client = None

try:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception:
    groq_client = None

memory = Memory(MEMORY_DB_PATH)
ai = AIEngine(memory)

def db_connect():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_subscription_db():
    conn = db_connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS discord_users (user_id TEXT PRIMARY KEY, username TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS discord_subscriptions (user_id TEXT PRIMARY KEY, plan TEXT NOT NULL, expires_at TEXT NOT NULL, granted_by TEXT NOT NULL, created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS discord_bans (user_id TEXT PRIMARY KEY, reason TEXT, banned_by TEXT NOT NULL, created_at TEXT NOT NULL)""")
    conn.commit()
    conn.close()

def utc_now():
    return datetime.now(timezone.utc)

def iso_now():
    return utc_now().isoformat()

def remember_user_sync(user_id: int, username: str):
    now = iso_now()
    conn = db_connect()
    row = conn.execute("SELECT user_id FROM discord_users WHERE user_id = ?", (str(user_id),)).fetchone()
    if row:
        conn.execute("UPDATE discord_users SET username = ?, last_seen = ? WHERE user_id = ?", (username, now, str(user_id)))
    else:
        conn.execute("INSERT INTO discord_users (user_id, username, first_seen, last_seen) VALUES (?, ?, ?, ?)", (str(user_id), username, now, now))
    conn.commit()
    conn.close()

def get_subscription_sync(user_id: int):
    conn = db_connect()
    row = conn.execute("SELECT user_id, plan, expires_at, granted_by, created_at FROM discord_subscriptions WHERE user_id = ?", (str(user_id),)).fetchone()
    conn.close()
    if not row:
        return None
    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except Exception:
        return None
    if expires <= utc_now():
        conn = db_connect()
        conn.execute("DELETE FROM discord_subscriptions WHERE user_id = ?", (str(user_id),))
        conn.commit()
        conn.close()
        return None
    return dict(row)

def grant_subscription_sync(user_id: int, plan: str, granted_by: int):
    plan = plan.lower()
    if plan not in PREMIUM_PLANS:
        raise ValueError(f"Unknown plan. Choose: {', '.join(PREMIUM_PLANS)}")
    current = get_subscription_sync(user_id)
    now = utc_now()
    if current:
        try:
            current_expiry = datetime.fromisoformat(current["expires_at"])
            start = max(now, current_expiry)
        except Exception:
            start = now
    else:
        start = now
    expires = start + timedelta(days=PREMIUM_PLANS[plan]["days"])
    conn = db_connect()
    conn.execute("""INSERT INTO discord_subscriptions (user_id, plan, expires_at, granted_by, created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET plan=excluded.plan, expires_at=excluded.expires_at, granted_by=excluded.granted_by, created_at=excluded.created_at""",
                 (str(user_id), plan, expires.isoformat(), str(granted_by), now.isoformat()))
    conn.commit()
    conn.close()
    return expires

def revoke_subscription_sync(user_id: int):
    conn = db_connect()
    cur = conn.execute("DELETE FROM discord_subscriptions WHERE user_id = ?", (str(user_id),))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def is_banned_sync(user_id: int):
    conn = db_connect()
    row = conn.execute("SELECT user_id FROM discord_bans WHERE user_id = ?", (str(user_id),)).fetchone()
    conn.close()
    return row is not None

def ban_user_sync(user_id: int, reason: str, banned_by: int):
    conn = db_connect()
    conn.execute("""INSERT INTO discord_bans (user_id, reason, banned_by, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason, banned_by=excluded.banned_by, created_at=excluded.created_at""",
                 (str(user_id), reason, str(banned_by), iso_now()))
    conn.commit()
    conn.close()

def unban_user_sync(user_id: int):
    conn = db_connect()
    cur = conn.execute("DELETE FROM discord_bans WHERE user_id = ?", (str(user_id),))
    conn.commit()
    removed = cur.rowcount > 0
    conn.close()
    return removed

def get_user_count_sync():
    conn = db_connect()
    row = conn.execute("SELECT COUNT(*) AS count FROM discord_users").fetchone()
    conn.close()
    return int(row["count"])

def get_premium_count_sync():
    conn = db_connect()
    rows = conn.execute("SELECT user_id, expires_at FROM discord_subscriptions").fetchall()
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
    row = conn.execute("SELECT COUNT(*) AS count FROM discord_bans").fetchone()
    conn.close()
    return int(row["count"])

def get_all_user_ids_sync():
    conn = db_connect()
    rows = conn.execute("SELECT user_id FROM discord_users").fetchall()
    conn.close()
    return [int(row["user_id"]) for row in rows]

init_subscription_db()

def is_admin(user: discord.abc.User) -> bool:
    return user.id == DISCORD_ADMIN_ID

async def require_admin(interaction: discord.Interaction) -> bool:
    if not is_admin(interaction.user):
        msg = "⛔ **Admin only.**"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return False
    return True

async def user_is_banned(user_id: int) -> bool:
    return await asyncio.to_thread(is_banned_sync, user_id)

async def ensure_not_banned(interaction: discord.Interaction) -> bool:
    if await user_is_banned(interaction.user.id):
        msg = "⛔ You are banned from King Zarry AI."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return False
    return True

async def track_user(user: discord.abc.User):
    await asyncio.to_thread(remember_user_sync, user.id, str(user))

def generate_elevenlabs_voice(text: str) -> io.BytesIO:
    if not eleven_client:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")
    try:
        logger.info(f"TTS provider: ElevenLabs | TTS model: {_redact(ELEVENLABS_MODEL_ID)}")
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(chunk for chunk in audio_generator)
    except Exception as e:
        raise RuntimeError(f"ElevenLabs generation failed: {_redact(str(e))}")
    audio_io = io.BytesIO(audio_bytes)
    audio_io.seek(0)
    return audio_io

async def generate_edgetts_voice(text: str) -> io.BytesIO:
    temp_dir = None
    try:
        import edge_tts
        temp_dir = tempfile.mkdtemp(prefix="king_zarry_tts_")
        output_file = os.path.join(temp_dir, "voice.mp3")
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(output_file)
        with open(output_file, "rb") as f:
            audio_bytes = f.read()
        audio_io = io.BytesIO(audio_bytes)
        audio_io.seek(0)
        return audio_io
    finally:
        if temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

async def generate_tts_audio(text: str) -> tuple:
    try:
        if eleven_client and ELEVENLABS_API_KEY:
            audio = await asyncio.to_thread(generate_elevenlabs_voice, text)
            return audio, "ElevenLabs"
    except Exception as e:
        logger.warning(f"ElevenLabs TTS failed, trying AriaNeural fallback: {_redact(str(e))}")
    try:
        audio = await generate_edgetts_voice(text)
        return audio, "AriaNeural"
    except Exception as e:
        logger.error(f"EdgeTTS fallback failed: {_redact(str(e))}")
        raise RuntimeError(f"TTS unavailable: {_redact(str(e))}")

def detect_market_and_timeframe(text: str):
    upper = text.upper()
    symbol = "BTC/USD"
    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "GOLD", "XAU"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"],
    }
    for market_symbol, names in markets.items():
        if any(name in upper for name in names):
            symbol = market_symbol
            break
    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", text.lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe

def detect_market_intent_discord(text: str):
    if not text:
        return False, "XAU/USD", "15m"
    upper = text.upper()
    lower = text.lower()
    has_market = any(kw in upper for kw in ["XAU/USD","XAUUSD","XAU","GOLD","BTC/USD","BTCUSDT","BTC","ETH/USD","ETHUSDT","ETH","SOL/USD","SOLUSDT","SOL"])
    if not has_market:
        return False, "XAU/USD", "15m"
    intent_keywords = [
        "analy","signal","trend","check","price","forecast","predict",
        "buy","sell","support","resist","chart","outlook","market",
        "happen","doing","view","status","update","plan",
        "bias","direction","call","setup","entry","sl","tp","target",
        "should i","what about","how is","what is","whats","what's",
        "give me","show me","tell me"
    ]
    is_short_market = len(text.strip()) < 35 and has_market
    has_intent = any(kw in lower for kw in intent_keywords) or is_short_market
    if not has_intent:
        return False, "XAU/USD", "15m"
    symbol, timeframe = detect_market_and_timeframe(text)
    return True, symbol, timeframe

def detect_news_intent_discord(text: str):
    lower = text.lower()
    news_keywords = ["news","headline","event","calendar","economic","happen","what happened","latest"]
    if any(k in lower for k in news_keywords):
        has_market = any(kw in text.upper() for kw in ["BTC","ETH","SOL","XAU","GOLD"])
        if has_market:
            return True
        if "btc news" in lower or "gold news" in lower or "eth news" in lower:
            return True
    return False

def normalize_alert_symbol_discord(raw: str):
    if shared_normalize_symbol:
        try:
            return shared_normalize_symbol(raw)
        except Exception:
            pass
    upper = raw.upper().strip()
    mapping = {"XAU":"XAU/USD","XAUUSD":"XAU/USD","XAU/USD":"XAU/USD","GOLD":"XAU/USD","BTC":"BTC/USD","BTCUSD":"BTC/USD","BTC/USD":"BTC/USD","ETH":"ETH/USD","ETHUSD":"ETH/USD","ETH/USD":"ETH/USD","SOL":"SOL/USD","SOLUSD":"SOL/USD","SOL/USD":"SOL/USD"}
    if upper in mapping:
        return mapping[upper]
    for k,v in mapping.items():
        if k in upper:
            return v
    return None

def parse_alert_request_discord(text: str):
    if shared_parse_alert:
        try:
            return shared_parse_alert(text)
        except Exception:
            pass
    if not text:
        return None
    original = text.strip()
    lower = original.lower()
    cleaned = re.sub(r"^/alert\s*", "", original, flags=re.IGNORECASE).strip()
    price_match = re.findall(r"(\d+(?:\.\d+)?)", cleaned)
    if not price_match:
        return None
    try:
        target_price = float(price_match[-1])
    except:
        return None
    if target_price <= 0:
        return None
    symbol = normalize_alert_symbol_discord(cleaned) or normalize_alert_symbol_discord(original)
    if not symbol:
        return None
    condition = "REACHES"
    if re.search(r"\babove\b|\bgoes above\b", lower):
        condition = "ABOVE" if "below" not in lower or lower.rfind("above") > lower.rfind("below") else "BELOW"
    if re.search(r"\bbelow\b|\bdrops below\b|\bfalls below\b", lower):
        if "above" in lower and "below" in lower:
            condition = "ABOVE" if lower.rfind("above") > lower.rfind("below") else "BELOW"
        else:
            condition = "BELOW"
    cmd_match = re.search(r"(above|below|reaches|reach|hit|hits)", cleaned.lower())
    if cmd_match:
        w = cmd_match.group(1)
        if w == "above": condition = "ABOVE"
        elif w == "below": condition = "BELOW"
        else: condition = "REACHES"
    return {"symbol": symbol, "target_price": target_price, "condition": condition, "raw": original}

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def build_discord_signal_embed(market_data: Dict[str, Any], news_data: Optional[Dict[str, Any]] = None) -> Embed:
    symbol = market_data.get("symbol", "UNKNOWN")
    signal = market_data.get("signal", "WAIT")
    mtf_bias = market_data.get("mtf_bias", market_data.get("trend", "NEUTRAL"))
    mtf_score = market_data.get("mtf_score", market_data.get("strength", 0))
    confidence = market_data.get("confidence", "LOW")
    strength = market_data.get("strength", 0)
    price = safe_float(market_data.get("price") or market_data.get("current_price"))
    entry_low = safe_float(market_data.get("entry_low"))
    entry_high = safe_float(market_data.get("entry_high"))
    stop_loss = safe_float(market_data.get("stop_loss"))
    tp1 = safe_float(market_data.get("tp1"))
    tp2 = safe_float(market_data.get("tp2"))
    tp3 = safe_float(market_data.get("tp3"))
    support = safe_float(market_data.get("support"))
    resistance = safe_float(market_data.get("resistance"))
    rsi = safe_float(market_data.get("rsi"))
    ema9 = safe_float(market_data.get("ema9"))
    ema21 = safe_float(market_data.get("ema21"))
    ema50 = safe_float(market_data.get("ema50"))
    atr = safe_float(market_data.get("atr"))
    structure = market_data.get("structure", "NEUTRAL")
    entry_quality = market_data.get("entry_quality", market_data.get("entry_status", ""))
    reasons = market_data.get("reasons", market_data.get("reason", []))
    if isinstance(reasons, str):
        reasons = [reasons]
    news_risk = market_data.get("news_risk", (news_data.get("risk") if news_data else "LOW"))
    h4_trend = market_data.get("h4_trend", "")
    h1_trend = market_data.get("h1_trend", "")
    m15_trend = market_data.get("m15_trend", "")
    m5_trend = market_data.get("m5_trend", "")
    plan_status = market_data.get("plan_status") or market_data.get("daily_plan_status") or market_data.get("status", "ACTIVE")

    if signal == "BUY":
        color = discord.Color.green()
        emoji = "🟢"
    elif signal == "SELL":
        color = discord.Color.red()
        emoji = "🔴"
    else:
        color = discord.Color.gold()
        emoji = "🟡"

    entry_display = {"EARLY": "🟢 EARLY", "GOOD ENTRY": "🟢 GOOD ENTRY", "ACCEPTABLE": "🟡 ACCEPTABLE", "LATE": "🟠 LATE", "EXTENDED / AVOID": "🔴 EXTENDED / AVOID", "MISSED": "🔴 MISSED", "INVALIDATED": "⚫ INVALIDATED"}.get(entry_quality.upper(), entry_quality) if entry_quality else "UNKNOWN"

    title = f"👑 KING ZARRY AI • {symbol} SIGNAL"
    desc = f"{emoji} **{signal}** | ⏱ Execution: 15M | {entry_display}"

    embed = Embed(title=title, description=desc, color=color)
    embed.add_field(name="📊 MULTI-TIMEFRAME", value=f"4H: {h4_trend or 'NEUTRAL'}\n1H: {h1_trend or 'NEUTRAL'}\n15M: {m15_trend or 'NEUTRAL'}\n5M: {m5_trend or 'NEUTRAL'}", inline=True)
    embed.add_field(name="📈 ASSESSMENT", value=f"🔥 Confidence: {confidence} ({mtf_score}/100)\n💪 Strength: {strength}/100\n🧱 Alignment: {mtf_bias}", inline=True)
    embed.add_field(name="💵 PRICE", value=f"💰 Price: `${price:,.2f}`\n🎯 Entry: `${entry_low:,.2f} - ${entry_high:,.2f}`\n🛑 SL: `${stop_loss:,.2f}`", inline=False)
    embed.add_field(name="🎯 TARGETS", value=f"TP1: `${tp1:,.2f}`\nTP2: `${tp2:,.2f}`\nTP3: `${tp3:,.2f}`\n⚖️ RR: 1:{market_data.get('rr', 3.5)}", inline=True)
    embed.add_field(name="🏗 LEVELS", value=f"Support: `${support:,.2f}`\nResistance: `${resistance:,.2f}`\nStructure: {structure}", inline=True)
    embed.add_field(name="📊 INDICATORS", value=f"RSI: {rsi:.1f}\nEMA9: {ema9:,.2f}\nEMA21: {ema21:,.2f}\nEMA50: {ema50:,.2f}\nATR: {atr:,.2f}", inline=True)
    news_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "EXTREME": "🔴"}.get(news_risk, "⚪")
    news_val = f"{news_emoji} {news_risk}"
    if news_data and news_data.get("events"):
        news_val += f"\n📅 {len(news_data['events'])} events 24H"
    embed.add_field(name="📰 NEWS RISK", value=news_val, inline=True)
    embed.add_field(name="🟢 ENTRY STATUS", value=entry_display, inline=True)
    if reasons:
        embed.add_field(name="🧠 Why", value="\n".join(f"{i+1}. {r}" for i, r in enumerate(reasons[:5]))[:1024], inline=False)
    embed.set_footer(text="⚠️ Multi-timeframe analysis. Not financial advice.")
    return embed

def build_discord_signal_chart(symbol: str, timeframe: str, market_data: Dict[str, Any]):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, FancyArrowPatch
        from io import BytesIO

        candles = None
        try:
            candles = market_engine.get_candles(symbol, timeframe, 100)
        except Exception:
            try:
                candles = market_engine.get_candles(symbol, "15m", 100)
            except Exception as ce:
                logger.warning(f"Discord chart: candle fetch failed {symbol}: {_redact(str(ce))}")
                return None

        if not candles or len(candles) < 10:
            return None

        cc = candles[-70:]
        o = []; h = []; l = []; c = []; t = []
        for x in cc:
            try:
                o.append(float(x.get("open", 0))); h.append(float(x.get("high", 0)))
                l.append(float(x.get("low", 0))); c.append(float(x.get("close", 0)))
                t.append(None)
            except Exception:
                continue
        if len(c) < 10:
            return None
        xs = list(range(len(c)))

        def ema_local(v, p):
            if len(v) < p:
                return [float("nan")]*len(v)
            r = []; m = 2/(p+1); s = sum(v[:p])/p
            for i in range(len(v)):
                if i < p-1: r.append(float("nan"))
                elif i == p-1: r.append(s)
                else:
                    s = ((v[i] - s)*m) + s
                    r.append(s)
            return r

        e21 = ema_local(c, 21); e50 = ema_local(c, 50)
        fig, ax = plt.subplots(figsize=(14, 8), dpi=140)
        fig.patch.set_facecolor("#ffffff"); ax.set_facecolor("#ffffff")
        try:
            w = 0.58
            for i in range(len(cc)):
                col = "#16A34A" if c[i] >= o[i] else "#DC2626"
                ax.vlines(i, l[i], h[i], linewidth=0.8, color="#555555")
                bt = min(o[i], c[i]); ht = max(abs(c[i] - o[i]), 0.000001)
                ax.add_patch(Rectangle((i-w/2, bt), w, ht, facecolor=col, edgecolor=col, linewidth=0.5))
            ax.plot(xs, e21, linewidth=1.4, label="EMA21")
            ax.plot(xs, e50, linewidth=1.4, label="EMA50")
            sig = market_data.get("signal", "WAIT")
            cur = safe_float(market_data.get("price") or market_data.get("current_price") or c[-1])
            su = safe_float(market_data.get("support")); re_ = safe_float(market_data.get("resistance"))
            el = safe_float(market_data.get("entry_low")); eh = safe_float(market_data.get("entry_high"))
            sl = safe_float(market_data.get("stop_loss")); t3 = safe_float(market_data.get("tp3"))
            atr = safe_float(market_data.get("atr"))
            lv = []
            if sig in ["BUY", "SELL"] and el and eh and sl and t3:
                x0 = max(0, len(xs) - 18); bw = 18
                try:
                    if sig == "BUY":
                        ax.add_patch(Rectangle((x0, el), bw, eh-el, alpha=0.25, color="green"))
                        ax.add_patch(Rectangle((x0, sl), bw, el-sl, alpha=0.20, color="red"))
                        ax.add_patch(Rectangle((x0, eh), bw, t3-eh, alpha=0.15, color="green"))
                        ar = FancyArrowPatch((x0+bw/2, eh), (x0+bw/2, t3), arrowstyle="->", mutation_scale=18, linewidth=1.5, color="green")
                    else:
                        ax.add_patch(Rectangle((x0, el), bw, eh-el, alpha=0.25, color="green"))
                        ax.add_patch(Rectangle((x0, eh), bw, sl-eh, alpha=0.20, color="red"))
                        ax.add_patch(Rectangle((x0, t3), bw, el-t3, alpha=0.15, color="green"))
                        ar = FancyArrowPatch((x0+bw/2, el), (x0+bw/2, t3), arrowstyle="->", mutation_scale=18, linewidth=1.5, color="red")
                    ax.add_patch(ar)
                    lv = [(el, "ENTRY LOW"), (eh, "ENTRY HIGH"), (sl, "SL"), (market_data.get("tp1", 0), "TP1"), (market_data.get("tp2", 0), "TP2"), (t3, "TP3")]
                except Exception: lv = []
            else:
                if su: lv.append((su, "SUPPORT"))
                if re_: lv.append((re_, "RESISTANCE"))
            for l_, lb in lv:
                if l_ is None: continue
                ax.axhline(l_, linestyle=":", linewidth=0.7, alpha=0.6)
                try: ax.text(len(xs)+0.8, l_, f"{lb} {l_:,.2f}", fontsize=8, fontweight="bold")
                except Exception: pass
            if cur:
                ax.axhline(cur, linewidth=1, alpha=0.5)
                try: ax.text(len(xs)-1, cur, f" {cur:,.2f}", fontsize=9, fontweight="bold")
                except Exception: pass
            ti = "🟢 BUY" if sig == "BUY" else "🔴 SELL" if sig == "SELL" else "⚠️ WAIT"
            mb = market_data.get("mtf_bias", ""); mt = f" MTF {mb}" if mb else ""
            ax.set_title(f"👑 KING ZARRY AI • {symbol} • {timeframe.upper()}{mt} • {ti}", fontsize=13, fontweight="bold", loc="left", pad=12)
            ax.set_xlim(-1, len(xs)+9); ax.grid(True, alpha=0.15, linewidth=0.7)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            ax.legend(loc="upper left", frameon=False, fontsize=8)
            plt.tight_layout()
            buf = BytesIO(); buf.name = "king_zarry_signal.png"
            fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
            buf.seek(0); return buf
        finally: plt.close(fig)
    except Exception as e:
        logger.warning(f"Discord chart failed {symbol}: {_redact(repr(e))}")
        return None

def enhance_text_prompt(user_prompt: str) -> str:
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    sp = "You are King Zarry's cinematic AI video prompt engineer. Convert idea into ONE detailed high-quality video generation prompt. Include: subject, environment, action, camera, lighting, atmosphere, style, composition. Return ONLY final prompt under 1200 chars."
    c = groq_client.chat.completions.create(model=GROQ_TEXT_MODEL, messages=[{"role": "system", "content": sp}, {"role": "user", "content": user_prompt}], temperature=0.7, max_tokens=500)
    r = c.choices[0].message.content
    if not r: raise RuntimeError("Groq empty prompt")
    return r.strip()

def enhance_image_prompt(image_bytes: bytes, motion_prompt: str):
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    enc = base64.b64encode(image_bytes).decode("utf-8")
    du = "data:image/jpeg;base64," + enc
    sp = "You are King Zarry's image-to-video prompt engineer. Analyze image + requested motion. Create ONE cinematic image-to-video prompt preserving subject identities, faces, clothing, objects, composition. Return ONLY final prompt under 1200 chars."
    uc = [{"type": "text", "text": "Motion:\n" + motion_prompt}, {"type": "image_url", "image_url": {"url": du}}]
    c = groq_client.chat.completions.create(model=GROQ_VISION_MODEL, messages=[{"role": "system", "content": sp}, {"role": "user", "content": uc}], temperature=0.6, max_tokens=600)
    r = c.choices[0].message.content
    if not r: raise RuntimeError("Groq empty image prompt")
    return r.strip()

def generate_text_video(prompt: str) -> bytes:
    if not FAL_KEY: raise RuntimeError("FAL_KEY is not configured.")
    r = fal_client.subscribe(TEXT_TO_VIDEO_MODEL, arguments={"prompt": prompt})
    vu = r.get("video", {}).get("url")
    if not vu: raise RuntimeError("Fal.ai no video URL")
    resp = requests.get(vu, timeout=120); resp.raise_for_status(); return resp.content

def generate_image_video(image_bytes: bytes, prompt: str) -> bytes:
    if not FAL_KEY: raise RuntimeError("FAL_KEY is not configured.")
    iu = fal_client.upload(image_bytes, "image/jpeg")
    r = fal_client.subscribe(IMAGE_TO_VIDEO_MODEL, arguments={"image_url": iu, "prompt": prompt})
    vu = r.get("video", {}).get("url")
    if not vu: raise RuntimeError("Fal.ai no video URL")
    resp = requests.get(vu, timeout=120); resp.raise_for_status(); return resp.content

def save_video(video_bytes: bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tf:
        tf.write(video_bytes); return tf.name

# ============================================================
# FIX 1: Media-aware send helpers (Discord)
# ============================================================
_MEDIA_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^\s)]+)\)")
_MEDIA_VIDEO_LINK_RE = re.compile(r"\[▶ Watch Video\]\((https?://[^\s)]+)\)")
_MEDIA_DIRECT_LINK_RE = re.compile(r"\*\*Direct link:\*\*\s*(https?://[^\s\n]+)")

def _extract_media_from_response(text: str) -> Dict[str, List[str]]:
    if not text:
        return {"images": [], "videos": []}
    images = list(dict.fromkeys(_MEDIA_IMAGE_RE.findall(text)))
    videos = list(dict.fromkeys(_MEDIA_VIDEO_LINK_RE.findall(text)))
    for url in _MEDIA_DIRECT_LINK_RE.findall(text):
        low = url.lower()
        if any(ext in low for ext in [".mp4", ".webm", ".mov", "video"]):
            if url not in videos:
                videos.append(url)
        elif url not in images:
            images.append(url)
    return {"images": images, "videos": videos}

async def send_chunks(destination, text: str):
    if not text: text = "❌ Empty response"
    for c in [text[i:i+1900] for i in range(0, len(text), 1900)]:
        await destination.reply(c, mention_author=False)

async def send_ai_response(message: discord.Message, text: str):
    """
    Send an AI response with auto-render of generated images/videos.
    Falls back to send_chunks() for plain text.
    """
    if not text:
        await send_chunks(message, "❌ Empty response")
        return

    media = _extract_media_from_response(text)

    # Clean the text for display (strip raw markdown image tags)
    display = text
    display = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", display)
    display = re.sub(r"\*\*Direct link:\*\*\s*https?://[^\s\n]+", "", display)
    display = re.sub(r"\n{3,}", "\n\n", display).strip()

    # --- Images ---
    if media["images"]:
        sent_any = False
        for idx, url in enumerate(media["images"][:5]):
            try:
                e = Embed(color=discord.Color.gold())
                e.set_image(url=url)
                if idx == 0 and display:
                    e.description = display[:2000]
                await message.reply(embed=e, mention_author=False)
                sent_any = True
            except Exception as ex:
                logger.warning(f"Discord image embed failed: {_redact(str(ex))}")
                try:
                    await message.reply(url, mention_author=False)
                    sent_any = True
                except Exception:
                    pass
        if sent_any:
            # If we couldn't fit the text in the embed, send it as follow-up
            if not display:
                pass
            elif len(display) > 2000:
                for chunk in [display[i:i+1900] for i in range(2000, len(display), 1900)]:
                    try:
                        await message.reply(chunk, mention_author=False)
                    except Exception:
                        pass
            # Also send any video links
            if media["videos"]:
                for url in media["videos"][:3]:
                    try:
                        await message.reply(url, mention_author=False)
                    except Exception:
                        pass
            return

    # --- Videos ---
    if media["videos"]:
        header = display[:1800] if display else "🎬 Generated video"
        await send_chunks(message, header)
        for url in media["videos"][:3]:
            try:
                await message.reply(url, mention_author=False)
            except Exception as ex:
                logger.warning(f"Discord video send failed: {_redact(str(ex))}")
        return

    # --- Plain text ---
    await send_chunks(message, text)

async def send_followup_chunks(interaction, text: str):
    if not text: text = "❌ Empty response"
    for c in [text[i:i+1900] for i in range(0, len(text), 1900)]:
        await interaction.followup.send(c)

class KingZarryAI(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            guild = discord.Object(id=DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to guild {DISCORD_GUILD_ID}.", flush=True)
        except Exception as e:
            print(f"❌ COMMAND SYNC ERROR: {_redact(repr(e))}", flush=True)

    async def on_ready(self):
        print("\n" + "="*60, flush=True)
        print("👑 KING ZARRY AI DISCORD IS ONLINE", flush=True)
        print("="*60, flush=True)
        print(f"🤖 Logged in as: {self.user}", flush=True)
        print(f"🆔 Bot ID: {self.user.id}", flush=True)
        print("="*60 + "\n", flush=True)

    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if await user_is_banned(message.author.id): return
        await track_user(message.author)
        content = message.content.strip()
        if self.user:
            content = content.replace(f"<@{self.user.id}>", "").replace(f"<@!{self.user.id}>", "").strip()
        images = [a for a in message.attachments if a.content_type and a.content_type.startswith("image/")]
        audio_attachments = []
        for a in message.attachments:
            ct = (a.content_type or "").lower()
            name = (a.filename or "").lower()
            is_audio = ct.startswith("audio/") or name.endswith((".ogg",".mp3",".m4a",".wav",".flac",".mp4",".webm",".opus",".aac",".wma"))
            if is_audio and not ct.startswith("image/"): audio_attachments.append(a)
        if not content and not images and not audio_attachments: return

        is_voice_transcription = False
        if audio_attachments and not content:
            if stt_engine is None:
                await message.reply("🎙️ STT not configured.", mention_author=False); return
            aa = audio_attachments[0]
            if aa.size and aa.size > 10 * 1024 * 1024:
                await message.reply("❌ Audio too large (max 10MB).", mention_author=False); return
            try:
                async with message.channel.typing():
                    ab = await aa.read()
                    fn = aa.filename or "voice.ogg"
                    tr = await asyncio.to_thread(stt_engine.transcribe_bytes, ab, fn)
                    if not tr or not tr.strip():
                        await message.reply("🎙️ Couldn't understand.", mention_author=False); return
                    tr = tr.strip()
                    await message.reply(f"🎙️ I heard: {tr[:500]}", mention_author=False)
                    content = tr; is_voice_transcription = True
            except Exception as e:
                logger.warning(f"Discord STT error: {_redact(str(e))}")
                await message.reply("🎙️ Voice failed.", mention_author=False); return

        # PRIORITY 1: MEDIA
        try:
            has_img = bool(images)
            is_media_edit = has_img and _looks_like_media_request(content)
            is_media_text = (not has_img) and _looks_like_media_request(content)
            if is_media_edit or is_media_text:
                logger.info(f"Media req: '{content[:60]}'")
                it = None
                if has_img:
                    a = images[0]
                    if a.size > MAX_IMAGE_SIZE:
                        await message.reply("❌ Image > 10MB.", mention_author=False); return
                    ib = await a.read()
                    it = (a.content_type or "image/png", ib)
                async with message.channel.typing():
                    ans = await asyncio.to_thread(ai.ask, str(message.author.id), content, it)
                # FIX 1: media-aware sender
                await send_ai_response(message, ans or "❌ No response")
                return
        except Exception as e:
            logger.warning(f"Media err: {_redact(str(e))}")

        # PRIORITY 2: ALERTS
        try:
            p = parse_alert_request_discord(content)
            if p and not images:
                cf = shared_create_alert
                if cf is None:
                    try:
                        from bot import create_price_alert as bc; cf = bc
                    except Exception: cf = None
                if cf:
                    r = await asyncio.to_thread(cf, message.author.id, p["symbol"], p["target_price"], p["condition"])
                    if r.get("success"):
                        cd = {"ABOVE":"above","BELOW":"below","REACHES":"reaches"}.get(p["condition"], p["condition"])
                        await message.reply(f"🔔 Alert created\n{p['symbol']} {cd} {p['target_price']}\nID: `{r['id']}`", mention_author=False)
                        return
                    elif r.get("duplicate"):
                        await message.reply(f"⚠️ Duplicate alert for {p['symbol']} {p['condition']} {p['target_price']}", mention_author=False)
                        return
        except Exception as e:
            logger.warning(f"Alert err: {_redact(str(e))}")

        # PRIORITY 3: MARKET
        try:
            im, sym, tf = detect_market_intent_discord(content)
            if im and not images:
                async with message.channel.typing():
                    try:
                        md = await asyncio.to_thread(market_engine.analyze_market, sym, tf)
                        nd = await asyncio.to_thread(news_engine.get_news_for_asset, sym)
                        emb = build_discord_signal_embed(md, nd)
                        cf = None
                        try:
                            cb = await asyncio.to_thread(build_discord_signal_chart, sym, tf, md)
                            if cb:
                                cf = File(fp=cb, filename="king_zarry_signal.png")
                                emb.set_image(url="attachment://king_zarry_signal.png")
                        except Exception as ce:
                            logger.warning(f"Chart err: {_redact(repr(ce))}")
                        if cf: await message.reply(embed=emb, file=cf, mention_author=False)
                        else: await message.reply(embed=emb, mention_author=False)
                        return
                    except Exception as me:
                        logger.warning(f"Market err: {_redact(str(me))}")
        except Exception as e:
            logger.warning(f"Market detect err: {_redact(str(e))}")

        # PRIORITY 4: NEWS
        try:
            if detect_news_intent_discord(content) and not images:
                async with message.channel.typing():
                    sym, _ = detect_market_and_timeframe(content)
                    try:
                        nd = await asyncio.to_thread(news_engine.get_news_for_asset, sym)
                        if nd:
                            emb = Embed(title=f"📰 {sym} News", description=nd.get("summary", "Market context")[:1500], color=discord.Color.blue())
                            emb.add_field(name="Risk", value=nd.get("risk", "LOW"), inline=True)
                            if nd.get("events"):
                                ev = "\n".join([f"• {e.get('event','')[:80]}" for e in nd["events"][:3]])
                                emb.add_field(name="Events", value=ev[:1024], inline=False)
                            await message.reply(embed=emb, mention_author=False)
                            return
                    except Exception: pass
        except Exception: pass

        # PRIORITY 5: AI
        try:
            async with message.channel.typing():
                it = None
                if images:
                    a = images[0]
                    if a.size > MAX_IMAGE_SIZE:
                        await message.reply("❌ Image > 10MB.", mention_author=False); return
                    ib = await a.read()
                    it = (a.content_type or "image/png", ib)
                    sym, tf = detect_market_and_timeframe(content)
                    if sym != "BTC/USD" or any(k in content.upper() for k in ["CHART","SIGNAL","ANALYSIS"]):
                        content = f"Analyze this chart. Market: {sym} TF: {tf}. Only use info visible in image."
                    elif not content:
                        content = "Analyze this image."
                fp = SYSTEM_VOICE_PROMPT + "\n\nUser: " + content
                ans = await asyncio.to_thread(ai.ask, str(message.author.id), fp, it)
            if not ans: ans = "❌ No response."
            vt = ["use voice","speak","send audio","voice message","say this","can you speak","female voice","audio"]
            wv = is_voice_transcription or any(t in content.lower() for t in vt)
            vf = None
            if wv:
                try:
                    af, pv = await generate_tts_audio(ans[:800])
                    vf = File(fp=af, filename="king_zarry_voice.mp3")
                except Exception as ve:
                    logger.warning(f"Voice err: {_redact(str(ve))}")
                    # FIX 1: media-aware sender
                    await send_ai_response(message, ans); return
            if vf:
                await message.reply(content=ans[:1900], file=vf, mention_author=False)
            else:
                # FIX 1: media-aware sender
                await send_ai_response(message, ans)
        except Exception as e:
            logger.error(f"AI err: {_redact(repr(e))}")
            try: await message.reply("❌ Error. Try again.", mention_author=False)
            except Exception: pass

client = KingZarryAI()

from discord.ext import tasks

@tasks.loop(seconds=60)
async def discord_price_alert_loop():
    try:
        ga = shared_get_all_active; gp = shared_get_price; ck = shared_check_triggered
        if not ga or not gp or not ck: return
        aa = await asyncio.to_thread(ga)
        if not aa: return
        from collections import defaultdict
        by_sym = defaultdict(list)
        for a in aa: by_sym[a["symbol"]].append(a)
        for sym, alerts in by_sym.items():
            try:
                cp = await asyncio.to_thread(gp, sym)
                if cp is None: continue
                ni = datetime.now(timezone.utc).isoformat()
                for a in alerts:
                    try:
                        lp = a.get("last_checked_price")
                        trg = ck(current_price=float(cp), target_price=float(a["target_price"]), condition=a["condition"], last_price=lp)
                        try:
                            conn = db_connect()
                            conn.execute("UPDATE price_alerts SET last_checked_price=?, last_checked_at=? WHERE id=?", (cp, ni, a["id"]))
                            conn.commit(); conn.close()
                        except Exception: pass
                        if trg:
                            uid = int(a["user_id"]); tgt = float(a["target_price"]); cnd = a["condition"]
                            cd = {"ABOVE": f"Above {tgt}", "BELOW": f"Below {tgt}", "REACHES": f"Reached {tgt}"}.get(cnd, cnd)
                            try:
                                u = client.get_user(uid)
                                if u is None:
                                    try: u = await client.fetch_user(uid)
                                    except Exception: u = None
                                if u:
                                    emb = Embed(title="🔔 PRICE ALERT", description="Your alert triggered.", color=discord.Color.gold())
                                    emb.add_field(name="Asset", value=sym, inline=True)
                                    emb.add_field(name="Target", value=str(tgt), inline=True)
                                    emb.add_field(name="Current", value=f"{cp:.2f}", inline=True)
                                    emb.add_field(name="Condition", value=cd, inline=False)
                                    await u.send(embed=emb)
                                conn = db_connect()
                                conn.execute("UPDATE price_alerts SET active=0, triggered=1, triggered_at=?, last_checked_price=?, last_checked_at=? WHERE id=?", (ni, cp, ni, a["id"]))
                                conn.commit(); conn.close()
                            except Exception as se:
                                logger.warning(f"Alert send err: {_redact(str(se))}")
                    except Exception: continue
            except Exception: continue
    except Exception as e:
        logger.warning(f"Alert loop err: {_redact(str(e))}")

@discord_price_alert_loop.before_loop
async def before_alert_loop():
    await client.wait_until_ready()
    print("🔔 Price alert loop starting", flush=True)

_orig_on_ready = client.on_ready
async def enhanced_on_ready():
    await _orig_on_ready()
    if not discord_price_alert_loop.is_running():
        discord_price_alert_loop.start()
        print("🔔 Alert task started", flush=True)

client.on_ready = enhanced_on_ready

# ============ SLASH COMMANDS ============
@client.tree.command(name="start", description="Start King Zarry AI")
async def start(interaction: discord.Interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    e = Embed(title="👑 KING ZARRY AI", description="AI Agent • Market • Vision • Memory • Voice • Image/Video", color=discord.Color.gold())
    e.add_field(name="Trading", value="`/signal BTC` `/btc` `/eth` `/sol` `/xau` `/plan`", inline=False)
    e.add_field(name="Alerts", value="`/alert` `/alerts` `/cancelalert`", inline=False)
    e.add_field(name="AI", value="`/ask` `/voice` `/tts`", inline=False)
    e.add_field(name="Creative", value="Just type `Draw a cyberpunk trader`", inline=False)
    e.add_field(name="Video", value="`/textvideo` `/imagevideo`", inline=False)
    e.add_field(name="News", value="`/news` `/events`", inline=False)
    await interaction.response.send_message(embed=e)

@client.tree.command(name="help", description="Help")
async def help_cmd(interaction: discord.Interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.send_message("👑 **HELP**\n\n`/signal BTC` `/btc` `/eth` `/sol` `/xau` `/plan` `/analyze`\n`/alert` `/alerts` `/cancelalert`\n`/ask` `/voice` `/tts`\n`/textvideo` `/imagevideo`\n`/news` `/events`\n`/premium` `/status`\n`/join` `/say` `/leave`")

@client.tree.command(name="ping", description="Status check")
async def ping(interaction: discord.Interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.send_message("👑 King Zarry AI online!\n🤖 AI: OK\n📊 Market: OK\n📰 News: OK\n🎙️ Voice: OK")

VALID_TF = {"1m","5m","15m","30m","1h","2h","4h","1d"}
def _ntf(tf): return tf.lower().strip() if tf.lower().strip() in VALID_TF else "15m"

async def handle_signal(interaction, symbol, timeframe="15m", defer=True):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    if defer: await interaction.response.defer()
    try:
        tf = _ntf(timeframe)
        md = await asyncio.to_thread(market_engine.analyze_market, symbol, tf)
        nd = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
        emb = build_discord_signal_embed(md, nd)
        cf = None
        try:
            cb = await asyncio.to_thread(build_discord_signal_chart, symbol, tf, md)
            if cb:
                cf = File(fp=cb, filename="king_zarry_signal.png")
                emb.set_image(url="attachment://king_zarry_signal.png")
        except Exception as ce:
            logger.warning(f"Chart err: {_redact(repr(ce))}")
        if cf: await interaction.followup.send(embed=emb, file=cf)
        else: await interaction.followup.send(embed=emb)
    except Exception as e:
        logger.error(f"Signal err {symbol}: {_redact(repr(e))}")
        await interaction.followup.send("⚠️ Signal failed. Retry.")

@client.tree.command(name="signal", description="MTF signal")
@app_commands.choices(symbol=[
    app_commands.Choice(name="BTC/USD", value="BTC/USD"),
    app_commands.Choice(name="ETH/USD", value="ETH/USD"),
    app_commands.Choice(name="SOL/USD", value="SOL/USD"),
    app_commands.Choice(name="XAU/USD Gold", value="XAU/USD"),
])
async def signal_cmd(interaction, symbol: str = "BTC/USD"):
    await handle_signal(interaction, symbol, "15m")

@client.tree.command(name="btc", description="BTC analysis")
async def btc(interaction, timeframe: str = "15m"):
    await handle_signal(interaction, "BTC/USD", timeframe)

@client.tree.command(name="eth", description="ETH analysis")
async def eth(interaction):
    await handle_signal(interaction, "ETH/USD", "15m")

@client.tree.command(name="sol", description="SOL analysis")
async def sol(interaction):
    await handle_signal(interaction, "SOL/USD", "15m")

@client.tree.command(name="xau", description="XAU analysis")
async def xau(interaction):
    await handle_signal(interaction, "XAU/USD", "15m")

@client.tree.command(name="gold", description="Gold analysis")
async def gold(interaction, timeframe: str = "15m"):
    await handle_signal(interaction, "XAU/USD", timeframe)

@client.tree.command(name="crypto", description="Crypto prices")
async def crypto(interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    res = []
    for s in ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD"]:
        try:
            d = await asyncio.to_thread(market_engine.analyze_market, s, "15m")
            p = safe_float(d.get("price"))
            sg = d.get("signal", "WAIT")
            res.append(f"**{s}**: `${p:,.2f}` - {sg}")
        except Exception as e:
            res.append(f"**{s}**: Error - {_redact(str(e))[:50]}")
    await interaction.followup.send("👑 **PRICES**\n\n" + "\n".join(res))

@client.tree.command(name="analyze", description="Custom market")
async def analyze(interaction, symbol: str, timeframe: str = "15m"):
    await handle_signal(interaction, symbol.upper(), timeframe)

@client.tree.command(name="plan", description="Daily plan")
async def plan_cmd(interaction, symbol: str = "BTC/USD"):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        td = market_engine.get_trading_date()
        p = await asyncio.to_thread(market_engine.get_daily_plan, symbol, td)
        if not p:
            await interaction.followup.send(f"📭 No plan for {symbol} on {td}."); return
        e = build_discord_signal_embed(p, None)
        e.title = f"📋 PLAN • {symbol} • {td}"
        await interaction.followup.send(embed=e)
    except Exception as e:
        await interaction.followup.send(f"❌ Plan: {_redact(str(e))[:300]}")

@client.tree.command(name="news", description="News engine status")
async def news_cmd(interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        from news import provider_status, news_health
        s = provider_status(); h = news_health()
        e = Embed(title="📰 NEWS ENGINE", color=discord.Color.blue())
        e.add_field(name="Status", value=f"Health: {h.get('status')}", inline=False)
        e.add_field(name="Calendar", value="✅" if s.get("calendar_available") else "❌", inline=True)
        e.add_field(name="Headlines", value="✅" if s.get("news_available") else "❌", inline=True)
        await interaction.followup.send(embed=e)
    except Exception as e:
        await interaction.followup.send(f"❌ News: {_redact(str(e))[:300]}")

@client.tree.command(name="events", description="Upcoming events")
async def events_cmd(interaction, hours: int = 24):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        from news import get_upcoming_events
        ev = await asyncio.to_thread(get_upcoming_events, hours)
        if not ev:
            await interaction.followup.send(f"📰 No events in next {hours}h."); return
        e = Embed(title=f"📅 Events ({hours}h)", color=discord.Color.gold())
        for x in ev[:10]:
            e.add_field(name=f"{x.get('impact','medium').upper()} - {x.get('time','')[:50]}", value=x.get("event", "Unknown")[:100], inline=False)
        await interaction.followup.send(embed=e)
    except Exception as e:
        await interaction.followup.send(f"❌ Events: {_redact(str(e))[:300]}")

@client.tree.command(name="premium", description="Premium status/manage")
@app_commands.choices(plan=[
    app_commands.Choice(name="monthly - 250 XTR", value="monthly"),
    app_commands.Choice(name="3 months - 600 XTR", value="3month"),
    app_commands.Choice(name="yearly - 2000 XTR", value="yearly"),
    app_commands.Choice(name="revoke", value="revoke"),
])
async def premium(interaction, user: Optional[discord.User] = None, plan: Optional[app_commands.Choice[str]] = None):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    if user is None and plan is None:
        sub = await asyncio.to_thread(get_subscription_sync, interaction.user.id)
        if not sub:
            await interaction.response.send_message("⭐ No active Premium.", ephemeral=True); return
        ex = datetime.fromisoformat(sub["expires_at"])
        await interaction.response.send_message(f"⭐ Premium active\nPlan: {sub['plan']}\nExpires: {ex:%Y-%m-%d}", ephemeral=True)
        return
    if not await require_admin(interaction): return
    if user is None or plan is None:
        await interaction.response.send_message("❌ Usage: /premium @user monthly", ephemeral=True); return
    if plan.value == "revoke":
        rm = await asyncio.to_thread(revoke_subscription_sync, user.id)
        await interaction.response.send_message("🗑️ Revoked" if rm else "ℹ️ No premium", ephemeral=True); return
    ex = await asyncio.to_thread(grant_subscription_sync, user.id, plan.value, interaction.user.id)
    await interaction.response.send_message(f"⭐ Premium activated for {user.mention}\nPlan: {plan.value}\nExpires: {ex:%Y-%m-%d}", ephemeral=True)

@client.tree.command(name="status", description="Premium status alias")
async def status_cmd(interaction):
    await premium(interaction)

@client.tree.command(name="admin", description="Admin panel")
async def admin(interaction):
    if not await require_admin(interaction): return
    u = await asyncio.to_thread(get_user_count_sync)
    p = await asyncio.to_thread(get_premium_count_sync)
    b = await asyncio.to_thread(get_banned_count_sync)
    e = Embed(title="👑 ADMIN", color=discord.Color.gold())
    e.add_field(name="Users", value=str(u), inline=True)
    e.add_field(name="Premium", value=str(p), inline=True)
    e.add_field(name="Banned", value=str(b), inline=True)
    await interaction.response.send_message(embed=e, ephemeral=True)

@client.tree.command(name="users", description="User stats")
async def users(interaction):
    if not await require_admin(interaction): return
    t = await asyncio.to_thread(get_user_count_sync)
    p = await asyncio.to_thread(get_premium_count_sync)
    b = await asyncio.to_thread(get_banned_count_sync)
    await interaction.response.send_message(f"👑 Users: {t}\nPremium: {p}\nBanned: {b}\nGuilds: {len(client.guilds)}", ephemeral=True)

@client.tree.command(name="ban", description="Ban user")
async def ban(interaction, user: discord.User, reason: str = "No reason"):
    if not await require_admin(interaction): return
    if user.id == DISCORD_ADMIN_ID:
        await interaction.response.send_message("❌ Can't ban admin.", ephemeral=True); return
    await asyncio.to_thread(ban_user_sync, user.id, reason, interaction.user.id)
    await interaction.response.send_message(f"⛔ Banned {user.mention}\nReason: {reason}", ephemeral=True)

@client.tree.command(name="unban", description="Unban user")
async def unban(interaction, user_id: str):
    if not await require_admin(interaction): return
    try: tid = int(user_id)
    except ValueError:
        await interaction.response.send_message("❌ ID must be number", ephemeral=True); return
    rm = await asyncio.to_thread(unban_user_sync, tid)
    await interaction.response.send_message("✅ Unbanned" if rm else "ℹ️ Not banned", ephemeral=True)

@client.tree.command(name="broadcast", description="Broadcast message")
async def broadcast(interaction, message: str, attachment: Optional[discord.Attachment] = None):
    if not await require_admin(interaction): return
    if len(message) > 1900:
        await interaction.response.send_message("❌ Max 1900 chars", ephemeral=True); return
    ABT = {"image/png","image/jpeg","image/webp","image/gif","video/mp4"}
    bb = None; bf = None
    if attachment:
        if attachment.size > MAX_IMAGE_SIZE:
            await interaction.response.send_message("❌ Max 10MB", ephemeral=True); return
        if not attachment.content_type or attachment.content_type not in ABT:
            await interaction.response.send_message("❌ Bad type", ephemeral=True); return
        try: bb = await attachment.read(); bf = attachment.filename
        except Exception as e:
            await interaction.response.send_message(f"❌ {_redact(str(e))[:200]}", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    uids = await asyncio.to_thread(get_all_user_ids_sync)
    sent = 0; fail = 0
    for uid in uids:
        if uid == DISCORD_ADMIN_ID: continue
        try:
            u = client.get_user(uid)
            if u is None: u = await client.fetch_user(uid)
            if await user_is_banned(uid): continue
            if bb:
                f = discord.File(io.BytesIO(bb), filename=bf)
                await u.send("👑 ANNOUNCEMENT\n\n" + message, file=f)
            else:
                await u.send("👑 ANNOUNCEMENT\n\n" + message)
            sent += 1; await asyncio.sleep(0.5)
        except Exception: fail += 1
    await interaction.followup.send(f"📢 Done\nSent: {sent}\nFailed: {fail}", ephemeral=True)

@client.tree.command(name="ask", description="Ask AI")
async def ask(interaction, question: str):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        ans = await asyncio.to_thread(ai.ask, str(interaction.user.id), question)
        # FIX 1: send media-aware follow-up
        media = _extract_media_from_response(ans or "")
        if media["images"] or media["videos"]:
            # text portion first
            display = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", ans or "")
            display = re.sub(r"\n{3,}", "\n\n", display).strip()
            if display:
                for c in [display[i:i+1900] for i in range(0, len(display), 1900)]:
                    await interaction.followup.send(c)
            for url in media["images"][:5]:
                try:
                    e = Embed(color=discord.Color.gold())
                    e.set_image(url=url)
                    await interaction.followup.send(embed=e)
                except Exception:
                    try: await interaction.followup.send(url)
                    except Exception: pass
            for url in media["videos"][:3]:
                try: await interaction.followup.send(url)
                except Exception: pass
        else:
            await send_followup_chunks(interaction, ans)
    except Exception as e:
        logger.error(f"/ask err: {_redact(repr(e))}")
        await interaction.followup.send("⚠️ AI busy.")

@client.tree.command(name="voice", description="AI voice answer")
async def voice_command(interaction, question: str):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        fp = SYSTEM_VOICE_PROMPT + "\n\nUser: " + question
        ans = await asyncio.to_thread(ai.ask, str(interaction.user.id), fp)
        af, pv = await generate_tts_audio(ans)
        f = File(fp=af, filename="king_zarry_voice.mp3")
        await interaction.followup.send(content=f"🗣️ **{pv}:**\n{ans[:1500]}", file=f)
    except Exception as e:
        logger.error(f"/voice err: {_redact(repr(e))}")
        await interaction.followup.send("⚠️ Voice busy.")

@client.tree.command(name="tts", description="Text to speech")
async def tts_cmd(interaction, text: str):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer()
    try:
        af, pv = await generate_tts_audio(text)
        f = File(fp=af, filename="king_zarry_tts.mp3")
        await interaction.followup.send(content=f"🎙️ **TTS {pv}:** {text[:500]}", file=f)
    except Exception as e2:
        await interaction.followup.send(f"❌ TTS: {_redact(str(e2))[:300]}")

@client.tree.command(name="textvideo", description="Text to video (Fal.ai)")
async def textvideo(interaction, prompt: str):
    if not await ensure_not_banned(interaction): return
    if not prompt.strip():
        await interaction.response.send_message("❌ Provide prompt", ephemeral=True); return
    if len(prompt) > MAX_PROMPT_LENGTH:
        await interaction.response.send_message(f"❌ Max {MAX_PROMPT_LENGTH}", ephemeral=True); return
    await track_user(interaction.user)
    await interaction.response.defer()
    sm = await interaction.followup.send("🧠 Enhancing...")
    vp = None
    try:
        ep = await asyncio.to_thread(enhance_text_prompt, prompt.strip())
        await sm.edit(content="🎬 Generating...")
        vb = await asyncio.to_thread(generate_text_video, ep)
        if len(vb) > MAX_VIDEO_SIZE:
            await sm.edit(content="⚠️ Video too large."); return
        vp = save_video(vb)
        f = discord.File(vp, filename="king-zarry-video.mp4")
        e = Embed(title="👑 Video", description="🎬 Complete")
        e.add_field(name="Prompt", value=ep[:1000], inline=False)
        await interaction.followup.send(embed=e, file=f)
        await sm.delete()
    except Exception as err:
        logger.error(f"Text video err: {_redact(repr(err))}")
        await sm.edit(content="❌ Video gen unavailable.")
    finally:
        if vp and os.path.exists(vp):
            try: os.remove(vp)
            except OSError: pass

@client.tree.command(name="imagevideo", description="Image to video (Fal.ai)")
async def imagevideo(interaction, image: discord.Attachment, motion: str):
    if not await ensure_not_banned(interaction): return
    if image.content_type not in ALLOWED_VIDEO_IMAGE_TYPES:
        await interaction.response.send_message("❌ PNG/JPEG/WebP only.", ephemeral=True); return
    if image.size > MAX_IMAGE_SIZE:
        await interaction.response.send_message("❌ Max 10MB.", ephemeral=True); return
    if not motion.strip():
        await interaction.response.send_message("❌ Describe motion.", ephemeral=True); return
    await track_user(interaction.user)
    await interaction.response.defer()
    sm = await interaction.followup.send("📥 Downloading...")
    vp = None
    try:
        ib = await image.read()
        ep = await asyncio.to_thread(enhance_image_prompt, ib, motion.strip())
        await sm.edit(content="🎬 Generating...")
        vb = await asyncio.to_thread(generate_image_video, ib, ep)
        if len(vb) > MAX_VIDEO_SIZE:
            await sm.edit(content="⚠️ Too large."); return
        vp = save_video(vb)
        f = discord.File(vp, filename="king-zarry-image-video.mp4")
        e = Embed(title="👑 Video", description="🖼️ Complete")
        e.add_field(name="Motion", value=ep[:1000], inline=False)
        await interaction.followup.send(embed=e, file=f)
        await sm.delete()
    except Exception as err:
        logger.error(f"Img video err: {_redact(repr(err))}")
        await sm.edit(content="❌ Unavailable.")
    finally:
        if vp and os.path.exists(vp):
            try: os.remove(vp)
            except OSError: pass

@client.tree.command(name="clear_memory", description="Clear memory")
async def clear_memory(interaction):
    if not await ensure_not_banned(interaction): return
    await interaction.response.defer(ephemeral=True)
    try:
        await asyncio.to_thread(memory.clear_history, str(interaction.user.id))
        await interaction.followup.send("🧹 Memory cleared.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ {_redact(str(e))[:1200]}", ephemeral=True)

@client.tree.command(name="alert", description="Create alert")
@app_commands.choices(
    symbol=[
        app_commands.Choice(name="XAU/USD Gold", value="XAU/USD"),
        app_commands.Choice(name="BTC/USD", value="BTC/USD"),
        app_commands.Choice(name="ETH/USD", value="ETH/USD"),
        app_commands.Choice(name="SOL/USD", value="SOL/USD"),
    ],
    condition=[
        app_commands.Choice(name="above", value="ABOVE"),
        app_commands.Choice(name="below", value="BELOW"),
        app_commands.Choice(name="reaches", value="REACHES"),
    ]
)
async def alert_slash(interaction, symbol: str, condition: str, price: float):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer(ephemeral=True)
    try:
        ns = normalize_alert_symbol_discord(symbol)
        if not ns:
            await interaction.followup.send(f"❌ Unsupported {symbol}", ephemeral=True); return
        if price <= 0:
            await interaction.followup.send("❌ Price > 0", ephemeral=True); return
        cu = condition.upper()
        if cu not in ["ABOVE","BELOW","REACHES"]:
            await interaction.followup.send("❌ Bad condition", ephemeral=True); return
        cf = shared_create_alert
        if cf is None:
            try:
                from bot import create_price_alert as bc; cf = bc
            except Exception: cf = None
        if not cf:
            await interaction.followup.send("❌ Alerts unavailable", ephemeral=True); return
        r = await asyncio.to_thread(cf, interaction.user.id, ns, float(price), cu)
        if r.get("success"):
            e = Embed(title="🔔 Alert Created", description="Monitoring...", color=discord.Color.gold())
            e.add_field(name="Asset", value=ns, inline=True)
            e.add_field(name="Condition", value=f"{cu} {price}", inline=True)
            e.add_field(name="ID", value=f"`{r['id']}`", inline=False)
            await interaction.followup.send(embed=e, ephemeral=True)
        elif r.get("duplicate"):
            await interaction.followup.send(f"⚠️ Duplicate: {ns} {cu} {price}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed", ephemeral=True)
    except Exception as e:
        logger.error(f"/alert err: {_redact(repr(e))}")
        await interaction.followup.send(f"❌ {_redact(str(e))[:300]}", ephemeral=True)

@client.tree.command(name="alerts", description="List your alerts")
async def alerts_slash(interaction):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer(ephemeral=True)
    try:
        gf = shared_get_alerts
        if gf is None:
            try:
                from bot import get_user_price_alerts as bg; gf = bg
            except Exception: gf = None
        if not gf:
            await interaction.followup.send("❌ Alerts unavailable", ephemeral=True); return
        aa = await asyncio.to_thread(gf, interaction.user.id, True)
        if not aa:
            await interaction.followup.send("📭 No alerts. /alert", ephemeral=True); return
        e = Embed(title="🔔 Your Alerts", description=f"{len(aa)} active", color=discord.Color.gold())
        for i, a in enumerate(aa[:10], 1):
            cs = {"ABOVE":"≥","BELOW":"≤","REACHES":"≈"}.get(a["condition"], a["condition"])
            e.add_field(name=f"{i}. {a['symbol']} {cs} {a['target_price']}", value=f"ID `{a['id']}` | {a['condition']}", inline=False)
        await interaction.followup.send(embed=e, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ {_redact(str(e))[:300]}", ephemeral=True)

@client.tree.command(name="cancelalert", description="Cancel alert(s)")
async def cancelalert_slash(interaction, alert_id: str):
    if not await ensure_not_banned(interaction): return
    await track_user(interaction.user)
    await interaction.response.defer(ephemeral=True)
    try:
        uid = interaction.user.id
        if alert_id.lower().strip() == "all":
            caf = shared_cancel_all
            if caf is None:
                try:
                    from bot import cancel_all_user_alerts as bc; caf = bc
                except Exception: caf = None
            if not caf:
                await interaction.followup.send("❌ Cancel unavailable", ephemeral=True); return
            n = await asyncio.to_thread(caf, uid)
            await interaction.followup.send(f"✅ Cancelled {n}", ephemeral=True); return
        try: aid = int(alert_id.strip())
        except ValueError:
            await interaction.followup.send("❌ Bad ID", ephemeral=True); return
        cf = shared_cancel_alert
        if cf is None:
            try:
                from bot import cancel_user_alert as bc; cf = bc
            except Exception: cf = None
        if not cf:
            await interaction.followup.send("❌ Cancel unavailable", ephemeral=True); return
        ok = await asyncio.to_thread(cf, uid, aid)
        await interaction.followup.send("✅ Cancelled" if ok else "❌ Not found", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ {_redact(str(e))[:300]}", ephemeral=True)

@client.tree.command(name="join", description="Join voice channel")
async def join(interaction):
    if not await ensure_not_banned(interaction): return
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Join VC first", ephemeral=True); return
    ch = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(ch)
    else:
        await ch.connect()
    await interaction.response.send_message(f"🔊 Joined {ch.name}")

@client.tree.command(name="say", description="Speak in VC")
async def say(interaction, text: str):
    if not await ensure_not_banned(interaction): return
    await interaction.response.defer()
    vc = interaction.guild.voice_client
    if not vc:
        if interaction.user.voice and interaction.user.voice.channel:
            vc = await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("❌ Join VC first"); return
    try:
        aus, pv = await generate_tts_audio(text)
        await interaction.followup.send(f"🎙️ Speaking with {pv}: {text[:500]}")
        src = discord.FFmpegPCMAudio(aus, pipe=True)
        if vc.is_playing(): vc.stop()
        vc.play(src)
    except Exception as e:
        logger.error(f"/say err: {_redact(str(e))}")
        await interaction.followup.send(f"❌ {_redact(str(e))[:300]}")

@client.tree.command(name="leave", description="Leave VC")
async def leave(interaction):
    if not await ensure_not_banned(interaction): return
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Disconnected")
    else:
        await interaction.response.send_message("⚠️ Not in VC", ephemeral=True)

@client.tree.command(name="adminstatus", description="Admin diagnostics")
async def adminstatus(interaction):
    if not await require_admin(interaction):
        await interaction.response.send_message("❌ Not authorized", ephemeral=True); return
    try:
        from news import provider_status, news_health
        ps = provider_status(); h = news_health()
        e = Embed(title="🛠️ DIAGNOSTICS", color=discord.Color.red())
        e.add_field(name="ElevenLabs", value="ENABLED" if eleven_client else "DISABLED", inline=True)
        e.add_field(name="Groq", value="ENABLED" if groq_client else "DISABLED", inline=True)
        e.add_field(name="Fal", value="ENABLED" if FAL_KEY else "DISABLED", inline=True)
        e.add_field(name="Agnes", value="ENABLED" if os.getenv("AGNES_API_KEY") else "DISABLED", inline=True)
        e.add_field(name="AceData", value="ENABLED" if os.getenv("ACEDATA_API_KEY") else "DISABLED", inline=True)
        e.add_field(name="News", value=f"{ps}\n{h}", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)
    except Exception as e:
        logger.error(f"adminstatus: {_redact(repr(e))}")
        await interaction.response.send_message(f"❌ {_redact(str(e))[:500]}", ephemeral=True)

if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
