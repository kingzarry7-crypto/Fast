"""Secure cTrader Open API OAuth foundation for King Zarry AI.

Demo-only connection flow. This module deliberately does not submit orders.
Trading must remain disabled until account environment, symbol mapping, and risk
controls have been validated against the connected cTrader demo account.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api/ctrader", tags=["cTrader"])
STATE_TTL_SECONDS = 600


def _config():
    client_id = os.getenv("CTRADER_CLIENT_ID", "").strip()
    client_secret = os.getenv("CTRADER_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv(
        "CTRADER_REDIRECT_URI",
        "https://fast-production-0eba.up.railway.app/api/ctrader/callback",
    ).strip()
    state_secret = os.getenv("CTRADER_STATE_SECRET", "").strip() or client_secret
    return client_id, client_secret, redirect_uri, state_secret


def _sign_state(payload: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_state(state: str, secret: str) -> bool:
    try:
        payload, signature = state.rsplit(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        user_id, issued = payload.split(":", 1)
        age = int(time.time()) - int(issued)
        return bool(user_id) and 0 <= age <= STATE_TTL_SECONDS and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


@router.get("/status")
async def ctrader_status(request: Request):
    """Connection readiness only; never claims an account is connected without tokens."""
    user_row = request.app.state.ctrader_require_current_user(request)
    client_id, client_secret, redirect_uri, _ = _config()
    return {
        "provider": "cTrader Open API",
        "configured": bool(client_id and client_secret and redirect_uri),
        "connected": False,
        "environment": "demo_only",
        "automated_orders_enabled": False,
        "message": "OAuth connection storage and demo-account verification must complete before trading can be enabled.",
    }


@router.get("/connect")
async def ctrader_connect(request: Request):
    user_row = request.app.state.ctrader_require_current_user(request)
    client_id, client_secret, redirect_uri, state_secret = _config()
    if not client_id or not client_secret or not state_secret:
        raise HTTPException(status_code=503, detail="cTrader credentials are not configured on the backend.")
    user_id = str(user_row.get("id") if isinstance(user_row, dict) else user_row[0])
    state = _sign_state(f"{user_id}:{int(time.time())}", state_secret)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "trading",
        "product": " cTrader",
        "state": state,
    }
    return RedirectResponse("https://id.ctrader.com/my/settings/openapi/grantingaccess/?" + urlencode(params))


@router.get("/callback")
async def ctrader_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    # OAuth callback is public by design; signed state prevents forged callbacks.
    client_id, client_secret, redirect_uri, state_secret = _config()
    if error:
        raise HTTPException(status_code=400, detail="cTrader authorization was declined.")
    if not code or not state or not client_id or not client_secret or not state_secret:
        raise HTTPException(status_code=400, detail="Missing cTrader authorization parameters.")
    if not _verify_state(state, state_secret):
        raise HTTPException(status_code=400, detail="Invalid or expired cTrader authorization state.")
    try:
        response = requests.get(
            "https://openapi.ctrader.com/apps/token",
            params={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not exchange the cTrader authorization code.") from exc
    # Do not return access/refresh tokens to the browser or logs. Persistence is
    # intentionally not enabled until encrypted token storage is configured.
    if not payload.get("accessToken") or not payload.get("refreshToken"):
        raise HTTPException(status_code=502, detail="cTrader returned an incomplete token response.")
    raise HTTPException(
        status_code=503,
        detail="Authorization succeeded, but secure encrypted token storage is not configured. Trading remains disabled.",
    )
