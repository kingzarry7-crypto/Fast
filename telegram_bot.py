import os
import re
import html
import asyncio
import base64
import sqlite3
import tempfile
import subprocess
import shutil
from io import BytesIO
from datetime import datetime, timezone, timedelta

import requests

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

from telegram import Update, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    filters,
)

# ============================================================
# 👑 KING ZARRY AI
# SINGLE-FILE TELEGRAM BOT
# ============================================================

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

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

TELEGRAM_BOT_TOKEN = clean_env_str(os.getenv("TELEGRAM_BOT_TOKEN"))

XAI_API_KEY = clean_env_str(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
XAI_BASE_URL = clean_env_str(os.getenv("XAI_BASE_URL"), "https://api.x.ai/v1")
XAI_MODEL = clean_env_str(os.getenv("XAI_MODEL") or os.getenv("GROK_MODEL"), "grok-4")

GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
GROQ_BASE_URL = clean_env_str(os.getenv("GROQ_BASE_URL"), "https://api.groq.com/openai/v1")
GROQ_MODEL = clean_env_str(os.getenv("GROQ_MODEL"), "llama-3.3-70b-versatile")

OPENAI_API_KEY = clean_env_str(os.getenv("OPENAI_API_KEY"))
OPENAI_BASE_URL = clean_env_str(os.getenv("OPENAI_BASE_URL"), "https://api.openai.com/v1")
OPENAI_MODEL = clean_env_str(os.getenv("OPENAI_MODEL"), "gpt-4o-mini")

GEMINI_API_KEY = clean_env_str(os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = clean_env_str(os.getenv("GEMINI_MODEL"), "gemini-2.5-flash")

TWELVE_DATA_API_KEY = clean_env_str(os.getenv("TWELVE_DATA_API_KEY"))
TWELVE_DATA_URL = "https://api.twelvedata.com"

AI_PROVIDER = clean_env_str(os.getenv("AI_PROVIDER"), "AUTO").upper()

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

# ============================================================
# TELEGRAM STARS PLANS
# ============================================================

MONTHLY_STARS = env_int("MONTHLY_STARS", 150)
THREE_MONTH_STARS = env_int("THREE_MONTH_STARS", 500)
YEARLY_STARS = env_int("YEARLY_STARS", 2500)

SUBSCRIPTION_PLANS = {
    "monthly": {
        "name": "👑 Monthly VIP",
        "days": 30,
        "stars": MONTHLY_STARS,
        "description": "30 days King Zarry AI VIP access",
    },
    "3month": {
        "name": "🔥 3-Month VIP",
        "days": 90,
        "stars": THREE_MONTH_STARS,
        "description": "90 days King Zarry AI VIP access",
    },
    "yearly": {
        "name": "💎 Yearly VIP",
        "days": 365,
        "stars": YEARLY_STARS,
        "description": "365 days King Zarry AI VIP access",
    },
}

# ============================================================
# OPTIONAL GEMINI SDK
# ============================================================

try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False

DEFAULT_TIMEFRAME = "15min"

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are an advanced AI assistant specializing in:
- General questions
- Programming
- Technology
- Business
- Trading education
- BTC
- ETH
- SOL
- Forex
- Gold/XAUUSD
- Technical analysis
- Chart analysis
- Image analysis
- Creative tasks

Rules:
1. Never reveal private chain-of-thought or hidden reasoning.
2. Never output <think> blocks or control tokens.
3. Answer directly.
4. Never invent live market prices.
5. Trading analysis is probabilistic and never guarantees profit.
6. Use supplied market data when discussing current prices.
7. Explain important risk when appropriate.
"""

# ============================================================
# STRING HELPERS
# ============================================================

def clean_ai_response(text):
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()

def escape_html(text):
    if not text:
        return ""
    text = html.escape(text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
    return text

async def send_long_message(message, text, is_raw_html=False):
    text = clean_ai_response(text)
    if not text:
        text = "King Zarry AI returned an empty response."

    formatted = text if is_raw_html else escape_html(text)
    chunk_size = 3800
    chunks = [formatted[i:i + chunk_size] for i in range(0, len(formatted), chunk_size)]

    for chunk in chunks:
        try:
            await message.reply_text(chunk, parse_mode="HTML")
        except Exception:
            await message.reply_text(re.sub(r"<[^>]+>", "", chunk), parse_mode=None)

# ============================================================
# SQLITE DATABASE
# ============================================================

def db_connect():
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection

def init_database():
    connection = db_connect()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT,
            expires_at TEXT,
            payment_method TEXT,
            payment_id TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            plan TEXT,
            payment_method TEXT,
            payment_id TEXT UNIQUE,
            amount INTEGER,
            currency TEXT,
            payload TEXT,
            created_at TEXT
        )
    """)
    connection.commit()
    connection.close()

init_database()

def is_subscribed(user_id):
    if user_id in ADMIN_IDS:
        return True
    connection = db_connect()
    row = connection.execute("SELECT expires_at FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
    connection.close()
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
    connection = db_connect()
    row = connection.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)).fetchone()
    connection.close()
    return dict(row) if row else None

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
    connection = db_connect()
    connection.execute(
        """
        INSERT INTO subscriptions (user_id, username, plan, expires_at, payment_method, payment_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            plan=excluded.plan,
            expires_at=excluded.expires_at,
            payment_method=excluded.payment_method,
            payment_id=excluded.payment_id
        """,
        (user_id, username, plan, expires_at.isoformat(), payment_method, payment_id, now.isoformat())
    )
    connection.commit()
    connection.close()
    return expires_at

