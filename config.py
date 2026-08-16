import os
from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()

# =========================================================
# KING ZARRY AI 👑
# CENTRAL CONFIGURATION
# =========================================================

# Database / Persistent Memory
DB_PATH = os.getenv("DB_PATH", "king_zarry_memory.db")
MAX_MEMORY_MESSAGES = int(os.getenv("MAX_MEMORY_MESSAGES", "20")) # Limits conversation context per user

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# =========================================================
# AI PROVIDERS & API KEYS
# =========================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

XAI_API_KEY = os.getenv("XAI_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Fal.ai Key (Video Generation)
FAL_KEY = os.getenv("FAL_KEY")


# AI provider selection mode (AUTO, GROQ, GEMINI, OPENAI, XAI)
AI_PROVIDER = (
    os.getenv("AI_PROVIDER", "AUTO")
    .upper()
    .strip()
)


# =========================================================
# MODELS & VOICE CONFIG
# =========================================================

# Groq Models
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "llama-3.2-11b-vision-preview"
)

# Google Gemini Model
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-1.5-flash"
)

# OpenAI Model
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

# xAI Model
XAI_MODEL = os.getenv(
    "XAI_MODEL",
    "grok-beta"
)

# ElevenLabs Voice & Model defaults
ELEVENLABS_MODEL_ID = os.getenv(
    "ELEVENLABS_MODEL_ID",
    "eleven_flash_v2_5"
)

ELEVENLABS_VOICE_ID = os.getenv(
    "ELEVENLABS_VOICE_ID",
    "21m00Tcm4TlvDq8ikWAM"
)

# Fal.ai Video Models
TEXT_TO_VIDEO_MODEL = os.getenv(
    "TEXT_TO_VIDEO_MODEL",
    "fal-ai/ltx-video"
)

IMAGE_TO_VIDEO_MODEL = os.getenv(
    "IMAGE_TO_VIDEO_MODEL",
    "fal-ai/ltx-video/image-to-video"
)


# =========================================================
# API ENDPOINTS & URLS
# =========================================================

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

OPENAI_URL = (
    "https://api.openai.com/v1/chat/completions"
)

XAI_URL = (
    "https://api.x.ai/v1/chat/completions"
)

ELEVENLABS_URL = (
    "https://api.elevenlabs.io/v1"
)


# =========================================================
# MARKET DATA
# =========================================================

TWELVE_DATA_API_KEY = os.getenv(
    "TWELVE_DATA_API_KEY"
)

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)


# =========================================================
# STATUS HELPER
# =========================================================

def provider_status():
    """Returns a dictionary indicating active/configured integrations."""
    return {
        "mode": AI_PROVIDER,
        "database": bool(DB_PATH),
        "groq": bool(GROQ_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "xai": bool(XAI_API_KEY),
        "elevenlabs": bool(ELEVENLABS_API_KEY),
        "fal": bool(FAL_KEY),
        "telegram": bool(TELEGRAM_BOT_TOKEN),
        "discord": bool(DISCORD_BOT_TOKEN),
        "twelve_data": bool(TWELVE_DATA_API_KEY),
    }
