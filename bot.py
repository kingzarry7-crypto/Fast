print("🇳🇬 BOTPY-V5-FIXED-LOADED 🇳🇬", flush=True)
print("=" * 60, flush=True)
print("🔵 BOOT: bot.py starting...", flush=True)
print("=" * 60, flush=True)

import os
import re
import html
import json
import sys
import asyncio
import base64
import sqlite3
import tempfile
import shutil
import logging
from io import BytesIO
from datetime import datetime, timezone, timedelta, time as dt_time
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo

print(f"🔵 BOOT: stdlib imports OK | Python {sys.version.split()[0]}", flush=True)

import requests
print("🔵 BOOT: requests OK", flush=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
print("🔵 BOOT: matplotlib OK", flush=True)

from dotenv import load_dotenv
load_dotenv()
print("🔵 BOOT: dotenv OK", flush=True)

from telegram import LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
)
from telegram.error import Conflict, Forbidden, BadRequest, RetryAfter
print("🔵 BOOT: python-telegram-bot OK", flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger("king_zarry")

def clean_env_str(value, default=""):
    if not value:
        return default
    value = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(value)).strip()
    return value if value else default

def env_int(name, default=0):
    try:
        return int(clean_env_str(os.getenv(name), str(default)))
    except Exception:
        return default

