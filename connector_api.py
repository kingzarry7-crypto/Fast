"""KZ official connector layer.

Provider-authorized accounts are the preferred path for supported services.
Browser sessions remain available as a fallback for sites without an official
connector, but they are not treated as the connector itself.

Secrets are encrypted at rest with a server-side key and are never returned
to the frontend, workflow goals, memory, or audit details.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from nacl.secret import SecretBox

from database import get_db_cursor


router = APIRouter(prefix="/api/connectors", tags=["connectors"])

GITHUB_AUTHORIZE = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://fast.kingzarry7.workers.dev").rstrip("/")
CONNECTOR_STATE_SECRET = os.getenv("CONNECTOR_STATE_SECRET") or os.getenv("SESSION_SECRET") or ""
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "").strip()
GITHUB_SCOPES = os.getenv("GITHUB_OAUTH_SCOPES", "read:user repo").strip()


def _now() -> int:
    return int(time.time())


def _require_state_secret() -> bytes:
    secret = CONNECTOR_STATE_SECRET.strip()
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="KZ connector security is not configured. Set CONNECTOR_STATE_SECRET (32+ characters).",
        )
    return secret.encode("utf-8")


def _token_box() -> SecretBox:
    # SecretBox requires exactly 32 bytes. Hashing the configured secret gives
    # a stable encryption key without storing another key in the database.
    raw = os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY", "").strip()
    if len(raw) < 32:
        raise HTTPException(
            status_code=503,
            detail="KZ connector encryption is not configured. Set KZ_CONNECTOR_ENCRYPTION_KEY (32+ characters).",
        )
    key = hashlib.sha256(raw.encode("utf-8")).digest()
    return SecretBox(key)


def _encrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    box = _token_box()
    encrypted = box.encrypt(str(value).encode("utf-8"))
    return base64.urlsafe_b64encode(bytes(encrypted)).decode("ascii")


def _decrypt(value: Optional[str]) -> str:
    if not value:
        return ""
    box = _token_box()
    raw = base64.urlsafe_b64decode(str(value).encode("ascii"))
    return box.decrypt(raw).decode("utf-8")


def _sign_state(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(_require_state_secret(), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def _verify_state(value: str) -> Dict[str, Any]:
    try:
        encoded, sig = str(value or "").split(".", 1)
        expected = hmac.new(_require_state_secret(), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp") or 0) < _now():
            raise ValueError("expired")
        if payload.get("provider") not in {"github", "tiktok", "shopify"}:
            raise ValueError("wrong provider")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired connector authorization state") from exc


def _row_value(row: Any, key: str, index: int = 0) -> Any:
    if row is None:
        return None
    try:
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
    except Exception:
        pass
    try:
        return row[index]
    except Exception:
        return None


def _user_id(request: Request) -> str:
    # api.py exposes the authenticated-user helper; importing it here would
    # create a circular import, so resolve it only when the endpoint runs.
    import api
    row = api._require_current_user(request)
    return str(api._row_value(row, "id", 0))


def _github_configured() -> bool:
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET and GITHUB_REDIRECT_URI and CONNECTOR_STATE_SECRET)


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "King-Zarry-AI-Connector/1.0",
    }


def _github_request(method: str, path: str, token: str, **kwargs: Any) -> requests.Response:
    url = GITHUB_API.rstrip("/") + "/" + path.lstrip("/")
    response = requests.request(method, url, headers=_github_headers(token), timeout=25, **kwargs)
    if response.status_code >= 400:
        detail = "GitHub connector request failed"
        try:
            body = response.json()
            detail = str(body.get("message") or detail)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail[:500])
    return response


def _github_account(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, provider, provider_account_id, display_name, scopes,
                   token_expires_at, metadata
            FROM web_connected_accounts
            WHERE user_id = %s AND provider = 'github' AND revoked_at IS NULL
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(_row_value(row, "id", 0)),
        "provider": str(_row_value(row, "provider", 1) or "github"),
        "provider_account_id": str(_row_value(row, "provider_account_id", 2) or ""),
        "display_name": str(_row_value(row, "display_name", 3) or "GitHub"),
        "scopes": _row_value(row, "scopes", 4) or [],
        "token_expires_at": str(_row_value(row, "token_expires_at", 5) or "") or None,
        "metadata": _row_value(row, "metadata", 6) or {},
    }


def _github_token(user_id: str) -> str:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT access_token_encrypted
            FROM web_connected_accounts
            WHERE user_id = %s AND provider = 'github' AND revoked_at IS NULL
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
    token = _decrypt(_row_value(row, "access_token_encrypted", 0) if row else None)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub is not connected")
    return token


def _save_github_connection(
    user_id: str,
    github_user: Dict[str, Any],
    access_token: str,
    refresh_token: Optional[str],
    expires_in: Optional[int],
    scopes: list[str],
) -> None:
    expires_at = None
    if expires_in:
        expires_at = datetime.fromtimestamp(_now() + int(expires_in), timezone.utc)
    metadata = {
        "login": github_user.get("login"),
        "avatar_url": github_user.get("avatar_url"),
        "html_url": github_user.get("html_url"),
    }
    expires_at = None
    if expires_in:
        expires_at = datetime.fromtimestamp(_now() + int(expires_in), timezone.utc)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_connected_accounts
              (user_id, provider, provider_account_id, display_name, scopes,
               access_token_encrypted, refresh_token_encrypted, token_expires_at, metadata, revoked_at)
            VALUES (%s, 'github', %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, NULL)
            ON CONFLICT (user_id, provider, provider_account_id)
            DO UPDATE SET
              display_name = EXCLUDED.display_name,
              scopes = EXCLUDED.scopes,
              access_token_encrypted = EXCLUDED.access_token_encrypted,
              refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
              token_expires_at = EXCLUDED.token_expires_at,
              metadata = EXCLUDED.metadata,
              revoked_at = NULL,
              updated_at = NOW()
            """,
            (
                user_id,
                str(github_user.get("id") or github_user.get("login") or ""),
                str(github_user.get("login") or "GitHub"),
                json.dumps(scopes),
                _encrypt(access_token),
                _encrypt(refresh_token),
                expires_at,
                json.dumps(metadata),
            ),
        )


