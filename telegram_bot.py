import os
import re
import html
import asyncio
import base64
import requests
import math
from io import BytesIO
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyArrowPatch

from telegram import Update, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    TypeHandler,
    filters,
)

# =========================================================
# 👑 KING ZARRY AI - TELEGRAM BOT
# AI + TRADING + VISION + SUBSCRIPTIONS + STARS + TTS
# =========================================================

from subscription import (
    ADMIN_IDS,
    MONTHLY_DAYS,
    THREE_MONTH_DAYS,
    YEARLY_DAYS,
    init_subscription_db,
    is_subscribed,
    activate_subscription,
    deactivate_subscription,
    get_subscription,
    record_payment,
    get_payment_history,
)

try:
    from voice import create_voice_note
except ImportError:
    async def create_voice_note(text: str):
        raise RuntimeError("Voice note support is not configured.")

init_subscription_db()

# =========================================================
# STRING HELPERS
# =========================================================

def clean_env_str(val: str, default: str = "") -> str:
    if not val:
        return default

    cleaned = re.sub(
        r'[\u200b\u200c\u200d\u2060\ufeff]',
        '',
        val
    ).strip()

    return cleaned if cleaned else default

def clean_ai_response(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL
    )

    if "<think>" in text:
        text = re.sub(
            r"<think>.*$",
            "",
            text,
            flags=re.DOTALL
        )

    text = re.sub(r"<\|.*?\|>", "", text)

    return text.strip()

def escape_html(text: str) -> str:
    if not text:
        return ""

    text = html.escape(text)

    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)

    return text

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = clean_env_str(
    os.environ.get("TELEGRAM_BOT_TOKEN")
)

GROK_API_KEY = clean_env_str(
    os.environ.get("GROK_API_KEY")
    or os.environ.get("GROQ_API_KEY")
)

OPENAI_API_KEY = clean_env_str(
    os.environ.get("OPENAI_API_KEY")
)

GEMINI_API_KEY = clean_env_str(
    os.environ.get("GEMINI_API_KEY")
)

TWELVE_DATA_API_KEY = clean_env_str(
    os.environ.get("TWELVE_DATA_API_KEY")
)

AI_PROVIDER = clean_env_str(
    os.environ.get("AI_PROVIDER"),
    "AUTO"
).upper()

GROK_MODEL = clean_env_str(
    os.environ.get("GROK_MODEL")
    or os.environ.get("GROQ_MODEL"),
    "llama-3.3-70b-versatile"
)

OPENAI_MODEL = clean_env_str(
    os.environ.get("OPENAI_MODEL"),
    "gpt-4o-mini"
)

GEMINI_MODEL = clean_env_str(
    os.environ.get("GEMINI_MODEL"),
    "gemini-2.5-flash"
)

GROK_BASE_URL = clean_env_str(
    os.environ.get("GROK_BASE_URL")
    or os.environ.get("GROQ_BASE_URL"),
    "https://api.groq.com/openai/v1"
)

OPENAI_BASE_URL = clean_env_str(
    os.environ.get("OPENAI_BASE_URL"),
    "https://api.openai.com/v1"
)

TWELVE_DATA_URL = "https://api.twelvedata.com"

# =========================================================
# TELEGRAM STARS
# =========================================================

MONTHLY_STARS = int(os.environ.get("MONTHLY_STARS", "150"))
THREE_MONTH_STARS = int(os.environ.get("THREE_MONTH_STARS", "500"))
YEARLY_STARS = int(os.environ.get("YEARLY_STARS", "2500"))

SUBSCRIPTION_PLANS = {
    "monthly": {
        "name": "👑 Monthly VIP",
        "days": MONTHLY_DAYS,
        "stars": MONTHLY_STARS,
        "description": "30 days of King Zarry AI VIP access",
    },
    "3month": {
        "name": "🔥 3-Month VIP",
        "days": THREE_MONTH_DAYS,
        "stars": THREE_MONTH_STARS,
        "description": "90 days of King Zarry AI VIP access",
    },
    "yearly": {
        "name": "💎 Yearly VIP",
        "days": YEARLY_DAYS,
        "stars": YEARLY_STARS,
        "description": "365 days of King Zarry AI VIP access",
    },
}

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

if not any([GROK_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY]):
    raise RuntimeError(
        "No AI API keys configured. Set GROK_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."
    )

try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False

# =========================================================
# 👑 SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are an advanced AI assistant for:
- General questions
- Programming
- Technology
- Trading education
- BTC, ETH, SOL, Forex and Gold/XAUUSD
- Market analysis
- Chart/image analysis
- Creative writing
- Business ideas

