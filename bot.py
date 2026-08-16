import os
import re
import io
import asyncio
import tempfile
import base64
import requests
import discord
import fal_client

from discord import app_commands, File
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from groq import Groq
from fal_client import FalClientHTTPError

from memory import Memory
from ai_engine import AIEngine

from market import (
    get_price,
    analyze_market
)

from voice import speak

load_dotenv()

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

# ElevenLabs Environment Variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default voice

# Groq & Fal.ai Video Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FAL_KEY = os.getenv("FAL_KEY")

# Vision & Text Models
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")

TEXT_TO_VIDEO_MODEL = os.getenv("TEXT_TO_VIDEO_MODEL", "fal-ai/ltx-video")
IMAGE_TO_VIDEO_MODEL = os.getenv("IMAGE_TO_VIDEO_MODEL", "fal-ai/ltx-video/image-to-video")

MAX_PROMPT_LENGTH = 1500
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 24 * 1024 * 1024  # 24 MB

ALLOWED_VIDEO_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

# System prompt configured to maintain direct, natural persona without meta-bragging
SYSTEM_VOICE_PROMPT = (
    "You are King Zarry AI, an advanced multi-platform assistant with text, vision, and market analysis capabilities. "
    "Keep responses concise, clear, and direct. "
    "NEVER mention ElevenLabs, Discord, Telegram, or any underlying tools, models, or APIs. "
    "If the user asks if you can speak, talk, or send voice messages, respond naturally with: "
    "'Yes, I can talk to you freely! What would you like me to say?'"
)


# ==========================================================
# CHECK CONFIGURATION
# ==========================================================

print()
print("=" * 60)
print("👑 KING ZARRY AI DISCORD")
print("=" * 60)

print("🔑 Discord token:", "FOUND" if DISCORD_BOT_TOKEN else "MISSING")
print("🎙️ ElevenLabs API Key:", "FOUND" if ELEVENLABS_API_KEY else "MISSING (Fallback enabled)")
print("🔊 Voice Model ID:", ELEVENLABS_MODEL_ID)
print("🧠 Groq API Key:", "FOUND" if GROQ_API_KEY else "MISSING")
print("🎬 Fal.ai Key:", "FOUND" if FAL_KEY else "MISSING")
print("🏠 Guild ID:", DISCORD_GUILD_ID if DISCORD_GUILD_ID else "GLOBAL COMMANDS")
print("💾 Database:", DATABASE_PATH)
print("=" * 60)

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("❌ DISCORD_BOT_TOKEN is missing from environment variables.")

# Initialize API Clients
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ==========================================================
# MEMORY + AI ENGINE
# ==========================================================

memory = Memory(DATABASE_PATH)
ai = AIEngine(memory)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def generate_elevenlabs_voice(text: str) -> io.BytesIO:
    """Generates audio bytes safely without raising StopIteration across threads."""
    if not eleven_client:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured.")

    try:
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128"
        )
        audio_bytes = b"".join([chunk for chunk in audio_generator])
    except Exception as e:
        raise RuntimeError(f"ElevenLabs generation failed: {e}")

    audio_io = io.BytesIO(audio_bytes)
    audio_io.seek(0)
    return audio_io


async def play_voice_in_channel(voice_client: discord.VoiceClient, text: str):
    """Generates speech via ElevenLabs (with fallback) and plays in voice channel."""
    try:
        audio_stream = await asyncio.to_thread(generate_elevenlabs_voice, text)
        audio_source = discord.FFmpegPCMAudio(audio_stream, pipe=True)
        
        if voice_client.is_playing():
            voice_client.stop()
            
        voice_client.play(
            audio_source,
            after=lambda e: print(f"🎙️ Finished playing voice: {e}") if e else None
        )
    except Exception as e:
        print(f"⚠️ ElevenLabs voice error, falling back to default voice module: {e}")
        await speak(voice_client, text)


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
# VIDEO GENERATION HELPERS (FAL.AI INTEGRATION)
# ==========================================================

