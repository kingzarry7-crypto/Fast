import os
import re
import html
import asyncio
import base64
import requests
import json

from telegram import (
    Update,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    filters,
)

# =========================================================
# 👑 KING ZARRY AI - TELEGRAM BOT
# AI + TRADING + VISION + SUBSCRIPTIONS + TELEGRAM STARS + TTS
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

from voice import create_voice_note

# =========================================================
# DATABASE INITIALIZATION
# =========================================================

init_subscription_db()


# =========================================================
# STRING HELPERS
# =========================================================

def clean_env_str(val: str, default: str = "") -> str:
    """
    Remove whitespace and hidden Unicode characters
    from environment variables.
    """
    if not val:
        return default

    cleaned = re.sub(
        r'[\u200b\u200c\u200d\u2060\ufeff]',
        '',
        val
    ).strip()

    return cleaned if cleaned else default


def clean_ai_response(text: str) -> str:
    """
    Remove <think> blocks and model control tokens.
    """
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

    text = re.sub(
        r"<\|.*?\|>",
        "",
        text
    )

    return text.strip()


def escape_html(text: str) -> str:
    """
    Safely convert basic Markdown to Telegram HTML.
    """
    if not text:
        return ""

    text = html.escape(text)

    text = re.sub(
        r'\*\*(.*?)\*\*',
        r'<b>\1</b>',
        text
    )

    text = re.sub(
        r'\*(.*?)\*',
        r'<i>\1</i>',
        text
    )

    text = re.sub(
        r'`(.*?)`',
        r'<code>\1</code>',
        text
    )

    return text


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TELEGRAM_BOT_TOKEN = clean_env_str(
    os.environ.get("TELEGRAM_BOT_TOKEN")
)

# AI PROVIDERS
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

# AI PROVIDER
AI_PROVIDER = clean_env_str(
    os.environ.get("AI_PROVIDER"),
    "AUTO"
).upper()

# MODELS
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

# API ENDPOINTS
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
# TELEGRAM STARS SUBSCRIPTION SETTINGS
# =========================================================

MONTHLY_STARS = int(
    os.environ.get("MONTHLY_STARS", "150")
)

THREE_MONTH_STARS = int(
    os.environ.get("THREE_MONTH_STARS", "500")
)

YEARLY_STARS = int(
    os.environ.get("YEARLY_STARS", "2500")
)


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


# =========================================================
# STARTUP VALIDATION
# =========================================================

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing from environment variables."
    )

if not any([
    GROK_API_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY
]):
    raise RuntimeError(
        "No AI API keys configured. "
        "Set GROK_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."
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
# 👑 KING ZARRY AI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are an advanced AI assistant for:
- General questions
- Programming
- Technology
- Trading education
- BTC
- ETH
- SOL
- Forex
- Gold/XAUUSD
- Market analysis
- Image/chart analysis
- Creative writing
- Business ideas

CRITICAL RULES:

1. Never reveal internal reasoning or chain-of-thought.
2. Never output <think> blocks.
3. Never output hidden control tokens.
4. Never fabricate tool calls.
5. Never pretend a tool was used when it was not.
6. Answer directly and clearly.
7. For trading, never guarantee profit.
8. Explain uncertainty and risk.
9. Do not describe financial predictions as guaranteed.
10. Keep answers useful and practical.

You are branded as:

👑 KING ZARRY AI
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

async def send_long_message(message, text: str):

    raw_text = clean_ai_response(text)

    if not raw_text:
        raw_text = "King Zarry AI returned an empty response."

    formatted_text = escape_html(raw_text)

    chunk_size = 3800

    chunks = [
        formatted_text[i:i + chunk_size]
        for i in range(
            0,
            len(formatted_text),
            chunk_size
        )
    ]

    for chunk in chunks:

        try:

            await message.reply_text(
                chunk,
                parse_mode="HTML"
            )

        except Exception:

            plain_chunks = [
                raw_text[i:i + chunk_size]
                for i in range(
                    0,
                    len(raw_text),
                    chunk_size
                )
            ]

            for p_chunk in plain_chunks:

                await message.reply_text(
                    p_chunk,
                    parse_mode=None
                )


# =========================================================
# 🔐 SUBSCRIPTION ACCESS CONTROL
# =========================================================

def user_has_access(user_id: int) -> bool:
    return is_subscribed(user_id)


async def require_subscription(
    update: Update
) -> bool:

    if not update.effective_user:
        return False

    user_id = update.effective_user.id

    if user_has_access(user_id):
        return True

    if update.message:

        await update.message.reply_text(
            "🔒 **KING ZARRY AI VIP**\n\n"
            "Your subscription is not active.\n\n"
            "👑 Subscribe to unlock:\n"
            "• AI Chat\n"
            "• Trading analysis\n"
            "• BTC / ETH / SOL\n"
            "• Gold/XAUUSD\n"
            "• AI Vision\n"
            "• Chart analysis\n"
            "• Advanced AI features\n\n"
            "Use /buy to choose your VIP plan.",
            parse_mode="Markdown"
        )

    return False


# =========================================================
# 🤖 OPENAI-COMPATIBLE REQUEST
# =========================================================

def openai_compatible_request(
    messages,
    api_key,
    base_url,
    model,
    disable_tools=True
):

    if not api_key:
        raise RuntimeError(
            "API key missing for request."
        )

    endpoint = (
        f"{base_url.rstrip('/')}"
        "/chat/completions"
    )

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
            f"API Error ({response.status_code}): "
            f"{error_data}"
        )

    data = response.json()

    try:

        content = (
            data["choices"][0]
            ["message"]["content"]
            .strip()
        )

        if (
            content.startswith('{"name":')
            or content.startswith('{"tool":')
        ):
            content = (
                "I couldn't complete that action, "
                "but I am ready to answer your question "
                "directly."
            )

        return clean_ai_response(content)

    except Exception:

        raise RuntimeError(
            f"Invalid API response structure: {data}"
        )


