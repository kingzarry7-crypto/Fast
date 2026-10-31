"""Authenticated FastAPI routes for the general-assistant gateway."""
import inspect
import logging
import time
from fastapi import APIRouter, HTTPException, Request
from .identity import AuthenticatedPrincipal
from .policy import general_gateway_enabled, image_generation_enabled
from .schemas import (
    AssistantRequest, AssistantResponse, ImageRequest, ImageResponse,
    MemoryPreferenceRequest,
)

logger = logging.getLogger(__name__)


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
            storage = getattr(gateway, "image_storage", None) or getattr(provider, "storage", None)
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
        except Exception as exc:
            # Keep the client response generic; log only the exception class so
            # operators can distinguish SDK/network failures without exposing
            # credentials, request headers, or provider error messages.
            logger.error("R2 public storage verification failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=502, detail="R2 public storage verification failed")

    @router.post("/admin/image-generation-smoke-test")
    async def admin_image_generation_smoke_test(request: Request):
        # Admin authorization always happens before the persistent one-use claim.
        if admin_check is None:
            raise HTTPException(status_code=503, detail="Image smoke test is unavailable")
        try:
            admin = admin_check(request)
            if inspect.isawaitable(admin):
                await admin
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=403, detail="Admin access denied")

        from database import get_db_cursor
        from uuid import uuid4
        from urllib.parse import urlsplit
        import requests

        request_uuid = uuid4()
        request_id = str(request_uuid)
        claimed = False

        def record_outcome(status, provider_name=None, image_url=None, error_type=None):
            # The lock row is the durable audit record; never store credentials or prompts.
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    UPDATE zarry_image_smoke_test_lock
                    SET status = %s, request_id = %s, provider = %s,
                        image_url = %s, error_type = %s,
                        completed_at = CASE WHEN %s IN ('succeeded', 'failed')
                                            THEN NOW() ELSE completed_at END
                    WHERE lock_key = 'replicate-one-shot-v1'
                    """,
                    (status, request_id, provider_name, image_url, error_type, status),
                )

        try:
            # The table is provisioned by the explicit, checksum-tracked
            # migration runner; runtime requests never need schema privileges.
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO zarry_image_smoke_test_lock (lock_key, status, request_id)
                    VALUES ('replicate-one-shot-v1', 'claimed', %s)
                    ON CONFLICT (lock_key) DO NOTHING
                    RETURNING lock_key
                """, (request_id,))
                claimed = cur.fetchone() is not None
            if not claimed:
                raise HTTPException(status_code=409, detail="The one-time image test has already been used")

            provider = getattr(gateway, "image_provider", None)
            storage = getattr(gateway, "image_storage", None) or getattr(provider, "storage", None)
            if provider is None or storage is None:
                raise RuntimeError("Image generation and storage are not configured")

            record_outcome("running")
            result = provider.generate(
                "A simple photorealistic studio photograph of a single ripe orange on a clean neutral background.",
                request_id=request_uuid, width=1024, height=1024,
            )
            image_url = result.get("image_url") if isinstance(result, dict) else None
            parsed = urlsplit(str(image_url or ""))
            expected_host = str(getattr(storage, "public_host", "") or "").lower()
            if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() != expected_host:
                raise RuntimeError("Generated image URL did not match the configured public storage host")
            response = requests.get(image_url, timeout=20)
            response.raise_for_status()
            if not response.content.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
                raise RuntimeError("Generated object was not a PNG")

            provider_name = str(result.get("provider", "replicate-z-image-turbo"))
            record_outcome("succeeded", provider_name=provider_name, image_url=image_url)
            return {
                "status": "ok",
                "request_id": request_id,
                "provider": provider_name,
                "image_url": image_url,
                "public_retrieval": "verified",
                "public_generation_enabled": False,
                "budget_reservation_usd": "0.01",
            }
        except HTTPException:
            raise
        except Exception as exc:
            if claimed:
                try:
                    record_outcome("failed", error_type=type(exc).__name__)
                except Exception as audit_exc:
                    logger.error("One-shot image audit update failed (%s)", type(audit_exc).__name__)
            logger.error("One-shot image generation smoke test failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=502, detail="One-time image generation test failed; lock remains consumed")

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
