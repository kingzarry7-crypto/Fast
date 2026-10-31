"""Authenticated FastAPI routes for the general-assistant gateway."""
import inspect
import time
from fastapi import APIRouter, HTTPException, Request
from .identity import AuthenticatedPrincipal
from .policy import general_gateway_enabled, image_generation_enabled
from .schemas import (
    AssistantRequest, AssistantResponse, ImageRequest, ImageResponse,
    MemoryPreferenceRequest,
)


def create_general_router(
    require_web_user, gateway, enabled_check=general_gateway_enabled,
    image_enabled_check=image_generation_enabled, admin_check=None,
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

    @router.post("/admin/connection-test")
    async def admin_connection_test(request: Request):
        # This diagnostic is deliberately independent of the public chat flag.
        # It is callable only through the application's existing admin gate.
        if admin_check is None:
            raise HTTPException(status_code=503, detail="Admin connection test is unavailable")
        try:
            admin = admin_check(request)
            if inspect.isawaitable(admin):
                admin = await admin
            user = admin[0] if isinstance(admin, tuple) else admin
            user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
            if not user_id and isinstance(user, (tuple, list)) and user:
                user_id = user[0]
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            principal = AuthenticatedPrincipal(
                subject_id=f"web:{user_id}", platform="web", platform_user_id=str(user_id)
            )
            handler = getattr(gateway, "chat", None)
            if not callable(handler):
                raise HTTPException(status_code=503, detail="ZARRY assistant is unavailable")
            payload = AssistantRequest(message="Reply with exactly: ZARRY_CONNECTION_OK.")
            started = time.monotonic()
            result = handler(principal=principal, payload=payload)
            if inspect.isawaitable(result):
                result = await result
            validated = AssistantResponse.model_validate(result)
            if validated.request_id != payload.request_id or not validated.response.strip():
                raise RuntimeError("ZARRY returned an invalid smoke-test response")
            return {
                "status": "ok",
                "provider": validated.provider,
                "request_id": str(validated.request_id),
                "latency_ms": max(0, round((time.monotonic() - started) * 1000)),
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=502, detail="ZARRY connection test failed")

    @router.post("/admin/image-storage-test")
    async def admin_image_storage_test(request: Request):
        # This test is admin-only and does not invoke Replicate or image generation.
        if admin_check is None:
            raise HTTPException(status_code=503, detail="Image storage test is unavailable")
        try:
            admin = admin_check(request)
            if inspect.isawaitable(admin):
                await admin
            provider = getattr(gateway, "image_provider", None)
            storage = getattr(provider, "storage", None)
            verifier = getattr(storage, "verify_public_round_trip", None)
            if not callable(verifier):
                raise HTTPException(status_code=503, detail="R2 storage is not configured")
            result = verifier()
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict) or result.get("status") != "ok":
                raise RuntimeError("R2 storage verification did not complete")
            return result
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=502, detail="R2 public storage verification failed")

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
