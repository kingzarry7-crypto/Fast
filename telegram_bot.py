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
# 👑 KING ZARRY AI
# TELEGRAM BOT
#
# Gemini + OpenAI
# AUTO provider switching
# Vision / chart analysis
# Twelve Data trading analysis
# Normal AI chat
# =========================================================


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

# AUTO / GEMINI / OPENAI
AI_PROVIDER = os.environ.get(
    "AI_PROVIDER",
    "AUTO"
).upper().strip()

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OPENAI_MODEL = os.environ.get(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

TWELVE_DATA_URL = "https://api.twelvedata.com"

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


# =========================================================
# STARTUP VALIDATION
# =========================================================

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing."
    )

if not GEMINI_API_KEY and not OPENAI_API_KEY:
    raise RuntimeError(
        "No AI provider is configured. "
        "Add GEMINI_API_KEY and/or OPENAI_API_KEY."
    )

if AI_PROVIDER not in {
    "AUTO",
    "GEMINI",
    "OPENAI",
}:
    raise RuntimeError(
        "AI_PROVIDER must be AUTO, GEMINI, or OPENAI."
    )


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
# GENERAL AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant for the
King Zarry community.

You can help with:

- Bitcoin
- Ethereum
- Solana
- Cryptocurrency
- Forex
- Gold / XAUUSD
- Trading
- Technical analysis
- Market structure
- Risk management
- Programming
- Coding
- Artificial intelligence
- Technology
- Business
- Education
- General questions
- Casual conversation

IMPORTANT TRADING RULES:

Never guarantee profit.

Never claim a trade is certain to win.

When discussing markets, clearly distinguish:

1. Confirmed information
2. Probable scenarios
3. Uncertain scenarios

If live market data has not been provided,
do not pretend that you have live prices.

If market data is supplied by the trading engine,
use that data.

When discussing trade setups:

- Explain the reasoning.
- Give invalidation.
- Discuss risk.
- Avoid overconfidence.

Keep answers useful and reasonably concise.

You are King Zarry AI 👑.
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


def normalize_timeframe(timeframe):

    timeframe = (
        timeframe
        .lower()
        .strip()
    )

    return TIMEFRAME_MAP.get(
        timeframe,
        timeframe
    )


# =========================================================
# TELEGRAM MESSAGE LIMIT
# =========================================================

async def send_long_message(
    message,
    text
):

    if not text:

        text = (
            "❌ King Zarry AI returned "
            "an empty response."
        )

    # Telegram supports messages up to
    # approximately 4096 characters.
    chunk_size = 3900

    chunks = [
        text[i:i + chunk_size]
        for i in range(
            0,
            len(text),
            chunk_size
        )
    ]

    for chunk in chunks:

        await message.reply_text(
            chunk
        )


# =========================================================
# GEMINI TEXT
# =========================================================

def gemini_text(prompt):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    if not GEMINI_SDK_AVAILABLE:

        raise RuntimeError(
            "Gemini SDK is not installed. "
            "Add google-genai to requirements.txt."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=[

            types.Content(
                role="user",
                parts=[

                    types.Part.from_text(
                        text=(
                            SYSTEM_PROMPT
                            + "\n\nUSER:\n"
                            + prompt
                        )
                    )

                ],
            )

        ],
    )

    answer = getattr(
        response,
        "text",
        None
    )

    if not answer:

        raise RuntimeError(
            "Gemini returned no text."
        )

    return answer.strip()


# =========================================================
# GEMINI VISION
# =========================================================

def gemini_vision(
    image_bytes,
    mime_type,
    prompt
):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    if not GEMINI_SDK_AVAILABLE:

        raise RuntimeError(
            "Gemini SDK is not installed."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    image_part = (
        types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
    )

    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=[

            SYSTEM_PROMPT
            + "\n\n"
            + prompt,

            image_part,

        ],
    )

    answer = getattr(
        response,
        "text",
        None
    )

    if not answer:

        raise RuntimeError(
            "Gemini returned no vision response."
        )

    return answer.strip()


# =========================================================
# OPENAI TEXT
# =========================================================

