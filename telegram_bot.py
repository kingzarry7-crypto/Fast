import os
import re
import asyncio
import base64
import requests
import traceback

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
# PHASE 1: STABLE CHAT + COMMANDS + VISION
# =========================================================


# =========================================================
# ENVIRONMENT HELPERS
# =========================================================

def clean_env_str(value, default=""):
    if not value:
        return default

    value = str(value)

    # Remove invisible Unicode characters
    value = re.sub(
        r"[\u200b\u200c\u200d\u2060\ufeff]",
        "",
        value
    )

    return value.strip() or default


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = clean_env_str(
    os.environ.get("TELEGRAM_BOT_TOKEN")
)

GROQ_API_KEY = clean_env_str(
    os.environ.get("GROQ_API_KEY")
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


# =========================================================
# AI CONFIGURATION
# =========================================================

AI_PROVIDER = clean_env_str(
    os.environ.get("AI_PROVIDER"),
    "AUTO"
).upper()


# GroqCloud
GROQ_MODEL = clean_env_str(
    os.environ.get("GROQ_MODEL"),
    "openai/gpt-oss-120b"
)

GROQ_BASE_URL = clean_env_str(
    os.environ.get("GROQ_BASE_URL"),
    "https://api.groq.com/openai/v1"
)


# OpenAI
OPENAI_MODEL = clean_env_str(
    os.environ.get("OPENAI_MODEL"),
    "gpt-4o-mini"
)

OPENAI_BASE_URL = clean_env_str(
    os.environ.get("OPENAI_BASE_URL"),
    "https://api.openai.com/v1"
)


# Gemini
GEMINI_MODEL = clean_env_str(
    os.environ.get("GEMINI_MODEL"),
    "gemini-3.6-flash"
)


# =========================================================
# VALIDATION
# =========================================================

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "❌ TELEGRAM_BOT_TOKEN is missing."
    )


if not any([
    GROQ_API_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY
]):
    raise RuntimeError(
        "❌ No AI provider configured.\n"
        "Set GROQ_API_KEY, OPENAI_API_KEY, "
        "or GEMINI_API_KEY."
    )


# =========================================================
# GEMINI SDK
# =========================================================

try:
    from google import genai
    from google.genai import types

    GEMINI_SDK_AVAILABLE = True

except Exception as e:
    GEMINI_SDK_AVAILABLE = False
    print(f"⚠️ Gemini SDK unavailable: {e}")


# =========================================================
# 👑 KING ZARRY AI PERSONALITY
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant of the King Zarry community.

Your personality:
- Friendly
- Calm
- Intelligent
- Helpful
- Natural
- Conversational
- Confident without pretending to know things you don't know

You can help with:
- General conversation
- Stories
- Programming
- Technology
- Trading
- Forex
- Gold / XAUUSD
- BTC
- ETH
- SOL
- Market analysis
- Risk management

For normal conversation, respond naturally like a real AI assistant.

For trading:
- Never guarantee profits.
- Never claim a trade is certain.
- Clearly distinguish facts, probabilities, and assumptions.
- Explain risk and invalidation when giving setups.

Do NOT call tools.
Do NOT invent browser results.
Do NOT pretend to have live information unless live data was actually provided.