def _audit(user_id: str, event: str, operation: str = "", target: str = "", approval_id: Optional[str] = None) -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_audit_logs (user_id, event, service, tool_name, approval_id, details)
            VALUES (%s, %s, 'github', 'github_connector', %s, %s::jsonb)
            """,
            (user_id, event, approval_id, json.dumps({"operation": operation, "target": target[:500]})),
        )


def _action_fingerprint(service: str, operation: str, target: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {"service": service, "operation": operation, "target": target, "payload": payload},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _github_execute(user_id: str, operation: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = _github_token(user_id)
    operation = str(operation or "").strip().lower()

    if operation == "list_repositories":
        response = _github_request("GET", "/user/repos?sort=updated&per_page=50", token)
        repos = response.json()
        return {
            "verified": True,
            "operation": operation,
            "repositories": [
                {"name": x.get("name"), "full_name": x.get("full_name"), "private": bool(x.get("private")), "url": x.get("html_url")}
                for x in repos
            ],
        }

    if operation == "get_repository":
        owner = str(payload.get("owner") or "").strip()
        repo = str(payload.get("repo") or "").strip()
        if not owner or not repo:
            raise HTTPException(status_code=400, detail="owner and repo are required")
        response = _github_request("GET", f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}", token)
        x = response.json()
        return {"verified": True, "operation": operation, "repository": {
            "full_name": x.get("full_name"), "private": bool(x.get("private")),
            "default_branch": x.get("default_branch"), "url": x.get("html_url"),
        }}

    if operation == "create_issue":
        owner = str(payload.get("owner") or "").strip()
        repo = str(payload.get("repo") or "").strip()
        title = str(payload.get("title") or "").strip()[:300]
        body = str(payload.get("body") or "")[:10000]
        if not owner or not repo or not title:
            raise HTTPException(status_code=400, detail="owner, repo and title are required")
        response = _github_request(
            "POST", f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/issues",
            token, json={"title": title, "body": body},
        )
        x = response.json()
        return {"verified": bool(x.get("html_url") and x.get("number")), "operation": operation,
                "issue": {"number": x.get("number"), "title": x.get("title"), "url": x.get("html_url"), "state": x.get("state")}}

    if operation == "create_file":
        owner = str(payload.get("owner") or "").strip()
        repo = str(payload.get("repo") or "").strip()
        path = str(payload.get("path") or "").strip().lstrip("/")
        content = str(payload.get("content") or "")
        message = str(payload.get("message") or "").strip()[:300]
        branch = str(payload.get("branch") or "").strip()
        if not owner or not repo or not path or not content or not message:
            raise HTTPException(status_code=400, detail="owner, repo, path, content and message are required")
        body = {"message": message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii")}
        if branch:
            body["branch"] = branch
        response = _github_request(
            "PUT", f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/contents/{urllib.parse.quote(path, safe='/')}",
            token, json=body,
        )
        x = response.json()
        return {"verified": bool(x.get("content", {}).get("html_url") or x.get("commit", {}).get("sha")),
                "operation": operation,
                "file": {"path": path, "url": x.get("content", {}).get("html_url"), "commit_sha": x.get("commit", {}).get("sha")}}

    raise HTTPException(status_code=400, detail=f"Unsupported GitHub operation: {operation}")



# ---------------------------------------------------------------------------
# Shopify official Admin API connector (OAuth 2.0).
# ---------------------------------------------------------------------------
SHOPIFY_AUTHORIZE = "https://{shop}/admin/oauth/authorize"
SHOPIFY_TOKEN = "https://{shop}/admin/oauth/access_token"
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07").strip()
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "").strip()
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "").strip()
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI", "").strip()
SHOPIFY_SCOPES = os.getenv(
    "SHOPIFY_OAUTH_SCOPES",
    "read_products,write_products,read_orders,write_inventory",
).strip()

def _shopify_configured() -> bool:
    return bool(SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET and SHOPIFY_REDIRECT_URI and CONNECTOR_STATE_SECRET)

def _shopify_store(value: str) -> str:
    store = str(value or "").strip().lower()
    store = re.sub(r"^https?://", "", store).split("/", 1)[0]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", store):
        raise HTTPException(status_code=400, detail="Use your Shopify store domain, for example your-store.myshopify.com")
    return store

def _shopify_headers(token: str) -> Dict[str, str]:
    return {"X-Shopify-Access-Token": token, "Content-Type": "application/json", "Accept": "application/json"}

def _shopify_request(store: str, token: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"https://{store}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    response = requests.post(url, headers=_shopify_headers(token), json={"query": query, "variables": variables or {}}, timeout=25)
    try:
        body = response.json()
    except Exception:
        body = {}
    if response.status_code >= 400 or body.get("errors"):
        raise HTTPException(status_code=502, detail="Shopify API request failed")
    return body

def _save_shopify_connection(user_id: str, store: str, token: str, refresh_token: Optional[str], expires_in: Optional[int], scopes: list[str], shop: Dict[str, Any]) -> None:
    expires_at = None
    if expires_in:
        expires_at = datetime.fromtimestamp(_now() + int(expires_in), timezone.utc)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_connected_accounts
              (user_id, provider, provider_account_id, display_name, scopes,
               access_token_encrypted, refresh_token_encrypted, token_expires_at, metadata, revoked_at)
            VALUES (%s, 'shopify', %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, NULL)
            ON CONFLICT (user_id, provider, provider_account_id)
            DO UPDATE SET
              display_name = EXCLUDED.display_name,
              scopes = EXCLUDED.scopes,
              access_token_encrypted = EXCLUDED.access_token_encrypted,
              refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
              token_expires_at = EXCLUDED.token_expires_at,
              metadata = EXCLUDED.metadata,
              revoked_at = NULL,
              updated_at = NOW()
            """,
            (
                user_id, store, str(shop.get("name") or store), json.dumps(scopes),
                _encrypt(token), _encrypt(refresh_token), expires_at, json.dumps({"store": store, "shop": shop}),
            ),
        )

