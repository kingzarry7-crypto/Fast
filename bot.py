import os
import base64
import asyncio
import requests
import discord
from discord import app_commands
import re


# =========================================================
# 👑 KING ZARRY AI
# MULTI-PROVIDER AI DISCORD BOT
#
# PROVIDERS:
# 1. GOOGLE GEMINI
# 2. HUGGING FACE
# 3. OPENAI
#
# AUTOMATIC FALLBACK:
# GEMINI -> HUGGING FACE -> OPENAI
# =========================================================


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

DISCORD_BOT_TOKEN = os.environ.get(
    "DISCORD_BOT_TOKEN"
)

DISCORD_GUILD_ID = os.environ.get(
    "DISCORD_GUILD_ID"
)

TWELVE_DATA_API_KEY = os.environ.get(
    "TWELVE_DATA_API_KEY"
)

# ---------------------------------------------------------
# GOOGLE GEMINI
# ---------------------------------------------------------

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

# ---------------------------------------------------------
# HUGGING FACE
# ---------------------------------------------------------

HF_TOKEN = os.environ.get(
    "HF_TOKEN"
)

HF_MODEL = os.environ.get(
    "HF_MODEL",
    "Qwen/Qwen2.5-VL-3B-Instruct"
)

# ---------------------------------------------------------
# OPENAI
# ---------------------------------------------------------

OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY"
)

OPENAI_MODEL = os.environ.get(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)


# =========================================================
# API URLS
# =========================================================

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)

HF_URL = (
    "https://router.huggingface.co/v1/chat/completions"
)

OPENAI_URL = (
    "https://api.openai.com/v1/chat/completions"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)


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

    if not timeframe:

        return "15min"

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
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant inside the
King Zarry Discord community.

You can discuss:

- Cryptocurrency
- Bitcoin
- Ethereum
- Solana
- Forex
- Gold / XAUUSD
- Technical analysis
- Trading concepts
- Risk management
- Market structure
- Programming
- Coding
- Artificial intelligence
- Technology
- Business
- General questions
- Casual conversation
- Education
- Everyday topics

Your personality should be:

- Helpful
- Intelligent
- Clear
- Friendly
- Practical
- Confident but not reckless
- Concise unless more detail is requested

Use emojis naturally when appropriate.

IMPORTANT TRADING RULES:

Never guarantee that a trade will win.

Never claim certainty about future market movement.

When discussing a market, distinguish between:

1. CONFIRMED
2. PROBABLE
3. UNCERTAIN

If the user asks for a trade setup:

- Explain the reasoning.
- Give entry logic.
- Give invalidation logic.
- Discuss stop loss.
- Discuss take profit.
- Mention risk/reward when possible.
- Never promise profit.

Never pretend to have live market data unless
live market data has actually been supplied.

If live data is supplied by the bot,
you may analyze it.

