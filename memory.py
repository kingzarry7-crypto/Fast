import os
import re
import asyncio
import base64
import requests
import discord
from discord.ext import commands

from memory import Memory  # Import your fixed Memory class

# =========================================================
# 👑 KING ZARRY AI - DISCORD BOT
# Multi-Provider Engine (Groq, Gemini, OpenAI) + Memory
# =========================================================

# --- ENVIRONMENT VARIABLES & CLEANUP ---
def clean_env_str(val: str, default: str = "") -> str:
    if not val:
        return default
    cleaned = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', val).strip()
    return cleaned if cleaned else default

def clean_ai_response(text: str) -> str:
    """Strips reasoning blocks (<think>...</think>), truncated think tags, and control tokens."""
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in text:
        text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()

DISCORD_BOT_TOKEN = clean_env_str(os.environ.get("DISCORD_BOT_TOKEN"))
DISCORD_ADMIN_ID = clean_env_str(os.environ.get("DISCORD_ADMIN_ID"))

# Provider Keys
GROK_API_KEY = clean_env_str(os.environ.get("GROK_API_KEY") or os.environ.get("GROQ_API_KEY"))
OPENAI_API_KEY = clean_env_str(os.environ.get("OPENAI_API_KEY"))
GEMINI_API_KEY = clean_env_str(os.environ.get("GEMINI_API_KEY"))

# Default Models
GROK_MODEL = clean_env_str(os.environ.get("GROK_MODEL") or os.environ.get("GROQ_MODEL"), "qwen/qwen3.6-27b")
GROK_VISION_MODEL = clean_env_str(os.environ.get("GROK_VISION_MODEL"), "llama-3.2-11b-vision-instruct")
OPENAI_MODEL = clean_env_str(os.environ.get("OPENAI_MODEL"), "gpt-4o-mini")
GEMINI_MODEL = clean_env_str(os.environ.get("GEMINI_MODEL"), "gemini-2.0-flash")

# API Base Endpoints
GROK_BASE_URL = clean_env_str(os.environ.get("GROK_BASE_URL") or os.environ.get("GROQ_BASE_URL"), "https://api.groq.com/openai/v1")
OPENAI_BASE_URL = clean_env_str(os.environ.get("OPENAI_BASE_URL"), "https://api.openai.com/v1")

# --- INITIALIZE MEMORY & GEMINI SDK ---
memory = Memory(database_path="king_zarry_memory.db", retention_hours=24)

try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False

SYSTEM_PROMPT = """
You are King Zarry AI 👑, the official assistant for the King Zarry community.

You assist with trading (BTC, ETH, SOL, Forex, Gold/XAUUSD), market analysis, programming, image analysis, and general conversational queries.

CRITICAL INSTRUCTIONS:
- DO NOT generate internal reasoning, chain-of-thought, or <think> tags in your output.
- Respond directly to what the user asks.
- If asked to edit, enhance, or adjust a picture, politely explain what image-editing tools (like Photoshop AI, Canva, or Midjourney) can achieve that effect or provide image-generation prompts.
"""

# =========================================================
# AI ROUTING FUNCTIONS
# =========================================================

def openai_compatible_request(messages, api_key, base_url, model):
    if not api_key:
        raise RuntimeError("API Key missing.")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
    if response.status_code != 200:
        raise RuntimeError(f"API Error ({response.status_code}): {response.text}")
    data = response.json()
    return clean_ai_response(data["choices"][0]["message"]["content"].strip())

def gemini_request(messages_or_prompt, image_bytes=None, mime_type=None):
    if not GEMINI_API_KEY or not GEMINI_SDK_AVAILABLE:
        raise RuntimeError("Gemini SDK unavailable.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    if image_bytes:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        contents = [f"{SYSTEM_PROMPT}\n\nTask: {messages_or_prompt}", image_part]
    else:
        contents = [f"{SYSTEM_PROMPT}\n\nHistory and Prompt:\n{messages_or_prompt}"]

    models_to_try = [GEMINI_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"]
    for model_name in dict.fromkeys(models_to_try):
        try:
            response = client.models.generate_content(
                model=model_name, contents=contents,
                config=types.GenerateContentConfig(max_output_tokens=2048)
            )
            if response.text:
                return clean_ai_response(response.text)
        except Exception:
            continue
    raise RuntimeError("All Gemini models failed.")

def ask_ai_with_history(user_prompt: str, history: list) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_prompt})

    # Try Groq -> Gemini -> OpenAI
    if GROK_API_KEY:
        try:
            return openai_compatible_request(messages, GROK_API_KEY, GROK_BASE_URL, GROK_MODEL)
        except Exception:
            pass

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            full_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            return gemini_request(full_prompt)
        except Exception:
            pass

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
        except Exception:
            pass

    raise RuntimeError("All AI providers failed.")

