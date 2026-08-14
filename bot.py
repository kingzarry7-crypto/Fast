import os
import re
import asyncio
import discord

from discord import app_commands

from memory import Memory
from ai_engine import AIEngine

from market import (
    get_price,
    analyze_market
)

from voice import speak


# ==========================================================
# 👑 KING ZARRY AI
# DISCORD BOT
# ==========================================================

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "king_zarry_memory.db"
)


# ==========================================================
# CHECK CONFIGURATION
# ==========================================================

print()
print("=" * 60)
print("👑 KING ZARRY AI DISCORD")
print("=" * 60)

print(
    "🔑 Discord token:",
    "FOUND" if DISCORD_BOT_TOKEN else "MISSING"
)

print(
    "🏠 Guild ID:",
    DISCORD_GUILD_ID if DISCORD_GUILD_ID else "GLOBAL COMMANDS"
)

print(
    "💾 Database:",
    DATABASE_PATH
)

print("=" * 60)


if not DISCORD_BOT_TOKEN:
    raise RuntimeError(
        "❌ DISCORD_BOT_TOKEN is missing from environment variables."
    )


# ==========================================================
# MEMORY + AI ENGINE
# ==========================================================

memory = Memory(
    DATABASE_PATH
)

ai = AIEngine(
    memory
)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def detect_market_and_timeframe(text: str):
    """Detects crypto/forex symbols and timeframes in message text."""
    upper = text.upper()
    symbol = "UNKNOWN"
    markets = {
        "XAU/USD": ["XAU/USD", "XAUUSD", "GOLD"],
        "BTC/USD": ["BTC/USD", "BTCUSDT", "BTC"],
        "ETH/USD": ["ETH/USD", "ETHUSDT", "ETH"],
        "SOL/USD": ["SOL/USD", "SOLUSDT", "SOL"],
        "EUR/USD": ["EUR/USD", "EURUSD"],
        "GBP/USD": ["GBP/USD", "GBPUSD"],
    }
    for m_symbol, names in markets.items():
        if any(name in upper for name in names):
            symbol = m_symbol
            break

    match = re.search(r"\b(1m|5m|15m|30m|1h|2h|4h|1d)\b", text.lower())
    timeframe = match.group(1) if match else "15m"
    return symbol, timeframe


def build_chart_prompt(symbol: str, timeframe: str) -> str:
    """Builds chart analysis prompt for vision processing."""
    return f"""
Analyze this trading chart screenshot.

Market: {symbol}
Timeframe: {timeframe}

Only use information actually visible in the image.

Inspect and summarize:
1. Overall trend & Market structure
2. Support & Resistance levels
3. Candlestick patterns & EMA/RSI indicators (if visible)
4. Probable BUY or SELL setups with Entry, Invalidation (Stop Loss), and Take Profit targets.

Format output clearly with King Zarry AI headers.
"""