def openai_request(
    messages
):

    if not OPENAI_API_KEY:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    headers = {

        "Authorization":
            f"Bearer {OPENAI_API_KEY}",

        "Content-Type":
            "application/json",

    }

    payload = {

        "model":
            OPENAI_MODEL,

        "messages":
            messages,

        "temperature":
            0.3,

        "max_tokens":
            1500,

    }

    response = requests.post(

        OPENAI_URL,

        headers=headers,

        json=payload,

        timeout=120,

    )

    if response.status_code != 200:

        try:

            error_data = (
                response.json()
            )

        except Exception:

            error_data = (
                response.text
            )

        raise RuntimeError(
            "OpenAI API error: "
            f"{error_data}"
        )

    data = response.json()

    try:

        answer = (
            data["choices"][0]
            ["message"]["content"]
        )

    except Exception:

        raise RuntimeError(
            "Unexpected OpenAI response: "
            f"{data}"
        )

    if isinstance(
        answer,
        list
    ):

        pieces = []

        for item in answer:

            if isinstance(
                item,
                dict
            ):

                if item.get(
                    "type"
                ) == "text":

                    pieces.append(
                        item.get(
                            "text",
                            ""
                        )
                    )

        answer = "\n".join(
            pieces
        )

    if not answer:

        raise RuntimeError(
            "OpenAI returned no text."
        )

    return answer.strip()


# =========================================================
# OPENAI VISION
# =========================================================

def openai_vision(
    image_bytes,
    mime_type,
    prompt
):

    if not OPENAI_API_KEY:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    image_base64 = (
        base64.b64encode(
            image_bytes
        ).decode("utf-8")
    )

    messages = [

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
                            f"base64,"
                            f"{image_base64}"

                    },

                },

            ],

        },

    ]

    return openai_request(
        messages
    )


# =========================================================
# PROVIDER SELECTION
# =========================================================

def ask_ai(
    prompt
):

    # -----------------------------------------------------
    # GEMINI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "GEMINI":

        return gemini_text(
            prompt
        )

    # -----------------------------------------------------
    # OPENAI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "OPENAI":

        return openai_request([

            {
                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT,

            },

            {
                "role":
                    "user",

                "content":
                    prompt,

            },

        ])

    # -----------------------------------------------------
    # AUTO
    # Gemini first, OpenAI fallback
    # -----------------------------------------------------

    errors = []

    if GEMINI_API_KEY:

        try:

            return gemini_text(
                prompt
            )

        except Exception as e:

            errors.append(
                f"Gemini: {e}"
            )

    if OPENAI_API_KEY:

        try:

            return openai_request([

                {
                    "role":
                        "system",

                    "content":
                        SYSTEM_PROMPT,

                },

                {
                    "role":
                        "user",

                    "content":
                        prompt,

                },

            ])

        except Exception as e:

            errors.append(
                f"OpenAI: {e}"
            )

    raise RuntimeError(
        "All AI providers failed. "
        + " | ".join(errors)
    )


# =========================================================
# VISION PROVIDER
# =========================================================

def analyze_image_with_ai(
    image_bytes,
    mime_type,
    prompt
):

    errors = []

    # -----------------------------------------------------
    # GEMINI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "GEMINI":

        return gemini_vision(
            image_bytes,
            mime_type,
            prompt
        )

    # -----------------------------------------------------
    # OPENAI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "OPENAI":

        return openai_vision(
            image_bytes,
            mime_type,
            prompt
        )

    # -----------------------------------------------------
    # AUTO
    # -----------------------------------------------------

    if GEMINI_API_KEY:

        try:

            return gemini_vision(
                image_bytes,
                mime_type,
                prompt
            )

        except Exception as e:

            errors.append(
                f"Gemini vision: {e}"
            )

    if OPENAI_API_KEY:

        try:

            return openai_vision(
                image_bytes,
                mime_type,
                prompt
            )

        except Exception as e:

            errors.append(
                f"OpenAI vision: {e}"
            )

    raise RuntimeError(
        "All vision providers failed. "
        + " | ".join(errors)
    )


# =========================================================
# TWELVE DATA
# =========================================================

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

            "symbol":
                symbol,

            "interval":
                interval,

            "outputsize":
                outputsize,

            "apikey":
                TWELVE_DATA_API_KEY,

        },

        timeout=20,

    )

    response.raise_for_status()

    data = response.json()

    if data.get(
        "status"
    ) == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error."
            )
        )

    if "values" not in data:

        raise RuntimeError(
            "No candle data returned "
            f"for {symbol}: {data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            f"Not enough data returned "
            f"for {symbol}."
        )

    return candles