# =========================================================
# 💎 GEMINI
# =========================================================

def gemini_request(
    prompt: str,
    image_bytes=None,
    mime_type=None
):

    if (
        not GEMINI_API_KEY
        or not GEMINI_SDK_AVAILABLE
    ):
        raise RuntimeError(
            "Gemini SDK unavailable or API key missing."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    if image_bytes:

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )

        contents = [
            (
                f"{SYSTEM_PROMPT}\n\n"
                f"Task: {prompt}"
            ),
            image_part
        ]

    else:

        contents = [
            (
                f"{SYSTEM_PROMPT}\n\n"
                f"USER:\n{prompt}"
            )
        ]

    models_to_try = [
        GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    last_error = None

    for model_name in dict.fromkeys(
        models_to_try
    ):

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    max_output_tokens=2048
                )
            )

            answer = getattr(
                response,
                "text",
                None
            )

            if answer:
                return clean_ai_response(answer)

        except Exception as e:

            last_error = e

    raise RuntimeError(
        f"All Gemini models failed. "
        f"Last error: {last_error}"
    )


# =========================================================
# 🧠 UNIFIED AI ROUTER
# =========================================================

def ask_ai(prompt: str) -> str:

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    if AI_PROVIDER == "GROK":

        return openai_compatible_request(
            messages,
            GROK_API_KEY,
            GROK_BASE_URL,
            GROK_MODEL,
            disable_tools=True
        )

    if AI_PROVIDER == "OPENAI":

        return openai_compatible_request(
            messages,
            OPENAI_API_KEY,
            OPENAI_BASE_URL,
            OPENAI_MODEL,
            disable_tools=True
        )

    if AI_PROVIDER == "GEMINI":

        return gemini_request(prompt)

    errors = []

    # GROQ
    if GROK_API_KEY:

        try:

            return openai_compatible_request(
                messages,
                GROK_API_KEY,
                GROK_BASE_URL,
                GROK_MODEL,
                disable_tools=True
            )

        except Exception as e:

            errors.append(
                f"Groq: {e}"
            )

    # GEMINI
    if (
        GEMINI_API_KEY
        and GEMINI_SDK_AVAILABLE
    ):

        try:

            return gemini_request(prompt)

        except Exception as e:

            errors.append(
                f"Gemini: {e}"
            )

    # OPENAI
    if OPENAI_API_KEY:

        try:

            return openai_compatible_request(
                messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL,
                disable_tools=True
            )

        except Exception as e:

            errors.append(
                f"OpenAI: {e}"
            )

    raise RuntimeError(
        "All configured AI providers failed.\n"
        + " | ".join(errors)
    )


