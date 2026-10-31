"""Default-off policy switches for general assistant capabilities."""
from __future__ import annotations
import os


def enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def general_gateway_enabled() -> bool:
    return enabled("ZARRY_GENERAL_ENABLED", False)


def shared_memory_enabled() -> bool:
    return enabled("ZARRY_SHARED_MEMORY_ENABLED", False)
