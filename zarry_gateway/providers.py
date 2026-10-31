"""Server-side adapters for the isolated ZARRY general-chat service."""
from __future__ import annotations

import os
from typing import Protocol
from uuid import UUID

import requests


class TextProvider(Protocol):
    name: str

    def generate(self, *, message: str, request_id: UUID, timeout: tuple[float, float]) -> str: ...


class SelfHostedZarryProvider:
    """Calls the dedicated general-chat contract, never the trading explain route."""

    name = "self-hosted-zarry"

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout: tuple[float, float] = (5.0, 90.0), session=None):
        self.base_url = (base_url if base_url is not None else os.getenv("ZARRY_SERVICE_URL", "")).strip().rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("ZARRY_API_KEY", "")
        self.timeout = timeout
        self.session = session or requests

    def generate(self, *, message: str, request_id: UUID, timeout=None) -> str:
        if not self.base_url.startswith("https://") or not self.api_key:
            raise RuntimeError("ZARRY text provider is not configured")
        response = self.session.post(
            self.base_url + "/v1/chat",
            json={"request_id": str(request_id), "messages": [{"role": "user", "content": message}]},
            headers={"Authorization": "Bearer " + self.api_key},
            timeout=timeout or self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("request_id") != str(request_id):
            raise RuntimeError("ZARRY provider returned a mismatched request ID")
        answer = data.get("response")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("ZARRY provider returned an empty response")
        return answer.strip()
