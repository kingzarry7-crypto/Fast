import os
import re
import asyncio
import base64
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# 👑 KING ZARRY AI - TELEGRAM BOT
# Multi-Provider Engine (Groq, Gemini, OpenAI, Custom API)
# =========================================================


# =========================================================
# STRING SANITIZATION HELPERS
# =========================================================

def clean_env_str(val: str, default: str = "") -> str:
    """Strips whitespace and hidden zero-width unicode characters from environment variables."""
    if not val:
        return default
    cleaned = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', val).strip()
    return cleaned if cleaned else default


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = clean_env_str(os.environ.get("TELEGRAM_BOT_TOKEN"))

# Provider Keys
GROK_API_KEY = clean_env_str(os.environ.get("GROK_API_KEY") or os.environ.get("GROQ_API_KEY"))
OPENAI_API_KEY = clean_env_str(os.environ.get("OPENAI_API_KEY"))
GEMINI_API_KEY = clean_env_str(os.environ.get("GEMINI_API_KEY"))
TWELVE_DATA_API_KEY = clean_env_str(os.environ.get("TWELVE_DATA_API_KEY"))

# Provider Config (AUTO / GROK / OPENAI / GEMINI)
AI_PROVIDER = clean_env_str(os.environ.get("AI_PROVIDER"), "AUTO").upper()

# Default Models
GROK_MODEL = clean_env_str(os.environ.get("GROK_MODEL") or os.environ.get("GROQ_MODEL"), "llama-3.3-70b-versatile")
OPENAI_MODEL = clean_env_str(os.environ.get("OPENAI_MODEL"), "gpt-4o-mini")
GEMINI_MODEL = clean_env_str(os.environ.get("GEMINI_MODEL"), "gemini-3.7-flash")

# API Base Endpoints
GROK_BASE_URL = clean_env_str(os.environ.get("GROK_BASE_URL") or os.environ.get("GROQ_BASE_URL"), "https://api.groq.com/openai/v1")
OPENAI_BASE_URL = clean_env_str(os.environ.get("OPENAI_BASE_URL"), "https://api.openai.com/v1")

TWELVE_DATA_URL = "https://api.twelvedata.com"


# =========================================================
# STARTUP VALIDATION
# =========================================================

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from environment variables.")

if not any([GROK_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY]):
    raise RuntimeError("No AI API keys configured. Please set GROK_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.")


# =========================================================
# OPTIONAL GEMINI SDK
# =========================================================

try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False


# =========================================================
# AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑, the official assistant for the King Zarry community.

You assist with trading (BTC, ETH, SOL, Forex, Gold/XAUUSD), market analysis, programming, and general conversational queries.

CRITICAL INSTRUCTION:
- DO NOT generate tool calls, function calls, or raw JSON syntax blocks like `{"name": "browser.search"}`.
- Always reply in clean, direct conversational text or formatted Markdown.