# =========================================================
# 👁️ AI VISION
# =========================================================

def analyze_image_with_ai(
    image_bytes: bytes,
    mime_type: str,
    prompt: str
) -> str:

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    vision_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url":
                        f"data:{mime_type};"
                        f"base64,{image_base64}"
                    }
                }
            ]
        }
    ]

    errors = []

    # GROQ / compatible vision
    if GROK_API_KEY:

        try:

            vision_model = GROK_MODEL

            return openai_compatible_request(
                vision_messages,
                GROK_API_KEY,
                GROK_BASE_URL,
                vision_model,
                disable_tools=True
            )

        except Exception as e:

            errors.append(
                f"Groq Vision: {e}"
            )

    # GEMINI VISION
    if (
        GEMINI_API_KEY
        and GEMINI_SDK_AVAILABLE
    ):

        try:

            return gemini_request(
                prompt,
                image_bytes,
                mime_type
            )

        except Exception as e:

            errors.append(
                f"Gemini Vision: {e}"
            )

    # OPENAI VISION
    if OPENAI_API_KEY:

        try:

            return openai_compatible_request(
                vision_messages,
                OPENAI_API_KEY,
                OPENAI_BASE_URL,
                OPENAI_MODEL,
                disable_tools=True
            )

        except Exception as e:

            errors.append(
                f"OpenAI Vision: {e}"
            )

    raise RuntimeError(
        "All vision providers failed.\n"
        + " | ".join(errors)
    )


# =========================================================
# 📊 TWELVE DATA
# =========================================================

def get_market_candles(
    symbol,
    interval="30min",
    outputsize=100
):

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY is not configured."
        )

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
            f"Insufficient candle data "
            f"available for {symbol}."
        )

    return candles


# =========================================================
# EMA
# =========================================================

def ema(values, period):

    if (
        not values
        or len(values) < period
    ):
        return 0.0

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


# =========================================================
# RSI
# =========================================================

def rsi(values, period=14):

    if (
        not values
        or len(values) < period + 1
    ):
        return 50.0

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
        return 100.0

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

    elif signal == "SELL":

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

    else:

        stop_loss = current_price

        tp1 = current_price

        tp2 = current_price

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
        "strength": min(
            90,
            max(
                50,
                50 + abs(score) * 10
            )
        ),
    }


# =========================================================
# ANALYZE SYMBOL
# =========================================================

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
# FORMAT TRADING ANALYSIS
# =========================================================

def format_analysis(
    data,
    title="KING ZARRY AI SIGNAL"
):

    return (
        f"🎯 **{title}**\n\n"

        f"📊 **{data['symbol']}**\n"
        f"⏱ Timeframe: **{data['interval']}**\n\n"

        f"{data['direction']} "
        f"**SIGNAL: {data['signal']}**\n"

        f"📈 Trend: **{data['trend']}**\n"

        f"💪 Strength: "
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

        f"EMA9: "
        f"`${data['ema9']:,.2f}`\n"

        f"EMA21: "
        f"`${data['ema21']:,.2f}`\n"

        f"EMA50: "
        f"`${data['ema50']:,.2f}`\n\n"

        "⚠️ This is algorithmic analysis, "
        "not a guaranteed trade.\n"
        "Always use proper risk management."
    )


# =========================================================
# SYMBOL DETECTION
# =========================================================

def detect_market_and_timeframe(
    text
):

    upper = text.upper()

    symbol = "BTC/USD"

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
    }

    for m_symbol, names in markets.items():

        if any(
            name in upper
            for name in names
        ):

            symbol = m_symbol
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


# =========================================================
# IMAGE PROMPT
# =========================================================

def build_image_prompt(
    caption: str
) -> str:

    if caption and caption.strip():

        return (
            "The user attached an image and "
            "gave this request:\n\n"
            f"{caption.strip()}\n\n"
            "Follow the request precisely."
        )

    return (
        "Analyze this image carefully.\n\n"
        "If it is a financial/trading chart, "
        "identify price action, trend, "
        "support/resistance, indicators, "
        "possible setups and invalidation levels.\n\n"
        "If it is a general image, "
        "describe what is visible clearly."
    )


