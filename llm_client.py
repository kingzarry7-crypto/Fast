"""OpenAI-compatible LLM client with provider-aware automatic failover.

Provider model names and base URLs are not interchangeable. DeepSeek is
intentionally excluded from the fallback chain.
"""
from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from openai import OpenAI

logger = logging.getLogger("kz_llm_client")

# (name, key env, base URL, model env, default model, optional endpoint env)
# OpenAI is first in AUTO mode because it is the configured paid primary. If it
# is unavailable, the remaining configured providers are tried in order.
PROVIDERS = [
    ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", "OPENAI_MODEL", "gpt-5.4-nano", None),
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1", "GROQ_MODEL", "openai/gpt-oss-20b", None),
    ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_MODEL", "gemini-2.5-flash", None),
    ("chutes", "CHUTES_API_KEY", "https://llm.chutes.ai/v1", "CHUTES_MODEL", "google/gemma-4-31B-turbo-TEE", "CHUTES_URL"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "OPENROUTER_MODEL", "openrouter/free", "OPENROUTER_BASE_URL"),
    ("cloudflare", "CLOUDFLARE_AI_TOKEN", "https://kingzarry-ai-inference.kingzarry7.workers.dev/v1", "CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "CLOUDFLARE_AI_URL"),
    ("huggingface", "HF_TOKEN", "https://router.huggingface.co/v1", "HF_MODEL_ID", "KINGZARRY3/zarry-coder-model", "HF_INFERENCE_URL"),
]


def _api_base_url(value: str, fallback: str) -> str:
    """Normalize a configured OpenAI-compatible endpoint to its API base URL."""
    value = (value or "").strip()
    if not value:
        return fallback
    for suffix in ("/chat/completions", "/completions"):
        if value.rstrip("/").endswith(suffix):
            value = value.rstrip("/")[:-len(suffix)]
            break
    return value.rstrip("/")


def _configured_providers():
    requested = os.getenv("AI_PROVIDER", "AUTO").strip().upper()
    aliases = {
        "AUTOMATIC": "AUTO",
        "HF": "HUGGINGFACE",
        "HUGGING_FACE": "HUGGINGFACE",
        "CLOUDFLARE_AI": "CLOUDFLARE",
        "WORKERS_AI": "CLOUDFLARE",
    }
    requested = aliases.get(requested, requested)
    configured = []

    for name, key_env, default_base_url, model_env, default_model, endpoint_env in PROVIDERS:
        key = os.getenv(key_env, "").strip()
        # Recover legacy Railway variable names that accidentally contain a
        # trailing space. start.sh also normalizes these at process startup.
        if not key and key_env == "GROQ_API_KEY":
            key = os.getenv("GROQ_API_KEY ", "").strip()
        if not key:
            continue
        if requested not in ("", "AUTO") and requested != name.upper():
            continue

        model = os.getenv(model_env, "").strip()
        if not model and model_env == "GROQ_MODEL":
            model = os.getenv("GROQ_MODEL ", "").strip()
        model = model or default_model
        endpoint = os.getenv(endpoint_env, "").strip() if endpoint_env else ""
        base_url = _api_base_url(endpoint, default_base_url)
        configured.append((name, key, base_url, model))

    # A pinned provider must be honored rather than silently using another.
    if requested not in ("", "AUTO") and not configured:
        supported = ", ".join(name.upper() for name, *_ in PROVIDERS)
        raise RuntimeError(
            f"Requested AI provider {requested} is not configured or unsupported. "
            f"Supported providers: {supported}"
        )
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
            if name == "openai" and model.lower().startswith(("gpt-5", "o1", "o3", "o4")):
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            response = client.chat.completions.create(**kwargs)
            answer = response.choices[0].message.content if response.choices else None
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
            raise RuntimeError("empty_completion")
        except Exception as exc:
            errors.append(f"{name}:{type(exc).__name__}")
            logger.warning("LLM provider %s failed; trying next provider (%s)", name, type(exc).__name__)

    raise RuntimeError("All configured LLM providers failed: " + ", ".join(errors))
