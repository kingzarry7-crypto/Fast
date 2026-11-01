"""Server-side adapters for the isolated ZARRY general-chat service."""
from __future__ import annotations

import os
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID

import requests


class TextProvider(Protocol):
    name: str

    def generate(self, *, message: str, request_id: UUID, timeout: tuple[float, float]) -> str: ...


def _normalise_chat_messages(messages, fallback_message: str) -> list[dict[str, str]]:
    """Keep the private service contract to user/assistant turns while preserving trusted app context."""
    system_context = []
    turns = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if role == "system":
            system_context.append(content.strip())
        elif role in {"user", "assistant"}:
            turns.append({"role": role, "content": content.strip()[:8000]})

    if not turns:
        turns = [{"role": "user", "content": str(fallback_message or "").strip()[:8000]}]
    if turns[-1]["role"] != "user":
        turns.append({"role": "user", "content": str(fallback_message or "").strip()[:8000]})

    if system_context:
        last_user = next((item for item in reversed(turns) if item["role"] == "user"), None)
        if last_user is not None:
            prefix = "[Trusted application context]\n" + "\n\n".join(system_context)
            room = max(0, 8000 - len(last_user["content"]) - 2)
            if room:
                last_user["content"] = (prefix[:room] + "\n\n" + last_user["content"])[:8000]

    turns = turns[-20:]
    while len(turns) > 1 and sum(len(item["content"]) for item in turns) > 24000:
        turns.pop(0)
    return turns


class SelfHostedZarryProvider:
    """Calls the dedicated general-chat contract, never the trading explain route."""

    name = "self-hosted-zarry"

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 timeout: tuple[float, float] = (5.0, 180.0), session=None):
        if base_url is not None:
            selected_base_url = base_url
        else:
            private_service_url = os.getenv("ZARRY_PRIVATE_SERVICE_URL", "").strip()
            configured_service_url = os.getenv("ZARRY_SERVICE_URL", "").strip()
            configured_host = (urlsplit(configured_service_url).hostname or "").lower()
            if private_service_url:
                selected_base_url = private_service_url
            elif configured_host == "zarry-production.up.railway.app":
                # This Railway project exposes the ZARRY service privately as zarry.
                # Prefer service-to-service traffic over the public Railway hostname.
                selected_base_url = "http://zarry.railway.internal:8080"
            else:
                selected_base_url = configured_service_url
        self.base_url = selected_base_url.strip().rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("ZARRY_API_KEY", "")
        self.timeout = timeout
        self.session = session or requests

    def generate(self, *, message: str, request_id: UUID, messages=None, timeout=None) -> str:
        parsed_url = urlsplit(self.base_url)
        host = (parsed_url.hostname or "").lower()
        secure_public_url = parsed_url.scheme == "https" and bool(host)
        railway_private_url = (
            parsed_url.scheme == "http"
            and host.endswith(".railway.internal")
            and bool(host)
        )
        if not (secure_public_url or railway_private_url) or parsed_url.username or parsed_url.password or not self.api_key:
            raise RuntimeError("ZARRY text provider is not configured")
        bounded_messages = _normalise_chat_messages(messages, message)
        if not 1 <= len(bounded_messages) <= 20:
            raise ValueError("Conversation history is outside the supported bounds")
        response = self.session.post(
            self.base_url + "/v1/chat",
            json={"request_id": str(request_id), "messages": bounded_messages},
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