TRADING GUIDELINES:
- Never guarantee profits or safe wins.
- Differentiate confirmed technical data vs. probability vs. market uncertainty.
- Explain trade setup logic, risk-to-reward ratios, and invalidation levels clearly.
- Keep responses informative, grounded, and concise.
"""


# =========================================================
# TIMEFRAME MAP & HELPERS
# =========================================================

TIMEFRAME_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min",
    "30m": "30min", "1h": "1h", "2h": "2h",
    "4h": "4h", "1d": "1day",
}

def normalize_timeframe(timeframe: str) -> str:
    tf = timeframe.lower().strip()
    return TIMEFRAME_MAP.get(tf, tf)


async def send_long_message(message, text: str, parse_mode: str = "Markdown"):
    if not text:
        text = "❌ King Zarry AI returned an empty response."

    chunk_size = 3900
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    for chunk in chunks:
        try:
            await message.reply_text(chunk, parse_mode=parse_mode)
        except Exception:
            # Fallback to plain text if Markdown formatting throws an exception
            await message.reply_text(chunk, parse_mode=None)


# =========================================================
# OPENAI-COMPATIBLE & GROQ API ENGINE
# =========================================================

def openai_compatible_request(messages, api_key, base_url, model, disable_tools=True):
    if not api_key:
        raise RuntimeError("API Key missing for request.")

    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1500,
    }

    # Safely handle tool choice without passing invalid parameters
    if not disable_tools:
        payload["tool_choice"] = "auto"

    response = requests.post(endpoint, headers=headers, json=payload, timeout=90)

    if response.status_code != 200:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text
        raise RuntimeError(f"API Error ({response.status_code}): {error_data}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"].strip()
        # Clean out rogue JSON strings if the model attempts an unrequested function call
        if content.startswith('{"name":') or content.startswith('{"tool":'):
            content = "I couldn't complete that search action, but I am ready to answer your question directly!"
        return content
    except Exception:
        raise RuntimeError(f"Invalid API response structure: {data}")


# =========================================================
# GEMINI ENGINE WITH MODERN MODEL FALLBACK
# =========================================================

def gemini_request(prompt: str, image_bytes=None, mime_type=None):
    if not GEMINI_API_KEY or not GEMINI_SDK_AVAILABLE:
        raise RuntimeError("Gemini SDK is unavailable or GEMINI_API_KEY is not provided.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    if image_bytes:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        contents = [f"{SYSTEM_PROMPT}\n\n{prompt}", image_part]
    else:
        contents = [f"{SYSTEM_PROMPT}\n\nUSER:\n{prompt}"]

    # Priority fallback chain starting with Gemini 3.7 Flash
    models_to_try = [GEMINI_MODEL, "gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    last_error = None

    for model_name in dict.fromkeys(models_to_try):  # Deduplicate while preserving order
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            answer = getattr(response, "text", None)
            if answer:
                return answer.strip()
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


# =========================================================
# UNIFIED AI TEXT ROUTER
# =========================================================

def ask_ai(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    if AI_PROVIDER == "GROK":
        return openai_compatible_request(messages, GROK_API_KEY, GROK_BASE_URL, GROK_MODEL, disable_tools=True)
    
    if AI_PROVIDER == "OPENAI":
        return openai_compatible_request(messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, disable_tools=False)

    if AI_PROVIDER == "GEMINI":
        return gemini_request(prompt)

    # AUTO MODE: Cascade Fallback Strategy (Groq -> Gemini -> OpenAI)
    errors = []
    
    if GROK_API_KEY:
        try:
            return openai_compatible_request(messages, GROK_API_KEY, GROK_BASE_URL, GROK_MODEL, disable_tools=True)
        except Exception as e:
            errors.append(f"_groq: {e}")

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            return gemini_request(prompt)
        except Exception as e:
            errors.append(f"_gemini: {e}")

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, disable_tools=False)
        except Exception as e:
            errors.append(f"_openai: {e}")

    raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))


# =========================================================
# UNIFIED AI VISION ROUTER
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
                    "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}
                }
            ]
        }
    ]

    # Active, stable Groq vision fallback model
    GROQ_VISION_FALLBACK = "qwen/qwen3.6-27b"

    if AI_PROVIDER == "GROK":
        vision_model = GROK_MODEL if "vision" in GROK_MODEL or "qwen" in GROK_MODEL else GROQ_VISION_FALLBACK
        return openai_compatible_request(vision_messages, GROK_API_KEY, GROK_BASE_URL, vision_model, disable_tools=True)

    if AI_PROVIDER == "OPENAI":
        return openai_compatible_request(vision_messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, disable_tools=False)

    if AI_PROVIDER == "GEMINI":
        return gemini_request(prompt, image_bytes, mime_type)

    # AUTO VISION FALLBACK
    errors = []

    if GROK_API_KEY:
        try:
            vision_model = GROK_MODEL if "vision" in GROK_MODEL or "qwen" in GROK_MODEL else GROQ_VISION_FALLBACK
            return openai_compatible_request(vision_messages, GROK_API_KEY, GROK_BASE_URL, vision_model, disable_tools=True)
        except Exception as e:
            errors.append(f"Groq Vision: {e}")

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            return gemini_request(prompt, image_bytes, mime_type)
        except Exception as e:
            errors.append(f"Gemini Vision: {e}")

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(vision_messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, disable_tools=False)
        except Exception as e:
            errors.append(f"OpenAI Vision: {e}")

    raise RuntimeError("All vision providers failed. " + " | ".join(errors))


# =========================================================
# TWELVE DATA TECHNICAL INDICATORS
# =========================================================

def get_market_candles(symbol, interval="15min", outputsize=100):
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is not configured in environment variables.")

    response = requests.get(
        f"{TWELVE_DATA_URL}/time_series",
        params={"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_API_KEY},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Twelve Data endpoint returned an error."))

    candles = list(reversed(data.get("values", [])))
    if len(candles) < 50:
        raise RuntimeError(f"Insufficient candle data available for {symbol}.")
    return candles


def ema(values, period):
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result


def rsi(values, period=14):
    if len(values) < (period + 1):
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze_market(closes, highs, lows):
    current_price = closes[-1]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    current_rsi = rsi(closes, 14)

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])

    score = 0
    score += 1 if ema9 > ema21 else -1
    score += 1 if ema21 > ema50 else -1
    score += 1 if current_price > ema21 else -1
    if 50 < current_rsi < 70:
        score += 1
    elif 30 < current_rsi < 50:
        score -= 1

    if score >= 3:
        signal, direction, trend = "BUY", "🟢", "BULLISH"
    elif score <= -3:
        signal, direction, trend = "SELL", "🔴", "BEARISH"
    else:
        signal, direction, trend = "WAIT", "🟡", "NEUTRAL"

    risk = abs(current_price - recent_low) if signal == "BUY" else abs(recent_high - current_price)
    if risk <= 0:
        risk = current_price * 0.005

    stop_loss = (current_price - risk) if signal == "BUY" else (current_price + risk)
    tp1 = (current_price + risk * 1.5) if signal == "BUY" else (current_price - risk * 1.5)
    tp2 = (current_price + risk * 2.5) if signal == "BUY" else (current_price - risk * 2.5)

    return {
        "price": current_price, "signal": signal, "direction": direction, "trend": trend,
        "rsi": current_rsi, "ema9": ema9, "ema21": ema21, "ema50": ema50,
        "entry": current_price, "stop_loss": stop_loss, "tp1": tp1, "tp2": tp2,
        "strength": min(90, max(50, 50 + abs(score) * 10)),
    }


def analyze_symbol(symbol, interval="15min"):
    candles = get_market_candles(symbol, interval, 100)
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    
    result = analyze_market(closes, highs, lows)
    result["symbol"], result["interval"] = symbol, interval
    return result


def format_analysis(data, title="KING ZARRY AI SIGNAL"):
    return (
        f"👑 *{title}*\n\n"
        f"📊 *{data['symbol']}* | Timeframe: *{data['interval']}*\n\n"
        f"{data['direction']} *SIGNAL: {data['signal']}*\n"
        f"📈 Trend: *{data['trend']}* | Strength: *{data['strength']}%*\n\n"
        f"💰 Entry: `${data['entry']:,.2f}`\n"
        f"🛑 Stop Loss: `${data['stop_loss']:,.2f}`\n"
        f"🎯 TP1: `${data['tp1']:,.2f}` | TP2: `${data['tp2']:,.2f}`\n\n"
        f"📊 RSI: *{data['rsi']:.2f}*\n"
        f"EMA9: `${data['ema9']:,.2f}` | EMA21: `${data['ema21']:,.2f}` | EMA50: `${data['ema50']:,.2f}`\n\n"
        "⚠️ Algorithmic analysis only. Always apply strict risk management."
    )


def detect_market_and_timeframe(text):
    upper = text.upper()
    symbol = "BTC/USD"
    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "GOLD"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"],
    }
    for m_symbol, names in markets.items():
        if any(name in upper for name in names):
            symbol = m_symbol
            break

    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", text.lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe


def build_chart_prompt(symbol, timeframe):
    return f"""
