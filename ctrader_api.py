"""cTrader Open API OAuth and demo-account verification for King Zarry AI.

No order-submission endpoint is exposed. Trading stays disabled until separate
risk, symbol, model-contract, and demo execution tests have been reviewed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from database import get_db_cursor
from connector_api import _connector_user_id, _encrypt, _decrypt, _row_value

router = APIRouter(prefix="/api/ctrader", tags=["cTrader"])
STATE_TTL_SECONDS = 600
AUTH_URL = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
TOKEN_URL = "https://openapi.ctrader.com/apps/token"
ACCOUNTS_URL = "https://openapi.ctrader.com/apps/accounts"


def _config():
    return (
        os.getenv("CTRADER_CLIENT_ID", "").strip(),
        os.getenv("CTRADER_CLIENT_SECRET", "").strip(),
        os.getenv("CTRADER_REDIRECT_URI", "https://fast-production-0eba.up.railway.app/api/ctrader/callback").strip(),
        (os.getenv("CTRADER_STATE_SECRET", "").strip() or os.getenv("CONNECTOR_STATE_SECRET", "").strip()),
    )


def _sign_state(user_id: str, secret: str) -> str:
    payload = json.dumps({"uid": user_id, "iat": int(time.time()), "provider": "ctrader"}, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return encoded + "." + signature


def _verify_state(state: str, secret: str) -> str:
    import base64
    try:
        encoded, signature = state.rsplit(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        age = int(time.time()) - int(payload["iat"])
        if payload.get("provider") != "ctrader" or not payload.get("uid") or age < 0 or age > STATE_TTL_SECONDS:
            raise ValueError()
        return str(payload["uid"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired cTrader authorization state") from exc


def _connection(user_id: str):
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT provider_account_id, display_name, scopes, access_token_encrypted,
                      refresh_token_encrypted, token_expires_at, metadata
               FROM web_connected_accounts
               WHERE user_id=%s AND provider='ctrader' AND revoked_at IS NULL
               ORDER BY updated_at DESC LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "account_id": str(_row_value(row, "provider_account_id", 0) or ""),
        "display_name": str(_row_value(row, "display_name", 1) or "cTrader"),
        "scopes": _row_value(row, "scopes", 2) or [],
        "access_token": _decrypt(_row_value(row, "access_token_encrypted", 3)),
        "refresh_token": _decrypt(_row_value(row, "refresh_token_encrypted", 4)),
        "expires_at": _row_value(row, "token_expires_at", 5),
        "metadata": _row_value(row, "metadata", 6) or {},
    }


def _save_connection(user_id: str, token_data: dict, account: dict):
    account_id = str(account.get("accountId") or account.get("account_id") or "")
    if not account_id:
        raise HTTPException(status_code=502, detail="cTrader returned no account ID")
    expires_in = int(token_data.get("expiresIn") or token_data.get("expires_in") or 0)
    expires_at = datetime.fromtimestamp(time.time() + expires_in, timezone.utc) if expires_in > 0 else None
    scopes = token_data.get("scope") or "trading"
    if isinstance(scopes, str):
        scopes = scopes.split()
    metadata = {
        "environment": str(account.get("environment") or account.get("accountType") or "").lower(),
        "broker_title": str(account.get("brokerTitle") or account.get("brokerName") or ""),
        "trader_login": str(account.get("traderLogin") or ""),
        "demo_verified": True,
    }
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO web_connected_accounts
              (user_id, provider, provider_account_id, display_name, scopes,
               access_token_encrypted, refresh_token_encrypted, token_expires_at, metadata, revoked_at)
              VALUES (%s, 'ctrader', %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, NULL)
              ON CONFLICT (user_id, provider, provider_account_id)
              DO UPDATE SET display_name=EXCLUDED.display_name, scopes=EXCLUDED.scopes,
                access_token_encrypted=EXCLUDED.access_token_encrypted,
                refresh_token_encrypted=EXCLUDED.refresh_token_encrypted,
                token_expires_at=EXCLUDED.token_expires_at, metadata=EXCLUDED.metadata,
                revoked_at=NULL, updated_at=NOW()""",
            (user_id, account_id, "cTrader " + account_id, json.dumps(scopes),
             _encrypt(token_data.get("accessToken")), _encrypt(token_data.get("refreshToken")),
             expires_at, json.dumps(metadata)),
        )