def get_market_price(
    symbol
):

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing."
        )

    response = requests.get(

        f"{TWELVE_DATA_URL}/price",

        params={

            "symbol":
                symbol,

            "apikey":
                TWELVE_DATA_API_KEY,

        },

        timeout=20,

    )

    response.raise_for_status()

    data = response.json()

    if data.get(
        "status"
    ) == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error."
            )
        )

    if "price" not in data:

        raise RuntimeError(
            f"Unexpected price response: "
            f"{data}"
        )

    return float(
        data["price"]
    )


# =========================================================
# EMA
# =========================================================

def ema(
    values,
    period
):

    if len(values) < period:

        return None

    multiplier = (
        2 / (period + 1)
    )

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


# =========================================================
# RSI
# =========================================================

def rsi(
    values,
    period=14
):

    if len(values) < (
        period + 1
    ):

        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values)
    ):

        change = (
            values[i]
            - values[i - 1]
        )

        if change > 0:

            gains.append(
                change
            )

            losses.append(0)

        else:

            gains.append(0)

            losses.append(
                abs(change)
            )

    avg_gain = (
        sum(
            gains[:period]
        ) / period
    )

    avg_loss = (
        sum(
            losses[:period]
        ) / period
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

    rs = (
        avg_gain
        / avg_loss
    )

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

    if len(closes) < 50:

        raise RuntimeError(
            "Not enough market data."
        )

    current_price = closes[-1]

    ema9 = ema(
        closes,
        9
    )

    ema21 = ema(
        closes,
        21
    )

    ema50 = ema(
        closes,
        50
    )

    current_rsi = rsi(
        closes,
        14
    )

    if (
        ema9 is None
        or ema21 is None
        or ema50 is None
        or current_rsi is None
    ):

        raise RuntimeError(
            "Indicators could not be calculated."
        )

    recent_high = max(
        highs[-20:]
    )

    recent_low = min(
        lows[-20:]
    )

    score = 0

    # EMA 9 / 21

    if ema9 > ema21:

        score += 1

    else:

        score -= 1

    # EMA 21 / 50

    if ema21 > ema50:

        score += 1

    else:

        score -= 1

    # Price / EMA 21

    if current_price > ema21:

        score += 1

    else:

        score -= 1

    # RSI

    if 50 < current_rsi < 70:

        score += 1

    elif 30 < current_rsi < 50:

        score -= 1

    # Signal

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

    entry = current_price

    # Risk management

    if signal == "BUY":

        risk = (
            entry
            - recent_low
        )

        if risk <= 0:

            risk = (
                entry * 0.005
            )

        stop_loss = (
            entry - risk
        )

        tp1 = (
            entry
            + risk * 1.5
        )

        tp2 = (
            entry
            + risk * 2.5
        )

    elif signal == "SELL":

        risk = (
            recent_high
            - entry
        )

        if risk <= 0:

            risk = (
                entry * 0.005
            )

        stop_loss = (
            entry + risk
        )

        tp1 = (
            entry
            - risk * 1.5
        )

        tp2 = (
            entry
            - risk * 2.5
        )

    else:

        stop_loss = recent_low
        tp1 = recent_high
        tp2 = recent_high

    strength = min(
        90,
        max(
            50,
            50 + abs(score) * 10
        )
    )

    return {

        "price":
            current_price,

        "signal":
            signal,

        "direction":
            direction,

        "trend":
            trend,

        "rsi":
            current_rsi,

        "ema9":
            ema9,

        "ema21":
            ema21,

        "ema50":
            ema50,

        "entry":
            entry,

        "stop_loss":
            stop_loss,

        "tp1":
            tp1,

        "tp2":
            tp2,

        "strength":
            strength,

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


# =========================================================
# FORMAT ANALYSIS
# =========================================================

def format_analysis(
    data,
    title="KING ZARRY AI SIGNAL"
):

    return (

        f"👑 *{title}*\n\n"

        f"📊 *{data['symbol']}*\n"

        f"⏱ Timeframe: "
        f"*{data['interval']}*\n\n"

        f"{data['direction']} "
        f"*SIGNAL: {data['signal']}*\n"

        f"📈 Trend: "
        f"*{data['trend']}*\n"

        f"🔥 Analysis Strength: "
        f"*{data['strength']}%*\n\n"

        f"💰 Entry: "
        f"`${data['entry']:,.2f}`\n"

        f"🛑 Stop Loss: "
        f"`${data['stop_loss']:,.2f}`\n"

        f"🎯 TP1: "
        f"`${data['tp1']:,.2f}`\n"

        f"🎯 TP2: "
        f"`${data['tp2']:,.2f}`\n\n"

        f"📊 RSI: "
        f"*{data['rsi']:.2f}*\n"

        f"EMA 9: "
        f"`${data['ema9']:,.2f}`\n"

        f"EMA 21: "
        f"`${data['ema21']:,.2f}`\n"

        f"EMA 50: "
        f"`${data['ema50']:,.2f}`\n\n"

        "⚠️ Algorithmic analysis only. "
        "No signal guarantees profit."

    )


# =========================================================
# MARKET / TIMEFRAME DETECTION
# =========================================================

def detect_market_and_timeframe(
    text
):

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

        "EUR/USD": [

            "EUR/USD",
            "EURUSD",

        ],

        "GBP/USD": [

            "GBP/USD",
            "GBPUSD",

        ],

    }

    for market, names in markets.items():

        for name in names:

            if name in upper:

                symbol = market

                break

        if symbol != "UNKNOWN":

            break

    timeframe = "15m"

    match = re.search(

        r"\b("
        r"1m|"
        r"5m|"
        r"15m|"
        r"30m|"
        r"1h|"
        r"2h|"
        r"4h|"
        r"1d"
        r")\b",

        text.lower()

    )

    if match:

        timeframe = (
            match.group(1)
        )

    return symbol, timeframe


# =========================================================
# CHART PROMPT
# =========================================================

def build_chart_prompt(
    symbol,
    timeframe
):

    return f"""
Analyze this trading chart screenshot.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information actually visible
in the image.

Carefully inspect:

1. Overall trend
2. Market structure
3. Higher highs
4. Higher lows
5. Lower highs
6. Lower lows
7. Support
8. Resistance
9. Breakout
10. Breakdown
11. Candlestick behaviour
12. EMA if visible
13. RSI if visible
14. Possible BUY setup
15. Possible SELL setup
16. Entry area
17. Invalidation / stop area
18. TP1
19. TP2
20. Reason for the setup

Return:

👑 KING ZARRY AI CHART ANALYSIS

📊 Market:
⏱ Timeframe:

🎯 Signal: BUY / SELL / WAIT

📈 Trend:

🏗 Market Structure:

🟢 Support:

🔴 Resistance:

💰 Entry Zone:

🛑 Invalidation / Stop:

🎯 TP1:
🎯 TP2:

📊 Indicators:

🧠 Reason:

⚠️ Risk Warning:

IMPORTANT:

Do not invent prices that cannot be read.

If exact prices are unclear,
describe the area instead.

Never guarantee profit.

If the chart does not contain enough information,
say WAIT and explain what is missing.
"""


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "👑 *WELCOME TO KING ZARRY AI*\n\n"

        "🤖 Your AI assistant is ONLINE.\n\n"

        "*TRADING COMMANDS*\n\n"

        "📊 /signal - BTC 15M signal\n"

        "₿ /btc - Bitcoin analysis\n"

        "🟡 /gold - Gold analysis\n"

        "🪙 /crypto - Crypto prices\n"

        "📈 /analyze - Market analysis\n\n"

        "*AI COMMANDS*\n\n"

        "🧠 /ask - Ask anything\n"

        "📸 Send a chart image - "
        "AI will analyze it\n\n"

        "💬 You can also simply send me "
        "a normal message.\n\n"

        "👑 *King Zarry AI is ready.*",

        parse_mode="Markdown"

    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "👑 *KING ZARRY AI COMMANDS*\n\n"

        "📊 /signal - BTC signal\n"

        "₿ /btc - BTC analysis\n"

        "🟡 /gold - Gold analysis\n"

        "🪙 /crypto - Crypto prices\n"

        "📈 /analyze BTC/USD 15m\n"

        "🧠 /ask your question\n\n"

        "📸 *Chart Analysis*\n"
        "Send a screenshot/chart image "
        "with an optional caption such as:\n\n"

        "`XAUUSD 15m`\n\n"

        "💬 Normal messages are also "
        "answered automatically.",

        parse_mode="Markdown"

    )


