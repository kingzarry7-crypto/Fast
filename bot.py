import os
import re
import base64
import asyncio
import tempfile
import subprocess
from pathlib import Path

import discord
from discord import app_commands
import requests


# ============================================================
# 👑 KING ZARRY AI
# MULTI-PROVIDER + VISION + TRADING + DISCORD VOICE
#
# PROVIDERS:
# 🟢 Gemini
# 🔵 OpenAI
#
# FEATURES:
# 💬 Normal AI chat
# 📸 Image/chart analysis
# 📊 Trading analysis
# 🎙️ Discord voice
# 🔊 AI speech
# 🔄 Automatic provider fallback
# ============================================================


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ============================================================
# PROVIDER CONFIGURATION
# ============================================================

PROVIDER_MODE = os.getenv(
    "PROVIDER_MODE",
    "AUTO"
).upper().strip()


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)


OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)


OPENAI_TTS_MODEL = os.getenv(
    "OPENAI_TTS_MODEL",
    "gpt-4o-mini-tts"
)


OPENAI_TTS_VOICE = os.getenv(
    "OPENAI_TTS_VOICE",
    "alloy"
)


# ============================================================
# MARKET DATA
# ============================================================

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)


# ============================================================
# PROVIDER STATUS
# ============================================================

GEMINI_ENABLED = bool(GEMINI_API_KEY)

OPENAI_ENABLED = bool(OPENAI_API_KEY)


# ============================================================
# OPTIONAL GEMINI SDK
# ============================================================

try:

    from google import genai

    GEMINI_SDK_AVAILABLE = True

except Exception:

    genai = None

    GEMINI_SDK_AVAILABLE = False


gemini_client = None

if GEMINI_ENABLED and GEMINI_SDK_AVAILABLE:

    try:

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception as e:

        print(
            "⚠️ Gemini client initialization failed:",
            repr(e)
        )

        gemini_client = None


# ============================================================
# OPTIONAL OPENAI SDK
# ============================================================

try:

    from openai import OpenAI

    OPENAI_SDK_AVAILABLE = True

except Exception:

    OpenAI = None

    OPENAI_SDK_AVAILABLE = False


openai_client = None

if OPENAI_ENABLED and OPENAI_SDK_AVAILABLE:

    try:

        openai_client = OpenAI(
            api_key=OPENAI_API_KEY
        )

    except Exception as e:

        print(
            "⚠️ OpenAI client initialization failed:",
            repr(e)
        )

        openai_client = None


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant inside
the King Zarry AI Discord community.

Your personality:

- Friendly
- Intelligent
- Practical
- Confident but never dishonest
- Clear
- Helpful
- Natural
- Occasionally playful
- Use emojis when appropriate

You can help with:

- Cryptocurrency
- Bitcoin
- Ethereum
- Solana
- Forex
- Gold / XAUUSD
- Trading
- Technical analysis
- Market structure
- Risk management
- Programming
- Python
- Discord bots
- Artificial intelligence
- Technology
- Business
- General questions
- Education
- Everyday conversations

TRADING SAFETY:

Never guarantee a trade.

Never say that a trade is certain to win.

Clearly distinguish:

CONFIRMED
PROBABLE
UNCERTAIN

Never invent live prices.

If live market data is supplied,
you may analyze it.

If live data is not supplied,
say so.

When giving a trading setup,
include reasoning and risk.

Do not encourage reckless position sizing.

