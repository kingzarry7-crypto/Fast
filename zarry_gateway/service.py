"""Orchestration for authenticated ZARRY general-assistant text requests."""
from __future__ import annotations

from uuid import UUID, uuid4
import os

from .identity import AuthenticatedPrincipal
from .providers import SelfHostedZarryProvider
from .schemas import AssistantRequest


class AssistantService:
    """ZARRY-first text service with explicit opt-in conversation memory."""

    def __init__(self, text_provider=None, memory_store=None, image_provider=None, image_storage=None):
        self.text_provider = text_provider or SelfHostedZarryProvider()
        self.memory_store = memory_store
        self.image_provider = image_provider
        self.image_storage = image_storage or getattr(image_provider, "storage", None)
        if self.image_storage is None:
            required = ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
                        "R2_BUCKET", "R2_PUBLIC_BASE_URL")
            if all(os.getenv(name, "").strip() for name in required):
                from .image_storage import CloudflareR2ImageStorage
                try:
                    self.image_storage = CloudflareR2ImageStorage(
                        bucket=os.environ["R2_BUCKET"],
                        public_base_url=os.environ["R2_PUBLIC_BASE_URL"],
                    )
                except Exception:
                    # Keep the service available; the admin diagnostic reports
                    # storage as unavailable without leaking configuration details.
                    self.image_storage = None

    def image(self, *, principal: AuthenticatedPrincipal, payload):
        if not isinstance(principal, AuthenticatedPrincipal):
            raise PermissionError("An authenticated principal is required")
        if self.image_provider is None:
            raise RuntimeError("Image generation is unavailable")
        width, height = (int(value) for value in payload.size.split("x", 1))
        result = self.image_provider.generate(
            payload.prompt,
            request_id=payload.request_id,
            width=width,
            height=height,
        )
        if not isinstance(result, dict):
            raise RuntimeError("Image provider returned an invalid result")
        # Provider diagnostics such as budget_reserved_usd are for the
        # admin-only smoke test, not part of the strict public image contract.
        public_fields = ("request_id", "image_url", "provider", "fallback_used")
        return {key: result[key] for key in public_fields if key in result}

    def chat(self, *, principal: AuthenticatedPrincipal, payload: AssistantRequest) -> dict:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise PermissionError("An authenticated principal is required")
        request_id = payload.request_id if isinstance(payload.request_id, UUID) else UUID(str(payload.request_id))
        conversation_id = payload.conversation_id or uuid4()
        messages = []
        memory_enabled = bool(
            self.memory_store is not None and self.memory_store.is_enabled(principal)
        )
        if memory_enabled:
            messages.extend(self.memory_store.get_history(principal, conversation_id, limit=12))
        messages.append({"role": "user", "content": payload.message})
        if len(messages) > 20:
            messages = messages[-20:]
        answer = self.text_provider.generate(
            message=payload.message,
            request_id=request_id,
            messages=messages,
        )
        if memory_enabled:
            self.memory_store.append_turn(
                principal=principal,
                conversation_id=conversation_id,
                user_message=payload.message,
                assistant_message=answer,
            )
        return {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "response": answer,
            "provider": self.text_provider.name,
            "fallback_used": False,
        }