@router.get("/status")
async def ctrader_status(request: Request):
    user_id = _connector_user_id(request)
    client_id, client_secret, redirect_uri, state_secret = _config()
    connection = _connection(user_id)
    metadata = connection["metadata"] if connection else {}
    return {
        "provider": "cTrader Open API",
        "configured": bool(client_id and client_secret and redirect_uri and len(state_secret) >= 32),
        "connected": bool(connection),
        "account_id": connection["account_id"] if connection else None,
        "environment": metadata.get("environment") if connection else None,
        "demo_verified": bool(metadata.get("demo_verified")) if connection else False,
        "automated_orders_enabled": False,
        "message": "Connection is read-only; automated orders are disabled.",
    }


@router.get("/connect")
async def ctrader_connect(request: Request):
    user_id = _connector_user_id(request)
    client_id, client_secret, redirect_uri, state_secret = _config()
    if not client_id or not client_secret or len(state_secret) < 32:
        raise HTTPException(status_code=503, detail="Set cTrader credentials and a 32+ character CONNECTOR_STATE_SECRET in Railway.")
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": "trading", "product": "web", "state": _sign_state(user_id, state_secret)}
    return RedirectResponse(AUTH_URL + "?" + urlencode(params))


@router.get("/callback")
async def ctrader_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    client_id, client_secret, redirect_uri, state_secret = _config()
    if error:
        raise HTTPException(status_code=400, detail="cTrader authorization was declined.")
    if not code or not state or not client_id or not client_secret or len(state_secret) < 32:
        raise HTTPException(status_code=400, detail="Missing cTrader authorization parameters.")
    user_id = _verify_state(state, state_secret)
    try:
        token_response = requests.get(TOKEN_URL, params={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": client_id, "client_secret": client_secret,
        }, timeout=20)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = str(token_data.get("accessToken") or "")
        if not access_token:
            raise ValueError("No access token")
        accounts_response = requests.get(ACCOUNTS_URL, params={"accessToken": access_token}, timeout=20)
        accounts_response.raise_for_status()
        accounts_payload = accounts_response.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="cTrader authorization or account lookup failed; tokens were not returned to the browser.") from exc

    accounts = accounts_payload.get("data") or accounts_payload.get("accounts") or []
    if isinstance(accounts_payload, list):
        accounts = accounts_payload
    if not isinstance(accounts, list) or not accounts:
        raise HTTPException(status_code=422, detail="cTrader authorization succeeded, but no accessible account was returned.")
    # Fail closed: only save a single explicitly demo account. Never silently
    # select a live account when the API response's environment is ambiguous.
    demo_accounts = [a for a in accounts if isinstance(a, dict) and (
        str(a.get("environment") or "").lower() == "demo"
        or str(a.get("accountType") or "").lower() == "demo"
    )]
    if len(demo_accounts) != 1:
        raise HTTPException(status_code=422, detail="Could not uniquely verify one cTrader demo account. No account was saved; trading remains disabled.")
    _save_connection(user_id, token_data, demo_accounts[0])
    return RedirectResponse("https://fast.kingzarry7.workers.dev/?connector=ctrader&status=connected", status_code=303)


@router.post("/disconnect")
async def ctrader_disconnect(request: Request):
    user_id = _connector_user_id(request)
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_connected_accounts SET revoked_at=NOW(), updated_at=NOW() WHERE user_id=%s AND provider='ctrader' AND revoked_at IS NULL", (user_id,))
    return {"success": True, "provider": "ctrader", "automated_orders_enabled": False}