def _shopify_token(user_id: str, store: str = "") -> tuple[str, str]:
    with get_db_cursor(commit=False) as cur:
        if store:
            cur.execute(
                "SELECT provider_account_id, access_token_encrypted FROM web_connected_accounts WHERE user_id=%s AND provider='shopify' AND provider_account_id=%s AND revoked_at IS NULL LIMIT 1",
                (user_id, store),
            )
        else:
            cur.execute(
                "SELECT provider_account_id, access_token_encrypted FROM web_connected_accounts WHERE user_id=%s AND provider='shopify' AND revoked_at IS NULL ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            )
        row=cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Shopify is not connected")
    store_name=str(_row_value(row, "provider_account_id", 0) or "")
    token=_decrypt(_row_value(row, "access_token_encrypted", 1))
    if not store_name or not token:
        raise HTTPException(status_code=401, detail="Shopify connection is incomplete")
    return store_name, token

@router.get("/shopify/start")
async def shopify_start(request: Request, shop: str):
    user_id = _user_id(request)
    if not _shopify_configured():
        raise HTTPException(status_code=503, detail="Shopify connector is not configured on KZ")
    store = _shopify_store(shop)
    state = _sign_state({"provider":"shopify","user_id":user_id,"store":store,"nonce":secrets.token_urlsafe(18),"exp":_now()+600})
    params={"client_id":SHOPIFY_CLIENT_ID,"scope":SHOPIFY_SCOPES,"redirect_uri":SHOPIFY_REDIRECT_URI,"state":state}
    return RedirectResponse(SHOPIFY_AUTHORIZE.format(shop=store)+"?"+urllib.parse.urlencode(params))

@router.get("/shopify/callback")
async def shopify_callback(request: Request):
    # Return OAuth failures to the dashboard instead of leaving the user with no response.
    if not _shopify_configured():
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error=shopify_not_configured")
    error=request.query_params.get("error")
    if error:
        detail=request.query_params.get("error_description") or error
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error=shopify_{urllib.parse.quote(str(detail)[:300])}")
    try:
        payload=_verify_state(request.query_params.get("state") or "")
        if payload.get("provider")!="shopify":
            raise HTTPException(status_code=400, detail="Invalid Shopify connector state")
        user_id=str(payload.get("user_id") or "").strip()
        store=_shopify_store(str(payload.get("store") or ""))
        code=request.query_params.get("code") or ""
        if not code:
            raise HTTPException(status_code=400, detail="Shopify authorization code missing")

        # Validate Shopify's callback HMAC before exchanging the one-time code.
        supplied_hmac=str(request.query_params.get("hmac") or "")
        if not supplied_hmac:
            raise HTTPException(status_code=400, detail="Shopify callback HMAC missing")
        pairs=[(key,value) for key,value in request.query_params.multi_items() if key!="hmac"]
        pairs.sort()
        message=urllib.parse.urlencode(pairs)
        expected_hmac=hmac.new(SHOPIFY_CLIENT_SECRET.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied_hmac, expected_hmac):
            raise HTTPException(status_code=400, detail="Shopify callback HMAC validation failed")

        response=requests.post(
            SHOPIFY_TOKEN.format(shop=store),
            data={"client_id":SHOPIFY_CLIENT_ID,"client_secret":SHOPIFY_CLIENT_SECRET,"code":code,"expiring":"1"},
            headers={"Accept":"application/json","Content-Type":"application/x-www-form-urlencoded"},
            timeout=25,
        )
        if response.status_code>=400:
            detail="Shopify token exchange failed"
            try:
                body=response.json()
                detail=str(body.get("error_description") or body.get("error") or detail)
            except Exception:
                pass
            raise HTTPException(status_code=502, detail=detail[:300])
        data=response.json()
        token=str(data.get("access_token") or "")
        if not token:
            raise HTTPException(status_code=502, detail="Shopify did not return an access token")
        scopes=[x.strip() for x in str(data.get("scope") or SHOPIFY_SCOPES).split(",") if x.strip()]
        body=_shopify_request(store, token, "query { shop { id name myshopifyDomain } }")
        shop_data=((body.get("data") or {}).get("shop") or {})
        _save_shopify_connection(user_id,store,token,data.get("refresh_token"),data.get("expires_in"),scopes,shop_data)
        _audit(user_id,"connector_connected",target=store)
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector=shopify&connected=1&name={urllib.parse.quote(str(shop_data.get('name') or store))}")
    except HTTPException as exc:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error=shopify_{urllib.parse.quote(str(exc.detail or 'authorization_failed')[:300])}")
    except Exception as exc:
        logger.exception("Shopify callback failed: %s", type(exc).__name__)
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error=shopify_callback_failed")

@router.post("/shopify/action")
async def shopify_action(request: Request):
    user_id=_user_id(request)
    body=await request.json()
    operation=str((body or {}).get("operation") or "").strip().lower()
    payload=dict((body or {}).get("payload") or {})
    store,token=_shopify_token(user_id,str(payload.get("shop") or ""))
    if operation=="shop":
        result=_shopify_request(store,token,"query { shop { id name myshopifyDomain } }")
    elif operation=="products":
        result=_shopify_request(store,token,"query { products(first: 20) { nodes { id title status handle } } }")
    elif operation=="orders":
        result=_shopify_request(store,token,"query { orders(first: 20, sortKey: CREATED_AT, reverse: true) { nodes { id name createdAt displayFinancialStatus displayFulfillmentStatus } } }")
    else:
        raise HTTPException(status_code=400, detail="Unsupported Shopify read operation")
    return {"status":"ok","provider":"shopify","operation":operation,"store":store,"verified":True,"result":result.get("data") or {}}

@router.get("/status")
async def connector_status(request: Request):
    user_id = _user_id(request)
    account = _github_account(user_id)
    tiktok_account = _provider_account(user_id, "tiktok")
    return {
        "shopify": {
            "configured": _shopify_configured(),
            "connected": bool(_provider_account(user_id, "shopify")),
            "account": _provider_account(user_id, "shopify"),
            "authorization_mode": "oauth",
        },
        "github": {
            "configured": _github_configured(),
            "connected": bool(account),
            "account": account,
            "authorization_mode": "oauth",
        },
        "tiktok": {
            "configured": _tiktok_configured(),
            "connected": bool(tiktok_account),
            "account": tiktok_account,
            "authorization_mode": "oauth_qr",
        },
    }


def _provider_account(user_id: str, provider: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, provider, provider_account_id, display_name, scopes,
                   token_expires_at, metadata
            FROM web_connected_accounts
            WHERE user_id = %s AND provider = %s AND revoked_at IS NULL
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id, provider),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(_row_value(row, "id", 0)),
        "provider": str(_row_value(row, "provider", 1) or provider),
        "provider_account_id": str(_row_value(row, "provider_account_id", 2) or ""),
        "display_name": str(_row_value(row, "display_name", 3) or provider),
        "scopes": _row_value(row, "scopes", 4) or [],
        "token_expires_at": str(_row_value(row, "token_expires_at", 5) or "") or None,
        "metadata": _row_value(row, "metadata", 6) or {},
    }

