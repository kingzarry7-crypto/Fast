import os
import re
import io
import wave
import base64
import asyncio
import tempfile
import subprocess
from pathlib import Path

import requests
import discord
from discord import app_commands

# ============================================================
# OPTIONAL AI SDKs
# ============================================================

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Discord voice receive extension
try:
    from discord.ext import voice_recv
except ImportError:
    voice_recv = None


# ============================================================
# KING ZARRY AI
# MULTI-PROVIDER + VOICE VERSION
# ============================================================

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

# ------------------------------------------------------------
# Provider
#
# GEMINI
# OPENAI
# AUTO
# ------------------------------------------------------------

AI_PROVIDER = os.environ.get(
    "AI_PROVIDER",
    "AUTO"
).upper().strip()

# ------------------------------------------------------------
# Models
# ------------------------------------------------------------

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OPENAI_MODEL = os.environ.get(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

OPENAI_TTS_MODEL = os.environ.get(
    "OPENAI_TTS_MODEL",
    "gpt-4o-mini-tts"
)

OPENAI_TTS_VOICE = os.environ.get(
    "OPENAI_TTS_VOICE",
    "alloy"
)

# Gemini TTS model can be changed from Railway variables
GEMINI_TTS_MODEL = os.environ.get(
    "GEMINI_TTS_MODEL",
    "gemini-3.1-flash-tts-preview"
)

GEMINI_TTS_VOICE = os.environ.get(
    "GEMINI_TTS_VOICE",
    "Kore"
)

# ------------------------------------------------------------
# URLs
# ------------------------------------------------------------

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)


# ============================================================
# PROVIDER STATUS
# ============================================================

def gemini_enabled():
    return bool(
        GEMINI_API_KEY
        and genai is not None
    )


def openai_enabled():
    return bool(
        OPENAI_API_KEY
        and OpenAI is not None
    )


def provider_status():

    return {
        "gemini": gemini_enabled(),
        "openai": openai_enabled(),
    }


def selected_provider():

    status = provider_status()

    if AI_PROVIDER == "GEMINI":
        if status["gemini"]:
            return "GEMINI"

        raise RuntimeError(
            "AI_PROVIDER=GEMINI but GEMINI_API_KEY "
            "or google-genai is missing."
        )

    if AI_PROVIDER == "OPENAI":
        if status["openai"]:
            return "OPENAI"

        raise RuntimeError(
            "AI_PROVIDER=OPENAI but OPENAI_API_KEY "
            "or openai package is missing."
        )

    # AUTO
    if status["gemini"]:
        return "GEMINI"

    if status["openai"]:
        return "OPENAI"

    raise RuntimeError(
        "No AI provider is configured. "
        "Add GEMINI_API_KEY or OPENAI_API_KEY."
    )


# ============================================================
# AI SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant inside the
King Zarry Discord community.

You can discuss:

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
- Everyday conversation

PERSONALITY:

Be intelligent, natural, friendly and practical.

Use emojis when appropriate.

Keep normal answers reasonably concise.

TRADING SAFETY:

Never guarantee profit.

Never claim a trade is certain to win.

Clearly distinguish:

CONFIRMED
PROBABLE
UNCERTAIN

Never pretend to have live market information
unless live data was actually provided.

When discussing a trading setup, explain:

- Direction
- Entry
- Stop loss / invalidation
- Targets
- Reason
- Risk

If the information is insufficient,
say WAIT rather than inventing information.

