"""Run an authenticated deployment smoke test against a live ZARRY service.

Usage:
  ZARRY_SERVICE_URL=https://... ZARRY_API_KEY=... python smoke_test.py

The script never submits a trade; it sends a synthetic WAIT assessment.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests


def is_allowed_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def main() -> int:
    base_url = os.getenv("ZARRY_SERVICE_URL", "").strip().rstrip("/")
    api_key = os.getenv("ZARRY_API_KEY", "").strip()
    if not is_allowed_base_url(base_url) or not api_key:
        print("Set HTTPS ZARRY_SERVICE_URL (or HTTP loopback only) and ZARRY_API_KEY", file=sys.stderr)
        return 2

    timeout = (5, 45)
    root = requests.get(base_url + "/", timeout=timeout)
    root.raise_for_status()
    root_data = root.json()
    if root_data.get("service") != "ZARRY" or root_data.get("mode") != "explanation_only":
        raise RuntimeError("ZARRY smoke test failed: root status contract is invalid")

    health = requests.get(base_url + "/health", timeout=timeout)
    health.raise_for_status()
    ready = requests.get(base_url + "/ready", timeout=timeout)
    ready.raise_for_status()
    if ready.json().get("model_loaded") is not True:
        raise RuntimeError("ZARRY smoke test failed: readiness did not confirm model loaded")

    payload = {
        "symbol": "BTCUSD",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": {
            "trend_4h": "bullish",
            "direction_1h": "bearish",
            "setup_15m": "mixed",
            "entry_5m": "not_confirmed",
            "last_price": 68000,
            "data_fresh": True,
        },
        "expected_fields": [
            "trend_4h",
            "direction_1h",
            "setup_15m",
            "entry_5m",
            "data_fresh",
        ],
        "kitty_assessment": {"decision": "WAIT", "reason_codes": ["deployment_smoke_test"]},
        "task": "explain",
    }
    rejected = requests.post(base_url + "/v1/explain", json=payload, timeout=timeout)
    if rejected.status_code != 401:
        raise RuntimeError("ZARRY smoke test failed: unauthenticated request was not rejected")

    response = requests.post(
        base_url + "/v1/explain",
        json=payload,
        headers={"Authorization": "Bearer " + api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("symbol") != "BTCUSD" or result.get("decision") != "WAIT":
        raise RuntimeError("ZARRY smoke test failed: symbol/decision changed")
    if result.get("authority") != "KITTY_DETERMINISTIC_ENGINE":
        raise RuntimeError("ZARRY smoke test failed: authority marker missing")
    if result.get("mode") != "explanation_only":
        raise RuntimeError("ZARRY smoke test failed: explanation-only marker missing")
    if result.get("explanation_source") != "model":
        raise RuntimeError("ZARRY smoke test failed: Qwen did not generate the explanation")
    if result.get("cited_fields") != payload["expected_fields"]:
        raise RuntimeError("ZARRY smoke test failed: expected citations were not preserved")
    if result.get("numeric_claims") != []:
        raise RuntimeError("ZARRY smoke test failed: numeric claims were returned")
    print("ZARRY authenticated Qwen smoke test passed: health, readiness, auth rejection, Kitty WAIT, citations, explanation-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