def safe_float(val, default=0.0):
    """Safely convert numerical/string responses to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def format_market(data: dict, title: str) -> str:
    """Safely formats market dictionary into a readable Discord message."""
    symbol = data.get('symbol', 'UNKNOWN')
    timeframe = data.get('timeframe', '15m')
    signal = data.get('signal', 'NEUTRAL')
    trend = data.get('trend', 'NEUTRAL')

    price = safe_float(data.get('price'))
    support = safe_float(data.get('support'))
    resistance = safe_float(data.get('resistance'))
    ema9 = safe_float(data.get('ema9'))
    ema21 = safe_float(data.get('ema21'))
    ema50 = safe_float(data.get('ema50'))
    rsi = safe_float(data.get('rsi'))

    return (
        f"👑 **{title}**\n\n"
        f"📊 Market: **{symbol}**\n"
        f"⏱ Timeframe: **{timeframe}**\n\n"
        f"🎯 Signal: **{signal}**\n"
        f"📈 Trend: **{trend}**\n\n"
        f"💰 Price: `${price:,.5f}`\n\n"
        f"🟢 Support: `${support:,.5f}`\n"
        f"🔴 Resistance: `${resistance:,.5f}`\n\n"
        f"EMA 9: `${ema9:,.5f}`\n"
        f"EMA 21: `${ema21:,.5f}`\n"
        f"EMA 50: `${ema50:,.5f}`\n"
        f"RSI: **{rsi:.2f}**\n\n"
        "⚠️ Algorithmic analysis only. No guaranteed profit."
    )


# ==========================================================
# DISCORD CLIENT
# ==========================================================

class KingZarryAI(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    # ======================================================
    # COMMAND SYNC
    # ======================================================

    async def setup_hook(self):
        try:
            if DISCORD_GUILD_ID:
                guild = discord.Object(id=int(DISCORD_GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"✅ Synced {len(synced)} commands to Discord server ({DISCORD_GUILD_ID}).")
            else:
                synced = await self.tree.sync()
                print(f"✅ Synced {len(synced)} global commands.")

        except Exception as e:
            print("❌ COMMAND SYNC ERROR:", repr(e))

    # ======================================================
    # READY
    # ======================================================

    async def on_ready(self):
        print()
        print("=" * 60)
        print("👑 KING ZARRY AI IS ONLINE")
        print("=" * 60)
        print(f"🤖 Logged in as: {self.user}")
        print(f"🆔 Bot ID: {self.user.id}")
        print("💬 Normal messages: ENABLED")
        print("📸 Multi-Provider Vision: ENABLED")
        print("🧠 AI memory: ENABLED")
        print("📊 Market analysis: ENABLED")
        print("🎙️ Voice: ENABLED")
        print("=" * 60)
        print("🚀 KING ZARRY AI READY")
        print("=" * 60)
        print()

    # ======================================================
    # NORMAL DISCORD MESSAGES
    # ======================================================

    async def on_message(self, message: discord.Message):

        # Ignore messages from bots (including self)
        if message.author.bot:
            return

        print(f"💬 Message from {message.author}: {message.content[:100]}")

        content = message.content.strip()

        # Remove bot mention from prompt content
        if self.user:
            content = content.replace(f"<@{self.user.id}>", "")
            content = content.replace(f"<@!{self.user.id}>", "")
            content = content.strip()

        # Extract Image Attachments
        images = [
            attachment
            for attachment in message.attachments
            if attachment.content_type and attachment.content_type.startswith("image/")
        ]

        # Ignore completely empty messages without attachments
        if not content and not images:
            return

        try:
            async with message.channel.typing():
                image_tuple = None

                if images:
                    attachment = images[0]
                    if attachment.size > (10 * 1024 * 1024):
                        await message.reply(
                            "❌ Image size must be below 10 MB.",
                            mention_author=False
                        )
                        return

                    image_bytes = await attachment.read()
                    mime_type = attachment.content_type or "image/png"
                    image_tuple = (mime_type, image_bytes)

                    symbol, timeframe = detect_market_and_timeframe(content)
                    if symbol != "UNKNOWN" or any(kw in content.upper() for kw in ["CHART", "SIGNAL", "ANALYSIS"]):
                        content = build_chart_prompt(symbol, timeframe)
                    elif not content:
                        content = "Analyze this image carefully and explain what you see in detail."

                # AI Engine Execution (Run off-thread)
                answer = await asyncio.to_thread(
                    ai.ask,
                    str(message.author.id),
                    content,
                    image_tuple
                )

            if not answer:
                answer = "❌ I couldn't generate a response."

            await send_chunks(message, answer)

        except Exception as e:
            print("\n❌ AI MESSAGE ERROR:", repr(e), "\n")
            try:
                await message.reply(
                    f"❌ **King Zarry AI error**\n\n`{str(e)[:1500]}`",
                    mention_author=False
                )
            except Exception as reply_error:
                print("❌ Could not send error reply:", repr(reply_error))


# ==========================================================
# SEND LONG DISCORD MESSAGE (CHUNKS)
# ==========================================================

async def send_chunks(destination, text: str):
    if not text:
        text = "❌ King Zarry AI returned an empty response."

    chunks = [text[i:i + 1900] for i in range(0, len(text), 1900)]

    for chunk in chunks:
        await destination.reply(chunk, mention_author=False)


async def send_followup_chunks(interaction: discord.Interaction, text: str):
    if not text:
        text = "❌ AI returned an empty response."

    chunks = [text[i:i + 1900] for i in range(0, len(text), 1900)]

    for chunk in chunks:
        await interaction.followup.send(chunk)


# ==========================================================
# CREATE CLIENT
# ==========================================================

client = KingZarryAI()


# ==========================================================
# SLASH COMMANDS
# ==========================================================

@client.tree.command(name="start", description="Start King Zarry AI")
async def start(interaction: discord.Interaction):
    await interaction.response.send_message(
        "👑 **KING ZARRY AI IS ONLINE**\n\n"
        "🧠 AI Agent (Grok / OpenAI / Gemini)\n"
        "📊 Market Intelligence\n"
        "📸 Multi-Provider Vision\n"
        "💾 Memory\n"
        "🎙️ Voice\n"
        "🔧 AI Tools\n\n"
        "**COMMANDS**\n\n"
        "`/ask` Ask the AI\n"
        "`/stats` Bot analytics\n"
        "`/btc` Bitcoin analysis\n"
        "`/gold` Gold analysis\n"
        "`/crypto` Crypto prices\n"
        "`/analyze` Market analysis\n"
        "`/clear_memory` Clear your AI memory\n"
        "`/join` Join voice\n"
        "`/say` Speak\n"
        "`/leave` Leave voice\n\n"
        "💬 Or simply send me a normal message or upload a chart."
    )


@client.tree.command(name="stats", description="Check King Zarry AI user analytics")
async def stats(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        stats_data = await asyncio.to_thread(memory.get_user_stats)
        total_guilds = len(client.guilds) if client.guilds else 1

        embed = discord.Embed(
            title="👑 King Zarry AI Statistics",
            color=discord.Color.gold()
        )
        embed.add_field(name="📊 Servers / Guilds", value=str(total_guilds), inline=True)
        embed.add_field(name="👥 Total Unique Users (DB)", value=str(stats_data.get("total_users", 0)), inline=True)
        embed.add_field(name="⚡ Active Users (Last 24h)", value=str(stats_data.get("active_24h", 0)), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        print("❌ /stats ERROR:", repr(e))
        await interaction.followup.send(f"❌ Stats error:\n`{str(e)[:1200]}`", ephemeral=True)


@client.tree.command(name="ask", description="Ask King Zarry AI anything")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        answer = await asyncio.to_thread(
            ai.ask,
            str(interaction.user.id),
            question
        )
        await send_followup_chunks(interaction, answer)
    except Exception as e:
        print("❌ /ask ERROR:", repr(e))
        await interaction.followup.send(f"❌ AI error:\n`{str(e)[:1200]}`")


@client.tree.command(name="btc", description="Analyze Bitcoin")
async def btc(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, "BTC/USD", "15m")
        await interaction.followup.send(format_market(data, "₿ KING ZARRY AI BTC"))
    except Exception as e:
        print("❌ /btc ERROR:", repr(e))
        await interaction.followup.send(f"❌ BTC error:\n`{str(e)[:1200]}`")


@client.tree.command(name="gold", description="Analyze Gold / XAUUSD")
async def gold(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, "XAU/USD", "15m")
        await interaction.followup.send(format_market(data, "🟡 KING ZARRY AI GOLD"))
    except Exception as e:
        print("❌ /gold ERROR:", repr(e))
        await interaction.followup.send(f"❌ Gold error:\n`{str(e)[:1200]}`")


@client.tree.command(name="crypto", description="Show crypto prices")
async def crypto(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        btc_price = safe_float(await asyncio.to_thread(get_price, "BTC/USD"))
        eth_price = safe_float(await asyncio.to_thread(get_price, "ETH/USD"))
        sol_price = safe_float(await asyncio.to_thread(get_price, "SOL/USD"))

        await interaction.followup.send(
            "👑 **KING ZARRY AI CRYPTO**\n\n"
            f"₿ BTC: `${btc_price:,.2f}`\n"
            f"Ξ ETH: `${eth_price:,.2f}`\n"
            f"◎ SOL: `${sol_price:,.2f}`"
        )
    except Exception as e:
        print("❌ /crypto ERROR:", repr(e))
        await interaction.followup.send(f"❌ Crypto error:\n`{str(e)[:1200]}`")


@client.tree.command(name="analyze", description="Analyze a market")
@app_commands.describe(
    symbol="Example: BTC/USD",
    timeframe="1m, 5m, 15m, 30m, 1h, 4h, 1d"
)
async def analyze(interaction: discord.Interaction, symbol: str, timeframe: str = "15m"):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, symbol.upper().strip(), timeframe)
        await interaction.followup.send(format_market(data, "👑 KING ZARRY AI ANALYSIS"))
    except Exception as e:
        print("❌ /analyze ERROR:", repr(e))
        await interaction.followup.send(f"❌ Analysis error:\n`{str(e)[:1200]}`")


@client.tree.command(name="clear_memory", description="Clear your King Zarry AI memory")
async def clear_memory(interaction: discord.Interaction):
    try:
        await asyncio.to_thread(memory.clear, str(interaction.user.id))
        await interaction.response.send_message("🧹 Your King Zarry AI memory has been cleared.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Memory error: `{str(e)[:1000]}`")


@client.tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ Join a voice channel first.")
        return

    channel = interaction.user.voice.channel
    await interaction.response.defer()

    try:
        voice = interaction.guild.voice_client
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            await channel.connect()

        await interaction.followup.send(f"🎙️ Joined **{channel.name}**.")
    except Exception as e:
        print("❌ /join ERROR:", repr(e))
        await interaction.followup.send(f"❌ Voice error:\n`{str(e)[:1200]}`")


@client.tree.command(name="say", description="Make King Zarry AI speak")
@app_commands.describe(text="Text to speak")
async def say(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    voice = interaction.guild.voice_client

    if not voice or not voice.is_connected():
        await interaction.followup.send("❌ Use `/join` first.")
        return

    try:
        await speak(voice, text)
        await interaction.followup.send("🎙️ Speaking now. 👑")
    except Exception as e:
        print("❌ /say ERROR:", repr(e))
        await interaction.followup.send(f"❌ Voice error:\n`{str(e)[:1200]}`")


@client.tree.command(name="leave", description="Leave voice channel")
async def leave(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if not voice or not voice.is_connected():
        await interaction.response.send_message("❌ I'm not in a voice channel.")
        return

    await voice.disconnect()
    await interaction.response.send_message("🚪 King Zarry AI left voice.")


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("👑 STARTING KING ZARRY AI DISCORD")
    print("=" * 60)

    client.run(DISCORD_BOT_TOKEN)
