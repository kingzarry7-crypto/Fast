"""Run a deployment smoke test against a live ZARRY service.

Usage:
  ZARRY_SERVICE_URL=https://... ZARRY_API_KEY=... python smoke_test.py

The script never submits a trade; it sends a synthetic WAIT assessment.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import requests


def main() -> int:
    base_url = os.getenv("ZARRY_SERVICE_URL", "").strip().rstrip("/")
    api_key = os.getenv("ZARRY_API_KEY", "").strip()
    if not base_url.startswith("https://") or not api_key:
        print("Set HTTPS ZARRY_SERVICE_URL and ZARRY_API_KEY", file=sys.stderr)
        return 2

    timeout = (5, 30)
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
        "context": {"rsi_14": 50.0, "timeframe": "1h", "status": "synthetic smoke test"},
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
    print("ZARRY deployment smoke test passed: root, health, readiness, auth rejection, and WAIT preservation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
