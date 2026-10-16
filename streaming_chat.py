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
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import ai_engine

logger = logging.getLogger("kz_streaming_chat")

_TIMEOUT = max(8, min(int(os.getenv("AI_STREAM_TIMEOUT", "30")), 30))
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
    return "data: " + json.dumps(jsonable_encoder(event), ensure_ascii=False, separators=(",", ":")) + "\n\n"


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
    token_parameter: str = "max_tokens",
) -> Generator[str, None, None]:
    if not key:
        raise RuntimeError("provider_not_configured")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.85,
        token_parameter: 2000,
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
        json={"model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "messages": messages,
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



def _build_zarry_context(messages: list):
    """Keep system instructions/project memory while bounding recent chat history."""
    items = [item for item in (messages or []) if isinstance(item, dict)]
    system_message = next((item for item in items if item.get("role") == "system"), None)
    recent_turns = [
        item for item in items
        if item.get("role") in ("user", "assistant")
    ][-4:]
    context_messages = ([system_message] if system_message else []) + recent_turns

    sections = []
    if system_message:
        system_content = system_message.get("content", "")
        if isinstance(system_content, str) and system_content.strip():
            sections.append("SYSTEM INSTRUCTIONS AND PROJECT MEMORY:\n" + system_content.strip())
    if recent_turns:
        lines = ["RECENT CONVERSATION:"]
        for item in recent_turns:
            text = item.get("content", "")
            if not isinstance(text, str) or not text.strip():
                continue
            role = "USER" if item.get("role") == "user" else "ASSISTANT"
            lines.append(f"{role}: {text.strip()}")
        if len(lines) > 1:
            sections.append("\n".join(lines))
    return "\n\n".join(sections).strip(), context_messages


def _stream_zarry(messages: list):
    """Use the Colab-hosted Zarry /generate API for the streaming chat path."""
    endpoint = os.getenv("ZARRY_API_URL", "").strip()
    if not endpoint:
        raise RuntimeError("zarry_not_configured")
    prompt, context_messages = _build_zarry_context(messages)
    payload = {
        # Some /generate implementations prioritize prompt over messages;
        # include system instructions and project memory in all prompt aliases.
        "prompt": prompt, "input": prompt, "text": prompt,
        "messages": context_messages, "history": context_messages[-4:], "max_new_tokens": 192,
        "temperature": 0.7,
    }
    headers = {"Content-Type": "application/json", "bypass-tunnel-reminder": "true"}
    token = os.getenv("ZARRY_API_KEY", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(endpoint, json=payload, headers=headers, timeout=(8, min(_TIMEOUT, 25)))
    if response.status_code >= 400:
        raise RuntimeError(f"zarry_http_{response.status_code}")
    data = response.json()
    answer = data if isinstance(data, str) else None
    if isinstance(data, dict):
        for key in ("response", "generated_text", "text", "output", "result", "answer", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                answer = value
                break
        if not answer:
            choices = data.get("choices") or []
            if choices and isinstance(choices[0], dict):
                answer = (choices[0].get("message") or {}).get("content") or choices[0].get("text")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("zarry_empty_completion")
    yield answer.strip()


def _provider_streams(messages: list):
    # Prefer the user's Colab-hosted Zarry model for streaming chat as well.
    if os.getenv("ZARRY_API_URL", "").strip():
        yield "zarry", _stream_zarry(messages)
    if ai_engine.HF_TOKEN:
        yield "huggingface", _stream_openai_compatible(
            url=ai_engine.HF_INFERENCE_URL,
            key=ai_engine.HF_TOKEN,
            model=ai_engine.HF_MODEL_ID,
            messages=messages,
        )
        # A configured/custom model may be missing or unavailable on the HF router.
        # Try the known OpenAI-compatible fallback before moving to other providers.
        fallback_model = (getattr(ai_engine, "HF_FALLBACK_MODEL_ID", "") or "").strip()
        if fallback_model and fallback_model != ai_engine.HF_MODEL_ID:
            yield "huggingface_fallback", _stream_openai_compatible(
                url=ai_engine.HF_INFERENCE_URL,
                key=ai_engine.HF_TOKEN,
                model=fallback_model,
                messages=messages,
            )
    # Cloudflare's Worker returns a complete JSON answer, so emit it as one SSE token.
    if ai_engine.CLOUDFLARE_AI_TOKEN:
        yield "cloudflare", _stream_cloudflare(messages)
    if ai_engine.OPENAI_API_KEY:
        yield "openai", _stream_openai_compatible(
            url=ai_engine.OPENAI_URL,
            key=ai_engine.OPENAI_API_KEY,
            model=ai_engine.OPENAI_MODEL,
            messages=messages,
            token_parameter="max_completion_tokens",
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
    yield _sse({"type": "activity", "stage": "thinking", "label": "Thinking through your request", "done": False})

    # Match /api/chat routing: explicit image/video requests must be handled
    # before coding, connectors, or ordinary LLM streaming. The streaming
    # request currently carries text only, so image edits ask for an upload.
    try:
        media_intent = ai_engine._detect_media_intent(message, has_image=False)
    except Exception as exc:
        logger.warning("Streaming media intent detection failed: %s", type(exc).__name__)
        media_intent = None
    if media_intent is not None:
        try:
            reply = str(engine._route_media_request(user_id, message, media_intent, None) or "").strip()
        except Exception as exc:
            logger.exception("Streaming media task failed safely: %s", type(exc).__name__)
            reply = "I recognized this as a media task, but the media pipeline failed. No successful output was created; please retry or check the media provider configuration."
        if not reply:
            reply = "I recognized this as a media task, but no media result was returned. Nothing is being reported as completed."
        engine._save_memory(user_id, message, reply)
        yield _sse({"type": "activity", "stage": "media", "label": "Handling image/video request", "done": True})
        yield _sse({"type": "start", "provider": "media_agent"})
        yield _sse({"type": "delta", "text": reply})
        yield _sse({
            "type": "done",
            "conversation_id": conversation_id,
            "text": reply,
            "provider": "media_agent",
            "status": "handled",
        })
        return

    # Build requests must use the coding executor instead of the generic chat model.
    # Keep this before web research and ordinary generation so the request cannot drift
    # into an unrelated email/account explanation.
    try:
        from coding_request import handle_coding_request
        coding_result = handle_coding_request(message)
    except Exception as exc:
        logger.exception("Streaming coding router failed: %s", type(exc).__name__)
        coding_result = {
            "status": "error",
            "provider": "coding_agent",
            "operation": "generate_project",
            "reply": "The Coding Agent could not start safely. No project was created or deployed. Check Railway logs and retry.",
            "project": None,
        }
    if coding_result is not None:
        reply = str(coding_result.get("reply") or "").strip()
        engine._save_memory(user_id, message, reply)
        yield _sse({"type": "activity", "stage": "coding", "label": "Generating project files", "done": True})
        yield _sse({"type": "start", "provider": "coding_agent"})
        yield _sse({"type": "delta", "text": reply})
        yield _sse({
            "type": "done",
            "conversation_id": conversation_id,
            "text": reply,
            "status": coding_result.get("status"),
            "provider": "coding_agent",
            "operation": coding_result.get("operation"),
            "project": coding_result.get("project"),
        })
        return

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
            yield _sse({"type": "activity", "stage": "responding", "label": "Preparing connected-account response", "done": False})
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

    # Keep explicit market/capability/project requests on the same specialist
    # router as /api/chat. Without this, the streaming endpoint can answer with
    # generic prose instead of a verified market-agent result.
    try:
        import agent_router
        agent_result = agent_router.route_agent_request(message, str(user_id))
    except Exception as exc:
        logger.exception("Streaming specialist router failed: %s", type(exc).__name__)
        agent_result = None
        try:
            import agent_router
            if agent_router._market_requested(message):
                agent_result = {
                    "status": "unavailable",
                    "provider": "market_agent",
                    "reply": "I recognized this as a market-analysis request, but the Market Agent failed safely. No price or signal was invented; check market-provider configuration and retry.",
                }
        except Exception:
            pass
    if agent_result is not None and str(agent_result.get("reply") or "").strip():
        reply = str(agent_result["reply"])[:8000]
        engine._save_memory(user_id, message, reply)
        yield _sse({"type": "activity", "stage": "specialist", "label": "Using the relevant specialist agent", "done": True})
        yield _sse({"type": "start", "provider": str(agent_result.get("provider") or "specialist_agent")})
        yield _sse({"type": "delta", "text": reply})
        yield _sse({
            "type": "done",
            "conversation_id": conversation_id,
            "text": reply,
            "status": agent_result.get("status") or "completed",
            "provider": agent_result.get("provider"),
            "operation": agent_result.get("operation"),
            "target": agent_result.get("target"),
        })
        return

    # Streaming is intentionally limited to ordinary text chat after media,
    # coding, account, and specialist routers have all declined the request.
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

    research_footer = ""
    try:
        import web_research_engine as web_research
        import tavily_search
        wants_research = web_research.should_research(message)
        wants_tavily = tavily_search.should_trigger_tavily(message)
        if wants_research or wants_tavily:
            if web_research.is_configured():
                yield _sse({
                    "type": "activity",
                    "stage": "searching",
                    "label": "Searching the web",
                    "done": False,
                })
                research_result = web_research.research(
                    message,
                    deep=any(term in message.lower() for term in ("deep research", "comprehensive", "thorough", "in-depth")),
                )
                search_count = int(research_result.get("searches") or 0)
                source_list = research_result.get("sources") or []
                source_count = len(source_list)
                research_context = web_research.format_for_ai(research_result)
                if research_context:
                    persistent_ctx = (persistent_ctx + "\n\n" + research_context).strip()
                    research_footer = web_research.sources_footer(source_list)
                yield _sse({
                    "type": "activity",
                    "stage": "searching",
                    "label": f"Web searches: {search_count} · sources found: {source_count}",
                    "done": True,
                    "searches": search_count,
                    "sources": source_count,
                    "source_urls": [{"title": str(s.get("title") or ""), "url": str(s.get("url") or "")} for s in source_list[:8] if isinstance(s, dict) and str(s.get("url") or "").startswith(("https://", "http://"))],
                })
            elif tavily_search.is_tavily_configured() and wants_tavily:
                yield _sse({
                    "type": "activity",
                    "stage": "searching",
                    "label": "Searching the web with Tavily",
                    "done": False,
                })
                tavily_result = tavily_search.search_web(message, max_results=5, search_depth="basic", include_answer=True)
                source_list = tavily_result.get("sources") or []
                source_count = len(source_list)
                search_count = 0 if tavily_result.get("cached") else 1
                research_context = tavily_search.format_for_ai(tavily_result)
                if research_context:
                    persistent_ctx = (persistent_ctx + "\n\n" + research_context).strip()
                    research_footer = web_research.sources_footer(source_list)
                yield _sse({
                    "type": "activity",
                    "stage": "searching",
                    "label": (f"Cached web results reused · sources found: {source_count}" if tavily_result.get("cached") else f"Web searches: {search_count} · sources found: {source_count}"),
                    "done": True,
                    "searches": search_count,
                    "sources": source_count,
                    "source_urls": [{"title": str(s.get("title") or ""), "url": str(s.get("url") or "")} for s in source_list[:8] if isinstance(s, dict) and str(s.get("url") or "").startswith(("https://", "http://"))],
                })
            else:
                yield _sse({
                    "type": "activity",
                    "stage": "searching",
                    "label": "Web search unavailable — no configured search provider can handle this request",
                    "done": True,
                    "searches": 0,
                    "sources": 0,
                })
    except Exception as exc:
        logger.warning("Streaming web research failed: %s", type(exc).__name__)
        yield _sse({
            "type": "activity",
            "stage": "searching",
            "label": "Web research failed; continuing without search results",
            "done": True,
        })

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
            yield _sse({"type": "activity", "stage": "responding", "label": "Writing response", "done": False})
            yield _sse({"type": "start", "provider": provider_name})
            for delta in stream:
                full_text += delta
                yield _sse({"type": "delta", "text": delta})
            if full_text.strip():
                cleaned = ai_engine.clean_ai_response(full_text).strip()
                if cleaned and research_footer and "**Sources:**" not in cleaned:
                    cleaned += research_footer
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
            # Log the real, sanitized provider error so HTTP status/auth/route
            # failures can be diagnosed from Railway without exposing API tokens.
            safe_error = ai_engine._redact_secrets(str(exc))[:350]
            logger.warning(
                "Streaming provider failed | provider=%s error_type=%s detail=%s",
                provider_name,
                type(exc).__name__,
                safe_error,
            )
            # Never append a second provider's full response after partial
            # output: that would duplicate text in the UI. The frontend can
            # keep the partial response rather than silently corrupting it.
            if full_text.strip():
                cleaned = ai_engine.clean_ai_response(full_text).strip()
                if cleaned and research_footer and "**Sources:**" not in cleaned:
                    cleaned += research_footer
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

    # Streaming endpoints are not supported by every provider and can fail
    # independently of normal chat. Make one final attempt through AIEngine's
    # standard non-streaming provider router before reporting an error.
    try:
        logger.warning("Streaming providers exhausted; trying AIEngine fallback")
        fallback_text = str(engine.ask(user_id, message) or "").strip()
        if fallback_text:
            cleaned = ai_engine.clean_ai_response(fallback_text).strip()
            if cleaned:
                engine._save_memory(user_id, message, cleaned)
                yield _sse({"type": "start", "provider": "ai_engine_fallback"})
                yield _sse({"type": "delta", "text": cleaned})
                yield _sse({
                    "type": "done",
                    "conversation_id": conversation_id,
                    "text": cleaned,
                    "fallback": True,
                    "provider": "ai_engine_fallback",
                })
                return
    except Exception as exc:
        safe_error = ai_engine._redact_secrets(str(exc))[:350]
        logger.exception("AIEngine final fallback failed: %s", safe_error)

    yield _sse({
        "type": "error",
        "message": "AI providers are temporarily unavailable. Please try again shortly.",
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

                # Explicit media requests must not be interpreted as broad KZ
                # Work missions (e.g. "fix this image for me"). Let the media
                # router handle those before work/connector interception.
                try:
                    media_intent_for_work = ai_engine._detect_media_intent(message, has_image=False)
                except Exception:
                    media_intent_for_work = None
                if media_intent_for_work is not None:
                    work_intent = None
                else:
                    try:
                        from work_intent import parse as parse_work_intent
                        work_intent = parse_work_intent(message)
                    except Exception:
                        work_intent = None

                if work_intent and work_intent.get("kind") in {"approve", "reject", "status"}:
                    try:
                        from kz_agent import approve as approve_kz_agent, get as get_kz_agent
                        user_row = await __import__("asyncio").to_thread(require_current_user, request)
                        user_id = str(user_row.get("id") if isinstance(user_row, dict) else user_row[0])
                        kind = work_intent["kind"]
                        workflow_id = str(work_intent.get("workflow_id") or "")
                        if kind == "status":
                            agent = await __import__("asyncio").to_thread(get_kz_agent, user_id, workflow_id)
                        else:
                            agent = await __import__("asyncio").to_thread(approve_kz_agent, user_id, workflow_id, kind == "approve")
                            if kind == "approve" and agent.get("status") == "approved":
                                from workflow_engine import run_workflow
                                await __import__("asyncio").to_thread(run_workflow, workflow_id, user_id)
                                agent = await __import__("asyncio").to_thread(get_kz_agent, user_id, workflow_id)
                        agent = jsonable_encoder(agent)
                        if not agent or agent.get("status") == "not_found":
                            return JSONResponse({"detail": "KZ mission not found for this account. Check the full mission ID."}, status_code=404)
                        reply = (f"KZ mission {kind} processed.\\n\\nGoal: {agent.get('goal', '')}\\nStatus: {str(agent.get('status', '')).replace('_', ' ')}\\nProgress: {agent.get('completed_steps', 0)}/{agent.get('total_steps', 0)} steps\\nMission ID: {agent.get('id', workflow_id)}\\nNext: {agent.get('activity', '')}")
                        if request.url.path == "/api/chat/stream":
                            async def work_events():
                                yield _sse({"type": "start", "provider": "kz_agent"})
                                yield _sse({"type": "agent", "agent": agent})
                                yield _sse({"type": "delta", "text": reply})
                                yield _sse({"type": "done", "text": reply, "agent": agent})
                            return _ConnectorStreamingResponse(work_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
                        return JSONResponse({"status": "success", "reply": reply, "agent": agent})
                    except ValueError as exc:
                        msg = str(exc)
                        return JSONResponse({"detail": msg}, status_code=404 if "not found" in msg.lower() else 400)
                    except Exception as exc:
                        logger.exception("KZ Work decision failed: %s", type(exc).__name__)
                        return JSONResponse({"detail": "KZ Work could not process this decision safely."}, status_code=500)

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
                        agent = jsonable_encoder(agent)
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

                connector_response = await _handle_connector_chat(
                    request,
                    message,
                    stream=request.url.path == "/api/chat/stream",
                    requested_conversation_id=str(payload.get("conversation_id") or "").strip() or None,
                )
                # Starlette requires every HTTP middleware path to return a
                # Response. A connector intent can be recognized before the
                # account agent has enough context to act; in that case, let
                # the normal chat route handle the message instead of returning
                # None (which crashes the entire ASGI request with
                # TypeError: 'NoneType' object is not callable).
                if connector_response is None:
                    logger.info("Connector intent had no actionable result; falling back to normal chat")
                    return await call_next(request)
                return connector_response
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
