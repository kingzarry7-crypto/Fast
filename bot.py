import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")


# =========================================================
# BINANCE MARKET DATA
# =========================================================

BINANCE_URL = "https://api.binance.com"


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

    candles = get_binance_klines(
        symbol=symbol,
        interval=interval,
        limit=100
    )

    closes = [float(candle[4]) for candle in candles]
    highs = [float(candle[2]) for candle in candles]
    lows = [float(candle[3]) for candle in candles]

    current_price = closes[-1]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)

    current_rsi = rsi(closes, 14)

    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])

    score = 0

    # EMA trend
    if ema9 > ema21:
        score += 1
    else:
        score -= 1

    if ema21 > ema50:
        score += 1
    else:
        score -= 1

    # Price position
    if current_price > ema21:
        score += 1
    else:
        score -= 1

    # RSI
    if current_rsi > 50 and current_rsi < 70:
        score += 1
    elif current_rsi < 50 and current_rsi > 30:
        score -= 1

    # Determine signal
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

    # Risk levels
    if signal == "BUY":

        entry = current_price

        risk = entry - recent_low

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry - risk
        take_profit_1 = entry + (risk * 1.5)
        take_profit_2 = entry + (risk * 2.5)

    elif signal == "SELL":

        entry = current_price

        risk = recent_high - entry

        if risk <= 0:
            risk = entry * 0.005

        stop_loss = entry + risk
        take_profit_1 = entry - (risk * 1.5)
        take_profit_2 = entry - (risk * 2.5)

    else:

        entry = current_price
        stop_loss = recent_low
        take_profit_1 = recent_high
        take_profit_2 = recent_high

    confidence = min(95, max(50, 50 + abs(score) * 10))

    return {
        "symbol": symbol,
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
        "tp1": take_profit_1,
        "tp2": take_profit_2,
        "confidence": confidence
    }


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 Welcome to King Zarry AI! 👑\n\n"
        "Your Binance market-analysis engine is online. 📡📈\n\n"
        "Commands:\n"
        "/signal - BTC trading signal\n"
        "/gold - Gold analysis\n"
        "/btc - Bitcoin analysis\n"
        "/crypto - Crypto market\n"
        "/help - Show commands"
    )


# =========================================================
# HELP
# =========================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 KING ZARRY AI 👑\n\n"
        "/signal - BTC signal\n"
        "/btc - Bitcoin analysis\n"
        "/crypto - Crypto market\n"
        "/gold - Gold analysis\n"
        "/start - Start bot\n"
        "/help - Commands"
    )


# =========================================================
# SIGNAL
# =========================================================

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🧠 KING ZARRY AI\n\n"
        "📡 Analyzing Binance 15-minute market data...\n"
        "⏳ Please wait..."
    )

    try:

        data = analyze_symbol("BTCUSDT", "15m")

        message = (
            "👑 KING ZARRY AI SIGNAL\n\n"
            "₿ BTC/USDT\n"
            "⏱ Timeframe: 15M\n\n"

            f"{data['direction']} SIGNAL: {data['signal']}\n"
            f"📈 TREND: {data['trend']}\n"
            f"🔥 CONFIDENCE: {data['confidence']}%\n\n"

            f"💰 Entry: ${data['entry']:,.2f}\n"
            f"🛑 Stop Loss: ${data['stop_loss']:,.2f}\n"
            f"🎯 TP1: ${data['tp1']:,.2f}\n"
            f"🎯 TP2: ${data['tp2']:,.2f}\n\n"

            f"📊 RSI: {data['rsi']:.2f}\n"
            f"EMA 9: ${data['ema9']:,.2f}\n"
            f"EMA 21: ${data['ema21']:,.2f}\n"
            f"EMA 50: ${data['ema50']:,.2f}\n\n"

            "📡 Data source: Binance\n"
            "⚠️ Algorithmic market analysis only. "
            "Signals are not guaranteed profits."
        )

        await update.message.reply_text(message)

    except Exception as e:

        print("SIGNAL ERROR:", repr(e))

        await update.message.reply_text(
            "❌ Signal engine couldn't retrieve Binance data.\n\n"
            "Please try /signal again."
        )


# =========================================================
# BTC
# =========================================================

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        data = analyze_symbol("BTCUSDT", "15m")

        await update.message.reply_text(
            "₿ BTC/USDT ANALYSIS\n\n"
            f"💰 Price: ${data['price']:,.2f}\n"
            f"📈 Trend: {data['trend']}\n"
            f"{data['direction']} Signal: {data['signal']}\n"
            f"📊 RSI: {data['rsi']:.2f}\n"
            f"🔥 Confidence: {data['confidence']}%\n\n"
            "📡 Binance: CONNECTED"
        )

    except Exception as e:

        print("BTC ERROR:", repr(e))

        await update.message.reply_text(
            "❌ Unable to retrieve BTC analysis."
        )


# =========================================================
# CRYPTO
# =========================================================

async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        btc_price = get_binance_price("BTCUSDT")
        eth_price = get_binance_price("ETHUSDT")
        sol_price = get_binance_price("SOLUSDT")

        await update.message.reply_text(
            "🪙 KING ZARRY AI CRYPTO MARKET\n\n"
            f"₿ BTC: ${btc_price:,.2f}\n"
            f"Ξ ETH: ${eth_price:,.2f}\n"
            f"◎ SOL: ${sol_price:,.2f}\n\n"
            "📡 Binance market data: CONNECTED"
        )

    except Exception as e:

        print("CRYPTO ERROR:", repr(e))

        await update.message.reply_text(
            "❌ Unable to retrieve crypto market data."
        )


# =========================================================
# GOLD
# =========================================================

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🟡 GOLD ANALYSIS\n\n"
        "Gold requires a dedicated market-data feed.\n\n"
        "📡 Binance: ACTIVE\n"
        "⏳ Twelve Data integration will provide XAU/USD data."
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    if not TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing from Render Environment Variables."
        )

    if BINANCE_API_KEY:
        print("Binance API key: FOUND")
    else:
        print(
            "Binance API key: NOT SET "
            "(public market data can still be used)"
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("crypto", crypto))
    app.add_handler(CommandHandler("gold", gold))

    print("👑 King Zarry AI is running...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:

        await asyncio.Event().wait()

    finally:

        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