def analyze_image_with_ai(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    vision_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
            ]
        }
    ]

    if GROK_API_KEY:
        try:
            return openai_compatible_request(vision_messages, GROK_API_KEY, GROK_BASE_URL, GROK_VISION_MODEL)
        except Exception:
            pass

    if GEMINI_API_KEY and GEMINI_SDK_AVAILABLE:
        try:
            return gemini_request(prompt, image_bytes, mime_type)
        except Exception:
            pass

    if OPENAI_API_KEY:
        try:
            return openai_compatible_request(vision_messages, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
        except Exception:
            pass

    raise RuntimeError("All vision providers failed.")


# =========================================================
# DISCORD BOT EVENT HANDLERS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"👑 King Zarry AI Discord Bot online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Slash sync error: {e}")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    user_id = str(message.author.id)

    # Allow users to trigger with !ask or by direct message / tagging the bot
    is_mentioned = bot.user.mentioned_in(message) and not message.mention_everyone
    is_dm = isinstance(message.channel, discord.DMChannel)

    if not (is_mentioned or is_dm or message.content.startswith("!ask")):
        await bot.process_commands(message)
        return

    # Clean the input text
    clean_text = message.content.replace(f"<@{bot.user.id}>", "").replace("!ask", "").strip()

    async with message.channel.typing():
        try:
            # --- VISION ATTACHMENT HANDLING ---
            if message.attachments:
                attachment = message.attachments[0]
                if any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
                    image_bytes = await attachment.read()
                    mime_type = attachment.content_type or "image/jpeg"
                    prompt = clean_text if clean_text else "Analyze this image and describe what you see."

                    # Save image tag into memory so follow-up questions remember the image
                    memory_prompt = f"[User attached an image] {prompt}".strip()
                    memory.add(user_id, "user", memory_prompt)

                    response = await asyncio.to_thread(analyze_image_with_ai, image_bytes, mime_type, prompt)
                    memory.add(user_id, "assistant", response)

                    chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                    first_chunk = True
                    for chunk in chunks:
                        if first_chunk:
                            await message.reply(chunk)
                            first_chunk = False
                        else:
                            await message.channel.send(chunk)
                    return

            # --- TEXT HANDLING ---
            if not clean_text:
                await message.reply("How can I assist you today? 👑")
                return

            # Fetch 24-hour context history from SQLite
            history = memory.get_history(user_id, limit=10)

            # Save incoming prompt
            memory.add(user_id, "user", clean_text)

            # Get response from multi-provider engine
            response = await asyncio.to_thread(ask_ai_with_history, clean_text, history)

            # Save assistant response
            memory.add(user_id, "assistant", response)

            # Split response into 1900 character chunks if needed
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            first_chunk = True
            for chunk in chunks:
                if first_chunk:
                    await message.reply(chunk)
                    first_chunk = False
                else:
                    await message.channel.send(chunk)

        except Exception as e:
            await message.reply(f"❌ **King Zarry AI Error:** `{e}`")

    await bot.process_commands(message)


# =========================================================
# SLASH COMMANDS
# =========================================================

@bot.tree.command(name="stats", description="Displays unique bot user analytics (Admin Only)")
async def stats(interaction: discord.Interaction):
    if DISCORD_ADMIN_ID and str(interaction.user.id) != DISCORD_ADMIN_ID:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return

    stats_data = memory.get_user_stats()
    embed = discord.Embed(title="👑 King Zarry AI Stats", color=discord.Color.gold())
    embed.add_field(name="Total Guilds", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Total Unique Users (DB)", value=str(stats_data["total_users"]), inline=True)
    embed.add_field(name="Active Users (24h)", value=str(stats_data["active_24h"]), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear_memory", description="Clears your 24-hour conversation memory")
async def clear_memory(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    memory.clear(user_id)
    await interaction.response.send_message("🧹 Your conversation memory has been cleared!", ephemeral=True)


# =========================================================
# RUN BOT
# =========================================================

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is missing.")
    bot.run(DISCORD_BOT_TOKEN)
