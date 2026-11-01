"""Safe, non-persistent startup connectivity check for the Fast-to-ZARRY path."""
from __future__ import annotations

import logging
import time
from uuid import uuid4

logger = logging.getLogger(__name__)


def run_general_gateway_smoke(provider) -> str:
    """Exercise the configured provider without touching user memory or logging secrets."""
    if not getattr(provider, "base_url", "") or not getattr(provider, "api_key", ""):
        logger.info("ZARRY_GENERAL_GATEWAY_SMOKE status=skipped reason=provider_not_configured")
        return "skipped"

    started = time.monotonic()
    try:
        answer = provider.generate(
            message="Reply with exactly: ZARRY_CONNECTION_OK.",
            request_id=uuid4(),
            timeout=(5.0, 180.0),
        )
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("ZARRY provider returned an empty startup response")
        latency_ms = max(0, round((time.monotonic() - started) * 1000))
        logger.info(
            "ZARRY_GENERAL_GATEWAY_SMOKE status=passed provider=%s latency_ms=%d",
            getattr(provider, "name", "unknown"),
            latency_ms,
        )
        return "passed"
    except Exception as exc:
        # Never log exception messages: requests errors can include URL/header details.
        logger.error(
            "ZARRY_GENERAL_GATEWAY_SMOKE status=failed error_type=%s",
            type(exc).__name__,
        )
        return "failed"
