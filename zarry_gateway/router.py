"""Authenticated FastAPI routes for the general-assistant gateway."""
from __future__ import annotations
import inspect
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from .identity import AuthenticatedPrincipal
from .policy import general_gateway_enabled
from .schemas import AssistantRequest, AssistantResponse, ImageRequest, ImageResponse


def create_general_router(require_web_user, gateway, enabled_check=general_gateway_enabled):
    router = APIRouter(prefix="/api/assistant", tags=["ZARRY general assistant"])

    async def principal_for(request: Request) -> AuthenticatedPrincipal:
        user = require_web_user(request)
        if inspect.isawaitable(user):
            user = await user
        user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        return AuthenticatedPrincipal(
            subject_id=f"web:{user_id}", platform="web",
            platform_user_id=str(user_id), shared_memory_enabled=False,
        )

    @router.post("/chat", response_model=AssistantResponse)
    async def chat(payload: AssistantRequest, request: Request):
        if not enabled_check():
            raise HTTPException(status_code=503, detail="ZARRY general assistant is not enabled")
        principal = await principal_for(request)
        handler = getattr(gateway, "chat", None)
        if not callable(handler):
            raise HTTPException(status_code=503, detail="ZARRY assistant is unavailable")
        result = handler(principal=principal, payload=payload)
        if inspect.isawaitable(result):
            result = await result
        try:
            return AssistantResponse.model_validate(result)
        except Exception:
            raise HTTPException(status_code=502, detail="Invalid assistant response")

    @router.post("/image", response_model=ImageResponse)
    async def image(payload: ImageRequest, request: Request):
        if not enabled_check():
            raise HTTPException(status_code=503, detail="ZARRY general assistant is not enabled")
        principal = await principal_for(request)
        handler = getattr(gateway, "image", None)
        if not callable(handler):
            raise HTTPException(status_code=503, detail="Image generation is unavailable")
        result = handler(principal=principal, payload=payload)
        if inspect.isawaitable(result):
            result = await result
        try:
            return ImageResponse.model_validate(result)
        except Exception:
            raise HTTPException(status_code=502, detail="Invalid image response")

    return router
