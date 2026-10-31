"""Fail-closed identity boundaries for web, Telegram, and Discord principals.

Existing platform identity rows are not proof of a verified account link. Until an
explicit authenticated linking flow exists, each platform identity remains isolated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject_id: str
    platform: str
    platform_user_id: str
    shared_memory_enabled: bool = False

    def __post_init__(self) -> None:
        if self.platform not in {"web", "telegram", "discord"}:
            raise ValueError("Unsupported client platform")
        if not self.subject_id or not self.platform_user_id:
            raise ValueError("Principal identifiers must be non-empty")


class IdentityResolver:
    """Resolve a stable platform-scoped subject; never infer cross-platform links."""

    def __init__(self, verified_link_lookup=None):
        # Deliberately ignore legacy identity tables unless a future verified-link
        # store/flow is supplied. No display-name or username matching is allowed.
        self._verified_link_lookup = verified_link_lookup

    def resolve(self, platform: str, platform_user_id: str) -> AuthenticatedPrincipal:
        platform = str(platform).strip().lower()
        external_id = str(platform_user_id).strip()
        if platform not in {"web", "telegram", "discord"}:
            raise ValueError("Unsupported client platform")
        if not external_id or len(external_id) > 256:
            raise ValueError("Invalid platform user identifier")
        linked_subject: Optional[str] = None
        if self._verified_link_lookup is not None:
            linked_subject = self._verified_link_lookup(platform, external_id)
        if linked_subject:
            return AuthenticatedPrincipal(
                subject_id=str(linked_subject), platform=platform,
                platform_user_id=external_id, shared_memory_enabled=False,
            )
        return AuthenticatedPrincipal(
            subject_id=f"{platform}:{external_id}", platform=platform,
            platform_user_id=external_id, shared_memory_enabled=False,
        )
