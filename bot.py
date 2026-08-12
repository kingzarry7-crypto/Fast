import os
import re
import base64
import asyncio
import requests
import discord

from discord import app_commands


# =========================================================
# ENVIRONMENT
# =========================================================

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

TWELVE_DATA_URL = "https://api.twelvedata.com"
OPENAI_URL = "https://api.openai.com/v1/responses"

OPENAI_MODEL = os.environ.get(
    "OPENAI_MODEL",
    "gpt-4.1-mini"
)


# =========================================================
# VALIDATION
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing in Railway Variables."
    )

if not TWELVE_DATA_API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY is missing in Railway Variables."
    )

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing in Railway Variables."
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
    timeframe = timeframe.lower().strip()

    return TIMEFRAME_MAP.get(
        timeframe,
        timeframe
    )


# =========================================================
# DISCORD MESSAGE HELPER
# =========================================================

async def send_long_message(
    channel,
    text,
    reference=None
):
    """
    Discord messages have a 2000 character limit.
    Split long AI responses safely.
    """

    if not text:
        text = "❌ AI returned an empty response."

    chunks = []

    while len(text) > 1900:
        split_at = text.rfind(
            "\n",
            0,
            1900
        )

        if split_at < 500:
            split_at = 1900

        chunks.append(
            text[:split_at]
        )

        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    first = True

    for chunk in chunks:

        if first and reference is not None:
            await reference.reply(
                chunk,
                mention_author=False
            )
            first = False

        else:
            await channel.send(chunk)


async def send_interaction_message(
    interaction,
    text
):
    """
    Discord interaction responses also have limits.
    """

    if not text:
        text = "❌ AI returned an empty response."

    chunks = []

    while len(text) > 1900:

        split_at = text.rfind(
            "\n",
            0,
            1900
        )

        if split_at < 500:
            split_at = 1900

        chunks.append(
            text[:split_at]
        )

        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    await interaction.followup.send(
        chunks[0]
    )

    for chunk in chunks[1:]:
        await interaction.channel.send(chunk)


# =========================================================
# TWELVE DATA
# =========================================================

def get_market_candles(
    symbol,
    interval="15min",
    outputsize=100
):

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
                "Twelve Data returned an error."
            )
        )

    if "values" not in data:
        raise RuntimeError(
            f"Unexpected Twelve Data response: {data}"
        )

    candles = list(
        reversed(data["values"])
    )

    if len(candles) < 50:
        raise RuntimeError(
            f"Not enough market data for {symbol}."
        )

    return candles


def get_market_price(symbol):

    response = requests.get(
        f"{TWELVE_DATA_URL}/price",
        params={
            "symbol": symbol,
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
                "Twelve Data returned an error."
            )
        )

    if "price" not in data:
        raise RuntimeError(
            f"Unexpected price response: {data}"
        )

    return float(data["price"])


# =========================================================
# INDICATORS
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

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(abs(change))

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

        risk = entry - recent_low

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry - risk
        tp1 = entry + (risk * 1.5)
        tp2 = entry + (risk * 2.5)

    elif signal == "SELL":

        risk = recent_high - entry

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry + risk
        tp1 = entry - (risk * 1.5)
        tp2 = entry - (risk * 2.5)

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


# =========================================================
# FORMAT MARKET ANALYSIS
# =========================================================

def format_analysis(
    data,
    title="KING ZARRY AI SIGNAL"
):

    return (
        f"👑 **{title}**\n\n"

        f"📊 **{data['symbol']}**\n"
        f"⏱ Timeframe: **{data['interval']}**\n\n"

        f"{data['direction']} "
        f"**SIGNAL: {data['signal']}**\n"

        f"📈 Trend: **{data['trend']}**\n"

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

        f"📊 RSI: **{data['rsi']:.2f}**\n"

        f"EMA 9: "
        f"`${data['ema9']:,.2f}`\n"

        f"EMA 21: "
        f"`${data['ema21']:,.2f}`\n"

        f"EMA 50: "
        f"`${data['ema50']:,.2f}`\n\n"

        "📡 Data: **Twelve Data**\n"
        "⚠️ Algorithmic analysis only. "
        "No signal guarantees profit."
    )


# =========================================================
# OPENAI TEXT AI
# =========================================================

def extract_openai_text(data):

    text = data.get("output_text")

    if text:
        return text.strip()

    pieces = []

    for item in data.get(
        "output",
        []
    ):

        for content in item.get(
            "content",
            []
        ):

            if content.get(
                "type"
            ) == "output_text":

                value = content.get(
                    "text",
                    ""
                )

                if value:
                    pieces.append(value)

    if pieces:
        return "\n".join(pieces).strip()

    raise RuntimeError(
        "OpenAI returned no text."
    )


