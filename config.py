import os


def clean_env_str(value, default=None):
    if value is None:
        return default
    value = str(value).strip()
    return value or default


# OpenRouter provides an OpenAI-compatible API.
OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_BASE_URL = clean_env_str(
    os.getenv("OPENROUTER_BASE_URL"),
    "https://openrouter.ai/api/v1",
)
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)

# Backwards-compatible OpenAI settings for code that still imports these names.
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_BASE_URL = OPENROUTER_BASE_URL
OPENAI_MODEL = OPENROUTER_MODEL
