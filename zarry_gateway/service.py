"""Orchestration for authenticated ZARRY general-assistant text requests."""
from __future__ import annotations

from uuid import UUID, uuid4

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

    def image(self, *, principal: AuthenticatedPrincipal, payload):
        if not isinstance(principal, AuthenticatedPrincipal):
            raise PermissionError("An authenticated principal is required")
        if self.image_provider is None:
            raise RuntimeError("Image generation is unavailable")
        width, height = (int(value) for value in payload.size.split("x", 1))
        return self.image_provider.generate(
            payload.prompt,
            request_id=payload.request_id,
            width=width,
            height=height,
        )

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
