"""Small OpenAI-compatible LLM client with automatic provider selection.

The first configured provider in PROVIDERS wins. Set AI_MODEL to override
that provider's default model without changing code.
"""
import os

from openai import OpenAI


# (environment variable, OpenAI-compatible base URL, default model)
PROVIDERS = [
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    (
        "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash",
    ),
    ("DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek-chat"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "deepseek/deepseek-chat"),
    ("OPENAI_API_KEY", None, "gpt-5.4-nano"),
]


def get_client():
    for env, base_url, default_model in PROVIDERS:
        key = os.getenv(env)
        if key:
            model = os.getenv("AI_MODEL", default_model)
            return OpenAI(api_key=key, base_url=base_url), model
    raise RuntimeError("No API key found in environment variables")


client, MODEL = get_client()


def ask(messages, max_tokens=500):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
