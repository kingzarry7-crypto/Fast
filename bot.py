import os
import asyncio
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# =========================
# ENVIRONMENT VARIABLES
# =========================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to King Zarry AI! 👑\n\n"
        "Your AI trading assistant is online. 📈\n\n"
        "Commands:\n"
        "/signal - Get trading signal\n"
        "/gold - Gold analysis\n"
        "/btc - Bitcoin analysis\n"
        "/crypto - Crypto analysis\n"
        "/help - Show commands"
    )


# =========================
# HELP
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 KING ZARRY AI HELP 👑\n\n"
        "/start - Start bot\n"
        "/signal - Trading signal\n"
        "/gold - Gold analysis\n"
        "/btc - Bitcoin analysis\n"
        "/crypto - Crypto analysis"
    )


# =========================
# BINANCE PRICE
# =========================

def get_binance_price(symbol):
    url = "https://api.binance.com/api/v3/ticker/price"

    response = requests.get(
        url,
        params={"symbol": symbol},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return float(data["price"])


# =========================
# SIGNAL
# =========================

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        btc = get_binance_price("BTCUSDT")
        eth = get_binance_price("ETHUSDT")

        message = (
            "📊 KING ZARRY AI SIGNAL\n\n"
            f"₿ BTC/USDT: ${btc:,.2f}\n"
            f"Ξ ETH/USDT: ${eth:,.2f}\n\n"
            "🧠 Market engine connected.\n\n"
            "⚠️ This is market analysis, not guaranteed financial advice."
        )

        await update.message.reply_text(message)

    except Exception as e:

        print("Signal error:", e)

        await update.message.reply_text(
            "❌ I couldn't retrieve Binance market data right now.\n"
            "Please try /signal again."
        )


# =========================
# GOLD
# =========================

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🟡 GOLD ANALYSIS\n\n"
        "Gold signal engine is being prepared.\n\n"
        "📊 Binance data connection: ACTIVE\n"
        "⚠️ Gold requires a separate market-data source."
    )


# =========================
# BTC
# =========================

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        price = get_binance_price("BTCUSDT")

        await update.message.reply_text(
            "₿ BTC/USDT\n\n"
            f"💰 Current price: ${price:,.2f}\n\n"
            "📡 Binance market data: CONNECTED\n"
            "🧠 AI analysis engine: ACTIVE"
        )

    except Exception as e:

        print("BTC error:", e)

        await update.message.reply_text(
            "❌ Unable to retrieve BTC price."
        )


# =========================
# CRYPTO
# =========================

async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        btc = get_binance_price("BTCUSDT")
        eth = get_binance_price("ETHUSDT")
        sol = get_binance_price("SOLUSDT")

        await update.message.reply_text(
            "🪙 KING ZARRY AI CRYPTO MARKET\n\n"
            f"₿ BTC: ${btc:,.2f}\n"
            f"Ξ ETH: ${eth:,.2f}\n"
            f"◎ SOL: ${sol:,.2f}\n\n"
            "📡 Binance data: CONNECTED\n"
            "🧠 Analysis engine: ACTIVE"
        )

    except Exception as e:

        print("Crypto error:", e)

        await update.message.reply_text(
            "❌ Unable to retrieve crypto market data."
        )


# =========================
# MAIN
# =========================

async def main():

    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing from Render Environment Variables."
        )

    if BINANCE_API_KEY:
        print("Binance key: OK")
    else:
        print("Binance key: NOT SET")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("crypto", crypto))

    print("King Zarry AI is running...")

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
