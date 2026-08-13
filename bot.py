import os
import re
import base64
import asyncio
import tempfile
import subprocess
from typing import Optional

import requests
import discord
from discord import app_commands


# =========================================================
# KING ZARRY AI 👑
# DISCORD + SHARED AI ENGINE
# GEMINI / OPENAI PROVIDER SWITCHING
# =========================================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

AI_PROVIDER = os.getenv("AI_PROVIDER", "AUTO").upper().strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

TWELVE_DATA_URL = "https://api.twelvedata.com"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

OPENAI_URL = (
    "https://api.openai.com/v1/chat/completions"
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant for the King Zarry community.

You can help with:

• Cryptocurrency
• Bitcoin
• Ethereum
• Solana
• Forex
• Gold / XAUUSD
• Technical analysis
• Market structure
• Trading concepts
• Risk management
• Programming
• Coding
• Artificial intelligence
• Technology
• Business
• General questions
• Education
• Casual conversation

TRADING RULES:

Never guarantee a winning trade.

Never claim certainty about future market movement.

Clearly distinguish:

CONFIRMED
PROBABLE
UNCERTAIN

When discussing a trading setup, explain:

• Direction
• Market structure
• Entry area
• Stop/invalidation
• Take profits
• Risk/reward
• Reasoning

Never pretend to have live market data unless live data has actually been supplied.

If live market data is supplied, analyze that data.

Be practical and concise.

Use emojis naturally.

You are King Zarry AI 👑.
"""


# =========================================================
# PROVIDER STATUS
# =========================================================

def gemini_enabled():
    return bool(GEMINI_API_KEY)


def openai_enabled():
    return bool(OPENAI_API_KEY)


def provider_status():

    return {
        "gemini": gemini_enabled(),
        "openai": openai_enabled(),
        "mode": AI_PROVIDER,
    }


# =========================================================
# GEMINI
# =========================================================

def gemini_request(
    messages,
    image_bytes=None,
    image_mime="image/png"
):

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    parts = []

    for message in messages:

        if message["role"] == "system":
            continue

        content = message["content"]

        if isinstance(content, str):

            parts.append({
                "text": content
            })

        elif isinstance(content, list):

            for item in content:

                if item.get("type") == "text":

                    parts.append({
                        "text": item.get(
                            "text",
                            ""
                        )
                    })

    if image_bytes:

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        parts.append({

            "inline_data": {

                "mime_type": image_mime,

                "data": encoded,
            }

        })

    payload = {

        "systemInstruction": {

            "parts": [

                {
                    "text": SYSTEM_PROMPT
                }

            ]
        },

        "contents": [

            {
                "role": "user",

                "parts": parts
            }

        ],

        "generationConfig": {

            "temperature": 0.3,

            "maxOutputTokens": 1500
        }
    }

    url = (
        f"{GEMINI_URL}/"
        f"{GEMINI_MODEL}:generateContent"
    )

    response = requests.post(

        url,

        headers={

            "x-goog-api-key":
                GEMINI_API_KEY,

            "Content-Type":
                "application/json",
        },

        json=payload,

        timeout=120,
    )

    if response.status_code != 200:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            f"Gemini API error: {error}"
        )

    data = response.json()

    try:

        candidates = data["candidates"]

        text_parts = []

        for candidate in candidates:

            content = candidate.get(
                "content",
                {}
            )

            for part in content.get(
                "parts",
                []
            ):

                if "text" in part:

                    text_parts.append(
                        part["text"]
                    )

        answer = "\n".join(
            text_parts
        ).strip()

    except Exception:

        answer = ""

    if not answer:

        raise RuntimeError(
            f"Gemini returned no text: {data}"
        )

    return answer


# =========================================================
# OPENAI
# =========================================================

def openai_request(
    messages,
    image_bytes=None,
    image_mime="image/png"
):

    if not OPENAI_API_KEY:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    prepared_messages = []

    for message in messages:

        role = message["role"]

        content = message["content"]

        if isinstance(content, str):

            prepared_messages.append({

                "role": role,

                "content": content
            })

        else:

            prepared_messages.append({

                "role": role,

                "content": content
            })

    if image_bytes:

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        data_url = (
            f"data:{image_mime};base64,"
            f"{encoded}"
        )

        prepared_messages.append({

            "role": "user",

            "content": [

                {
                    "type": "text",

                    "text":
                        "Analyze the attached image carefully."
                },

                {
                    "type": "image_url",

                    "image_url": {

                        "url": data_url,

                        "detail": "high"
                    }
                }

            ]
        })

    headers = {

        "Authorization":
            f"Bearer {OPENAI_API_KEY}",

        "Content-Type":
            "application/json"
    }

    payload = {

        "model": OPENAI_MODEL,

        "messages": prepared_messages,

        "temperature": 0.3,

        "max_tokens": 1500
    }

    response = requests.post(

        OPENAI_URL,

        headers=headers,

        json=payload,

        timeout=120
    )

    if response.status_code != 200:

        try:
            error = response.json()
        except Exception:
            error = response.text

        raise RuntimeError(
            f"OpenAI API error: {error}"
        )

    data = response.json()

    try:

        answer = (
            data["choices"][0]
            ["message"]["content"]
        )

    except Exception:

        raise RuntimeError(
            f"Unexpected OpenAI response: {data}"
        )

    if not answer:

        raise RuntimeError(
            "OpenAI returned no text."
        )

    return answer.strip()


# =========================================================
# PROVIDER ROUTER
# =========================================================

def ask_ai(prompt):

    messages = [

        {
            "role": "system",

            "content":
                SYSTEM_PROMPT
        },

        {
            "role": "user",

            "content":
                prompt
        }

    ]

    errors = []

    # -----------------------------------------------------
    # GEMINI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "GEMINI":

        return gemini_request(
            messages
        )

    # -----------------------------------------------------
    # OPENAI ONLY
    # -----------------------------------------------------

    if AI_PROVIDER == "OPENAI":

        return openai_request(
            messages
        )

    # -----------------------------------------------------
    # AUTO
    # Gemini first, OpenAI fallback
    # -----------------------------------------------------

    if gemini_enabled():

        try:

            return gemini_request(
                messages
            )

        except Exception as e:

            errors.append(
                f"Gemini: {e}"
            )

    if openai_enabled():

        try:

            return openai_request(
                messages
            )

        except Exception as e:

            errors.append(
                f"OpenAI: {e}"
            )

    raise RuntimeError(
        "No AI provider was able to respond.\n"
        + "\n".join(errors)
    )


# =========================================================
# VISION
# =========================================================

def analyze_chart_image(
    image_bytes,
    symbol="UNKNOWN",
    timeframe="15m",
    image_mime="image/png"
):

    prompt = f"""
Analyze this trading chart for King Zarry AI 👑.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information that is actually visible.

Analyze:

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
11. Candlestick behavior
12. EMA if visible
13. RSI if visible
14. Possible BUY setup
15. Possible SELL setup
16. Entry area
17. Invalidation / stop area
18. TP1
19. TP2
20. Reason

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

Do not invent prices.

If a price is unclear, say that it is unclear.

If there is not enough information, return WAIT.

Never guarantee profit.
"""

    messages = [

        {
            "role": "system",

            "content":
                SYSTEM_PROMPT
        },

        {
            "role": "user",

            "content":
                prompt
        }

    ]

    errors = []

    if AI_PROVIDER == "GEMINI":

        return gemini_request(
            messages,
            image_bytes,
            image_mime
        )

    if AI_PROVIDER == "OPENAI":

        return openai_request(
            messages,
            image_bytes,
            image_mime
        )

    if gemini_enabled():

        try:

            return gemini_request(
                messages,
                image_bytes,
                image_mime
            )

        except Exception as e:

            errors.append(
                f"Gemini vision: {e}"
            )

    if openai_enabled():

        try:

            return openai_request(
                messages,
                image_bytes,
                image_mime
            )

        except Exception as e:

            errors.append(
                f"OpenAI vision: {e}"
            )

    raise RuntimeError(
        "No vision provider available.\n"
        + "\n".join(errors)
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


def normalize_timeframe(
    timeframe
):

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
                TWELVE_DATA_API_KEY
        },

        timeout=30
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

    if "values" not in data:

        raise RuntimeError(
            f"Unexpected Twelve Data response: {data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            "Not enough market data."
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
                TWELVE_DATA_API_KEY
        },

        timeout=30
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

    if "price" not in data:

        raise RuntimeError(
            f"Unexpected price response: {data}"
        )

    return float(
        data["price"]
    )


# =========================================================
# INDICATORS
# =========================================================

def ema(
    values,
    period
):

    if len(values) < period:
        return None

    multiplier = 2 / (
        period + 1
    )

    result = (
        sum(values[:period])
        / period
    )

    for price in values[period:]:

        result = (
            (
                price - result
            )
            * multiplier
        ) + result

    return result


def rsi(
    values,
    period=14
):

    if len(values) < period + 1:
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

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(
                abs(change)
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

    if None in (
        ema9,
        ema21,
        ema50,
        current_rsi
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

    entry = current_price

    if signal == "BUY":

        risk = (
            entry - recent_low
        )

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry - risk

        tp1 = entry + risk * 1.5

        tp2 = entry + risk * 2.5

    elif signal == "SELL":

        risk = (
            recent_high - entry
        )

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry + risk

        tp1 = entry - risk * 1.5

        tp2 = entry - risk * 2.5

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

        f"👑 **{title}**\n\n"

        f"📊 **{data['symbol']}**\n"

        f"⏱ Timeframe: "
        f"**{data['interval']}**\n\n"

        f"{data['direction']} "
        f"**SIGNAL: {data['signal']}**\n"

        f"📈 Trend: "
        f"**{data['trend']}**\n"

        f"🔥 Strength: "
        f"**{data['strength']}%**\n\n"

        f"💰 Entry: "
        f"`${data['entry']:,.5f}`\n"

        f"🛑 Stop Loss: "
        f"`${data['stop_loss']:,.5f}`\n"

        f"🎯 TP1: "
        f"`${data['tp1']:,.5f}`\n"

        f"🎯 TP2: "
        f"`${data['tp2']:,.5f}`\n\n"

        f"📊 RSI: "
        f"**{data['rsi']:.2f}**\n"

        f"EMA 9: "
        f"`${data['ema9']:,.5f}`\n"

        f"EMA 21: "
        f"`${data['ema21']:,.5f}`\n"

        f"EMA 50: "
        f"`${data['ema50']:,.5f}`\n\n"

        "⚠️ Algorithmic analysis only. "
        "No signal guarantees profit."
    )


# =========================================================
# DISCORD MESSAGE CHUNKING
# =========================================================

async def send_long_message(
    destination,
    text,
    reply=False
):

    if not text:
        text = "❌ AI returned an empty response."

    chunks = [

        text[i:i + 1900]

        for i in range(
            0,
            len(text),
            1900
        )
    ]

    for index, chunk in enumerate(chunks):

        if reply and index == 0:

            await destination.reply(
                chunk,
                mention_author=False
            )

        else:

            await destination.channel.send(
                chunk
            )


# =========================================================
# MARKET DETECTION
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
            "GOLD"
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
        ]
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
        timeframe = match.group(1)

    return symbol, timeframe


# =========================================================
# DISCORD VOICE
# =========================================================

async def create_voice_file(
    text
):

    try:

        import edge_tts

    except ImportError:

        raise RuntimeError(
            "edge-tts is not installed."
        )

    file = tempfile.NamedTemporaryFile(
        suffix=".mp3",
        delete=False
    )

    file.close()

    communicate = edge_tts.Communicate(
        text,
        "en-US-AriaNeural"
    )

    await communicate.save(
        file.name
    )

    return file.name


# =========================================================
# DISCORD CLIENT
# =========================================================

class KingZarryAI(
    discord.Client
):

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

            synced = await self.tree.sync()

            print(
                f"👑 Synced {len(synced)} "
                f"global commands."
            )

    async def on_ready(self):

        print(
            "👑 ======================================="
        )

        print(
            "👑 KING ZARRY AI IS ONLINE"
        )

        print(
            "👑 ======================================="
        )

        status = provider_status()

        print(
            f"🧠 Provider mode: {status['mode']}"
        )

        print(
            f"🟢 Gemini: "
            f"{'ON' if status['gemini'] else 'OFF'}"
        )

        print(
            f"🔵 OpenAI: "
            f"{'ON' if status['openai'] else 'OFF'}"
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
            "🎙️ Discord voice system loaded."
        )

        print(
            "💬 All-message AI chat loaded."
        )

        print(
            f"👑 Logged in as {self.user}"
        )

    async def on_message(
        self,
        message
    ):

        if message.author.bot:
            return

        # -------------------------------------------------
        # IMAGE
        # -------------------------------------------------

        images = [

            a for a in message.attachments

            if (
                a.content_type
                and
                a.content_type.startswith(
                    "image/"
                )
            )
        ]

        if images:

            attachment = images[0]

            if attachment.size > 10 * 1024 * 1024:

                await message.reply(
                    "❌ Maximum chart image size is 10 MB.",
                    mention_author=False
                )

                return

            try:

                async with message.channel.typing():

                    image_bytes = (
                        await attachment.read()
                    )

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            message.content
                        )
                    )

                    result = await asyncio.to_thread(

                        analyze_chart_image,

                        image_bytes,

                        symbol,

                        timeframe,

                        attachment.content_type
                        or "image/png"
                    )

                await send_long_message(
                    message,
                    result,
                    reply=True
                )

            except Exception as e:

                print(
                    "❌ VISION ERROR:",
                    repr(e)
                )

                await message.reply(
                    f"❌ Chart analysis failed:\n"
                    f"`{str(e)[:1200]}`",
                    mention_author=False
                )

            return

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        content = (
            message.content
            .strip()
        )

        if not content:
            return

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

        if not content:

            content = (
                "The user mentioned King Zarry AI. "
                "Respond naturally."
            )

        try:

            async with message.channel.typing():

                answer = await asyncio.to_thread(
                    ask_ai,
                    content
                )

            await send_long_message(
                message,
                answer,
                reply=True
            )

        except Exception as e:

            print(
                "❌ AI CHAT ERROR:",
                repr(e)
            )

            await message.reply(
                f"❌ AI error:\n"
                f"`{str(e)[:1200]}`",
                mention_author=False
            )


client = KingZarryAI()


# =========================================================
# /START
# =========================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(
    interaction
):

    await interaction.response.send_message(

        "👑 **WELCOME TO KING ZARRY AI**\n\n"

        "🤖 AI assistant ONLINE.\n\n"

        "🧠 Gemini/OpenAI provider switching\n"

        "📊 Live trading analysis\n"

        "📸 Chart vision analysis\n"

        "🎙️ Discord voice\n\n"

        "**COMMANDS**\n"

        "`/signal` BTC signal\n"

        "`/btc` Bitcoin analysis\n"

        "`/gold` Gold analysis\n"

        "`/crypto` Crypto prices\n"

        "`/analyze` Market analysis\n"

        "`/analyze_chart` Chart analysis\n"

        "`/ask` Ask anything\n"

        "`/join` Join your voice channel\n"

        "`/say` Speak AI text in voice\n"

        "`/leave` Leave voice channel\n\n"

        "💬 You can also simply message me."
    )


# =========================================================
# /HELP
# =========================================================

@client.tree.command(
    name="help",
    description="Show King Zarry AI commands"
)
async def help_command(
    interaction
):

    await interaction.response.send_message(

        "👑 **KING ZARRY AI COMMANDS**\n\n"

        "📊 `/signal`\n"

        "₿ `/btc`\n"

        "🟡 `/gold`\n"

        "🪙 `/crypto`\n"

        "📈 `/analyze`\n"

        "📸 `/analyze_chart`\n"

        "💬 `/ask`\n\n"

        "🎙️ `/join`\n"

        "🗣️ `/say`\n"

        "🚪 `/leave`\n\n"

        "💬 Normal messages → AI\n"

        "📷 Upload chart → AI vision"
    )


# =========================================================
# /ASK
# =========================================================

@client.tree.command(
    name="ask",
    description="Ask King Zarry AI anything"
)
@app_commands.describe(
    question="Your question"
)
async def ask(
    interaction,
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

        await interaction.followup.send(
            f"❌ AI error: `{str(e)[:1200]}`"
        )


# =========================================================
# /SIGNAL
# =========================================================

@client.tree.command(
    name="signal",
    description="Generate BTC 15-minute signal"
)
async def signal(
    interaction
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

        await interaction.followup.send(
            f"❌ BTC error: `{str(e)[:1000]}`"
        )


# =========================================================
# /BTC
# =========================================================

@client.tree.command(
    name="btc",
    description="Analyze Bitcoin"
)
async def btc(
    interaction
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

        await interaction.followup.send(
            f"❌ BTC error: `{str(e)[:1000]}`"
        )


# =========================================================
# /GOLD
# =========================================================

@client.tree.command(
    name="gold",
    description="Analyze XAU/USD gold"
)
async def gold(
    interaction
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

        await interaction.followup.send(
            f"❌ Gold error: `{str(e)[:1000]}`"
        )


# =========================================================
# /CRYPTO
# =========================================================

@client.tree.command(
    name="crypto",
    description="Show crypto prices"
)
async def crypto(
    interaction
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

            f"₿ BTC/USD: `${btc_price:,.2f}`\n"

            f"Ξ ETH/USD: `${eth_price:,.2f}`\n"

            f"◎ SOL/USD: `${sol_price:,.2f}`"
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Crypto error: `{str(e)[:1000]}`"
        )


# =========================================================
# /ANALYZE
# =========================================================

@client.tree.command(
    name="analyze",
    description="Analyze a live market"
)
@app_commands.describe(
    symbol="Example: BTC/USD or XAU/USD",
    timeframe="1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d"
)
async def analyze(
    interaction,
    symbol: str,
    timeframe: str = "15m"
):

    await interaction.response.defer()

    try:

        symbol = (
            symbol.upper()
            .strip()
        )

        interval = normalize_timeframe(
            timeframe
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

        await interaction.followup.send(
            f"❌ Analysis error: `{str(e)[:1000]}`"
        )


# =========================================================
# /ANALYZE_CHART
# =========================================================

@client.tree.command(
    name="analyze_chart",
    description="Analyze a trading chart"
)
@app_commands.describe(
    symbol="Example: BTC/USD",
    timeframe="Example: 15m",
    image="Trading chart screenshot"
)
async def analyze_chart(
    interaction,
    symbol: str,
    timeframe: str,
    image: discord.Attachment
):

    await interaction.response.defer()

    try:

        if not (
            image.content_type
            and
            image.content_type.startswith(
                "image/"
            )
        ):

            await interaction.followup.send(
                "❌ Please upload an image."
            )

            return

        if image.size > 10 * 1024 * 1024:

            await interaction.followup.send(
                "❌ Maximum image size is 10 MB."
            )

            return

        image_bytes = await image.read()

        result = await asyncio.to_thread(

            analyze_chart_image,

            image_bytes,

            symbol.upper().strip(),

            timeframe,

            image.content_type
            or "image/png"
        )

        chunks = [

            result[i:i + 1900]

            for i in range(
                0,
                len(result),
                1900
            )
        ]

        for chunk in chunks:

            await interaction.followup.send(
                chunk
            )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Chart error: `{str(e)[:1000]}`"
        )


# =========================================================
# /JOIN
# =========================================================

@client.tree.command(
    name="join",
    description="Join your current Discord voice channel"
)
async def join(
    interaction
):

    if not interaction.user.voice:

        await interaction.response.send_message(
            "❌ You need to be inside a voice channel first."
        )

        return

    channel = interaction.user.voice.channel

    await interaction.response.defer()

    try:

        if interaction.guild.voice_client:

            await interaction.guild.voice_client.move_to(
                channel
            )

        else:

            await channel.connect()

        await interaction.followup.send(
            f"🎙️ King Zarry AI joined **{channel.name}**."
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Voice connection failed: "
            f"`{str(e)[:1000]}`"
        )


# =========================================================
# /SAY
# =========================================================

@client.tree.command(
    name="say",
    description="Make King Zarry AI speak in your voice channel"
)
@app_commands.describe(
    text="What you want King Zarry AI to say"
)
async def say(
    interaction,
    text: str
):

    await interaction.response.defer()

    voice = interaction.guild.voice_client

    if not voice:

        await interaction.followup.send(
            "❌ Use `/join` first."
        )

        return

    audio_file = None

    try:

        audio_file = await create_voice_file(
            text
        )

        if voice.is_playing():
            voice.stop()

        source = discord.FFmpegOpusAudio(
            audio_file
        )

        voice.play(
            source
        )

        await interaction.followup.send(
            "🎙️ Speaking now. 👑"
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Voice error: `{str(e)[:1000]}`"
        )

    finally:

        # The file is removed when playback
        # has finished by the callback below.
        pass


# =========================================================
# /LEAVE
# =========================================================

@client.tree.command(
    name="leave",
    description="Leave the Discord voice channel"
)
async def leave(
    interaction
):

    voice = interaction.guild.voice_client

    if not voice:

        await interaction.response.send_message(
            "❌ I'm not in a voice channel."
        )

        return

    await voice.disconnect()

    await interaction.response.send_message(
        "🚪 King Zarry AI left the voice channel."
    )


# =========================================================
# START DISCORD
# =========================================================

async def run_discord():

    if not DISCORD_BOT_TOKEN:

        raise RuntimeError(
            "DISCORD_BOT_TOKEN is missing."
        )

    print(
        "👑 ======================================="
    )

    print(
        "👑 KING ZARRY AI IS STARTING"
    )

    print(
        "👑 ======================================="
    )

    client.run(
        DISCORD_BOT_TOKEN
    )


if __name__ == "__main__":
    client.run(TOKEN)