def ask_ai(prompt):

    headers = {
        "Authorization": (
            f"Bearer {OPENAI_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are King Zarry AI 👑. "
                            "You are a helpful AI assistant "
                            "with strong knowledge of trading, "
                            "crypto, forex, gold, technical "
                            "analysis and general questions. "
                            "Answer the user's actual question. "
                            "Be clear and useful. "
                            "For trading questions, explain "
                            "risk and never guarantee profit. "
                            "Do not pretend to have live prices "
                            "unless live market data was supplied."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            },
        ],
    }

    response = requests.post(
        OPENAI_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )

    if not response.ok:

        try:
            error_data = response.json()

        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"OpenAI API error: {error_data}"
        )

    data = response.json()

    return extract_openai_text(data)


# =========================================================
# OPENAI CHART IMAGE ANALYSIS
# =========================================================

def analyze_chart_image(
    image_bytes,
    symbol="Unknown",
    timeframe="Unknown"
):

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = f"""
You are King Zarry AI 👑.

Analyze this uploaded trading chart.

Market:
{symbol}

Timeframe:
{timeframe}

Only use information that is actually visible
in the image.

Analyse:

1. Overall trend
2. Market structure
3. Higher highs and higher lows
4. Lower highs and lower lows
5. Support
6. Resistance
7. Breakout or breakdown
8. Candlestick behaviour
9. EMA if visible
10. RSI if visible
11. Possible BUY / SELL / WAIT setup
12. Entry zone
13. Invalidation / stop area
14. TP1
15. TP2
16. Main reason
17. Risk

Use this format:

👑 KING ZARRY AI CHART ANALYSIS

📊 Market:
⏱ Timeframe:

🎯 Signal:
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

Do not invent exact prices that cannot be
read from the image.

If information is unclear, say so.

Never claim a trade is guaranteed.
"""

    headers = {
        "Authorization": (
            f"Bearer {OPENAI_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are King Zarry AI. "
                            "You carefully analyse trading "
                            "screenshots. "
                            "Never invent information that "
                            "cannot be seen."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                    {
                        "type": "input_image",
                        "image_url": (
                            "data:image/png;base64,"
                            + image_base64
                        ),
                    },
                ],
            },
        ],
    }

    response = requests.post(
        OPENAI_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    if not response.ok:

        try:
            error_data = response.json()

        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"OpenAI image API error: {error_data}"
        )

    data = response.json()

    return extract_openai_text(data)


# =========================================================
# DETECT MARKET / TIMEFRAME
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
            "BITCOIN",
            "BTC",
        ],

        "ETH/USD": [
            "ETH/USD",
            "ETHUSDT",
            "ETHEREUM",
            "ETH",
        ],

        "SOL/USD": [
            "SOL/USD",
            "SOLUSDT",
            "SOLANA",
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
        r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b",
        text.lower()
    )

    if match:
        timeframe = match.group(1)

    return symbol, timeframe


# =========================================================
# DISCORD BOT
# =========================================================