CRITICAL RULES:
1. Never reveal internal reasoning or chain-of-thought.
2. Never output <think> blocks or control tokens.
3. Answer directly and clearly.
4. For trading, never guarantee profit.
5. Always mention risk when appropriate.
6. Do not invent live prices. Live market values must come from market data.
7. For TTS requests, output only the exact words to speak.
"""

# =========================================================
# TIMEFRAME
# =========================================================

TIMEFRAME_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1day",
}

def normalize_timeframe(timeframe: str) -> str:
    tf = timeframe.lower().strip()
    return TIMEFRAME_MAP.get(tf, tf)

# =========================================================
# MESSAGE SENDING
# =========================================================

async def send_long_message(message, text: str, is_raw_html: bool = False):
    raw_text = clean_ai_response(text)

    if not raw_text:
        raw_text = "King Zarry AI returned an empty response."

    formatted_text = raw_text if is_raw_html else escape_html(raw_text)
    chunk_size = 3800

    chunks = [
        formatted_text[i:i + chunk_size]
        for i in range(0, len(formatted_text), chunk_size)
    ]

    for chunk in chunks:
        try:
            await message.reply_text(
                chunk,
                parse_mode="HTML"
            )
        except Exception:
            await message.reply_text(
                raw_text[:chunk_size],
                parse_mode=None
            )

# =========================================================
# 🔐 SUBSCRIPTION
# =========================================================

def user_has_access(user_id: int) -> bool:
    return user_id in ADMIN_IDS or is_subscribed(user_id)

async def require_subscription(update: Update) -> bool:
    if not update.effective_user:
        return False

    if user_has_access(update.effective_user.id):
        return True

    if update.message:
        await update.message.reply_text(
            "🔒 <b>KING ZARRY AI VIP</b>\n\n"
            "Your subscription is not active.\n\n"
            "👑 Subscribe to unlock:\n"
            "• AI Chat\n"
            "• Trading signals\n"
            "• BTC / ETH / SOL\n"
            "• Gold/XAUUSD\n"
            "• AI Vision\n"
            "• Chart analysis\n\n"
            "Use /buy to choose your VIP plan.",
            parse_mode="HTML"
        )

    return False

# =========================================================
# 🤖 AI REQUESTS
# =========================================================

def openai_compatible_request(
    messages,
    api_key,
    base_url,
    model,
    disable_tools=True
):
    if not api_key:
        raise RuntimeError("API key missing.")

    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    if "groq.com" in base_url.lower():
        payload["reasoning_format"] = "hidden"

    if not disable_tools:
        payload["tool_choice"] = "auto"

    response = requests.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"API Error ({response.status_code}): {error_data}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"].strip()

        if (
            content.startswith('{"name":')
            or content.startswith('{"tool":')
        ):
            return (
                "I couldn't complete that action, "
                "but I am ready to answer your question directly."
            )

        return clean_ai_response(content)

    except Exception:
        raise RuntimeError(
            f"Invalid API response structure: {data}"
        )

def gemini_request(prompt: str, image_bytes=None, mime_type=None):
    if not GEMINI_API_KEY or not GEMINI_SDK_AVAILABLE:
        raise RuntimeError("Gemini SDK unavailable or API key missing.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    if image_bytes:
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        contents = [
            f"{SYSTEM_PROMPT}\n\nTask: {prompt}",
            image_part
        ]
    else:
        contents = [
            f"{SYSTEM_PROMPT}\n\nUSER:\n{prompt}"
        ]

    models_to_try = [
        GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    last_error = None

    for model_name in dict.fromkeys(models_to_try):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=2048
                )
            )

            answer = getattr(response, "text", None)

            if answer:
                return clean_ai_response(answer)

        except Exception as e:
            last_error = e

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )

def ask_ai(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    if AI_PROVIDER == "GROK":
        return openai_compatible_request(
            messages,
            GROK_API_KEY,
            GROK_BASE_URL,
            GROK_MODEL
        )

    if AI_PROVIDER == "OPENAI":
        return openai_compatible_request(
            messages,
            OPENAI_API_KEY,
            OPENAI_BASE_URL,
            OPENAI_MODEL
        )

    if AI_PROVIDER == "GEMINI":
        return gemini_request(prompt)

    errors = []

    if GROK_API_KEY:
        try:
            return openai_compatible_request(
                messages,
                GROK_API_KEY,
                GROK_BASE_URL,
                GROK_MODEL
            )
        except Exception as e:
            errors.append(f"Groq: {e}")

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            return gemini_request(prompt)
        except Exception as e:
            errors.append(f"Gemini: {e}")

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(
                messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL
            )
        except Exception as e:
            errors.append(f"OpenAI: {e}")

    raise RuntimeError(
        "All configured AI providers failed.\n" + " | ".join(errors)
    )

# =========================================================
# 👁️ VISION
# =========================================================

def analyze_image_with_ai(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    vision_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}"
                    }
                }
            ]
        }
    ]

    errors = []

    if GROK_API_KEY:
        try:
            return openai_compatible_request(
                vision_messages,
                GROK_API_KEY,
                GROK_BASE_URL,
                GROK_MODEL
            )
        except Exception as e:
            errors.append(f"Groq Vision: {e}")

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            return gemini_request(
                prompt,
                image_bytes,
                mime_type
            )
        except Exception as e:
            errors.append(f"Gemini Vision: {e}")

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(
                vision_messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL
            )
        except Exception as e:
            errors.append(f"OpenAI Vision: {e}")

    raise RuntimeError(
        "All vision providers failed.\n" + " | ".join(errors)
    )

# =========================================================
# 📊 TWELVE DATA
# =========================================================

def get_market_candles(symbol, interval="30min", outputsize=120):
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
        timeout=20,
    )

    response.raise_for_status()
    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Twelve Data error.")
        )

    values = data.get("values", [])

    if len(values) < 60:
        raise RuntimeError(
            f"Insufficient candle data available for {symbol}."
        )

    return list(reversed(values))

# =========================================================
# INDICATORS
# =========================================================

def ema(values, period):
    if not values or len(values) < period:
        return 0.0

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = ((price - result) * multiplier) + result

    return result

def rsi(values, period=14):
    if not values or len(values) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            (avg_gain * (period - 1)) + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1)) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return max(
            (max(highs[-14:]) - min(lows[-14:])),
            closes[-1] * 0.005
        )

    true_ranges = []

    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period

# =========================================================
# 🧠 MARKET STRUCTURE HELPERS
# =========================================================

def find_swing_levels(highs, lows, lookback=30):
    window_highs = highs[-lookback:]
    window_lows = lows[-lookback:]

    resistance = max(window_highs)
    support = min(window_lows)

    return support, resistance

def detect_structure(highs, lows, closes, ema21, ema50):
    if len(closes) < 12:
        return "NEUTRAL"

    first_half = closes[-12:-6]
    second_half = closes[-6:]

    first_high = max(first_half)
    second_high = max(second_half)

    first_low = min(first_half)
    second_low = min(second_half)

    higher_high = second_high > first_high
    higher_low = second_low > first_low

    lower_high = second_high < first_high
    lower_low = second_low < first_low

    if higher_high and higher_low and ema21 >= ema50:
        return "BULLISH"

    if lower_high and lower_low and ema21 <= ema50:
        return "BEARISH"

    return "NEUTRAL"

# =========================================================
# 🎯 ADVANCED SCORING MARKET ENGINE
# =========================================================

def analyze_market(closes, highs, lows, opens, symbol="XAU/USD"):
    current_price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    current_rsi = rsi(closes, 14)
    current_atr = atr(highs, lows, closes, 14)

    support, resistance = find_swing_levels(
        highs,
        lows,
        lookback=min(35, len(closes))
    )

    structure = detect_structure(
        highs,
        lows,
        closes,
        ema21,
        ema50
    )

    zone_size = max(current_atr * 0.55, current_price * 0.001)

    demand_low = support
    demand_high = support + zone_size

    supply_high = resistance
    supply_low = resistance - zone_size

    bullish_score = 0.0
    bearish_score = 0.0

    # 1. EMA Alignment (Strict Rule: EMA 9 > EMA 21 > EMA 50)
    if ema9 > ema21 > ema50:
        bullish_score += 3.0
    elif ema9 > ema21:
        bullish_score += 1.0

    if ema9 < ema21 < ema50:
        bearish_score += 3.0
    elif ema9 < ema21:
        bearish_score += 1.0

    # 2. Price relative to EMAs
    if current_price > ema9:
        bullish_score += 1.5
    elif current_price > ema21:
        bullish_score += 1.0

    if current_price < ema9:
        bearish_score += 1.5
    elif current_price < ema21:
        bearish_score += 1.0

    # 3. RSI Momentum & Overbought/Oversold Guardrails
    prev_rsi = rsi(closes[:-1], 14) if len(closes) > 15 else current_rsi
    rsi_rising = current_rsi > prev_rsi

    # Overbought (>75) and Oversold (<25) Filters prevent buying tops/selling bottoms
    if current_rsi > 75:
        # Heavily penalize bullish scores on overbought RSI unless breaking resistance
        if current_price <= resistance:
            bullish_score -= 2.0
            bearish_score += 1.5
    elif current_rsi < 25:
        # Heavily penalize bearish scores on oversold RSI unless breaking support
        if current_price >= support:
            bearish_score -= 2.0
            bullish_score += 1.5
    elif current_rsi > 50:
        if current_rsi < 65 and rsi_rising:
            bullish_score += 2.0
        elif current_rsi >= 65 and not rsi_rising:
            bearish_score += 1.0
        else:
            bullish_score += 1.0
    else:
        if current_rsi > 35 and not rsi_rising:
            bearish_score += 2.0
        elif current_rsi <= 35 and rsi_rising:
            bullish_score += 1.0
        else:
            bearish_score += 1.0

    # 4. Market Structure
    if structure == "BULLISH":
        bullish_score += 2.5
    elif structure == "BEARISH":
        bearish_score += 2.5

    # 5. Support / Resistance Proximity
    dist_to_support = abs(current_price - support)
    dist_to_resistance = abs(current_price - resistance)

    if dist_to_support <= current_atr * 1.2:
        bullish_score += 2.0
    if dist_to_resistance <= current_atr * 1.2:
        bearish_score += 2.0

    if current_price > resistance:
        bullish_score += 2.5
    if current_price < support:
        bearish_score += 2.5

    # 6. Candle Momentum (Last 3 candles)
    recent_closes = closes[-3:]
    recent_opens = opens[-3:]
    
    bullish_candles = sum(1 for c, o in zip(recent_closes, recent_opens) if c > o)
    if bullish_candles >= 2:
        bullish_score += 1.0
    elif bullish_candles <= 1:
        bearish_score += 1.0

    total_max = 12.5
    norm_bullish = min(100, int((max(0, bullish_score) / total_max) * 100))
    norm_bearish = min(100, int((max(0, bearish_score) / total_max) * 100))

    score_diff = abs(norm_bullish - norm_bearish)

    # Pre-initialize position values
    entry = current_price
    entry_zone_low = demand_low
    entry_zone_high = supply_high
    stop_loss = None
    tp1 = None
    tp2 = None
    tp3 = None
    risk = current_atr

    # High quality setup threshold requirement (>= 75/100)
    MIN_SCORE_THRESHOLD = 75

    if norm_bullish >= MIN_SCORE_THRESHOLD and norm_bullish > norm_bearish and score_diff >= 15 and current_rsi <= 75:
        signal = "BUY"
        direction = "🟢"
        trend = "BULLISH"
        strength = norm_bullish
        
        # Optimized Entry Zone based on dynamic ATR pullback
        entry_low = max(support, current_price - current_atr * 0.3)
        entry_high = current_price
        entry = (entry_low + entry_high) / 2
        
        # Stop Loss placed below support with ATR buffer
        stop_loss = min(support - (current_atr * 0.2), entry - (current_atr * 1.0))
        risk = entry - stop_loss
        if risk <= 0:
            risk = current_atr * 1.0
            stop_loss = entry - risk

        # Take Profit targets based on ATR multiples
        tp1 = entry + (risk * 1.5)
        tp2 = entry + (risk * 2.5)
        tp3 = entry + (risk * 3.5)
        
        entry_zone_low = entry_low
        entry_zone_high = entry_high

    elif norm_bearish >= MIN_SCORE_THRESHOLD and norm_bearish > norm_bullish and score_diff >= 15 and current_rsi >= 25:
        signal = "SELL"
        direction = "🔴"
        trend = "BEARISH"
        strength = norm_bearish
        
        # Optimized Entry Zone based on dynamic ATR pullback
        entry_low = current_price
        entry_high = min(resistance, current_price + current_atr * 0.3)
        entry = (entry_low + entry_high) / 2
        
        # Stop Loss placed above resistance with ATR buffer
        stop_loss = max(resistance + (current_atr * 0.2), entry + (current_atr * 1.0))
        risk = stop_loss - entry
        if risk <= 0:
            risk = current_atr * 1.0
            stop_loss = entry + risk

        # Take Profit targets based on ATR multiples
        tp1 = entry - (risk * 1.5)
        tp2 = entry - (risk * 2.5)
        tp3 = entry - (risk * 3.5)
        
        entry_zone_low = entry_low
        entry_zone_high = entry_high

    else:
        signal = "WAIT"
        direction = "🟡"
        trend = structure if structure != "NEUTRAL" else "NEUTRAL"
        strength = max(norm_bullish, norm_bearish)

    rr = (
        abs(tp3 - entry) / abs(entry - stop_loss)
        if signal != "WAIT" and stop_loss is not None and tp3 is not None and abs(entry - stop_loss) > 0
        else 0
    )

    return {
        "price": current_price,
        "signal": signal,
        "direction": direction,
        "trend": trend,
        "structure": structure,
        "rsi": current_rsi,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "atr": current_atr,
        "support": support,
        "resistance": resistance,
        "demand_low": demand_low,
        "demand_high": demand_high,
        "supply_low": supply_low,
        "supply_high": supply_high,
        "entry": entry,
        "entry_zone_low": entry_zone_low,
        "entry_zone_high": entry_zone_high,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "risk": risk,
        "rr": rr,
        "strength": strength,
        "bullish_score": norm_bullish,
        "bearish_score": norm_bearish,
    }

def analyze_symbol(symbol, interval="15min"):
    candles = get_market_candles(
        symbol,
        interval,
        120
    )

    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    opens = [float(c["open"]) for c in candles]

    result = analyze_market(
        closes,
        highs,
        lows,
        opens,
        symbol
    )

    result["symbol"] = symbol
    result["interval"] = interval
    result["candles"] = candles

    return result

# =========================================================
# 📝 SIGNAL TEXT
# =========================================================

def format_signal(data):
    symbol = data["symbol"]
    signal = data["signal"]

    if signal == "BUY":
        setup_text = f"High probability bullish confluence ({data['strength']}/100). EMA alignment & momentum confirmed."
        sl_str = f"{data['stop_loss']:,.2f}"
        tp1_str = f"{data['tp1']:,.2f}"
        tp2_str = f"{data['tp2']:,.2f}"
        tp3_str = f"{data['tp3']:,.2f}"
        rr_str = f"1:{data['rr']:.1f}"
    elif signal == "SELL":
        setup_text = f"High probability bearish confluence ({data['strength']}/100). EMA alignment & momentum confirmed."
        sl_str = f"{data['stop_loss']:,.2f}"
        tp1_str = f"{data['tp1']:,.2f}"
        tp2_str = f"{data['tp2']:,.2f}"
        tp3_str = f"{data['tp3']:,.2f}"
        rr_str = f"1:{data['rr']:.1f}"
    else:
        if data['rsi'] > 75:
            setup_text = "RSI severely overbought (>75). Suppressing buy signals to prevent buying at local tops."
        elif data['rsi'] < 25:
            setup_text = "RSI severely oversold (<25). Suppressing sell signals to prevent shorting at local bottoms."
        else:
            setup_text = (
                f"Setup score ({data['strength']}/100) below quality threshold (75/100) or market is in consolidation. "
                "Awaiting high-probability breakout."
            )
        sl_str = "N/A"
        tp1_str = "N/A"
        tp2_str = "N/A"
        tp3_str = "N/A"
        rr_str = "N/A"

    return (
        f"👑 <b>KING ZARRY AI • {symbol} SIGNAL</b>\n\n"
        f"{data['direction']} <b>{signal}</b>\n"
        f"⏱ Timeframe: <b>{data['interval']}</b>\n"
        f"📈 Trend: <b>{data['trend']}</b>\n"
        f"🏗 Structure: <b>{data['structure']}</b>\n"
        f"💪 Setup strength: <b>{data['strength']:.0f}/100</b>\n"
        f"⚖️ Risk-Reward: <b>{rr_str}</b>\n\n"
        f"💰 Current price: <b>{data['price']:,.2f}</b>\n\n"
        f"🎯 <b>ENTRY ZONE</b>\n"
        f"<code>{data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}</code>\n\n"
        f"🛑 Stop Loss: <code>{sl_str}</code>\n"
        f"🎯 TP1 (1.5x Risk): <code>{tp1_str}</code>\n"
        f"🎯 TP2 (2.5x Risk): <code>{tp2_str}</code>\n"
        f"🎯 TP3 (3.5x Risk): <code>{tp3_str}</code>\n\n"
        f"🧱 Support: <code>{data['support']:,.2f}</code>\n"
        f"🚧 Resistance: <code>{data['resistance']:,.2f}</code>\n"
        f"📊 RSI (14): <b>{data['rsi']:.1f}</b>\n"
        f"📏 ATR (14): <code>{data['atr']:,.2f}</code>\n"
        f"📏 EMA 9: <code>{data['ema9']:,.2f}</code>\n"
        f"📏 EMA 21: <code>{data['ema21']:,.2f}</code>\n"
        f"📏 EMA 50: <code>{data['ema50']:,.2f}</code>\n\n"
        f"🧠 <b>Setup:</b> {setup_text}\n\n"
        f"⚠️ <i>Algorithmic market analysis, not guaranteed financial advice. "
        f"Use proper position sizing and risk management.</i>"
    )

# =========================================================
# 📈 TRADINGVIEW-STYLE CHART IMAGE
# =========================================================

def _parse_candle_time(value):
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass

    return datetime.now()

def build_signal_chart(data):
    candles = data["candles"][-65:]

    times = [
        _parse_candle_time(c.get("datetime", ""))
        for c in candles
    ]

    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]

    x = list(range(len(candles)))

    fig, ax = plt.subplots(figsize=(14, 7.8), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    candle_width = 0.58

    for i in range(len(candles)):
        o = opens[i]
        h = highs[i]
        l = lows[i]
        c = closes[i]

        bullish = c >= o
        body_color = "#155EEF" if bullish else "#C62828"

        ax.vlines(i, l, h, linewidth=0.8, color="#6b7280", zorder=2)

        body_bottom = min(o, c)
        body_height = max(abs(c - o), 0.00001)

        rect = Rectangle(
            (i - candle_width / 2, body_bottom),
            candle_width,
            body_height,
            facecolor=body_color,
            edgecolor=body_color,
            linewidth=0.6,
            zorder=3
        )
        ax.add_patch(rect)

    ema21_values = []
    ema50_values = []

    for i in range(len(candles)):
        partial = closes[:i + 1]
        ema21_values.append(ema(partial, 21) if len(partial) >= 21 else float("nan"))
        ema50_values.append(ema(partial, 50) if len(partial) >= 50 else float("nan"))

    ax.plot(x, ema21_values, linewidth=1.3, label="EMA 21")
    ax.plot(x, ema50_values, linewidth=1.3, label="EMA 50")

    signal = data["signal"]
    current = data["price"]

    entry_low = data["entry_zone_low"]
    entry_high = data["entry_zone_high"]

    sl = data["stop_loss"]
    tp1 = data["tp1"]
    tp2 = data["tp2"]
    tp3 = data["tp3"]

    support = data["support"]
    resistance = data["resistance"]

    y_min = min(min(lows), sl if signal != "WAIT" and sl else min(lows))
    y_max = max(max(highs), tp3 if signal != "WAIT" and tp3 else max(highs))
    padding = max((y_max - y_min) * 0.08, data["atr"] * 0.8)

    ax.axhline(support, linewidth=0.9, linestyle="--", alpha=0.65)
    ax.axhline(resistance, linewidth=0.9, linestyle="--", alpha=0.65)

    ax.text(len(x) - 1, support, "  SUPPORT", va="bottom", fontsize=8)
    ax.text(len(x) - 1, resistance, "  RESISTANCE", va="bottom", fontsize=8)

    zone_x = len(x) - 25

    if signal == "BUY":
        ax.add_patch(
            Rectangle(
                (zone_x, data["demand_low"]),
                25,
                data["demand_high"] - data["demand_low"],
                facecolor="#B7E4C7",
                edgecolor="#52B788",
                alpha=0.35,
                linewidth=1
            )
        )
        ax.text(zone_x + 1, data["demand_high"], "DEMAND", fontsize=8, va="bottom")

    elif signal == "SELL":
        ax.add_patch(
            Rectangle(
                (zone_x, data["supply_low"]),
                25,
                data["supply_high"] - data["supply_low"],
                facecolor="#F8C4C4",
                edgecolor="#C62828",
                alpha=0.35,
                linewidth=1
            )
        )
        ax.text(zone_x + 1, data["supply_high"], "SUPPLY", fontsize=8, va="bottom")

    if signal in ("BUY", "SELL"):
        if signal == "BUY":
            entry_color = "#BFE7E7"
            stop_color = "#F6B7B7"
            target_color = "#BDE7F2"
        else:
            entry_color = "#F5D0D0"
            stop_color = "#F6B7B7"
            target_color = "#E0C8F5"

        x0 = max(0, len(x) - 17)
        width = 17

        ax.add_patch(
            Rectangle(
                (x0, entry_low),
                width,
                entry_high - entry_low,
                facecolor=entry_color,
                edgecolor="#555555",
                alpha=0.55,
                linewidth=0.8,
                zorder=1
            )
        )

        if signal == "BUY":
            stop_bottom = sl
            stop_height = entry_low - sl
        else:
            stop_bottom = entry_high
            stop_height = sl - entry_high

        ax.add_patch(
            Rectangle(
                (x0, stop_bottom),
                width,
                max(stop_height, data["atr"] * 0.1),
                facecolor=stop_color,
                edgecolor="#C62828",
                alpha=0.45,
                linewidth=0.8,
                zorder=1
            )
        )

        if signal == "BUY":
            target_bottom = entry_high
            target_height = tp3 - entry_high
        else:
            target_bottom = tp3
            target_height = entry_low - tp3

        ax.add_patch(
            Rectangle(
                (x0, target_bottom),
                width,
                max(target_height, data["atr"] * 0.1),
                facecolor=target_color,
                edgecolor="#2D7DD2",
                alpha=0.30,
                linewidth=0.8,
                zorder=1
            )
        )

        levels = [
            (entry_low, "ENTRY LOW"),
            (entry_high, "ENTRY HIGH"),
            (sl, "STOP LOSS"),
            (tp1, "TP1"),
            (tp2, "TP2"),
            (tp3, "TP3"),
        ]

        for level, label in levels:
            ax.axhline(level, linewidth=0.8, linestyle=":", alpha=0.65)
            ax.text(
                len(x) + 0.7,
                level,
                f"{label}  {level:,.2f}",
                va="center",
                fontsize=8,
                fontweight="bold"
            )

        arrow_start = x0 + width * 0.52

        if signal == "BUY":
            arrow = FancyArrowPatch(
                (arrow_start, entry_high),
                (arrow_start, tp3),
                arrowstyle="->",
                mutation_scale=18,
                linewidth=1.6,
                color="#111827"
            )
        else:
            arrow = FancyArrowPatch(
                (arrow_start, entry_low),
                (arrow_start, tp3),
                arrowstyle="->",
                mutation_scale=18,
                linewidth=1.6,
                color="#111827"
            )

        ax.add_patch(arrow)

    ax.axhline(current, linewidth=1.0, linestyle="-", alpha=0.55)
    ax.text(
        len(x) - 1,
        current,
        f"  {current:,.2f}",
        va="center",
        fontsize=9,
        fontweight="bold"
    )

    title_signal = (
        "🟢 BUY" if signal == "BUY"
        else "🔴 SELL" if signal == "SELL"
        else "🟡 WAIT"
    )

    ax.set_title(
        f"👑 KING ZARRY AI • {data['symbol']} • {data['interval']} • {title_signal}",
        fontsize=15,
        fontweight="bold",
        loc="left",
        pad=12
    )

    if times:
        tick_positions = list(range(0, len(times), max(1, len(times) // 6)))
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(
            [times[i].strftime("%d %b\n%H:%M") for i in tick_positions],
            fontsize=8
        )

    ax.set_xlim(-1, len(x) + 8)
    ax.set_ylim(y_min - padding, y_max + padding)

    ax.grid(True, alpha=0.15, linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(loc="upper left", fontsize=8, frameon=False)
    plt.tight_layout()

    buffer = BytesIO()
    buffer.name = "king_zarry_signal.png"

    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)

    return buffer

# =========================================================
# 🔎 SYMBOL DETECTION
# =========================================================

def detect_market_and_timeframe(text):
    upper = text.upper()
    symbol = "XAU/USD"

    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "XAU", "GOLD"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"],
    }

    for m_symbol, names in markets.items():
        if any(name in upper for name in names):
            symbol = m_symbol
            break

    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", text.lower())
    timeframe = match.group(1) if match else "1h"

    return symbol, timeframe

def build_image_prompt(caption: str) -> str:
    if caption and caption.strip():
        return (
            "The user attached an image and gave this request:\n\n"
            f"{caption.strip()}\n\n"
            "Follow the request precisely."
        )

    return (
        "Analyze this image carefully.\n\n"
        "If it is a financial/trading chart, identify price action, "
        "trend, support/resistance, indicators, possible setups and "
        "invalidation levels.\n\n"
        "If it is a general image, describe what is visible clearly."
    )

# =========================================================
# COMMAND HANDLERS
# =========================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    subscribed = user and user_has_access(user.id)

    status_text = "🟢 <b>VIP ACTIVE</b>" if subscribed else "🔴 <b>VIP NOT ACTIVE</b>"

    welcome_text = (
        "👑 <b>WELCOME TO KING ZARRY AI</b>\n\n"
        "Your AI assistant for trading, programming, vision and more.\n\n"
        f"{status_text}\n\n"
        "💎 <b>VIP Commands</b>\n"
        "• /buy - Buy VIP subscription\n"
        "• /status - Check subscription\n"
        "• /history - Payment history\n\n"
        "🤖 <b>AI Commands</b>\n"
        "• /ask &lt;question&gt;\n"
        "• /tts &lt;text&gt;\n"
        "• /signal XAU 1h\n"
        "• /btc\n"
        "• /eth\n"
        "• /sol\n"
        "• /xau\n\n"
        "📸 Send a photo/chart for AI Vision.\n\n"
        "👑 <b>KING ZARRY AI</b>"
    )

    await send_long_message(update.message, welcome_text, is_raw_html=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 <b>KING ZARRY AI VIP</b>\n\n"
        "Choose your subscription:\n\n"
        f"🌟 <b>Monthly</b>\n30 days • {MONTHLY_STARS} Stars\n\n"
        f"🔥 <b>3 Months</b>\n90 days • {THREE_MONTH_STARS} Stars\n\n"
        f"💎 <b>Yearly</b>\n365 days • {YEARLY_STARS} Stars\n\n"
        "Use:\n/monthly\n/3month\n/yearly"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def send_subscription_invoice(update: Update, plan_key: str):
    if plan_key not in SUBSCRIPTION_PLANS:
        await update.message.reply_text("❌ Invalid subscription plan.")
        return

    plan = SUBSCRIPTION_PLANS[plan_key]

    await update.message.reply_invoice(
        title=plan["name"],
        description=plan["description"],
        payload=f"kingzarry_subscription:{plan_key}",
        currency="XTR",
        prices=[LabeledPrice(plan["name"], plan["stars"])],
        provider_token="",
        start_parameter=f"kingzarry-{plan_key}"
    )

async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_subscription_invoice(update, "monthly")

async def three_month_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_subscription_invoice(update, "3month")

async def yearly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_subscription_invoice(update, "yearly")

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    payload = query.invoice_payload

    if not payload.startswith("kingzarry_subscription:"):
        await query.answer(ok=False, error_message="Invalid subscription payment.")
        return

    plan_key = payload.split(":", 1)[1]

    if plan_key not in SUBSCRIPTION_PLANS:
        await query.answer(ok=False, error_message="This subscription plan is no longer available.")
        return

    expected_amount = SUBSCRIPTION_PLANS[plan_key]["stars"]

    if query.currency != "XTR":
        await query.answer(ok=False, error_message="Payment must be made using Telegram Stars.")
        return

    if query.total_amount != expected_amount:
        await query.answer(ok=False, error_message="Payment amount does not match the subscription plan.")
        return

    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    payment = message.successful_payment
    user = update.effective_user

    if not payment or not user:
        return

    payload = payment.invoice_payload
    if not payload.startswith("kingzarry_subscription:"):
        return

    plan_key = payload.split(":", 1)[1]
    if plan_key not in SUBSCRIPTION_PLANS:
        await message.reply_text("⚠️ Payment received, but plan couldn't be identified.")
        return

    plan = SUBSCRIPTION_PLANS[plan_key]
    payment_id = payment.telegram_payment_charge_id
    username = user.username or user.full_name or str(user.id)

    recorded = record_payment(
        user_id=user.id,
        username=username,
        plan=plan_key,
        payment_method="telegram_stars",
        payment_id=payment_id,
        amount=payment.total_amount,
        currency=payment.currency,
        payload=payload,
    )

    if not recorded:
        await message.reply_text("⚠️ This payment has already been processed.")
        return

    expires_at = activate_subscription(
        user_id=user.id,
        username=username,
        days=plan["days"],
        plan=plan_key,
        payment_method="telegram_stars",
        payment_id=payment_id,
    )

    await message.reply_text(
        "🎉 <b>PAYMENT SUCCESSFUL!</b>\n\n"
        "👑 Welcome to <b>KING ZARRY AI VIP</b>!\n\n"
        f"📦 Plan: <b>{plan['name']}</b>\n"
        f"⭐ Paid: <b>{payment.total_amount} Stars</b>\n\n"
        f"🗓 VIP expires:\n<code>{expires_at.strftime('%Y-%m-%d %H:%M UTC')}</code>\n\n"
        "✅ Access active.",
        parse_mode="HTML"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    if user.id in ADMIN_IDS:
        await update.message.reply_text("👑 <b>KING ZARRY ADMIN</b>\n\n🟢 Unlimited access", parse_mode="HTML")
        return

    subscription = get_subscription(user.id)
    if not subscription:
        await update.message.reply_text("🔴 <b>NO ACTIVE SUBSCRIPTION</b>\n\nUse /buy to subscribe.", parse_mode="HTML")
        return

    if not is_subscribed(user.id):
        await update.message.reply_text("🔴 <b>SUBSCRIPTION EXPIRED</b>\n\nUse /buy to renew.", parse_mode="HTML")
        return

    expires_at = subscription.get("expires_at")
    plan = subscription.get("plan", "VIP")

    await update.message.reply_text(
        f"🟢 <b>VIP ACTIVE</b>\n\n👑 Plan: <b>{plan}</b>\n📅 Expires: <code>{expires_at}</code>",
        parse_mode="HTML"
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    history = get_payment_history(user.id, 10)
    if not history:
        await update.message.reply_text("💳 No payment history found.")
        return

    lines = ["💳 <b>KING ZARRY PAYMENT HISTORY</b>\n"]
    for row in history:
        plan, method, amount, currency, created = row
        lines.append(f"• <b>{plan}</b> | {amount} {currency}\n  {method}\n  {created}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage:\n/grant USER_ID DAYS")
        return

    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ USER_ID and DAYS must be numbers.")
        return

    expires_at = activate_subscription(
        user_id=target_user_id,
        username="admin_granted",
        days=days,
        plan="admin",
        payment_method="admin",
        payment_id=None,
    )

    await update.message.reply_text(
        f"✅ <b>Subscription granted.</b>\n\n👤 User ID: <code>{target_user_id}</code>\n📅 Days: <b>{days}</b>\n⏰ Expires: <code>{expires_at}</code>",
        parse_mode="HTML"
    )

async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage:\n/revoke USER_ID")
        return

    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid USER_ID.")
        return

    deactivate_subscription(target_user_id)
    await update.message.reply_text(f"🚫 <b>Subscription revoked.</b>\n\nUser ID: <code>{target_user_id}</code>", parse_mode="HTML")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update):
        return

    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("⚠️ Usage:\n/ask What is Bitcoin?")
        return

    await update.message.chat.send_action("typing")

    try:
        answer = await asyncio.to_thread(ask_ai, question)
        await send_long_message(update.message, answer)
    except Exception as e:
        await update.message.reply_text(f"❌ AI Error:\n{e}")

async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update):
        return

    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("⚠️ Usage:\n/tts Hello from King Zarry AI!")
        return

    await update.message.chat.send_action("record_voice")
    voice_file = None

    try:
        voice_file = await create_voice_note(text)
        with open(voice_file, "rb") as voice:
            await update.message.reply_voice(voice=voice, caption="👑 King Zarry AI")
    except Exception as e:
        await update.message.reply_text(f"❌ Voice Error:\n{e}")
    finally:
        if voice_file and os.path.exists(voice_file):
            try:
                os.remove(voice_file)
            except OSError:
                pass

async def quick_symbol_command(symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update):
        return

    await update.message.chat.send_action("typing")

    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, "15min")
        await send_long_message(update.message, format_signal(data), is_raw_html=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Market Data Error:\n{e}")

# Quick Market Wrappers
async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await quick_symbol_command("BTC/USD", update, context)

async def eth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await quick_symbol_command("ETH/USD", update, context)

async def sol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await quick_symbol_command("SOL/USD", update, context)

async def xau_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await quick_symbol_command("XAU/USD", update, context)

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update):
        return

    raw_args = " ".join(context.args).strip()
    symbol, timeframe = detect_market_and_timeframe(raw_args or "XAUUSD 1h")
    tf_normalized = normalize_timeframe(timeframe)

    await update.message.chat.send_action("typing")

    status_message = await update.message.reply_text(
        "👑 <b>KING ZARRY AI</b>\n📡 Scanning live market data...\n📈 Building signal chart...",
        parse_mode="HTML"
    )

    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, tf_normalized)

        await send_long_message(update.message, format_signal(data), is_raw_html=True)

        try:
            chart = await asyncio.to_thread(build_signal_chart, data)
            sl_caption = f"{data['stop_loss']:,.2f}" if data['stop_loss'] else "N/A"
            tp3_caption = f"{data['tp3']:,.2f}" if data['tp3'] else "N/A"

            caption = (
                f"👑 KING ZARRY AI\n"
                f"{data['direction']} {data['signal']} • {data['symbol']} • {data['interval']}\n"
                f"Entry: {data['entry_zone_low']:,.2f} - {data['entry_zone_high']:,.2f}\n"
                f"SL: {sl_caption} | TP3: {tp3_caption}"
            )

            await update.message.reply_photo(photo=chart, caption=caption)
        except Exception as chart_error:
            print(f"⚠️ Signal chart error: {chart_error}")
            await update.message.reply_text("⚠️ Chart image generation failed.")

        try:
            await status_message.delete()
        except Exception:
            pass

    except Exception as e:
        try:
            await status_message.edit_text(f"❌ <b>Signal Error</b>\n\n{html.escape(str(e))}", parse_mode="HTML")
        except Exception:
            await update.message.reply_text(f"❌ Signal Error:\n{e}")

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if not await require_subscription(update):
        return

    user_text = update.message.text.strip()
    if user_text.startswith("/"):
        return

    await update.message.chat.send_action("typing")

    try:
        answer = await asyncio.to_thread(ask_ai, user_text)
        await send_long_message(update.message, answer)
    except Exception as e:
        await update.message.reply_text(f"❌ AI Error:\n{e}")

async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not await require_subscription(update):
        return

    await update.message.chat.send_action("typing")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()

        caption = update.message.caption or ""
        prompt = build_image_prompt(caption)

        result = await asyncio.to_thread(
            lambda: analyze_image_with_ai(bytes(image_bytes), "image/jpeg", prompt)
        )

        await send_long_message(update.message, result)
    except Exception as e:
        await update.message.reply_text(f"❌ Vision Error:\n{e}")

async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 <b>KING ZARRY AI PAYMENT SUPPORT</b>\n\nIf you paid but your subscription did not activate, contact support.",
        parse_mode="HTML"
    )

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("⚠️ Telegram Bot Error:", context.error)

# =========================================================
# MAIN
# =========================================================

def main():
    print("👑 =======================================")
    print("👑 KING ZARRY AI TELEGRAM")
    print("👑 AI + ADVANCED TRADING SIGNALS")
    print("👑 =======================================")

    application = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_error_handler(global_error_handler)

    # BASIC
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # SUBSCRIPTIONS
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("monthly", monthly_command))
    application.add_handler(CommandHandler("3month", three_month_command))
    application.add_handler(CommandHandler("yearly", yearly_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("paysupport", paysupport_command))

    # ADMIN
    application.add_handler(CommandHandler("grant", grant_command))
    application.add_handler(CommandHandler("revoke", revoke_command))

    # AI / VOICE
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("tts", tts_command))

    # ADVANCED SIGNAL
    application.add_handler(CommandHandler("signal", signal_command))

    # QUICK MARKET COMMANDS
    application.add_handler(CommandHandler("btc", btc_command))
    application.add_handler(CommandHandler("eth", eth_command))
    application.add_handler(CommandHandler("sol", sol_command))
    application.add_handler(CommandHandler("xau", xau_command))

    # TELEGRAM STARS PAYMENTS
    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # MEDIA & TEXT
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    print("📡 Telegram polling active.")
    print("👑 KING ZARRY AI IS ONLINE!")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
