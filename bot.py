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


# ==========================================================
# DISCORD CLIENT
# ==========================================================

class KingZarryAI(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        # IMPORTANT FOR NORMAL MESSAGES
        intents.message_content = True

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )

    # ======================================================
    # COMMAND SYNC
    # ======================================================

    async def setup_hook(self):

        try:

            if DISCORD_GUILD_ID:

                guild = discord.Object(
                    id=int(DISCORD_GUILD_ID)
                )

                # Copy commands to test server
                self.tree.copy_global_to(
                    guild=guild
                )

                synced = await self.tree.sync(
                    guild=guild
                )

                print(
                    f"✅ Synced {len(synced)} "
                    f"commands to Discord server."
                )

            else:

                synced = await self.tree.sync()

                print(
                    f"✅ Synced {len(synced)} "
                    f"global commands."
                )

        except Exception as e:

            print(
                "❌ COMMAND SYNC ERROR:",
                repr(e)
            )

    # ======================================================
    # READY
    # ======================================================

    async def on_ready(self):

        print()
        print("=" * 60)
        print("👑 KING ZARRY AI IS ONLINE")
        print("=" * 60)

        print(
            f"🤖 Logged in as: {self.user}"
        )

        print(
            f"🆔 Bot ID: {self.user.id}"
        )

        print(
            "💬 Normal messages: ENABLED"
        )

        print(
            "📸 Multi-Provider Vision: ENABLED"
        )

        print(
            "🧠 AI memory: ENABLED"
        )

        print(
            "📊 Market analysis: ENABLED"
        )

        print(
            "🎙️ Voice: ENABLED"
        )

        print("=" * 60)
        print("🚀 KING ZARRY AI READY")
        print("=" * 60)
        print()

    # ======================================================
    # NORMAL DISCORD MESSAGES
    # ======================================================

    async def on_message(
        self,
        message
    ):

        # Ignore bots
        if message.author.bot:
            return

        print(
            f"💬 Message from "
            f"{message.author}: "
            f"{message.content[:100]}"
        )

        content = (
            message.content
            .strip()
        )

        # Remove bot mention
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

        # ==================================================
        # FIND IMAGES
        # ==================================================

        images = [

            attachment

            for attachment in message.attachments

            if (
                attachment.content_type
                and
                attachment.content_type.startswith(
                    "image/"
                )
            )
        ]

        # Nothing to process
        if not content and not images:

            return

        try:

            async with message.channel.typing():

                image_tuple = None

                # ==================================================
                # IMAGE PROCESSING
                # ==================================================

                if images:

                    attachment = images[0]

                    if attachment.size > (
                        10 * 1024 * 1024
                    ):

                        await message.reply(
                            "❌ Image must be below 10 MB.",
                            mention_author=False
                        )

                        return

                    image_bytes = (
                        await attachment.read()
                    )

                    mime_type = (
                        attachment.content_type
                        or "image/png"
                    )

                    image_tuple = (
                        mime_type,
                        image_bytes
                    )

                    # Build prompt for trading charts if caption exists or if context fits
                    symbol, timeframe = detect_market_and_timeframe(content)
                    if symbol != "UNKNOWN" or any(kw in content.upper() for kw in ["CHART", "SIGNAL", "ANALYSIS"]):
                        content = build_chart_prompt(symbol, timeframe)
                    elif not content:
                        content = "Analyze this image carefully and explain what you see in detail."

                # ==================================================
                # ASK AI (Supports Grok, OpenAI, Gemini)
                # ==================================================

                answer = await asyncio.to_thread(

                    ai.ask,

                    str(message.author.id),

                    content,

                    image_tuple
                )

            if not answer:

                answer = (
                    "❌ I couldn't generate a response."
                )

            await send_chunks(
                message,
                answer
            )

        except Exception as e:

            print()
            print("❌ AI MESSAGE ERROR")
            print(repr(e))
            print()

            try:

                await message.reply(

                    "❌ **King Zarry AI error**\n\n"
                    f"`{str(e)[:1500]}`",

                    mention_author=False
                )

            except Exception as reply_error:

                print(
                    "❌ Could not send error:",
                    repr(reply_error)
                )


