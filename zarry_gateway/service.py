"""Orchestration for authenticated ZARRY general-assistant text requests."""
from __future__ import annotations

from uuid import UUID, uuid4

from .identity import AuthenticatedPrincipal
from .providers import SelfHostedZarryProvider
from .schemas import AssistantRequest


class AssistantService:
    """ZARRY-first text service.

    Fallback is intentionally absent until provider allow-listing and bounded
    pricing have been verified. Provider errors therefore fail closed.
    """

    def __init__(self, text_provider=None):
        self.text_provider = text_provider or SelfHostedZarryProvider()

    def chat(self, *, principal: AuthenticatedPrincipal, payload: AssistantRequest) -> dict:
        if not isinstance(principal, AuthenticatedPrincipal):
            raise PermissionError("An authenticated principal is required")
        request_id = payload.request_id if isinstance(payload.request_id, UUID) else UUID(str(payload.request_id))
        answer = self.text_provider.generate(
            message=payload.message,
            request_id=request_id,
        )
        return {
            "request_id": request_id,
            "conversation_id": payload.conversation_id or uuid4(),
            "response": answer,
            "provider": self.text_provider.name,
            "fallback_used": False,
        }