@router.get("/accounts")
async def connector_accounts(request: Request):
    user_id = _user_id(request)
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT provider, provider_account_id, display_name, scopes, token_expires_at, metadata
            FROM web_connected_accounts
            WHERE user_id = %s AND revoked_at IS NULL
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []
    return {
        "accounts": [
            {
                "provider": str(_row_value(x, "provider", 0)),
                "provider_account_id": str(_row_value(x, "provider_account_id", 1) or ""),
                "display_name": str(_row_value(x, "display_name", 2) or ""),
                "scopes": _row_value(x, "scopes", 3) or [],
                "token_expires_at": str(_row_value(x, "token_expires_at", 4) or "") or None,
                "metadata": _row_value(x, "metadata", 5) or {},
            }
            for x in rows
        ]
    }


@router.get("/github/start")
async def github_start(request: Request):
    user_id = _user_id(request)
    if not _github_configured():
        raise HTTPException(status_code=503, detail="GitHub connector is not configured on KZ")
    state = _sign_state({"provider": "github", "user_id": user_id, "nonce": secrets.token_urlsafe(18), "exp": _now() + 600})
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": GITHUB_SCOPES,
        "state": state,
    }
    return RedirectResponse(GITHUB_AUTHORIZE + "?" + urllib.parse.urlencode(params))