# ==========================================================
# SEND LONG DISCORD MESSAGE
# ==========================================================

async def send_chunks(
    destination,
    text
):

    if not text:

        text = (
            "❌ King Zarry AI returned an empty response."
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

        await destination.reply(
            chunk,
            mention_author=False
        )


# ==========================================================
# CREATE CLIENT (INSTANTIATED BEFORE COMMAND DECORATORS)
# ==========================================================

client = KingZarryAI()


# ==========================================================
# /START
# ==========================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(
    interaction: discord.Interaction
):

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


# ==========================================================
# /STATS
# ==========================================================

@client.tree.command(
    name="stats",
    description="Check King Zarry AI user analytics"
)
async def stats(
    interaction: discord.Interaction
):

    await interaction.response.defer(ephemeral=True)

    try:

        # Non-blocking async wrapper around DB retrieval
        stats_data = await asyncio.to_thread(memory.get_user_stats)

        total_guilds = len(client.guilds) if client.guilds else 1

        embed = discord.Embed(
            title="👑 King Zarry AI Statistics",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="📊 Servers / Guilds",
            value=str(total_guilds),
            inline=True
        )

        embed.add_field(
            name="👥 Total Unique Users (DB)",
            value=str(stats_data.get("total_users", 0)),
            inline=True
        )

        embed.add_field(
            name="⚡ Active Users (Last 24h)",
            value=str(stats_data.get("active_24h", 0)),
            inline=True
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    except Exception as e:

        print("❌ /stats ERROR:", repr(e))

        await interaction.followup.send(
            f"❌ Stats error:\n`{str(e)[:1200]}`",
            ephemeral=True
        )


# ==========================================================
# /ASK
# ==========================================================

@client.tree.command(
    name="ask",
    description="Ask King Zarry AI anything"
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

        answer = await asyncio.to_thread(

            ai.ask,

            str(interaction.user.id),

            question
        )

        await send_followup_chunks(
            interaction,
            answer
        )

    except Exception as e:

        print(
            "❌ /ask ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ AI error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /BTC
# ==========================================================

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

            analyze_market,

            "BTC/USD",

            "15m"
        )

        await interaction.followup.send(

            format_market(
                data,
                "₿ KING ZARRY AI BTC"
            )
        )

    except Exception as e:

        print(
            "❌ /btc ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ BTC error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /GOLD
# ==========================================================

@client.tree.command(
    name="gold",
    description="Analyze Gold / XAUUSD"
)
async def gold(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        data = await asyncio.to_thread(

            analyze_market,

            "XAU/USD",

            "15m"
        )

        await interaction.followup.send(

            format_market(
                data,
                "🟡 KING ZARRY AI GOLD"
            )
        )

    except Exception as e:

        print(
            "❌ /gold ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Gold error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /CRYPTO
# ==========================================================

@client.tree.command(
    name="crypto",
    description="Show crypto prices"
)
async def crypto(
    interaction: discord.Interaction
):

    await interaction.response.defer()

    try:

        btc_price = await asyncio.to_thread(
            get_price,
            "BTC/USD"
        )

        eth_price = await asyncio.to_thread(
            get_price,
            "ETH/USD"
        )

        sol_price = await asyncio.to_thread(
            get_price,
            "SOL/USD"
        )

        await interaction.followup.send(

            "👑 **KING ZARRY AI CRYPTO**\n\n"

            f"₿ BTC: `${btc_price:,.2f}`\n"
            f"Ξ ETH: `${eth_price:,.2f}`\n"
            f"◎ SOL: `${sol_price:,.2f}`"
        )

    except Exception as e:

        print(
            "❌ /crypto ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Crypto error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /ANALYZE
# ==========================================================

@client.tree.command(
    name="analyze",
    description="Analyze a market"
)
@app_commands.describe(
    symbol="Example: BTC/USD",
    timeframe="1m, 5m, 15m, 30m, 1h, 4h, 1d"
)
async def analyze(
    interaction: discord.Interaction,
    symbol: str,
    timeframe: str = "15m"
):

    await interaction.response.defer()

    try:

        data = await asyncio.to_thread(

            analyze_market,

            symbol.upper().strip(),

            timeframe
        )

        await interaction.followup.send(

            format_market(
                data,
                "👑 KING ZARRY AI ANALYSIS"
            )
        )

    except Exception as e:

        print(
            "❌ /analyze ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Analysis error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /CLEAR_MEMORY
# ==========================================================

@client.tree.command(
    name="clear_memory",
    description="Clear your King Zarry AI memory"
)
async def clear_memory(
    interaction: discord.Interaction
):

    try:

        memory.clear(
            str(interaction.user.id)
        )

        await interaction.response.send_message(
            "🧹 Your King Zarry AI memory has been cleared."
        )

    except Exception as e:

        await interaction.response.send_message(
            f"❌ Memory error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /JOIN
# ==========================================================

@client.tree.command(
    name="join",
    description="Join your voice channel"
)
async def join(
    interaction: discord.Interaction
):

    if not interaction.user.voice:

        await interaction.response.send_message(
            "❌ Join a voice channel first."
        )

        return

    channel = (
        interaction.user.voice.channel
    )

    await interaction.response.defer()

    try:

        voice = (
            interaction.guild.voice_client
        )

        if voice:

            await voice.move_to(
                channel
            )

        else:

            await channel.connect()

        await interaction.followup.send(
            f"🎙️ Joined **{channel.name}**."
        )

    except Exception as e:

        print(
            "❌ /join ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Voice error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /SAY
# ==========================================================

@client.tree.command(
    name="say",
    description="Make King Zarry AI speak"
)
@app_commands.describe(
    text="Text to speak"
)
async def say(
    interaction: discord.Interaction,
    text: str
):

    await interaction.response.defer()

    voice = interaction.guild.voice_client

    if not voice:

        await interaction.followup.send(
            "❌ Use `/join` first."
        )

        return

    try:

        await speak(
            voice,
            text
        )

        await interaction.followup.send(
            "🎙️ Speaking now. 👑"
        )

    except Exception as e:

        print(
            "❌ /say ERROR:",
            repr(e)
        )

        await interaction.followup.send(
            f"❌ Voice error:\n`{str(e)[:1200]}`"
        )


# ==========================================================
# /LEAVE
# ==========================================================

@client.tree.command(
    name="leave",
    description="Leave voice channel"
)
async def leave(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

    if not voice:

        await interaction.response.send_message(
            "❌ I'm not in voice."
        )

        return

    await voice.disconnect()

    await interaction.response.send_message(
        "🚪 King Zarry AI left voice."
    )


# ==========================================================
# MARKET FORMAT
# ==========================================================

def format_market(
    data,
    title
):

    return (

        f"👑 **{title}**\n\n"

        f"📊 Market: **{data['symbol']}**\n"

        f"⏱ Timeframe: "
        f"**{data['timeframe']}**\n\n"

        f"🎯 Signal: **{data['signal']}**\n"

        f"📈 Trend: **{data['trend']}**\n\n"

        f"💰 Price: "
        f"`${data['price']:,.5f}`\n\n"

        f"🟢 Support: "
        f"`${data['support']:,.5f}`\n"

        f"🔴 Resistance: "
        f"`${data['resistance']:,.5f}`\n\n"

        f"EMA 9: "
        f"`${data['ema9']:,.5f}`\n"

        f"EMA 21: "
        f"`${data['ema21']:,.5f}`\n"

        f"EMA 50: "
        f"`${data['ema50']:,.5f}`\n"

        f"RSI: "
        f"**{data['rsi']:.2f}**\n\n"

        "⚠️ Algorithmic analysis only. "
        "No guaranteed profit."
    )


# ==========================================================
# FOLLOW-UP CHUNKS
# ==========================================================

async def send_followup_chunks(
    interaction,
    text
):

    if not text:

        text = (
            "❌ AI returned an empty response."
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

        await interaction.followup.send(
            chunk
        )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("👑 STARTING KING ZARRY AI DISCORD")
    print("=" * 60)

    client.run(
        DISCORD_BOT_TOKEN
    )
