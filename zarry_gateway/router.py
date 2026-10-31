"""Authenticated FastAPI routes for the general-assistant gateway."""
import inspect
from fastapi import APIRouter, HTTPException, Request
from .identity import AuthenticatedPrincipal
from .policy import general_gateway_enabled, image_generation_enabled
from .schemas import (
    AssistantRequest, AssistantResponse, ImageRequest, ImageResponse,
    MemoryPreferenceRequest,
)


def create_general_router(
    require_web_user, gateway, enabled_check=general_gateway_enabled,
    image_enabled_check=image_generation_enabled,
):
    router = APIRouter(prefix="/api/assistant", tags=["ZARRY general assistant"])

    async def principal_for(request: Request):
        user = require_web_user(request)
        if inspect.isawaitable(user):
            user = await user
        user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        return AuthenticatedPrincipal(
            subject_id=f"web:{user_id}", platform="web", platform_user_id=str(user_id)
        )

    @router.get("/memory")
    async def memory_preference(request: Request):
        principal = await principal_for(request)
        store = getattr(gateway, "memory_store", None)
        if store is None:
            return {"enabled": False}
        try:
            return {"enabled": bool(store.is_enabled(principal))}
        except Exception:
            raise HTTPException(status_code=503, detail="Memory preference is unavailable")

    @router.put("/memory")
    async def update_memory_preference(payload: MemoryPreferenceRequest, request: Request):
        principal = await principal_for(request)
        store = getattr(gateway, "memory_store", None)
        if store is None:
            raise HTTPException(status_code=503, detail="Memory is unavailable")
        try:
            store.set_enabled(principal, payload.enabled)
            return {"enabled": bool(payload.enabled)}
        except Exception:
            raise HTTPException(status_code=503, detail="Could not update memory preference")

    @router.post("/chat", response_model=AssistantResponse)
    async def chat(payload: AssistantRequest, request: Request):
        if not enabled_check():
            raise HTTPException(status_code=503, detail="ZARRY general assistant is not enabled")
        principal = await principal_for(request)
        handler = getattr(gateway, "chat", None)
        if not callable(handler):
            raise HTTPException(status_code=503, detail="ZARRY assistant is unavailable")
        try:
            result = handler(principal=principal, payload=payload)
            if inspect.isawaitable(result):
                result = await result
            return AssistantResponse.model_validate(result)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=502, detail="ZARRY assistant request failed")

    @router.post("/image", response_model=ImageResponse)
    async def image(payload: ImageRequest, request: Request):
        if not enabled_check() or not image_enabled_check():
            raise HTTPException(status_code=503, detail="ZARRY image generation is not enabled")
        principal = await principal_for(request)
        handler = getattr(gateway, "image", None)
        if not callable(handler):
            raise HTTPException(status_code=503, detail="Image generation is unavailable")
        try:
            result = handler(principal=principal, payload=payload)
            if inspect.isawaitable(result):
                result = await result
            return ImageResponse.model_validate(result)
        except HTTPException:
            raise
        except Exception:
            # Provider errors and malformed responses must not leak internal
            # details or become unstructured server errors.
            raise HTTPException(status_code=502, detail="ZARRY image request failed")

    return router