@router.get("/github/callback")
async def github_callback(request: Request):
    if not _github_configured():
        raise HTTPException(status_code=503, detail="GitHub connector is not configured on KZ")
    error = request.query_params.get("error")
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error={urllib.parse.quote(error)}")
    # OAuth returns directly to Railway, while the login cookie may live on
    # the Vercel frontend host behind the /api proxy. The signed, short-lived
    # state already binds this authorization request to the logged-in KZ user,
    # so do not require the frontend cookie on the provider callback host.
    payload = _verify_state(request.query_params.get("state") or "")
    user_id = str(payload.get("user_id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=403, detail="Connector authorization state has no KZ user")
    code = request.query_params.get("code") or ""
    if not code:
        raise HTTPException(status_code=400, detail="GitHub authorization code missing")
    response = requests.post(
        GITHUB_TOKEN,
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI,
        },
        headers={"Accept": "application/json", "User-Agent": "King-Zarry-AI-Connector/1.0"},
        timeout=25,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="GitHub token exchange failed")
    token_data = response.json()
    access_token = str(token_data.get("access_token") or "")
    if not access_token:
        raise HTTPException(status_code=502, detail="GitHub did not return an access token")
    me = _github_request("GET", "/user", access_token).json()
    _save_github_connection(
        user_id,
        me,
        access_token,
        token_data.get("refresh_token"),
        token_data.get("expires_in"),
        [x for x in str(token_data.get("scope") or GITHUB_SCOPES).replace(",", " ").split() if x],
    )
    _audit(user_id, "connector_connected", target=str(me.get("login") or "github"))
    return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector=github&connected=1")



# ---------------------------------------------------------------------------
# TikTok official connector (OAuth 2.0 + QR authorization)
# ---------------------------------------------------------------------------
TIKTOK_AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_QR_CREATE = "https://open.tiktokapis.com/v2/oauth/get_qrcode/"
TIKTOK_QR_CHECK = "https://open.tiktokapis.com/v2/oauth/check_qrcode/"
TIKTOK_USER_INFO = "https://open.tiktokapis.com/v2/user/info/"
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "").strip()
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "").strip()
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "").strip()
TIKTOK_SCOPES = os.getenv("TIKTOK_OAUTH_SCOPES", "user.info.basic").strip()
_TIKTOK_QR_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _tiktok_configured() -> bool:
    return bool(TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET and TIKTOK_REDIRECT_URI and CONNECTOR_STATE_SECRET)


