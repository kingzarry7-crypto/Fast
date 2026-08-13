import asyncio
import discord

from discord import app_commands

from config import (
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD_ID,
    DATABASE_PATH
)

from memory import Memory

from ai_engine import AIEngine

from market import (
    get_price,
    analyze_market
)

from voice import speak


# ==========================================================
# KING ZARRY AI 👑
# ==========================================================

memory = Memory(
    DATABASE_PATH
)

ai = AIEngine(
    memory
)


class KingZarryAI(
    discord.Client
):

    def __init__(self):

        intents = discord.Intents.default()

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

            commands = await self.tree.sync(
                guild=guild
            )

            print(
                f"👑 Synced {len(commands)} "
                f"guild commands."
            )

        else:

            commands = await self.tree.sync()

            print(
                f"👑 Synced {len(commands)} "
                f"global commands."
            )

    async def on_ready(self):

        print()
        print("=" * 50)
        print("👑 KING ZARRY AI")
        print("🚀 ONLINE")
        print("=" * 50)
        print(
            f"🤖 Logged in as {self.user}"
        )
        print("=" * 50)

    async def on_message(
        self,
        message
    ):

        if message.author.bot:
            return

        content = message.content.strip()

        if self.user:

            content = content.replace(
                f"<@{self.user.id}>",
                ""
            )

            content = content.replace(
                f"<@!{self.user.id}>",
                ""
            ).strip()

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

        if not content and not images:
            return

        if not content:

            content = (
                "Analyze this image carefully."
            )

        try:

            async with message.channel.typing():

                image = None

                if images:

                    attachment = images[0]

                    if attachment.size > 10 * 1024 * 1024:

                        await message.reply(
                            "❌ Image must be below 10 MB.",
                            mention_author=False
                        )

                        return

                    image_bytes = (
                        await attachment.read()
                    )

                    image = (
                        attachment.content_type
                        or "image/png",
                        image_bytes
                    )

                answer = await asyncio.to_thread(

                    ai.ask,

                    str(message.author.id),

                    content,

                    image
                )

            await send_chunks(
                message,
                answer
            )

        except Exception as e:

            print(
                "❌ AI ERROR:",
                repr(e)
            )

            await message.reply(
                "❌ King Zarry AI encountered an error:\n"
                f"`{str(e)[:1000]}`",
                mention_author=False
            )


client = KingZarryAI()


async def send_chunks(
    destination,
    text
):

    chunks = [
        text[i:i + 1900]
        for i in range(
            0,
            len(text),
            1900
        )
    ]

    for chunk in chunks:

        if hasattr(
            destination,
            "reply"
        ):

            await destination.reply(
                chunk,
                mention_author=False
            )

        else:

            await destination.followup.send(
                chunk
            )


# ==========================================================
# /START
# ==========================================================

@client.tree.command(
    name="start",
    description="Start King Zarry AI"
)
async def start(interaction):

    await interaction.response.send_message(

        "👑 **KING ZARRY AI IS ONLINE**\n\n"

        "🧠 AI Agent\n"
        "📊 Market Intelligence\n"
        "📸 Vision\n"
        "💾 Memory\n"
        "🎙️ Voice\n"
        "🔧 AI Tools\n\n"

        "**COMMANDS**\n\n"

        "`/ask` Ask the AI\n"
        "`/btc` Bitcoin analysis\n"
        "`/gold` Gold analysis\n"
        "`/crypto` Crypto prices\n"
        "`/analyze` Market analysis\n"
        "`/clear_memory` Clear your AI memory\n"
        "`/join` Join voice\n"
        "`/say` Speak\n"
        "`/leave` Leave voice\n\n"

        "💬 Or simply send me a message."
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
    interaction,
    question: str
):

    await interaction.response.defer()

    try:

        answer = await asyncio.to_thread(

            ai.ask,

            str(interaction.user.id),

            question
        )

        await interaction.followup.send(
            answer[:1900]
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ AI error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /BTC
# ==========================================================

@client.tree.command(
    name="btc",
    description="Analyze Bitcoin"
)
async def btc(interaction):

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

        await interaction.followup.send(
            f"❌ BTC error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /GOLD
# ==========================================================

@client.tree.command(
    name="gold",
    description="Analyze Gold / XAUUSD"
)
async def gold(interaction):

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

        await interaction.followup.send(
            f"❌ Gold error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /CRYPTO
# ==========================================================

@client.tree.command(
    name="crypto",
    description="Show crypto prices"
)
async def crypto(interaction):

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

        await interaction.followup.send(
            f"❌ Crypto error: `{str(e)[:1000]}`"
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
    interaction,
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

        await interaction.followup.send(
            f"❌ Analysis error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /CLEAR_MEMORY
# ==========================================================

@client.tree.command(
    name="clear_memory",
    description="Clear your King Zarry AI memory"
)
async def clear_memory(interaction):

    memory.clear(
        str(interaction.user.id)
    )

    await interaction.response.send_message(
        "🧹 Your King Zarry AI memory has been cleared."
    )


# ==========================================================
# /JOIN
# ==========================================================

@client.tree.command(
    name="join",
    description="Join your voice channel"
)
async def join(interaction):

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

        await interaction.followup.send(
            f"❌ Voice error: `{str(e)[:1000]}`"
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
    interaction,
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

        await interaction.followup.send(
            f"❌ Voice error: `{str(e)[:1000]}`"
        )


# ==========================================================
# /LEAVE
# ==========================================================

@client.tree.command(
    name="leave",
    description="Leave voice channel"
)
async def leave(interaction):

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
        f"⏱ Timeframe: **{data['timeframe']}**\n\n"

        f"🎯 Signal: **{data['signal']}**\n"
        f"📈 Trend: **{data['trend']}**\n\n"

        f"💰 Price: `${data['price']:,.5f}`\n\n"

        f"🟢 Support: "
        f"`${data['support']:,.5f}`\n"

        f"🔴 Resistance: "
        f"`${data['resistance']:,.5f}`\n\n"

        f"EMA 9: `${data['ema9']:,.5f}`\n"
        f"EMA 21: `${data['ema21']:,.5f}`\n"
        f"EMA 50: `${data['ema50']:,.5f}`\n"
        f"RSI: **{data['rsi']:.2f}**\n\n"

        "⚠️ Algorithmic analysis only. "
        "No guaranteed profit."
    )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    print("👑 Starting King Zarry AI...")

    client.run(
        DISCORD_BOT_TOKEN
    )