def deactivate_subscription(user_id):
    connection = db_connect()
    connection.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
    connection.commit()
    connection.close()

def record_payment(user_id, username, plan, payment_method, payment_id, amount, currency, payload):
    connection = db_connect()
    try:
        connection.execute(
            """
            INSERT INTO payments (user_id, username, plan, payment_method, payment_id, amount, currency, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, plan, payment_method, payment_id, amount, currency, payload, datetime.now(timezone.utc).isoformat())
        )
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()

def get_payment_history(user_id, limit=10):
    connection = db_connect()
    rows = connection.execute(
        "SELECT plan, payment_method, amount, currency, created_at FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    connection.close()
    return rows

def user_has_access(user_id):
    return user_id in ADMIN_IDS or is_subscribed(user_id)

async def require_subscription(update):
    user = update.effective_user
    if not user:
        return False
    if user_has_access(user.id):
        return True

    if update.message:
        await update.message.reply_text(
            "🔒 <b>KING ZARRY AI VIP</b>\n\n"
            "Your VIP access is not active.\n\n"
            "👑 VIP unlocks:\n"
            "• AI Chat\n"
            "• 15m Trading Signals\n"
            "• BTC / ETH / SOL\n"
            "• Gold/XAUUSD\n"
            "• AI Vision\n"
            "• Chart analysis\n"
            "• TTS\n\n"
            "Use /buy to activate VIP.",
            parse_mode="HTML"
        )
    return False

# ============================================================
# AI PROVIDERS
# ============================================================

def openai_compatible_request(messages, api_key, base_url, model):
    if not api_key:
        raise RuntimeError("API key is missing.")

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2500,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        raise RuntimeError(f"API Error {response.status_code}: {error_data}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            parts = [item["text"] for item in content if isinstance(item, dict) and item.get("text")]
            content = "\n".join(parts)
        return clean_ai_response(str(content))
    except Exception:
        raise RuntimeError(f"Invalid AI response: {data}")

def gemini_request(prompt, image_bytes=None, mime_type=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key missing.")
    if not GEMINI_SDK_AVAILABLE:
        raise RuntimeError("Gemini SDK is not installed.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    if image_bytes:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        contents = [f"{SYSTEM_PROMPT}\n\nUSER TASK:\n{prompt}", image_part]
    else:
        contents = [f"{SYSTEM_PROMPT}\n\nUSER:\n{prompt}"]

    models = [GEMINI_MODEL, "gemini-2.5-flash", "gemini-2.0-flash"]
    last_error = None

    for model in dict.fromkeys(models):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2500
                )
            )
            text = getattr(response, "text", None)
            if text:
                return clean_ai_response(text)
        except Exception as error:
            last_error = error

    raise RuntimeError(f"Gemini failed: {last_error}")

def ask_ai(prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    if AI_PROVIDER == "XAI":
        return openai_compatible_request(messages, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL)
    if AI_PROVIDER == "GROQ":
        return openai_compatible_request(messages, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL)
    if AI_PROVIDER == "OPENAI":
        return openai_compatible_request(messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
    if AI_PROVIDER == "GEMINI":
        return gemini_request(prompt)

    errors = []
    providers = [
        ("xAI", XAI_API_KEY, XAI_BASE_URL, XAI_MODEL),
        ("Groq", GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL),
        ("OpenAI", OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
    ]

    for name, key, base_url, model in providers:
        if not key:
            continue
        try:
            return openai_compatible_request(messages, key, base_url, model)
        except Exception as error:
            errors.append(f"{name}: {error}")

    if GEMINI_API_KEY:
        try:
            return gemini_request(prompt)
        except Exception as error:
            errors.append(f"Gemini: {error}")

    raise RuntimeError("All configured AI providers failed.\n" + "\n".join(errors))

def analyze_image_with_ai(image_bytes, mime_type, prompt):
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    vision_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}
            ]
        }
    ]

    errors = []
    if XAI_API_KEY:
        try:
            return openai_compatible_request(vision_messages, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL)
        except Exception as error:
            errors.append(f"xAI Vision: {error}")

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(vision_messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
        except Exception as error:
            errors.append(f"OpenAI Vision: {error}")

    if GEMINI_API_KEY:
        try:
            return gemini_request(prompt, image_bytes, mime_type)
        except Exception as error:
            errors.append(f"Gemini Vision: {error}")

    raise RuntimeError("All vision providers failed.\n" + "\n".join(errors))

# ============================================================
# INDICATORS & ENGINE
# ============================================================

def get_market_candles(symbol, interval=DEFAULT_TIMEFRAME, outputsize=150):
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured.")

    response = requests.get(
        f"{TWELVE_DATA_URL}/time_series",
        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Twelve Data error."))

    values = data.get("values", [])
    if len(values) < 60:
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
    gains = [max(values[i] - values[i - 1], 0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0) for i in range(1, len(values))]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    if len(closes) < 2:
        return 0.0
    ranges = [
        max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        for i in range(1, len(closes))
    ]
    if len(ranges) < period:
        return sum(ranges) / len(ranges)
    return sum(ranges[-period:]) / period

def find_swing_levels(highs, lows, lookback=40):
    lookback = min(lookback, len(highs))
    return min(lows[-lookback:]), max(highs[-lookback:])

def detect_structure(highs, lows, closes):
    if len(closes) < 20:
        return "NEUTRAL"
    first, second = closes[-20:-10], closes[-10:]
    if max(second) > max(first) and min(second) > min(first):
        return "BULLISH"
    if max(second) < max(first) and min(second) < min(first):
        return "BEARISH"
    return "NEUTRAL"

def candle_momentum(opens, closes, count=5):
    opens, closes = opens[-count:], closes[-count:]
    bullish = sum(1 for o, c in zip(opens, closes) if c > o)
    bearish = sum(1 for o, c in zip(opens, closes) if c < o)
    return bullish, bearish

def analyze_market(closes, highs, lows, opens, symbol):
    price = closes[-1]
    ema9, ema21, ema50 = ema(closes, 9), ema(closes, 21), ema(closes, 50)
    current_rsi, previous_rsi = rsi(closes, 14), rsi(closes[:-1], 14)
    current_atr = atr(highs, lows, closes, 14)
    support, resistance = find_swing_levels(highs, lows, 40)
    structure = detect_structure(highs, lows, closes)

    bullish_score, bearish_score = 0.0, 0.0
    reasons_buy, reasons_sell = [], []

    # 1. EMA
    if ema9 > ema21 > ema50:
        bullish_score += 22
        reasons_buy.append("EMA 9 > EMA 21 > EMA 50")
    elif ema9 > ema21:
        bullish_score += 10
        reasons_buy.append("Short-term EMA bullish")

    if ema9 < ema21 < ema50:
        bearish_score += 22
        reasons_sell.append("EMA 9 < EMA 21 < EMA 50")
    elif ema9 < ema21:
        bearish_score += 10
        reasons_sell.append("Short-term EMA bearish")

    # 2. Location
    if price > ema9:
        bullish_score += 8
        reasons_buy.append("Price above EMA 9")
    else:
        bearish_score += 8
        reasons_sell.append("Price below EMA 9")

    bullish_score += 7 if price > ema21 else 0
    bearish_score += 7 if price <= ema21 else 0
    bullish_score += 8 if price > ema50 else 0
    bearish_score += 8 if price <= ema50 else 0

    # 3. RSI
    rsi_rising = current_rsi > previous_rsi
    if 52 <= current_rsi <= 68:
        bullish_score += 12
        if rsi_rising:
            bullish_score += 5
        reasons_buy.append(f"Healthy bullish RSI {current_rsi:.1f}")
    elif 32 <= current_rsi <= 48:
        bearish_score += 12
        if not rsi_rising:
            bearish_score += 5
        reasons_sell.append(f"Bearish RSI {current_rsi:.1f}")
    elif current_rsi > 75:
        bearish_score += 12
        reasons_sell.append("RSI overbought")
    elif current_rsi < 25:
        bullish_score += 12
        reasons_buy.append("RSI oversold")

    # 4. Structure
    if structure == "BULLISH":
        bullish_score += 15
        reasons_buy.append("Bullish market structure")
    elif structure == "BEARISH":
        bearish_score += 15
        reasons_sell.append("Bearish market structure")

    # 5. S/R
    if 0 <= (price - support) <= current_atr * 1.25:
        bullish_score += 12
        reasons_buy.append("Price near support")
    if 0 <= (resistance - price) <= current_atr * 1.25:
        bearish_score += 12
        reasons_sell.append("Price near resistance")

    if price > resistance:
        bullish_score += 18
        reasons_buy.append("Resistance breakout")
    if price < support:
        bearish_score += 18
        reasons_sell.append("Support breakdown")

    # 6. Candles
    bullish_candles, bearish_candles = candle_momentum(opens, closes, 5)
    if bullish_candles >= 4:
        bullish_score += 10
        reasons_buy.append("Strong bullish candle momentum")
    elif bearish_candles >= 4:
        bearish_score += 10
        reasons_sell.append("Strong bearish candle momentum")
    elif bullish_candles > bearish_candles:
        bullish_score += 5
    elif bearish_candles > bullish_candles:  # FIXED TYPO HERE
        bearish_score += 5

    # 7. Momentum
    if len(closes) >= 6:
        momentum = closes[-1] - closes[-6]
        if momentum > 0:
            bullish_score += 8
            reasons_buy.append("Positive short-term momentum")
        elif momentum < 0:
            bearish_score += 8
            reasons_sell.append("Negative short-term momentum")

    max_score = 120.0
    bullish_percent = int((min(bullish_score, max_score) / max_score) * 100)
    bearish_percent = int((min(bearish_score, max_score) / max_score) * 100)
    difference = abs(bullish_percent - bearish_percent)

    ema_spread = abs(ema9 - ema21) / price
    is_flat_market = (
        difference < 18
        or (45 <= current_rsi <= 55 and ema_spread < 0.0005)
        or (structure == "NEUTRAL" and difference < 25)
    )

    if is_flat_market:
        signal = "WAIT"
        confidence = "LOW"
        strength = max(bullish_percent, bearish_percent)
        reasons = []
        if difference < 18:
            reasons.append("Market is sideways with conflicting signals")
        if 45 <= current_rsi <= 55:
            reasons.append(f"RSI is neutral ({current_rsi:.1f})")
        if ema_spread < 0.0005:
            reasons.append("EMAs are flat and compressing")
        if structure == "NEUTRAL":
            reasons.append("No clear higher highs or lower lows")
    elif bullish_percent > bearish_percent:
        signal = "BUY"
        strength = bullish_percent
        confidence = "HIGH" if strength >= 75 else "MEDIUM"
        reasons = reasons_buy
    else:
        signal = "SELL"
        strength = bearish_percent
        confidence = "HIGH" if strength >= 75 else "MEDIUM"
        reasons = reasons_sell

    if current_atr <= 0:
        current_atr = price * 0.002

    if signal == "BUY":
        entry_low = max(support, price - current_atr * 0.35)
        entry_high = price
        entry = (entry_low + entry_high) / 2
        stop_loss = min(support - current_atr * 0.25, entry - current_atr * 1.05)
        risk = max(entry - stop_loss, current_atr)
        stop_loss = entry - risk if (entry - stop_loss) <= 0 else stop_loss
        tp1, tp2, tp3 = entry + risk * 1.5, entry + risk * 2.5, entry + risk * 3.5
    elif signal == "SELL":
        entry_low = price
        entry_high = min(resistance, price + current_atr * 0.35)
        entry = (entry_low + entry_high) / 2
        stop_loss = max(resistance + current_atr * 0.25, entry + current_atr * 1.05)
        risk = max(stop_loss - entry, current_atr)
        stop_loss = entry + risk if (stop_loss - entry) <= 0 else stop_loss
        tp1, tp2, tp3 = entry - risk * 1.5, entry - risk * 2.5, entry - risk * 3.5
    else:
        entry_low = entry_high = entry = price
        stop_loss = price - current_atr
        tp1, tp2, tp3 = price + current_atr, price + current_atr * 2, price + current_atr * 3
        risk = current_atr

    return {
        "symbol": symbol,
        "interval": DEFAULT_TIMEFRAME,
        "price": price,
        "signal": signal,
        "trend": "BULLISH" if bullish_percent > bearish_percent else "BEARISH" if bearish_percent > bullish_percent else "NEUTRAL",
        "structure": structure,
        "strength": strength,
        "confidence": confidence,
        "bullish_score": bullish_percent,
        "bearish_score": bearish_percent,
        "score_difference": difference,
        "rsi": current_rsi,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "atr": current_atr,
        "support": support,
        "resistance": resistance,
        "demand_low": support,
        "demand_high": support + current_atr * 0.55,
        "supply_low": resistance - current_atr * 0.55,
        "supply_high": resistance,
        "entry": entry,
        "entry_zone_low": entry_low,
        "entry_zone_high": entry_high,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "risk": risk,
        "rr": 3.5,
        "reasons": reasons[:6],
        "candles": []
    }

def analyze_symbol(symbol, interval=DEFAULT_TIMEFRAME):
    candles = get_market_candles(symbol, interval, 150)
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    opens = [float(c["open"]) for c in candles]

    result = analyze_market(closes, highs, lows, opens, symbol)
    result["candles"] = candles
    return result

def format_signal(data):
    signal = data["signal"]
    emoji, action = ("🟢", "BUY") if signal == "BUY" else ("🔴", "SELL") if signal == "SELL" else ("⚠️", "WAIT / NO TRADE")
    confidence_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "⚠️"}.get(data["confidence"], "⚠️")
    reasons = "\n".join(f"• {reason}" for reason in data["reasons"])

    if signal == "WAIT":
        return (
            f"👑 <b>KING ZARRY AI • {data['symbol']} ANALYSIS</b>\n\n"
            f"{emoji} <b>STATUS: {action}</b>\n"
            f"⏱ Timeframe: <b>15 MINUTES</b>\n\n"
            f"💰 Current price:\n<code>{data['price']:,.2f}</code>\n\n"
            f"📊 BUY score: <b>{data['bullish_score']}/100</b>\n"
            f"📉 SELL score: <b>{data['bearish_score']}/100</b>\n\n"
            f"🏗 Structure: <b>{data['structure']}</b>\n"
            f"📈 Trend: <b>{data['trend']}</b>\n\n"
            f"🧱 Support: <code>{data['support']:,.2f}</code>\n"
            f"🚧 Resistance: <code>{data['resistance']:,.2f}</code>\n"
            f"📊 RSI 14: <code>{data['rsi']:.1f}</code>\n\n"
            f"🛑 <b>Why you should WAIT:</b>\n{reasons}\n\n"
            f"💡 <i>Market is choppy or lacking clear directional momentum. Do not force low-quality trades.</i>"
        )

    return (
        f"👑 <b>KING ZARRY AI • {data['symbol']} SIGNAL</b>\n\n"
        f"{emoji} <b>{action}</b>\n"
        f"⏱ Timeframe: <b>15 MINUTES</b>\n"
        f"{confidence_emoji} Confidence: <b>{data['confidence']}</b>\n"
        f"💪 Strength: <b>{data['strength']}/100</b>\n"
        f"📊 BUY score: <b>{data['bullish_score']}/100</b>\n"
        f"📉 SELL score: <b>{data['bearish_score']}/100</b>\n\n"
        f"💰 Current price:\n<code>{data['price']:,.2f}</code>\n\n"
        f"🎯 <b>ENTRY ZONE</b>\n"
        f"<code>{data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}</code>\n\n"
        f"🛑 Stop Loss:\n<code>{data['stop_loss']:,.2f}</code>\n"
        f"🎯 TP1:\n<code>{data['tp1']:,.2f}</code>\n"
        f"🎯 TP2:\n<code>{data['tp2']:,.2f}</code>\n"
        f"🎯 TP3:\n<code>{data['tp3']:,.2f}</code>\n\n"
        f"⚖️ Risk/Reward:\n<b>1:{data['rr']:.1f}</b>\n\n"
        f"🏗 Structure:\n<b>{data['structure']}</b>\n"
        f"📈 Trend:\n<b>{data['trend']}</b>\n\n"
        f"🧱 Support:\n<code>{data['support']:,.2f}</code>\n"
        f"🚧 Resistance:\n<code>{data['resistance']:,.2f}</code>\n\n"
        f"📊 RSI 14:\n<code>{data['rsi']:.1f}</code>\n"
        f"📏 EMA 9:\n<code>{data['ema9']:,.2f}</code>\n"
        f"📏 EMA 21:\n<code>{data['ema21']:,.2f}</code>\n"
        f"📏 EMA 50:\n<code>{data['ema50']:,.2f}</code>\n"
        f"📐 ATR:\n<code>{data['atr']:,.2f}</code>\n\n"
        f"🧠 <b>Why the engine chose {action}:</b>\n{reasons}\n\n"
        f"⚠️ <i>Algorithmic market analysis. Use appropriate risk management.</i>"
    )

# ============================================================
# CHART GENERATION
# ============================================================

def parse_candle_time(value):
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass
    return datetime.now()

def build_signal_chart(data):
    candles = data["candles"][-70:]
    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    times = [parse_candle_time(c.get("datetime", "")) for c in candles]
    x = list(range(len(candles)))

    fig, ax = plt.subplots(figsize=(14, 8), dpi=140)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    try:
        width = 0.58
        for i in range(len(candles)):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            candle_color = "#16A34A" if c >= o else "#DC2626"
            ax.vlines(i, l, h, linewidth=0.8, color="#555555")
            bottom = min(o, c)
            height = max(abs(c - o), 0.000001)
            ax.add_patch(Rectangle((i - width / 2, bottom), width, height, facecolor=candle_color, edgecolor=candle_color, linewidth=0.5))

        ema21_vals = [ema(closes[:i + 1], 21) if i >= 20 else float("nan") for i in range(len(closes))]
        ema50_vals = [ema(closes[:i + 1], 50) if i >= 49 else float("nan") for i in range(len(closes))]

        ax.plot(x, ema21_vals, linewidth=1.4, label="EMA 21")
        ax.plot(x, ema50_vals, linewidth=1.4, label="EMA 50")

        signal = data["signal"]
        current = data["price"]
        support, resistance = data["support"], data["resistance"]

        if signal in ["BUY", "SELL"]:
            x0 = max(0, len(x) - 18)
            box_width = 18
            entry_low, entry_high = data["entry_zone_low"], data["entry_zone_high"]
            sl, tp1, tp2, tp3 = data["stop_loss"], data["tp1"], data["tp2"], data["tp3"]

            if signal == "BUY":
                ax.add_patch(Rectangle((x0, entry_low), box_width, entry_high - entry_low, alpha=0.25))
                ax.add_patch(Rectangle((x0, sl), box_width, entry_low - sl, alpha=0.20))
                ax.add_patch(Rectangle((x0, entry_high), box_width, tp3 - entry_high, alpha=0.15))
                arrow = FancyArrowPatch((x0 + box_width / 2, entry_high), (x0 + box_width / 2, tp3), arrowstyle="->", mutation_scale=18, linewidth=1.5)
            else:
                ax.add_patch(Rectangle((x0, entry_low), box_width, entry_high - entry_low, alpha=0.25))
                ax.add_patch(Rectangle((x0, entry_high), box_width, sl - entry_high, alpha=0.20))
                ax.add_patch(Rectangle((x0, tp3), box_width, entry_low - tp3, alpha=0.15))
                arrow = FancyArrowPatch((x0 + box_width / 2, entry_low), (x0 + box_width / 2, tp3), arrowstyle="->", mutation_scale=18, linewidth=1.5)

            ax.add_patch(arrow)
            levels = [(entry_low, "ENTRY LOW"), (entry_high, "ENTRY HIGH"), (sl, "STOP LOSS"), (tp1, "TP1"), (tp2, "TP2"), (tp3, "TP3")]
        else:
            levels = [(support, "SUPPORT"), (resistance, "RESISTANCE")]

        for level, label in levels:
            ax.axhline(level, linestyle=":", linewidth=0.7, alpha=0.6)
            ax.text(len(x) + 0.8, level, f"{label} {level:,.2f}", fontsize=8, fontweight="bold")

        ax.axhline(current, linewidth=1, alpha=0.5)
        ax.text(len(x) - 1, current, f" {current:,.2f}", fontsize=9, fontweight="bold")

        title = "🟢 BUY" if signal == "BUY" else "🔴 SELL" if signal == "SELL" else "⚠️ WAIT"
        ax.set_title(f"👑 KING ZARRY AI • {data['symbol']} • 15M • {title}", fontsize=15, fontweight="bold", loc="left", pad=12)

        if times:
            step = max(1, len(times) // 7)
            ticks = list(range(0, len(times), step))
            ax.set_xticks(ticks)
            ax.set_xticklabels([times[i].strftime("%d %b\n%H:%M") for i in ticks], fontsize=8)

        sl = data.get("stop_loss", support)
        tp3 = data.get("tp3", resistance)
        y_low = min(min(lows), sl)
        y_high = max(max(highs), tp3)
        padding = max((y_high - y_low) * 0.08, data["atr"] * 0.8)

        ax.set_ylim(y_low - padding, y_high + padding)
        ax.set_xlim(-1, len(x) + 9)
        ax.grid(True, alpha=0.15, linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(loc="upper left", frameon=False, fontsize=8)

        plt.tight_layout()
        buffer = BytesIO()
        buffer.name = "king_zarry_signal.png"
        fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight", facecolor="white")
        buffer.seek(0)
        return buffer
    finally:
        plt.close(fig)

# ============================================================
# SYMBOL PARSER & TTS
# ============================================================

def detect_market_and_timeframe(text):
    upper = text.upper()
    symbol = "XAU/USD"
    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "XAU", "GOLD"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"]
    }
    for market, names in markets.items():
        if any(name in upper for name in names):
            symbol = market
            break

    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", text.lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe

TIMEFRAME_MAP = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1day"}

def normalize_timeframe(timeframe):
    return TIMEFRAME_MAP.get(timeframe.lower().strip(), DEFAULT_TIMEFRAME)

async def create_voice_note(text):
    if not shutil.which("python"):
        raise RuntimeError("Python executable unavailable.")
    try:
        import edge_tts
    except Exception:
        raise RuntimeError("TTS unavailable. Install edge-tts.")

    temp_dir = tempfile.mkdtemp(prefix="king_zarry_tts_")
    output_file = os.path.join(temp_dir, "voice.mp3")
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_file)  # FIXED ASYNC TTS CALL
    return output_file

# ============================================================
# TELEGRAM HANDLERS
# ============================================================

async def start_command(update, context):
    user = update.effective_user
    active = user and user_has_access(user.id)
    status = "🟢 <b>VIP ACTIVE</b>" if active else "🔴 <b>VIP NOT ACTIVE</b>"

    text = (
        "👑 <b>KING ZARRY AI</b>\n\n"
        "Your AI trading and intelligence assistant is online. 🚀\n\n"
        f"{status}\n\n"
        "🤖 <b>AI</b>\n/ask &lt;question&gt;\n/tts &lt;text&gt;\n\n"
        "📊 <b>15M SIGNALS</b>\n/signal XAU\n/signal BTC\n/signal ETH\n/signal SOL\n\n"
        "⚡ Quick commands:\n/xau\n/btc\n/eth\n/sol\n\n"
        "💎 <b>VIP</b>\n/buy\n/status\n/history\n\n"
        "📸 Send a chart or image for AI Vision."
    )
    await send_long_message(update.message, text, is_raw_html=True)

async def help_command(update, context):
    await start_command(update, context)

async def buy_command(update, context):
    text = (
        "👑 <b>KING ZARRY AI VIP</b>\n\nChoose your plan:\n\n"
        f"🌟 <b>Monthly</b>\n30 days • {MONTHLY_STARS} Stars\n/monthly\n\n"
        f"🔥 <b>3 Months</b>\n90 days • {THREE_MONTH_STARS} Stars\n/3month\n\n"
        f"💎 <b>Yearly</b>\n365 days • {YEARLY_STARS} Stars\n/yearly"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def send_subscription_invoice(update, plan_key):
    if plan_key not in SUBSCRIPTION_PLANS:
        await update.message.reply_text("❌ Invalid plan.")
        return
    plan = SUBSCRIPTION_PLANS[plan_key]
    await update.message.reply_invoice(
        title=plan["name"],
        description=plan["description"],
        payload=f"kingzarry_subscription:{plan_key}",
        currency="XTR",
        prices=[LabeledPrice(plan["name"], plan["stars"])],
        provider_token=""
    )

async def monthly_command(update, context):
    await send_subscription_invoice(update, "monthly")

async def three_month_command(update, context):
    await send_subscription_invoice(update, "3month")

async def yearly_command(update, context):
    await send_subscription_invoice(update, "yearly")

async def precheckout_handler(update, context):
    query = update.pre_checkout_query
    payload = query.invoice_payload

    if not payload.startswith("kingzarry_subscription:"):
        await query.answer(ok=False, error_message="Invalid subscription.")
        return

    plan_key = payload.split(":", 1)[1]
    if plan_key not in SUBSCRIPTION_PLANS:
        await query.answer(ok=False, error_message="Plan unavailable.")
        return

    plan = SUBSCRIPTION_PLANS[plan_key]
    if query.currency != "XTR" or query.total_amount != plan["stars"]:
        await query.answer(ok=False, error_message="Payment validation failed.")
        return

    await query.answer(ok=True)

async def successful_payment_handler(update, context):
    message, user = update.message, update.effective_user
    payment = message.successful_payment if message else None
    if not payment or not user:
        return

    payload = payment.invoice_payload
    if not payload.startswith("kingzarry_subscription:"):
        return

    plan_key = payload.split(":", 1)[1]
    if plan_key not in SUBSCRIPTION_PLANS:
        await message.reply_text("⚠️ Payment received, but plan identification failed.")
        return

    plan = SUBSCRIPTION_PLANS[plan_key]
    username = user.username or user.full_name or str(user.id)
    payment_id = payment.telegram_payment_charge_id

    if not record_payment(user.id, username, plan_key, "telegram_stars", payment_id, payment.total_amount, payment.currency, payload):
        await message.reply_text("⚠️ This payment has already been processed.")
        return

    expires_at = activate_subscription(user.id, username, plan["days"], plan_key, "telegram_stars", payment_id)
    await message.reply_text(
        f"🎉 <b>PAYMENT SUCCESSFUL!</b>\n\n👑 Welcome to <b>KING ZARRY AI VIP</b>!\n\n"
        f"📦 Plan: <b>{plan['name']}</b>\n⭐ Paid: <b>{payment.total_amount} Stars</b>\n\n"
        f"📅 Expires:\n<code>{expires_at.strftime('%Y-%m-%d %H:%M UTC')}</code>",
        parse_mode="HTML"
    )

async def status_command(update, context):
    user = update.effective_user
    if not user:
        return
    if user.id in ADMIN_IDS:
        await update.message.reply_text("👑 <b>KING ZARRY ADMIN</b>\n\n🟢 Unlimited access.", parse_mode="HTML")
        return

    subscription = get_subscription(user.id)
    if not subscription or not is_subscribed(user.id):
        await update.message.reply_text("🔴 <b>NO ACTIVE VIP</b>\n\nUse /buy to subscribe.", parse_mode="HTML")
        return

    await update.message.reply_text(
        f"🟢 <b>VIP ACTIVE</b>\n\n👑 Plan: <b>{subscription['plan']}</b>\n📅 Expires:\n<code>{subscription['expires_at']}</code>",
        parse_mode="HTML"
    )

async def history_command(update, context):
    user = update.effective_user
    if not user:
        return
    history = get_payment_history(user.id, 10)
    if not history:
        await update.message.reply_text("💳 No payment history.")
        return

    lines = ["💳 <b>KING ZARRY PAYMENT HISTORY</b>\n"]
    for row in history:
        lines.append(f"• <b>{html.escape(row['plan'])}</b>\n  {html.escape(row['payment_method'])}\n  {row['amount']} {html.escape(row['currency'])}\n  {html.escape(row['created_at'])}\n")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def grant_command(update, context):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage:\n/grant USER_ID DAYS")
        return

    try:
        target_id, days = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ USER_ID and DAYS must be numbers.")
        return

    expiry = activate_subscription(target_id, "admin_granted", days, "admin", "admin", None)
    await update.message.reply_text(f"✅ <b>VIP GRANTED</b>\n\n👤 User: <code>{target_id}</code>\n📅 Days: <b>{days}</b>\n⏰ Expires:\n<code>{expiry}</code>", parse_mode="HTML")

async def revoke_command(update, context):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage:\n/revoke USER_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid USER_ID.")
        return

    deactivate_subscription(target_id)
    await update.message.reply_text(f"🚫 <b>VIP REVOKED</b>\n\nUser: <code>{target_id}</code>", parse_mode="HTML")

async def ask_command(update, context):
    if not await require_subscription(update):
        return
    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("Usage:\n/ask What is Bitcoin?")
        return

    await update.message.chat.send_action("typing")
    try:
        answer = await asyncio.to_thread(ask_ai, question)
        await send_long_message(update.message, answer)
    except Exception as error:
        await update.message.reply_text(f"❌ AI Error:\n{error}")

async def tts_command(update, context):
    if not await require_subscription(update):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("Usage:\n/tts Hello from King Zarry AI!")
        return

    await update.message.chat.send_action("record_voice")
    voice_file = None
    try:
        voice_file = await create_voice_note(text)
        with open(voice_file, "rb") as voice:
            await update.message.reply_voice(voice=voice, caption="👑 King Zarry AI")
    except Exception as error:
        await update.message.reply_text(f"❌ TTS Error:\n{error}")
    finally:
        if voice_file:
            shutil.rmtree(os.path.dirname(voice_file), ignore_errors=True)

async def quick_symbol_command(symbol, update, context):
    if not await require_subscription(update):
        return
    await update.message.chat.send_action("typing")
    status = await update.message.reply_text("👑 <b>KING ZARRY AI</b>\n\n📡 Reading live market data...", parse_mode="HTML")

    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, DEFAULT_TIMEFRAME)
        await send_long_message(update.message, format_signal(data), is_raw_html=True)

        try:
            chart = await asyncio.to_thread(build_signal_chart, data)
            sig_icon = "🟢" if data["signal"] == "BUY" else "🔴" if data["signal"] == "SELL" else "⚠️"
            caption = (
                f"👑 KING ZARRY AI\n{sig_icon} {data['signal']} • {data['symbol']} • 15M\n"
                f"Entry: {data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}\n"
                f"SL: {data['stop_loss']:,.2f}\nTP3: {data['tp3']:,.2f}"
            ) if data["signal"] != "WAIT" else f"👑 KING ZARRY AI\n⚠️ WAIT / NO TRADE • {data['symbol']} • 15M"

            await update.message.reply_photo(photo=chart, caption=caption)
        except Exception as chart_error:
            print("⚠️ Chart error:", chart_error)

        try:
            await status.delete()
        except Exception:
            pass
    except Exception as error:
        try:
            await status.edit_text(f"❌ <b>Signal Error</b>\n\n{html.escape(str(error))}", parse_mode="HTML")
        except Exception:
            await update.message.reply_text(f"❌ Signal Error:\n{error}")

async def btc_command(update, context):
    await quick_symbol_command("BTC/USD", update, context)

async def eth_command(update, context):
    await quick_symbol_command("ETH/USD", update, context)

async def sol_command(update, context):
    await quick_symbol_command("SOL/USD", update, context)

async def xau_command(update, context):
    await quick_symbol_command("XAU/USD", update, context)

async def signal_command(update, context):
    if not await require_subscription(update):
        return
    raw = " ".join(context.args).strip()
    symbol, timeframe = detect_market_and_timeframe(raw or "XAUUSD")
    interval = normalize_timeframe(timeframe)

    status = await update.message.reply_text(
        f"👑 <b>KING ZARRY AI</b>\n\n📡 Scanning live market data...\n📊 {symbol}\n⏱ {interval}",
        parse_mode="HTML"
    )

    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, interval)
        await send_long_message(update.message, format_signal(data), is_raw_html=True)

        try:
            chart = await asyncio.to_thread(build_signal_chart, data)
            sig_icon = "🟢" if data["signal"] == "BUY" else "🔴" if data["signal"] == "SELL" else "⚠️"
            caption = (
                f"👑 KING ZARRY AI\n{sig_icon} {data['signal']} • {data['symbol']} • {data['interval']}\n"
                f"Entry: {data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}\n"
                f"SL: {data['stop_loss']:,.2f}\nTP3: {data['tp3']:,.2f}"
            ) if data["signal"] != "WAIT" else f"👑 KING ZARRY AI\n⚠️ WAIT / NO TRADE • {data['symbol']} • {data['interval']}"

            await update.message.reply_photo(photo=chart, caption=caption)
        except Exception as chart_error:
            print("⚠️ Chart generation error:", chart_error)

        try:
            await status.delete()
        except Exception:
            pass
    except Exception as error:
        try:
            await status.edit_text(f"❌ <b>SIGNAL ERROR</b>\n\n{html.escape(str(error))}", parse_mode="HTML")
        except Exception:
            await update.message.reply_text(f"❌ Signal Error:\n{error}")

async def text_message_handler(update, context):
    if not update.message or not update.message.text:
        return
    if not await require_subscription(update):
        return

    text = update.message.text.strip()
    if text.startswith("/"):
        return

    await update.message.chat.send_action("typing")
    try:
        answer = await asyncio.to_thread(ask_ai, text)
        await send_long_message(update.message, answer)
    except Exception as error:
        await update.message.reply_text(f"❌ AI Error:\n{error}")

def build_image_prompt(caption):
    if caption and caption.strip():
        return f"Analyze the attached image.\n\nUser request:\n{caption.strip()}\n\nAnalyze technical indicators/chart patterns if applicable."
    return "Analyze this image carefully. Identify trend, support, resistance, or general details clearly."

async def photo_message_handler(update, context):
    if not update.message or not await require_subscription(update):
        return
    await update.message.chat.send_action("typing")

    try:
        photo = update.message.photo[-1]
        telegram_file = await context.bot.get_file(photo.file_id)
        image_bytes = await telegram_file.download_as_bytearray()

        prompt = build_image_prompt(update.message.caption or "")
        result = await asyncio.to_thread(analyze_image_with_ai, bytes(image_bytes), "image/jpeg", prompt)
        await send_long_message(update.message, result)
    except Exception as error:
        await update.message.reply_text(f"❌ Vision Error:\n{error}")

async def paysupport_command(update, context):
    await update.message.reply_text(
        "💳 <b>KING ZARRY AI PAYMENT SUPPORT</b>\n\n"
        "If your Telegram Stars VIP payment did not activate automatically, "
        "contact the admin with your Telegram charge ID.",
        parse_mode="HTML"
    )

async def global_error_handler(update, context):
    print("⚠️ Telegram error:", repr(context.error))

def validate_configuration():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is missing.")
    if not any([XAI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY]):
        raise RuntimeError("❌ No AI API key configured.")

# ============================================================
# MAIN
# ============================================================

def main():
    validate_configuration()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_error_handler(global_error_handler)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("monthly", monthly_command))
    application.add_handler(CommandHandler("3month", three_month_command))
    application.add_handler(CommandHandler("yearly", yearly_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("paysupport", paysupport_command))

    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))

    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("tts", tts_command))

    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("eth", eth_command))
    application.add_handler(CommandHandler("sol", sol_command))
    application.add_handler(CommandHandler("xau", xau_command))

    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    print("👑 KING ZARRY AI IS ONLINE!")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