Analyze this chart screenshot for {symbol} ({timeframe}).
Identify price action structures, support/resistance levels, trend bias, and actionable trade setups.
Format clearly with King Zarry AI headers. Base all calculations on the visible prices in the image.
"""


# =========================================================
# TELEGRAM HANDLERS
# =========================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👑 *WELCOME TO KING ZARRY AI*\n\n"
        "I am your multi-provider AI trading assistant and community bot.\n\n"
        "*Available Commands:*\n"
        "• `/ask <question>` - Ask any question or request a story\n"
        "• `/signal <symbol>` - Get algorithmic market signals (e.g. `/signal BTC`)\n"
        "• `/xau` | `/btc` | `/eth` | `/sol` - Instant technical analyses\n"
        "• *Send a Photo/Screenshot* - Upload a chart image for AI Vision analysis\n"
        "• *Send any Message* - Chat directly with the AI"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("⚠️ Usage: `/ask What is the current outlook on Gold?`", parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")
    try:
        answer = await asyncio.to_thread(ask_ai, question)
        await send_long_message(update.message, answer)
    except Exception as e:
        await update.message.reply_text(f"❌ AI Error: `{e}`", parse_mode="Markdown")


async def quick_symbol_command(symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, "15min")
        await send_long_message(update.message, format_analysis(data, f"{symbol} ANALYSIS"))
    except Exception as e:
        await update.message.reply_text(f"❌ Market Data Error: `{e}`", parse_mode="Markdown")


async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_args = " ".join(context.args).strip()
    symbol, timeframe = detect_market_and_timeframe(raw_args if raw_args else "BTC")
    tf_normalized = normalize_timeframe(timeframe)
    
    await update.message.chat.send_action("typing")
    try:
        data = await asyncio.to_thread(analyze_symbol, symbol, tf_normalized)
        await send_long_message(update.message, format_analysis(data, f"{symbol} SIGNAL"))
    except Exception as e:
        await update.message.reply_text(f"❌ Signal Error: `{e}`", parse_mode="Markdown")


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    
    # Ignore commands handled by CommandHandler
    if user_text.startswith("/"):
        return

    await update.message.chat.send_action("typing")
    try:
        answer = await asyncio.to_thread(ask_ai, user_text)
        await send_long_message(update.message, answer)
    except Exception as e:
        await update.message.reply_text(f"❌ AI Error: `{e}`", parse_mode="Markdown")


async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.chat.send_action("typing")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        caption = update.message.caption or ""
        symbol, timeframe = detect_market_and_timeframe(caption)
        prompt = build_chart_prompt(symbol, timeframe)

        result = await asyncio.to_thread(analyze_image_with_ai, bytes(image_bytes), "image/jpeg", prompt)
        await send_long_message(update.message, result)
    except Exception as e:
        await update.message.reply_text(f"❌ Vision Error: `{e}`", parse_mode="Markdown")


# =========================================================
# MAIN ENTRYPOINT
# =========================================================

def main():
    print("👑 Starting King Zarry AI Telegram Bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("signal", signal_command))
    
    # Quick Market Shortcuts
    application.add_handler(CommandHandler("btc", lambda u, c: quick_symbol_command("BTC/USD", u, c)))
    application.add_handler(CommandHandler("eth", lambda u, c: quick_symbol_command("ETH/USD", u, c)))
    application.add_handler(CommandHandler("sol", lambda u, c: quick_symbol_command("SOL/USD", u, c)))
    application.add_handler(CommandHandler("xau", lambda u, c: quick_symbol_command("XAU/USD", u, c)))

    # Register Message Handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    print("📡 Telegram polling active. King Zarry AI is online!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
