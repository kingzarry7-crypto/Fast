import os
import requests
import discord
from discord import app_commands

# =========================================================
# ENVIRONMENT
# =========================================================

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

TWELVE_DATA_URL = "https://api.twelvedata.com"


# =========================================================
# TWELVE DATA
# =========================================================

def get_market_candles(
    symbol,
    interval="15min",
    outputsize=100
):
    """
    Get OHLC market data from Twelve Data.

    Twelve Data returns newest candles first,
    so the data is reversed before analysis.
    """

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
            "apikey": TWELVE_DATA_API_KEY
        },
        timeout=15
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
    """
    Get the latest price from Twelve Data.
    """

    if not TWELVE_DATA_API_KEY:
        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing."
        )

    response = requests.get(
        f"{TWELVE_DATA_URL}/price",
        params={
            "symbol": symbol,
            "apikey": TWELVE_DATA_API_KEY
        },
        timeout=15
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

    # =====================================================
    # EMA 9 vs EMA 21
    # =====================================================

    if ema9 > ema21:
        score += 1
    else:
        score -= 1

    # =====================================================
    # EMA 21 vs EMA 50
    # =====================================================

    if ema21 > ema50:
        score += 1
    else:
        score -= 1

    # =====================================================
    # PRICE vs EMA 21
    # =====================================================

    if current_price > ema21:
        score += 1
    else:
        score -= 1

    # =====================================================
    # RSI
    # =====================================================

    if 50 < current_rsi < 70:

        score += 1

    elif 30 < current_rsi < 50:

        score -= 1

    # =====================================================
    # SIGNAL
    # =====================================================

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

    # =====================================================
    # RISK MANAGEMENT
    # =====================================================

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

    # =====================================================
    # SIGNAL STRENGTH
    # =====================================================

    signal_strength = min(
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
        "strength": signal_strength
    }


# =========================================================
# ANALYZE SYMBOL
# =========================================================

def analyze_symbol(
    symbol,
    interval="15min"
):

    candles = get_market_candles(
        symbol=symbol,
        interval=interval,
        outputsize=100
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

    data = analyze_market(
        closes,
        highs,
        lows
    )

    data["symbol"] = symbol

    return data


# =========================================================
# DISCORD BOT
# =========================================================

class KingZarryAI(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

    async def setup_hook(self):

        await self.tree.sync()


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
        "🪙 `/crypto` - Crypto prices\n"
        "🟡 `/gold` - XAU/USD analysis\n"
        "❓ `/help` - Show commands"
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
        "🪙 `/crypto` - BTC / ETH / SOL prices\n"
        "🟡 `/gold` - XAU/USD 15M analysis"
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

        message = (
            "👑 **KING ZARRY AI SIGNAL**\n\n"

            "₿ **BTC/USD**\n"
            "⏱ Timeframe: **15M**\n\n"

            f"{data['direction']} "
            f"**SIGNAL: {data['signal']}**\n"

            f"📈 Trend: **{data['trend']}**\n"

            f"🔥 Signal Strength: "
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

            "📡 Data: **Twelve Data**\n"

            "⚠️ Algorithmic analysis only. "
            "No signal guarantees profit."
        )

        await interaction.followup.send(
            message
        )

    except Exception as e:

        print(
            "SIGNAL ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **BTC data couldn't be retrieved.**\n\n"
            "Check the Railway deployment logs."
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
            "₿ **BTC/USD ANALYSIS**\n\n"

            f"💰 Price: "
            f"`${data['price']:,.2f}`\n"

            f"📈 Trend: "
            f"**{data['trend']}**\n"

            f"{data['direction']} Signal: "
            f"**{data['signal']}**\n"

            f"🔥 Signal Strength: "
            f"**{data['strength']}%**\n\n"

            f"📊 RSI: "
            f"**{data['rsi']:.2f}**\n"

            f"EMA 9: "
            f"`${data['ema9']:,.2f}`\n"

            f"EMA 21: "
            f"`${data['ema21']:,.2f}`\n"

            f"EMA 50: "
            f"`${data['ema50']:,.2f}`\n\n"

            "📡 Data: **Twelve Data**"
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
            "❌ **Unable to retrieve crypto market data.**\n\n"
            "Check the Railway deployment logs."
        )


# =========================================================
# /GOLD
# =========================================================

@client.tree.command(
    name="gold",
    description="Analyze XAU/USD gold on 15-minute timeframe"
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

        message = (
            "👑 **KING ZARRY AI GOLD SIGNAL**\n\n"

            "🟡 **XAU/USD**\n"
            "⏱ Timeframe: **15M**\n\n"

            f"{data['direction']} "
            f"**SIGNAL: {data['signal']}**\n"

            f"📈 Trend: "
            f"**{data['trend']}**\n"

            f"🔥 Signal Strength: "
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

            "📡 Data: **Twelve Data**\n"

            "⚠️ Algorithmic analysis only. "
            "No signal guarantees profit."
        )

        await interaction.followup.send(
            message
        )

    except Exception as e:

        print(
            "GOLD ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **Gold data couldn't be retrieved.**\n\n"
            "Check the Railway deployment logs."
        )


# =========================================================
# /ANALYZE
# =========================================================

@client.tree.command(
    name="analyze",
    description="Analyze a Twelve Data market symbol"
)
@app_commands.describe(
    symbol="Example: BTC/USD, XAU/USD, EUR/USD",
    timeframe="Example: 15min, 1h, 4h"
)
async def analyze(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15min"
):

    await interaction.response.defer()

    try:

        symbol = symbol.upper().strip()

        data = analyze_symbol(
            symbol,
            timeframe
        )

        await interaction.followup.send(
            "👑 **KING ZARRY AI MARKET ANALYSIS**\n\n"

            f"📊 **{symbol}**\n"
            f"⏱ Timeframe: **{timeframe}**\n\n"

            f"{data['direction']} "
            f"**SIGNAL: {data['signal']}**\n"

            f"📈 Trend: "
            f"**{data['trend']}**\n"

            f"🔥 Signal Strength: "
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

            "📡 Data: **Twelve Data**\n"

            "⚠️ Algorithmic analysis only. "
            "No signal guarantees profit."
        )

    except Exception as e:

        print(
            "ANALYZE ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            "❌ **Unable to analyze that market.**\n\n"
            "Check the symbol and timeframe, then try again."
        )


# =========================================================
# START BOT
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing."
    )


if not TWELVE_DATA_API_KEY:

    raise RuntimeError(
        "TWELVE_DATA_API_KEY is missing."
    )


print(
    "👑 King Zarry AI Discord bot is starting..."
)

client.run(TOKEN)