# =========================================================
# /ASK
# =========================================================

async def ask_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    question = " ".join(
        context.args
    ).strip()

    if not question:

        await update.message.reply_text(

            "🧠 Usage:\n\n"
            "`/ask What is market structure?`",

            parse_mode="Markdown"

        )

        return

    try:

        await update.message.chat.send_action(
            "typing"
        )

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
            "❌ ASK ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ AI error:\n"
            f"`{str(e)[:1500]}`",

            parse_mode="Markdown"

        )


# =========================================================
# /SIGNAL
# =========================================================

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

                "KING ZARRY AI BTC SIGNAL"

            )

        )

    except Exception as e:

        print(
            "❌ SIGNAL ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ BTC analysis failed:\n"
            f"`{str(e)[:1000]}`",

            parse_mode="Markdown"

        )


# =========================================================
# /BTC
# =========================================================

async def btc_command(
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

                "KING ZARRY AI BTC ANALYSIS"

            )

        )

    except Exception as e:

        print(
            "❌ BTC ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ BTC analysis failed:\n"
            f"`{str(e)[:1000]}`",

            parse_mode="Markdown"

        )


# =========================================================
# /GOLD
# =========================================================

async def gold_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.chat.send_action(
        "typing"
    )

    try:

        data = await asyncio.to_thread(

            analyze_symbol,

            "XAU/USD",

            "15min"

        )

        await send_long_message(

            update.message,

            format_analysis(

                data,

                "KING ZARRY AI GOLD SIGNAL"

            )

        )

    except Exception as e:

        print(
            "❌ GOLD ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ Gold analysis failed:\n"
            f"`{str(e)[:1000]}`",

            parse_mode="Markdown"

        )


