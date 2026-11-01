"""Separate general-chat contract for ZARRY; never accepts Kitty/trading authority data."""
from __future__ import annotations

import hmac
import os
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class GeneralChatRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=80)
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, messages):
        if messages[-1].role != "user":
            raise ValueError("last message must be from the user")
        if sum(len(m.content) for m in messages) > 24000:
            raise ValueError("conversation payload is too large")
        return messages


class GeneralChatResponse(StrictModel):
    request_id: str
    response: str = Field(min_length=1, max_length=12000)
    model: str = Field(min_length=1, max_length=120)


GENERAL_SYSTEM_PROMPT = (
    "You are ZARRY, a helpful general-purpose AI assistant. "
    "Answer clearly and honestly. Do not claim to have performed actions you have not performed. "
    "You have no authority to make trading decisions, access broker accounts, or place orders. "
    "If asked about trading, explain general concepts only; Kitty remains the sole trading authority."
)


def _chat_max_tokens() -> int:
    """Bound general-chat generation so a bad setting cannot exhaust CPU resources."""
    try:
        value = int(os.getenv("ZARRY_CHAT_MAX_TOKENS", "128"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="general chat token configuration is invalid") from exc
    if value < 16 or value > 512:
        raise HTTPException(status_code=503, detail="general chat token limit must be between 16 and 512")
    return value


def create_general_chat_router():
    router = APIRouter(prefix="/v1", tags=["ZARRY general chat"])

    async def authenticate(authorization: str | None = Header(default=None)):
        expected = os.getenv("ZARRY_API_KEY", "")
        parts = authorization.split() if authorization else []
        supplied = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""
        if not expected:
            raise HTTPException(status_code=503, detail="service authentication is not configured")
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @router.post("/chat", response_model=GeneralChatResponse, dependencies=[Depends(authenticate)])
    def chat(payload: GeneralChatRequest, request: Request):
        model = getattr(request.app.state, "model", None)
        if model is None:
            raise HTTPException(status_code=503, detail="model is not loaded")
        messages = [{"role": "system", "content": GENERAL_SYSTEM_PROMPT}]
        messages.extend(message.model_dump() for message in payload.messages)
        max_tokens = _chat_max_tokens()
        model_lock = getattr(request.app.state, "model_lock", None)
        if model_lock is None:
            raise HTTPException(status_code=503, detail="model inference lock is not initialized")
        try:
            with model_lock:
                result = model.create_chat_completion(
                    messages=messages,
                    temperature=0.4,
                    max_tokens=max_tokens,
                )
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("empty model response")
        except Exception as exc:
            raise HTTPException(status_code=502, detail="general chat inference failed") from exc
        return GeneralChatResponse(
            request_id=payload.request_id,
            response=answer.strip()[:12000],
            model=os.getenv("ZARRY_MODEL_REPO", "self-hosted-zarry"),
        )

    return router
