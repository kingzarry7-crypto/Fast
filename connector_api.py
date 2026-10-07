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
import secrets
import time
import urllib.parse
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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
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
        if payload.get("provider") != "github":
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


@router.get("/status")
async def connector_status(request: Request):
    user_id = _user_id(request)
    account = _github_account(user_id)
    return {
        "github": {
            "configured": _github_configured(),
            "connected": bool(account),
            "account": account,
            "authorization_mode": "oauth",
        }
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
    payload = _verify_state(request.query_params.get("state") or "")
    user_id = _user_id(request)
    if str(payload.get("user_id")) != user_id:
        raise HTTPException(status_code=403, detail="Connector authorization belongs to a different KZ session")
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