You are King Zarry AI 👑.
"""


# =========================================================
# DISCORD MESSAGE LIMIT
# =========================================================

async def send_long_message(
    destination,
    text,
    reply=False
):

    if not text:

        text = (
            "❌ AI returned an empty response."
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

        if reply:

            await destination.reply(
                chunk,
                mention_author=False
            )

            reply = False

        else:

            await destination.channel.send(
                chunk
            )


# =========================================================
# GEMINI
# =========================================================

def gemini_request(
    prompt,
    image_bytes=None,
    image_mime="image/png"
):

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    url = (
        f"{GEMINI_URL}/"
        f"{GEMINI_MODEL}:generateContent"
    )

    headers = {

        "Content-Type":
            "application/json",

        "x-goog-api-key":
            GEMINI_API_KEY,

    }

    parts = [

        {
            "text": prompt
        }

    ]

    if image_bytes:

        image_base64 = (
            base64.b64encode(
                image_bytes
            ).decode("utf-8")
        )

        parts.append({

            "inline_data": {

                "mime_type":
                    image_mime,

                "data":
                    image_base64,

            }

        })

    payload = {

        "system_instruction": {

            "parts": [

                {
                    "text":
                        SYSTEM_PROMPT
                }

            ]

        },

        "contents": [

            {

                "role": "user",

                "parts": parts,

            }

        ],

        "generationConfig": {

            "temperature": 0.3,

            "maxOutputTokens": 1600,

        },

    }

    response = requests.post(

        url,

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
            "Gemini API error: "
            f"{error_data}"
        )

    data = response.json()

    try:

        candidates = (
            data["candidates"]
        )

        if not candidates:

            raise RuntimeError(
                "Gemini returned no candidates."
            )

        parts = (
            candidates[0]
            ["content"]
            ["parts"]
        )

        answer_parts = []

        for part in parts:

            if "text" in part:

                answer_parts.append(
                    part["text"]
                )

        answer = "\n".join(
            answer_parts
        ).strip()

    except Exception:

        raise RuntimeError(
            "Unexpected Gemini response: "
            f"{data}"
        )

    if not answer:

        raise RuntimeError(
            "Gemini returned no text."
        )

    return answer


# =========================================================
# HUGGING FACE
# =========================================================

def hf_request(
    messages
):

    if not HF_TOKEN:

        raise RuntimeError(
            "HF_TOKEN is not configured."
        )

    headers = {

        "Authorization":
            f"Bearer {HF_TOKEN}",

        "Content-Type":
            "application/json",

    }

    payload = {

        "model":
            HF_MODEL,

        "messages":
            messages,

        "temperature":
            0.3,

        "max_tokens":
            1600,

    }

    response = requests.post(

        HF_URL,

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
            "Hugging Face API error: "
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
            "Unexpected Hugging Face response: "
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
            "Hugging Face returned no text."
        )

    return answer.strip()


# =========================================================
# OPENAI
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
            1600,

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

    if not answer:

        raise RuntimeError(
            "OpenAI returned no text."
        )

    return answer.strip()


# =========================================================
# MULTI-PROVIDER AI ROUTER
# =========================================================

def ask_ai(
    prompt
):

    errors = []

    # -----------------------------------------------------
    # 1. GEMINI
    # -----------------------------------------------------

    if GEMINI_API_KEY:

        try:

            print(
                "🟢 AI PROVIDER: GEMINI"
            )

            return gemini_request(
                prompt
            )

        except Exception as e:

            print(
                "⚠️ Gemini failed:",
                repr(e)
            )

            errors.append(
                f"Gemini: {str(e)[:500]}"
            )

    # -----------------------------------------------------
    # 2. HUGGING FACE
    # -----------------------------------------------------

    if HF_TOKEN:

        try:

            print(
                "🟣 AI PROVIDER: HUGGING FACE"
            )

            messages = [

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

            ]

            return hf_request(
                messages
            )

        except Exception as e:

            print(
                "⚠️ Hugging Face failed:",
                repr(e)
            )

            errors.append(
                f"Hugging Face: "
                f"{str(e)[:500]}"
            )

    # -----------------------------------------------------
    # 3. OPENAI
    # -----------------------------------------------------

    if OPENAI_API_KEY:

        try:

            print(
                "🔵 AI PROVIDER: OPENAI"
            )

            messages = [

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

            ]

            return openai_request(
                messages
            )

        except Exception as e:

            print(
                "⚠️ OpenAI failed:",
                repr(e)
            )

            errors.append(
                f"OpenAI: "
                f"{str(e)[:500]}"
            )

    # -----------------------------------------------------
    # NO PROVIDER
    # -----------------------------------------------------

    raise RuntimeError(

        "No AI provider is available.\n"

        "Add at least one of:\n"

        "GEMINI_API_KEY\n"
        "HF_TOKEN\n"
        "OPENAI_API_KEY\n\n"

        + "\n".join(errors)

    )


# =========================================================
# AI VISION ROUTER
# =========================================================

def analyze_chart_image(
    image_bytes,
    symbol="UNKNOWN",
    timeframe="15m",
    image_mime="image/png"
):

    prompt = f"""
