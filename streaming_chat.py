"""KING ZARRY AI — additive web token streaming.

This module does not replace /api/chat. It adds a true SSE token stream for
simple text chat using the existing OpenAI-compatible Groq/OpenRouter providers.
The frontend only opts into this path for normal text chat; images, market/tool
requests and other special flows continue through the existing endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable, Dict, Generator, Optional

import requests
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import ai_engine

logger = logging.getLogger("kz_streaming_chat")

_TIMEOUT = max(8, int(os.getenv("AI_STREAM_TIMEOUT", "60")))
_OPENROUTER_URL = ai_engine.OPENROUTER_URL
_OPENROUTER_KEY = ai_engine.OPENROUTER_API_KEY
_OPENROUTER_MODEL = ai_engine.OPENROUTER_MODEL
_GROQ_URL = ai_engine.GROQ_URL
_GROQ_KEY = ai_engine.GROQ_API_KEY
_GROQ_MODEL = ai_engine.GROQ_MODEL
_CHUTES_URL = ai_engine.CHUTES_URL
_CHUTES_KEY = ai_engine.CHUTES_API_KEY
_CHUTES_MODEL = ai_engine.CHUTES_MODEL


class StreamChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


def _sse(event: Dict[str, Any]) -> str:
    return "data: " + json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n\n"


def _extract_delta(payload: Dict[str, Any]) -> str:
    try:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
    except Exception:
        pass
    return ""


def _stream_openai_compatible(
    *,
    url: str,
    key: str,
    model: str,
    messages: list,
) -> Generator[str, None, None]:
    if not key:
        raise RuntimeError("provider_not_configured")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 2000,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    with requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=(10, _TIMEOUT),
        stream=True,
    ) as response:
        if response.status_code >= 400:
            body = response.text[:400]
            raise RuntimeError(f"provider_http_{response.status_code}: {body}")
        for raw in response.iter_lines(chunk_size=1, decode_unicode=True):
            line = (raw or "").strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                payload = json.loads(line)
            except Exception:
                continue
            delta = _extract_delta(payload)
            if delta:
                yield delta


def _automatic_provider_stream(messages: list):
    """Use the same Railway key/model selection as normal AI chat."""
    from llm_client import get_client

    client, model = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=2000,
        stream=True,
    )
    for chunk in response:
        try:
            delta = chunk.choices[0].delta.content
            if isinstance(delta, str) and delta:
                yield delta
        except Exception:
            continue


def _provider_streams(messages: list):
    # Primary path: the centralized provider selector (Groq -> Gemini ->
    # DeepSeek -> OpenRouter -> OpenAI). Existing direct streams remain as
    # compatibility fallbacks if the selected provider cannot stream.
    try:
        from llm_client import get_client
        client, _ = get_client()
        provider_name = "automatic"
        for env_name, name in (
            ("GROQ_API_KEY", "groq"),
            ("GEMINI_API_KEY", "gemini"),
            ("DEEPSEEK_API_KEY", "deepseek"),
            ("OPENROUTER_API_KEY", "openrouter"),
            ("OPENAI_API_KEY", "openai"),
        ):
            if os.getenv(env_name):
                provider_name = name
                break
        yield provider_name, _automatic_provider_stream(messages)
    except Exception:
        pass

    if _GROQ_KEY:
        yield "groq", _stream_openai_compatible(
            url=_GROQ_URL,
            key=_GROQ_KEY,
            model=_GROQ_MODEL,
            messages=messages,
        )
    if _OPENROUTER_KEY:
        yield "openrouter", _stream_openai_compatible(
            url=_OPENROUTER_URL,
            key=_OPENROUTER_KEY,
            model=_OPENROUTER_MODEL,
            messages=messages,
        )
    if _CHUTES_KEY:
        yield "chutes", _stream_openai_compatible(
            url=_CHUTES_URL,
            key=_CHUTES_KEY,
            model=_CHUTES_MODEL,
            messages=messages,
        )


def _build_stream_generator(
    *,
    user_id: str,
    message: str,
    conversation_id: str,
    memory_factory: Callable[[str, Optional[str]], Any],
) -> Generator[str, None, None]:
    memory = memory_factory(user_id, conversation_id)
    engine = ai_engine.AIEngine(memory=memory)

    # Streaming is intentionally limited to ordinary text chat. The normal
    # /api/chat path remains authoritative for tools, web research, media and
    # images, so this feature cannot silently bypass those systems.
    casual = True
    history = engine._load_memory_history(user_id, limit=20)
    persistent_ctx = engine._load_persistent_context(user_id)
    try:
        if ai_engine.provider_registry is not None:
            persistent_ctx = (
                persistent_ctx
                + "\n\n"
                + ai_engine.provider_registry.owner_context(user_id)
            ).strip()
    except Exception:
        pass

    messages = engine._build_openai_messages(
        message,
        history,
        None,
        persistent_ctx,
        casual=casual,
    )

    full_text = ""
    last_error = None
    started_provider = None

    for provider_name, stream in _provider_streams(messages):
        try:
            started_provider = provider_name
            yield _sse({"type": "start", "provider": provider_name})
            for delta in stream:
                full_text += delta
                yield _sse({"type": "delta", "text": delta})
            if full_text.strip():
                cleaned = ai_engine.clean_ai_response(full_text).strip()
                if cleaned:
                    engine._save_memory(user_id, message, cleaned)
                yield _sse({
                    "type": "done",
                    "conversation_id": conversation_id,
                    "text": cleaned,
                })
                return
            last_error = "empty_stream"
        except Exception as exc:
            last_error = f"{provider_name}:{type(exc).__name__}"
            logger.warning(
                "Streaming provider failed | provider=%s error=%s",
                provider_name,
                type(exc).__name__,
            )
            # Never append a second provider's full response after partial
            # output: that would duplicate text in the UI. The frontend can
            # keep the partial response rather than silently corrupting it.
            if full_text.strip():
                cleaned = ai_engine.clean_ai_response(full_text).strip()
                if cleaned:
                    engine._save_memory(user_id, message, cleaned)
                yield _sse({
                    "type": "done",
                    "conversation_id": conversation_id,
                    "text": cleaned,
                    "partial": True,
                })
                return
            yield _sse({
                "type": "provider_error",
                "provider": provider_name,
            })
            continue

    yield _sse({
        "type": "error",
        "message": "Streaming provider unavailable",
        "fallback": True,
        "provider": started_provider,
        "detail": last_error,
    })


def install_streaming_chat(
    app,
    *,
    require_current_user,
    get_or_create_conversation,
    maybe_set_conversation_title,
    memory_factory,
):
    if app is None:
        raise RuntimeError("FastAPI app is required")
    if require_current_user is None:
        raise RuntimeError("authentication helper is required")

    @app.post("/api/chat/stream")
    async def chat_stream_endpoint(request: Request, chat: StreamChatRequest):
        user_row = await __import__("asyncio").to_thread(
            require_current_user, request
        )
        user_id = str(user_row["id"] if isinstance(user_row, dict) else user_row[0])
        message = str(chat.message or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message required")

        conversation_id = await __import__("asyncio").to_thread(
            get_or_create_conversation,
            user_id,
            (chat.conversation_id or "").strip() or None,
        )
        await __import__("asyncio").to_thread(
            maybe_set_conversation_title,
            conversation_id,
            message,
        )

        return StreamingResponse(
            _build_stream_generator(
                user_id=user_id,
                message=message,
                conversation_id=str(conversation_id),
                memory_factory=memory_factory,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    logger.info("REALTIME_TEXT_STREAMING_PATCH_INSTALLED")