# =========================================================
# 👑 START
# =========================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    subscribed = (
        user
        and is_subscribed(user.id)
    )

    if subscribed:

        status_text = (
            "🟢 **VIP ACTIVE**"
        )

    else:

        status_text = (
            "🔴 **VIP NOT ACTIVE**"
        )

    welcome_text = (
        "👑 **WELCOME TO KING ZARRY AI**\n\n"

        "Your AI assistant for trading, "
        "programming, vision and more.\n\n"

        f"{status_text}\n\n"

        "💎 **VIP Commands**\n"
        "• `/buy` - Buy VIP subscription\n"
        "• `/status` - Check subscription\n"
        "• `/history` - Payment history\n\n"

        "🤖 **AI Commands**\n"
        "• `/ask <question>`\n"
        "• `/tts <text>`\n"
        "• `/signal BTC`\n"
        "• `/btc`\n"
        "• `/eth`\n"
        "• `/sol`\n"
        "• `/xau`\n\n"

        "📸 Send a photo/chart for AI Vision.\n\n"

        "👑 **KING ZARRY AI**"
    )

    await send_long_message(
        update.message,
        welcome_text
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await start_command(
        update,
        context
    )


# =========================================================
# 💎 BUY SUBSCRIPTION
# =========================================================

async def buy_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message

    text = (
        "👑 **KING ZARRY AI VIP**\n\n"
        "Choose your subscription:\n\n"

        f"🌟 **Monthly**\n"
        f"30 days • {MONTHLY_STARS} Stars\n\n"

        f"🔥 **3 Months**\n"
        f"90 days • {THREE_MONTH_STARS} Stars\n\n"

        f"💎 **Yearly**\n"
        f"365 days • {YEARLY_STARS} Stars\n\n"

        "Use one of these commands:\n"
        "`/monthly`\n"
        "`/3month`\n"
        "`/yearly`"
    )

    await message.reply_text(
        text,
        parse_mode="Markdown"
    )


# =========================================================
# SEND STAR INVOICE
# =========================================================

async def send_subscription_invoice(
    update: Update,
    plan_key: str
):

    if plan_key not in SUBSCRIPTION_PLANS:

        await update.message.reply_text(
            "❌ Invalid subscription plan."
        )

        return

    plan = SUBSCRIPTION_PLANS[
        plan_key
    ]

    payload = (
        f"kingzarry_subscription:"
        f"{plan_key}"
    )

    prices = [
        LabeledPrice(
            plan["name"],
            plan["stars"]
        )
    ]

    await update.message.reply_invoice(
        title=plan["name"],
        description=plan["description"],
        payload=payload,
        currency="XTR",
        prices=prices,
        provider_token="",
        start_parameter=(
            f"kingzarry-{plan_key}"
        )
    )


# =========================================================
# MONTHLY
# =========================================================

async def monthly_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await send_subscription_invoice(
        update,
        "monthly"
    )


# =========================================================
# 3 MONTH
# =========================================================

async def three_month_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await send_subscription_invoice(
        update,
        "3month"
    )


# =========================================================
# YEARLY
# =========================================================

async def yearly_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await send_subscription_invoice(
        update,
        "yearly"
    )


# =========================================================
# 💳 PRE-CHECKOUT
# =========================================================

async def precheckout_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.pre_checkout_query

    payload = query.invoice_payload

    if not payload.startswith(
        "kingzarry_subscription:"
    ):

        await query.answer(
            ok=False,
            error_message=(
                "Invalid subscription payment."
            )
        )

        return

    plan_key = payload.split(
        ":",
        1
    )[1]

    if plan_key not in SUBSCRIPTION_PLANS:

        await query.answer(
            ok=False,
            error_message=(
                "This subscription plan "
                "is no longer available."
            )
        )

        return

    expected_amount = SUBSCRIPTION_PLANS[
        plan_key
    ]["stars"]

    if query.currency != "XTR":

        await query.answer(
            ok=False,
            error_message=(
                "Payment must be made using "
                "Telegram Stars."
            )
        )

        return

    if query.total_amount != expected_amount:

        await query.answer(
            ok=False,
            error_message=(
                "Payment amount does not "
                "match the subscription plan."
            )
        )

        return

    await query.answer(
        ok=True
    )


# =========================================================
# 💰 SUCCESSFUL PAYMENT
# =========================================================

async def successful_payment_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message
    payment = message.successful_payment
    user = update.effective_user

    if not payment or not user:
        return

    payload = payment.invoice_payload

    if not payload.startswith(
        "kingzarry_subscription:"
    ):
        return

    plan_key = payload.split(
        ":",
        1
    )[1]

    if plan_key not in SUBSCRIPTION_PLANS:

        await message.reply_text(
            "⚠️ Payment received, but the "
            "subscription plan could not be identified.\n\n"
            "Please contact support."
        )

        return

    plan = SUBSCRIPTION_PLANS[
        plan_key
    ]

    payment_id = (
        payment.telegram_payment_charge_id
    )

    username = (
        user.username
        or user.full_name
        or str(user.id)
    )

    # -----------------------------------------------------
    # Record payment FIRST.
    # If it already exists, do not activate twice.
    # -----------------------------------------------------

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

        await message.reply_text(
            "⚠️ This payment has already "
            "been processed.\n\n"
            "Your existing VIP subscription "
            "remains protected."
        )

        return

    # -----------------------------------------------------
    # ACTIVATE SUBSCRIPTION
    # -----------------------------------------------------

    expires_at = activate_subscription(
        user_id=user.id,
        username=username,
        days=plan["days"],
        plan=plan_key,
        payment_method="telegram_stars",
        payment_id=payment_id,
    )

    await message.reply_text(
        "🎉 **PAYMENT SUCCESSFUL!**\n\n"

        "👑 Welcome to **KING ZARRY AI VIP**!\n\n"

        f"📦 Plan: **{plan['name']}**\n"
        f"⭐ Paid: **{payment.total_amount} Stars**\n\n"

        f"🗓 VIP expires:\n"
        f"`{expires_at.strftime('%Y-%m-%d %H:%M UTC')}`\n\n"

        "✅ Your VIP access is now active.\n\n"

        "Use `/ask` to talk to King Zarry AI.\n"
        "Use `/signal BTC` for a market signal.",
        parse_mode="Markdown"
    )


# =========================================================
# 📅 SUBSCRIPTION STATUS
# =========================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    if user.id in ADMIN_IDS:

        await update.message.reply_text(
            "👑 **KING ZARRY ADMIN**\n\n"
            "🟢 Unlimited access",
            parse_mode="Markdown"
        )

        return

    subscription = get_subscription(
        user.id
    )

    if not subscription:

        await update.message.reply_text(
            "🔴 **NO ACTIVE SUBSCRIPTION**\n\n"
            "Use `/buy` to subscribe.",
            parse_mode="Markdown"
        )

        return

    if not is_subscribed(user.id):

        await update.message.reply_text(
            "🔴 **SUBSCRIPTION EXPIRED**\n\n"
            "Use `/buy` to renew your VIP access.",
            parse_mode="Markdown"
        )

        return

    expires_at = subscription.get(
        "expires_at"
    )

    plan = subscription.get(
        "plan",
        "VIP"
    )

    await update.message.reply_text(
        "🟢 **VIP ACTIVE**\n\n"
        f"👑 Plan: **{plan}**\n"
        f"📅 Expires: `{expires_at}`\n\n"
        "Enjoy King Zarry AI VIP.",
        parse_mode="Markdown"
    )


# =========================================================
# 💳 PAYMENT HISTORY
# =========================================================

async def history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    history = get_payment_history(
        user.id,
        10
    )

    if not history:

        await update.message.reply_text(
            "💳 No payment history found."
        )

        return

    lines = [
        "💳 **KING ZARRY PAYMENT HISTORY**\n"
    ]

    for row in history:

        plan = row[0]
        method = row[1]
        amount = row[2]
        currency = row[3]
        created = row[4]

        lines.append(
            f"• **{plan}** | "
            f"{amount} {currency}\n"
            f"  {method}\n"
            f"  {created}\n"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown"
    )


# =========================================================
# 👑 ADMIN GRANT
# =========================================================

async def grant_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user or user.id not in ADMIN_IDS:

        await update.message.reply_text(
            "⛔ Admin only."
        )

        return

    if len(context.args) < 2:

        await update.message.reply_text(
            "Usage:\n"
            "/grant USER_ID DAYS\n\n"
            "Example:\n"
            "/grant 123456789 30"
        )

        return

    try:

        target_user_id = int(
            context.args[0]
        )

        days = int(
            context.args[1]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ USER_ID and DAYS must be numbers."
        )

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
        "✅ **Subscription granted.**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"📅 Days: **{days}**\n"
        f"⏰ Expires: `{expires_at}`",
        parse_mode="Markdown"
    )