def _tiktok_save_connection(
    user_id: str,
    open_id: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_in: Optional[int],
    scopes: list[str],
    profile: Optional[Dict[str, Any]] = None,
) -> None:
    profile = profile or {}
    expires_at = None
    if expires_in:
        expires_at = datetime.fromtimestamp(_now() + int(expires_in), timezone.utc)
    metadata = {
        "open_id": open_id,
        "display_name": profile.get("display_name"),
        "avatar_url": profile.get("avatar_url"),
    }
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_connected_accounts
              (user_id, provider, provider_account_id, display_name, scopes,
               access_token_encrypted, refresh_token_encrypted, token_expires_at, metadata, revoked_at)
            VALUES (%s, 'tiktok', %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, NULL)
            ON CONFLICT (user_id, provider, provider_account_id)
            DO UPDATE SET
              display_name = EXCLUDED.display_name,
              scopes = EXCLUDED.scopes,
              access_token_encrypted = EXCLUDED.access_token_encrypted,
              refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
              token_expires_at = EXCLUDED.token_expires_at,
              metadata = EXCLUDED.metadata,
              revoked_at = NULL,
              updated_at = NOW()
            """,
            (
                user_id, open_id, str(profile.get("display_name") or "TikTok"),
                json.dumps(scopes), _encrypt(access_token), _encrypt(refresh_token),
                expires_at, json.dumps(metadata),
            ),
        )


def _tiktok_profile(access_token: str) -> Dict[str, Any]:
    response = requests.get(
        TIKTOK_USER_INFO,
        params={"fields": "open_id,union_id,avatar_url,display_name"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=25,
    )
    if response.status_code >= 400:
        return {}
    body = response.json()
    return body.get("data") or {}


def _tiktok_exchange(code: str, user_id: str) -> Dict[str, Any]:
    response = requests.post(
        TIKTOK_TOKEN,
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TIKTOK_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        timeout=25,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("error_description") or response.json().get("error")
        except Exception:
            detail = None
        raise HTTPException(status_code=502, detail=f"TikTok token exchange failed{': ' + str(detail) if detail else ''}")
    token_data = response.json()
    access_token = str(token_data.get("access_token") or "")
    open_id = str(token_data.get("open_id") or "")
    if not access_token or not open_id:
        raise HTTPException(status_code=502, detail="TikTok did not return an access token and open_id")
    profile = _tiktok_profile(access_token)
    scopes = [x.strip() for x in str(token_data.get("scope") or TIKTOK_SCOPES).replace(" ", ",").split(",") if x.strip()]
    _tiktok_save_connection(user_id, open_id, access_token, token_data.get("refresh_token"), token_data.get("expires_in"), scopes, profile)
    _audit(user_id, "connector_connected", target=str(profile.get("display_name") or open_id))
    return {"open_id": open_id, "display_name": profile.get("display_name"), "scopes": scopes}


@router.get("/tiktok/start")
async def tiktok_start(request: Request):
    user_id = _user_id(request)
    if not _tiktok_configured():
        raise HTTPException(status_code=503, detail="TikTok connector is not configured on KZ")
    state = _sign_state({"provider": "tiktok", "user_id": user_id, "nonce": secrets.token_urlsafe(18), "exp": _now() + 600})
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": TIKTOK_SCOPES,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
    }
    return RedirectResponse(TIKTOK_AUTHORIZE + "?" + urllib.parse.urlencode(params))


@router.get("/tiktok/callback")
async def tiktok_callback(request: Request):
    if not _tiktok_configured():
        raise HTTPException(status_code=503, detail="TikTok connector is not configured on KZ")
    error = request.query_params.get("error")
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector_error=tiktok_{urllib.parse.quote(error)}")
    payload = _verify_state(request.query_params.get("state") or "")
    if payload.get("provider") != "tiktok":
        raise HTTPException(status_code=400, detail="Invalid TikTok connector state")
    user_id = _user_id(request)
    if str(payload.get("user_id")) != user_id:
        raise HTTPException(status_code=403, detail="TikTok authorization belongs to a different KZ session")
    code = request.query_params.get("code") or ""
    if not code:
        raise HTTPException(status_code=400, detail="TikTok authorization code missing")
    result = _tiktok_exchange(code, user_id)
    return RedirectResponse(f"{FRONTEND_URL}/dashboard?connector=tiktok&connected=1&name={urllib.parse.quote(str(result.get('display_name') or 'TikTok'))}")


@router.post("/tiktok/qr/start")
async def tiktok_qr_start(request: Request):
    user_id = _user_id(request)
    if not _tiktok_configured():
        raise HTTPException(status_code=503, detail="TikTok connector is not configured on KZ")
    client_ticket = secrets.token_urlsafe(18)
    state = _sign_state({"provider": "tiktok", "user_id": user_id, "nonce": secrets.token_urlsafe(18), "exp": _now() + 600})
    response = requests.post(
        TIKTOK_QR_CREATE,
        data={"client_key": TIKTOK_CLIENT_KEY, "scope": TIKTOK_SCOPES, "state": state},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=25,
    )
    body = response.json()
    if response.status_code >= 400 or body.get("error"):
        raise HTTPException(status_code=502, detail=str(body.get("error_description") or body.get("error") or "TikTok QR creation failed"))
    scan_url = str(body.get("scan_qrcode_url") or "")
    token = str(body.get("token") or "")
    if not scan_url or not token:
        raise HTTPException(status_code=502, detail="TikTok did not return a QR authorization URL")
    parsed = urllib.parse.urlsplit(scan_url)
    query = urllib.parse.parse_qs(parsed.query)
    query["client_ticket"] = [client_ticket]
    scan_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query, doseq=True), parsed.fragment))
    session_id = secrets.token_urlsafe(24)
    _TIKTOK_QR_SESSIONS[session_id] = {
        "user_id": user_id, "token": token, "client_ticket": client_ticket,
        "created_at": _now(), "state": state,
    }
    return {"status": "pending", "session_id": session_id, "scan_qrcode_url": scan_url, "expires_in": 600}


@router.post("/tiktok/qr/status")
async def tiktok_qr_status(request: Request):
    user_id = _user_id(request)
    body = await request.json()
    session_id = str(body.get("session_id") or "").strip()
    session = _TIKTOK_QR_SESSIONS.get(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="TikTok QR session not found or expired")
    if _now() - int(session.get("created_at") or 0) > 600:
        _TIKTOK_QR_SESSIONS.pop(session_id, None)
        return {"status": "expired"}
    response = requests.post(
        TIKTOK_QR_CHECK,
        data={"client_key": TIKTOK_CLIENT_KEY, "client_secret": TIKTOK_CLIENT_SECRET, "token": session["token"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=25,
    )
    data = response.json()
    if response.status_code >= 400 or data.get("error"):
        raise HTTPException(status_code=502, detail=str(data.get("error_description") or data.get("error") or "TikTok QR status check failed"))
    status = str(data.get("status") or "new")
    if status == "confirmed":
        returned_ticket = str(data.get("client_ticket") or "")
        if returned_ticket != str(session.get("client_ticket") or ""):
            raise HTTPException(status_code=502, detail="TikTok QR integrity check failed")
        redirect_uri = str(data.get("redirect_uri") or "")
        parsed = urllib.parse.urlparse(redirect_uri)
        code = urllib.parse.parse_qs(parsed.query).get("code", [""])[0]
        if not code:
            raise HTTPException(status_code=502, detail="TikTok confirmed the QR code but returned no authorization code")
        result = _tiktok_exchange(code, user_id)
        _TIKTOK_QR_SESSIONS.pop(session_id, None)
        return {"status": "connected", "connected": True, "account": result}
    if status == "expired":
        _TIKTOK_QR_SESSIONS.pop(session_id, None)
    return {"status": status, "connected": False}

@router.post("/github/disconnect")
async def github_disconnect(request: Request):
    user_id = _user_id(request)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE web_connected_accounts
            SET revoked_at = NOW(), updated_at = NOW()
            WHERE user_id = %s AND provider = 'github' AND revoked_at IS NULL
            """,
            (user_id,),
        )
    _audit(user_id, "connector_disconnected")
    return {"success": True, "provider": "github"}