TELEGRAM_BOT_TOKEN = clean_env_str(os.getenv("TELEGRAM_BOT_TOKEN"))
XAI_API_KEY = clean_env_str(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
XAI_BASE_URL = clean_env_str(os.getenv("XAI_BASE_URL"), "https://api.x.ai/v1")
XAI_MODEL = clean_env_str(os.getenv("XAI_MODEL") or os.getenv("GROK_MODEL"), "grok-4")
GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
GROQ_BASE_URL = clean_env_str(os.getenv("GROQ_BASE_URL"), "https://api.groq.com/openai/v1")
GROQ_MODEL = clean_env_str(os.getenv("GROQ_MODEL"), "openai/gpt-oss-20b")
OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_BASE_URL = clean_env_str(os.getenv("OPENROUTER_BASE_URL"), "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = clean_env_str(os.getenv("OPENROUTER_MODEL"), "openrouter/free")
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_BASE_URL = OPENROUTER_BASE_URL
OPENAI_MODEL = OPENROUTER_MODEL
GEMINI_API_KEY = clean_env_str(os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = clean_env_str(os.getenv("GEMINI_MODEL"), "gemini-2.5-flash")
TWELVE_DATA_API_KEY = clean_env_str(os.getenv("TWELVE_DATA_API_KEY"))
TWELVE_DATA_URL = "https://api.twelvedata.com"
AI_PROVIDER = clean_env_str(os.getenv("AI_PROVIDER"), "AUTO").upper()
ELEVENLABS_API_KEY = clean_env_str(os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = clean_env_str(os.getenv("ELEVENLABS_VOICE_ID"), "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL_ID = clean_env_str(os.getenv("ELEVENLABS_MODEL_ID"), "eleven_flash_v2_5")
DISCORD_BOT_TOKEN = clean_env_str(os.getenv("DISCORD_BOT_TOKEN"))

ADMIN_IDS = set()
admin_ids_raw = clean_env_str(os.getenv("ADMIN_IDS"))
if admin_ids_raw:
    for item in admin_ids_raw.split(","):
        try:
            ADMIN_IDS.add(int(item.strip()))
        except Exception:
            pass
single_admin = clean_env_str(os.getenv("ADMIN_ID"))
if single_admin:
    try:
        ADMIN_IDS.add(int(single_admin))
    except Exception:
        pass

DATABASE_PATH = clean_env_str(os.getenv("DATABASE_PATH"), "king_zarry.db")
MEMORY_DB_PATH = clean_env_str(os.getenv("MEMORY_DB_PATH"), "king_zarry_memory.db")
MONTHLY_STARS = env_int("MONTHLY_STARS", 150)
THREE_MONTH_STARS = env_int("THREE_MONTH_STARS", 500)
YEARLY_STARS = env_int("YEARLY_STARS", 2500)

SUBSCRIPTION_PLANS = {
    "monthly": {"name": "👑 Monthly VIP", "days": 30, "stars": MONTHLY_STARS, "description": "30 days King Zarry AI VIP access"},
    "3month": {"name": "🔥 3-Month VIP", "days": 90, "stars": THREE_MONTH_STARS, "description": "90 days King Zarry AI VIP access"},
    "yearly": {"name": "💎 Yearly VIP", "days": 365, "stars": YEARLY_STARS, "description": "365 days King Zarry AI VIP access"},
}

print(f"🔵 BOOT: TELEGRAM_BOT_TOKEN {'FOUND (len=' + str(len(TELEGRAM_BOT_TOKEN)) + ')' if TELEGRAM_BOT_TOKEN else 'MISSING'}", flush=True)

def _verify_telegram_token(token: str) -> bool:
    if not token:
        print("❌ TELEGRAM_TOKEN CHECK: empty token", flush=True)
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        r = requests.get(url, timeout=15)
        data = r.json()
        if r.status_code == 200 and data.get("ok"):
            bot_info = data.get("result", {})
            print(f"✅ TELEGRAM_TOKEN CHECK: valid | bot=@{bot_info.get('username')} id={bot_info.get('id')}", flush=True)
            return True
        else:
            print(f"❌ TELEGRAM_TOKEN CHECK: invalid | status={r.status_code} | response={str(data)[:200]}", flush=True)
            return False
    except Exception as e:
        print(f"❌ TELEGRAM_TOKEN CHECK: request failed | {type(e).__name__}: {str(e)[:200]}", flush=True)
        return False

_telegram_token_ok = _verify_telegram_token(TELEGRAM_BOT_TOKEN)

if not _telegram_token_ok:
    print("❌ CRITICAL: Telegram token is invalid. Cannot start Telegram bot.", flush=True)
    print("➡️ ACTION REQUIRED:", flush=True)
    print("   1. Open @BotFather in Telegram", flush=True)
    print("   2. /mybots → your bot → API Token → copy", flush=True)
    print("   3. Update TELEGRAM_BOT_TOKEN in Railway → Variables", flush=True)
    print("   4. Railway will auto-redeploy", flush=True)
    sys.exit(1)

print("🔵 BOOT: proceeding with module imports...", flush=True)

try:
    from shared_memory import SharedMemory
    print("🔵 BOOT: memory imported", flush=True)
except Exception as e:
    print(f"❌ BOOT: memory import failed | {e}", flush=True)
    raise

try:
    from ai_engine import AIEngine
    print("🔵 BOOT: ai_engine imported", flush=True)
except Exception as e:
    print(f"❌ BOOT: ai_engine import failed | {e}", flush=True)
    raise

try:
    import fiverr_agent
    logger.info("🧑‍💻 Fiverr Agent loaded | skills=%d", len(fiverr_agent.SKILLS))
except Exception as e:
    fiverr_agent = None
    logger.warning("Fiverr Agent import failed: %s", e)
except Exception as e:
    print(f"❌ BOOT: ai_engine import failed | {e}", flush=True)
    raise

try:
    from news_engine import news_engine
    print("🔵 BOOT: news_engine imported", flush=True)
except Exception as e:
    print(f"❌ BOOT: news_engine import failed | {e}", flush=True)
    raise

try:
    import stt_engine_openrouter as stt_engine
    logger.info(f"🎙️ STT Engine loaded: {stt_engine.provider_status()} | source={stt_engine.__file__} | build={getattr(stt_engine, "STT_ENGINE_BUILD", "UNKNOWN")}")
except Exception as e:
    stt_engine = None
    logger.warning(f"STT Engine import failed: {e}")

try:
    import tavily_search
    if tavily_search.is_tavily_configured():
        logger.info(f"🌐 Tavily loaded: {tavily_search.provider_status()}")
    else:
        logger.info("ℹ️ Tavily not configured in Telegram - continuing without web search")
        tavily_search = None
except Exception as e:
    tavily_search = None
    logger.info(f"ℹ️ Tavily import failed in Telegram: {e}")

print("🔵 BOOT: initializing Memory instance...", flush=True)
try:
    memory_instance = SharedMemory("telegram", MEMORY_DB_PATH)
    print("🔵 BOOT: Memory instance created", flush=True)
except Exception as e:
    print(f"❌ BOOT: Memory init failed | {e}", flush=True)
    raise

print("🔵 BOOT: initializing AIEngine...", flush=True)
try:
    ai_engine = AIEngine(memory=memory_instance)
    print("🔵 BOOT: AIEngine created", flush=True)
except Exception as e:
    print(f"❌ BOOT: AIEngine init failed | {e}", flush=True)
    raise

logger.info("🧠 Memory + 🤖 AIEngine + 📰 NewsEngine loaded")

try:
    from ai_engine import AGNES_API_KEY as _AGNES_KEY_CHECK, AGNES_IMAGE_MODEL as _AGNES_IMG, AGNES_VIDEO_MODEL as _AGNES_VID
    if _AGNES_KEY_CHECK:
        logger.info(f"🎨 Agnes AI ready | image={_AGNES_IMG} video={_AGNES_VID}")
    else:
        logger.info("ℹ️ Agnes AI not configured - media generation disabled (set AGNES_API_KEY to enable)")
except Exception as _agnes_check_err:
    logger.info(f"ℹ️ Agnes status check skipped: {_agnes_check_err}")

DEFAULT_TIMEFRAME = "15min"
PRIMARY_EXECUTION_TF = "15min"

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


# Media URL extractors (for send_ai_response — render images/videos in Telegram)
_MEDIA_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^\s)]+)\)")
_MEDIA_VIDEO_LINK_RE = re.compile(r"\[▶ Watch Video\]\((https?://[^\s)]+)\)")
_MEDIA_DIRECT_LINK_RE = re.compile(r"\*\*Direct link:\*\*\s*(https?://[^\s\n]+)")

def clean_ai_response(text):
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\|.*?\|>", "", text)
    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<tool_call>|</tool_call>|<function_calls>|</function_calls>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"SELECT\s+.*FROM\s+price_alerts.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"king_zarry.*\.db", "", text, flags=re.IGNORECASE)
    # --- LINK REMOVAL (fix: stop attaching/citing links in signals & AI replies) ---
    # Strip markdown-style links [label](url) -> keep label text only
    text = re.sub(r"\[([^\]]+)\]\((?:https?://|www\.)[^\)]+\)", r"\1", text, flags=re.IGNORECASE)
    # Strip any raw URLs (http/https/www.)
    text = re.sub(r"(?:https?://|www\.)\S+", "", text, flags=re.IGNORECASE)
    # Strip a trailing "Sources:" / "📰 Sources:" section and everything after it
    text = re.sub(r"(?im)^\s*(📰\s*)?\*{0,2}sources?:?\*{0,2}\s*$.*", "", text, flags=re.DOTALL)
    # Collapse leftover empty markdown bullets / double blank lines created by stripping links
    text = re.sub(r"(?m)^[•\-\*]\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def escape_html(text):
    if not text:
        return ""
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    return text


def _extract_media_from_response(text: str) -> Dict[str, List[str]]:
    """Pull image/video URLs out of an AI response."""
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


async def send_ai_response(message, text, is_raw_html=False):
    """
    Send an AI response. Auto-detects generated images/videos and sends
    them via reply_photo / reply_video so they actually render in Telegram.
    Falls back to send_long_message() for plain text.

    Media URLs are extracted from the RAW response before clean_ai_response()
    strips links (so pure-text replies still get URL noise removed).
    """
    if is_raw_html:
        await send_long_message(message, text, is_raw_html=True)
        return

    # Approach A: extract media from RAW text first (before URL stripping)
    media = _extract_media_from_response(text or "")
    logger.info(
        f"send_ai_response: images={len(media['images'])} videos={len(media['videos'])}"
    )

    cleaned = clean_ai_response(text) or "King Zarry AI returned an empty response."

    # --- Images ---
    if media["images"]:
        caption_source = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text or "")
        caption_source = re.sub(r"\*\*Direct link:\*\*\s*https?://[^\s\n]+", "", caption_source)
        caption_source = clean_ai_response(caption_source)
        caption_source = re.sub(r"\n{3,}", "\n\n", caption_source).strip() or "🎨 Generated image"
        caption = caption_source[:1000]

        sent_any = False
        for url in media["images"][:5]:
            try:
                await message.reply_photo(
                    photo=url,
                    caption=escape_html(caption) if not sent_any else None,
                    parse_mode="HTML" if not sent_any else None,
                )
                sent_any = True
            except Exception as e:
                logger.warning(f"reply_photo failed for {url}: {e}")
                try:
                    await message.reply_text(f"🖼 Image link: {url}")
                    sent_any = True
                except Exception:
                    pass
        if sent_any:
            return

    # --- Videos ---
    if media["videos"]:
        sent_any = False
        for url in media["videos"][:3]:
            try:
                await message.reply_video(
                    video=url,
                    caption="🎬 Generated video" if not sent_any else None,
                    supports_streaming=True,
                )
                sent_any = True
            except Exception as e:
                logger.warning(f"reply_video failed for {url}: {e}")
                try:
                    await message.reply_text(
                        f"🎬 Video: {url}", disable_web_page_preview=False
                    )
                    sent_any = True
                except Exception:
                    pass
        if sent_any:
            return

    # --- Plain text ---
    await send_long_message(message, cleaned, is_raw_html=False)


async def send_long_message(message, text, is_raw_html=False):
    text = clean_ai_response(text)
    if not text:
        text = "King Zarry AI returned an empty response."
    formatted = text if is_raw_html else escape_html(text)
    chunk_size = 3800
    chunks = [formatted[i:i+chunk_size] for i in range(0, len(formatted), chunk_size)]
    for chunk in chunks:
        try:
            await message.reply_text(chunk, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            await message.reply_text(re.sub(r"<[^>]+>", "", chunk), parse_mode=None, disable_web_page_preview=True)

def db_connect():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = db_connect()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY, username TEXT, plan TEXT, expires_at TEXT,
            payment_method TEXT, payment_id TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, plan TEXT,
            payment_method TEXT, payment_id TEXT UNIQUE, amount INTEGER, currency TEXT,
            payload TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
            created_at TEXT, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, message TEXT,
            interval_seconds INTEGER, next_run TEXT, active INTEGER DEFAULT 1, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            target_price REAL NOT NULL,
            condition TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            triggered INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            triggered_at TEXT,
            last_checked_price REAL,
            last_checked_at TEXT
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_alerts_user ON price_alerts(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(active, triggered)")
        conn.commit()
    finally:
        conn.close()

init_database()
print("🔵 BOOT: database initialized", flush=True)

try:
    from price_alerts import (
        normalize_alert_symbol,
        parse_alert_request,
        create_price_alert,
        get_user_price_alerts,
        cancel_user_alert,
        cancel_all_user_alerts,
        get_all_active_price_alerts,
        get_current_price_for_alert,
        check_alert_triggered_v2,
        ensure_price_alerts_table,
    )
    try:
        ensure_price_alerts_table(db_connect())
    except Exception:
        pass
    print("🔵 BOOT: price_alerts imported (shared)", flush=True)
except Exception as e:
    logger.warning(f"price_alerts import failed, falling back to local: {e}")
    print(f"⚠️ BOOT: using local price_alerts fallback | {e}", flush=True)
    def normalize_alert_symbol(raw: str) -> Optional[str]:
        upper = raw.upper().strip()
        mapping = {"XAU": "XAU/USD", "XAUUSD": "XAU/USD", "XAU/USD": "XAU/USD", "GOLD": "XAU/USD", "BTC": "BTC/USD", "BTCUSD": "BTC/USD", "BTC/USD": "BTC/USD", "ETH": "ETH/USD", "ETHUSD": "ETH/USD", "ETH/USD": "ETH/USD", "SOL": "SOL/USD", "SOLUSD": "SOL/USD", "SOL/USD": "SOL/USD"}
        if upper in mapping:
            return mapping[upper]
        for k, v in mapping.items():
            if k in upper:
                return v
        return None
    def parse_alert_request(text: str) -> Optional[Dict]:
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
        symbol = normalize_alert_symbol(cleaned) or normalize_alert_symbol(original)
        if not symbol:
            return None
        condition = "REACHES"
        if re.search(r"\babove\b|\bgoes above\b", lower):
            condition = "ABOVE"
        if re.search(r"\bbelow\b|\bdrops below\b|\bfalls below\b", lower):
            condition = "BELOW" if "above" not in lower or lower.rfind("below") > lower.rfind("above") else "ABOVE"
        cmd_match = re.search(r"(above|below|reaches|reach|hit|hits)", cleaned.lower())
        if cmd_match:
            w = cmd_match.group(1)
            if w == "above":
                condition = "ABOVE"
            elif w == "below":
                condition = "BELOW"
            else:
                condition = "REACHES"
        return {"symbol": symbol, "target_price": target_price, "condition": condition, "raw": original}
    def create_price_alert(user_id: int, symbol: str, target_price: float, condition: str) -> Dict:
        now = datetime.now(timezone.utc).isoformat()
        conn = db_connect()
        try:
            existing = conn.execute("SELECT id FROM price_alerts WHERE user_id=? AND symbol=? AND target_price=? AND condition=? AND active=1", (user_id, symbol, target_price, condition)).fetchone()
            if existing:
                return {"success": False, "duplicate": True, "id": existing["id"]}
            cur = conn.cursor()
            cur.execute("INSERT INTO price_alerts (user_id, symbol, target_price, condition, active, triggered, created_at) VALUES (?,?,?,?,?,?,?)", (user_id, symbol, target_price, condition, 1, 0, now))
            conn.commit()
            return {"success": True, "id": cur.lastrowid}
        finally:
            conn.close()
    def get_user_price_alerts(user_id: int, active_only: bool = True):
        conn = db_connect()
        try:
            if active_only:
                rows = conn.execute("SELECT * FROM price_alerts WHERE user_id=? AND active=1 ORDER BY id ASC", (user_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM price_alerts WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    def cancel_user_alert(user_id: int, alert_id: int) -> bool:
        conn = db_connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE price_alerts SET active=0 WHERE id=? AND user_id=?", (alert_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    def cancel_all_user_alerts(user_id: int) -> int:
        conn = db_connect()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE price_alerts SET active=0 WHERE user_id=? AND active=1", (user_id,))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()
    def get_all_active_price_alerts():
        conn = db_connect()
        try:
            rows = conn.execute("SELECT * FROM price_alerts WHERE active=1 AND triggered=0").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    def get_current_price_for_alert(symbol: str) -> Optional[float]:
        try:
            from market import get_price as market_get_price
            price = market_get_price(symbol)
            if price:
                return float(price)
        except Exception:
            pass
        return None
    def check_alert_triggered_v2(current_price: float, target_price: float, condition: str, last_price: Optional[float] = None) -> bool:
        if condition == "ABOVE":
            return current_price >= target_price
        if condition == "BELOW":
            return current_price <= target_price
        tolerance = max(abs(target_price) * 0.002, 0.01)
        if abs(current_price - target_price) <= tolerance:
            return True
        if last_price is not None:
            if (last_price < target_price <= current_price) or (last_price > target_price >= current_price):
                return True
        return False

def save_user(user):
    if not user:
        return
    now = datetime.now(timezone.utc).isoformat()
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    conn = db_connect()
    try:
        conn.execute("""INSERT INTO users (user_id, username, first_name, last_name, created_at, updated_at)
            VALUES (?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, first_name=excluded.first_name, last_name=excluded.last_name, updated_at=excluded.updated_at""",
            (user.id, username, first_name, last_name, now, now))
        conn.commit()
    finally:
        conn.close()
    try:
        if memory_instance:
            memory_instance.register_user(user_id=str(user.id), platform="telegram", username=username, first_name=first_name, last_name=last_name)
    except Exception as e:
        logger.warning(f"Memory register warning: {e}")

def update_subscription_username(user_id, username):
    if not username:
        return
    conn = db_connect()
    try:
        conn.execute("UPDATE subscriptions SET username=? WHERE user_id=?", (username, user_id))
        conn.commit()
    finally:
        conn.close()

def is_subscribed(user_id):
    if user_id in ADMIN_IDS:
        return True
    conn = db_connect()
    try:
        row = conn.execute("SELECT expires_at FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return False
    try:
        expiry = datetime.fromisoformat(row["expires_at"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)
    except Exception:
        return False

def get_subscription(user_id):
    conn = db_connect()
    try:
        row = conn.execute("SELECT * FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def activate_subscription(user_id, username, days, plan, payment_method, payment_id=None):
    now = datetime.now(timezone.utc)
    existing = get_subscription(user_id)
    if existing:
        try:
            old_expiry = datetime.fromisoformat(existing["expires_at"])
            if old_expiry.tzinfo is None:
                old_expiry = old_expiry.replace(tzinfo=timezone.utc)
        except Exception:
            old_expiry = now
        start_from = old_expiry if old_expiry > now else now
    else:
        start_from = now
    expires_at = start_from + timedelta(days=days)
    conn = db_connect()
    try:
        conn.execute("""INSERT INTO subscriptions (user_id, username, plan, expires_at, payment_method, payment_id, created_at)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, plan=excluded.plan, expires_at=excluded.expires_at,
            payment_method=excluded.payment_method, payment_id=excluded.payment_id""",
            (user_id, username, plan, expires_at.isoformat(), payment_method, payment_id, now.isoformat()))
        conn.commit()
    finally:
        conn.close()
    try:
        if memory_instance:
            memory_instance.set_user_subscription(str(user_id), True, expires_at.isoformat())
    except Exception:
        pass
    return expires_at

def deactivate_subscription(user_id):
    conn = db_connect()
    try:
        conn.execute("DELETE FROM subscriptions WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    try:
        if memory_instance:
            memory_instance.set_user_subscription(str(user_id), False, None)
    except Exception:
        pass

def record_payment(user_id, username, plan, payment_method, payment_id, amount, currency, payload):
    conn = db_connect()
    try:
        conn.execute("""INSERT INTO payments (user_id, username, plan, payment_method, payment_id, amount, currency, payload, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, username, plan, payment_method, payment_id, amount, currency, payload, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_payment_history(user_id, limit=10):
    conn = db_connect()
    try:
        return conn.execute("SELECT plan, payment_method, amount, currency, created_at FROM payments WHERE user_id=? ORDER BY id DESC LIMIT?", (user_id, limit)).fetchall()
    finally:
        conn.close()

def get_all_subscribers():
    conn = db_connect()
    try:
        return conn.execute("""SELECT s.user_id, COALESCE(NULLIF(s.username,''), NULLIF(u.username,''), '') AS username,
            COALESCE(u.first_name,'') AS first_name, COALESCE(u.last_name,'') AS last_name,
            s.plan, s.expires_at, s.payment_method, s.payment_id, s.created_at
            FROM subscriptions s LEFT JOIN users u ON u.user_id=s.user_id ORDER BY s.created_at DESC""").fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = db_connect()
    try:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [row["user_id"] for row in rows]
    finally:
        conn.close()

def get_user_count():
    conn = db_connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])
    finally:
        conn.close()

def get_payment_stats():
    conn = db_connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS payments, COALESCE(SUM(amount),0) AS stars FROM payments").fetchone()
        return {"payments": int(row["payments"]), "stars": int(row["stars"])}
    finally:
        conn.close()

def user_has_access(user_id):
    return user_id in ADMIN_IDS or is_subscribed(user_id)

async def require_subscription(update):
    user = update.effective_user
    if not user:
        return False
    save_user(user)
    if user_has_access(user.id):
        return True
    if update.message:
        await update.message.reply_text(
            "🔒 <b>KING ZARRY AI VIP</b>\n\nYour VIP access is not active.\n\n"
            "👑 VIP unlocks:\n• AI Chat\n• Image & Video Generation (Agnes AI)\n• Multi-Timeframe Signals 4H→1H→15M→5M\n• News + Economic Calendar\n• BTC / ETH / SOL / XAU\n• AI Vision\n• /plan One-Day Trade Plan\n• TTS\n\nUse /buy to activate VIP.",
            parse_mode="HTML")
    return False

def ask_ai(prompt: str, user_id: str = "system"):
    if not ai_engine:
        raise RuntimeError("AI Engine not initialized")
    return ai_engine.ask(user_id=str(user_id), prompt=prompt, image=None)

def analyze_image_with_ai(image_bytes: bytes, mime_type: str, prompt: str, user_id: str = "vision_user"):
    if not ai_engine:
        raise RuntimeError("AI Engine not initialized")
    return ai_engine.ask(user_id=str(user_id), prompt=prompt, image=(mime_type, image_bytes))

async def create_voice_note_file(text: str) -> BytesIO:
    if ai_engine:
        try:
            audio_io = await asyncio.to_thread(ai_engine.generate_speech, text)
            if isinstance(audio_io, BytesIO):
                audio_io.seek(0)
                audio_io.name = "voice.mp3"
                return audio_io
            if isinstance(audio_io, (bytes, bytearray)):
                bio = BytesIO(bytes(audio_io))
                bio.seek(0)
                bio.name = "voice.mp3"
                return bio
        except Exception as e:
            logger.warning(f"ElevenLabs via engine failed, trying edge_tts: {e}")
    try:
        import edge_tts
        temp_dir = tempfile.mkdtemp(prefix="king_zarry_tts_")
        output_file = os.path.join(temp_dir, "voice.mp3")
        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        await communicate.save(output_file)
        with open(output_file, "rb") as f:
            bio = BytesIO(f.read())
        shutil.rmtree(temp_dir, ignore_errors=True)
        bio.seek(0)
        bio.name = "voice.mp3"
        return bio
    except Exception as e:
        raise RuntimeError(f"TTS unavailable: {e}")

def get_market_candles(symbol, interval=DEFAULT_TIMEFRAME, outputsize=150):
    """Candles via market.py — Binance free for crypto, Twelve for gold/forex."""
    try:
        from market import get_candles as _m_get_candles
        tf = str(interval or "15m").lower().strip()
        # bot historically used 15min/5min Twelve names
        tf = {"15min": "15m", "5min": "5m", "1min": "1m", "30min": "30m", "1day": "1d"}.get(tf, tf)
        candles = _m_get_candles(symbol, tf, outputsize)
        if not candles or len(candles) < 15:
            raise RuntimeError(f"Only {len(candles) if candles else 0} candles for {symbol}")
        return candles
    except Exception as e:
        # Legacy Twelve path as last resort
        if not TWELVE_DATA_API_KEY:
            raise RuntimeError(f"Market data unavailable for {symbol}: {e}")
        response = requests.get(
            f"{TWELVE_DATA_URL}/time_series",
            params={"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_API_KEY},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "error":
            raise RuntimeError(data.get("message", "Twelve Data error."))
        values = data.get("values", [])
        if len(values) < 15:
            raise RuntimeError(f"Only {len(values)} candles were returned for {symbol}.")
        return list(reversed(values))

def ema(values, period):
    if len(values) < period:
        return sum(values) / len(values)
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result

def rsi(values, period=14):
    if len(values) < period + 1:
        return 50.0
    gains = [max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses = [max(values[i-1]-values[i],0) for i in range(1,len(values))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period-1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period-1)) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    if len(closes) < 2:
        return 0.0
    ranges = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1,len(closes))]
    if len(ranges) < period:
        return sum(ranges)/len(ranges)
    return sum(ranges[-period:])/period

def find_swing_levels(highs, lows, lookback=40):
    lookback = min(lookback, len(highs))
    return (min(lows[-lookback:]), max(highs[-lookback:]))

def detect_structure(highs, lows, closes):
    if len(closes) < 20:
        return "NEUTRAL"
    first = closes[-20:-10]
    second = closes[-10:]
    if max(second) > max(first) and min(second) > min(first):
        return "BULLISH"
    if max(second) < max(first) and min(second) < min(first):
        return "BEARISH"
    return "NEUTRAL"

def candle_momentum(opens, closes, count=5):
    opens = opens[-count:]
    closes = closes[-count:]
    bullish = sum(1 for o,c in zip(opens, closes) if c>o)
    bearish = sum(1 for o,c in zip(opens, closes) if c<o)
    return bullish, bearish

def detect_fresh_cross(closes, fast_period=9, slow_period=21, lookback=4):
    if len(closes) < slow_period + lookback + 1:
        return False, None
    diffs = []
    for i in range(len(closes)-lookback-1, len(closes)+1):
        window = closes[:i]
        if len(window) < slow_period:
            diffs.append(0)
            continue
        diffs.append(ema(window, fast_period)-ema(window, slow_period))
    fresh=False
    direction=None
    for i in range(1,len(diffs)):
        if diffs[i-1]<=0<diffs[i]:
            fresh=True
            direction="UP"
        elif diffs[i-1]>=0>diffs[i]:
            fresh=True
            direction="DOWN"
    return fresh, direction

def detect_exhaustion(price, ema21, current_atr, current_rsi):
    if current_atr<=0:
        return False
    distance=abs(price-ema21)/current_atr
    if current_rsi>=78 and distance>=2.2:
        return True
    if current_rsi<=22 and distance>=2.2:
        return True
    return False

def detect_volatility_spike(highs, lows, closes):
    if len(closes)<45:
        return False
    recent_atr=atr(highs[-15:],lows[-15:],closes[-15:],14)
    baseline_atr=atr(highs[-45:-15],lows[-45:-15],closes[-45:-15],14)
    if baseline_atr<=0:
        return False
    return recent_atr>baseline_atr*1.8

def detect_exhaustion_advanced(price, ema9, ema21, ema50, current_atr, current_rsi, highs, lows, closes, opens):
    warnings = []
    score = 0
    if current_atr <= 0:
        return {"exhausted": False, "score": 0, "warnings": []}
    distance_ema21 = abs(price - ema21) / current_atr
    distance_ema50 = abs(price - ema50) / current_atr if ema50 else 0
    if current_rsi >= 78:
        warnings.append(f"RSI overbought {current_rsi:.1f}")
        score += 30
    elif current_rsi <= 22:
        warnings.append(f"RSI oversold {current_rsi:.1f}")
        score += 30
    elif current_rsi >= 72 or current_rsi <= 28:
        score += 15
    if distance_ema21 >= 3.0:
        warnings.append(f"Price extremely extended from EMA21 ({distance_ema21:.1f} ATR)")
        score += 35
    elif distance_ema21 >= 2.2:
        warnings.append(f"Price extended from EMA21 ({distance_ema21:.1f} ATR)")
        score += 20
    if distance_ema50 >= 4.0:
        warnings.append(f"Far from EMA50 major trend ({distance_ema50:.1f} ATR)")
        score += 20
    if len(closes) >= 7:
        bullish_run = 0
        bearish_run = 0
        for i in range(-1, -8, -1):
            try:
                if closes[i] > opens[i]:
                    bullish_run += 1
                else:
                    break
            except:
                break
        for i in range(-1, -8, -1):
            try:
                if closes[i] < opens[i]:
                    bearish_run += 1
                else:
                    break
            except:
                break
        if bullish_run >= 5:
            warnings.append(f"{bullish_run} consecutive bullish candles - exhaustion risk")
            score += 25
        if bearish_run >= 5:
            warnings.append(f"{bearish_run} consecutive bearish candles - exhaustion risk")
            score += 25
    if len(closes) >= 15:
        recent_range = highs[-1] - lows[-1]
        avg_range = sum(highs[i]-lows[i] for i in range(-15, -1)) / 14 if len(highs) >= 15 else recent_range
        if avg_range > 0 and recent_range > avg_range * 2.5:
            warnings.append(f"Abnormal candle expansion ({recent_range/avg_range:.1f}x avg)")
            score += 20
    if len(highs) >= 20:
        recent_high = max(highs[-20:-1])
        recent_low = min(lows[-20:-1])
        if price > recent_high and closes[-1] < recent_high:
            warnings.append("Failed bullish breakout - wick rejection")
            score += 25
        if price < recent_low and closes[-1] > recent_low:
            warnings.append("Failed bearish breakdown - wick rejection")
            score += 25
    return {
        "exhausted": score >= 50,
        "score": min(score, 100),
        "warnings": warnings[:4],
        "distance_ema21": distance_ema21,
        "distance_ema50": distance_ema50
    }

def detect_late_entry_status(data_15m, data_5m=None, data_1h=None):
    if not data_15m:
        return {"status": "UNKNOWN", "emoji": "⚪", "reasons": [], "action": "WAIT"}
    price = data_15m["price"]
    atr_val = data_15m.get("atr", 0)
    rsi_val = data_15m.get("rsi", 50)
    ema21 = data_15m.get("ema21", price)
    support = data_15m.get("support", price)
    resistance = data_15m.get("resistance", price)
    signal = data_15m.get("signal", "WAIT")
    if atr_val <= 0:
        atr_val = price * 0.002
    score = 0
    reasons = []
    dist_ema = abs(price - ema21) / atr_val if atr_val else 0
    if dist_ema >= 3.5:
        score += 40
        reasons.append(f"Price {dist_ema:.1f} ATR from EMA21 - extended")
    elif dist_ema >= 2.0:
        score += 20
        reasons.append(f"Price {dist_ema:.1f} ATR from EMA21")
    if signal == "BUY":
        dist_from_support = (price - support) / atr_val if atr_val else 0
        if dist_from_support >= 4.0:
            score += 30
            reasons.append(f"Already {dist_from_support:.1f} ATR above support - late")
        entry_zone = data_15m.get("entry_zone_high", price)
        if price > entry_zone + atr_val * 1.5:
            score += 25
            reasons.append("Price beyond entry zone + 1.5 ATR")
    elif signal == "SELL":
        dist_from_resistance = (resistance - price) / atr_val if atr_val else 0
        if dist_from_resistance >= 4.0:
            score += 30
            reasons.append(f"Already {dist_from_resistance:.1f} ATR below resistance - late")
    if (signal == "BUY" and rsi_val >= 72) or (signal == "SELL" and rsi_val <= 28):
        score += 20
        reasons.append(f"RSI {rsi_val:.1f} suggests late entry")
    if data_5m:
        if data_5m.get("signal") != signal and signal != "WAIT":
            score += 15
            reasons.append(f"5M {data_5m.get('signal')} conflicts with 15M {signal}")
        if data_5m.get("exhaustion_advanced", {}).get("exhausted"):
            score += 20
            reasons.append("5M shows exhaustion")
    entry = data_15m.get("entry", price)
    tp3 = data_15m.get("tp3", price)
    sl = data_15m.get("stop_loss", price)
    if signal in ["BUY", "SELL"] and entry != sl:
        risk = abs(entry - sl)
        if risk > 0:
            remaining_rr = abs(tp3 - price) / risk if signal == "BUY" else abs(price - tp3) / risk
            if remaining_rr < 1.0:
                score += 35
                reasons.append(f"Only {remaining_rr:.1f}R remaining - poor RR")
            elif remaining_rr < 1.5:
                score += 15
                reasons.append(f"Only {remaining_rr:.1f}R left")
    if score >= 70:
        status = "EXTENDED / AVOID"
        emoji = "🔴"
        action = "WAIT FOR PULLBACK"
    elif score >= 45:
        status = "LATE"
        emoji = "🟠"
        action = "WAIT FOR RETEST"
    elif score >= 25:
        status = "ACCEPTABLE"
        emoji = "🟡"
        action = "ACCEPTABLE WITH REDUCED SIZE"
    else:
        status = "EARLY"
        emoji = "🟢"
        action = "EARLY - GOOD ENTRY WINDOW"
    if signal == "WAIT":
        status = "NO SETUP"
        emoji = "⚪"
        action = "WAIT"
    return {
        "status": status,
        "emoji": emoji,
        "score": score,
        "reasons": reasons[:3],
        "action": action,
        "dist_ema": dist_ema
    }

def analyze_market(closes, highs, lows, opens, symbol, interval=DEFAULT_TIMEFRAME):
    price=closes[-1]
    ema9=ema(closes,9)
    ema21=ema(closes,21)
    ema50=ema(closes,50)
    current_rsi=rsi(closes,14)
    previous_rsi=rsi(closes[:-1],14)
    current_atr=atr(highs,lows,closes,14)
    support,resistance=find_swing_levels(highs,lows,40)
    structure=detect_structure(highs,lows,closes)
    fresh_cross,cross_direction=detect_fresh_cross(closes)
    is_exhausted=detect_exhaustion(price,ema21,current_atr,current_rsi)
    is_volatile_spike=detect_volatility_spike(highs,lows,closes)
    exhaustion_adv = detect_exhaustion_advanced(price, ema9, ema21, ema50, current_atr, current_rsi, highs, lows, closes, opens)
    bullish_score=0.0
    bearish_score=0.0
    reasons_buy=[]
    reasons_sell=[]
    if ema9>ema21>ema50:
        bullish_score+=22
        reasons_buy.append("EMA 9 > EMA 21 > EMA 50")
    elif ema9>ema21:
        bullish_score+=10
        reasons_buy.append("Short-term EMA bullish")
    if ema9<ema21<ema50:
        bearish_score+=22
        reasons_sell.append("EMA 9 < EMA 21 < EMA 50")
    elif ema9<ema21:
        bearish_score+=10
        reasons_sell.append("Short-term EMA bearish")
    if price>ema9:
        bullish_score+=8
        reasons_buy.append("Price above EMA 9")
    else:
        bearish_score+=8
        reasons_sell.append("Price below EMA 9")
    if price>ema21:
        bullish_score+=7
    else:
        bearish_score+=7
    if price>ema50:
        bullish_score+=8
    else:
        bearish_score+=8
    rsi_rising=(current_rsi>previous_rsi)
    if 52<=current_rsi<=68:
        bullish_score+=12
        if rsi_rising:
            bullish_score+=5
        reasons_buy.append(f"Healthy bullish RSI {current_rsi:.1f}")
    elif 32<=current_rsi<=48:
        bearish_score+=12
        if not rsi_rising:
            bearish_score+=5
        reasons_sell.append(f"Bearish RSI {current_rsi:.1f}")
    elif current_rsi>75:
        bearish_score+=12
        reasons_sell.append("RSI overbought")
    elif current_rsi<25:
        bullish_score+=12
        reasons_buy.append("RSI oversold")
    if structure=="BULLISH":
        bullish_score+=15
        reasons_buy.append("Bullish market structure")
    elif structure=="BEARISH":
        bearish_score+=15
        reasons_sell.append("Bearish market structure")
    if fresh_cross and cross_direction=="UP":
        bullish_score+=10
        reasons_buy.append("Fresh bullish EMA crossover")
    elif fresh_cross and cross_direction=="DOWN":
        bearish_score+=10
        reasons_sell.append("Fresh bearish EMA crossover")
    if is_exhausted:
        bullish_score=max(0,bullish_score-15)
        bearish_score=max(0,bearish_score-15)
    if 0<=price-support<=current_atr*1.25:
        bullish_score+=12
        reasons_buy.append("Price near support")
    if 0<=resistance-price<=current_atr*1.25:
        bearish_score+=12
        reasons_sell.append("Price near resistance")
    if price>resistance:
        bullish_score+=18
        reasons_buy.append("Resistance breakout")
    if price<support:
        bearish_score+=18
        reasons_sell.append("Support breakdown")
    bullish_candles,bearish_candles=candle_momentum(opens,closes,5)
    if bullish_candles>=4:
        bullish_score+=10
        reasons_buy.append("Strong bullish candle momentum")
    elif bearish_candles>=4:
        bearish_score+=10
        reasons_sell.append("Strong bearish candle momentum")
    elif bullish_candles>bearish_candles:
        bullish_score+=5
    elif bearish_candles>bullish_candles:
        bearish_score+=5
    if len(closes)>=6:
        momentum=closes[-1]-closes[-6]
        if momentum>0:
            bullish_score+=8
            reasons_buy.append("Positive short-term momentum")
        elif momentum<0:
            bearish_score+=8
            reasons_sell.append("Negative short-term momentum")
    max_score=120.0
    bullish_percent=int((min(bullish_score,max_score)/max_score)*100)
    bearish_percent=int((min(bearish_score,max_score)/max_score)*100)
    difference=abs(bullish_percent-bearish_percent)
    ema_spread=(abs(ema9-ema21)/price if price else 0)
    is_flat_market=(difference<10 or (48<=current_rsi<=52 and ema_spread<0.0002) or (structure=="NEUTRAL" and difference<14) or is_exhausted or is_volatile_spike)
    if is_flat_market:
        signal="WAIT"
        confidence="LOW"
        strength=max(bullish_percent,bearish_percent)
        reasons=[]
        if difference<10:
            reasons.append("Market is sideways with conflicting signals")
        if 48<=current_rsi<=52:
            reasons.append(f"RSI is neutral ({current_rsi:.1f})")
        if ema_spread<0.0002:
            reasons.append("EMAs are flat and compressing")
        if structure=="NEUTRAL":
            reasons.append("No clear higher highs or lower lows")
        if is_exhausted:
            reasons.append("Move looks exhausted/over-extended -- late entry risk")
        if is_volatile_spike:
            reasons.append("Volatility just spiked -- choppy/news-driven tape")
    elif bullish_percent>bearish_percent:
        signal="BUY"
        strength=bullish_percent
        confidence="HIGH" if strength>=75 else "MEDIUM"
        reasons=reasons_buy
    else:
        signal="SELL"
        strength=bearish_percent
        confidence="HIGH" if strength>=75 else "MEDIUM"
        reasons=reasons_sell
    if current_atr<=0:
        current_atr=price*0.002
    if signal=="BUY":
        entry_low=max(support,price-current_atr*0.35)
        entry_high=price
        entry=(entry_low+entry_high)/2
        stop_loss=min(support-current_atr*0.25,entry-current_atr*1.05)
        risk=max(entry-stop_loss,current_atr)
        stop_loss=entry-risk if entry-stop_loss<=0 else stop_loss
        tp1=entry+risk*1.5
        tp2=entry+risk*2.5
        tp3=entry+risk*3.5
    elif signal=="SELL":
        entry_low=price
        entry_high=min(resistance,price+current_atr*0.35)
        entry=(entry_low+entry_high)/2
        stop_loss=max(resistance+current_atr*0.25,entry+current_atr*1.05)
        risk=max(stop_loss-entry,current_atr)
        stop_loss=entry+risk if stop_loss-entry<=0 else stop_loss
        tp1=entry-risk*1.5
        tp2=entry-risk*2.5
        tp3=entry-risk*3.5
    else:
        entry_low=price
        entry_high=price
        entry=price
        stop_loss=price-current_atr
        tp1=price+current_atr
        tp2=price+current_atr*2
        tp3=price+current_atr*3
        risk=current_atr
    return {"symbol": symbol, "interval": interval, "price": price, "signal": signal,
            "trend": ("BULLISH" if bullish_percent>bearish_percent else "BEARISH" if bearish_percent>bullish_percent else "NEUTRAL"),
            "structure": structure, "strength": strength, "confidence": confidence,
            "bullish_score": bullish_percent, "bearish_score": bearish_percent, "score_difference": difference,
            "rsi": current_rsi, "ema9": ema9, "ema21": ema21, "ema50": ema50, "atr": current_atr,
            "support": support, "resistance": resistance,
            "demand_low": support, "demand_high": support+current_atr*0.55,
            "supply_low": resistance-current_atr*0.55, "supply_high": resistance,
            "entry": entry, "entry_zone_low": entry_low, "entry_zone_high": entry_high,
            "stop_loss": stop_loss, "tp1": tp1, "tp2": tp2, "tp3": tp3, "risk": risk, "rr": 3.5,
            "reasons": reasons[:6], "fresh_cross": fresh_cross, "exhausted": is_exhausted,
            "volatility_spike": is_volatile_spike, "exhaustion_advanced": exhaustion_adv, "candles": []}

def analyze_symbol(symbol, interval=DEFAULT_TIMEFRAME):
    candles=get_market_candles(symbol,interval,150)
    closes=[float(c["close"]) for c in candles]
    highs=[float(c["high"]) for c in candles]
    lows=[float(c["low"]) for c in candles]
    opens=[float(c["open"]) for c in candles]
    result=analyze_market(closes,highs,lows,opens,symbol,interval)
    result["candles"]=candles
    return result

def analyze_single_timeframe_safe(symbol, interval, outputsize=150):
    try:
        candles = get_market_candles(symbol, interval, outputsize)
        closes=[float(c["close"]) for c in candles]
        highs=[float(c["high"]) for c in candles]
        lows=[float(c["low"]) for c in candles]
        opens=[float(c["open"]) for c in candles]
        result=analyze_market(closes,highs,lows,opens,symbol,interval)
        result["candles"]=candles
        result["error"] = None
        return result
    except Exception as e:
        logger.warning(f"TF {interval} failed for {symbol}: {e}")
        return {"symbol": symbol, "interval": interval, "signal": "WAIT", "trend": "NEUTRAL", "error": str(e), "price": 0, "candles": [], "rsi": 50, "ema9":0, "ema21":0, "ema50":0, "atr":0, "support":0, "resistance":0, "strength":0, "confidence":"LOW", "reasons":[f"{interval} data unavailable: {e}"], "exhaustion_advanced": {"exhausted": False, "score":0, "warnings":[]}}

def analyze_multi_timeframe(symbol):
    tf_4h = analyze_single_timeframe_safe(symbol, "4h", 150)
    tf_1h = analyze_single_timeframe_safe(symbol, "1h", 150)
    tf_15m = analyze_single_timeframe_safe(symbol, "15min", 150)
    tf_5m = analyze_single_timeframe_safe(symbol, "5min", 150)
    signals = [tf_4h.get("signal"), tf_1h.get("signal"), tf_15m.get("signal"), tf_5m.get("signal")]
    trends = [tf_4h.get("trend"), tf_1h.get("trend"), tf_15m.get("trend"), tf_5m.get("trend")]
    bullish_count = sum(1 for s in signals if s == "BUY") + sum(1 for t in trends if t == "BULLISH")
    bearish_count = sum(1 for s in signals if s == "SELL") + sum(1 for t in trends if t == "BEARISH")
    regime_4h = tf_4h.get("trend", "NEUTRAL")
    if tf_4h.get("signal") == "BUY" and tf_4h.get("trend") == "BULLISH":
        regime_4h = "BULLISH"
    elif tf_4h.get("signal") == "SELL" and tf_4h.get("trend") == "BEARISH":
        regime_4h = "BEARISH"
    confirm_1h = tf_1h.get("trend", "NEUTRAL")
    if bullish_count >= 5:
        mtf_bias = "BULLISH"
        mtf_signal = "BUY"
    elif bearish_count >= 5:
        mtf_bias = "BEARISH"
        mtf_signal = "SELL"
    elif bullish_count >= 3 and tf_15m.get("signal") == "BUY":
        mtf_bias = "BULLISH"
        mtf_signal = "BUY"
    elif bearish_count >= 3 and tf_15m.get("signal") == "SELL":
        mtf_bias = "BEARISH"
        mtf_signal = "SELL"
    else:
        mtf_bias = "NEUTRAL"
        mtf_signal = "WAIT"
    conflict = False
    if tf_4h.get("trend") == "BULLISH" and tf_1h.get("trend") == "BEARISH":
        conflict = True
    if tf_4h.get("trend") == "BEARISH" and tf_1h.get("trend") == "BULLISH":
        conflict = True
    base_strength = tf_15m.get("strength", 0)
    mtf_strength = base_strength
    if mtf_bias != "NEUTRAL" and tf_15m.get("signal") == mtf_signal:
        if tf_4h.get("trend") == tf_15m.get("trend") and tf_1h.get("trend") == tf_15m.get("trend"):
            mtf_strength = min(100, base_strength + 15)
        elif tf_4h.get("trend") == tf_15m.get("trend") or tf_1h.get("trend") == tf_15m.get("trend"):
            mtf_strength = min(100, base_strength + 7)
    elif conflict:
        mtf_strength = max(0, base_strength - 20)
    return {
        "symbol": symbol, "4h": tf_4h, "1h": tf_1h, "15m": tf_15m, "5m": tf_5m,
        "mtf_bias": mtf_bias, "mtf_signal": mtf_signal,
        "bullish_count": bullish_count, "bearish_count": bearish_count,
        "conflict": conflict, "regime_4h": regime_4h, "confirm_1h": confirm_1h,
        "mtf_strength": mtf_strength, "primary": tf_15m
    }

def ai_confirm_signal_mtf(mtf_data, news_data=None):
    data_15m = mtf_data.get("15m", {})
    if data_15m.get("signal") == "WAIT" and mtf_data.get("mtf_signal") == "WAIT":
        return mtf_data
    try:
        tf_4h = mtf_data["4h"]
        tf_1h = mtf_data["1h"]
        tf_15m = mtf_data["15m"]
        tf_5m = mtf_data["5m"]
        late_entry = detect_late_entry_status(tf_15m, tf_5m, tf_1h)
        exhaustion = tf_15m.get("exhaustion_advanced", {})
        summary = f"""
You are King Zarry AI trading decision engine. Analyze MULTI-TIMEFRAME data and give final verdict.

Symbol: {mtf_data['symbol']}
Primary Execution: 15M

4H (Major Regime):
- Trend: {tf_4h.get('trend')} Signal: {tf_4h.get('signal')} Strength: {tf_4h.get('strength')}
- RSI: {tf_4h.get('rsi',0):.1f} EMA9: {tf_4h.get('ema9',0):.2f} EMA21: {tf_4h.get('ema21',0):.2f} EMA50: {tf_4h.get('ema50',0):.2f}
- Support: {tf_4h.get('support',0):.2f} Resistance: {tf_4h.get('resistance',0):.2f}
- Structure: {tf_4h.get('structure')} Reasons: {'; '.join(tf_4h.get('reasons',[])[:2])}

1H (Directional Confirmation):
- Trend: {tf_1h.get('trend')} Signal: {tf_1h.get('signal')} Strength: {tf_1h.get('strength')}
- RSI: {tf_1h.get('rsi',0):.1f} EMA21: {tf_1h.get('ema21',0):.2f} EMA50: {tf_1h.get('ema50',0):.2f}
- Structure: {tf_1h.get('structure')}

15M (PRIMARY SETUP):
- Price: {tf_15m.get('price',0):.2f} Signal: {tf_15m.get('signal')} Strength: {tf_15m.get('strength')}/100 Confidence: {tf_15m.get('confidence')}
- RSI: {tf_15m.get('rsi',0):.1f} EMA9: {tf_15m.get('ema9',0):.2f} EMA21: {tf_15m.get('ema21',0):.2f} EMA50: {tf_15m.get('ema50',0):.2f} ATR: {tf_15m.get('atr',0):.2f}
- Support: {tf_15m.get('support',0):.2f} Resistance: {tf_15m.get('resistance',0):.2f}
- Structure: {tf_15m.get('structure')} Fresh Cross: {tf_15m.get('fresh_cross')} Exhausted: {tf_15m.get('exhausted')}
- Reasons: {'; '.join(tf_15m.get('reasons',[])[:3])}
- Entry: {tf_15m.get('entry',0):.2f} SL: {tf_15m.get('stop_loss',0):.2f} TP3: {tf_15m.get('tp3',0):.2f}

5M (Entry Timing):
- Signal: {tf_5m.get('signal')} Trend: {tf_5m.get('trend')} RSI: {tf_5m.get('rsi',0):.1f}
- Structure: {tf_5m.get('structure')} Strength: {tf_5m.get('strength')}

MTF Consensus:
- Bias: {mtf_data.get('mtf_bias')} Signal: {mtf_data.get('mtf_signal')} Strength: {mtf_data.get('mtf_strength')}
- Conflict: {mtf_data.get('conflict')} Bullish Count: {mtf_data.get('bullish_count')} Bearish Count: {mtf_data.get('bearish_count')}

Late Entry Detection:
- Status: {late_entry['status']} Score: {late_entry['score']} Action: {late_entry['action']}
- Reasons: {'; '.join(late_entry['reasons'])}

Exhaustion:
- Score: {exhaustion.get('score',0)} Exhausted: {exhaustion.get('exhausted')} Warnings: {'; '.join(exhaustion.get('warnings',[])[:2])}

News:
- Risk: {news_data.get('risk','LOW') if news_data else 'LOW'} Events: {len(news_data.get('events',[])) if news_data else 0}

Based on ALL data above, is this reasonably timed quality setup, or late/over-extended/low-quality?

Reply format EXACTLY:
CONFIRM - 12 words max reason
or REJECT - 12 words max reason
or UNSURE - 12 words max reason
"""
        reply = ask_ai(summary, user_id="market_engine_mtf")
        reply = reply.strip()
        if not reply:
            return mtf_data
        verdict = reply.split()[0].upper().strip(":-")
        mtf_data["ai_verdict"] = reply
        mtf_data["ai_verdict_raw"] = reply
        if verdict == "REJECT":
            mtf_data["15m"]["signal"] = "WAIT"
            mtf_data["15m"]["confidence"] = "LOW"
            mtf_data["15m"]["reasons"] = [f"AI MTF cross-check: {reply}"]
            mtf_data["mtf_signal"] = "WAIT"
        elif verdict == "UNSURE" and mtf_data["15m"]["confidence"] == "MEDIUM":
            mtf_data["15m"]["confidence"] = "LOW"
    except Exception as error:
        logger.warning(f"AI MTF cross-check skipped: {error}")
    return mtf_data

def ai_confirm_signal(data):
    if data["signal"] == "WAIT":
        return data
    try:
        summary = (f"Symbol: {data['symbol']} ({data['interval']})\nCurrent price: {data['price']:.2f}\n"
                   f"Algorithmic call: {data['signal']} (confidence {data['confidence']}, strength {data['strength']}/100)\n"
                   f"RSI14: {data['rsi']:.1f}\nEMA9: {data['ema9']:.2f} / EMA21: {data['ema21']:.2f} / EMA50: {data['ema50']:.2f}\n"
                   f"Structure: {data['structure']}\nSupport: {data['support']:.2f} / Resistance: {data['resistance']:.2f}\n"
                   f"Fresh EMA crossover: {data['fresh_cross']}\nLooks exhausted/over-extended: {data['exhausted']}\n"
                   f"Recent volatility spike: {data['volatility_spike']}\nReasons: {'; '.join(data['reasons'])}\n\n"
                   "Based ONLY on data above, is this reasonably timed setup? Reply exactly: CONFIRM, REJECT, or UNSURE - plus reason 12 words max.")
        reply = ask_ai(summary, user_id="market_engine")
        reply = reply.strip()
        if not reply:
            return data
        verdict = reply.split()[0].upper().strip(":-")
        data["ai_verdict"] = reply
        if verdict == "REJECT":
            data["signal"] = "WAIT"
            data["confidence"] = "LOW"
            data["reasons"] = [f"AI cross-check flagged: {reply}"]
        elif verdict == "UNSURE" and data["confidence"] == "MEDIUM":
            data["confidence"] = "LOW"
    except Exception as error:
        logger.warning(f"AI cross-check skipped: {error}")
    return data

def format_signal_mtf(mtf_data, news_data=None):
    tf_15m = mtf_data.get("15m", {})
    tf_4h = mtf_data.get("4h", {})
    tf_1h = mtf_data.get("1h", {})
    tf_5m = mtf_data.get("5m", {})
    signal = mtf_data.get("mtf_signal", tf_15m.get("signal", "WAIT"))
    data = tf_15m
    data["signal"] = signal
    late_entry = detect_late_entry_status(tf_15m, tf_5m, tf_1h)
    exhaustion_adv = tf_15m.get("exhaustion_advanced", {})
    if signal == "BUY":
        emoji = "🟢"
        action = "BUY"
    elif signal == "SELL":
        emoji = "🔴"
        action = "SELL"
    else:
        emoji = "⏳"
        action = "WAIT / NO TRADE"
    confidence_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "⚠️"}.get(data.get("confidence", "LOW"), "⚠️")
    def tf_icon(tf_data):
        s = tf_data.get("signal", "WAIT")
        t = tf_data.get("trend", "NEUTRAL")
        if s == "BUY" or t == "BULLISH":
            return "🟢 BULLISH"
        elif s == "SELL" or t == "BEARISH":
            return "🔴 BEARISH"
        else:
            return "⚪ NEUTRAL"
    mtf_block = f"4H: {tf_icon(tf_4h)} (Major Regime)\n1H: {tf_icon(tf_1h)} (Directional)\n15M: {tf_icon(tf_15m)} (Primary Setup)\n5M: {tf_icon(tf_5m)} (Entry Timing)"
    news_block = ""
    if news_data:
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "EXTREME": "🔴"}.get(news_data.get("risk", "LOW"), "⚪")
        news_block = f"{risk_emoji} NEWS RISK: {news_data.get('risk','LOW')}\n"
        if news_data.get("events"):
            news_block += f"📅 {len(news_data['events'])} events in 24H\n"
            for ev in news_data["events"][:2]:
                news_block += f"• {ev.get('event','')[:50]} - {ev.get('time','')}\n"
        if news_data.get("risk") in ["HIGH", "EXTREME"]:
            news_block += "⚠️ High volatility expected - reduce size\n"
    else:
        news_block = "📰 NEWS RISK: LOW\n📅 No high-impact events\n📰 Status: NEWS DATA UNAVAILABLE\n"
    late_block = f"{late_entry['emoji']} ENTRY STATUS: {late_entry['status']}\n📍 Action: {late_entry['action']}\n"
    if late_entry["reasons"]:
        late_block += f"Reasons: {'; '.join(late_entry['reasons'][:2])}\n"
    exh_block = ""
    if exhaustion_adv.get("exhausted"):
        exh_block = f"⚠️ EXHAUSTION WARNING (Score {exhaustion_adv.get('score',0)}/100)\n"
        for w in exhaustion_adv.get("warnings", [])[:2]:
            exh_block += f"• {w}\n"
    ai_verdict = mtf_data.get("ai_verdict", data.get("ai_verdict"))
    ai_line = (f"🧠 <b>AI VERDICT:</b>\n{html.escape(ai_verdict)}\n\n" if ai_verdict else "")
    reasons = "\n".join(f"{i+1}. {reason}" for i, reason in enumerate(data.get("reasons", [])[:5]))
    interval_display = "15M"
    if signal == "WAIT":
        next_trigger = ""
        if mtf_data.get("conflict"):
            next_trigger = f"Next trigger: Wait for 4H/1H alignment. 4H is {tf_4h.get('trend')} but 1H is {tf_1h.get('trend')}."
        elif tf_15m.get("trend") == "NEUTRAL":
            next_trigger = "Next trigger: Wait for 15M reclaim above EMA21 and 5M bullish confirmation."
        else:
            next_trigger = f"Next trigger: Wait for 15M {mtf_data.get('mtf_bias')} reclaim and 5M confirmation."
        return (f"👑 <b>KING ZARRY AI • {data.get('symbol','')} SIGNAL</b>\n\n{emoji} <b>STATUS: {action}</b>\n⏱ Execution: <b>{interval_display}</b>\n\n"
                f"📊 <b>MULTI-TIMEFRAME</b>\n{mtf_block}\n\n"
                f"💰 Current price:\n<code>{data.get('price',0):,.2f}</code>\n\n"
                f"📊 BUY score: <b>{data.get('bullish_score',0)}/100</b>\n📉 SELL score: <b>{data.get('bearish_score',0)}/100</b>\n\n"
                f"🏗 Structure: <b>{data.get('structure','NEUTRAL')}</b>\n📈 MTF Bias: <b>{mtf_data.get('mtf_bias','NEUTRAL')}</b>\n\n"
                f"🧱 Support: <code>{data.get('support',0):,.2f}</code>\n🚧 Resistance: <code>{data.get('resistance',0):,.2f}</code>\n"
                f"📊 RSI 14: <code>{data.get('rsi',0):.1f}</code>\n\n"
                f"{news_block}\n"
                f"{late_block}\n"
                f"{exh_block}\n"
                f"🛑 <b>Why WAIT:</b>\n{reasons}\n\n"
                f"💡 {next_trigger}\n\n"
                f"{ai_line}"
                f"⚠️ <i>Multi-timeframe analysis. Use appropriate risk management.</i>")
    return (f"👑 <b>KING ZARRY AI • {data.get('symbol','')} SIGNAL</b>\n\n{emoji} <b>{action}</b>\n⏱ Execution: <b>{interval_display}</b>\n\n"
            f"📊 <b>MULTI-TIMEFRAME</b>\n{mtf_block}\n\n"
            f"{confidence_emoji} Confidence: <b>{data.get('confidence','LOW')} ({mtf_data.get('mtf_strength', data.get('strength',0))}/100)</b>\n"
            f"💪 Strength: <b>{data.get('strength',0)}/100</b>\n📊 BUY: <b>{data.get('bullish_score',0)}/100</b> SELL: <b>{data.get('bearish_score',0)}/100</b>\n\n"
            f"💰 <b>PRICE</b>\n<code>{data.get('price',0):,.2f}</code>\n\n"
            f"🎯 <b>ENTRY ZONE</b>\n<code>{data.get('entry_zone_low',0):,.2f} - {data.get('entry_zone_high',0):,.2f}</code>\n\n"
            f"🛑 Stop Loss:\n<code>{data.get('stop_loss',0):,.2f}</code>\n🎯 TP1:\n<code>{data.get('tp1',0):,.2f}</code>\n🎯 TP2:\n<code>{data.get('tp2',0):,.2f}</code>\n🎯 TP3:\n<code>{data.get('tp3',0):,.2f}</code>\n\n"
            f"⚖️ Risk/Reward: <b>1:{data.get('rr',3.5):.1f}</b>\n\n"
            f"🏗 Structure: <b>{data.get('structure','')}</b>\n📈 Trend: <b>{data.get('trend','')}</b>\n\n"
            f"🧱 Support: <code>{data.get('support',0):,.2f}</code>\n🚧 Resistance: <code>{data.get('resistance',0):,.2f}</code>\n\n"
            f"📊 RSI 14: <code>{data.get('rsi',0):.1f}</code>\n📏 EMA 9: <code>{data.get('ema9',0):,.2f}</code>\n📏 EMA 21: <code>{data.get('ema21',0):,.2f}</code>\n📏 EMA 50: <code>{data.get('ema50',0):,.2f}</code>\n📐 ATR: <code>{data.get('atr',0):,.2f}</code>\n\n"
            f"{news_block}\n"
            f"{late_block}\n"
            f"{exh_block}\n"
            f"🧠 <b>Why {action}:</b>\n{reasons}\n\n"
            f"{ai_line}"
            f"⚠️ <i>Multi-timeframe analysis. Not financial advice.</i>")

def format_signal(data):
    signal=data["signal"]
    if signal=="BUY":
        emoji="🟢"
        action="BUY"
    elif signal=="SELL":
        emoji="🔴"
        action="SELL"
    else:
        emoji="⚠️"
        action="WAIT / NO TRADE"
    confidence_emoji={"HIGH":"🔥","MEDIUM":"⚡","LOW":"⚠️"}.get(data["confidence"],"⚠️")
    reasons="\n".join(f"• {reason}" for reason in data["reasons"])
    ai_verdict=data.get("ai_verdict")
    ai_line=(f"🤖 <b>AI cross-check:</b>\n{html.escape(ai_verdict)}\n\n" if ai_verdict else "")
    interval_display=data["interval"].replace("min"," MIN").replace("h"," H").replace("day"," DAY").upper()
    if signal=="WAIT":
        return (f"👑 <b>KING ZARRY AI • {data['symbol']} ANALYSIS</b>\n\n{emoji} <b>STATUS: {action}</b>\n⏱ Timeframe: <b>{interval_display}</b>\n\n"
                f"💰 Current price:\n<code>{data['price']:,.2f}</code>\n\n📊 BUY score: <b>{data['bullish_score']}/100</b>\n📉 SELL score: <b>{data['bearish_score']}/100</b>\n\n"
                f"🏗 Structure: <b>{data['structure']}</b>\n📈 Trend: <b>{data['trend']}</b>\n\n🧱 Support: <code>{data['support']:,.2f}</code>\n🚧 Resistance: <code>{data['resistance']:,.2f}</code>\n"
                f"📊 RSI 14: <code>{data['rsi']:.1f}</code>\n\n🛑 <b>Why you should WAIT:</b>\n{reasons}\n\n💡 <i>Market is choppy or lacking clear directional momentum.</i>")
    return (f"👑 <b>KING ZARRY AI • {data['symbol']} SIGNAL</b>\n\n{emoji} <b>{action}</b>\n⏱ Timeframe: <b>{interval_display}</b>\n{confidence_emoji} Confidence: <b>{data['confidence']}</b>\n"
            f"💪 Strength: <b>{data['strength']}/100</b>\n📊 BUY score: <b>{data['bullish_score']}/100</b>\n📉 SELL score: <b>{data['bearish_score']}/100</b>\n\n"
            f"💰 Current price:\n<code>{data['price']:,.2f}</code>\n\n🎯 <b>ENTRY ZONE</b>\n<code>{data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}</code>\n\n"
            f"🛑 Stop Loss:\n<code>{data['stop_loss']:,.2f}</code>\n🎯 TP1:\n<code>{data['tp1']:,.2f}</code>\n🎯 TP2:\n<code>{data['tp2']:,.2f}</code>\n🎯 TP3:\n<code>{data['tp3']:,.2f}</code>\n\n"
            f"⚖️ Risk/Reward:\n<b>1:{data['rr']:.1f}</b>\n\n🏗 Structure:\n<b>{data['structure']}</b>\n📈 Trend:\n<b>{data['trend']}</b>\n\n🧱 Support:\n<code>{data['support']:,.2f}</code>\n"
            f"🚧 Resistance:\n<code>{data['resistance']:,.2f}</code>\n\n📊 RSI 14:\n<code>{data['rsi']:.1f}</code>\n📏 EMA 9:\n<code>{data['ema9']:,.2f}</code>\n📏 EMA 21:\n<code>{data['ema21']:,.2f}</code>\n"
            f"📏 EMA 50:\n<code>{data['ema50']:,.2f}</code>\n📐 ATR:\n<code>{data['atr']:,.2f}</code>\n\n🧠 <b>Why the engine chose {action}:</b>\n{reasons}\n\n{ai_line}⚠️ <i>Algorithmic market analysis. Use appropriate risk management.</i>")

def parse_candle_time(value):
    for fmt in ["%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%d"]:
        try:
            return datetime.strptime(value,fmt)
        except Exception:
            pass
    return datetime.now()

def build_signal_chart(data):
    if "15m" in data:
        chart_data = data["15m"]
        mtf_bias = data.get("mtf_bias", "")
    else:
        chart_data = data
        mtf_bias = ""
    candles=chart_data["candles"][-70:]
    opens=[float(c["open"]) for c in candles]
    highs=[float(c["high"]) for c in candles]
    lows=[float(c["low"]) for c in candles]
    closes=[float(c["close"]) for c in candles]
    times=[parse_candle_time(c.get("datetime","")) for c in candles]
    x=list(range(len(candles)))
    fig, ax=plt.subplots(figsize=(14,8),dpi=140)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")
    try:
        width=0.58
        for i in range(len(candles)):
            o=opens[i]; h=highs[i]; l=lows[i]; c=closes[i]
            candle_color=("#16A34A" if c>=o else "#DC2626")
            ax.vlines(i,l,h,linewidth=0.8,color="#555555")
            bottom=min(o,c)
            height=max(abs(c-o),0.000001)
            ax.add_patch(Rectangle((i-width/2,bottom),width,height,facecolor=candle_color,edgecolor=candle_color,linewidth=0.5))
        ema21_vals=[ema(closes[:i+1],21) if i>=20 else float("nan") for i in range(len(closes))]
        ema50_vals=[ema(closes[:i+1],50) if i>=49 else float("nan") for i in range(len(closes))]
        ax.plot(x,ema21_vals,linewidth=1.4,label="EMA 21")
        ax.plot(x,ema50_vals,linewidth=1.4,label="EMA 50")
        signal=chart_data.get("signal","WAIT")
        if "mtf_signal" in data:
            signal = data["mtf_signal"]
        current=chart_data["price"]
        support=chart_data["support"]
        resistance=chart_data["resistance"]
        late_info = detect_late_entry_status(chart_data)
        if signal in ["BUY","SELL"]:
            x0=max(0,len(x)-18)
            box_width=18
            entry_low=chart_data["entry_zone_low"]
            entry_high=chart_data["entry_zone_high"]
            sl=chart_data["stop_loss"]
            tp1=chart_data["tp1"]; tp2=chart_data["tp2"]; tp3=chart_data["tp3"]
            if signal=="BUY":
                ax.add_patch(Rectangle((x0,entry_low),box_width,entry_high-entry_low,alpha=0.25,color="green"))
                ax.add_patch(Rectangle((x0,sl),box_width,entry_low-sl,alpha=0.20,color="red"))
                ax.add_patch(Rectangle((x0,entry_high),box_width,tp3-entry_high,alpha=0.15,color="green"))
                arrow=FancyArrowPatch((x0+box_width/2,entry_high),(x0+box_width/2,tp3),arrowstyle="->",mutation_scale=18,linewidth=1.5,color="green")
            else:
                ax.add_patch(Rectangle((x0,entry_low),box_width,entry_high-entry_low,alpha=0.25,color="green"))
                ax.add_patch(Rectangle((x0,entry_high),box_width,sl-entry_high,alpha=0.20,color="red"))
                ax.add_patch(Rectangle((x0,tp3),box_width,entry_low-tp3,alpha=0.15,color="green"))
                arrow=FancyArrowPatch((x0+box_width/2,entry_low),(x0+box_width/2,tp3),arrowstyle="->",mutation_scale=18,linewidth=1.5,color="red")
            ax.add_patch(arrow)
            levels=[(entry_low,"ENTRY LOW"),(entry_high,"ENTRY HIGH"),(sl,"STOP LOSS"),(tp1,"TP1"),(tp2,"TP2"),(tp3,"TP3")]
            if late_info["status"] in ["LATE", "EXTENDED / AVOID"]:
                ax.text(0.5, 0.95, f"⚠️ {late_info['status']}", transform=ax.transAxes, fontsize=12, fontweight="bold", color="red", ha="center", bbox=dict(facecolor="yellow", alpha=0.5))
        else:
            levels=[(support,"SUPPORT"),(resistance,"RESISTANCE")]
        for level,label in levels:
            ax.axhline(level,linestyle=":",linewidth=0.7,alpha=0.6)
            ax.text(len(x)+0.8,level,f"{label} {level:,.2f}",fontsize=8,fontweight="bold")
        ax.axhline(current,linewidth=1,alpha=0.5)
        ax.text(len(x)-1,current,f" {current:,.2f}",fontsize=9,fontweight="bold")
        title=("🟢 BUY" if signal=="BUY" else "🔴 SELL" if signal=="SELL" else "⚠️ WAIT")
        interval_display="15M"
        mtf_title = f" MTF {mtf_bias}" if mtf_bias else ""
        ax.set_title(f"👑 KING ZARRY AI • {chart_data['symbol']} • {interval_display}{mtf_title} • {title}",fontsize=13,fontweight="bold",loc="left",pad=12)
        if times:
            step=max(1,len(times)//7)
            ticks=list(range(0,len(times),step))
            ax.set_xticks(ticks)
            ax.set_xticklabels([times[i].strftime("%d %b\n%H:%M") for i in ticks],fontsize=8)
        sl=chart_data.get("stop_loss",support)
        tp3=chart_data.get("tp3",resistance)
        y_low=min(min(lows),sl)
        y_high=max(max(highs),tp3)
        padding=max((y_high-y_low)*0.08,chart_data["atr"]*0.8) if chart_data.get("atr") else (y_high-y_low)*0.08
        ax.set_ylim(y_low-padding,y_high+padding)
        ax.set_xlim(-1,len(x)+9)
        ax.grid(True,alpha=0.15,linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(loc="upper left",frameon=False,fontsize=8)
        plt.tight_layout()
        buffer=BytesIO()
        buffer.name="king_zarry_signal.png"
        fig.savefig(buffer,format="png",dpi=140,bbox_inches="tight",facecolor="white")
        buffer.seek(0)
        return buffer
    finally:
        plt.close(fig)

def detect_market_and_timeframe(text):
    """Resolve any crypto (Binance) / gold / forex (Twelve) from user text."""
    try:
        from market import resolve_trading_symbol
        symbol = resolve_trading_symbol(text or "BTC")
    except Exception:
        symbol = "BTC/USD"
        upper = (text or "").upper()
        for name, canon in (("GOLD","XAU/USD"),("XAU","XAU/USD"),("BTC","BTC/USD"),("ETH","ETH/USD"),("SOL","SOL/USD")):
            if name in upper:
                symbol = canon
                break
    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", (text or "").lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe

# =========================================================
# FIX: SLASH-ONLY MARKET INTENT
# Only /btc /eth /sol /xau /gold /signal /plan ... can trigger the MTF
# signal pipeline. Plain text ("btc", "gold signal", "analyze eth")
# ALWAYS goes to normal AI chat.
# =========================================================
_SIGNAL_SLASH_RE = re.compile(
    r"^\s*/(?P<cmd>btc|eth|sol|xau|xag|gold|silver|bitcoin|ethereum|solana|bnb|xrp|signal|plan)"
    r"(?:@\w+)?(?:\s+(?P<rest>.+))?\s*$",
    re.IGNORECASE,
)

def detect_market_intent(text: str):
    """Return (True, symbol, timeframe) ONLY for slash trading commands."""
    if not text:
        return False, "XAU/USD", "15m"
    stripped = text.strip()
    m = _SIGNAL_SLASH_RE.match(stripped)
    if not m:
        return False, "XAU/USD", "15m"
    cmd = (m.group("cmd") or "").lower()
    rest = (m.group("rest") or "").strip()
    if cmd in ("signal", "plan"):
        query = rest or "XAUUSD"
    else:
        query = f"{cmd} {rest}".strip()
    symbol, timeframe = detect_market_and_timeframe(query)
    return True, symbol, timeframe

# FIX: only treat a message as a price-alert request when the user actually
# talks about alerts. Before this, ANY message with a symbol + a number
# ("btc is at 100k", "gold 4300") was turned into a price alert.
_ALERT_INTENT_RE = re.compile(
    r"\b(alert|alerts|notify|notification|let me know|tell me when|ping me|warn me)\b",
    re.IGNORECASE,
)

def detect_notification_intent(text: str):
    if not text:
        return False, "", ""
    lower = text.lower()
    price_patterns = [
        r"alert me when",
        r"notify me when",
        r"alert.*breaks",
        r"alert.*hits",
        r"notify.*breaks",
        r"price alert",
        r"set.*alert",
    ]
    reminder_patterns = [
        r"remind me",
        r"reminder",
        r"remind.*tomorrow",
        r"remind.*at \d",
    ]
    briefing_patterns = [
        r"briefing every",
        r"send me.*every",
        r"daily.*brief",
        r"morning.*brief",
        r"every morning",
        r"every hour",
        r"every day",
    ]
    is_price_alert = any(re.search(p, lower) for p in price_patterns)
    is_reminder = any(re.search(p, lower) for p in reminder_patterns)
    is_briefing = any(re.search(p, lower) for p in briefing_patterns)
    if is_price_alert:
        upper = text.upper()
        symbol = "BTC/USD"
        if any(k in upper for k in ["BTC", "BTCUSD", "BTC/USD"]):
            symbol = "BTC/USD"
        elif any(k in upper for k in ["ETH", "ETHUSD"]):
            symbol = "ETH/USD"
        elif any(k in upper for k in ["SOL"]):
            symbol = "SOL/USD"
        elif any(k in upper for k in ["XAU", "GOLD", "XAUUSD"]):
            symbol = "XAU/USD"
        return True, "price_alert", symbol
    if is_reminder:
        return True, "reminder", text
    if is_briefing:
        return True, "briefing", text
    return False, "", ""

TIMEFRAME_MAP={"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h","2h":"2h","4h":"4h","1d":"1day"}
def normalize_timeframe(timeframe):
    return TIMEFRAME_MAP.get(timeframe.lower().strip(),DEFAULT_TIMEFRAME)

async def start_command(update, context):
    user=update.effective_user
    if user:
        save_user(user)
        if user.username:
            update_subscription_username(user.id,user.username)
    active=(user and user_has_access(user.id))
    status=("🟢 <b>VIP ACTIVE</b>" if active else "🔴 <b>VIP NOT ACTIVE</b>")
    text=("👑 <b>KING ZARRY AI</b>\n\nYour AI trading and intelligence assistant is online. 🚀\n\n"
          f"{status}\n\n🤖 <b>AI</b>\nJust chat with me normally, or /ask &lt;question&gt;\n/tts &lt;text&gt;\n\n"
          "🎨 <b>IMAGE & VIDEO GENERATION</b>\nJust type:\n"
          "• <i>Draw a cyberpunk trader</i>\n"
          "• <i>Create an image of gold bars</i>\n"
          "• <i>Make a video of a sunrise</i>\n"
          "• Send a photo + caption <i>make it look vintage</i>\n\n"
          "📊 <b>15M SIGNALS - MTF 4H→1H→15M→5M</b>\n"
          "Signals only come when you use a command:\n"
          "/signal XAU\n/signal BTC\n/signal ETH\n/signal SOL\n\n📋 <b>One-Day Plan</b>\n/plan BTC\n/plan XAU\n\n📰 <b>News</b>\n/news BTC\n/events\n\n⚡ Quick:\n/xau\n/btc\n/eth\n/sol\n\n"
          "🧠 <b>Market Intelligence</b>\n/intel — live market regime, news, macro and crypto context\n\n"
          "🔔 <b>Price alerts</b>\n/alert XAU above 4329\n/alerts\n\n"
          "💎 <b>VIP</b>\n/buy\n/status\n/history\n/paysupport\n\n📸 Send a chart for AI Vision")
    await send_long_message(update.message,text,is_raw_html=True)

async def help_command(update, context):
    await start_command(update,context)

async def buy_command(update, context):
    text=(f"👑 <b>KING ZARRY AI VIP</b>\n\nChoose your plan:\n\n🌟 <b>Monthly</b>\n30 days • {MONTHLY_STARS} Stars\n/monthly\n\n"
          f"🔥 <b>3 Months</b>\n90 days • {THREE_MONTH_STARS} Stars\n/3month\n\n💎 <b>Yearly</b>\n365 days • {YEARLY_STARS} Stars\n/yearly")
    await update.message.reply_text(text,parse_mode="HTML")

async def send_subscription_invoice(update, plan_key):
    if plan_key not in SUBSCRIPTION_PLANS:
        await update.message.reply_text("❌ Invalid plan.")
        return
    plan=SUBSCRIPTION_PLANS[plan_key]
    await update.message.reply_invoice(title=plan["name"],description=plan["description"],payload=f"kingzarry_subscription:{plan_key}",currency="XTR",prices=[LabeledPrice(plan["name"],plan["stars"])],provider_token="")

async def monthly_command(update, context):
    await send_subscription_invoice(update,"monthly")
async def three_month_command(update, context):
    await send_subscription_invoice(update,"3month")
async def yearly_command(update, context):
    await send_subscription_invoice(update,"yearly")

async def precheckout_handler(update, context):
    query=update.pre_checkout_query
    payload=query.invoice_payload
    if not payload.startswith("kingzarry_subscription:"):
        await query.answer(ok=False,error_message="Invalid subscription.")
        return
    plan_key=payload.split(":",1)[1]
    if plan_key not in SUBSCRIPTION_PLANS:
        await query.answer(ok=False,error_message="Plan unavailable.")
        return
    plan=SUBSCRIPTION_PLANS[plan_key]
    if query.currency!="XTR" or query.total_amount!=plan["stars"]:
        await query.answer(ok=False,error_message="Payment validation failed.")
        return
    await query.answer(ok=True)

async def successful_payment_handler(update, context):
    message=update.message
    user=update.effective_user
    payment=(message.successful_payment if message else None)
    if not payment or not user:
        return
    save_user(user)
    payload=payment.invoice_payload
    if not payload.startswith("kingzarry_subscription:"):
        return
    plan_key=payload.split(":",1)[1]
    if plan_key not in SUBSCRIPTION_PLANS:
        await message.reply_text("⚠️ Payment received, but plan identification failed.")
        return
    plan=SUBSCRIPTION_PLANS[plan_key]
    username=(f"@{user.username}" if user.username else (user.full_name or str(user.id)))
    payment_id=payment.telegram_payment_charge_id
    if not record_payment(user.id,username,plan_key,"telegram_stars",payment_id,payment.total_amount,payment.currency,payload):
        existing=get_subscription(user.id)
        if existing:
            await message.reply_text("ℹ️ <b>This payment was already processed.</b>\n\nYour VIP subscription is active.",parse_mode="HTML")
        else:
            await message.reply_text("⚠️ Payment was already recorded, but no subscription record was found. Please contact admin with your charge ID.")
        return
    expires_at=activate_subscription(user.id,username,plan["days"],plan_key,"telegram_stars",payment_id)
    await message.reply_text(f"🎉 <b>PAYMENT SUCCESSFUL!</b>\n\n👑 Welcome to <b>KING ZARRY AI VIP</b>!\n\n"
                             f"👤 Account: <b>{html.escape(username)}</b>\n📦 Plan: <b>{html.escape(plan['name'])}</b>\n"
                             f"⭐ Paid: <b>{payment.total_amount} Stars</b>\n\n📅 Expires:\n<code>{expires_at.strftime('%Y-%m-%d %H:%M UTC')}</code>\n\n🟢 <b>VIP ACTIVATED</b>",parse_mode="HTML")

async def status_command(update, context):
    user=update.effective_user
    if not user:
        return
    save_user(user)
    if user.id in ADMIN_IDS:
        await update.message.reply_text("👑 <b>KING ZARRY ADMIN</b>\n\n🟢 Unlimited access.\n\n👥 /users\n💎 /subscribers\n📊 /stats\n📢 /broadcast &lt;message&gt;\n🔔 /notify\n📋 /notifications\n❌ /cancelnotify",parse_mode="HTML")
        return
    subscription=get_subscription(user.id)
    if not subscription or not is_subscribed(user.id):
        await update.message.reply_text("🔴 <b>NO ACTIVE VIP</b>\n\nUse /buy to subscribe.",parse_mode="HTML")
        return
    await update.message.reply_text(f"🟢 <b>VIP ACTIVE</b>\n\n👑 Plan: <b>{html.escape(subscription['plan'])}</b>\n📅 Expires:\n<code>{html.escape(subscription['expires_at'])}</code>",parse_mode="HTML")

async def history_command(update, context):
    user=update.effective_user
    if not user:
        return
    save_user(user)
    history=get_payment_history(user.id,10)
    if not history:
        await update.message.reply_text("💳 No payment history.")
        return
    lines=["💳 <b>KING ZARRY PAYMENT HISTORY</b>\n"]
    for row in history:
        lines.append(f"• <b>{html.escape(str(row['plan']))}</b>\n {html.escape(str(row['payment_method']))}\n {row['amount']} {html.escape(str(row['currency']))}\n {html.escape(str(row['created_at']))}\n")
    await update.message.reply_text("\n".join(lines),parse_mode="HTML")

async def paysupport_command(update, context):
    await update.message.reply_text(
        "💬 <b>KING ZARRY PAY SUPPORT</b>\n\n"
        "Having issues with Stars payment?\n\n"
        "1. Ensure you have enough Telegram Stars\n"
        "2. Try /buy again\n"
        "3. Check /status\n"
        "4. Contact admin with your payment Charge ID\n\n"
        "Commands:\n/buy - View plans\n/status - Check VIP\n/history - Payment history",
        parse_mode="HTML")

async def users_command(update, context):
    user=update.effective_user
    if not user:
        return
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    rows=get_all_subscribers()
    if not rows:
        await update.message.reply_text("👑 <b>KING ZARRY AI USERS</b>\n\n📭 No subscribers found yet.",parse_mode="HTML")
        return
    now=datetime.now(timezone.utc)
    active=[]; expired=[]
    for row in rows:
        try:
            expiry=datetime.fromisoformat(row["expires_at"])
            if expiry.tzinfo is None:
                expiry=expiry.replace(tzinfo=timezone.utc)
            if expiry>now:
                active.append(row)
            else:
                expired.append(row)
        except Exception:
            expired.append(row)
    lines=["👑 <b>KING ZARRY AI USERS</b>","",f"👥 Total: <b>{len(rows)}</b>",f"🟢 Active: <b>{len(active)}</b>",f"🔴 Expired: <b>{len(expired)}</b>","","━━━━━━━━━━━━━━━━━━"]
    for index,row in enumerate(rows,1):
        user_id=row["user_id"]
        username=(row["username"] or "")
        first_name=(row["first_name"] or "")
        last_name=(row["last_name"] or "")
        if username:
            display_name=f"@{username.lstrip('@')}"
        elif first_name or last_name:
            display_name=f"{first_name} {last_name}".strip()
        else:
            display_name="No username"
        try:
            expiry=datetime.fromisoformat(row["expires_at"])
            if expiry.tzinfo is None:
                expiry=expiry.replace(tzinfo=timezone.utc)
            is_active=(expiry>now)
        except Exception:
            is_active=False
        status=("🟢 ACTIVE" if is_active else "🔴 EXPIRED")
        lines.append(f"\n<b>{index}. {html.escape(display_name)}</b>\n🆔 <code>{user_id}</code>\n👑 Plan: <b>{html.escape(str(row['plan'] or 'Unknown'))}</b>\n{status}\n"
                     f"📅 Expires:\n<code>{html.escape(str(row['expires_at'] or 'Unknown'))}</code>\n💳 Payment: <b>{html.escape(str(row['payment_method'] or 'Unknown'))}</b>\n"
                     f"🧾 Charge ID:\n<code>{html.escape(str(row['payment_id'] or 'Unknown'))}</code>\n━━━━━━━━━━━━━━━━━━")
    await send_long_message(update.message,"\n".join(lines),is_raw_html=True)

async def subscribers_command(update, context):
    await users_command(update,context)

async def broadcast_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    message=update.message
    is_reply=bool(message.reply_to_message)
    target_msg=message.reply_to_message if is_reply else message
    text_to_send=""
    if not is_reply:
        raw_text=message.text or ""
        text_to_send=re.sub(r"^/broadcast(@\w+)?\s*","",raw_text,count=1,flags=re.IGNORECASE).strip("\n")
        has_media=bool(message.photo or message.video or message.document or message.voice or message.audio)
        if not text_to_send and not has_media:
            await update.message.reply_text("📢 <b>BROADCAST USAGE</b>\n\n1. <code>/broadcast Important update!</code>\n2. Attach media with caption <code>/broadcast Your message</code>\n3. Reply to any message with <code>/broadcast</code>",parse_mode="HTML")
            return
    all_user_ids=get_all_users()
    if not all_user_ids:
        await update.message.reply_text("📭 No users found in database.")
        return
    status_msg=await update.message.reply_text(f"🚀 Starting broadcast to <b>{len(all_user_ids)}</b> users...",parse_mode="HTML")
    success=0; failed=0; blocked=0
    async def send_to_user(uid):
        if is_reply:
            await context.bot.copy_message(chat_id=uid,from_chat_id=target_msg.chat_id,message_id=target_msg.message_id)
        elif message.photo or message.video or message.document or message.voice or message.audio:
            caption=message.caption or ""
            caption=re.sub(r"^/broadcast(@\w+)?\s*","",caption,count=1,flags=re.IGNORECASE).strip("\n")
            await context.bot.copy_message(chat_id=uid,from_chat_id=message.chat_id,message_id=message.message_id,caption=escape_html(caption) if caption else None,parse_mode="HTML" if caption else None)
        else:
            if len(text_to_send) > 3800:
                chunks = [text_to_send[i:i+3800] for i in range(0, len(text_to_send), 3800)]
                for chunk in chunks:
                    await context.bot.send_message(chat_id=uid,text=escape_html(chunk),parse_mode="HTML",disable_web_page_preview=True)
            else:
                await context.bot.send_message(chat_id=uid,text=escape_html(text_to_send),parse_mode="HTML",disable_web_page_preview=True)
    for uid in all_user_ids:
        try:
            await send_to_user(uid)
            success+=1
            await asyncio.sleep(0.05)
        except Forbidden:
            blocked+=1; failed+=1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await send_to_user(uid); success+=1
            except Exception:
                failed+=1
        except BadRequest:
            failed+=1
        except Exception:
            failed+=1
    await status_msg.edit_text(f"📢 <b>BROADCAST COMPLETED</b>\n\n🎯 Total: <b>{len(all_user_ids)}</b>\n✅ Sent: <b>{success}</b>\n🚫 Failed: <b>{failed}</b> (Blocked: {blocked})",parse_mode="HTML")

async def stats_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        if update.message:
            await update.message.reply_text("⛔ Admin only.")
        return
    rows=get_all_subscribers()
    now=datetime.now(timezone.utc)
    active_count=0; expired_count=0
    for row in rows:
        try:
            expiry=datetime.fromisoformat(row["expires_at"])
            if expiry.tzinfo is None:
                expiry=expiry.replace(tzinfo=timezone.utc)
            if expiry>now:
                active_count+=1
            else:
                expired_count+=1
        except Exception:
            expired_count+=1
    total_users=get_user_count()
    payment_stats=get_payment_stats()
    await update.message.reply_text(f"👑 <b>KING ZARRY AI STATS</b>\n\n👥 Total users: <b>{total_users}</b>\n💎 Subscribers: <b>{len(rows)}</b>\n"
                                    f"🟢 Active VIP: <b>{active_count}</b>\n🔴 Expired: <b>{expired_count}</b>\n\n💳 Payments: <b>{payment_stats['payments']}</b>\n"
                                    f"⭐ Stars: <b>{payment_stats['stars']}</b>",parse_mode="HTML")

async def grant_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if len(context.args)<2:
        await update.message.reply_text("Usage:\n/grant USER_ID DAYS"); return
    try:
        target_id=int(context.args[0]); days=int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ USER_ID and DAYS must be numbers."); return
    if days<=0:
        await update.message.reply_text("❌ DAYS must be greater than 0."); return
    expiry=activate_subscription(target_id,"admin_granted",days,"admin","admin",None)
    await update.message.reply_text(f"✅ <b>VIP GRANTED</b>\n\n👤 User: <code>{target_id}</code>\n📅 Days: <b>{days}</b>\n⏰ Expires:\n<code>{expiry}</code>",parse_mode="HTML")

async def revoke_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if not context.args:
        await update.message.reply_text("Usage:\n/revoke USER_ID"); return
    try:
        target_id=int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid USER_ID."); return
    deactivate_subscription(target_id)
    await update.message.reply_text(f"🚫 <b>VIP REVOKED</b>\n\nUser: <code>{target_id}</code>",parse_mode="HTML")

async def notify_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if len(context.args)<2:
        await update.message.reply_text("Usage:\n/notify <seconds> <message>\nExample:\n/notify 3600 Market update every hour",parse_mode="HTML"); return
    try:
        interval=int(context.args[0])
        if interval<60:
            await update.message.reply_text("❌ Minimum interval is 60 seconds."); return
        msg=" ".join(context.args[1:])
        if not msg:
            await update.message.reply_text("❌ Message cannot be empty."); return
        conn=db_connect()
        try:
            conn.execute("INSERT INTO notifications (admin_id, message, interval_seconds, next_run, active, created_at) VALUES (?,?,?,?,?,?)",
                         (user.id, msg, interval, (datetime.now(timezone.utc)+timedelta(seconds=interval)).isoformat(), 1, datetime.now(timezone.utc).isoformat()))
            conn.commit()
        finally:
            conn.close()
        await update.message.reply_text(f"✅ <b>Notification scheduled</b>\n\n⏱ Every: <b>{interval}s</b>\n📝 Message: {html.escape(msg)}",parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ Interval must be a number (seconds).")

async def notifications_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    conn=db_connect()
    try:
        rows=conn.execute("SELECT * FROM notifications WHERE active=1 ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    if not rows:
        await update.message.reply_text("📭 No active notifications.")
        return
    lines=["🔔 <b>ACTIVE NOTIFICATIONS</b>\n"]
    for r in rows:
        lines.append(f"🆔 {r['id']} - Every {r['interval_seconds']}s\n📝 {html.escape(r['message'][:100])}\nNext: {html.escape(str(r['next_run']))}\n")
    await update.message.reply_text("\n".join(lines),parse_mode="HTML")

async def cancelnotify_command(update, context):
    user=update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if not context.args:
        await update.message.reply_text("Usage:\n/cancelnotify <id>\nUse /notifications to see IDs"); return
    try:
        nid=int(context.args[0])
        conn=db_connect()
        try:
            conn.execute("UPDATE notifications SET active=0 WHERE id=?", (nid,))
            conn.commit()
        finally:
            conn.close()
        await update.message.reply_text(f"✅ Notification {nid} cancelled.")
    except ValueError:
        await update.message.reply_text("❌ Invalid ID.")


# ============================================================
# AGENT SIGNAL WATCH — always-on scanner → Telegram push
# FIX: now OFF by default. Before, it DM'd the admin a signal every scan
# cycle without being asked, which looked like "signals in normal chat".
# Turn it on in Railway with:
#   AGENT_SIGNAL_WATCH=true
#   AGENT_SIGNAL_INTERVAL_SEC=300   (default 300 = 5 min)
#   AGENT_SIGNAL_AUDIENCE=admin|subscribers|all  (default admin)
# ============================================================
AGENT_SIGNAL_WATCH = clean_env_str(os.getenv("AGENT_SIGNAL_WATCH", "false")).lower() in ("1", "true", "yes", "on")
try:
    AGENT_SIGNAL_INTERVAL_SEC = max(60, int(clean_env_str(os.getenv("AGENT_SIGNAL_INTERVAL_SEC", "300")) or "300"))
except ValueError:
    AGENT_SIGNAL_INTERVAL_SEC = 300
AGENT_SIGNAL_AUDIENCE = clean_env_str(os.getenv("AGENT_SIGNAL_AUDIENCE", "admin")).lower() or "admin"
try:
    from market import get_agent_watch_symbols
    AGENT_WATCH_SYMBOLS = get_agent_watch_symbols()
except Exception:
    AGENT_WATCH_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "XAU/USD"]



def _agent_signal_is_actionable(analysis: dict) -> bool:
    """BUY/SELL only if NOT a late entry — never push chase signals."""
    sig = str(analysis.get("signal") or "").upper().strip()
    if sig not in ("BUY", "SELL"):
        return False
    if analysis.get("late_entry") is True:
        return False
    eq = str(analysis.get("entry_quality") or "").upper()
    if eq in ("LATE", "RISKY"):
        return False
    # Confidence: only skip clearly weak numeric scores
    conf = analysis.get("confidence")
    if conf is None or conf == "":
        return True
    try:
        if isinstance(conf, (int, float)):
            return float(conf) >= 50
        c = str(conf).upper().strip()
        if c in ("LOW", "WEAK", "POOR"):
            return False
        # try parse number in string
        num = float("".join(ch for ch in c if ch.isdigit() or ch == ".") or "100")
        return num >= 50
    except Exception:
        return True


def _agent_signal_is_late(analysis: dict) -> bool:
    if analysis.get("late_entry") is True:
        return True
    eq = str(analysis.get("entry_quality") or "").upper()
    return eq in ("LATE", "RISKY")


def _agent_v2_verify_and_track(symbol: str, analysis: dict):
    """Run Agent V2 verification and persist an accepted signal."""
    try:
        from agent_v2 import verify_setup, register_signal
        verification = verify_setup(analysis)
        analysis["agent_v2"] = verification
        if verification.get("decision") != "SIGNAL":
            return verification, None
        signal_id = register_signal(symbol, analysis, verification)
        return verification, signal_id
    except Exception as e:
        logger.warning("agent_v2 verification unavailable for %s: %s", symbol, e)
        return {"decision": "SIGNAL", "score": None, "reasons": ["v2 unavailable"]}, None


def _agent_v2_update_lifecycle(symbol: str, analysis: dict):
    """Update existing V2 signals from the latest observed market price."""
    try:
        from agent_v2 import update_signal_lifecycle
        price = analysis.get("price") or analysis.get("current_price")
        return update_signal_lifecycle(symbol, price, analysis)
    except Exception as e:
        logger.debug("agent_v2 lifecycle update %s failed: %s", symbol, e)
        return []


def _agent_signal_fingerprint(symbol: str, analysis: dict) -> str:
    sig = str(analysis.get("signal") or "").upper()
    entry = str(analysis.get("entry") or analysis.get("price") or "")
    return f"{symbol}|{sig}|{entry}"


async def agent_morning_brief_job(context: ContextTypes.DEFAULT_TYPE):
    """Generate the daily Agent brief once and DM it to active Telegram VIP users."""
    try:
        from agent_core import build_morning_brief

        targets = set()
        for uid in get_all_users():
            try:
                if is_subscribed(uid) or uid in ADMIN_IDS:
                    try:
                        from agent_v2 import get_agent_preferences, preferences_allow_now
                        prefs = get_agent_preferences(str(uid))
                        if any(
                            preferences_allow_now(prefs, symbol=str(a.get("symbol") or ""), lifecycle=False)
                            for a in actionable
                        ):
                            targets.add(uid)
                    except Exception:
                        targets.add(uid)
            except Exception:
                continue

        if not targets:
            logger.info("agent_morning_brief: no active VIP Telegram users")
            return

        brief = await asyncio.to_thread(build_morning_brief)
        summary = str(brief.get("summary_text") or "").strip()
        if not summary:
            logger.warning("agent_morning_brief: generated brief was empty")
            return

        message = (
            "🌅 <b>KING ZARRY AI — MORNING BRIEF</b>\\n\\n"
            + html.escape(summary)
        )
        sent = 0
        failed = 0

        for uid in targets:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=message[:4096],
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                sent += 1
                await asyncio.sleep(0.08)
            except Forbidden:
                failed += 1
            except RetryAfter as e:
                failed += 1
                logger.warning("agent_morning_brief rate limit for %s: %s", uid, e)
            except Exception as e:
                failed += 1
                logger.debug("agent_morning_brief send %s failed: %s", uid, e)

        logger.info(
            "agent_morning_brief: generated once, sent=%s failed=%s vip_targets=%s",
            sent,
            failed,
            len(targets),
        )
    except Exception as e:
        logger.exception("agent_morning_brief failed: %s", e)


async def agent_signal_watch_job(context: ContextTypes.DEFAULT_TYPE):
    """Scan MTF signals; push new BUY/SELL packages to Telegram immediately."""
    if not AGENT_SIGNAL_WATCH:
        return
    try:
        from agent_core import tool_analyze_symbol, tool_learn, create_job, _update_job
    except Exception as e:
        logger.warning(f"agent_signal_watch: agent_core unavailable: {e}")
        return

    bot_data = context.application.bot_data
    last_map = bot_data.setdefault("agent_last_signals", {})

    actionable = []
    n_wait = 0
    n_late = 0
    n_dup = 0
    n_err = 0
    n_lowconf = 0
    scan_summary = []

    for symbol in AGENT_WATCH_SYMBOLS:
        try:
            analysis = await asyncio.to_thread(tool_analyze_symbol, symbol, "15m")
        except Exception as e:
            n_err += 1
            logger.warning(f"agent_signal_watch analyze {symbol}: {e}")
            scan_summary.append(f"{symbol}=ERR")
            continue

        sig = str(analysis.get("signal") or "WAIT").upper()
        price = analysis.get("price")
        late = _agent_signal_is_late(analysis)

        # Lifecycle state changes stay internal. Telegram receives only the
        # complete /signal-style package below, never a raw lifecycle event.
        scan_summary.append(
            f"{symbol}={sig}"
            + (f"@{price}" if price is not None else "")
            + ("/LATE" if late else "")
            + (f"/q={analysis.get('entry_quality')}" if analysis.get("entry_quality") else "")
        )

        # Late BUY/SELL → do NOT push trade signal
        if late and sig in ("BUY", "SELL"):
            n_late += 1
            fp_late = _agent_signal_fingerprint(symbol, analysis) + "|LATE"
            late_notified = bot_data.setdefault("agent_late_notified", {})
            if late_notified.get(symbol) != fp_late:
                late_notified[symbol] = fp_late
                bot_data.setdefault("agent_late_queue", []).append(analysis)
            try:
                tool_learn(
                    user_id="telegram_agent",
                    symbol=symbol,
                    signal=sig,
                    confidence=str(analysis.get("confidence") or ""),
                    notes=f"SKIPPED_LATE: {analysis.get('late_entry_reason') or analysis.get('entry_quality')}",
                    outcome="skipped_late_entry",
                )
            except Exception:
                pass
            continue

        if sig not in ("BUY", "SELL"):
            n_wait += 1
            continue

        if not _agent_signal_is_actionable(analysis):
            n_lowconf += 1
            continue

        verification, signal_id = _agent_v2_verify_and_track(symbol, analysis)
        if verification.get("decision") != "SIGNAL":
            n_lowconf += 1
            scan_summary.append(f"{symbol}=V2_WAIT(score={verification.get('score')})")
            try:
                from agent_core import tool_learn
                tool_learn(
                    user_id="telegram_agent",
                    symbol=symbol,
                    signal=sig,
                    confidence=str(analysis.get("confidence") or ""),
                    notes="agent_v2_verification_wait: " + "; ".join(verification.get("reasons") or [])[:500],
                    outcome="v2_verification_wait",
                    meta={"score": verification.get("score"), "threshold": verification.get("threshold")},
                )
            except Exception:
                pass
            continue

        try:
            from risk_guardian import evaluate_risk_guardian
            guardian = evaluate_risk_guardian(symbol, analysis, verification)
            analysis["risk_guardian"] = guardian
            if guardian.get("status") != "APPROVE":
                n_lowconf += 1
                scan_summary.append(
                    f"{symbol}=RISK_{guardian.get('status')}"
                )
                try:
                    from agent_core import tool_learn
                    tool_learn(
                        user_id="telegram_agent",
                        symbol=symbol,
                        signal=sig,
                        confidence=str(analysis.get("confidence") or ""),
                        notes="risk_guardian: " + "; ".join(guardian.get("reasons") or [])[:500],
                        outcome="risk_guardian_" + str(guardian.get("status") or "hold").lower(),
                        meta={"checks": guardian.get("checks") or [], "score": verification.get("score")},
                    )
                except Exception:
                    pass
                continue
        except Exception as guardian_error:
            logger.warning("risk_guardian unavailable for %s: %s", symbol, guardian_error)
            n_lowconf += 1
            scan_summary.append(f"{symbol}=RISK_ERROR")
            continue

        if signal_id:
            analysis["signal_id"] = signal_id

        fp = _agent_signal_fingerprint(symbol, analysis)
        if last_map.get(symbol) == fp:
            n_dup += 1
            continue
        last_map[symbol] = fp
        actionable.append(analysis)
        try:
            tool_learn(
                user_id="telegram_agent",
                symbol=symbol,
                signal=sig,
                confidence=str(analysis.get("confidence") or ""),
                notes="auto_watch_push",
                outcome="pushed_telegram",
            )
        except Exception:
            pass

    logger.info(
        "agent_signal_watch cycle: "
        + " | ".join(scan_summary)
        + f" || actionable={len(actionable)} wait={n_wait} late={n_late} dup={n_dup} lowconf={n_lowconf} err={n_err}"
    )

    # Notify admin once about late setups (warning only — not a trade signal)
    late_queue = bot_data.pop("agent_late_queue", [])
    if late_queue and ADMIN_IDS:
        late_lines = [
            "⚠️ <b>KING ZARRY AGENT — LATE ENTRY</b>",
            "",
            "Setup exists but it is <b>too late to open</b>. Signal NOT sent.",
            "",
        ]
        for a in late_queue:
            late_lines.append(
                "• <b>" + html.escape(str(a.get("symbol"))) + "</b> "
                + html.escape(str(a.get("signal") or "").upper())
                + " — quality <b>"
                + html.escape(str(a.get("entry_quality") or "LATE"))
                + "</b>" + chr(10) + "  "
                + html.escape(
                    str(
                        a.get("late_entry_reason")
                        or a.get("reason")
                        or "Extended move"
                    )[:200]
                )
            )
            late_lines.append("")
        late_lines.append("<i>Wait for pullback / better location. Not financial advice.</i>")
        late_text = chr(10).join(late_lines)
        for uid in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=late_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

    try:
        from agent_v2 import record_agent_heartbeat
        record_agent_heartbeat(
            status="degraded" if n_err else "online",
            scan_count=len(AGENT_WATCH_SYMBOLS),
            actionable_count=len(actionable),
            wait_count=n_wait + n_lowconf,
            error_count=n_err,
        )
    except Exception as heartbeat_error:
        logger.debug("Agent V2 heartbeat update failed: %s", heartbeat_error)

    if not actionable:
        return

    lines = [
        "🤖 <b>KING ZARRY AI • SIGNAL AGENT — LIVE SIGNAL</b>",
        "",
        "Auto-scan found actionable setup(s):",
        "",
    ]
    for a in actionable:
        lines.append(
            f"• <b>{html.escape(str(a.get('symbol')))}</b> — "
            f"<b>{html.escape(str(a.get('signal') or '').upper())}</b>\n"
            f"  Price: {html.escape(str(a.get('price') or '—'))}\n"
            f"  Entry: {html.escape(str(a.get('entry') or '—'))} | "
            f"SL: {html.escape(str(a.get('stop_loss') or '—'))}\n"
            f"  TP1: {html.escape(str(a.get('tp1') or '—'))} | "
            f"TP2: {html.escape(str(a.get('tp2') or '—'))}\n"
            f"  Conf: {html.escape(str(a.get('confidence') or '—'))} | "
            f"Trend: {html.escape(str(a.get('trend') or '—'))}"
            + (f"\\n  Agent ID: <code>{html.escape(str(a.get('signal_id')))}</code>" if a.get("signal_id") else "")
            + (f"\\n  V2 score: <b>{html.escape(str((a.get('agent_v2') or {}).get('score')))}</b>" if (a.get('agent_v2') or {}).get('score') is not None else "")
        )
        reasons = a.get("reasons") or []
        if isinstance(a.get("agent_v2"), dict):
            v2_reasons = a["agent_v2"].get("reasons") or []
            if v2_reasons:
                lines.append(f"  V2 check: {html.escape(str(v2_reasons[0])[:120])}")
        if isinstance(reasons, list) and reasons:
            lines.append(f"  Note: {html.escape(str(reasons[0])[:120])}")
        lines.append("")
    lines.append("<i>Not financial advice. Trading involves risk.</i>")
    text = "\n".join(lines)

    # Audience
    targets = set()
    if AGENT_SIGNAL_AUDIENCE in ("admin", "admins"):
        targets |= set(ADMIN_IDS)
    elif AGENT_SIGNAL_AUDIENCE in ("subscribers", "vip", "subs"):
        try:
            for uid in get_all_users():
                if is_subscribed(uid) or uid in ADMIN_IDS:
                    targets.add(uid)
        except Exception:
            targets |= set(ADMIN_IDS)
    else:  # all
        try:
            targets |= set(get_all_users())
        except Exception:
            targets |= set(ADMIN_IDS)
        targets |= set(ADMIN_IDS)

    if not targets:
        targets |= set(ADMIN_IDS)

    # Automatic Agent delivery uses the same complete presentation as /signal.
    # Rebuild MTF/news here so Entry, SL, TP1/TP2/TP3 and the chart are generated
    # from the same analysis path used by /signal.
    sent = 0
    for uid in targets:
        try:
            try:
                from agent_v2 import get_agent_preferences, preferences_allow_now
                prefs = get_agent_preferences(str(uid))
            except Exception:
                prefs = {"watch_symbols": ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD", "UNI/USD"], "signal_alerts": True}

            user_actionable = [
                a for a in actionable
                if preferences_allow_now(prefs, symbol=str(a.get("symbol") or ""), lifecycle=False)
            ]
            if not user_actionable:
                continue

            for a in user_actionable:
                sym = str(a.get("symbol") or "").strip()
                if not sym:
                    continue
                try:
                    mtf_data = await asyncio.to_thread(analyze_multi_timeframe, sym)
                    news_data = await asyncio.to_thread(news_engine.get_news_for_asset, sym)
                    mtf_data = await asyncio.to_thread(ai_confirm_signal_mtf, mtf_data, news_data)

                    signal_text = format_signal_mtf(mtf_data, news_data)
                    # Automatic delivery must identify the actual agent that generated the signal.
                    signal_text = "🤖 <b>SIGNAL AGENT</b>\n\n" + signal_text
                    if not signal_text:
                        raise ValueError("empty formatted signal")

                    chunks = [signal_text[i:i + 3800] for i in range(0, len(signal_text), 3800)]
                    for chunk in chunks:
                        await context.bot.send_message(
                            chat_id=int(uid),
                            text=chunk,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                        )

                    chart = await asyncio.to_thread(build_signal_chart, mtf_data)
                    sig = mtf_data.get("mtf_signal", (mtf_data.get("15m") or {}).get("signal", "WAIT"))
                    sig_icon = "🟢" if sig == "BUY" else "🔴" if sig == "SELL" else "⏳"
                    tf15 = mtf_data.get("15m") or {}
                    caption = (
                        f"👑 KING ZARRY AI • SIGNAL AGENT\n"
                        f"{sig_icon} {sig} • {sym} • 15M • MTF {mtf_data.get('mtf_bias','')}\n"
                        f"Entry: {float(tf15.get('entry_zone_low', 0)):,.2f} - {float(tf15.get('entry_zone_high', 0)):,.2f}\n"
                        f"SL: {float(tf15.get('stop_loss', 0)):,.2f}\n"
                        f"TP1: {float(tf15.get('tp1', 0)):,.2f}\n"
                        f"TP2: {float(tf15.get('tp2', 0)):,.2f}\n"
                        f"TP3: {float(tf15.get('tp3', 0)):,.2f}"
                    )
                    await context.bot.send_photo(
                        chat_id=int(uid),
                        photo=chart,
                        caption=caption[:1024],
                    )
                except Exception as package_error:
                    logger.warning("agent complete signal package %s %s failed: %s", uid, sym, package_error)
                    continue

            sent += 1
            await asyncio.sleep(0.08)
        except Exception as e:
            logger.debug(f"agent_signal_watch send {uid}: {e}")

    logger.info(f"agent_signal_watch: pushed {len(actionable)} signal(s) to {sent} chat(s)")


async def intelligence_command(update, context):
    """Compatibility handler for /intel and /intelligence.

    The command registrations expect this function, but this deployment
    previously omitted its definition. Reuse the existing agent scan
    implementation so startup succeeds without duplicating or changing
    the market-analysis logic.
    """
    return await agentscan_command(update, context)


async def agentscan_command(update, context):
    """Admin-only: force one agent market scan and reply with results."""
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("Admin only.")
        return
    await update.message.reply_text("🤖 Agent scanning BTC/ETH/SOL/XAU…")
    try:
        from agent_core import tool_analyze_symbol
    except Exception as e:
        await update.message.reply_text(f"agent_core error: {type(e).__name__}")
        return

    lines = ["🤖 <b>AGENT SCAN RESULT</b>", ""]
    actionable = []
    for symbol in AGENT_WATCH_SYMBOLS:
        try:
            analysis = await asyncio.to_thread(tool_analyze_symbol, symbol, "15m")
        except Exception as e:
            lines.append(f"• {html.escape(symbol)}: ERROR {html.escape(type(e).__name__)}")
            continue
        sig = str(analysis.get("signal") or "WAIT").upper()
        price = analysis.get("price")
        late = _agent_signal_is_late(analysis)
        eq = analysis.get("entry_quality") or "—"
        conf = analysis.get("confidence")
        err = analysis.get("error") or analysis.get("reason") or ""
        tag = ""
        if late and sig in ("BUY", "SELL"):
            tag = " — <b>LATE (not sent)</b>"
        elif sig in ("BUY", "SELL") and _agent_signal_is_actionable(analysis):
            tag = " — <b>WOULD PUSH</b>"
            actionable.append(analysis)
        lines.append(
            f"• <b>{html.escape(symbol)}</b>: {html.escape(sig)}"
            + (f" @ {html.escape(str(price))}" if price is not None else "")
            + f" | q={html.escape(str(eq))} conf={html.escape(str(conf))}"
            + tag
        )
        if err and sig == "WAIT":
            lines.append(f"  <i>{html.escape(str(err)[:120])}</i>")

    lines.append("")
    lines.append(f"Actionable now: <b>{len(actionable)}</b>")
    if not actionable:
        lines.append("No Telegram push — market is WAIT or late.")
    else:
        lines.append("Pushing LIVE SIGNAL to admin…")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)

    if actionable:
        # Reuse same format as watch job
        msg = ["🤖 <b>KING ZARRY AGENT — LIVE SIGNAL</b>", "", "Manual /agentscan:", ""]
        for a in actionable:
            msg.append(
                f"• <b>{html.escape(str(a.get('symbol')))}</b> — "
                f"<b>{html.escape(str(a.get('signal') or '').upper())}</b>\n"
                f"  Price: {html.escape(str(a.get('price') or '—'))} | "
                f"Entry: {html.escape(str(a.get('entry') or '—'))}\n"
                f"  SL: {html.escape(str(a.get('stop_loss') or '—'))} | "
                f"TP1: {html.escape(str(a.get('tp1') or '—'))}"
            )
        msg.append("")
        msg.append("<i>Not financial advice. Trading involves risk.</i>")
        text = "\n".join(msg)
        for uid in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=uid, text=text, parse_mode="HTML", disable_web_page_preview=True
                )
            except Exception as e:
                logger.warning("agentscan send failed %s: %s", uid, e)


async def notification_job(context: ContextTypes.DEFAULT_TYPE):
    conn=db_connect()
    try:
        now=datetime.now(timezone.utc)
        rows=conn.execute("SELECT * FROM notifications WHERE active=1").fetchall()
        for r in rows:
            try:
                next_run=datetime.fromisoformat(r["next_run"])
                if next_run.tzinfo is None:
                    next_run=next_run.replace(tzinfo=timezone.utc)
                if next_run<=now:
                    all_users=get_all_users()
                    for uid in all_users:
                        try:
                            await context.bot.send_message(chat_id=uid, text=f"🔔 <b>KING ZARRY AI UPDATE</b>\n\n{escape_html(r['message'])}", parse_mode="HTML", disable_web_page_preview=True)
                            await asyncio.sleep(0.05)
                        except Exception:
                            continue
                    new_next=now+timedelta(seconds=int(r["interval_seconds"]))
                    conn.execute("UPDATE notifications SET next_run=? WHERE id=?", (new_next.isoformat(), r["id"]))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Notify job error for {r['id']}: {e}")
    finally:
        conn.close()

    try:
        await check_personal_price_alerts_job(context)
    except Exception as e:
        logger.warning(f"Personal price alerts job error (admin broadcasts unaffected): {e}")

async def check_personal_price_alerts_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        active_alerts = get_all_active_price_alerts()
        if not active_alerts:
            return
        from collections import defaultdict
        alerts_by_symbol = defaultdict(list)
        for alert in active_alerts:
            alerts_by_symbol[alert["symbol"]].append(alert)
        for symbol, alerts in alerts_by_symbol.items():
            try:
                current_price = await asyncio.to_thread(get_current_price_for_alert, symbol)
                if current_price is None:
                    logger.debug(f"Price unavailable for {symbol}, skipping this cycle")
                    continue
                now_iso = datetime.now(timezone.utc).isoformat()
                for alert in alerts:
                    try:
                        last_price = alert.get("last_checked_price")
                        triggered = check_alert_triggered_v2(
                            current_price=current_price,
                            target_price=float(alert["target_price"]),
                            condition=alert["condition"],
                            last_price=last_price
                        )
                        try:
                            conn = db_connect()
                            try:
                                conn.execute(
                                    "UPDATE price_alerts SET last_checked_price=?, last_checked_at=? WHERE id=?",
                                    (current_price, now_iso, alert["id"])
                                )
                                conn.commit()
                            finally:
                                conn.close()
                        except Exception as db_err:
                            logger.warning(f"Failed to update last_checked for alert {alert['id']}: {db_err}")
                        if triggered:
                            user_id = int(alert["user_id"])
                            target = float(alert["target_price"])
                            cond = alert["condition"]
                            cond_display = {"ABOVE": f"Above {target}", "BELOW": f"Below {target}", "REACHES": f"Reached target"}.get(cond, cond)
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=(
                                        f"🔔 <b>KING ZARRY AI PRICE ALERT</b>\n\n"
                                        f"Asset: <b>{html.escape(symbol)}</b>\n"
                                        f"Target: <b>{target}</b>\n"
                                        f"Current price: <b>{current_price:.2f}</b>\n"
                                        f"Condition: <b>{html.escape(cond_display)}</b>\n\n"
                                        f"Your personal price alert has been triggered."
                                    ),
                                    parse_mode="HTML",
                                    disable_web_page_preview=True
                                )
                                conn = db_connect()
                                try:
                                    conn.execute(
                                        "UPDATE price_alerts SET active=0, triggered=1, triggered_at=?, last_checked_price=?, last_checked_at=? WHERE id=?",
                                        (now_iso, current_price, now_iso, alert["id"])
                                    )
                                    conn.commit()
                                finally:
                                    conn.close()
                                logger.info(f"Price alert triggered: id={alert['id']} user={user_id} {symbol} {cond} {target} current={current_price}")
                            except Forbidden:
                                logger.warning(f"User {user_id} blocked bot, deactivating alert {alert['id']}")
                                conn = db_connect()
                                try:
                                    conn.execute("UPDATE price_alerts SET active=0, triggered=0 WHERE id=?", (alert["id"],))
                                    conn.commit()
                                finally:
                                    conn.close()
                            except Exception as send_err:
                                logger.warning(f"Failed to send alert {alert['id']} to {user_id}: {send_err}")
                    except Exception as per_alert_err:
                        logger.warning(f"Error processing alert {alert.get('id')}: {per_alert_err}")
                        continue
            except Exception as per_symbol_err:
                logger.warning(f"Error processing symbol {symbol}: {per_symbol_err}")
                continue
    except Exception as e:
        logger.warning(f"check_personal_price_alerts_job failed: {e}")

async def alert_command(update, context):
    if not await require_subscription(update):
        return
    user = update.effective_user
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text(
            "🔔 <b>PERSONAL PRICE ALERTS</b>\n\n"
            "Usage:\n"
            "<code>/alert XAU above 4329</code>\n"
            "<code>/alert BTC below 100000</code>\n"
            "<code>/alert ETH reaches 5000</code>\n"
            "<code>/alert gold hits 4329</code>\n\n"
            "Or just say:\n"
            "<i>Alert me when XAU reaches 4329</i>\n"
            "<i>Notify me when BTC goes above 100000</i>\n\n"
            "Manage:\n"
            "/alerts - List your alerts\n"
            "/cancelalert <id> - Cancel one\n"
            "/cancelalert all - Cancel all",
            parse_mode="HTML"
        )
        return
    parsed = parse_alert_request(text)
    if not parsed:
        await update.message.reply_text(
            "❌ Could not parse alert.\n\n"
            "Examples:\n"
            "<code>/alert XAU above 4329</code>\n"
            "<code>/alert BTC below 100000</code>\n"
            "Please include symbol and price.",
            parse_mode="HTML"
        )
        return
    symbol = parsed["symbol"]
    target = parsed["target_price"]
    condition = parsed["condition"]
    if symbol not in ["XAU/USD", "BTC/USD", "ETH/USD", "SOL/USD"]:
        await update.message.reply_text(f"❌ Unsupported asset: {symbol}. Supported: XAU, BTC, ETH, SOL")
        return
    result = create_price_alert(user.id, symbol, target, condition)
    if not result.get("success"):
        if result.get("duplicate"):
            await update.message.reply_text(
                f"⚠️ You already have an active alert for <b>{html.escape(symbol)} {html.escape(condition)} {target}</b>\n\n"
                f"Use /alerts to view it.",
                parse_mode="HTML"
            )
            return
        await update.message.reply_text("❌ Failed to create alert. Try again.")
        return
    cond_display = {"ABOVE": "above", "BELOW": "below", "REACHES": "reaches"}.get(condition, condition)
    await update.message.reply_text(
        f"🔔 <b>Alert created.</b>\n"
        f"{html.escape(symbol)}\n"
        f"Condition: {html.escape(cond_display)} {target}\n"
        f"I'll monitor it automatically and notify you when the target is reached.\n\n"
        f"🆔 ID: <code>{result['id']}</code> | Use /alerts to manage",
        parse_mode="HTML"
    )

async def alerts_command(update, context):
    if not await require_subscription(update):
        return
    user = update.effective_user
    alerts = get_user_price_alerts(user.id, active_only=True)
    if not alerts:
        await update.message.reply_text(
            "📭 No active personal price alerts.\n\n"
            "Create one:\n"
            "<code>/alert XAU above 4329</code>\n"
            "Or: <i>Alert me when XAU reaches 4329</i>",
            parse_mode="HTML"
        )
        return
    lines = ["🔔 <b>YOUR PRICE ALERTS</b>\n"]
    for idx, a in enumerate(alerts, 1):
        cond_symbol = {"ABOVE": "≥", "BELOW": "≤", "REACHES": "≈"}.get(a["condition"], a["condition"])
        lines.append(
            f"{idx}. {html.escape(a['symbol'])} {cond_symbol} {a['target_price']}\n"
            f"   ID: <code>{a['id']}</code> | Status: Active | {html.escape(a['condition'])}\n"
        )
    lines.append("\nCancel: /cancelalert <id> or /cancelalert all")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cancelalert_command(update, context):
    if not await require_subscription(update):
        return
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "<code>/cancelalert 1</code> - Cancel alert ID 1\n"
            "<code>/cancelalert all</code> - Cancel all your alerts\n\n"
            "Use /alerts to see IDs",
            parse_mode="HTML"
        )
        return
    arg = context.args[0].lower().strip()
    if arg == "all":
        count = cancel_all_user_alerts(user.id)
        await update.message.reply_text(f"✅ Cancelled {count} personal alert(s).")
        return
    try:
        alert_id = int(arg)
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Use /alerts to see your alert IDs.")
        return
    success = cancel_user_alert(user.id, alert_id)
    if success:
        await update.message.reply_text(f"✅ Alert {alert_id} cancelled.")
    else:
        await update.message.reply_text(f"❌ Alert {alert_id} not found or not yours.")

async def ask_command(update, context):
    if not await require_subscription(update):
        return
    question=" ".join(context.args).strip()
    if not question:
        await update.message.reply_text("Usage:\n/ask What is Bitcoin?"); return
    await update.message.chat.send_action("typing")
    try:
        user_id=str(update.effective_user.id)
        upper_q = question.upper()
        for asset_kw in ["BTC", "ETH", "SOL", "XAU", "GOLD"]:
            if asset_kw in upper_q:
                try:
                    memory_instance.save_trading_preferences(user_id, preferred_assets=asset_kw)
                except:
                    pass
                break
        answer=await asyncio.to_thread(ai_engine.ask, user_id, question, None)
        await send_ai_response(update.message, answer)
    except Exception as error:
        logger.error(f"ask_ai Error: {error}")
        await update.message.reply_text("⚠️ <b>AI Service Temporarily Unavailable</b>\n\nPlease try again in a few seconds.",parse_mode="HTML")

async def tts_command(update, context):
    if not await require_subscription(update):
        return
    text=" ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage:\n/tts Hello from King Zarry AI!"); return
    await update.message.chat.send_action("record_voice")
    try:
        voice_io=await create_voice_note_file(text)
        await update.message.reply_voice(voice=voice_io, caption="👑 King Zarry AI")
    except Exception as error:
        logger.error(f"TTS Error: {error}")
        await update.message.reply_text("❌ TTS Error: Unable to generate voice note.",disable_web_page_preview=True)

async def quick_symbol_command(symbol, update, context):
    if not await require_subscription(update):
        return
    await update.message.chat.send_action("typing")
    status=await update.message.reply_text(f"👑 <b>KING ZARRY AI</b>\n\n📡 Multi-timeframe analysis 4H→1H→15M→5M...\n📊 {symbol}\n📰 Checking news & events...",parse_mode="HTML")
    try:
        mtf_data = await asyncio.to_thread(analyze_multi_timeframe, symbol)
        news_data = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
        mtf_data = await asyncio.to_thread(ai_confirm_signal_mtf, mtf_data, news_data)
        try:
            memory_instance.save_trading_preferences(str(update.effective_user.id), preferred_assets=symbol)
        except:
            pass
        await send_long_message(update.message, format_signal_mtf(mtf_data, news_data), is_raw_html=True)
        try:
            chart=await asyncio.to_thread(build_signal_chart, mtf_data)
            sig = mtf_data.get("mtf_signal", mtf_data["15m"]["signal"])
            sig_icon=("🟢" if sig=="BUY" else "🔴" if sig=="SELL" else "⏳")
            caption=(f"👑 KING ZARRY AI\n{sig_icon} {sig} • {symbol} • 15M MTF {mtf_data.get('mtf_bias','')}\nEntry: {mtf_data['15m']['entry_zone_low']:,.2f} - {mtf_data['15m']['entry_zone_high']:,.2f}\nSL: {mtf_data['15m']['stop_loss']:,.2f}\nTP3: {mtf_data['15m']['tp3']:,.2f}\nNews: {news_data.get('risk','LOW')} risk") if sig!="WAIT" else (f"👑 KING ZARRY AI\n⏳ WAIT / NO TRADE • {symbol} • 15M MTF")
            await update.message.reply_photo(photo=chart,caption=caption)
        except Exception as chart_error:
            logger.warning(f"Chart error: {chart_error}")
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as error:
        logger.error(f"Signal Error: {error}")
        try:
            await status.edit_text("❌ <b>Signal Error</b>\n\nFailed to fetch market data. Please try again.",parse_mode="HTML")
        except Exception:
            await update.message.reply_text("❌ Signal Error: Unable to fetch market data.",disable_web_page_preview=True)

async def btc_command(update, context):
    await quick_symbol_command("BTC/USD",update,context)
async def eth_command(update, context):
    await quick_symbol_command("ETH/USD",update,context)
async def sol_command(update, context):
    await quick_symbol_command("SOL/USD",update,context)
async def xau_command(update, context):
    await quick_symbol_command("XAU/USD",update,context)

async def signal_command(update, context):
    if not await require_subscription(update):
        return
    raw=" ".join(context.args).strip()
    symbol,timeframe=detect_market_and_timeframe(raw or "XAUUSD")
    interval=normalize_timeframe(timeframe)
    status=await update.message.reply_text(f"👑 <b>KING ZARRY AI</b>\n\n📡 Multi-timeframe scanning 4H→1H→15M→5M...\n📊 {symbol}\n⏱ Primary {interval} (MTF)\n📰 News check...",parse_mode="HTML")
    try:
        mtf_data = await asyncio.to_thread(analyze_multi_timeframe, symbol)
        news_data = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
        mtf_data = await asyncio.to_thread(ai_confirm_signal_mtf, mtf_data, news_data)
        await send_long_message(update.message, format_signal_mtf(mtf_data, news_data), is_raw_html=True)
        try:
            chart=await asyncio.to_thread(build_signal_chart, mtf_data)
            sig = mtf_data.get("mtf_signal", mtf_data["15m"]["signal"])
            sig_icon=("🟢" if sig=="BUY" else "🔴" if sig=="SELL" else "⏳")
            caption=(f"👑 KING ZARRY AI\n{sig_icon} {sig} • {symbol} • 15M • MTF {mtf_data.get('mtf_bias','')}\nEntry: {mtf_data['15m']['entry_zone_low']:,.2f} - {mtf_data['15m']['entry_zone_high']:,.2f}\nSL: {mtf_data['15m']['stop_loss']:,.2f}\nTP3: {mtf_data['15m']['tp3']:,.2f}") if sig!="WAIT" else (f"👑 KING ZARRY AI\n⏳ WAIT • {symbol} • 15M")
            await update.message.reply_photo(photo=chart,caption=caption)
        except Exception as chart_error:
            logger.warning(f"Chart generation error: {chart_error}")
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as error:
        logger.error(f"Signal Error: {error}")
        try:
            await status.edit_text("❌ <b>Signal Error</b>\n\nFailed to fetch market data. Please try again.",parse_mode="HTML")
        except Exception:
            await update.message.reply_text("❌ Signal Error: Unable to fetch market data.",disable_web_page_preview=True)

async def plan_command(update, context):
    if not await require_subscription(update):
        return
    raw=" ".join(context.args).strip()
    if not raw:
        await update.message.reply_text("Usage:\n/plan BTC\n/plan XAU\n/plan ETH 15m")
        return
    symbol, timeframe = detect_market_and_timeframe(raw)
    await update.message.chat.send_action("typing")
    status=await update.message.reply_text(f"👑 <b>KING ZARRY AI ONE-DAY PLANNER</b>\n\n📊 Analyzing {symbol}...\n⏱ 4H→1H→15M→5M\n📰 News + Calendar\n🧠 AI Planning...",parse_mode="HTML")
    try:
        mtf_data = await asyncio.to_thread(analyze_multi_timeframe, symbol)
        news_data = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
        mtf_data = await asyncio.to_thread(ai_confirm_signal_mtf, mtf_data, news_data)
        tf_15m = mtf_data["15m"]
        tf_4h = mtf_data["4h"]
        tf_1h = mtf_data["1h"]
        tf_5m = mtf_data["5m"]
        late_entry = detect_late_entry_status(tf_15m, tf_5m, tf_1h)
        planner_prompt = f"""
Create ONE-DAY TRADE PLAN for {symbol}

Use this MTF data:

4H Regime: {tf_4h.get('trend')} Signal {tf_4h.get('signal')} RSI {tf_4h.get('rsi',0):.1f} Structure {tf_4h.get('structure')} Support {tf_4h.get('support',0):.2f} Resistance {tf_4h.get('resistance',0):.2f}
1H Confirmation: {tf_1h.get('trend')} Signal {tf_1h.get('signal')} RSI {tf_1h.get('rsi',0):.1f} Structure {tf_1h.get('structure')}
15M Primary: Price {tf_15m.get('price',0):.2f} Signal {tf_15m.get('signal')} Strength {tf_15m.get('strength')} Confidence {tf_15m.get('confidence')} RSI {tf_15m.get('rsi',0):.1f} EMA9 {tf_15m.get('ema9',0):.2f} EMA21 {tf_15m.get('ema21',0):.2f} EMA50 {tf_15m.get('ema50',0):.2f} ATR {tf_15m.get('atr',0):.2f}
15M Entry: {tf_15m.get('entry_zone_low',0):.2f}-{tf_15m.get('entry_zone_high',0):.2f} SL {tf_15m.get('stop_loss',0):.2f} TP1 {tf_15m.get('tp1',0):.2f} TP2 {tf_15m.get('tp2',0):.2f} TP3 {tf_15m.get('tp3',0):.2f}
5M Timing: Signal {tf_5m.get('signal')} Trend {tf_5m.get('trend')} RSI {tf_5m.get('rsi',0):.1f}

MTF Bias: {mtf_data.get('mtf_bias')} MTF Signal: {mtf_data.get('mtf_signal')} Conflict: {mtf_data.get('conflict')} MTF Strength: {mtf_data.get('mtf_strength')}
Late Entry: {late_entry['status']} Action: {late_entry['action']} Score: {late_entry['score']}
Exhaustion: {tf_15m.get('exhaustion_advanced',{}).get('score',0)}/100 Warnings: {'; '.join(tf_15m.get('exhaustion_advanced',{}).get('warnings',[])[:2])}
News Risk: {news_data.get('risk','LOW')} Events: {len(news_data.get('events',[]))} Summary: {news_data.get('summary','')}
Upcoming Events: {'; '.join([e.get('event','')[:40] for e in news_data.get('events',[])[:3]])}

Produce ONE-DAY TRADE PLAN in this exact format:

👑 KING ZARRY AI
ONE-DAY TRADE PLAN

Asset: {symbol}
Market Bias: BULLISH/BEARISH/NEUTRAL
Preferred Direction: BUY/SELL/WAIT
Primary Setup: description
Entry Zone: numbers
Invalidation: number
SL: number
TP1: number
TP2: number
TP3: number
Expected Risk: 1:X
News Risk: LOW/MEDIUM/HIGH/EXTREME
Major Events: list
Best Trading Window: time suggestion
Avoid Trading When: conditions
Late Entry Level: price
Confidence: X/100
AI Note: short

IMPORTANT: This is a plan, not a guarantee. Use risk management.
Do NOT invent prices - use provided numbers.
"""
        ai_plan = await asyncio.to_thread(ai_engine.ask, str(update.effective_user.id), planner_prompt, None)
        await send_ai_response(update.message, ai_plan)
        try:
            chart=await asyncio.to_thread(build_signal_chart, mtf_data)
            await update.message.reply_photo(photo=chart, caption=f"👑 KING ZARRY AI - ONE DAY PLAN {symbol} - {mtf_data.get('mtf_bias')} - {news_data.get('risk')} News Risk")
        except Exception as e:
            logger.warning(f"Plan chart error: {e}")
        try:
            await status.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"Plan error: {e}")
        try:
            await status.edit_text("❌ <b>Plan Error</b>\n\nFailed to generate plan. Try again.", parse_mode="HTML")
        except:
            await update.message.reply_text("❌ Failed to generate trade plan.")

async def news_command(update, context):
    if not await require_subscription(update):
        return
    raw=" ".join(context.args).strip() or "BTC"
    symbol, _ = detect_market_and_timeframe(raw)
    await update.message.chat.send_action("typing")
    try:
        news_data = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
        text = f"👑 <b>KING ZARRY AI - NEWS {symbol}</b>\n\n"
        risk_emoji = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🟠","EXTREME":"🔴"}.get(news_data.get("risk","LOW"),"⚪")
        text += f"{risk_emoji} <b>NEWS RISK: {news_data.get('risk','LOW')}</b>\n\n"
        if news_data.get("events"):
            text += f"📅 <b>UPCOMING EVENTS ({len(news_data['events'])}):</b>\n"
            for ev in news_data["events"][:6]:
                imp = ev.get("importance","")
                imp_icon = "🔴" if str(imp).lower() in ["high","3","red"] else "🟡" if str(imp).lower() in ["medium","2"] else "⚪"
                text += f"{imp_icon} {html.escape(ev.get('event','')[:60])} - {html.escape(str(ev.get('time','')))} ({html.escape(str(ev.get('currency','')))}) - {html.escape(str(imp))}\n"
        else:
            text += "📅 No high-impact events in next 24H\n"
        if news_data.get("headlines"):
            text += "\n📰 <b>HEADLINES:</b>\n"
            for h in news_data["headlines"][:4]:
                text += f"• {html.escape(h.get('title','')[:80])} ({html.escape(h.get('source',''))})\n"
        if not news_data.get("news_available"):
            text += "\n📰 Status: NEWS DATA UNAVAILABLE (calendar fallback)\n"
        text += f"\n<i>Checked: {news_data.get('checked_at','')}</i>"
        await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"News error: {e}")
        await update.message.reply_text("❌ News unavailable.", disable_web_page_preview=True)



def _fiverr_is_admin(update) -> bool:
    user = getattr(update, "effective_user", None)
    return bool(user and (not ADMIN_IDS or user.id in ADMIN_IDS))

def _fiverr_usage() -> str:
    return (
        "🧑‍💻 <b>FIVERR AGENT</b>\n\n"
        "A separate Agent for your Fiverr business.\n\n"
        "Commands:\n"
        "• <code>/fiverr setup</code> — connect/configure your Fiverr workspace\n"
        "• <code>/fiverr status</code> — show Fiverr workspace status\n"
        "• <code>/fiverr skills</code> — show all skills\n"
        "• <code>/fiverr gig</code> — build a complete Gig draft\n"
        "• <code>/fiverr optimize</code> — improve an existing Gig\n"
        "• <code>/fiverr seo</code> — keyword/tag research\n"
        "• <code>/fiverr reply</code> — prepare a Buyer reply\n"
        "• <code>/fiverr offer</code> — prepare a Custom Offer\n"
        "• <code>/fiverr profile</code> — build profile copy\n"
        "• <code>/fiverr order</code> — order intake + plan\n"
        "• <code>/fiverr delivery</code> — delivery workflow\n"
        "• <code>/fiverr portfolio</code> — portfolio case study\n"
        "• <code>/fiverr pricing</code> — pricing options\n"
        "• <code>/fiverr analytics</code> — analyze supplied metrics\n"
        "• <code>/fiverr brief</code> — workspace brief\n"
        "• <code>/fiverr policy</code> — policy check\n"
        "• <code>/fiverr tasks</code> — workflow history\n"
        "• <code>/fiverr inbox</code> — synced Fiverr inbox events\n"
        "• <code>/fiverr read ID</code> — mark an inbox item read\n"
        "• <code>/fiverr approve ID</code> / <code>reject ID</code>\n"
        "• <code>/fiverr pack TASK_ID</code> — manual execution pack\n\n"
        "After starting a task, I can ask questions here on Telegram and continue from your answers."
    )

async def fiverr_command(update, context):
    if not update.message or not _fiverr_is_admin(update):
        if update.message:
            await update.message.reply_text("🧑‍💻 Fiverr Agent is private to the configured admin.")
        return
    if fiverr_agent is None:
        await update.message.reply_text("❌ Fiverr Agent module is unavailable.")
        return

    args = list(getattr(context, "args", []) or [])
    sub = (args[0].lower() if args else "help")
    user_id = str(update.effective_user.id)

    if sub in {"help", "start"}:
        await update.message.reply_text(
            _fiverr_usage(), parse_mode="HTML", disable_web_page_preview=True
        )
        return

    if sub == "status":
        workspace = fiverr_agent.get_workspace(user_id)
        missing = fiverr_agent.workspace_missing(workspace)
        message = fiverr_agent.workspace_text(workspace)
        if missing:
            message += "\n\n🟡 <b>Still needed:</b> " + ", ".join(html.escape(x) for x in missing)
        await update.message.reply_text(
            message, parse_mode="HTML", disable_web_page_preview=True
        )
        return

    if sub == "setup":
        task = fiverr_agent.create_task(
            user_id,
            "workspace_setup",
            "Connect Fiverr workspace",
            {
                "skill": "workflow",
                "step": "setup_questions",
                "messages": [],
                "workspace": fiverr_agent.get_workspace(user_id),
            },
        )
        await update.message.reply_text(
            "🧑‍💻 <b>FIVERR AGENT — WORKSPACE SETUP</b>\n\n"
            "Send these details in one message (you can also send them naturally):\n"
            "1. Fiverr profile URL or username\n"
            "2. Seller/display name\n"
            "3. Main service\n"
            "4. Target buyer\n"
            "5. Starting price/package range\n\n"
            "I will save the workspace and ask only for anything still missing.\n\n"
            "🔐 Never send your Fiverr password, 2FA code, recovery code or session cookie.\n\n"
            f"Setup task: <code>{html.escape(task['id'][:8])}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if sub == "skills":
        await update.message.reply_text(
            "🧑‍💻 <b>FIVERR AGENT SKILLS</b>\n\n" + fiverr_agent.skills_text(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if sub == "tasks":
        tasks = fiverr_agent.list_tasks(user_id, 12)
        if not tasks:
            await update.message.reply_text("🧑‍💻 No Fiverr Agent tasks yet.")
            return
        lines = ["🧑‍💻 <b>FIVERR WORKFLOW</b>", ""]
        for t in tasks:
            lines.append(
                f"• <code>{html.escape(t['id'][:8])}</code> — "
                f"{html.escape(t['kind'])} — {html.escape(t['status'])}"
            )
        await update.message.reply_text(
            "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True
        )
        return

    if sub == "inbox":
        items = fiverr_agent.list_inbox(user_id, 20)
        if not items:
            await update.message.reply_text(
                "📥 <b>FIVERR INBOX</b>\n\nNo synced Fiverr messages yet. "
                "The inbox becomes live when an official/supported integration sends events to the Agent.",
                parse_mode="HTML", disable_web_page_preview=True
            )
            return
        lines = ["📥 <b>FIVERR INBOX</b>", ""]
        for item in items:
            status = "🟡" if item.get("status") == "unread" else "⚪"
            sender = item.get("sender_name") or item.get("sender_username") or "Buyer"
            preview = str(item.get("message") or "").replace("\n", " ")[:180]
            lines.append(
                f"{status} <code>{html.escape(str(item['id'])[:8])}</code> "
                f"<b>{html.escape(str(sender)[:60])}</b> — {html.escape(preview)}"
            )
        lines.append("\nUse <code>/fiverr read ID</code> after reviewing an item.")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)
        return

    if sub == "read":
        if len(args) < 2:
            await update.message.reply_text("Use <code>/fiverr read ID</code>.", parse_mode="HTML")
            return
        items = fiverr_agent.list_inbox(user_id, 50)
        item = next((x for x in items if x["id"] == args[1] or x["id"].startswith(args[1])), None)
        if not item:
            await update.message.reply_text("❌ Fiverr inbox item not found.")
            return
        fiverr_agent.mark_inbox_read(item["id"], user_id)
        sender = item.get("sender_name") or item.get("sender_username") or "Buyer"
        await update.message.reply_text(
            "📥 <b>FIVERR MESSAGE</b>\n\n"
            f"From: <b>{html.escape(str(sender))}</b>\n"
            f"{html.escape(str(item.get('message') or ''))}\n\n"
            "Use <code>/fiverr reply</code> to prepare a response, then paste the buyer's "
            "message/context when asked.",
            parse_mode="HTML", disable_web_page_preview=True
        )
        return

    if sub == "pack":
        if len(args) < 2:
            await update.message.reply_text(
                "Use <code>/fiverr pack TASK_ID</code> after approval.",
                parse_mode="HTML",
            )
            return
        task_id = args[1]
        tasks = fiverr_agent.list_tasks(user_id, 50)
        task = next((t for t in tasks if t["id"] == task_id or t["id"].startswith(task_id)), None)
        if not task:
            await update.message.reply_text("❌ Fiverr task not found.")
            return
        if task.get("status") not in {"approved_for_manual_execution", "awaiting_approval"}:
            await update.message.reply_text(
                "🟡 This task is not approved yet. Review the draft first."
            )
            return
        await update.message.reply_text(
            "<pre>" + html.escape(fiverr_agent.render_manual_execution_pack(task))[:11000] + "</pre>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    if sub in {"approve", "reject"}:
        if len(args) < 2:
            await update.message.reply_text(
                "Use <code>/fiverr approve APPROVAL_ID</code> or "
                "<code>/fiverr reject APPROVAL_ID</code>.",
                parse_mode="HTML",
            )
            return
        result = fiverr_agent.decide_approval(args[1], user_id, sub == "approve")
        if not result:
            await update.message.reply_text("❌ Approval ID not found.")
            return

        task_id = str((result.get("payload") or {}).get("task_id") or "")
        if sub == "approve":
            if task_id:
                task = fiverr_agent.update_task(
                    task_id, user_id, status="approved_for_manual_execution",
                    data={"approval_id": result["id"], "execution_mode": "manual"}
                )
            else:
                task = None
            await update.message.reply_text(
                "✅ <b>FIVERR DRAFT APPROVED</b>\n\n"
                "The Agent will not pretend to publish or send it. "
                "Your approved manual execution pack is ready.\n\n"
                + (f"Use <code>/fiverr pack {html.escape(task_id[:8])}</code>."
                   if task_id else "No linked task was found."),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            if task_id:
                fiverr_agent.update_task(
                    task_id, user_id, status="rejected",
                    data={"approval_id": result["id"]}
                )
            await update.message.reply_text(
                "🛑 Fiverr draft rejected and recorded. Send a new instruction when ready."
            )
        return

    kind_map = {
        "gig": ("gig_creator", "Build a complete Fiverr Gig"),
        "optimize": ("gig_optimizer", "Optimize an existing Fiverr Gig"),
        "reply": ("client_reply", "Prepare a Fiverr Buyer reply"),
        "offer": ("custom_offer", "Prepare a Fiverr Custom Offer"),
        "profile": ("profile_builder", "Build Fiverr profile copy"),
        "seo": ("seo_research", "Research Fiverr keywords and tags"),
        "order": ("order_intake", "Plan a Fiverr order"),
        "delivery": ("delivery_planner", "Build a Fiverr delivery plan"),
        "portfolio": ("portfolio_builder", "Build a Fiverr portfolio case study"),
        "pricing": ("pricing", "Prepare Fiverr pricing options"),
        "analytics": ("analytics", "Analyze supplied Fiverr metrics"),
        "brief": ("fiverr_brief", "Build a Fiverr workspace brief"),
        "policy": ("policy_guard", "Run a Fiverr policy check"),
    }
    if sub not in kind_map:
        await update.message.reply_text(
            _fiverr_usage(), parse_mode="HTML", disable_web_page_preview=True
        )
        return

    kind, title = kind_map[sub]
    task = fiverr_agent.create_task(
        user_id,
        kind,
        title,
        {"skill": kind, "step": "waiting_for_brief", "messages": []},
    )
    await update.message.reply_text(
        f"🧑‍💻 <b>FIVERR AGENT — {html.escape(kind.upper())}</b>\n\n"
        "Tell me what you want done. You can give me a short brief or all the details.\n"
        "I will keep the task saved, ask focused questions if needed, then prepare a "
        "professional draft for your approval.\n\n"
        f"Task: <code>{html.escape(task['id'][:8])}</code>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def _fiverr_continue_task(update, context, text: str) -> bool:
    if fiverr_agent is None or not _fiverr_is_admin(update):
        return False

    user_id = str(update.effective_user.id)
    task = fiverr_agent.get_open_task(user_id)
    if not task or task.get("status") != "waiting_for_user":
        return False

    data = dict(task.get("data") or {})
    messages = list(data.get("messages") or [])
    messages.append({"role": "user", "content": text})
    data["messages"] = messages
    kind = str(task.get("kind") or "workflow")
    step = str(data.get("step") or "")

    if kind == "workspace_setup" and step == "setup_questions":
        prompt = (
            "Extract the Fiverr workspace details from this conversation. Return JSON only "
            "with keys: profile_url, username, seller_name, main_service, target_buyer, "
            "starting_price. Preserve known values and use empty strings for missing values.\n\n"
            + fiverr_agent.task_context({"data": data})
        )
        try:
            raw = await asyncio.to_thread(
                ai_engine.ask, user_id, prompt, None
            )
            match = re.search(r"\{.*\}", raw or "", flags=re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
        except Exception:
            parsed = {}

        if not isinstance(parsed, dict):
            parsed = {}

        workspace = fiverr_agent.save_workspace(user_id, parsed)
        missing = fiverr_agent.workspace_missing(workspace)
        if missing:
            data["workspace"] = workspace
            data["step"] = "setup_questions"
            fiverr_agent.update_task(
                task["id"], user_id, status="waiting_for_user", data=data
            )
            await update.message.reply_text(
                "🧑‍💻 <b>WORKSPACE ALMOST READY</b>\n\n"
                "I saved what you gave me. I only need:\n"
                + "\n".join(f"• {html.escape(item)}" for item in missing)
                + "\n\nReply naturally with those details.",
                parse_mode="HTML",
            )
            return True

        data["workspace"] = workspace
        data["step"] = "connected"
        fiverr_agent.update_task(
            task["id"], user_id, status="connected", data=data
        )
        await update.message.reply_text(
            fiverr_agent.workspace_text(workspace)
            + "\n\n✅ <b>Workspace ready.</b> Use <code>/fiverr gig</code>, "
              "<code>/fiverr optimize</code>, <code>/fiverr reply</code> or any other skill.",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return True

    if step in {"waiting_for_brief", "needs_revision"}:
        data["step"] = "drafting"
        await update.message.chat.send_action("typing")
        workspace = fiverr_agent.get_workspace(user_id)
        prompt = (
            f"{fiverr_agent.agent_system_instructions()}\n\n"
            f"SAVED FIVERR WORKSPACE:\n{json.dumps(workspace, ensure_ascii=False)}\n\n"
            f"SKILL: {kind}\n\n"
            "CONVERSATION SO FAR:\n" + fiverr_agent.task_context({"data": data}) + "\n\n"
            "TASK:\n"
            "First decide whether essential information is missing. If it is missing, "
            "ask only the smallest number of focused questions (maximum 3) and do not "
            "produce an approval-ready draft. If enough information exists, produce the "
            "complete professional draft. For gig_creator include title, category, tags, "
            "packages, delivery, revisions, description, FAQs, requirements and gallery "
            "checklist. For other skills use the fields appropriate to that skill.\n"
            "Never claim you accessed Fiverr."
        )
        try:
            answer = await asyncio.to_thread(ai_engine.ask, user_id, prompt, None)
        except Exception as exc:
            logger.warning("Fiverr Agent AI drafting failed: %s", exc)
            answer = (
                "I need a few details before I can prepare this: "
                "what exactly are you selling, who is the target buyer, and what price/"
                "delivery range should I use?"
            )

        data["last_response"] = answer
        if fiverr_agent.is_missing_information_response(answer):
            data["step"] = "waiting_for_brief"
            fiverr_agent.update_task(
                task["id"], user_id, status="waiting_for_user", data=data
            )
            await update.message.reply_text(
                "🧑‍💻 <b>FIVERR AGENT — MORE INFO NEEDED</b>\n\n"
                + html.escape(answer[:5000]),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return True

        data["draft"] = answer
        check = fiverr_agent.policy_check(answer)
        data["policy_check"] = check
        if check["ok"]:
            data["step"] = "awaiting_approval"
            task = fiverr_agent.update_task(
                task["id"], user_id, status="awaiting_approval", data=data
            )
            approval = fiverr_agent.create_approval(
                user_id,
                f"prepare_{kind}",
                {"task_id": task["id"], "draft": answer, "policy": check},
            )
            await update.message.reply_text(
                "🧑‍💻 <b>FIVERR AGENT — DRAFT READY FOR APPROVAL</b>\n\n"
                + html.escape(answer[:6500])
                + "\n\n🛡 <b>Policy check:</b> "
                + html.escape(check["message"])
                + f"\n\nApproval: <code>{html.escape(approval['id'])}</code>\n"
                f"Approve with <code>/fiverr approve {html.escape(approval['id'])}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            data["step"] = "needs_revision"
            fiverr_agent.update_task(
                task["id"], user_id, status="waiting_for_user", data=data
            )
            await update.message.reply_text(
                "⚠️ <b>POLICY REVIEW NEEDS REVISION</b>\n\n"
                + html.escape(check["message"])
                + "\n\nSend your revision instruction and I will rebuild the draft.",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        return True

    return False

async def events_command(update, context):
    if not await require_subscription(update):
        return
    await update.message.chat.send_action("typing")
    try:
        events = await asyncio.to_thread(news_engine.get_upcoming_events, 24)
        if not events:
            await update.message.reply_text("📅 <b>ECONOMIC CALENDAR</b>\n\n🟢 No high-impact events in next 24H\n📰 Status: NEWS DATA UNAVAILABLE", parse_mode="HTML")
            return
        text = "📅 <b>ECONOMIC CALENDAR - NEXT 24H</b>\n\n"
        for ev in events[:10]:
            imp = ev.get("importance","")
            imp_icon = "🔴" if str(imp).lower() in ["high","3","red"] else "🟡" if str(imp).lower() in ["medium","2"] else "⚪"
            text += f"{imp_icon} <b>{html.escape(ev.get('event','')[:60])}</b>\n   Time: {html.escape(str(ev.get('time','')))} | {html.escape(str(ev.get('currency','')))} | {html.escape(str(imp))}\n\n"
        text += "\n⚠️ <i>Major events may cause volatility. Reduce size before events.</i>"
        await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Events error: {e}")
        await update.message.reply_text("❌ Calendar unavailable.", disable_web_page_preview=True)

async def handle_photo(update, context):
    if not await require_subscription(update):
        return
    photo=update.message.photo[-1]
    prompt=update.message.caption or "Analyze this chart or image. If it is a financial chart, identify trend, support/resistance, market pattern, and potential setups. Consider multi-timeframe context."
    await update.message.chat.send_action("typing")
    try:
        file=await context.bot.get_file(photo.file_id)
        image_bytes=bytes(await file.download_as_bytearray())
        mime_type="image/jpeg"
        if file.file_path:
            fp=file.file_path.lower()
            if fp.endswith(".png"):
                mime_type="image/png"
            elif fp.endswith(".webp"):
                mime_type="image/webp"
            elif fp.endswith(".jpg") or fp.endswith(".jpeg"):
                mime_type="image/jpeg"
        user_id=str(update.effective_user.id)
        analysis=await asyncio.to_thread(ai_engine.ask, user_id, prompt, (mime_type, image_bytes))
        await send_ai_response(update.message, analysis)
    except Exception as error:
        logger.error(f"Vision Error: {error}")
        await update.message.reply_text("❌ <b>Vision Analysis Error</b>\n\nUnable to analyze image. Ensure vision API keys are valid.",parse_mode="HTML")

async def _process_telegram_text_pipeline(update, context, text: str, is_voice_transcription: bool = False):
    if not text or not text.strip():
        return
    text = text.strip()
    if text.startswith("/") and not is_voice_transcription:
        return
    if not await require_subscription(update):
        return
    user_id = str(update.effective_user.id)
    upper = text.upper()
    for kw in ["BTC", "ETH", "SOL", "XAU", "GOLD"]:
        if kw in upper and len(text) < 80:
            try:
                memory_instance.save_trading_preferences(user_id, preferred_assets=kw)
            except:
                pass
            break

    try:
        if _looks_like_media_request(text):
            logger.info(f"Media request detected, routing to ai_engine: '{text[:60]}'")
            answer = await asyncio.to_thread(ai_engine.ask, user_id, text, None)
            await send_ai_response(update.message, answer)
            return
    except Exception as media_err:
        logger.warning(f"Media intent pre-check failed (non-fatal): {media_err}")

    # FIX: only parse a price alert when the user actually mentions alerts.
    parsed_alert = parse_alert_request(text) if _ALERT_INTENT_RE.search(text) else None
    if parsed_alert:
        logger.info(f"Personal alert intent detected: '{text}' -> {parsed_alert}")
        user_telegram_id = update.effective_user.id
        symbol = parsed_alert["symbol"]
        target = parsed_alert["target_price"]
        condition = parsed_alert["condition"]
        result = create_price_alert(user_telegram_id, symbol, target, condition)
        if result.get("success"):
            cond_display = {"ABOVE": "above", "BELOW": "below", "REACHES": "reaches"}.get(condition, condition)
            await update.message.reply_text(
                f"🔔 <b>Alert created.</b>\n"
                f"{html.escape(symbol)}\n"
                f"Condition: {html.escape(cond_display)} {target}\n"
                f"I'll monitor it automatically and notify you when the target is reached.\n\n"
                f"🆔 ID: <code>{result['id']}</code> | Use /alerts to manage\n\n"
                f"🔔 Background scheduler checks every 60s alongside admin broadcasts",
                parse_mode="HTML"
            )
            return
        elif result.get("duplicate"):
            await update.message.reply_text(
                f"⚠️ You already have an active alert for <b>{html.escape(symbol)} {html.escape(condition)} {target}</b>\n\n"
                f"Use /alerts to view it.",
                parse_mode="HTML"
            )
            return
        else:
            await update.message.reply_text("❌ Failed to create alert. Please try again with format: Alert me when XAU reaches 4329")
            return

    is_notify, notify_type, notify_detail = detect_notification_intent(text)
    if is_notify:
        logger.info(f"Notification intent detected: '{text}' -> {notify_type} {notify_detail}")
        if notify_type == "price_alert":
            await update.message.reply_text(
                f"🔔 <b>KING ZARRY AI - PERSONAL ALERTS</b>\n\n"
                f"I can create personal price alerts for you!\n\n"
                f"Please specify clearly:\n"
                f"• <code>Alert me when XAU reaches 4329</code>\n"
                f"• <code>/alert XAU above 4329</code>\n"
                f"• <code>/alert BTC below 100000</code>\n\n"
                f"Supported: XAU, BTC, ETH, SOL | Conditions: above, below, reaches\n\n"
                f"Your alert will be stored only for your Telegram ID and checked every 60s by the scheduler.",
                parse_mode="HTML", disable_web_page_preview=True
            )
            return
        elif notify_type == "reminder":
            await update.message.reply_text(
                f"👑 <b>KING ZARRY AI - REMINDERS</b>\n\n"
                f"🔔 Scheduler: <b>ACTIVE</b> (JobQueue every 60s)\n"
                f"📝 Request: <code>{html.escape(text)}</code>\n\n"
                f"⚠️ Per-user timed reminders like 'tomorrow at 9am' are <b>not yet implemented</b> in this build.\n\n"
                f"✅ What IS implemented:\n"
                f"• Personal price alerts: <code>/alert XAU above 4329</code>\n"
                f"• Admin broadcasts: <code>/notify 3600 Your message</code>\n"
                f"• News monitor with 6h deduplication\n\n"
                f"<i>Price alerts ARE working, but datetime reminders need additional implementation.</i>",
                parse_mode="HTML", disable_web_page_preview=True
            )
            return
        elif notify_type == "briefing":
            await update.message.reply_text(
                f"👑 <b>KING ZARRY AI - BRIEFING SCHEDULER</b>\n\n"
                f"🔔 Notification job: <b>Scheduled every 60s</b> (Railway logs confirmed)\n"
                f"📝 Request: <code>{html.escape(text)}</code>\n\n"
                f"✅ Implemented:\n"
                f"• Personal price alerts: <code>/alert XAU above 4329</code> - checks every 60s\n"
                f"• Admin broadcast: <code>/notify 86400 BTC briefing</code> every 24h\n"
                f"• News monitor automatic high-impact alerts\n\n"
                f"💡 For personal alerts use /alert, for market overview use /plan BTC or /signal BTC",
                parse_mode="HTML", disable_web_page_preview=True
            )
            return

    # FIX: detect_market_intent is now slash-only, so normal text never
    # reaches the MTF signal pipeline. (Slash commands are handled by their
    # own CommandHandlers; this branch stays for safety.)
    is_market, symbol, timeframe = detect_market_intent(text)
    if is_market:
        logger.info(f"Market intent detected: '{text}' -> {symbol} (voice={is_voice_transcription})")
        status_msg = await update.message.reply_text(
            f"👑 <b>KING ZARRY AI</b>\n\n📡 Multi-timeframe analysis 4H→1H→15M→5M...\n📊 {symbol}\n📰 Checking news & events...",
            parse_mode="HTML"
        )
        try:
            mtf_data = await asyncio.to_thread(analyze_multi_timeframe, symbol)
            news_data = await asyncio.to_thread(news_engine.get_news_for_asset, symbol)
            mtf_data = await asyncio.to_thread(ai_confirm_signal_mtf, mtf_data, news_data)
            try:
                memory_instance.save_trading_preferences(user_id, preferred_assets=symbol)
            except:
                pass
            await send_long_message(update.message, format_signal_mtf(mtf_data, news_data), is_raw_html=True)
            try:
                chart = await asyncio.to_thread(build_signal_chart, mtf_data)
                sig = mtf_data.get("mtf_signal", mtf_data["15m"]["signal"])
                sig_icon = ("🟢" if sig == "BUY" else "🔴" if sig == "SELL" else "⏳")
                caption = (f"👑 KING ZARRY AI\n{sig_icon} {sig} • {symbol} • 15M MTF {mtf_data.get('mtf_bias','')}\nEntry: {mtf_data['15m']['entry_zone_low']:,.2f} - {mtf_data['15m']['entry_zone_high']:,.2f}\nSL: {mtf_data['15m']['stop_loss']:,.2f}\nTP3: {mtf_data['15m']['tp3']:,.2f}\nNews: {news_data.get('risk','LOW')} risk") if sig != "WAIT" else (f"👑 KING ZARRY AI\n⏳ WAIT / NO TRADE • {symbol} • 15M MTF")
                await update.message.reply_photo(photo=chart, caption=caption)
            except Exception as chart_error:
                logger.warning(f"Chart error in pipeline: {chart_error}")
            try:
                await status_msg.delete()
            except Exception:
                pass
            return
        except Exception as market_error:
            logger.warning(f"Market routing failed for '{text}': {market_error}, falling back to AI")
            try:
                await status_msg.delete()
            except:
                pass

    answer = await asyncio.to_thread(ai_engine.ask, user_id, text, None)
    await send_ai_response(update.message, answer)
    lower = text.lower()
    should_voice_reply = is_voice_transcription or any(k in lower for k in ["voice note", "send voice", "can you speak", "say it in voice", "talk to me"])
    if should_voice_reply:
        try:
            await update.message.chat.send_action("record_voice")
            voice_io = await create_voice_note_file(answer[:800])
            await update.message.reply_voice(voice=voice_io, caption="👑 King Zarry AI Voice")
        except Exception as ve:
            logger.warning(f"Voice follow-up failed: {ve}")

async def handle_text(update, context):

    try:
        if await _fiverr_continue_task(update, context, update.message.text.strip()):
            return
    except Exception as fiverr_err:
        logger.warning("Fiverr Agent continuation failed: %s", fiverr_err)

    if not update.message or not update.message.text:
        return
    if update.message.text.startswith("/"):
        return
    await update.message.chat.send_action("typing")
    try:
        await _process_telegram_text_pipeline(update, context, update.message.text.strip(), is_voice_transcription=False)
    except Exception as error:
        logger.error(f"Chat Error: {error}")
        await update.message.reply_text("⚠️ AI Service Temporarily Unavailable. Please try again shortly.", disable_web_page_preview=True)

MAX_VOICE_SIZE = 10 * 1024 * 1024

async def handle_voice(update, context):
    if not update.message:
        return
    if not await require_subscription(update):
        return
    telegram_file = None
    file_name = "voice.ogg"
    is_voice = False
    if update.message.voice:
        telegram_file = update.message.voice
        file_name = f"{telegram_file.file_id}.ogg"
        is_voice = True
        logger.info(f"🎙️ Telegram voice received: file_id={telegram_file.file_id} size={telegram_file.file_size} duration={telegram_file.duration}s")
        if telegram_file.file_size and telegram_file.file_size > MAX_VOICE_SIZE:
            await update.message.reply_text("❌ Voice message too large. Please send a shorter voice note (max 10 MB).")
            return
    elif update.message.audio:
        telegram_file = update.message.audio
        file_name = telegram_file.file_name or f"{telegram_file.file_id}.mp3"
        logger.info(f"🎵 Telegram audio received: {file_name} size={telegram_file.file_size}")
        if telegram_file.file_size and telegram_file.file_size > MAX_VOICE_SIZE:
            await update.message.reply_text("❌ Audio file too large (max 10 MB).")
            return
    else:
        logger.warning("handle_voice called without voice/audio")
        return
    if stt_engine is None:
        logger.error("STT engine not loaded - cannot transcribe voice")
        await update.message.reply_text("🎙️ Voice transcription service is currently unavailable. Please type your request instead. (STT engine not loaded)")
        return
    try:
        status = stt_engine.provider_status()
        if not status.get("has_key"):
            logger.error(f"STT has no key: {status}")
            await update.message.reply_text("🎙️ Voice transcription API key is not configured. Please type your request.")
            return
    except Exception as e:
        logger.warning(f"STT status check failed: {e}")
    await update.message.chat.send_action("typing")
    temp_dir = None
    temp_path = None
    try:
        logger.info(f"📥 Downloading Telegram voice: {file_name}")
        try:
            tg_file = await context.bot.get_file(telegram_file.file_id)
            logger.info(f"📥 Got Telegram file path: {tg_file.file_path}")
        except Exception as e:
            logger.error(f"A. Telegram get_file failed: {e}")
            await update.message.reply_text("🎙️ I couldn't download that voice message (Telegram file error). Please try again or type your request.")
            return
        temp_dir = tempfile.mkdtemp(prefix="kingzarry_voice_")
        temp_path = os.path.join(temp_dir, file_name)
        try:
            await tg_file.download_to_drive(custom_path=temp_path)
            downloaded_size = os.path.getsize(temp_path) if os.path.exists(temp_path) else 0
            logger.info(f"📥 Telegram voice downloaded: {downloaded_size} bytes to {temp_path}")
        except Exception as e:
            logger.error(f"A. Telegram download_to_drive failed: {e}")
            await update.message.reply_text("🎙️ I couldn't download that voice message (download failed). Please try again.")
            return
        if not os.path.exists(temp_path):
            logger.error("B. Downloaded file does not exist after download")
            await update.message.reply_text("🎙️ Downloaded voice file is missing. Please try again.")
            return
        file_size = os.path.getsize(temp_path)
        if file_size < 100:
            logger.warning(f"B. Voice file too small/invalid: {file_size} bytes")
            await update.message.reply_text("🎙️ Voice message appears empty or too short. Please speak for at least 1 second and try again.")
            return
        if file_size > MAX_VOICE_SIZE:
            logger.warning(f"B. Voice file exceeds limit after download: {file_size}")
            await update.message.reply_text("❌ Voice message too large after download.")
            return
        await update.message.chat.send_action("typing")
        logger.info(f"🎙️ Sending audio to OpenRouter-first STT: {file_name} {file_size} bytes")
        try:
            transcription = await asyncio.to_thread(stt_engine.transcribe_file, temp_path, file_name)
        except Exception as e:
            logger.error(f"C. STT provider exception: {e}")
            await update.message.reply_text("🎙️ Voice transcription service failed (provider error). Please try again or type your request.")
            return
        if not transcription or not transcription.strip():
            logger.warning(f"D. STT returned empty transcription for {file_name} size={file_size}")
            await update.message.reply_text("🎙️ I heard your voice but couldn't understand the words. Please speak clearly in English or type your request.")
            return
        transcription = transcription.strip()
        logger.info(f"✅ STT transcription received: {len(transcription)} chars, routing to pipeline")
        preview = transcription[:500]
        await update.message.reply_text(f"🎙️ I heard: {preview}", parse_mode=None)
        logger.info(f"🔄 Routing transcription through existing message pipeline: {transcription[:60]}...")
        try:
            await _process_telegram_text_pipeline(update, context, transcription, is_voice_transcription=True)
            logger.info(f"✅ Voice transcription successfully routed to normal pipeline")
        except Exception as e:
            logger.error(f"E. AI processing failure after transcription: {e}")
            await update.message.reply_text("⚠️ I understood your voice but failed to process the request. Please try typing it.")
    except Exception as e:
        logger.error(f"Voice handler unexpected error: {e}")
        await update.message.reply_text("🎙️ An unexpected error occurred with voice processing. Please type your request.", disable_web_page_preview=True)
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"🧹 Cleaned temp voice file: {temp_path}")
        except Exception:
            pass
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

def start_discord_if_configured():
    if os.path.exists("discord_bot.py"):
        logger.info("ℹ️ discord_bot.py detected - skipping inline Discord in bot.py (avoids token conflict)")
        return None
    if not DISCORD_BOT_TOKEN:
        return None
    try:
        import discord
        from discord.ext import commands
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            logger.info(f"💬 Discord bot online as {bot.user}")

        @bot.event
        async def on_message(message):
            if message.author == bot.user:
                return
            if message.content.startswith("!ask") or bot.user.mentioned_in(message):
                prompt = message.content.replace(f"<@{bot.user.id}>", "").replace("!ask", "").strip() or "Hello"
                try:
                    reply = await asyncio.to_thread(ai_engine.ask, str(message.author.id), prompt, None)
                    await message.channel.send(reply[:1900])
                except Exception as e:
                    logger.error(f"Discord AI error: {e}")
                    await message.channel.send("⚠️ AI temporarily unavailable.")
            await bot.process_commands(message)

        logger.info("💬 Discord inline integration configured")
        return bot
    except Exception as e:
        logger.warning(f"Discord import failed: {e}")
        return None

def main():
    print("🔵 MAIN: entered main()", flush=True)

    if not TELEGRAM_BOT_TOKEN:
        print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN is not configured.", flush=True)
        return

    if not _telegram_token_ok:
        print("❌ CRITICAL ERROR: Telegram token check failed earlier.", flush=True)
        return

    print("👑 KING ZARRY AI Starting - UPGRADED MTF + NEWS + AGNES MEDIA EDITION...", flush=True)
    print(f"📦 Database: {DATABASE_PATH}", flush=True)
    print(f"🧠 Memory DB: {MEMORY_DB_PATH}", flush=True)
    print(f"🤖 AI Provider: {AI_PROVIDER} (OpenRouter → Groq → Gemini)", flush=True)
    print(f"🔑 OPENROUTER: {'Yes' if OPENROUTER_API_KEY else 'No'} | GROQ: {'Yes' if GROQ_API_KEY else 'No'} | GEMINI: {'Yes' if GEMINI_API_KEY else 'No'}", flush=True)
    print(f"✅ AI Engine: {'Loaded' if ai_engine else 'FAILED'}", flush=True)
    print(f"✅ Memory: {'Loaded' if memory_instance else 'FAILED'}", flush=True)
    print(f"📰 News Engine: Loaded", flush=True)
    print(f"💳 Plans: Monthly {MONTHLY_STARS} Stars / 3Month {THREE_MONTH_STARS} Stars / Yearly {YEARLY_STARS} Stars", flush=True)
    print(f"👮 Admins: {ADMIN_IDS if ADMIN_IDS else 'None configured'}", flush=True)
    print(f"📊 Primary TF: {PRIMARY_EXECUTION_TF} | Architecture: 4H→1H→15M→5M", flush=True)

    print("🔵 MAIN: building Application...", flush=True)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    print("🔵 MAIN: Application built OK", flush=True)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("monthly", monthly_command))
    application.add_handler(CommandHandler("3month", three_month_command))
    application.add_handler(CommandHandler("yearly", yearly_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("agentscan", agentscan_command))
    application.add_handler(CommandHandler("agent", agentscan_command))
    application.add_handler(CommandHandler("intel", intelligence_command))
    application.add_handler(CommandHandler("intelligence", intelligence_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("paysupport", paysupport_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("subscribers", subscribers_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))
    application.add_handler(CommandHandler("notify", notify_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    application.add_handler(CommandHandler("cancelnotify", cancelnotify_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("tts", tts_command))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("eth", eth_command))
    application.add_handler(CommandHandler("sol", sol_command))
    application.add_handler(CommandHandler("xau", xau_command))
    application.add_handler(CommandHandler("plan", plan_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("events", events_command))
    application.add_handler(CommandHandler("alert", alert_command))
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CommandHandler("cancelalert", cancelalert_command))

    application.add_handler(CommandHandler("fiverr", fiverr_command))
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    print("🔵 MAIN: all handlers registered", flush=True)

    try:
        if application.job_queue:
            application.job_queue.run_repeating(notification_job, interval=60, first=60)
            if AGENT_SIGNAL_WATCH:
                application.job_queue.run_repeating(
                    agent_signal_watch_job,
                    interval=AGENT_SIGNAL_INTERVAL_SEC,
                    first=30,
                )
            # Daily morning brief: one fresh scan, then DM active Telegram VIP users.
            # Defaults to 08:00 Africa/Lagos. Disable with AGENT_MORNING_BRIEF=false.
            if clean_env_str(os.getenv("AGENT_MORNING_BRIEF"), "true").lower() in ("1", "true", "yes", "on"):
                try:
                    morning_hour = max(0, min(23, env_int("AGENT_MORNING_BRIEF_HOUR", 8)))
                    morning_minute = max(0, min(59, env_int("AGENT_MORNING_BRIEF_MINUTE", 0)))
                    morning_tz_name = clean_env_str(os.getenv("AGENT_MORNING_BRIEF_TIMEZONE"), "Africa/Lagos")
                    morning_tz = ZoneInfo(morning_tz_name)
                    application.job_queue.run_daily(
                        agent_morning_brief_job,
                        time=dt_time(
                            hour=morning_hour,
                            minute=morning_minute,
                            tzinfo=morning_tz,
                        ),
                        name="king-zarry-agent-morning-brief",
                    )
                    logger.info(
                        "🌅 Agent morning brief scheduled daily at %02d:%02d %s",
                        morning_hour,
                        morning_minute,
                        morning_tz_name,
                    )
                except Exception as e:
                    logger.warning("Agent morning brief scheduler unavailable: %s", e)
                logger.info(
                    f"🤖 Agent signal watch every {AGENT_SIGNAL_INTERVAL_SEC}s → audience={AGENT_SIGNAL_AUDIENCE}"
                )
                # One-shot: tell admin agent is auto-watching (no user ask needed)
                async def _agent_boot_ping(context: ContextTypes.DEFAULT_TYPE):
                    if not ADMIN_IDS:
                        logger.warning("agent boot ping: ADMIN_IDS empty — cannot DM")
                        return
                    text = chr(10).join([
                        "🤖 <b>KING ZARRY AGENT ONLINE</b>",
                        "",
                        "Auto-watching: BTC · ETH · SOL · XAU · UNI",
                        f"Scan every <b>{AGENT_SIGNAL_INTERVAL_SEC}s</b>",
                        f"Audience: <b>{html.escape(str(AGENT_SIGNAL_AUDIENCE))}</b>",
                        "",
                        "I will message you automatically when a non-late <b>BUY</b> or <b>SELL</b> appears.",
                        "No need to ask. Quiet = market is WAIT or late.",
                        "",
                        "<i>Not financial advice.</i>",
                    ])
                    for uid in ADMIN_IDS:
                        try:
                            await context.bot.send_message(
                                chat_id=uid,
                                text=text,
                                parse_mode="HTML",
                                disable_web_page_preview=True,
                            )
                            logger.info(f"agent boot ping sent to {uid}")
                        except Exception as e:
                            logger.warning(f"agent boot ping failed {uid}: {e}")
                application.job_queue.run_once(_agent_boot_ping, when=15)
            else:
                logger.info("🤖 Agent signal watch disabled (set AGENT_SIGNAL_WATCH=true to enable)")
            print("🔔 Notification job scheduled every 60s", flush=True)
        else:
            print("⚠️ JobQueue not available - add python-telegram-bot[job-queue] to requirements.txt", flush=True)
    except Exception as e:
        logger.warning(f"JobQueue not available: {e}")

    discord_bot = start_discord_if_configured()
    if discord_bot and DISCORD_BOT_TOKEN:
        import threading
        def run_discord():
            try:
                discord_bot.run(DISCORD_BOT_TOKEN)
            except Exception as e:
                logger.error(f"Discord bot crashed: {e}")
        threading.Thread(target=run_discord, daemon=True).start()
        print("💬 Discord bot thread started (inline)", flush=True)

    print("🔵 MAIN: about to call run_polling() — Telegram should now be LIVE", flush=True)
    print("👑 King Zarry AI Telegram Bot is online - MTF + News + Late Entry + Exhaustion + Planner + Agnes Media", flush=True)

    try:
        application.run_polling(drop_pending_updates=True, allowed_updates=["message", "pre_checkout_query"])
    except Conflict as e:
        print(f"❌ Telegram polling conflict: {type(e).__name__}: {e}", flush=True)
        print("🛑 Exiting with conflict code 2 so launcher will NOT restart a duplicate Telegram poller.", flush=True)
        raise SystemExit(2)
    except Exception as e:
        print(f"❌ run_polling() crashed: {type(e).__name__}: {e}", flush=True)
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ FATAL: main() crashed with {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)