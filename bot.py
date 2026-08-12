import os
import requests
import discord
from discord import app_commands
from openai import OpenAI
# =========================================================
# ENVIRONMENT
# =========================================================

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

TWELVE_DATA_URL = "https://api.twelvedata.com"
OPENAI_URL = "https://api.openai.com/v1/responses"

# You can change this in Railway without changing the code.
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


# =========================================================
# TIMEFRAME CONVERSION
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
    return TIMEFRAME_MAP.get(timeframe, timeframe)


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
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY,
        },
        timeout=15,
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

    candles = list(reversed(data["values"]))

    if len(candles) < 50:
        raise RuntimeError(
            f"Not enough data returned for {symbol}."
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
            "apikey": TWELVE_DATA_API_KEY,
        },
        timeout=15,
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

    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (
            (price - result) * multiplier
        ) + result

    return result


def rsi(values, period=14):

    if len(values) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = values[i] - values[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):

        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# =========================================================
# MARKET ANALYSIS
# =========================================================

def analyze_market(closes, highs, lows):

    if len(closes) < 50:
        raise RuntimeError(
            "Not enough market data for analysis."
        )

    current_price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    current_rsi = rsi(closes, 14)

    if (
        ema9 is None
        or ema21 is None
        or ema50 is None
        or current_rsi is None
    ):
        raise RuntimeError(
            "Indicators could not be calculated."
        )

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])

    score = 0

    # EMA 9 vs EMA 21
    if ema9 > ema21:
        score += 1
    else:
        score -= 1

    # EMA 21 vs EMA 50
    if ema21 > ema50:
        score += 1
    else:
        score -= 1

    # Price vs EMA 21
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

    # This is NOT a probability of winning.
    analysis_strength = min(
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
        "strength": analysis_strength,
    }


def analyze_symbol(symbol, interval="15min"):

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

def format_analysis(data, title="KING ZARRY AI SIGNAL"):

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
# OPENAI CHAT
# =========================================================

def ask_ai(prompt):

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing."
        )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
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
                            "You are King Zarry AI, a trading "
                            "market-analysis assistant. "
                            "Be concise, clear and useful. "
                            "You can explain technical analysis, "
                            "crypto, forex and gold. "
                            "Never claim that a trade is guaranteed "
                            "to win. Distinguish analysis from certainty."
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
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    text = data.get("output_text")

    if text:
        return text

    # Fallback parser
    output = data.get("output", [])

    pieces = []

    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                pieces.append(
                    content.get("text", "")
                )

    if pieces:
        return "\n".join(pieces)

    raise RuntimeError(
        "OpenAI returned no text."
    )


# =========================================================
# OPENAI CHART IMAGE ANALYSIS
# =========================================================