Keep normal answers reasonably concise.
"""


# =========================================================
# MESSAGE SENDER
# =========================================================

async def send_long_message(message, text):
    if not text:
        text = (
            "👑 King Zarry AI received your message "
            "but returned an empty response."
        )

    # Telegram message limit safety
    chunk_size = 3900

    for i in range(0, len(text), chunk_size):

        chunk = text[i:i + chunk_size]

        try:
            await message.reply_text(
                chunk,
                parse_mode=None
            )

        except Exception as e:

            print(
                f"⚠️ Telegram send error: {e}"
            )

            await message.reply_text(
                str(chunk)
            )


# =========================================================
# OPENAI-COMPATIBLE REQUEST
# =========================================================

def openai_request(
    messages,
    api_key,
    base_url,
    model
):

    if not api_key:
        raise RuntimeError(
            "API key is not configured."
        )

    endpoint = (
        base_url.rstrip("/")
        + "/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,

        # Keep this simple.
        # No tools.
        # No browser search.
        # No function calling.

        "temperature": 0.7,
        "max_tokens": 2000,
    }

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
            f"API Error {response.status_code}: "
            f"{error_data}"
        )

    data = response.json()

    try:

        content = (
            data["choices"][0]
            ["message"]
            ["content"]
        )

        if not content:
            raise RuntimeError(
                "AI returned empty content."
            )

        return str(content).strip()

    except Exception:

        raise RuntimeError(
            f"Unexpected AI response: {data}"
        )


# =========================================================
# GEMINI REQUEST
# =========================================================

def gemini_request(
    prompt,
    image_bytes=None,
    mime_type=None
):

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    if not GEMINI_SDK_AVAILABLE:
        raise RuntimeError(
            "Google GenAI SDK is not installed."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    if image_bytes:

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type or "image/jpeg"
        )

        contents = [
            f"{SYSTEM_PROMPT}\n\nUSER:\n{prompt}",
            image_part,
        ]

    else:

        contents = (
            f"{SYSTEM_PROMPT}\n\n"
            f"USER:\n{prompt}"
        )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
    )

    answer = getattr(
        response,
        "text",
        None
    )

    if not answer:
        raise RuntimeError(
            "Gemini returned empty content."
        )

    return answer.strip()


# =========================================================
# 👑 MAIN AI ROUTER
# =========================================================

def ask_ai(prompt):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    errors = []


    # -----------------------------------------------------
    # FORCE GROQ
    # -----------------------------------------------------

    if AI_PROVIDER == "GROQ":

        return openai_request(
            messages,
            GROQ_API_KEY,
            GROQ_BASE_URL,
            GROQ_MODEL,
        )


    # -----------------------------------------------------
    # FORCE OPENAI
    # -----------------------------------------------------

    if AI_PROVIDER == "OPENAI":

        return openai_request(
            messages,
            OPENAI_API_KEY,
            OPENAI_BASE_URL,
            OPENAI_MODEL,
        )


    # -----------------------------------------------------
    # FORCE GEMINI
    # -----------------------------------------------------

    if AI_PROVIDER == "GEMINI":

        return gemini_request(prompt)


    # -----------------------------------------------------
    # AUTO MODE
    #
    # Groq → Gemini → OpenAI
    # -----------------------------------------------------

    if GROQ_API_KEY:

        try:

            return openai_request(
                messages,
                GROQ_API_KEY,
                GROQ_BASE_URL,
                GROQ_MODEL,
            )

        except Exception as e:

            print(
                f"⚠️ Groq failed: {e}"
            )

            errors.append(
                f"Groq: {e}"
            )


    if GEMINI_API_KEY:

        try:

            return gemini_request(
                prompt
            )

        except Exception as e:

            print(
                f"⚠️ Gemini failed: {e}"
            )

            errors.append(
                f"Gemini: {e}"
            )


    if OPENAI_API_KEY:

        try:

            return openai_request(
                messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL,
            )

        except Exception as e:

            print(
                f"⚠️ OpenAI failed: {e}"
            )

            errors.append(
                f"OpenAI: {e}"
            )


    raise RuntimeError(
        "All configured AI providers failed.\n"
        + "\n".join(errors)
    )


# =========================================================
# 👁️ IMAGE / CHART ANALYSIS
# =========================================================

def analyze_image_with_ai(
    image_bytes,
    mime_type,
    prompt
):

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")


    vision_messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },

        {
            "role": "user",

            "content": [

                {
                    "type": "text",
                    "text": prompt,
                },

                {
                    "type": "image_url",

                    "image_url": {
                        "url":
                        f"data:{mime_type};"
                        f"base64,{image_base64}"
                    },
                },

            ],
        },

    ]


    errors = []


    # -----------------------------------------------------
    # GROQ VISION
    # -----------------------------------------------------

    if GROQ_API_KEY:

        try:

            # GPT-OSS 120B is text-focused.
            # Don't pretend it supports image input.

            raise RuntimeError(
                "Groq vision is not enabled "
                "for this Phase 1 configuration."
            )

        except Exception as e:

            errors.append(
                f"Groq Vision: {e}"
            )


    # -----------------------------------------------------
    # GEMINI VISION
    # -----------------------------------------------------

    if GEMINI_API_KEY:

        try:

            return gemini_request(
                prompt,
                image_bytes,
                mime_type,
            )

        except Exception as e:

            errors.append(
                f"Gemini Vision: {e}"
            )


    # -----------------------------------------------------
    # OPENAI VISION
    # -----------------------------------------------------

    if OPENAI_API_KEY:

        try:

            return openai_request(
                vision_messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL,
            )

        except Exception as e:

            errors.append(
                f"OpenAI Vision: {e}"
            )


    raise RuntimeError(
        "All vision providers failed.\n"
        + "\n".join(errors)
    )


# =========================================================
# MARKET DATA
# =========================================================

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)


def get_market_candles(
    symbol,
    interval="15min",
    outputsize=100
):

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing."
        )

    response = requests.get(

        f"{TWELVE_DATA_URL}/time_series",

        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY,
        },

        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error."
            )
        )

    candles = list(
        reversed(
            data.get("values", [])
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            f"Not enough candle data "
            f"for {symbol}."
        )

    return candles


# =========================================================
# TECHNICAL INDICATORS
# =========================================================

def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    result = (
        sum(values[:period])
        / period
    )

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
        ) + result

    return result


def rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = (
            values[i]
            - values[i - 1]
        )

        gains.append(
            max(change, 0)
        )

        losses.append(
            abs(min(change, 0))
        )

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains)
    ):

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


# =========================================================
# MARKET ANALYSIS
# =========================================================

def analyze_market(
    closes,
    highs,
    lows
):

    current_price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    current_rsi = rsi(
        closes,
        14
    )

    recent_high = max(
        highs[-20:]
    )

    recent_low = min(
        lows[-20:]
    )

    score = 0

    score += (
        1 if ema9 > ema21
        else -1
    )

    score += (
        1 if ema21 > ema50
        else -1
    )

    score += (
        1 if current_price > ema21
        else -1
    )

    if 50 < current_rsi < 70:
        score += 1

    elif 30 < current_rsi < 50:
        score -= 1


    if score >= 3:

        signal = "BUY"
        direction = "🟢"
        trend = "BULLISH"

    elif score <= -3:

        signal = "SELL"
        direction = "🔴"
        trend = "BEARISH"

    else:

        signal = "WAIT"
        direction = "🟡"
        trend = "NEUTRAL"


    if signal == "BUY":

        risk = abs(
            current_price
            - recent_low
        )

    else:

        risk = abs(
            recent_high
            - current_price
        )


    if risk <= 0:

        risk = (
            current_price
            * 0.005
        )


    if signal == "BUY":

        stop_loss = (
            current_price
            - risk
        )

        tp1 = (
            current_price
            + risk * 1.5
        )

        tp2 = (
            current_price
            + risk * 2.5
        )

    else:

        stop_loss = (
            current_price
            + risk
        )

        tp1 = (
            current_price
            - risk * 1.5
        )

        tp2 = (
            current_price
            - risk * 2.5
        )


    return {

        "price": current_price,

        "signal": signal,

        "direction": direction,

        "trend": trend,

        "rsi": current_rsi,

        "ema9": ema9,

        "ema21": ema21,

        "ema50": ema50,

        "entry": current_price,

        "stop_loss": stop_loss,

        "tp1": tp1,

        "tp2": tp2,

        "strength":
            min(
                90,
                max(
                    50,
                    50 + abs(score) * 10
                )
            ),
    }


def analyze_symbol(
    symbol,
    interval="15min"
):

    candles = get_market_candles(
        symbol,
        interval,
        100
    )

    closes = [
        float(c["close"])
        for c in candles
    ]

    highs = [
        float(c["high"])
        for c in candles
    ]

    lows = [
        float(c["low"])
        for c in candles
    ]

    result = analyze_market(
        closes,
        highs,
        lows
    )

    result["symbol"] = symbol
    result["interval"] = interval

    return result


def format_analysis(
    data,
    title="KING ZARRY AI SIGNAL"
):

    return (

        f"👑 {title}\n\n"

        f"📊 {data['symbol']} "
        f"| {data['interval']}\n\n"

        f"{data['direction']} "
        f"SIGNAL: {data['signal']}\n"

        f"📈 Trend: {data['trend']}\n"

        f"💪 Strength: "
        f"{data['strength']}%\n\n"

        f"💰 Entry: "
        f"${data['entry']:,.2f}\n"

        f"🛑 Stop Loss: "
        f"${data['stop_loss']:,.2f}\n"

        f"🎯 TP1: "
        f"${data['tp1']:,.2f}\n"

        f"🎯 TP2: "
        f"${data['tp2']:,.2f}\n\n"

        f"📊 RSI: "
        f"{data['rsi']:.2f}\n"

        f"EMA9: "
        f"${data['ema9']:,.2f}\n"

        f"EMA21: "
        f"${data['ema21']:,.2f}\n"

        f"EMA50: "
        f"${data['ema50']:,.2f}\n\n"

        "⚠️ Algorithmic analysis only. "
        "Manage risk appropriately."
    )


# =========================================================
# MARKET DETECTION
# =========================================================

def detect_market_and_timeframe(text):

    upper = text.upper()

    symbol = "UNKNOWN"

    markets = {

        "XAU/USD": [
            "XAU/USD",
            "XAUUSD",
            "GOLD",
        ],

        "BTC/USD": [
            "BTC/USD",
            "BTCUSDT",
            "BTC",
        ],

        "ETH/USD": [
            "ETH/USD",
            "ETHUSDT",
            "ETH",
        ],

        "SOL/USD": [
            "SOL/USD",
            "SOLUSDT",
            "SOL",
        ],
    }

    for market, names in markets.items():

        if any(
            name in upper
            for name in names
        ):

            symbol = market
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


def build_chart_prompt(
    symbol,
    timeframe
):

    return f"""