# =========================================================
# /CRYPTO
# =========================================================

async def crypto_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.chat.send_action(
        "typing"
    )

    try:

        btc_price = await asyncio.to_thread(
            get_market_price,
            "BTC/USD"
        )

        eth_price = await asyncio.to_thread(
            get_market_price,
            "ETH/USD"
        )

        sol_price = await asyncio.to_thread(
            get_market_price,
            "SOL/USD"
        )

        await update.message.reply_text(

            "🪙 *KING ZARRY AI CRYPTO MARKET*\n\n"

            f"₿ BTC/USD: "
            f"`${btc_price:,.2f}`\n"

            f"Ξ ETH/USD: "
            f"`${eth_price:,.2f}`\n"

            f"◎ SOL/USD: "
            f"`${sol_price:,.2f}`",

            parse_mode="Markdown"

        )

    except Exception as e:

        print(
            "❌ CRYPTO ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ Crypto data failed:\n"
            f"`{str(e)[:1000]}`",

            parse_mode="Markdown"

        )


# =========================================================
# /ANALYZE
# =========================================================

async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(

            "📈 Usage:\n\n"
            "`/analyze BTC/USD 15m`\n\n"
            "`/analyze XAU/USD 1h`",

            parse_mode="Markdown"

        )

        return

    symbol = (
        context.args[0]
        .upper()
        .strip()
    )

    timeframe = "15m"

    if len(context.args) >= 2:

        timeframe = (
            context.args[1]
            .lower()
            .strip()
        )

    interval = normalize_timeframe(
        timeframe
    )

    await update.message.chat.send_action(
        "typing"
    )

    try:

        data = await asyncio.to_thread(

            analyze_symbol,

            symbol,

            interval

        )

        await send_long_message(

            update.message,

            format_analysis(

                data,

                "KING ZARRY AI MARKET ANALYSIS"

            )

        )

    except Exception as e:

        print(
            "❌ ANALYZE ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ Market analysis failed:\n"
            f"`{str(e)[:1000]}`",

            parse_mode="Markdown"

        )


# =========================================================
# NORMAL TEXT MESSAGES
# =========================================================

async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return

    text = (
        update.message.text
        or ""
    ).strip()

    if not text:

        return

    print(
        f"💬 TELEGRAM MESSAGE | "
        f"{update.effective_user.id} | "
        f"{text!r}"
    )

    try:

        await update.message.chat.send_action(
            "typing"
        )

        answer = await asyncio.to_thread(

            ask_ai,

            text

        )

        await send_long_message(

            update.message,

            answer

        )

    except Exception as e:

        print(
            "❌ TEXT AI ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ *King Zarry AI could not respond.*\n\n"
            f"`{str(e)[:1500]}`",

            parse_mode="Markdown"

        )