# =========================================================
# 👑 ADMIN REVOKE
# =========================================================

async def revoke_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user or user.id not in ADMIN_IDS:

        await update.message.reply_text(
            "⛔ Admin only."
        )

        return

    if not context.args:

        await update.message.reply_text(
            "Usage:\n"
            "/revoke USER_ID"
        )

        return

    try:

        target_user_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Invalid USER_ID."
        )

        return

    deactivate_subscription(
        target_user_id
    )

    await update.message.reply_text(
        "🚫 **Subscription revoked.**\n\n"
        f"User ID: `{target_user_id}`",
        parse_mode="Markdown"
    )


# =========================================================
# /ASK
# =========================================================

async def ask_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await require_subscription(
        update
    ):
        return

    question = " ".join(
        context.args
    ).strip()

    if not question:

        await update.message.reply_text(
            "⚠️ Usage:\n"
            "/ask What is Bitcoin?"
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

        # Send corresponding voice note
        await update.message.chat.send_action("record_voice")

        voice_file = None
        try:
            voice_file = await create_voice_note(answer)
            with open(voice_file, "rb") as voice:
                await update.message.reply_voice(
                    voice=voice,
                    caption="👑 King Zarry AI Voice Response"
                )
        except Exception as v_err:
            print(f"⚠️ Voice generation failed during /ask: {v_err}")
        finally:
            if voice_file and os.path.exists(voice_file):
                try:
                    os.remove(voice_file)
                except OSError:
                    pass

    except Exception as e:

        await update.message.reply_text(
            f"❌ AI Error:\n{e}"
        )


# =========================================================
# /TTS
# =========================================================

async def tts_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await require_subscription(
        update
    ):
        return

    text = " ".join(
        context.args
    ).strip()

    if not text:

        await update.message.reply_text(
            "⚠️ Usage:\n"
            "/tts Hello from King Zarry AI!"
        )

        return

    await update.message.chat.send_action(
        "record_voice"
    )

    voice_file = None
    try:

        voice_file = await create_voice_note(text)

        with open(voice_file, "rb") as voice:
            await update.message.reply_voice(
                voice=voice,
                caption="👑 King Zarry AI"
            )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Voice Error:\n{e}"
        )

    finally:

        if voice_file and os.path.exists(voice_file):
            try:
                os.remove(voice_file)
            except OSError:
                pass


