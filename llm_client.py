"""OpenAI-compatible LLM client with per-provider models and automatic failover.

Do not reuse one AI_MODEL across providers: provider model names are not
interchangeable. DeepSeek is intentionally excluded from the fallback chain.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger("kz_llm_client")

# (key env, base URL, model env, safe default)
PROVIDERS = [
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "GROQ_MODEL", "openai/gpt-oss-20b"),
    ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_MODEL", "gemini-2.5-flash"),
    ("CHUTES_API_KEY", "https://llm.chutes.ai/v1", "CHUTES_MODEL", "google/gemma-4-31B-turbo-TEE"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "OPENROUTER_MODEL", "openrouter/free"),
    ("OPENAI_API_KEY", None, "OPENAI_MODEL", "gpt-5.4-nano"),
]


def _configured_providers():
    requested = os.getenv("AI_PROVIDER", "AUTO").strip().upper()
    configured = []
    for env, base_url, model_env, default_model in PROVIDERS:
        key = os.getenv(env, "").strip()
        if not key:
            continue
        name = env.removesuffix("_API_KEY").lower()
        if requested not in ("", "AUTO", "AUTOMATIC") and requested != name.upper():
            continue
        model = os.getenv(model_env, "").strip() or default_model
        configured.append((name, key, base_url, model))
    # A pinned provider should be honored rather than silently using another
    # provider. AUTO mode tries every configured provider in order.
    if requested not in ("", "AUTO", "AUTOMATIC") and not configured:
        raise RuntimeError(f"Requested AI provider {requested} is not configured")
    return configured


def get_client():
    """Return the first configured provider for callers that need streaming."""
    providers = _configured_providers()
    if not providers:
        raise RuntimeError("No supported AI provider is configured")
    _, key, base_url, model = providers[0]
    timeout = float(os.getenv("AI_PROVIDER_TIMEOUT", "12") or 12)
    return OpenAI(api_key=key, base_url=base_url, timeout=timeout, max_retries=0), model


def ask(messages: list[dict[str, Any]], max_tokens: int = 500):
    """Try each configured provider; only return a non-empty generated answer."""
    providers = _configured_providers()
    if not providers:
        raise RuntimeError("No supported AI provider is configured")

    errors = []
    timeout = float(os.getenv("AI_PROVIDER_TIMEOUT", "12") or 12)
    for name, key, base_url, model in providers:
        try:
            client = OpenAI(api_key=key, base_url=base_url, timeout=timeout, max_retries=0)
            kwargs: dict[str, Any] = {"model": model, "messages": messages}
            # Newer OpenAI reasoning models use max_completion_tokens; most
            # OpenAI-compatible providers use max_tokens.
            if name == "openai" and model.lower().startswith(("gpt-5", "o1", "o3", "o4")):
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content if response.choices else None
            if isinstance(text, str) and text.strip():
                return text.strip()
            raise RuntimeError("empty_completion")
        except Exception as exc:
            errors.append(f"{name}:{type(exc).__name__}")
            logger.warning("LLM provider %s failed; trying next provider (%s)", name, type(exc).__name__)
    raise RuntimeError("All configured LLM providers failed: " + ", ".join(errors))