Analyze this market chart screenshot.

Market: {symbol}
Timeframe: {timeframe}

Provide:

1. Market structure
2. Trend
3. Support
4. Resistance
5. Important price levels
6. Possible bullish setup
7. Possible bearish setup
8. Invalidation level
9. Risk considerations

Do not invent prices that are not visible.
Clearly distinguish observation from probability.

Keep the analysis concise and useful.
"""


# =========================================================
# TELEGRAM COMMANDS
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "👑 KING ZARRY AI ONLINE\n\n"

        "I'm ready. Send me a message and "
        "I'll respond.\n\n"

        "Commands:\n"
        "/start - Start the bot\n"
        "/ask <question> - Ask AI\n"
        "/signal - BTC market signal\n\n"

        "You can also send me a chart "
        "for analysis."
    )


async def ask_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = (
        " ".join(
            context.args
        ).strip()
    )

    if not question:

        await update.message.reply_text(
            "Use:\n\n"
            "/ask What is risk management?"
        )

        return


    await update.message.chat.send_action(
        "typing"
    )


    try:

        answer = await asyncio.to_thread(
            ask_ai,
            question
        )

        await send_long_message(
            update.message,
            answer
        )

    except Exception as e:

        print(
            f"❌ /ask ERROR: {e}"
        )

        await update.message.reply_text(
            "❌ King Zarry AI is temporarily "
            "unable to answer. Please try again."
        )


async def signal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.chat.send_action(
        "typing"
    )

    try:

        data = await asyncio.to_thread(
            analyze_symbol,
            "BTC/USD",
            "15min"
        )

        await send_long_message(
            update.message,
            format_analysis(
                data,
                "BTC SIGNAL"
            )
        )

    except Exception as e:

        print(
            f"❌ SIGNAL ERROR: {e}"
        )

        await update.message.reply_text(
            f"❌ Signal error: {e}"
        )


# =========================================================
# NORMAL TEXT
# =========================================================

async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if (
        not update.message
        or not update.message.text
    ):
        return


    user_text = (
        update.message.text.strip()
    )

    print(
        f"💬 Message from "
        f"{update.effective_user.first_name}: "
        f"{user_text}"
    )


    await update.message.chat.send_action(
        "typing"
    )


    try:

        answer = await asyncio.to_thread(
            ask_ai,
            user_text
        )

        await send_long_message(
            update.message,
            answer
        )

    except Exception as e:

        print(
            f"❌ AI MESSAGE ERROR: {e}"
        )

        traceback.print_exc()

        await update.message.reply_text(

            "👑 King Zarry AI is online, "
            "but my AI provider is temporarily "
            "unavailable.\n\n"

            "Please try again in a moment."
        )


# =========================================================
# PHOTO / CHART
# =========================================================

async def photo_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return


    await update.message.chat.send_action(
        "typing"
    )


    try:

        photo = (
            update.message.photo[-1]
        )

        file = await context.bot.get_file(
            photo.file_id
        )

        image_bytes = (
            await file.download_as_bytearray()
        )

        caption = (
            update.message.caption
            or ""
        )

        symbol, timeframe = (
            detect_market_and_timeframe(
                caption
            )
        )

        prompt = build_chart_prompt(
            symbol,
            timeframe
        )

        result = await asyncio.to_thread(

            analyze_image_with_ai,

            bytes(image_bytes),

            "image/jpeg",

            prompt
        )

        await send_long_message(
            update.message,
            result
        )


    except Exception as e:

        print(
            f"❌ VISION ERROR: {e}"
        )

        traceback.print_exc()

        await update.message.reply_text(

            "👑 I couldn't analyze that "
            "image right now.\n\n"

            "Please try sending the chart "
            "again."
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update,
    context
):

    print(
        "❌ TELEGRAM ERROR:"
    )

    print(
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "============================================================"
    )

    print(
        "👑 KING ZARRY AI TELEGRAM"
    )

    print(
        "============================================================"
    )

    print(
        f"🤖 AI Provider: {AI_PROVIDER}"
    )

    print(
        f"🧠 Groq Model: {GROQ_MODEL}"
    )

    print(
        f"🧠 Gemini Model: {GEMINI_MODEL}"
    )

    print(
        f"🔑 Groq API: "
        f"{'FOUND' if GROQ_API_KEY else 'NOT FOUND'}"
    )

    print(
        f"🔑 Gemini API: "
        f"{'FOUND' if GEMINI_API_KEY else 'NOT FOUND'}"
    )

    print(
        f"🔑 OpenAI API: "
        f"{'FOUND' if OPENAI_API_KEY else 'NOT FOUND'}"
    )

    print(
        "============================================================"
    )


    application = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )


    # Commands

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "ask",
            ask_command
        )
    )

    application.add_handler(
        CommandHandler(
            "signal",
            signal_command
        )
    )


    # Images

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_message
        )
    )


    # Normal text

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_message
        )
    )


    application.add_error_handler(
        error_handler
    )


    print(
        "📡 Telegram polling active."
    )

    print(
        "👑 KING ZARRY AI TELEGRAM READY"
    )


    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
