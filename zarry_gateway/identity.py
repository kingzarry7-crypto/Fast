"""Fail-closed identity boundaries; legacy mappings are not verified links."""
from dataclasses import dataclass
from typing import Optional
@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject_id: str
    platform: str
    platform_user_id: str
    shared_memory_enabled: bool = False
    def __post_init__(self):
        if self.platform not in {"web", "telegram", "discord"}:
            raise ValueError("Unsupported client platform")
        if not self.subject_id or not self.platform_user_id:
            raise ValueError("Principal identifiers must be non-empty")
class IdentityResolver:
    def __init__(self, verified_link_lookup=None):
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
        return AuthenticatedPrincipal(subject_id=str(linked_subject) if linked_subject else f"{platform}:{external_id}", platform=platform, platform_user_id=external_id, shared_memory_enabled=False)