Analyze this trading chart screenshot.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information actually visible in the image.

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

👑 **KING ZARRY AI CHART ANALYSIS**

📊 Market:
⏱ Timeframe:

🎯 Signal: BUY / SELL / WAIT
📈 Trend:

🏗 **Market Structure:**

🟢 **Support:**

🔴 **Resistance:**

💰 **Entry Zone:**

🛑 **Invalidation / Stop:**

🎯 **TP1:**

🎯 **TP2:**

📊 **Indicators:**

🧠 **Reason:**

⚠️ **Risk Warning:**

IMPORTANT:

Do not invent prices.

If exact prices cannot be clearly read,
describe the zone instead.

Never guarantee profit.

If there is not enough information,
return WAIT and explain why.
"""

    # -----------------------------------------------------
    # GEMINI VISION FIRST
    # -----------------------------------------------------

    if GEMINI_API_KEY:

        try:

            print(
                "📸 VISION PROVIDER: GEMINI"
            )

            return gemini_request(

                prompt,

                image_bytes,

                image_mime

            )

        except Exception as e:

            print(
                "⚠️ Gemini vision failed:",
                repr(e)
            )

    # -----------------------------------------------------
    # HUGGING FACE VISION
    # -----------------------------------------------------

    if HF_TOKEN:

        try:

            print(
                "📸 VISION PROVIDER: HUGGING FACE"
            )

            image_base64 = (
                base64.b64encode(
                    image_bytes
                ).decode("utf-8")
            )

            messages = [

                {

                    "role":
                        "system",

                    "content":
                        SYSTEM_PROMPT,

                },

                {

                    "role":
                        "user",

                    "content": [

                        {

                            "type":
                                "text",

                            "text":
                                prompt,

                        },

                        {

                            "type":
                                "image_url",

                            "image_url": {

                                "url":
                                    (
                                        f"data:{image_mime};"
                                        f"base64,"
                                        f"{image_base64}"
                                    )

                            },

                        },

                    ],

                },

            ]

            return hf_request(
                messages
            )

        except Exception as e:

            print(
                "⚠️ Hugging Face vision failed:",
                repr(e)
            )

    # -----------------------------------------------------
    # OPENAI VISION
    # -----------------------------------------------------

    if OPENAI_API_KEY:

        try:

            print(
                "📸 VISION PROVIDER: OPENAI"
            )

            image_base64 = (
                base64.b64encode(
                    image_bytes
                ).decode("utf-8")
            )

            messages = [

                {

                    "role":
                        "system",

                    "content":
                        SYSTEM_PROMPT,

                },

                {

                    "role":
                        "user",

                    "content": [

                        {

                            "type":
                                "text",

                            "text":
                                prompt,

                        },

                        {

                            "type":
                                "image_url",

                            "image_url": {

                                "url":
                                    (
                                        f"data:{image_mime};"
                                        f"base64,"
                                        f"{image_base64}"
                                    )

                            },

                        },

                    ],

                },

            ]

            return openai_request(
                messages
            )

        except Exception as e:

            print(
                "⚠️ OpenAI vision failed:",
                repr(e)
            )

    raise RuntimeError(
        "No vision-capable AI provider "
        "is configured."
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
                "Market data error."
            )
        )

    if "values" not in data:

        raise RuntimeError(
            f"Unexpected market data response: "
            f"{data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            f"Not enough data for {symbol}."
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
                "Price API error."
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
        2 /
        (period + 1)
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
            -
            values[i - 1]
        )

        if change > 0:

            gains.append(
                change
            )

            losses.append(
                0
            )

        else:

            gains.append(
                0
            )

            losses.append(
                abs(change)
            )

    avg_gain = (
        sum(
            gains[:period]
        )
        / period
    )

    avg_loss = (
        sum(
            losses[:period]
        )
        / period
    )

    for i in range(
        period,
        len(gains)
    ):

        avg_gain = (

            (
                avg_gain
                *
                (period - 1)
            )
            +
            gains[i]

        ) / period

        avg_loss = (

            (
                avg_loss
                *
                (period - 1)
            )
            +
            losses[i]

        ) / period

    if avg_loss == 0:

        return 100

    rs = (
        avg_gain
        / avg_loss
    )

    return (
        100
        -
        (
            100 /
            (1 + rs)
        )
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
        or
        ema21 is None
        or
        ema50 is None
        or
        current_rsi is None

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

    if ema9 > ema21:

        score += 1

    else:

        score -= 1

    if ema21 > ema50:

        score += 1

    else:

        score -= 1

    if current_price > ema21:

        score += 1

    else:

        score -= 1

    if (
        50 < current_rsi < 70
    ):

        score += 1

    elif (
        30 < current_rsi < 50
    ):

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

    entry = current_price

    if signal == "BUY":

        risk = (
            entry
            -
            recent_low
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
            +
            risk * 1.5
        )

        tp2 = (
            entry
            +
            risk * 2.5
        )

    elif signal == "SELL":

        risk = (
            recent_high
            -
            entry
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
            -
            risk * 1.5
        )

        tp2 = (
            entry
            -
            risk * 2.5
        )

    else:

        stop_loss = recent_low

        tp1 = recent_high

        tp2 = recent_high

    strength = min(

        90,

        max(

            50,

            50 +
            abs(score) * 10

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

        float(
            c["close"]
        )

        for c in candles

    ]

    highs = [

        float(
            c["high"]
        )

        for c in candles

    ]

    lows = [

        float(
            c["low"]
        )

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

        f"👑 **{title}**\n\n"

        f"📊 **{data['symbol']}**\n"

        f"⏱ Timeframe: "
        f"**{data['interval']}**\n\n"

        f"{data['direction']} "
        f"**SIGNAL: {data['signal']}**\n"

        f"📈 Trend: "
        f"**{data['trend']}**\n"

        f"🔥 Analysis Strength: "
        f"**{data['strength']}%**\n\n"

        f"💰 Entry: "
        f"`${data['entry']:,.2f}`\n"

        f"🛑 Stop Loss: "
        f"`${data['stop_loss']:,.2f}`\n"

        f"🎯 TP1: "
        f"`${data['tp1']:,.2f}`\n"

        f"🎯 TP2: "
        f"`${data['tp2']:,.2f}`\n\n"

        f"📊 RSI: "
        f"**{data['rsi']:.2f}**\n"

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

        r"\b"
        r"(1m|5m|15m|30m|1h|2h|4h|1d)"
        r"\b",

        text.lower()

    )

    if match:

        timeframe = (
            match.group(1)
        )

    return symbol, timeframe


# =========================================================
# DISCORD CLIENT
# =========================================================

class KingZarryAI(
    discord.Client
):

    def __init__(self):

        intents = (
            discord.Intents.default()
        )

        intents.message_content = True

        super().__init__(
            intents=intents
        )

        self.tree = (
            app_commands.CommandTree(
                self
            )
        )

    async def setup_hook(self):

        if DISCORD_GUILD_ID:

            guild = discord.Object(

                id=int(
                    DISCORD_GUILD_ID
                )

            )

            self.tree.copy_global_to(
                guild=guild
            )

            synced = await self.tree.sync(
                guild=guild
            )

            print(
                f"👑 Synced {len(synced)} "
                f"commands to test server."
            )

        else:

            synced = (
                await self.tree.sync()
            )

            print(
                f"👑 Synced {len(synced)} "
                f"global commands."
            )

    async def on_ready(self):

        print(
            f"👑 Logged in as {self.user}"
        )

        print(
            "📡 KING ZARRY AI IS ONLINE."
        )

        print(
            "💬 ALL-MESSAGE AI CHAT ENABLED."
        )

        print(
            "🧠 MULTI-PROVIDER AI ENABLED."
        )

        print(
            f"🟢 Gemini: "
            f"{'ON' if GEMINI_API_KEY else 'OFF'}"
        )

        print(
            f"🟣 Hugging Face: "
            f"{'ON' if HF_TOKEN else 'OFF'}"
        )

        print(
            f"🔵 OpenAI: "
            f"{'ON' if OPENAI_API_KEY else 'OFF'}"
        )


    # =====================================================
    # ALL NORMAL MESSAGES + IMAGES
    # =====================================================

    async def on_message(
        self,
        message: discord.Message
    ):

        print(
            f"💬 MESSAGE RECEIVED | "
            f"User: {message.author} | "
            f"Content: {message.content!r}"
        )

        if message.author.bot:

            return

        # -------------------------------------------------
        # IMAGE MESSAGE
        # -------------------------------------------------

        image_attachments = [

            attachment

            for attachment
            in message.attachments

            if (

                attachment.content_type

                and

                attachment.content_type.startswith(
                    "image/"
                )

            )

        ]

        if image_attachments:

            try:

                async with (
                    message.channel.typing()
                ):

                    attachment = (
                        image_attachments[0]
                    )

                    if attachment.size > (
                        10 * 1024 * 1024
                    ):

                        await message.reply(

                            "❌ Chart image is too large. "
                            "Maximum size is 10 MB.",

                            mention_author=False

                        )

                        return

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            message.content
                        )
                    )

                    image_bytes = (
                        await attachment.read()
                    )

                    mime = (
                        attachment.content_type
                        or
                        "image/png"
                    )

                    result = (
                        await asyncio.to_thread(

                            analyze_chart_image,

                            image_bytes,

                            symbol,

                            timeframe,

                            mime

                        )
                    )

                await send_long_message(

                    message,

                    result,

                    reply=True

                )

            except Exception as e:

                print(
                    "❌ IMAGE AI ERROR:",
                    repr(e)
                )

                await message.reply(

                    "❌ I couldn't analyse "
                    "that image.\n"
                    f"Error: `{str(e)[:1500]}`",

                    mention_author=False

                )

            return

        # -------------------------------------------------
        # TEXT MESSAGE
        # -------------------------------------------------

        content = (
            message.content.strip()
        )

        if not content:

            return

        clean_prompt = content

        if self.user:

            clean_prompt = (
                clean_prompt.replace(
                    f"<@{self.user.id}>",
                    ""
                )
            )

            clean_prompt = (
                clean_prompt.replace(
                    f"<@!{self.user.id}>",
                    ""
                )
            )

        clean_prompt = (
            clean_prompt.strip()
        )

        if not clean_prompt:

            clean_prompt = (
                "The user mentioned you. "
                "Respond naturally and ask "
                "how you can help."
            )

        try:

            async with (
                message.channel.typing()
            ):

                answer = (
                    await asyncio.to_thread(
                        ask_ai,
                        clean_prompt
                    )
                )

            await send_long_message(

                message,

                answer,

                reply=True

            )

        except Exception as e:

            print(
                "❌ CHAT AI ERROR:",
                repr(e)
            )

            await message.reply(

                "❌ **King Zarry AI could not respond.**\n"
                f"Error: `{str(e)[:1500]}`",

                mention_author=False

            )


# =========================================================
# CREATE CLIENT
# =========================================================

client = KingZarryAI()


# =========================================================
# /START
# =========================================================

@client.tree.command(

    name="start",

    description="Start King Zarry AI"

)
async def start(
    interaction: discord.Interaction
):

    await interaction.response.send_message(

        "👑 **WELCOME TO KING ZARRY AI**\n\n"

        "🤖 Your AI assistant is ONLINE.\n"
        "📡 Multi-provider AI is active.\n\n"

        "**🧠 AI PROVIDERS**\n"

        "🟢 Gemini\n"
        "🟣 Hugging Face\n"
        "🔵 OpenAI\n\n"

        "**📊 TRADING**\n"

        "📊 `/signal`\n"
        "₿ `/btc`\n"
        "🪙 `/crypto`\n"
        "🟡 `/gold`\n"
        "📈 `/analyze`\n"
        "📸 `/analyze_chart`\n\n"

        "**💬 AI CHAT**\n"

        "Send a normal message and I will respond.\n\n"

        "📷 Upload a trading chart and "
        "I will analyse it."

    )


# =========================================================
# /HELP
# =========================================================

@client.tree.command(

    name="help",

    description="Show King Zarry AI commands"

)
async def help_command(
    interaction: discord.Interaction
):

    await interaction.response.send_message(

        "👑 **KING ZARRY AI COMMANDS**\n\n"

        "📊 `/signal` - BTC signal\n"

        "₿ `/btc` - Bitcoin analysis\n"

        "🪙 `/crypto` - Crypto prices\n"

        "🟡 `/gold` - Gold analysis\n"

        "📈 `/analyze` - Live market analysis\n"

        "📸 `/analyze_chart` - Chart screenshot\n"

        "💬 Normal messages - AI chat\n"

        "📷 Upload chart - AI vision\n"

        "❓ `/ask` - Ask anything"

    )


# =========================================================
# /SIGNAL
# =========================================================

@client.tree.command(

    name="signal",

    description="Generate a BTC 15-minute analysis"

)
async def signal(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        data = await asyncio.to_thread(

            analyze_symbol,

            "BTC/USD",

            "15min"

        )

        await interaction.followup.send(

            format_analysis(

                data,

                "KING ZARRY AI BTC SIGNAL"

            )

        )

    except Exception as e:

        print(
            "SIGNAL ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ BTC analysis failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /BTC
# =========================================================

@client.tree.command(

    name="btc",

    description="Analyze Bitcoin"

)
async def btc(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        data = await asyncio.to_thread(

            analyze_symbol,

            "BTC/USD",

            "15min"

        )

        await interaction.followup.send(

            format_analysis(

                data,

                "KING ZARRY AI BTC ANALYSIS"

            )

        )

    except Exception as e:

        print(
            "BTC ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ BTC analysis failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /CRYPTO
# =========================================================

@client.tree.command(

    name="crypto",

    description="Show crypto market prices"

)
async def crypto(
    interaction: discord.Interaction
):

    await interaction.response.defer()

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

        await interaction.followup.send(

            "🪙 **KING ZARRY AI CRYPTO MARKET**\n\n"

            f"₿ BTC/USD: "
            f"`${btc_price:,.2f}`\n"

            f"Ξ ETH/USD: "
            f"`${eth_price:,.2f}`\n"

            f"◎ SOL/USD: "
            f"`${sol_price:,.2f}`"

        )

    except Exception as e:

        print(
            "CRYPTO ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ Crypto data failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /GOLD
# =========================================================

@client.tree.command(

    name="gold",

    description="Analyze XAU/USD gold"

)
async def gold(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        data = await asyncio.to_thread(

            analyze_symbol,

            "XAU/USD",

            "15min"

        )

        await interaction.followup.send(

            format_analysis(

                data,

                "KING ZARRY AI GOLD SIGNAL"

            )

        )

    except Exception as e:

        print(
            "GOLD ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ Gold analysis failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /ANALYZE
# =========================================================

@client.tree.command(

    name="analyze",

    description="Analyse live market data"

)
@app_commands.describe(

    symbol="Example: BTC/USD, XAU/USD, EUR/USD",

    timeframe="Example: 15m, 1h, 4h, 1d"

)
async def analyze(

    interaction: discord.Interaction,

    symbol: str,

    timeframe: str = "15m"

):

    await interaction.response.defer()

    try:

        symbol = (
            symbol.upper()
            .strip()
        )

        interval = (
            normalize_timeframe(
                timeframe
            )
        )

        data = await asyncio.to_thread(

            analyze_symbol,

            symbol,

            interval

        )

        await interaction.followup.send(

            format_analysis(

                data,

                "KING ZARRY AI MARKET ANALYSIS"

            )

        )

    except Exception as e:

        print(
            "ANALYZE ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ Market analysis failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /ANALYZE_CHART
# =========================================================

@client.tree.command(

    name="analyze_chart",

    description="Analyse an uploaded trading chart"

)
@app_commands.describe(

    symbol="Example: BTC/USD or XAU/USD",

    timeframe="Example: 15m, 1h, 4h",

    image="Upload your trading chart screenshot"

)
async def analyze_chart(

    interaction: discord.Interaction,

    symbol: str,

    timeframe: str,

    image: discord.Attachment

):

    await interaction.response.defer()

    try:

        content_type = (
            image.content_type
            or ""
        )

        if not content_type.startswith(
            "image/"
        ):

            await interaction.followup.send(

                "❌ Please upload a PNG, JPG "
                "or another image."

            )

            return

        if image.size > (
            10 * 1024 * 1024
        ):

            await interaction.followup.send(

                "❌ Image is too large. "
                "Maximum size is 10 MB."

            )

            return

        image_bytes = (
            await image.read()
        )

        result = await asyncio.to_thread(

            analyze_chart_image,

            image_bytes,

            symbol.upper().strip(),

            timeframe,

            content_type

        )

        await send_long_message(

            interaction,

            result

        )

    except Exception as e:

        print(
            "CHART COMMAND ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ Chart analysis failed: "
            f"`{str(e)[:1000]}`"

        )


# =========================================================
# /ASK
# =========================================================

@client.tree.command(

    name="ask",

    description="Ask King Zarry AI anything"

)
@app_commands.describe(

    question="Type your question"

)
async def ask(

    interaction: discord.Interaction,

    question: str

):

    await interaction.response.defer()

    try:

        answer = await asyncio.to_thread(

            ask_ai,

            question

        )

        await send_long_message(

            interaction,

            answer

        )

    except Exception as e:

        print(
            "ASK ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            f"❌ AI error: "
            f"`{str(e)[:1500]}`"

        )


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

if not DISCORD_BOT_TOKEN:

    raise RuntimeError(

        "DISCORD_BOT_TOKEN is missing."

    )


if not TWELVE_DATA_API_KEY:

    raise RuntimeError(

        "TWELVE_DATA_API_KEY is missing."

    )


if not (

    GEMINI_API_KEY
    or
    HF_TOKEN
    or
    OPENAI_API_KEY

):

    raise RuntimeError(

        "NO AI API KEY FOUND.\n\n"

        "Add at least one of:\n"

        "GEMINI_API_KEY\n"
        "HF_TOKEN\n"
        "OPENAI_API_KEY"

    )


# =========================================================
# STARTUP LOG
# =========================================================

print()
print(
    "👑 ======================================="
)
print(
    "👑 KING ZARRY AI IS STARTING"
)
print(
    "👑 ======================================="
)

print(
    f"🟢 Gemini: "
    f"{'ENABLED' if GEMINI_API_KEY else 'DISABLED'}"
)

print(
    f"🟣 Hugging Face: "
    f"{'ENABLED' if HF_TOKEN else 'DISABLED'}"
)

print(
    f"🔵 OpenAI: "
    f"{'ENABLED' if OPENAI_API_KEY else 'DISABLED'}"
)

print(
    f"🤖 Gemini model: {GEMINI_MODEL}"
)

print(
    f"🧠 Hugging Face model: {HF_MODEL}"
)

print(
    f"🔵 OpenAI model: {OPENAI_MODEL}"
)

print(
    "📸 Multi-provider vision loaded."
)

print(
    "💬 All-message AI chat loaded."
)

print(
    "📊 Trading analysis loaded."
)

print(
    "📡 KING ZARRY AI IS READY."
)

print()


# =========================================================
# RUN BOT
# =========================================================

client.run(
    DISCORD_BOT_TOKEN
)