class KingZarryAI(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        # Required for normal messages.
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
                id=int(DISCORD_GUILD_ID)
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
            f"👑 Logged in as {self.user}"
        )

        print(
            f"🆔 Bot ID: {self.user.id}"
        )

        print(
            "📡 King Zarry AI is ONLINE."
        )

        print(
            "💬 Normal message chat: ENABLED"
        )

        print(
            "📸 Image analysis: ENABLED"
        )


    async def on_message(
        self,
        message: discord.Message
    ):

        # -------------------------------------------------
        # IGNORE ALL BOTS
        # -------------------------------------------------

        if message.author.bot:
            return


        # -------------------------------------------------
        # IMAGE MESSAGE
        # -------------------------------------------------

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

            try:

                async with message.channel.typing():

                    symbol, timeframe = (
                        detect_market_and_timeframe(
                            message.content
                        )
                    )

                    attachment = image_attachments[0]

                    if attachment.size > (
                        10 * 1024 * 1024
                    ):

                        await message.reply(
                            "❌ Chart image is too large. "
                            "Please keep it under 10 MB.",
                            mention_author=False
                        )

                        return

                    image_bytes = (
                        await attachment.read()
                    )

                    result = await asyncio.to_thread(
                        analyze_chart_image,
                        image_bytes,
                        symbol,
                        timeframe
                    )

                await send_long_message(
                    message.channel,
                    result,
                    reference=message
                )

            except Exception as e:

                print(
                    "❌ IMAGE ERROR:",
                    repr(e)
                )

                await message.reply(
                    "❌ I couldn't analyse that image.\n\n"
                    f"**Error:** `{str(e)[:1200]}`",
                    mention_author=False
                )

            return


        # -------------------------------------------------
        # NORMAL MESSAGE
        # -------------------------------------------------

        content = message.content.strip()

        if not content:
            return


        # Remove bot mention if present.

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
                "Hello King Zarry AI. "
                "Are you online?"
            )


        # -------------------------------------------------
        # AI CHAT
        # -------------------------------------------------

        try:

            async with message.channel.typing():

                answer = await asyncio.to_thread(
                    ask_ai,
                    content
                )

            await send_long_message(
                message.channel,
                answer,
                reference=message
            )

        except Exception as e:

            print(
                "❌ CHAT ERROR:",
                repr(e)
            )

            await message.reply(
                "❌ I couldn't process that request "
                "right now.\n\n"
                f"**Error:** `{str(e)[:1200]}`",
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

        "🤖 **WELCOME TO KING ZARRY AI 👑**\n\n"

        "Your AI market-analysis engine "
        "is online. 📡📈\n\n"

        "**COMMANDS**\n\n"

        "📊 `/signal` - BTC 15M signal\n"
        "₿ `/btc` - Bitcoin analysis\n"
        "🪙 `/crypto` - Crypto prices\n"
        "🟡 `/gold` - Gold analysis\n"
        "📈 `/analyze` - Live market analysis\n"
        "📸 `/analyze_chart` - Chart analysis\n"
        "💬 Normal message - AI chat\n"
        "📷 Upload chart - AI chart analysis"
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

        "👑 **KING ZARRY AI**\n\n"

        "📊 `/signal` - BTC signal\n"
        "₿ `/btc` - BTC analysis\n"
        "🪙 `/crypto` - Crypto prices\n"
        "🟡 `/gold` - Gold analysis\n"
        "📈 `/analyze` - Live market\n"
        "📸 `/analyze_chart` - Chart screenshot\n\n"

        "💬 **AI CHAT**\n"
        "Send a normal message and I will answer.\n\n"

        "📷 **IMAGE ANALYSIS**\n"
        "Upload a trading chart and I will analyse it."
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

        await send_interaction_message(
            interaction,
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

        await interaction.followup.send(
            "❌ BTC data couldn't be retrieved."
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

        await send_interaction_message(
            interaction,
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

        await interaction.followup.send(
            "❌ Unable to retrieve BTC analysis."
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
            f"`${sol_price:,.2f}`\n\n"

            "📡 Data: **Twelve Data**"
        )

    except Exception as e:

        print(
            "❌ CRYPTO ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ Unable to retrieve crypto "
            "market data."
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

        await send_interaction_message(
            interaction,
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

        await interaction.followup.send(
            "❌ Gold data couldn't be retrieved."
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

        symbol = symbol.upper().strip()

        interval = normalize_timeframe(
            timeframe
        )

        data = await asyncio.to_thread(
            analyze_symbol,
            symbol,
            interval
        )

        await send_interaction_message(
            interaction,
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

        await interaction.followup.send(
            "❌ Unable to analyse that market.\n"
            "Check the symbol and timeframe."
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

        if not content_type.startswith("image/"):

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

        image_bytes = await image.read()

        result = await asyncio.to_thread(
            analyze_chart_image,
            image_bytes,
            symbol.upper().strip(),
            timeframe
        )

        await send_interaction_message(
            interaction,
            result
        )

    except Exception as e:

        print(
            "❌ CHART ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ I couldn't analyse that chart.\n\n"
            f"**Error:** `{str(e)[:1200]}`"
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

        await send_interaction_message(
            interaction,
            answer
        )

    except Exception as e:

        print(
            "❌ ASK ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ AI chat is unavailable right now.\n\n"
            f"**Error:** `{str(e)[:1200]}`"
        )


# =========================================================
# START BOT
# =========================================================

print(
    "========================================"
)

print(
    "👑 KING ZARRY AI"
)

print(
    "🤖 Starting Discord bot..."
)

print(
    f"🧠 OpenAI model: {OPENAI_MODEL}"
)

print(
    "💬 Text chat: ENABLED"
)

print(
    "📸 Image analysis: ENABLED"
)

print(
    "📊 Market analysis: ENABLED"
)

print(
    "========================================"
)


client.run(TOKEN)