You are King Zarry AI 👑.
"""


# ============================================================
# GEMINI CLIENT
# ============================================================

_gemini_client = None


def get_gemini_client():

    global _gemini_client

    if not gemini_enabled():

        raise RuntimeError(
            "Gemini is not configured."
        )

    if _gemini_client is None:

        _gemini_client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    return _gemini_client


# ============================================================
# OPENAI CLIENT
# ============================================================

_openai_client = None


def get_openai_client():

    global _openai_client

    if not openai_enabled():

        raise RuntimeError(
            "OpenAI is not configured."
        )

    if _openai_client is None:

        _openai_client = OpenAI(
            api_key=OPENAI_API_KEY
        )

    return _openai_client


# ============================================================
# GEMINI TEXT
# ============================================================

def gemini_text(prompt):

    client = get_gemini_client()

    response = client.models.generate_content(

        model=GEMINI_MODEL,

        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            SYSTEM_PROMPT
                            + "\n\nUSER:\n"
                            + prompt
                        )
                    }
                ]
            }
        ]
    )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return text.strip()


# ============================================================
# OPENAI TEXT
# ============================================================

def openai_text(prompt):

    client = get_openai_client()

    response = client.chat.completions.create(

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

    answer = (
        response.choices[0]
        .message
        .content
    )

    if not answer:

        raise RuntimeError(
            "OpenAI returned an empty response."
        )

    return answer.strip()


# ============================================================
# UNIVERSAL AI TEXT
# ============================================================

def ask_ai(prompt):

    provider = selected_provider()

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if provider == "GEMINI":

        try:

            return gemini_text(prompt)

        except Exception as first_error:

            print(
                "⚠️ Gemini failed:",
                repr(first_error)
            )

            # Automatic fallback
            if openai_enabled():

                print(
                    "🔄 Falling back to OpenAI..."
                )

                return openai_text(prompt)

            raise

    # --------------------------------------------------------
    # OPENAI
    # --------------------------------------------------------

    try:

        return openai_text(prompt)

    except Exception as first_error:

        print(
            "⚠️ OpenAI failed:",
            repr(first_error)
        )

        if gemini_enabled():

            print(
                "🔄 Falling back to Gemini..."
            )

            return gemini_text(prompt)

        raise


# ============================================================
# IMAGE / CHART ANALYSIS
# ============================================================

def analyze_chart_image(
    image_bytes,
    symbol="UNKNOWN",
    timeframe="15m"
):

    prompt = f"""
Analyze this trading chart screenshot.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information that is actually visible.

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
11. Candlestick behaviour
12. EMA if visible
13. RSI if visible
14. Possible BUY setup
15. Possible SELL setup
16. Entry area
17. Invalidation / stop
18. TP1
19. TP2
20. Reason

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

Do not invent prices.

If exact prices cannot be read,
describe the area instead.

Never guarantee profit.