def enhance_text_prompt(user_prompt: str) -> str:
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    system_prompt = """You are King Zarry's professional cinematic AI video prompt engineer.
Convert the user's simple idea into ONE detailed, high-quality video generation prompt.
Include: subject, environment, action, camera movement, lighting, atmosphere, cinematic style, realistic motion, composition.
Do not explain your answer. Return ONLY the final video prompt. Keep it under 1200 characters."""

    completion = groq_client.chat.completions.create(
        model=GROQ_TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=500,
    )

    result = completion.choices[0].message.content
    if not result:
        raise RuntimeError("Groq returned an empty prompt.")
    return result.strip()


def enhance_image_prompt(image_bytes: bytes, motion_prompt: str) -> str:
    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{encoded}"

    system_prompt = """You are King Zarry's professional image-to-video prompt engineer.
Analyze the supplied image and requested motion.
Create ONE cinematic image-to-video prompt.
Preserve subject identities, faces, clothing, objects, and overall composition while adding natural movement.
Return ONLY the final video prompt under 1200 characters."""

    user_content = [
        {"type": "text", "text": f"User's requested motion:\n{motion_prompt}"},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    completion = groq_client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.6,
        max_tokens=600,
    )

    result = completion.choices[0].message.content
    if not result:
        raise RuntimeError("Groq returned an empty image prompt.")
    return result.strip()


