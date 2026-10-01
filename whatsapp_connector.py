"""
KING ZARRY AI — official WhatsApp Cloud API connector.

Credentials are read only from environment variables. Never put tokens in chat,
source code, or the database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request
from typing import Any, Dict


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def status() -> Dict[str, Any]:
    configured = bool(_env("WHATSAPP_ACCESS_TOKEN") and _env("WHATSAPP_PHONE_NUMBER_ID"))
    return {
        "configured": configured,
        "provider": "meta_whatsapp_cloud_api",
        "phone_number_id_configured": bool(_env("WHATSAPP_PHONE_NUMBER_ID")),
        "access_token_configured": bool(_env("WHATSAPP_ACCESS_TOKEN")),
        "graph_version": _env("WHATSAPP_GRAPH_VERSION") or "v25.0",
        "graph_version_configured": True,
        "webhook_verify_configured": bool(_env("WHATSAPP_VERIFY_TOKEN")),
        "app_secret_configured": bool(_env("WHATSAPP_APP_SECRET")),
        "note": "Uses Meta WhatsApp Cloud API; outbound messages are approval-gated by the Agent.",
    }


def send_text(to: str, text: str) -> Dict[str, Any]:
    token = _env("WHATSAPP_ACCESS_TOKEN")
    phone_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    version = _env("WHATSAPP_GRAPH_VERSION") or "v25.0"
    if not token or not phone_id:
        raise RuntimeError(
            "WhatsApp connector is not configured. Set WHATSAPP_ACCESS_TOKEN, "
            "WHATSAPP_PHONE_NUMBER_ID, and WHATSAPP_GRAPH_VERSION in Railway."
        )
    recipient = "".join(ch for ch in str(to or "") if ch.isdigit())
    if not recipient or len(recipient) < 8:
        raise ValueError("WhatsApp recipient must be an international phone number")
    body = str(text or "").strip()
    if not body:
        raise ValueError("WhatsApp message cannot be empty")
    if len(body) > 4096:
        body = body[:4096]

    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://graph.facebook.com/{version}/{phone_id}/messages",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8") or "{}")
    except Exception as exc:
        raise RuntimeError(f"WhatsApp send failed: {type(exc).__name__}") from exc

    messages = data.get("messages") or []
    return {
        "status": "sent" if messages else "accepted",
        "message_id": (messages[0].get("id") if messages else None),
        "recipient": recipient,
        "provider": "meta_whatsapp_cloud_api",
    }


def verify_webhook_challenge(mode: str, token: str, challenge: str) -> str | None:
    expected = _env("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and expected and hmac.compare_digest(token or "", expected):
        return str(challenge or "")
    return None


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    app_secret = _env("WHATSAPP_APP_SECRET")
    if not app_secret:
        return False
    signature = (signature_header or "").strip()
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected}")
