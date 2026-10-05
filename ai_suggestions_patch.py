"""Additive endpoint that generates contextual follow-up suggestions from the AI itself."""
from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field


class SuggestionRequest(BaseModel):
    user_message: str = Field(min_length=1, max_length=3000)
    assistant_response: str = Field(min_length=1, max_length=6000)


def install_ai_suggestions(app, require_current_user):
    if app is None or require_current_user is None:
        raise RuntimeError("app and authentication helper are required")

    @app.post("/api/chat/suggestions")
    async def chat_suggestions_endpoint(request: Request, payload: SuggestionRequest):
        await __import__("asyncio").to_thread(require_current_user, request)
        from ai_suggestions import generate_suggestions

        suggestions = await __import__("asyncio").to_thread(
            generate_suggestions,
            payload.user_message,
            payload.assistant_response,
        )
        return {"status": "ok", "suggestions": suggestions}