# =========================================================
# PHOTO / CHART ANALYSIS
# =========================================================

async def photo_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return

    try:

        await update.message.chat.send_action(
            "typing"
        )

        photo = (
            update.message.photo[-1]
        )

        # Telegram photo is already hosted.
        file = await context.bot.get_file(
            photo.file_id
        )

        image_bytes = (
            await file.download_as_bytearray()
        )

        caption = (
            update.message.caption
            or ""
        ).strip()

        symbol, timeframe = (
            detect_market_and_timeframe(
                caption
            )
        )

        prompt = build_chart_prompt(
            symbol,
            timeframe
        )

        print(
            f"📸 TELEGRAM CHART | "
            f"Market={symbol} | "
            f"Timeframe={timeframe}"
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
            "❌ TELEGRAM VISION ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ I couldn't analyze that chart.\n\n"
            f"`{str(e)[:1500]}`",

            parse_mode="Markdown"

        )


# =========================================================
# DOCUMENT IMAGES
# =========================================================

async def document_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:

        return

    document = (
        update.message.document
    )

    if not document:

        return

    mime_type = (
        document.mime_type
        or ""
    )

    if not mime_type.startswith(
        "image/"
    ):

        return

    try:

        await update.message.chat.send_action(
            "typing"
        )

        file = await context.bot.get_file(
            document.file_id
        )

        image_bytes = (
            await file.download_as_bytearray()
        )

        caption = (
            update.message.caption
            or ""
        ).strip()

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

            mime_type,

            prompt

        )

        await send_long_message(

            update.message,

            result

        )

    except Exception as e:

        print(
            "❌ DOCUMENT VISION ERROR:",
            repr(e)
        )

        await update.message.reply_text(

            "❌ Image analysis failed:\n"
            f"`{str(e)[:1500]}`",

            parse_mode="Markdown"

        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "❌ TELEGRAM ERROR:",
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print(
        "👑 ======================================="
    )

    print(
        "👑 KING ZARRY AI TELEGRAM BOT"
    )

    print(
        "👑 ======================================="
    )

    print(
        "📱 Telegram: ENABLED"
    )

    print(
        f"🧠 Provider mode: {AI_PROVIDER}"
    )

    print(
        f"🤖 Gemini model: {GEMINI_MODEL}"
    )

    print(
        f"🔵 OpenAI model: {OPENAI_MODEL}"
    )

    print(
        "📸 Multi-provider vision loaded."
    )

    print(
        "📊 Trading analysis loaded."
    )

    print(
        "💬 Telegram AI chat loaded."
    )

    print(
        "📡 Telegram polling starting..."
    )

    # -----------------------------------------------------
    # BUILD APPLICATION
    # -----------------------------------------------------

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
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

    application.add_handler(
        CommandHandler(
            "btc",
            btc_command
        )
    )

    application.add_handler(
        CommandHandler(
            "gold",
            gold_command
        )
    )

    application.add_handler(
        CommandHandler(
            "crypto",
            crypto_command
        )
    )

    application.add_handler(
        CommandHandler(
            "analyze",
            analyze_command
        )
    )

    # -----------------------------------------------------
    # IMAGES
    # -----------------------------------------------------

    application.add_handler(

        MessageHandler(

            filters.PHOTO,

            photo_message

        )

    )

    # -----------------------------------------------------
    # IMAGE DOCUMENTS
    # -----------------------------------------------------

    application.add_handler(

        MessageHandler(

            filters.Document.IMAGE,

            document_message

        )

    )

    # -----------------------------------------------------
    # NORMAL TEXT
    # -----------------------------------------------------

    application.add_handler(

        MessageHandler(

            filters.TEXT
            & ~filters.COMMAND,

            text_message

        )

    )

    # -----------------------------------------------------
    # ERROR HANDLER
    # -----------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    print()
    print(
        "👑 ======================================="
    )

    print(
        "🟢 KING ZARRY AI TELEGRAM IS READY"
    )

    print(
        "📱 Send /start to your Telegram bot."
    )

    print(
        "💬 Normal messages are enabled."
    )

    print(
        "📸 Chart vision is enabled."
    )

    print(
        "📊 Trading analysis is enabled."
    )

    print(
        "👑 ======================================="
    )

    # -----------------------------------------------------
    # START TELEGRAM POLLING
    # -----------------------------------------------------

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
