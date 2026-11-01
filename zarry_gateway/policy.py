"""Default-off policy switches for general assistant capabilities."""
import os


def enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def general_gateway_enabled() -> bool:
    return enabled("ZARRY_GENERAL_ENABLED", False)


def shared_memory_enabled() -> bool:
    return enabled("ZARRY_SHARED_MEMORY_ENABLED", False)


def image_generation_enabled() -> bool:
    # Two independent gates are required. The operator must explicitly enable
    # image generation AND record approval after the one-time live smoke test.
    # This keeps production fail-closed if the older enable flag is already set.
    return (
        enabled("ZARRY_IMAGE_ENABLED", False)
        and enabled("ZARRY_IMAGE_LIVE_SMOKE_APPROVED", False)
    )