# =========================================================
# QUICK SYMBOL COMMAND
# =========================================================

async def quick_symbol_command(
    symbol: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await require_subscription(
        update
    ):
        return

    await update.message.chat.send_action(
        "typing"
    )

    try:

        data = await asyncio.to_thread(
            analyze_symbol,
            symbol,
            "15min"
        )

        await send_long_message(
            update.message,
            format_analysis(
                data,
                f"{symbol} ANALYSIS"
            )
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Market Data Error:\n{e}"
        )


# =========================================================
# SIGNAL
# =========================================================

async def signal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await require_subscription(
        update
    ):
        return

    raw_args = " ".join(
        context.args
    ).strip()

    symbol, timeframe = (
        detect_market_and_timeframe(
            raw_args
            if raw_args
            else "BTC"
        )
    )

    tf_normalized = normalize_timeframe(
        timeframe
    )

    await update.message.chat.send_action(
        "typing"
    )

    try:

        data = await asyncio.to_thread(
            analyze_symbol,
            symbol,
            tf_normalized
        )

        await send_long_message(
            update.message,
            format_analysis(
                data,
                f"{symbol} SIGNAL"
            )
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Signal Error:\n{e}"
        )


# =========================================================
# TEXT MESSAGE
# =========================================================

async def text_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if (
        not update.message
        or not update.message.text
    ):
        return

    if not await require_subscription(
        update
    ):
        return

    user_text = (
        update.message.text
        .strip()
    )

    if user_text.startswith("/"):
        return

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

        await update.message.reply_text(
            f"❌ AI Error:\n{e}"
        )


# =========================================================
# 📸 PHOTO MESSAGE
# =========================================================

async def photo_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not await require_subscription(
        update
    ):
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

        prompt = build_image_prompt(
            caption
        )

        result = await asyncio.to_thread(
            lambda: analyze_image_with_ai(
                bytes(image_bytes),
                "image/jpeg",
                prompt
            )
        )

        await send_long_message(
            update.message,
            result
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Vision Error:\n{e}"
        )


# =========================================================
# /PAYSUPPORT
# =========================================================

async def paysupport_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "💳 **KING ZARRY AI PAYMENT SUPPORT**\n\n"
        "If you paid but your VIP subscription "
        "did not activate, contact the bot administrator "
        "and provide your Telegram payment information.\n\n"
        "Use /status to check your subscription.",
        parse_mode="Markdown"
    )