You are King Zarry AI 👑.
"""


# ============================================================
# TIMEFRAME
# ============================================================

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


# ============================================================
# DISCORD MESSAGE LIMIT
# ============================================================

async def send_long_message(
    destination,
    text,
    reply=False
):

    if not text:

        text = (
            "❌ King Zarry AI returned "
            "an empty response."
        )

    chunks = [

        text[i:i + 1900]

        for i in range(
            0,
            len(text),
            1900
        )

    ]

    first = True

    for chunk in chunks:

        if reply and first:

            await destination.reply(
                chunk,
                mention_author=False
            )

        elif hasattr(
            destination,
            "channel"
        ):

            await destination.channel.send(
                chunk
            )

        else:

            await destination.followup.send(
                chunk
            )

        first = False


# ============================================================
# PROVIDER SELECTION
# ============================================================

def provider_status():

    return {

        "gemini": (
            GEMINI_ENABLED
            and gemini_client is not None
        ),

        "openai": (
            OPENAI_ENABLED
            and openai_client is not None
        ),

    }


def get_provider_order():

    status = provider_status()

    if PROVIDER_MODE == "GEMINI":

        return [
            "gemini"
        ]

    if PROVIDER_MODE == "OPENAI":

        return [
            "openai"
        ]

    # AUTO

    providers = []

    if status["gemini"]:

        providers.append(
            "gemini"
        )

    if status["openai"]:

        providers.append(
            "openai"
        )

    return providers


# ============================================================
# GEMINI TEXT
# ============================================================

def gemini_text(
    prompt
):

    if not gemini_client:

        raise RuntimeError(
            "Gemini is not available."
        )

    response = (
        gemini_client
        .models
        .generate_content(

            model=GEMINI_MODEL,

            contents=prompt,

            config=genai.types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                temperature=0.3,

                max_output_tokens=1200,

            )

        )
    )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:

        raise RuntimeError(
            "Gemini returned no text."
        )

    return text.strip()


# ============================================================
# OPENAI TEXT
# ============================================================

def openai_text(
    prompt
):

    if not openai_client:

        raise RuntimeError(
            "OpenAI is not available."
        )

    response = (
        openai_client
        .chat
        .completions
        .create(

            model=OPENAI_MODEL,

            messages=[

                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },

                {
                    "role": "user",
                    "content": prompt,
                },

            ],

            temperature=0.3,

            max_tokens=1200,

        )
    )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    if not answer:

        raise RuntimeError(
            "OpenAI returned no text."
        )

    return answer.strip()


# ============================================================
# UNIVERSAL AI TEXT
# ============================================================

def ask_ai(
    prompt
):

    providers = get_provider_order()

    if not providers:

        raise RuntimeError(
            "No AI provider is enabled.\n"
            "Add GEMINI_API_KEY or OPENAI_API_KEY."
        )

    errors = []

    for provider in providers:

        try:

            print(
                f"🧠 Trying AI provider: "
                f"{provider}"
            )

            if provider == "gemini":

                answer = gemini_text(
                    prompt
                )

            else:

                answer = openai_text(
                    prompt
                )

            print(
                f"✅ Provider succeeded: "
                f"{provider}"
            )

            return answer

        except Exception as e:

            print(
                f"⚠️ Provider failed: "
                f"{provider}: {repr(e)}"
            )

            errors.append(
                f"{provider}: {str(e)}"
            )

    raise RuntimeError(
        "All AI providers failed.\n"
        + "\n".join(errors)
    )


# ============================================================
# IMAGE / CHART ANALYSIS
# ============================================================

def gemini_image_analysis(
    image_bytes,
    mime_type,
    prompt
):

    if not gemini_client:

        raise RuntimeError(
            "Gemini is not available."
        )

    image_part = (
        genai.types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
    )

    response = (
        gemini_client
        .models
        .generate_content(

            model=GEMINI_MODEL,

            contents=[

                prompt,
                image_part,

            ],

            config=genai.types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                temperature=0.2,

                max_output_tokens=1500,

            )

        )
    )

    answer = getattr(
        response,
        "text",
        None
    )

    if not answer:

        raise RuntimeError(
            "Gemini returned no image analysis."
        )

    return answer.strip()


def openai_image_analysis(
    image_bytes,
    mime_type,
    prompt
):

    if not openai_client:

        raise RuntimeError(
            "OpenAI is not available."
        )

    encoded = base64.b64encode(
        image_bytes
    ).decode(
        "utf-8"
    )

    response = (
        openai_client
        .chat
        .completions
        .create(

            model=OPENAI_MODEL,

            messages=[

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
                                f"data:{mime_type};base64,{encoded}"

                            },

                        },

                    ],

                },

            ],

            temperature=0.2,

            max_tokens=1500,

        )
    )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    if not answer:

        raise RuntimeError(
            "OpenAI returned no image analysis."
        )

    return answer.strip()


def analyze_chart_image(
    image_bytes,
    mime_type,
    symbol="UNKNOWN",
    timeframe="15m"
):

    prompt = f"""
Analyze this trading chart screenshot.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information actually visible.

Inspect:

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
14. BUY possibility
15. SELL possibility
16. Entry area
17. Invalidation
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

If a price cannot be clearly read,
describe the area instead.

If there is insufficient information,
return WAIT and explain why.