@router.post("/github/action")
async def github_action(request: Request):
    user_id = _user_id(request)
    body = await request.json()
    operation = str(body.get("operation") or "").strip().lower()
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}

    read_ops = {"list_repositories", "get_repository"}
    if operation in read_ops:
        return {"status": "completed", "result": _github_execute(user_id, operation, payload)}

    if operation not in {"create_issue", "create_file"}:
        raise HTTPException(status_code=400, detail="Unsupported or unsafe GitHub operation")

    target = f"{payload.get('owner','')}/{payload.get('repo','')}"
    fingerprint = _action_fingerprint("github", operation, target, payload)
    approval_id = str(uuid.uuid4())
    exact_content = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_approvals
              (id, user_id, service, operation, target, exact_content, action_fingerprint, status)
            VALUES (%s, %s, 'github', %s, %s, %s, %s, 'pending')
            RETURNING id
            """,
            (approval_id, user_id, operation, target[:500], exact_content, fingerprint),
        )
        row = cur.fetchone()
        approval_id = str(_row_value(row, "id", 0) or approval_id)
    _audit(user_id, "connector_action_approval_created", operation, target, approval_id)
    return {
        "status": "waiting_for_approval",
        "approval_id": approval_id,
        "provider": "github",
        "operation": operation,
        "target": target,
        "preview": payload,
        "message": "Approval required. KZ will execute only this exact GitHub action after you approve it.",
    }


@router.post("/github/approve/{approval_id}")
async def github_approve(approval_id: str, request: Request):
    user_id = _user_id(request)
    body = await request.json()
    approved = bool(body.get("approved"))
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, operation, target, exact_content, action_fingerprint, status
            FROM web_approvals
            WHERE id = %s AND user_id = %s AND service = 'github'
            LIMIT 1
            """,
            (approval_id, user_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    status = str(_row_value(row, "status", 5) or "")
    if status != "pending":
        raise HTTPException(status_code=409, detail=f"Approval is already {status}")
    operation = str(_row_value(row, "operation", 1) or "")
    target = str(_row_value(row, "target", 2) or "")
    exact_content = str(_row_value(row, "exact_content", 3) or "{}")
    fingerprint = str(_row_value(row, "action_fingerprint", 4) or "")
    payload = json.loads(exact_content)
    if _action_fingerprint("github", operation, target, payload) != fingerprint:
        raise HTTPException(status_code=409, detail="Approval fingerprint mismatch; action was not executed")
    if not approved:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE web_approvals SET status='rejected', rejected_at=NOW() WHERE id=%s AND status='pending'",
                (approval_id,),
            )
        _audit(user_id, "connector_action_rejected", operation, target, approval_id)
        return {"status": "rejected", "approval_id": approval_id}

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE web_approvals SET status='approved', approved_at=NOW() WHERE id=%s AND status='pending'",
            (approval_id,),
        )
    try:
        result = _github_execute(user_id, operation, payload)
    except Exception:
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_approvals SET status='expired' WHERE id=%s AND status='approved'", (approval_id,))
        raise

    verified = bool(result.get("verified"))
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE web_approvals
            SET status=%s, executed_at=NOW()
            WHERE id=%s AND status='approved'
            """,
            ("executed" if verified else "expired", approval_id),
        )
    _audit(user_id, "connector_action_verified" if verified else "connector_action_unverified", operation, target, approval_id)
    if not verified:
        raise HTTPException(status_code=502, detail="GitHub accepted the request but KZ could not verify the resulting resource")
    return {"status": "completed", "verified": True, "approval_id": approval_id, "result": result}
