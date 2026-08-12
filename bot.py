import os
import requests
import discord
from discord import app_commands

# =========================================================
# ENVIRONMENT
# =========================================================

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

BINANCE_URL = "https://api.binance.com"


# =========================================================
# BINANCE DATA
# =========================================================

def get_binance_klines(symbol="BTCUSDT", interval="15m", limit=100):
    response = requests.get(
        f"{BINANCE_URL}/api/v3/klines",
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()


def get_binance_price(symbol):
    response = requests.get(
        f"{BINANCE_URL}/api/v3/ticker/price",
        params={"symbol": symbol},
        timeout=10
    )

    response.raise_for_status()
    return float(response.json()["price"])


# =========================================================
# INDICATORS
# =========================================================

def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

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
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# =========================================================
# MARKET ANALYSIS
# =========================================================

def analyze_symbol(symbol="BTCUSDT", interval="15m"):

    candles = get_binance_klines(symbol, interval, 100)

    closes = [float(c[4]) for c in candles]
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]

    current_price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    current_rsi = rsi(closes, 14)

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])

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

    if current_rsi > 50 and current_rsi < 70:
        score += 1
    elif current_rsi < 50 and current_rsi > 30:
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
        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 2.5

    elif signal == "SELL":

        risk = recent_high - entry

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry + risk
        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 2.5

    else:

        stop_loss = recent_low
        tp1 = recent_high
        tp2 = recent_high

    confidence = min(90, max(50, 50 + abs(score) * 10))

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
        "confidence": confidence
    }


# =========================================================
# DISCORD BOT
# =========================================================

class KingZarryAI(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):

        await self.tree.sync()


intents = discord.Intents.default()

client = KingZarryAI()


# =========================================================
# /START
# =========================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🤖 **Welcome to King Zarry AI! 👑**\n\n"
        "Your AI market-analysis engine is online. 📡📈\n\n"
        "Commands:\n"
        "📊 `/signal` - BTC trading signal\n"
        "₿ `/btc` - Bitcoin analysis\n"
        "🪙 `/crypto` - Crypto prices\n"
        "🟡 `/gold` - Gold analysis\n"
        "❓ `/help` - Show commands"
    )


# =========================================================
# /HELP
# =========================================================

@client.tree.command(
    name="help",
    description="Show King Zarry AI commands"
)
async def help_command(interaction: discord.Interaction):

    await interaction.response.send_message(
        "👑 **KING ZARRY AI COMMANDS**\n\n"
        "📊 `/signal` - BTC signal\n"
        "₿ `/btc` - BTC analysis\n"
        "🪙 `/crypto` - Crypto market\n"
        "🟡 `/gold` - Gold analysis"
    )


# =========================================================
# /SIGNAL
# =========================================================

@client.tree.command(
    name="signal",
    description="Generate a BTC 15-minute trading analysis"
)
async def signal(interaction: discord.Interaction):

    await interaction.response.defer()

    try:

        data = analyze_symbol("BTCUSDT", "15m")

        message = (
            "👑 **KING ZARRY AI SIGNAL**\n\n"
            "₿ **BTC/USDT**\n"
            "⏱ Timeframe: **15M**\n\n"

            f"{data['direction']} **SIGNAL: {data['signal']}**\n"
            f"📈 Trend: **{data['trend']}**\n"
            f"🔥 Confidence: **{data['confidence']}%**\n\n"

            f"💰 Entry: `${data['entry']:,.2f}`\n"
            f"🛑 Stop Loss: `${data['stop_loss']:,.2f}`\n"
            f"🎯 TP1: `${data['tp1']:,.2f}`\n"
            f"🎯 TP2: `${data['tp2']:,.2f}`\n\n"

            f"📊 RSI: **{data['rsi']:.2f}**\n"
            f"EMA 9: `${data['ema9']:,.2f}`\n"
            f"EMA 21: `${data['ema21']:,.2f}`\n"
            f"EMA 50: `${data['ema50']:,.2f}`\n\n"

            "📡 Data: Binance\n"
            "⚠️ Algorithmic analysis only. "
            "No signal guarantees profit."
        )

        await interaction.followup.send(message)

    except Exception as e:

        print("SIGNAL ERROR:", repr(e))

        await interaction.followup.send(
            "❌ I couldn't retrieve Binance market data."
        )


# =========================================================
# /BTC
# =========================================================

@client.tree.command(
    name="btc",
    description="Analyze Bitcoin"
)
async def btc(interaction: discord.Interaction):

    await interaction.response.defer()

    try:

        data = analyze_symbol("BTCUSDT", "15m")

        await interaction.followup.send(
            "₿ **BTC/USDT ANALYSIS**\n\n"
            f"💰 Price: `${data['price']:,.2f}`\n"
            f"📈 Trend: **{data['trend']}**\n"
            f"{data['direction']} Signal: **{data['signal']}**\n"
            f"📊 RSI: **{data['rsi']:.2f}**\n"
            f"🔥 Confidence: **{data['confidence']}%**"
        )

    except Exception:

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
async def crypto(interaction: discord.Interaction):

    await interaction.response.defer()

    try:

        btc_price = get_binance_price("BTCUSDT")
        eth_price = get_binance_price("ETHUSDT")
        sol_price = get_binance_price("SOLUSDT")

        await interaction.followup.send(
            "🪙 **KING ZARRY AI CRYPTO MARKET**\n\n"
            f"₿ BTC: `${btc_price:,.2f}`\n"
            f"Ξ ETH: `${eth_price:,.2f}`\n"
            f"◎ SOL: `${sol_price:,.2f}`\n\n"
            "📡 Binance market data: **CONNECTED**"
        )

    except Exception:

        await interaction.followup.send(
            "❌ Unable to retrieve crypto market data."
        )


# =========================================================
# /GOLD
# =========================================================

@client.tree.command(
    name="gold",
    description="Gold market analysis"
)
async def gold(interaction: discord.Interaction):

    await interaction.response.send_message(
        "🟡 **GOLD ANALYSIS**\n\n"
        "Gold needs a separate XAU/USD market-data feed.\n\n"
        "⏳ Gold data integration is coming next."
    )


# =========================================================
# START
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_BOT_TOKEN is missing."
    )

print("👑 King Zarry AI Discord bot is starting...")

client.run(TOKEN)