If there is not enough information,
return WAIT and explain why.
"""

    provider = selected_provider()

    # ========================================================
    # GEMINI VISION
    # ========================================================

    if provider == "GEMINI":

        try:

            client = get_gemini_client()

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png"
            )

            response = client.models.generate_content(

                model=GEMINI_MODEL,

                contents=[
                    SYSTEM_PROMPT,
                    prompt,
                    image_part
                ]
            )

            answer = getattr(
                response,
                "text",
                None
            )

            if answer:

                return answer.strip()

        except Exception as e:

            print(
                "⚠️ Gemini vision failed:",
                repr(e)
            )

            if not openai_enabled():

                raise

            print(
                "🔄 Falling back to OpenAI vision..."
            )

    # ========================================================
    # OPENAI VISION
    # ========================================================

    if not openai_enabled():

        raise RuntimeError(
            "No vision provider is available."
        )

    client = get_openai_client()

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    response = client.chat.completions.create(

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
                            "data:image/png;base64,"
                            + encoded
                        }
                    }
                ]
            }
        ],

        temperature=0.2,

        max_tokens=1400
    )

    answer = (
        response.choices[0]
        .message
        .content
    )

    if not answer:

        raise RuntimeError(
            "Vision provider returned no response."
        )

    return answer.strip()


# ============================================================
# TEXT TO SPEECH
# ============================================================

def openai_tts(text):

    client = get_openai_client()

    # Keep Discord voice replies reasonably short.
    text = text[:4000]

    response = client.audio.speech.create(

        model=OPENAI_TTS_MODEL,

        voice=OPENAI_TTS_VOICE,

        input=text,

        response_format="mp3"
    )

    audio_bytes = response.read()

    if not audio_bytes:

        raise RuntimeError(
            "OpenAI TTS returned empty audio."
        )

    return audio_bytes


def gemini_tts(text):

    """
    Gemini TTS REST implementation.

    Returns WAV audio bytes.
    """

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    text = text[:4000]

    url = (
        f"{GEMINI_API_URL}/"
        f"{GEMINI_TTS_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload = {

        "contents": [

            {
                "parts": [
                    {
                        "text": text
                    }
                ]
            }

        ],

        "generationConfig": {

            "responseModalities": [
                "AUDIO"
            ],

            "speechConfig": {

                "voiceConfig": {

                    "prebuiltVoiceConfig": {

                        "voiceName":
                        GEMINI_TTS_VOICE
                    }
                }
            }
        }
    }

    response = requests.post(

        url,

        json=payload,

        timeout=120
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Gemini TTS error: "
            + response.text[:2000]
        )

    data = response.json()

    try:

        part = (
            data["candidates"][0]
            ["content"]["parts"][0]
        )

        audio_data = (
            part["inlineData"]["data"]
        )

        mime_type = (
            part["inlineData"]
            .get(
                "mimeType",
                "audio/L16;rate=24000"
            )
        )

    except Exception:

        raise RuntimeError(
            f"Unexpected Gemini TTS response: "
            f"{data}"
        )

    pcm = base64.b64decode(
        audio_data
    )

    # Gemini audio is commonly returned as PCM.
    # Convert it to WAV so FFmpeg/Discord can play it.

    rate = 24000

    rate_match = re.search(
        r"rate=(\d+)",
        mime_type
    )

    if rate_match:

        rate = int(
            rate_match.group(1)
        )

    wav_buffer = io.BytesIO()

    with wave.open(
        wav_buffer,
        "wb"
    ) as wf:

        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)

    return wav_buffer.getvalue()


def text_to_speech(text):

    provider = selected_provider()

    if provider == "OPENAI":

        try:

            return (
                openai_tts(text),
                "mp3"
            )

        except Exception as e:

            print(
                "⚠️ OpenAI TTS failed:",
                repr(e)
            )

            if gemini_enabled():

                return (
                    gemini_tts(text),
                    "wav"
                )

            raise

    # Gemini first

    try:

        return (
            gemini_tts(text),
            "wav"
        )

    except Exception as e:

        print(
            "⚠️ Gemini TTS failed:",
            repr(e)
        )

        if openai_enabled():

            return (
                openai_tts(text),
                "mp3"
            )

        raise


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

    for chunk in chunks:

        if reply:

            await destination.reply(
                chunk,
                mention_author=False
            )

            reply = False

        else:

            if hasattr(
                destination,
                "channel"
            ):

                await destination.channel.send(
                    chunk
                )

            else:

                await destination.send(
                    chunk
                )


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
            "apikey": TWELVE_DATA_API_KEY,

        },

        timeout=20
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
            f"Unexpected market response: "
            f"{data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            "Not enough market candles."
        )

    return candles


def get_market_price(symbol):

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

        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Price error."
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


# ============================================================
# INDICATORS
# ============================================================

def ema(values, period):

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

    price = closes[-1]

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
            "Indicator calculation failed."
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

    if price > ema21:
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

    entry = price

    if signal == "BUY":

        risk = (
            entry
            - recent_low
        )

        if risk <= 0:

            risk = entry * 0.005

        stop = entry - risk
        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 2.5

    elif signal == "SELL":

        risk = (
            recent_high
            - entry
        )

        if risk <= 0:

            risk = entry * 0.005

        stop = entry + risk
        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 2.5

    else:

        stop = recent_low
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

        "price": price,
        "signal": signal,
        "direction": direction,
        "trend": trend,
        "rsi": current_rsi,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "entry": entry,
        "stop_loss": stop,
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

        timeframe = match.group(1)

    return symbol, timeframe


# ============================================================
# DISCORD VOICE
# ============================================================

class KingZarryVoiceSink(
    voice_recv.AudioSink
):

    def __init__(
        self,
        bot,
        guild_id
    ):

        super().__init__()

        self.bot = bot
        self.guild_id = guild_id

        self.buffers = {}

    def wants_opus(self):

        return False

    def write(
        self,
        user,
        data
    ):

        if user is None:

            return

        user_id = user.id

        if user_id not in self.buffers:

            self.buffers[user_id] = bytearray()

        self.buffers[user_id].extend(
            data.pcm
        )

        # Keep memory bounded.
        # Roughly prevents an accidentally
        # endless recording.
        if len(
            self.buffers[user_id]
        ) > 20 * 1024 * 1024:

            self.buffers[user_id] = (
                self.buffers[user_id]
                [-20 * 1024 * 1024:]
            )

    def get_audio(
        self,
        user_id
    ):

        return bytes(
            self.buffers.pop(
                user_id,
                b""
            )
        )

    def cleanup(self):

        self.buffers.clear()


# ============================================================
# CREATE WAV FROM PCM
# ============================================================

def pcm_to_wav(
    pcm_bytes
):

    output = io.BytesIO()

    with wave.open(
        output,
        "wb"
    ) as wf:

        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(
            pcm_bytes
        )

    return output.getvalue()


# ============================================================
# TRANSCRIBE AUDIO WITH GEMINI
# ============================================================

def gemini_transcribe(
    audio_bytes,
    mime_type="audio/wav"
):

    client = get_gemini_client()

    # Upload temporary audio file.
    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    ) as f:

        f.write(audio_bytes)
        path = f.name

    try:

        uploaded = client.files.upload(
            file=path
        )

        response = client.models.generate_content(

            model=GEMINI_MODEL,

            contents=[

                "Transcribe the speech exactly. "
                "Return only the spoken words.",

                uploaded

            ]
        )

        text = getattr(
            response,
            "text",
            None
        )

        if not text:

            raise RuntimeError(
                "Gemini returned no transcript."
            )

        return text.strip()

    finally:

        try:
            os.remove(path)
        except Exception:
            pass


# ============================================================
# TRANSCRIBE AUDIO WITH OPENAI
# ============================================================

def openai_transcribe(
    audio_bytes
):

    client = get_openai_client()

    audio_file = io.BytesIO(
        audio_bytes
    )

    audio_file.name = (
        "discord_voice.wav"
    )

    response = (
        client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=audio_file
        )
    )

    text = getattr(
        response,
        "text",
        None
    )

    if not text:

        raise RuntimeError(
            "OpenAI returned no transcript."
        )

    return text.strip()


def transcribe_audio(
    audio_bytes
):

    provider = selected_provider()

    if provider == "GEMINI":

        try:

            return gemini_transcribe(
                audio_bytes
            )

        except Exception as e:

            print(
                "⚠️ Gemini transcription failed:",
                repr(e)
            )

            if openai_enabled():

                return openai_transcribe(
                    audio_bytes
                )

            raise

    try:

        return openai_transcribe(
            audio_bytes
        )

    except Exception as e:

        print(
            "⚠️ OpenAI transcription failed:",
            repr(e)
        )

        if gemini_enabled():

            return gemini_transcribe(
                audio_bytes
            )

        raise


# ============================================================
# PLAY AUDIO IN DISCORD
# ============================================================

def make_audio_source(
    audio_bytes,
    extension
):

    temp_dir = tempfile.mkdtemp(
        prefix="king_zarry_voice_"
    )

    input_path = os.path.join(
        temp_dir,
        f"reply.{extension}"
    )

    output_path = os.path.join(
        temp_dir,
        "reply.mp3"
    )

    with open(
        input_path,
        "wb"
    ) as f:

        f.write(audio_bytes)

    # Convert everything to MP3.
    subprocess.run(

        [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            output_path
        ],

        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,

        check=True
    )

    return (
        discord.FFmpegPCMAudio(
            output_path
        ),
        temp_dir
    )


async def play_voice_response(
    voice_client,
    text
):

    if not voice_client:

        return

    if not voice_client.is_connected():

        return

    audio_bytes, extension = (
        await asyncio.to_thread(
            text_to_speech,
            text
        )
    )

    source, temp_dir = (
        await asyncio.to_thread(
            make_audio_source,
            audio_bytes,
            extension
        )
    )

    finished = asyncio.Event()

    def after(error):

        if error:

            print(
                "❌ Discord voice playback error:",
                repr(error)
            )

        asyncio.run_coroutine_threadsafe(
            cleanup_voice_file(
                temp_dir,
                finished
            ),
            voice_client.loop
        )

    voice_client.play(
        source,
        after=after
    )

    await finished.wait()


async def cleanup_voice_file(
    temp_dir,
    event
):

    try:

        import shutil

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

    finally:

        event.set()


# ============================================================
# DISCORD BOT
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

        self.voice_sinks = {}

    # --------------------------------------------------------
    # COMMAND SYNC
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # READY
    # --------------------------------------------------------

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
            f"🟢 Gemini: "
            f"{'ENABLED' if status['gemini'] else 'DISABLED'}"
        )

        print(
            f"🔵 OpenAI: "
            f"{'ENABLED' if status['openai'] else 'DISABLED'}"
        )

        print(
            f"🧠 Provider mode: "
            f"{AI_PROVIDER}"
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

    # --------------------------------------------------------
    # NORMAL MESSAGES
    # --------------------------------------------------------

    async def on_message(
        self,
        message
    ):

        if message.author.bot:

            return

        print(
            f"💬 MESSAGE | "
            f"{message.author}: "
            f"{message.content!r}"
        )

        # ====================================================
        # IMAGE
        # ====================================================

        images = [

            attachment

            for attachment
            in message.attachments

            if (
                attachment.content_type
                and attachment.content_type
                .startswith("image/")
            )

        ]

        if images:

            try:

                async with (
                    message.channel.typing()
                ):

                    image = images[0]

                    if image.size > (
                        10 * 1024 * 1024
                    ):

                        await message.reply(
                            "❌ Image is too large. "
                            "Maximum 10 MB.",
                            mention_author=False
                        )

                        return

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            message.content
                        )
                    )

                    image_bytes = (
                        await image.read()
                    )

                    result = (
                        await asyncio.to_thread(
                            analyze_chart_image,
                            image_bytes,
                            symbol,
                            timeframe
                        )
                    )

                await send_long_message(
                    message,
                    result,
                    reply=True
                )

            except Exception as e:

                print(
                    "❌ IMAGE ERROR:",
                    repr(e)
                )

                await message.reply(
                    "❌ Chart analysis failed.\n"
                    f"`{str(e)[:1200]}`",
                    mention_author=False
                )

            return

        # ====================================================
        # DISCORD VOICE MESSAGE ATTACHMENT
        # ====================================================

        audio_attachments = [

            attachment

            for attachment
            in message.attachments

            if (
                attachment.content_type
                and (
                    attachment.content_type
                    .startswith("audio/")
                    or attachment.filename
                    .lower()
                    .endswith(
                        (
                            ".ogg",
                            ".opus",
                            ".wav",
                            ".mp3",
                            ".m4a",
                            ".webm"
                        )
                    )
                )
            )

        ]

        if audio_attachments:

            try:

                async with (
                    message.channel.typing()
                ):

                    audio = (
                        audio_attachments[0]
                    )

                    if audio.size > (
                        20 * 1024 * 1024
                    ):

                        await message.reply(
                            "❌ Voice message is too large.",
                            mention_author=False
                        )

                        return

                    raw_audio = (
                        await audio.read()
                    )

                    # Discord voice messages are
                    # commonly OGG/Opus.
                    #
                    # Convert to WAV using FFmpeg.

                    with tempfile.TemporaryDirectory() as td:

                        input_path = (
                            Path(td)
                            / "input_audio"
                        )

                        output_path = (
                            Path(td)
                            / "voice.wav"
                        )

                        input_path.write_bytes(
                            raw_audio
                        )

                        await asyncio.to_thread(

                            subprocess.run,

                            [
                                "ffmpeg",
                                "-y",
                                "-i",
                                str(input_path),
                                "-ar",
                                "48000",
                                "-ac",
                                "1",
                                str(output_path)
                            ],

                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,

                            check=True
                        )

                        wav_bytes = (
                            output_path
                            .read_bytes()
                        )

                    transcript = (
                        await asyncio.to_thread(
                            transcribe_audio,
                            wav_bytes
                        )
                    )

                    if not transcript:

                        raise RuntimeError(
                            "I could not understand "
                            "the voice message."
                        )

                    print(
                        "🎙️ TRANSCRIPT:",
                        transcript
                    )

                    answer = (
                        await asyncio.to_thread(
                            ask_ai,
                            transcript
                        )
                    )

                await message.reply(
                    f"🎙️ **You said:**\n"
                    f"> {transcript[:1000]}\n\n"
                    f"👑 **King Zarry AI:**\n"
                    f"{answer[:3500]}",
                    mention_author=False
                )

            except Exception as e:

                print(
                    "❌ VOICE MESSAGE ERROR:",
                    repr(e)
                )

                await message.reply(
                    "❌ I couldn't process "
                    "that voice message.\n"
                    f"`{str(e)[:1200]}`",
                    mention_author=False
                )

            return

        # ====================================================
        # NORMAL TEXT
        # ====================================================

        content = (
            message.content
            .strip()
        )

        if not content:

            return

        clean_prompt = content

        if self.user:

            clean_prompt = (
                clean_prompt
                .replace(
                    f"<@{self.user.id}>",
                    ""
                )
                .replace(
                    f"<@!{self.user.id}>",
                    ""
                )
                .strip()
            )

        if not clean_prompt:

            clean_prompt = (
                "The user mentioned you. "
                "Respond naturally."
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
                "❌ CHAT ERROR:",
                repr(e)
            )

            await message.reply(
                "❌ **King Zarry AI error**\n"
                f"`{str(e)[:1500]}`",
                mention_author=False
            )


# ============================================================
# CLIENT
# ============================================================

client = KingZarryAI()


# ============================================================
# /START
# ============================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(
    interaction
):

    await interaction.response.send_message(

        "👑 **WELCOME TO KING ZARRY AI**\n\n"

        "🧠 Multi-provider AI is ONLINE.\n"
        "🎙️ Voice features are loaded.\n"
        "📸 Chart vision is loaded.\n\n"

        "**AI**\n"
        "💬 Normal messages\n"
        "🎙️ Voice messages\n"
        "🔊 Voice replies\n"
        "📸 Chart analysis\n\n"

        "**VOICE COMMANDS**\n"
        "🎧 `/join` - Join your voice channel\n"
        "🛑 `/leave` - Leave voice channel\n"
        "🗣️ `/listen` - Start listening\n"
        "🤫 `/stop_listening` - Stop listening\n\n"

        "**TRADING**\n"
        "📊 `/signal`\n"
        "₿ `/btc`\n"
        "🟡 `/gold`\n"
        "🪙 `/crypto`\n"
        "📈 `/analyze`\n"
        "📸 `/analyze_chart`\n\n"

        "👑 **King Zarry AI is ready.**"
    )


# ============================================================
# /HELP
# ============================================================

@client.tree.command(
    name="help",
    description="Show King Zarry AI commands"
)
async def help_command(
    interaction
):

    await interaction.response.send_message(

        "👑 **KING ZARRY AI COMMANDS**\n\n"

        "💬 `/ask` - Ask anything\n"
        "🎧 `/join` - Join voice\n"
        "🛑 `/leave` - Leave voice\n"
        "🗣️ `/listen` - Listen to voice\n"
        "🤫 `/stop_listening` - Stop listening\n"
        "🔊 `/speak` - Make AI speak\n\n"

        "📊 `/signal` - BTC signal\n"
        "₿ `/btc` - BTC analysis\n"
        "🟡 `/gold` - Gold analysis\n"
        "🪙 `/crypto` - Crypto prices\n"
        "📈 `/analyze` - Live analysis\n"
        "📸 `/analyze_chart` - Chart analysis"
    )


# ============================================================
# /JOIN
# ============================================================

@client.tree.command(
    name="join",
    description="Join your current Discord voice channel"
)
async def join(
    interaction
):

    if not interaction.user.voice:

        await interaction.response.send_message(
            "❌ You must join a voice channel first.",
            ephemeral=True
        )

        return

    channel = (
        interaction.user.voice.channel
    )

    await interaction.response.defer()

    try:

        existing = (
            interaction.guild.voice_client
        )

        if existing:

            if existing.channel.id != channel.id:

                await existing.move_to(
                    channel
                )

            vc = existing

        else:

            if voice_recv is not None:

                vc = await channel.connect(
                    cls=voice_recv.VoiceRecvClient
                )

            else:

                vc = await channel.connect()

        await interaction.followup.send(
            f"🎧 **King Zarry AI joined "
            f"{channel.mention}** 👑"
        )

    except Exception as e:

        print(
            "❌ JOIN ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ Could not join voice.\n"
            f"`{str(e)[:1200]}`"
        )


# ============================================================
# /LEAVE
# ============================================================

@client.tree.command(
    name="leave",
    description="Leave the current voice channel"
)
async def leave(
    interaction
):

    vc = (
        interaction.guild.voice_client
    )

    if not vc:

        await interaction.response.send_message(
            "❌ I am not in a voice channel.",
            ephemeral=True
        )

        return

    try:

        if voice_recv is not None:

            try:
                vc.stop()
            except Exception:
                pass

        await vc.disconnect()

        await interaction.response.send_message(
            "👋 **King Zarry AI left the voice channel.**"
        )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ Voice disconnect failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /SPEAK
# ============================================================

@client.tree.command(
    name="speak",
    description="Make King Zarry AI speak in your voice channel"
)
@app_commands.describe(
    text="What you want King Zarry AI to say"
)
async def speak(
    interaction,
    text: str
):

    await interaction.response.defer()

    vc = (
        interaction.guild.voice_client
    )

    if not vc:

        await interaction.followup.send(
            "❌ Use `/join` first."
        )

        return

    try:

        await play_voice_response(
            vc,
            text
        )

        await interaction.followup.send(
            "🔊 **King Zarry AI spoke the message.** 👑"
        )

    except Exception as e:

        print(
            "❌ SPEAK ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ Voice generation failed.\n"
            f"`{str(e)[:1200]}`"
        )


# ============================================================
# /LISTEN
# ============================================================

@client.tree.command(
    name="listen",
    description="Start listening to your Discord voice channel"
)
async def listen(
    interaction
):

    if voice_recv is None:

        await interaction.response.send_message(
            "❌ Voice receiving is not installed.",
            ephemeral=True
        )

        return

    vc = (
        interaction.guild.voice_client
    )

    if not vc:

        await interaction.response.send_message(
            "❌ Use `/join` first.",
            ephemeral=True
        )

        return

    if not isinstance(
        vc,
        voice_recv.VoiceRecvClient
    ):

        await interaction.response.send_message(
            "❌ Reconnect with `/leave` then `/join` "
            "to enable voice receiving.",
            ephemeral=True
        )

        return

    try:

        old_sink = (
            client.voice_sinks.get(
                interaction.guild.id
            )
        )

        if old_sink:

            try:
                vc.stop_listening()
            except Exception:
                pass

        sink = KingZarryVoiceSink(
            client,
            interaction.guild.id
        )

        client.voice_sinks[
            interaction.guild.id
        ] = sink

        vc.listen(
            sink
        )

        await interaction.response.send_message(

            "🎙️ **King Zarry AI is now listening.**\n\n"
            "Speak in the voice channel.\n"
            "Use `/stop_listening` when you're done."
        )

    except Exception as e:

        print(
            "❌ LISTEN ERROR:",
            repr(e)
        )

        await interaction.response.send_message(
            f"❌ Could not start listening.\n"
            f"`{str(e)[:1200]}`"
        )


# ============================================================
# /STOP_LISTENING
# ============================================================

@client.tree.command(
    name="stop_listening",
    description="Stop listening to voice"
)
async def stop_listening(
    interaction
):

    vc = (
        interaction.guild.voice_client
    )

    if not vc:

        await interaction.response.send_message(
            "❌ I am not in voice.",
            ephemeral=True
        )

        return

    try:

        if hasattr(
            vc,
            "stop_listening"
        ):

            vc.stop_listening()

        client.voice_sinks.pop(
            interaction.guild.id,
            None
        )

        await interaction.response.send_message(
            "🤫 **King Zarry AI stopped listening.**"
        )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ Could not stop listening: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /ASK
# ============================================================

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

        answer = (
            await asyncio.to_thread(
                ask_ai,
                question
            )
        )

        await send_long_message(
            interaction,
            answer
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ AI error: "
            f"`{str(e)[:1500]}`"
        )


# ============================================================
# /SIGNAL
# ============================================================

@client.tree.command(
    name="signal",
    description="Generate BTC 15-minute analysis"
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
            f"❌ BTC analysis failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /BTC
# ============================================================

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
            f"❌ BTC analysis failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /GOLD
# ============================================================

@client.tree.command(
    name="gold",
    description="Analyze XAU/USD"
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
            f"❌ Gold analysis failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /CRYPTO
# ============================================================

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

            f"₿ BTC/USD: "
            f"`${btc_price:,.2f}`\n"

            f"Ξ ETH/USD: "
            f"`${eth_price:,.2f}`\n"

            f"◎ SOL/USD: "
            f"`${sol_price:,.2f}`"

        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Crypto data failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /ANALYZE
# ============================================================

@client.tree.command(
    name="analyze",
    description="Analyze live market data"
)
@app_commands.describe(
    symbol="Example: BTC/USD or XAU/USD",
    timeframe="Example: 15m, 1h, 4h, 1d"
)
async def analyze(
    interaction,
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

        await interaction.followup.send(
            f"❌ Market analysis failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# /ANALYZE_CHART
# ============================================================

@client.tree.command(
    name="analyze_chart",
    description="Analyze a trading chart"
)
@app_commands.describe(
    symbol="Example: BTC/USD or XAU/USD",
    timeframe="Example: 15m, 1h, 4h",
    image="Upload your chart"
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
            and image.content_type
            .startswith("image/")
        ):

            await interaction.followup.send(
                "❌ Please upload an image."
            )

            return

        if image.size > (
            10 * 1024 * 1024
        ):

            await interaction.followup.send(
                "❌ Image is too large."
            )

            return

        image_bytes = (
            await image.read()
        )

        result = await asyncio.to_thread(

            analyze_chart_image,

            image_bytes,

            symbol.upper().strip(),

            timeframe

        )

        await send_long_message(
            interaction,
            result
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Chart analysis failed: "
            f"`{str(e)[:1000]}`"
        )


# ============================================================
# ENVIRONMENT CHECK
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing."
    )

if not TWELVE_DATA_API_KEY:

    raise RuntimeError(
        "TWELVE_DATA_API_KEY is missing."
    )

if not gemini_enabled() and not openai_enabled():

    raise RuntimeError(

        "No AI provider is configured.\n"

        "Add GEMINI_API_KEY or OPENAI_API_KEY "
        "to Railway Variables."

    )


# ============================================================
# START
# ============================================================

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
    f"{'ENABLED' if gemini_enabled() else 'DISABLED'}"
)

print(
    f"🔵 OpenAI: "
    f"{'ENABLED' if openai_enabled() else 'DISABLED'}"
)

print(
    f"🧠 Provider mode: "
    f"{AI_PROVIDER}"
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


client.run(TOKEN)
