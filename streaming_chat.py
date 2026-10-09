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

        # Providers occasionally omit/advertise an incorrect charset on SSE.
        # Requests can then decode UTF-8 emoji as Latin-1/Windows-1252 before
        # JSON parsing, producing text such as "Ã°ÂÂÂ" in the web chat.
        # SSE/JSON from our providers is UTF-8; force that decoding here.
        response.encoding = "utf-8"

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


def _stream_cloudflare(messages: list):
    """Call the Cloudflare Worker chat endpoint; it returns a JSON completion, not SSE."""
    token = ai_engine.CLOUDFLARE_AI_TOKEN
    url = ai_engine.CLOUDFLARE_AI_URL
    if not token:
        raise RuntimeError("cloudflare_not_configured")
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"model": "@cf/meta/llama-3.1-8b-instruct", "messages": messages,
              "temperature": 0.7, "max_tokens": 1200},
        timeout=(10, _TIMEOUT),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"cloudflare_http_{response.status_code}: {response.text[:300]}")
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("cloudflare_empty_completion")
    text = (choices[0].get("message") or {}).get("content")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("cloudflare_empty_completion")
    yield text


def _provider_streams(messages: list):
    # Keep streaming chat aligned with ai_engine's Cloudflare-first provider
    # order. Cloudflare's Worker returns a complete JSON answer, so emit it as
    # one SSE token; the frontend still receives the same stream event format.
    if ai_engine.CLOUDFLARE_AI_TOKEN:
        yield "cloudflare", _stream_cloudflare(messages)
    if ai_engine.OPENAI_API_KEY:
        yield "openai", _stream_openai_compatible(
            url=ai_engine.OPENAI_URL,
            key=ai_engine.OPENAI_API_KEY,
            model=ai_engine.OPENAI_MODEL,
            messages=messages,
        )
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

    # Account/connector actions must never fall through to the general LLM.
    # The streaming endpoint used to bypass account_agent entirely, which made
    # connected Gmail requests receive a generic "I cannot send email" answer.
    # Keep the existing approval/evidence gate authoritative by routing these
    # requests through the same web account agent used by /api/chat.
    try:
        from account_agent import handle_web_request
        connector_result = handle_web_request(str(user_id), message)
    except Exception as exc:
        logger.warning("Streaming connector router failed: %s", type(exc).__name__)
        connector_result = None

    if connector_result is not None:
        reply = str(connector_result.get("reply") or "").strip()
        if reply:
            engine._save_memory(user_id, message, reply)
            yield _sse({"type": "start", "provider": "account_agent"})
            yield _sse({"type": "delta", "text": reply})
            yield _sse({
                "type": "done",
                "conversation_id": conversation_id,
                "text": reply,
                "connector": True,
                "status": connector_result.get("status"),
                "kind": connector_result.get("kind"),
                "approval_id": connector_result.get("approval_id"),
                "provider": connector_result.get("provider"),
                "operation": connector_result.get("operation"),
                "target": connector_result.get("target"),
            })
            return

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


    # ------------------------------------------------------------------
    # Connector-aware chat bridge
    #
    # The main /api/chat and streaming /api/chat/stream routes normally
    # delegate to AIEngine. That is correct for ordinary conversation, but
    # it also meant a natural-language request such as "send an email to
    # ..." never reached the already-connected Google connector. Intercept
    # only explicit Gmail read/send intents here and leave all other chat
    # traffic untouched.
    # ------------------------------------------------------------------
    try:
        from fastapi.responses import JSONResponse, StreamingResponse as _ConnectorStreamingResponse
        from account_agent import handle_web_request
        
        def _connector_chat_intent(text: str):
            raw = str(text or "").strip().lower()
            if not raw:
                return False
            # Approval commands may include the exact approval UUID.
            # Keep them on the deterministic connector path instead of letting
            # the general LLM answer as if Gmail were unavailable.
            if re.fullmatch(r"(approve|reject)(?:\s+[0-9a-fA-F-]{36})?", raw):
                return True
            if raw in {
                "account status", "check connected accounts", "what accounts are connected",
                "show connected accounts", "check my connections", "monitor account status",
                "check my email", "check my gmail", "check my inbox", "check email", "check gmail",
                "check my drive", "check drive", "show my drive files",
                "check my calendar", "check calendar", "what is on my calendar", "show my calendar",
            }:
                return True
            if raw.startswith(("monitor my account", "monitor my gmail", "watch my gmail", "stop monitoring")):
                return True
            # Route explicit Shopify/store requests to the connected official
            # Shopify connector so they do not fall through to generic chat.
            if re.search(r"\b(shopify|my store|my shop|storefront|products|inventory|stock|orders|sales|purchases)\b", raw):
                return True
            # Route all explicit email work to the connector, even when
            # the user has not supplied the recipient/content yet. This keeps
            # compose/send requests out of the generic LLM fallback.
            return bool(re.search(r"\b(send|email|mail|compose|draft|write)\b", raw))

        def _connector_reply(user_id: str, message: str, conversation_id: str):
            result = handle_web_request(user_id, message)
            if not result:
                return None
            return {
                **result,
                "conversation_id": conversation_id,
                "connector_action": result.get("connector_action"),
            }

        async def _handle_connector_chat(request: Request, message: str, *, stream: bool, requested_conversation_id: str | None = None):
            user_row = await __import__("asyncio").to_thread(
                require_current_user, request
            )
            user_id = str(user_row["id"] if isinstance(user_row, dict) else user_row[0])
            # Conversation persistence is useful, but it must never prevent
            # a connected-account action from being prepared or executed.
            # If the conversation table/path is temporarily unavailable, keep
            # the connector action authoritative and use a transient ID.
            requested_id = (requested_conversation_id or "").strip() or None
            try:
                conversation_id = await __import__("asyncio").to_thread(
                    get_or_create_conversation,
                    user_id,
                    requested_id,
                )
                try:
                    await __import__("asyncio").to_thread(
                        maybe_set_conversation_title,
                        conversation_id,
                        message,
                    )
                except Exception as exc:
                    logger.warning(
                        "Connector conversation title update skipped: %s",
                        type(exc).__name__,
                    )
            except Exception as exc:
                import uuid
                conversation_id = requested_id or str(uuid.uuid4())
                logger.warning(
                    "Connector conversation setup skipped; action continues: %s",
                    type(exc).__name__,
                )

            try:
                result = await __import__("asyncio").to_thread(
                    _connector_reply,
                    user_id,
                    message,
                    str(conversation_id),
                )
            except Exception as exc:
                logger.exception(
                    "Connected-account action preparation failed: %s",
                    type(exc).__name__,
                )
                return JSONResponse(
                    {
                        "detail": "Connected-account action failed before preparation.",
                        "error_type": type(exc).__name__,
                    },
                    status_code=502,
                )
            if not result:
                return None

            # Persist the same user/assistant exchange that normal chat would
            # persist, without invoking the LLM for an external action.
            try:
                memory = memory_factory(user_id, str(conversation_id))
                memory.add_message(user_id, "user", message)
                memory.add_message(user_id, "assistant", result["reply"])
            except Exception as exc:
                logger.warning("Connector chat memory write failed: %s", type(exc).__name__)

            if not stream:
                return JSONResponse({
                    "status": "success",
                    "reply": result["reply"],
                    "conversation_id": str(conversation_id),
                    **({"connector_action": result["connector_action"]} if result.get("connector_action") else {}),
                })

            async def connector_events():
                yield _sse({"type": "start", "provider": "connector"})
                yield _sse({"type": "delta", "text": result["reply"]})
                yield _sse({
                    "type": "done",
                    "conversation_id": str(conversation_id),
                    "text": result["reply"],
                    **({"connector_action": result["connector_action"]} if result.get("connector_action") else {}),
                })

            return _ConnectorStreamingResponse(
                connector_events(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-transform",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        @app.middleware("http")
        async def connector_chat_middleware(request: Request, call_next):
            if request.method != "POST" or request.url.path not in {"/api/chat", "/api/chat/stream"}:
                return await call_next(request)

            try:
                raw_body = await request.body()
                payload = json.loads(raw_body.decode("utf-8") or "{}")
                message = str(payload.get("message") or "").strip()
                if not message:
                    return await call_next(request)

                # Route explicit KZ Work missions through the central agent
                # before ordinary chat. This keeps normal conversation unchanged.
                try:
                    from work_intent import parse as parse_work_intent
                    work_intent = parse_work_intent(message)
                except Exception:
                    work_intent = None

                if work_intent and work_intent.get("kind") == "create":
                    try:
                        from kz_agent import run as run_kz_agent
                        user_row = await __import__("asyncio").to_thread(
                            require_current_user, request
                        )
                        user_id = str(
                            user_row.get("id")
                            if isinstance(user_row, dict)
                            else user_row[0]
                        )
                        agent = await __import__("asyncio").to_thread(
                            run_kz_agent,
                            user_id,
                            str(work_intent.get("goal") or message),
                            account_id=str(payload.get("account_id") or "").strip() or None,
                            run_now=True,
                        )
                        reply = (
                            "KZ AGENT mission started.\\n\\n"
                            f"Goal: {agent.get('goal', '')}\\n"
                            f"Status: {agent.get('status', '').replace('_', ' ')}\\n"
                            f"Now: {agent.get('activity', '')}\\n"
                            f"Mission ID: {agent.get('id', '')}\\n\\n"
                            "I will stop for approval before consequential actions."
                        )
                        if request.url.path == "/api/chat/stream":
                            async def agent_events():
                                yield _sse({"type": "start", "provider": "kz_agent"})
                                yield _sse({"type": "agent", "agent": agent})
                                yield _sse({"type": "delta", "text": reply})
                                yield _sse({"type": "done", "text": reply, "agent": agent})
                            return _ConnectorStreamingResponse(
                                agent_events(), media_type="text/event-stream",
                                headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
                            )
                        return JSONResponse({"status": "success", "reply": reply, "agent": agent})
                    except Exception as exc:
                        logger.exception("KZ Agent mission creation failed: %s", type(exc).__name__)
                        return JSONResponse({"detail": "KZ Agent could not start the mission safely."}, status_code=500)

                # Only authenticate/intercept when this is an explicit connector
                # intent. Ordinary chat keeps its exact existing behavior.
                intent = _connector_chat_intent(message)
                if not intent:
                    return await call_next(request)

                return await _handle_connector_chat(
                    request,
                    message,
                    stream=request.url.path == "/api/chat/stream",
                    requested_conversation_id=str(payload.get("conversation_id") or "").strip() or None,
                )
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            except Exception as exc:
                logger.exception("Connector chat bridge failed: %s", type(exc).__name__)
                return JSONResponse(
                    {"detail": "Connected-account action could not be prepared safely."},
                    status_code=500,
                )

        logger.info("CONNECTOR_CHAT_BRIDGE_INSTALLED")
    except Exception as exc:
        logger.exception("CONNECTOR_CHAT_BRIDGE_FAILED: %s", type(exc).__name__)

    logger.info("REALTIME_TEXT_STREAMING_PATCH_INSTALLED")