# =========================================================
# GLOBAL ERROR HANDLER
# =========================================================

async def global_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "⚠️ Telegram Bot Error:",
        context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "👑 ======================================="
    )

    print(
        "👑 KING ZARRY AI TELEGRAM"
    )

    print(
        "👑 AI + TRADING + VIP SUBSCRIPTIONS"
    )

    print(
        "👑 ======================================="
    )

    print(
        f"⭐ Monthly: {MONTHLY_STARS} XTR"
    )

    print(
        f"⭐ 3 Month: {THREE_MONTH_STARS} XTR"
    )

    print(
        f"⭐ Yearly: {YEARLY_STARS} XTR"
    )

    print(
        f"👑 Admins: {len(ADMIN_IDS)}"
    )

    application = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # ERROR HANDLER
    # -----------------------------------------------------

    application.add_error_handler(
        global_error_handler
    )

    # -----------------------------------------------------
    # BASIC COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # -----------------------------------------------------
    # SUBSCRIPTION COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "buy",
            buy_command
        )
    )

    application.add_handler(
        CommandHandler(
            "monthly",
            monthly_command
        )
    )

    application.add_handler(
        CommandHandler(
            "3month",
            three_month_command
        )
    )

    application.add_handler(
        CommandHandler(
            "yearly",
            yearly_command
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command
        )
    )

    application.add_handler(
        CommandHandler(
            "history",
            history_command
        )
    )

    application.add_handler(
        CommandHandler(
            "paysupport",
            paysupport_command
        )
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "grant",
            grant_command
        )
    )

    application.add_handler(
        CommandHandler(
            "revoke",
            revoke_command
        )
    )

    # -----------------------------------------------------
    # AI & VOICE
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "ask",
            ask_command
        )
    )

    application.add_handler(
        CommandHandler(
            "tts",
            tts_command
        )
    )

    application.add_handler(
        CommandHandler(
            "signal",
            signal_command
        )
    )

    # -----------------------------------------------------
    # QUICK MARKET COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "btc",
            lambda u, c:
            quick_symbol_command(
                "BTC/USD",
                u,
                c
            )
        )
    )

    application.add_handler(
        CommandHandler(
            "eth",
            lambda u, c:
            quick_symbol_command(
                "ETH/USD",
                u,
                c
            )
        )
    )

    application.add_handler(
        CommandHandler(
            "sol",
            lambda u, c:
            quick_symbol_command(
                "SOL/USD",
                u,
                c
            )
        )
    )

    application.add_handler(
        CommandHandler(
            "xau",
            lambda u, c:
            quick_symbol_command(
                "XAU/USD",
                u,
                c
            )
        )
    )

    # -----------------------------------------------------
    # TELEGRAM STARS PAYMENT
    # -----------------------------------------------------

    application.add_handler(
        PreCheckoutQueryHandler(
            precheckout_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment_handler
        )
    )

    # -----------------------------------------------------
    # PHOTO / VISION
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            photo_message_handler
        )
    )

    # -----------------------------------------------------
    # NORMAL TEXT
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_message_handler
        )
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    print(
        "📡 Telegram polling active."
    )

    print(
        "👑 KING ZARRY AI IS ONLINE!"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":
    main()
