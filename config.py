import os


def clean_env_str(value, default=None):
    if value is None:
        return default
    value = str(value).strip()
    return value or default


# OpenRouter and OpenAI use compatible request formats, but their credentials,
# endpoints, and model names are independent. Never alias one provider to another.
OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_BASE_URL = clean_env_str(
    os.getenv("OPENROUTER_BASE_URL"),
    "https://openrouter.ai/api/v1",
)
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)

OPENAI_API_KEY = clean_env_str(os.getenv("OPENAI_API_KEY"))
OPENAI_BASE_URL = clean_env_str(
    os.getenv("OPENAI_BASE_URL"),
    "https://api.openai.com/v1",
)
OPENAI_MODEL = clean_env_str(os.getenv("OPENAI_MODEL"), "gpt-5.4-nano")
