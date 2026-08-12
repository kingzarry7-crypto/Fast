import os

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TWELVE_DATA_API_KEY = os.environ["TWELVE_DATA_API_KEY"]
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")

print("Telegram token: OK")
print("Twelve Data key: OK")
print("Binance key: OK" if BINANCE_API_KEY else "Binance key: NOT SET")import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to King Zarry AI!\n\n"
        "Your AI trading assistant is online. 👑📈\n\n"
        "Commands:\n"
        "/signal - Trading signal\n"
        "/gold - Gold analysis\n"
        "/btc - Bitcoin analysis\n"
        "/forex - Forex analysis\n"
        "/crypto - Crypto analysis\n"
        "/help - Show commands"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 King Zarry AI Help\n\n"
        "/start - Start the bot\n"
        "/signal - Trading signal\n"
        "/gold - Gold analysis\n"
        "/btc - Bitcoin analysis\n"
        "/forex - Forex analysis\n"
        "/crypto - Crypto analysis"
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 KING ZARRY AI\n\n"
        "⚙️ Signal engine is being connected."
    )


async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟡 XAUUSD / GOLD\n\n"
        "Gold analysis engine is being connected. 📈"
    )


async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "₿ BTC/USD\n\n"
        "Bitcoin analysis engine is being connected. 📊"
    )


async def forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💱 FOREX\n\n"
        "Forex analysis engine is being connected. 📈"
    )


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🪙 CRYPTO\n\n"
        "Crypto analysis engine is being connected. 📊"
    )


async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("forex", forex))
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