def analyze_chart_image(
    image_bytes,
    symbol,
    timeframe
):

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing."
        )

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    prompt = f"""
You are King Zarry AI.

Analyze the uploaded trading chart.

Market: {symbol}
Timeframe: {timeframe}

Inspect ONLY what is actually visible in the image.

Look for:

1. Overall trend
2. Market structure
3. Higher highs / higher lows
4. Lower highs / lower lows
5. Support
6. Resistance
7. Breakout or breakdown
8. Candlestick behavior
9. EMA information if visible
10. RSI information if visible
11. Possible bullish or bearish setup
12. Important invalidation level
13. Possible entry area
14. Possible TP1 and TP2

Return the analysis in this format:

👑 KING ZARRY AI CHART ANALYSIS

Market:
Timeframe:

Signal: BUY / SELL / WAIT
Trend:

Chart Structure:

Support:
Resistance:

Entry Zone:
Invalidation / Stop:

TP1:
TP2:

Indicators:

Reason:

Risk Warning:

Do not invent exact prices that cannot be read from the image.
If the chart does not provide enough information, say so.
Do not claim the signal is guaranteed.
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
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
                            "You are King Zarry AI, an expert "
                            "chart-analysis assistant. "
                            "Analyze screenshots carefully and "
                            "never invent information that isn't "
                            "visible."
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
        timeout=90,
    )

    response.raise_for_status()

    data = response.json()

    text = data.get("output_text")

    if text:
        return text

    output = data.get("output", [])

    pieces = []

    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                pieces.append(
                    content.get("text", "")
                )

    if pieces:
        return "\n".join(pieces)

    raise RuntimeError(
        "AI returned no chart analysis."
    )


# =========================================================
# DISCORD BOT
# =========================================================

class KingZarryAI(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        # Required for normal chat responses.
        intents.message_content = True

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

    async def setup_hook(self):

        await self.tree.sync()

    async def on_ready(self):

        print(
            f"👑 Logged in as {self.user}"
        )

        print(
            "📡 King Zarry AI is ONLINE."
        )

    async def on_message(
        self,
        message: discord.Message
    ):

        # Ignore itself
        if message.author == self.user:
            return

        # Only respond when the bot is mentioned.
        # This prevents the bot from replying to every
        # conversation in the server.
        if self.user not in message.mentions:
            return

        content = message.content

        # Remove bot mention
        content = content.replace(
            f"<@{self.user.id}>",
            ""
        ).replace(
            f"<@!{self.user.id}>",
            ""
        ).strip()

        if not content:
            content = (
                "Hello King Zarry AI. "
                "What can you help me analyse?"
            )

        try:

            async with message.channel.typing():

                answer = await self._run_ai_chat(
                    content
                )

            await message.reply(
                answer,
                mention_author=False
            )

        except Exception as e:

            print(
                "CHAT ERROR:",
                repr(e)
            )

            await message.reply(
                "❌ I couldn't process that request "
                "right now.",
                mention_author=False
            )

    async def _run_ai_chat(self, content):

        # Run blocking requests away from Discord's
        # event loop.
        import asyncio

        return await asyncio.to_thread(
            ask_ai,
            content
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
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "🤖 **WELCOME TO KING ZARRY AI 👑**\n\n"
        "Your AI market-analysis engine is online. 📡📈\n\n"

        "**Commands:**\n"
        "📊 `/signal` - BTC 15M signal\n"
        "₿ `/btc` - Bitcoin analysis\n"
        "🪙 `/crypto` - BTC / ETH / SOL prices\n"
        "🟡 `/gold` - XAU/USD analysis\n"
        "📸 `/analyze_chart` - Analyse a chart screenshot\n"
        "📈 `/analyze` - Analyse live market data\n"
        "💬 Mention me to chat with the AI"
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

        "📊 `/signal` - BTC 15M signal\n"
        "₿ `/btc` - BTC analysis\n"
        "🪙 `/crypto` - Crypto prices\n"
        "🟡 `/gold` - XAU/USD analysis\n"
        "📈 `/analyze` - Live market analysis\n"
        "📸 `/analyze_chart` - Chart screenshot analysis\n\n"

        "💬 **CHAT**\n"
        "Mention **King Zarry AI** in a message "
        "to ask questions normally."
    )


# =========================================================
# /SIGNAL
# =========================================================

@client.tree.command(
    name="signal",
    description="Generate a BTC 15-minute trading analysis"
)
async def signal(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        data = analyze_symbol(
            "BTC/USD",
            "15min"
        )

        await interaction.followup.send(
            format_analysis(
                data,
                "KING ZARRY AI SIGNAL"
            )
        )

    except Exception as e:

        print(
            "SIGNAL ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **BTC data couldn't be retrieved.**"
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

        data = analyze_symbol(
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
            "❌ **Unable to retrieve BTC analysis.**"
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

        btc_price = get_market_price(
            "BTC/USD"
        )

        eth_price = get_market_price(
            "ETH/USD"
        )

        sol_price = get_market_price(
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
            "CRYPTO ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **Unable to retrieve crypto market data.**"
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

        data = analyze_symbol(
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
            "❌ **Gold data couldn't be retrieved.**"
        )


# =========================================================
# /ANALYZE
# =========================================================

@client.tree.command(
    name="analyze",
    description="Analyse live Twelve Data market data"
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

        data = analyze_symbol(
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
            "❌ **Unable to analyse that market.**\n\n"
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

        # Check image type
        content_type = image.content_type or ""

        if not content_type.startswith("image/"):

            await interaction.followup.send(
                "❌ Please upload a chart image "
                "such as PNG or JPG."
            )

            return

        # Limit image size to 10 MB
        if image.size > 10 * 1024 * 1024:

            await interaction.followup.send(
                "❌ That image is too large. "
                "Please upload an image under 10 MB."
            )

            return

        image_bytes = await image.read()

        import asyncio

        result = await asyncio.to_thread(
            analyze_chart_image,
            image_bytes,
            symbol.upper().strip(),
            timeframe
        )

        await interaction.followup.send(
            result
        )

    except Exception as e:

        print(
            "CHART ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **I couldn't analyse that chart.**\n\n"
            "Make sure `OPENAI_API_KEY` is configured "
            "correctly in Railway."
        )


# =========================================================
# /ASK
# =========================================================

@client.tree.command(
    name="ask",
    description="Ask King Zarry AI a question"
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

        import asyncio

        answer = await asyncio.to_thread(
            ask_ai,
            question
        )

        await interaction.followup.send(
            answer
        )

    except Exception as e:

        print(
            "ASK ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **AI chat is unavailable right now.**"
        )


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing."
    )

if not TWELVE_DATA_API_KEY:
    raise RuntimeError(
        "TWELVE_DATA_API_KEY is missing."
    )

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing."
    )


print(
    "👑 King Zarry AI Discord bot is starting..."
)

client.run(TOKEN)
