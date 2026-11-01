"""OpenAI-compatible LLM client with provider-aware automatic failover.

DeepSeek is intentionally excluded from the fallback chain. Hugging Face's
custom model is tried first; if its router rejects the model with HTTP 400,
a known Inference Providers model is tried once before the provider is marked
failed.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

from openai import OpenAI
from uuid import uuid4

from zarry_gateway.providers import SelfHostedZarryProvider

logger = logging.getLogger("kz_llm_client")

# (name, key env, base URL, model env, default model, optional endpoint env)
PROVIDERS = [
    ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", "OPENAI_MODEL", "gpt-5.4-nano", None),
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1", "GROQ_MODEL", "openai/gpt-oss-20b", None),
    ("gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_MODEL", "gemini-2.5-flash", None),
    ("chutes", "CHUTES_API_KEY", "https://llm.chutes.ai/v1", "CHUTES_MODEL", "google/gemma-4-31B-turbo-TEE", "CHUTES_URL"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "OPENROUTER_MODEL", "openrouter/free", "OPENROUTER_BASE_URL"),
    ("cloudflare", "CLOUDFLARE_AI_TOKEN", "https://kingzarry-ai-inference.kingzarry7.workers.dev/v1", "CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "CLOUDFLARE_AI_URL"),
    ("huggingface", "HF_TOKEN", "https://router.huggingface.co/v1", "HF_MODEL_ID", "openai/gpt-oss-120b:cheapest", "HF_INFERENCE_URL"),
]
HF_ROUTER_BASE_URL = "https://router.huggingface.co/v1"
DEFAULT_HF_FALLBACK_MODEL = "openai/gpt-oss-120b:cheapest"


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


def _error_summary(exc: Exception) -> str:
    """Return a safe diagnostic without exposing provider response bodies."""
    status = getattr(exc, "status_code", None)
    return f"HTTP {status} {type(exc).__name__}" if status else type(exc).__name__

def _create_completion(name: str, key: str, base_url: str, model: str,
                       messages: list[dict[str, Any]], max_tokens: int,
                       timeout: float):
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



def _zarry_completion(messages: list[dict[str, Any]], max_tokens: int, timeout: float):
    """Call the pinned self-hosted Railway Qwen service, or legacy /generate if configured."""
    if os.getenv("ZARRY_PRIVATE_SERVICE_URL", "").strip() or os.getenv("ZARRY_SERVICE_URL", "").strip():
        latest_user_message = next(
            (
                str(item.get("content") or "")
                for item in reversed(messages or [])
                if isinstance(item, dict) and item.get("role") == "user"
            ),
            "",
        )
        provider = SelfHostedZarryProvider()
        return provider.generate(
            message=latest_user_message,
            request_id=uuid4(),
            messages=messages,
            timeout=(5.0, max(30.0, float(timeout))),
        )

    endpoint = os.getenv("ZARRY_API_URL", "").strip()
    if not endpoint:
        return None
    prompt = ""
    for item in reversed(messages or []):
        if isinstance(item, dict) and item.get("role") == "user":
            content = item.get("content", "")
            if isinstance(content, str):
                prompt = content
            elif isinstance(content, list):
                prompt = "\\n".join(
                    str(part.get("text", "")) for part in content if isinstance(part, dict)
                )
            break
    payload = {
        "prompt": prompt,
        "input": prompt,
        "text": prompt,
        "messages": messages,
        "history": [],
        "max_new_tokens": max_tokens,
        "temperature": 0.7,
    }
    headers = {"Content-Type": "application/json", "bypass-tunnel-reminder": "true"}
    token = os.getenv("ZARRY_API_KEY", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    answer = data if isinstance(data, str) else None
    if isinstance(data, dict):
        for key in ("response", "generated_text", "text", "output", "result", "answer", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                answer = value
                break
        if not answer:
            choices = data.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                first = choices[0]
                message = first.get("message") or {}
                answer = message.get("content") or first.get("text")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()
    raise RuntimeError("zarry_empty_completion")


def get_client():
    """Return the first configured provider for callers that need streaming."""
    providers = _configured_providers()
    if not providers:
        raise RuntimeError("No supported AI provider is configured")
    _, key, base_url, model = providers[0]
    timeout = float(os.getenv("AI_PROVIDER_TIMEOUT", "12") or 12)
    return OpenAI(api_key=key, base_url=base_url, timeout=timeout, max_retries=0), model


def ask(messages: list[dict[str, Any]], max_tokens: int = 500):
    """Try providers in order; recover once from an unsupported HF model."""
    errors = []
    timeout = float(os.getenv("AI_PROVIDER_TIMEOUT", "12") or 12)
    requested_provider = os.getenv("AI_PROVIDER", "AUTO").strip().upper()
    # A configured local Zarry endpoint is an automatic-mode fallback/primary,
    # but it must not override an explicit provider choice such as OPENAI.
    should_try_zarry = requested_provider in {"", "AUTO", "AUTOMATIC", "ZARRY", "LOCAL_ZARRY"}
    has_private_zarry = bool(
        os.getenv("ZARRY_PRIVATE_SERVICE_URL", "").strip()
        or os.getenv("ZARRY_SERVICE_URL", "").strip()
    )
    if should_try_zarry and (has_private_zarry or os.getenv("ZARRY_API_URL", "").strip()):
        try:
            answer = _zarry_completion(messages, max_tokens, timeout)
            if answer:
                logger.info("LLM provider local-zarry succeeded")
                return answer
        except Exception as exc:
            errors.append(f"zarry:generate:{_error_summary(exc)}")
            logger.warning("Local Zarry API failed; trying configured fallback providers (%s)", type(exc).__name__)

    providers = _configured_providers()
    if not providers:
        if errors:
            raise RuntimeError("All configured LLM providers failed: " + "; ".join(errors))
        raise RuntimeError("No supported AI provider is configured")

    for name, key, base_url, model in providers:
        try:
            return _create_completion(name, key, base_url, model, messages, max_tokens, timeout)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            # A Hub repo is not necessarily enabled on Inference Providers. If
            # the router rejects a custom model, retry with a documented model.
            if name == "huggingface" and status == 400 and base_url.rstrip("/") == HF_ROUTER_BASE_URL:
                fallback_model = os.getenv("HF_FALLBACK_MODEL_ID", "").strip() or DEFAULT_HF_FALLBACK_MODEL
                if fallback_model != model:
                    try:
                        logger.warning(
                            "Hugging Face rejected configured model %s (HTTP 400); retrying with fallback model %s",
                            model, fallback_model,
                        )
                        return _create_completion(
                            name, key, base_url, fallback_model, messages, max_tokens, timeout
                        )
                    except Exception as fallback_exc:
                        errors.append(
                            f"{name}:{model}:{_error_summary(exc)}; "
                            f"fallback {fallback_model}:{_error_summary(fallback_exc)}"
                        )
                        logger.warning(
                            "Hugging Face configured and fallback models failed (%s; %s)",
                            type(exc).__name__, type(fallback_exc).__name__,
                        )
                        continue
            errors.append(f"{name}:{model}:{_error_summary(exc)}")
            logger.warning(
                "LLM provider %s model %s failed; trying next provider (%s)",
                name, model, type(exc).__name__,
            )

    raise RuntimeError("All configured LLM providers failed: " + "; ".join(errors))
