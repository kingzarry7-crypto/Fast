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

# AI providers
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AI provider mode
AI_PROVIDER = (
    os.getenv("AI_PROVIDER", "AUTO")
    .upper()
    .strip()
)

# Models
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini"
)

# Market data
TWELVE_DATA_API_KEY = os.getenv(
    "TWELVE_DATA_API_KEY"
)

# API URLs
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models"
)

OPENAI_URL = (
    "https://api.openai.com/v1/chat/completions"
)

TWELVE_DATA_URL = (
    "https://api.twelvedata.com"
)


# =========================================================
# STATUS
# =========================================================

def provider_status():
    return {
        "mode": AI_PROVIDER,
        "gemini": bool(GEMINI_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "telegram": bool(TELEGRAM_BOT_TOKEN),
        "discord": bool(DISCORD_BOT_TOKEN),
        "twelve_data": bool(TWELVE_DATA_API_KEY),
    }