Never guarantee profit.
"""

    providers = get_provider_order()

    errors = []

    for provider in providers:

        try:

            if provider == "gemini":

                return gemini_image_analysis(
                    image_bytes,
                    mime_type,
                    prompt
                )

            return openai_image_analysis(
                image_bytes,
                mime_type,
                prompt
            )

        except Exception as e:

            errors.append(
                f"{provider}: {str(e)}"
            )

    raise RuntimeError(
        "Vision providers failed.\n"
        + "\n".join(errors)
    )


# ============================================================
# TWELVE DATA
# ============================================================

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

            "apikey":
            TWELVE_DATA_API_KEY,

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

    if "values" not in data:

        raise RuntimeError(
            f"Unexpected market response: {data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            "Not enough candles returned."
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

            "symbol": symbol,

            "apikey":
            TWELVE_DATA_API_KEY,

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

    if "price" not in data:

        raise RuntimeError(
            f"Unexpected price response: {data}"
        )

    return float(
        data["price"]
    )


# ============================================================
# INDICATORS
# ============================================================

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

    return (
        100
        - (100 / (1 + rs))
    )


# ============================================================
# MARKET ANALYSIS
# ============================================================

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
            entry
            - recent_low
        )

        if risk <= 0:

            risk = entry * 0.005

        stop_loss = (
            entry - risk
        )

        tp1 = (
            entry + risk * 1.5
        )

        tp2 = (
            entry + risk * 2.5
        )

    elif signal == "SELL":

        risk = (
            recent_high
            - entry
        )

        if risk <= 0:

            risk = entry * 0.005

        stop_loss = (
            entry + risk
        )

        tp1 = (
            entry - risk * 1.5
        )

        tp2 = (
            entry - risk * 2.5
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

        "price": current_price,

        "signal": signal,

        "direction": direction,

        "trend": trend,

        "rsi": current_rsi,

        "ema9": ema9,

        "ema21": ema21,

        "ema50": ema50,

        "entry": entry,

        "stop_loss": stop_loss,

        "tp1": tp1,

        "tp2": tp2,

        "strength": strength,

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


# ============================================================
# FORMAT SIGNAL
# ============================================================

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


# ============================================================
# MARKET DETECTION
# ============================================================

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
        r"1m|5m|15m|30m|1h|2h|4h|1d"
        r")\b",

        text.lower()

    )

    if match:

        timeframe = match.group(1)

    return symbol, timeframe


# ============================================================
# OPENAI TEXT TO SPEECH
# ============================================================

def openai_tts(
    text,
    output_path
):

    if not openai_client:

        raise RuntimeError(
            "OpenAI TTS requires "
            "OPENAI_API_KEY."
        )

    speech = (
        openai_client
        .audio
        .speech
        .create(

            model=OPENAI_TTS_MODEL,

            voice=OPENAI_TTS_VOICE,

            input=text,

            response_format="mp3",

        )
    )

    speech.stream_to_file(
        output_path
    )

    return output_path


# ============================================================
# FALLBACK TTS USING EDGE TTS
# ============================================================

async def edge_tts_speech(
    text,
    output_path
):

    try:

        import edge_tts

    except ImportError:

        raise RuntimeError(
            "edge-tts is not installed."
        )

    communicate = edge_tts.Communicate(

        text,

        os.getenv(
            "EDGE_TTS_VOICE",
            "en-US-AriaNeural"
        )

    )

    await communicate.save(
        output_path
    )

    return output_path


# ============================================================
# GENERATE VOICE
# ============================================================

async def create_voice_file(
    text
):

    temp_dir = Path(
        tempfile.gettempdir()
    )

    output_path = (
        temp_dir
        / f"king_zarry_{os.getpid()}_{id(text)}.mp3"
    )

    # Prefer OpenAI TTS when available.

    if OPENAI_ENABLED and openai_client:

        try:

            await asyncio.to_thread(

                openai_tts,

                text,

                str(output_path)

            )

            return output_path

        except Exception as e:

            print(
                "⚠️ OpenAI TTS failed:",
                repr(e)
            )

    # Fallback to Edge TTS.

    try:

        await edge_tts_speech(

            text,

            str(output_path)

        )

        return output_path

    except Exception as e:

        print(
            "⚠️ Edge TTS failed:",
            repr(e)
        )

    raise RuntimeError(
        "No working voice provider.\n"
        "Add OPENAI_API_KEY or install/configure edge-tts."
    )


# ============================================================
# DISCORD VOICE
# ============================================================

async def connect_to_voice(
    member
):

    if not member.voice:

        raise RuntimeError(
            "You must join a Discord voice channel first."
        )

    channel = member.voice.channel

    voice_client = (
        discord.utils.get(
            bot.voice_clients,
            guild=channel.guild
        )
    )

    if voice_client:

        if voice_client.channel.id != channel.id:

            await voice_client.move_to(
                channel
            )

        return voice_client

    return await channel.connect()


async def play_voice(
    guild,
    audio_path
):

    voice_client = (
        discord.utils.get(
            bot.voice_clients,
            guild=guild
        )
    )

    if not voice_client:

        raise RuntimeError(
            "King Zarry AI is not connected "
            "to a voice channel."
        )

    if voice_client.is_playing():

        voice_client.stop()

    source = discord.FFmpegPCMAudio(
        str(audio_path)
    )

    finished = asyncio.Event()

    def after_playing(error):

        if error:

            print(
                "❌ Discord voice playback error:",
                repr(error)
            )

        bot.loop.call_soon_threadsafe(
            finished.set
        )

    voice_client.play(
        source,
        after=after_playing
    )

    await finished.wait()


async def speak_in_voice(
    guild,
    text
):

    # Discord voice should not receive enormous messages.

    clean_text = text[:3500]

    audio_path = await create_voice_file(
        clean_text
    )

    try:

        await play_voice(
            guild,
            audio_path
        )

    finally:

        try:

            audio_path.unlink(
                missing_ok=True
            )

        except Exception:

            pass


# ============================================================
# DISCORD CLIENT
# ============================================================

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

        print(
            f"🟢 Gemini: "
            f"{'ENABLED' if GEMINI_ENABLED else 'DISABLED'}"
        )

        print(
            f"🔵 OpenAI: "
            f"{'ENABLED' if OPENAI_ENABLED else 'DISABLED'}"
        )

        print(
            f"🧠 Provider mode: "
            f"{PROVIDER_MODE}"
        )

        print(
            f"🤖 Gemini model: "
            f"{GEMINI_MODEL}"
        )

        print(
            f"🔵 OpenAI model: "
            f"{OPENAI_MODEL}"
        )

        print(
            "🎙️ Discord voice system loaded."
        )

        print(
            "📸 Multi-provider vision loaded."
        )

        print(
            "💬 All-message AI chat loaded."
        )

        print(
            f"👑 Logged in as {self.user}"
        )

    async def on_message(
        self,
        message: discord.Message
    ):

        if message.author.bot:

            return

        print(
            f"💬 MESSAGE | "
            f"{message.author}: "
            f"{message.content!r}"
        )

        # ====================================================
        # IMAGE CHAT
        # ====================================================

        image_attachments = [

            attachment

            for attachment in message.attachments

            if (

                attachment.content_type

                and attachment.content_type.startswith(
                    "image/"
                )

            )

        ]

        if image_attachments:

            attachment = (
                image_attachments[0]
            )

            if attachment.size > (
                10 * 1024 * 1024
            ):

                await message.reply(
                    "❌ Image too large. "
                    "Maximum size is 10 MB.",
                    mention_author=False
                )

                return

            try:

                async with message.channel.typing():

                    image_bytes = (
                        await attachment.read()
                    )

                    mime_type = (
                        attachment.content_type
                        or "image/png"
                    )

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            message.content
                        )
                    )

                    answer = await asyncio.to_thread(

                        analyze_chart_image,

                        image_bytes,

                        mime_type,

                        symbol,

                        timeframe

                    )

                await send_long_message(

                    message,

                    answer,

                    reply=True

                )

            except Exception as e:

                print(
                    "❌ IMAGE ERROR:",
                    repr(e)
                )

                await message.reply(

                    "❌ Chart analysis failed.\n"
                    f"`{str(e)[:1500]}`",

                    mention_author=False

                )

            return

        # ====================================================
        # NORMAL CHAT
        # ====================================================

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
                "The user mentioned you. "
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
                "❌ CHAT ERROR:",
                repr(e)
            )

            await message.reply(

                "❌ King Zarry AI could not respond.\n"
                f"`{str(e)[:1500]}`",

                mention_author=False

            )


# ============================================================
# CREATE CLIENT
# ============================================================

bot = KingZarryAI()


# ============================================================
# /START
# ============================================================

@bot.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(
    interaction: discord.Interaction
):

    await interaction.response.send_message(

        "👑 **WELCOME TO KING ZARRY AI**\n\n"

        "🤖 Your AI assistant is online.\n\n"

        "**💬 AI**\n"
        "`/ask` Ask anything\n\n"

        "**📊 TRADING**\n"
        "`/signal` BTC signal\n"
        "`/btc` Bitcoin analysis\n"
        "`/gold` Gold analysis\n"
        "`/analyze` Live market analysis\n"
        "`/crypto` Crypto prices\n\n"

        "**📸 VISION**\n"
        "`/analyze_chart` Analyze a chart\n\n"

        "**🎙️ VOICE**\n"
        "`/join` Join your voice channel\n"
        "`/speak` Make King Zarry AI speak\n"
        "`/voiceask` Ask AI and hear the answer\n"
        "`/leave` Leave voice channel\n\n"

        "💡 You can also simply send me a normal message."

    )


# ============================================================
# /HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="Show King Zarry AI commands"
)
async def help_command(
    interaction: discord.Interaction
):

    await interaction.response.send_message(

        "👑 **KING ZARRY AI COMMANDS**\n\n"

        "💬 `/ask` AI question\n"

        "📊 `/signal` BTC signal\n"

        "₿ `/btc` Bitcoin analysis\n"

        "🟡 `/gold` Gold analysis\n"

        "🪙 `/crypto` Crypto prices\n"

        "📈 `/analyze` Market analysis\n"

        "📸 `/analyze_chart` Chart vision\n\n"

        "🎙️ `/join` Join voice\n"

        "🔊 `/speak` Speak text\n"

        "🧠 `/voiceask` AI answer through voice\n"

        "🛑 `/leave` Leave voice\n\n"

        "💬 Normal messages also activate King Zarry AI."

    )


# ============================================================
# /ASK
# ============================================================

@bot.tree.command(
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

            "❌ AI error:\n"
            f"`{str(e)[:1500]}`"

        )


# ============================================================
# /JOIN
# ============================================================

@bot.tree.command(
    name="join",
    description="Join your Discord voice channel"
)
async def join(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Voice is only available inside a server."
        )

        return

    member = interaction.guild.get_member(
        interaction.user.id
    )

    if not member:

        await interaction.response.send_message(
            "❌ Could not find your server member profile."
        )

        return

    try:

        voice_client = await connect_to_voice(
            member
        )

        await interaction.response.send_message(

            "🎙️ **King Zarry AI joined the voice channel.**\n"
            "🔊 Use `/speak` or `/voiceask`."

        )

    except Exception as e:

        await interaction.response.send_message(

            "❌ Could not join voice.\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /LEAVE
# ============================================================

@bot.tree.command(
    name="leave",
    description="Leave the Discord voice channel"
)
async def leave(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ This command must be used in a server."
        )

        return

    voice_client = (
        discord.utils.get(
            bot.voice_clients,
            guild=interaction.guild
        )
    )

    if not voice_client:

        await interaction.response.send_message(
            "🎙️ I'm not currently in a voice channel."
        )

        return

    await voice_client.disconnect()

    await interaction.response.send_message(
        "👋 **King Zarry AI left the voice channel.**"
    )


# ============================================================
# /SPEAK
# ============================================================

@bot.tree.command(
    name="speak",
    description="Make King Zarry AI speak in Discord voice"
)
@app_commands.describe(
    text="What King Zarry AI should say"
)
async def speak(
    interaction: discord.Interaction,
    text: str
):

    await interaction.response.defer()

    if not interaction.guild:

        await interaction.followup.send(
            "❌ This command must be used in a server."
        )

        return

    try:

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if not member:

            raise RuntimeError(
                "Could not find your member profile."
            )

        await connect_to_voice(
            member
        )

        await interaction.followup.send(
            "🎙️ **Speaking...**"
        )

        await speak_in_voice(
            interaction.guild,
            text
        )

    except Exception as e:

        print(
            "❌ SPEAK ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            "❌ Voice error:\n"
            f"`{str(e)[:1200]}`"

        )


# ============================================================
# /VOICEASK
# ============================================================

@bot.tree.command(
    name="voiceask",
    description="Ask King Zarry AI and hear the answer"
)
@app_commands.describe(
    question="Ask King Zarry AI a question"
)
async def voiceask(
    interaction: discord.Interaction,
    question: str
):

    await interaction.response.defer()

    if not interaction.guild:

        await interaction.followup.send(
            "❌ This command must be used in a server."
        )

        return

    try:

        member = interaction.guild.get_member(
            interaction.user.id
        )

        if not member:

            raise RuntimeError(
                "Could not find your member profile."
            )

        await connect_to_voice(
            member
        )

        answer = await asyncio.to_thread(

            ask_ai,

            question

        )

        await interaction.followup.send(

            "🧠 **King Zarry AI:**\n"
            + answer[:1900]

        )

        await speak_in_voice(

            interaction.guild,

            answer

        )

    except Exception as e:

        print(
            "❌ VOICE ASK ERROR:",
            repr(e)
        )

        await interaction.followup.send(

            "❌ Voice AI error:\n"
            f"`{str(e)[:1200]}`"

        )


# ============================================================
# /SIGNAL
# ============================================================

@bot.tree.command(
    name="signal",
    description="Generate BTC 15-minute analysis"
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

        await interaction.followup.send(

            "❌ BTC analysis failed:\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /BTC
# ============================================================

@bot.tree.command(
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

        await interaction.followup.send(

            "❌ BTC analysis failed:\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /GOLD
# ============================================================

@bot.tree.command(
    name="gold",
    description="Analyze XAU/USD Gold"
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

        await interaction.followup.send(

            "❌ Gold analysis failed:\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /CRYPTO
# ============================================================

@bot.tree.command(
    name="crypto",
    description="Show crypto prices"
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

            f"₿ BTC/USD: `${btc_price:,.2f}`\n"

            f"Ξ ETH/USD: `${eth_price:,.2f}`\n"

            f"◎ SOL/USD: `${sol_price:,.2f}`"

        )

    except Exception as e:

        await interaction.followup.send(

            "❌ Crypto data failed:\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /ANALYZE
# ============================================================

@bot.tree.command(
    name="analyze",
    description="Analyze live market data"
)
@app_commands.describe(
    symbol="Example: BTC/USD or XAU/USD",
    timeframe="Example: 15m, 1h, 4h"
)
async def analyze(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15m"
):

    await interaction.response.defer()

    try:

        symbol = (
            symbol
            .upper()
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

            "❌ Market analysis failed:\n"
            f"`{str(e)[:1000]}`"

        )


# ============================================================
# /ANALYZE_CHART
# ============================================================

@bot.tree.command(
    name="analyze_chart",
    description="Analyze a trading chart"
)
@app_commands.describe(
    symbol="Example: BTC/USD or XAU/USD",
    timeframe="Example: 15m or 1h",
    image="Upload chart screenshot"
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
                "❌ Please upload an image."
            )

            return

        if image.size > (
            10 * 1024 * 1024
        ):

            await interaction.followup.send(
                "❌ Maximum image size is 10 MB."
            )

            return

        image_bytes = (
            await image.read()
        )

        result = await asyncio.to_thread(

            analyze_chart_image,

            image_bytes,

            content_type,

            symbol.upper().strip(),

            timeframe

        )

        await send_long_message(

            interaction,

            result

        )

    except Exception as e:

        await interaction.followup.send(

            "❌ Chart analysis failed:\n"
            f"`{str(e)[:1200]}`"

        )


# ============================================================
# STARTUP CHECKS
# ============================================================

if not DISCORD_BOT_TOKEN:

    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing."
    )


if not TWELVE_DATA_API_KEY:

    print(
        "⚠️ TWELVE_DATA_API_KEY is missing. "
        "Trading commands will not work."
    )


if not GEMINI_ENABLED and not OPENAI_ENABLED:

    raise RuntimeError(

        "No AI provider is configured.\n"
        "Add GEMINI_API_KEY or OPENAI_API_KEY "
        "to Railway Variables."

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

print(
    f"🟢 Gemini: "
    f"{'ENABLED' if GEMINI_ENABLED else 'DISABLED'}"
)

print(
    f"🔵 OpenAI: "
    f"{'ENABLED' if OPENAI_ENABLED else 'DISABLED'}"
)

print(
    f"🧠 Provider mode: "
    f"{PROVIDER_MODE}"
)

print(
    f"🤖 Gemini model: "
    f"{GEMINI_MODEL}"
)

print(
    f"🔵 OpenAI model: "
    f"{OPENAI_MODEL}"
)

print(
    "🎙️ Voice system loaded."
)

print(
    "📸 Multi-provider vision loaded."
)

print(
    "💬 All-message AI chat loaded."
)

print(
    "📡 KING ZARRY AI IS READY."
)


# ============================================================
# START BOT
# ============================================================

bot.run(
    DISCORD_BOT_TOKEN
)