def generate_text_video(prompt: str) -> bytes:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY is not configured.")

    # Execute text-to-video request using Fal.ai
    result = fal_client.subscribe(
        TEXT_TO_VIDEO_MODEL,
        arguments={
            "prompt": prompt
        }
    )

    video_url = result.get("video", {}).get("url")
    if not video_url:
        raise RuntimeError("Fal.ai failed to return a valid video URL.")

    # Download video bytes for Discord attachment
    response = requests.get(video_url, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download video from Fal.ai: {response.status_code}")

    return response.content


def generate_image_video(image_bytes: bytes, prompt: str) -> bytes:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY is not configured.")

    # Upload source image directly to Fal CDN
    image_url = fal_client.upload(image_bytes, "image/jpeg")

    # Execute image-to-video request using Fal.ai
    result = fal_client.subscribe(
        IMAGE_TO_VIDEO_MODEL,
        arguments={
            "image_url": image_url,
            "prompt": prompt
        }
    )

    video_url = result.get("video", {}).get("url")
    if not video_url:
        raise RuntimeError("Fal.ai failed to return a valid video URL.")

    # Download video bytes for Discord attachment
    response = requests.get(video_url, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download video from Fal.ai: {response.status_code}")

    return response.content


def save_video(video_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        temp_file.write(video_bytes)
        return temp_file.name


# ==========================================================
# DISCORD CLIENT
# ==========================================================

class KingZarryAI(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

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
        print("🎙️ ElevenLabs Voice: ENABLED")
        print("🎬 Fal.ai Video Generation: ENABLED")
        print("=" * 60)
        print("🚀 KING ZARRY AI READY")
        print("=" * 60)
        print()

    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        print(f"💬 Message from {message.author}: {message.content[:100]}")

        content = message.content.strip()

        if self.user:
            content = content.replace(f"<@{self.user.id}>", "")
            content = content.replace(f"<@!{self.user.id}>", "")
            content = content.strip()

        images = [
            attachment
            for attachment in message.attachments
            if attachment.content_type and attachment.content_type.startswith("image/")
        ]

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

                full_prompt = f"{SYSTEM_VOICE_PROMPT}\n\nUser Question: {content}"

                answer = await asyncio.to_thread(
                    ai.ask,
                    str(message.author.id),
                    full_prompt,
                    image_tuple
                )

            if not answer:
                answer = "❌ I couldn't generate a response."

            voice_triggers = ["use voice", "speak", "send audio", "voice message", "say this", "can you speak", "female voice", "audio"]
            wants_voice = any(trigger in content.lower() for trigger in voice_triggers)

            voice_file = None
            if wants_voice and eleven_client:
                try:
                    audio_fp = await asyncio.to_thread(generate_elevenlabs_voice, answer)
                    voice_file = File(fp=audio_fp, filename="king_zarry_voice.mp3")
                except Exception as voice_err:
                    print(f"⚠️ Voice generation error: {voice_err}")

            if voice_file:
                await message.reply(content=answer, file=voice_file, mention_author=False)
            else:
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
        "🧠 AI Agent (Groq / OpenAI / Gemini)\n"
        "📊 Market Intelligence\n"
        "📸 Multi-Provider Vision\n"
        "💾 Memory\n"
        "🎙️ ElevenLabs Voice (`eleven_flash_v2_5`)\n"
        "🎬 Fal.ai Video Generation\n"
        "🔧 AI Tools\n\n"
        "**COMMANDS**\n\n"
        "`/ask` Ask the AI\n"
        "`/voice` Ask the AI and receive a voice audio response\n"
        "`/textvideo` Generate a video from text prompt\n"
        "`/imagevideo` Animate an uploaded image\n"
        "`/stats` Bot analytics\n"
        "`/btc` Bitcoin analysis\n"
        "`/gold` Gold analysis\n"
        "`/crypto` Crypto prices\n"
        "`/analyze` Market analysis\n"
        "`/clear_memory` Clear your AI memory\n"
        "`/join` Join voice channel\n"
        "`/say` Speak in voice channel with ElevenLabs\n"
        "`/leave` Leave voice channel\n"
        "`/ping` Check bot connection status\n\n"
        "💬 Or simply send me a normal message or upload a chart."
    )


@client.tree.command(name="ping", description="Check if King Zarry AI is online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "👑 King Zarry AI is online!\n"
        "🧠 Groq: Connected\n"
        "🎬 Fal.ai Video Engine: Connected\n"
        "🎙️ Voice Engine: Connected"
    )


@client.tree.command(name="voice", description="Ask King Zarry AI and get an ElevenLabs audio response")
@app_commands.describe(question="Your question for voice response")
async def voice(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        full_prompt = f"{SYSTEM_VOICE_PROMPT}\n\nUser Question: {question}"
        answer = await asyncio.to_thread(
            ai.ask,
            str(interaction.user.id),
            full_prompt
        )

        if eleven_client:
            audio_fp = await asyncio.to_thread(generate_elevenlabs_voice, answer)
            discord_file = File(fp=audio_fp, filename="king_zarry_voice.mp3")
            await interaction.followup.send(content=f"🗣️ **King Zarry AI:**\n{answer}", file=discord_file)
        else:
            await interaction.followup.send(content=f"🗣️ **King Zarry AI:**\n{answer}\n\n*(ElevenLabs is not configured)*")

    except Exception as e:
        print("❌ /voice ERROR:", repr(e))
        await interaction.followup.send(f"❌ Voice error:\n`{str(e)[:1200]}`")


@client.tree.command(name="textvideo", description="Generate a video from a text prompt.")
@app_commands.describe(prompt="Describe the video you want to create.")
async def textvideo(interaction: discord.Interaction, prompt: str):
    prompt = prompt.strip()
    if not prompt:
        await interaction.response.send_message("❌ Please provide a video prompt.", ephemeral=True)
        return

    if len(prompt) > MAX_PROMPT_LENGTH:
        await interaction.response.send_message(
            f"❌ Prompt too long. Max: {MAX_PROMPT_LENGTH} chars.", ephemeral=True
        )
        return

    await interaction.response.defer()
    status_msg = await interaction.followup.send("🧠 **King Zarry is enhancing your prompt...**")
    video_path = None

    try:
        enhanced_prompt = await asyncio.to_thread(enhance_text_prompt, prompt)
        await status_msg.edit(
            content="🎬 **Generating video with Fal.ai...**\n⏳ This may take 20–60 seconds."
        )

        video_bytes = await asyncio.to_thread(generate_text_video, enhanced_prompt)

        if len(video_bytes) > MAX_VIDEO_SIZE:
            await status_msg.edit(content="⚠️ Generated video exceeds Discord's file size limit.")
            return

        video_path = save_video(video_bytes)
        file = discord.File(video_path, filename="king-zarry-video.mp4")

        embed = discord.Embed(title="👑 King Zarry Video", description="🎬 **Text → Video Complete (Fal.ai)**")
        embed.add_field(name="Enhanced Prompt", value=enhanced_prompt[:1000], inline=False)

        await interaction.followup.send(embed=embed, file=file)
        await status_msg.delete()

    except FalClientHTTPError as err:
        if err.status_code == 403 or "Exhausted balance" in str(err):
            print("⚠️ Fal.ai balance exhausted.")
            await status_msg.edit(
                content="⚠️ Video generation is currently offline due to API quota limits. "
                        "Text chat, vision, and voice features remain fully operational!"
            )
        else:
            await status_msg.edit(content=f"❌ Video generation error: `{err.message}`")

    except Exception as error:
        print("❌ Text-to-video error:", repr(error))
        await status_msg.edit(
            content=f"❌ **Generation failed.**\n`Technical error: {str(error)[:400]}`"
        )
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


@client.tree.command(name="imagevideo", description="Turn an image into a video.")
@app_commands.describe(
    image="Upload the image you want to animate.",
    motion="Describe how you want the image to move.",
)
async def imagevideo(
    interaction: discord.Interaction,
    image: discord.Attachment,
    motion: str,
):
    if image.content_type not in ALLOWED_VIDEO_IMAGE_TYPES:
        await interaction.response.send_message("❌ Upload a PNG, JPEG, or WebP image.", ephemeral=True)
        return

    if image.size > MAX_IMAGE_SIZE:
        await interaction.response.send_message("❌ Image exceeds max limit of 10 MB.", ephemeral=True)
        return

    motion = motion.strip()
    if not motion:
        await interaction.response.send_message("❌ Please describe requested motion.", ephemeral=True)
        return

    await interaction.response.defer()
    status_msg = await interaction.followup.send("📥 **Downloading and analyzing image...**")
    video_path = None

    try:
        image_bytes = await image.read()
        enhanced_prompt = await asyncio.to_thread(enhance_image_prompt, image_bytes, motion)

        await status_msg.edit(
            content="🎬 **Generating image-to-video animation with Fal.ai...**\n⏳ Please wait."
        )

        video_bytes = await asyncio.to_thread(generate_image_video, image_bytes, enhanced_prompt)

        if len(video_bytes) > MAX_VIDEO_SIZE:
            await status_msg.edit(content="⚠️ Generated video exceeds Discord's file size limit.")
            return

        video_path = save_video(video_bytes)
        file = discord.File(video_path, filename="king-zarry-image-video.mp4")

        embed = discord.Embed(title="👑 King Zarry Video", description="🖼️ **Image → Video Complete (Fal.ai)**")
        embed.add_field(name="Motion Prompt", value=enhanced_prompt[:1000], inline=False)

        await interaction.followup.send(embed=embed, file=file)
        await status_msg.delete()

    except FalClientHTTPError as err:
        if err.status_code == 403 or "Exhausted balance" in str(err):
            print("⚠️ Fal.ai balance exhausted.")
            await status_msg.edit(
                content="⚠️ Image animation is currently offline due to API quota limits. "
                        "Text chat, vision, and voice features remain fully operational!"
            )
        else:
            await status_msg.edit(content=f"❌ Video generation error: `{err.message}`")

    except Exception as error:
        print("❌ Image-to-video error:", repr(error))
        await status_msg.edit(
            content=f"❌ **Generation failed.**\n`Technical error: {str(error)[:400]}`"
        )
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass


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


@client.tree.command(name="btc", description="Analyze Bitcoin market")
@app_commands.describe(timeframe="Trading timeframe (e.g., 15m, 1h, 4h)")
async def btc(interaction: discord.Interaction, timeframe: str = "15m"):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, "BTC/USD", timeframe)
        message = format_market(data, "Bitcoin Market Analysis")
        await interaction.followup.send(message)
    except Exception as e:
        print("❌ /btc ERROR:", repr(e))
        await interaction.followup.send(f"❌ Market analysis failed:\n`{str(e)[:1200]}`")


@client.tree.command(name="gold", description="Analyze Gold market")
@app_commands.describe(timeframe="Trading timeframe (e.g., 15m, 1h, 4h)")
async def gold(interaction: discord.Interaction, timeframe: str = "15m"):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, "XAU/USD", timeframe)
        message = format_market(data, "Gold Market Analysis")
        await interaction.followup.send(message)
    except Exception as e:
        print("❌ /gold ERROR:", repr(e))
        await interaction.followup.send(f"❌ Gold analysis failed:\n`{str(e)[:1200]}`")


@client.tree.command(name="crypto", description="Check prices for popular cryptocurrencies")
async def crypto(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]
        results = []
        for sym in symbols:
            p = await asyncio.to_thread(get_price, sym)
            results.append(f"**{sym}**: `${safe_float(p):,.2f}`")

        msg = "👑 **Crypto Prices**\n\n" + "\n".join(results)
        await interaction.followup.send(msg)
    except Exception as e:
        print("❌ /crypto ERROR:", repr(e))
        await interaction.followup.send(f"❌ Price fetch failed:\n`{str(e)[:1200]}`")


@client.tree.command(name="analyze", description="Analyze any custom trading market symbol")
@app_commands.describe(symbol="Market symbol (e.g. BTC/USD, EUR/USD)", timeframe="Timeframe (e.g. 15m, 1h)")
async def analyze(interaction: discord.Interaction, symbol: str, timeframe: str = "15m"):
    await interaction.response.defer()
    try:
        data = await asyncio.to_thread(analyze_market, symbol.upper(), timeframe)
        message = format_market(data, f"{symbol.upper()} Analysis")
        await interaction.followup.send(message)
    except Exception as e:
        print("❌ /analyze ERROR:", repr(e))
        await interaction.followup.send(f"❌ Analysis failed:\n`{str(e)[:1200]}`")


@client.tree.command(name="clear_memory", description="Clear your personal AI conversation memory")
async def clear_memory(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await asyncio.to_thread(memory.clear_history, str(interaction.user.id))
        await interaction.followup.send("🧠 Your memory history has been cleared successfully!", ephemeral=True)
    except Exception as e:
        print("❌ /clear_memory ERROR:", repr(e))
        await interaction.followup.send(f"❌ Error clearing memory:\n`{str(e)[:1200]}`", ephemeral=True)


@client.tree.command(name="join", description="Join your current voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ You must be in a voice channel first!", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(f"🔊 Joined voice channel: **{channel.name}**")


@client.tree.command(name="say", description="Speak text into your current voice channel")
@app_commands.describe(text="The message King Zarry should speak out loud")
async def say(interaction: discord.Interaction, text: str):
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    if not voice_client:
        if interaction.user.voice and interaction.user.voice.channel:
            voice_client = await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("❌ Join a voice channel first or use `/join`!")
            return

    await interaction.followup.send(f"🎙️ **Speaking:** {text}")
    await play_voice_in_channel(voice_client, text)


@client.tree.command(name="leave", description="Disconnect King Zarry AI from the voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("⚠️ I am not currently in a voice channel.", ephemeral=True)


# ==========================================================
# RUN DISCORD CLIENT
# ==========================================================

if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
