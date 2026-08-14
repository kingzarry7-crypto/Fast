import os


# =========================================================
# KING ZARRY AI 👑
# CENTRAL CONFIGURATION
# =========================================================

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# =========================================================
# AI PROVIDERS
# =========================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

XAI_API_KEY = os.getenv("XAI_API_KEY")


# AI provider mode
AI_PROVIDER = (
    os.getenv("AI_PROVIDER", "AUTO")
    .upper()
    .strip()
)


# =========================================================
# MODELS
# =========================================================

# Updated to Qwen 3.6 27B for Vision + Text Multimodal capabilities
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "qwen/qwen3.6-27b"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

XAI_MODEL = os.getenv(
    "XAI_MODEL",
    "grok-beta"
)


# =========================================================
# API URLS
# =========================================================

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)

OPENAI_URL = (
    "https://api.openai.com/v1/chat/completions"
)

XAI_URL = (
    "https://api.x.ai/v1/chat/completions"
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
# STATUS
# =========================================================

def provider_status():

    return {

        "mode":
            AI_PROVIDER,

        "groq":
            bool(GROQ_API_KEY),

        "gemini":
            bool(GEMINI_API_KEY),

        "openai":
            bool(OPENAI_API_KEY),

        "xai":
            bool(XAI_API_KEY),

        "telegram":
            bool(TELEGRAM_BOT_TOKEN),

        "discord":
            bool(DISCORD_BOT_TOKEN),

        "twelve_data":
            bool(TWELVE_DATA_API_KEY)

    }
