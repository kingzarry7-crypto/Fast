"""KZ official Google Workspace connector.

Uses Google's server-side OAuth flow and encrypted tokens stored in the existing
web_connected_accounts table. Consequential actions require an exact approval
record before execution and are marked successful only when Google returns
verifiable evidence.

Supported:
- Gmail: list recent messages, send email (approval required)
- Drive: list/search files, upload a text file (approval required)
- Calendar: list upcoming events, create event (approval required)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from nacl.secret import SecretBox

from database import get_db_cursor


router = APIRouter(prefix="/api/connectors/google", tags=["google-connector"])
logger = logging.getLogger("king_zarry_google_connector")

GOOGLE_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_GMAIL = "https://gmail.googleapis.com/gmail/v1"
GOOGLE_DRIVE = "https://www.googleapis.com/drive/v3"
GOOGLE_CALENDAR = "https://www.googleapis.com/calendar/v3"

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://fast.kingzarry7.workers.dev").rstrip("/")
# Keep OAuth return handling aligned with the Cloudflare production domain.
FRONTEND_CUSTOM_DOMAIN = "kingzarry.bid"
FRONTEND_CUSTOM_ORIGINS = {
    "https://kingzarry.bid",
    "https://www.kingzarry.bid",
    "https://app.kingzarry.bid",
}
CONNECTOR_STATE_SECRET = os.getenv("CONNECTOR_STATE_SECRET") or os.getenv("SESSION_SECRET") or ""
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = (
    os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    or "https://fast-production-0eba.up.railway.app/api/connectors/google/callback"
)

DEFAULT_GOOGLE_SCOPES = " ".join([
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
])
GOOGLE_SCOPES = os.getenv("GOOGLE_OAUTH_SCOPES", DEFAULT_GOOGLE_SCOPES).strip()


def _connector_user_id(request: Request) -> str:
    """Resolve the logged-in KZ web user from the same session cookie as /api/auth/me.

    OAuth start endpoints must use the authenticated web session. Do not accept
    a user id from query/body parameters because that would let one account
    start an OAuth flow for another account.
    """
    raw_token = request.cookies.get("king_zarry_web_session")
    if not raw_token or len(raw_token) > 500:
        raise HTTPException(status_code=401, detail="Authentication required")
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT s.user_id
               FROM web_sessions s
               JOIN web_users u ON u.id = s.user_id
               WHERE s.token_hash = %s
                 AND s.revoked_at IS NULL
                 AND s.expires_at > NOW()
                 AND u.account_status = 'active'
               LIMIT 1""",
            (token_hash,),
        )
        row = cur.fetchone()
    user_id = str(_row_value(row, "user_id", 0) or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


def _now() -> int:
    return int(time.time())


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


def _is_allowed_frontend_origin(value: str) -> bool:
    origin = str(value or "").strip().rstrip("/")
    if not origin:
        return False
    if origin in {
        FRONTEND_URL,
        "https://fast-a84x.vercel.app",
        "https://fast.kingzarry7.workers.dev",
        *FRONTEND_CUSTOM_ORIGINS,
    }:
        return True
    try:
        parsed = urllib.parse.urlparse(origin)
        return parsed.scheme == "https" and (
            parsed.hostname == FRONTEND_CUSTOM_DOMAIN
            or bool(parsed.hostname and parsed.hostname.endswith("." + FRONTEND_CUSTOM_DOMAIN))
        ) and not parsed.path and not parsed.params and not parsed.query and not parsed.fragment
    except Exception:
        return False


def _oauth_return_url(request: Request) -> str:
    """Return OAuth to the exact trusted frontend host that started the flow."""
    configured = FRONTEND_URL
    raw = (request.headers.get("origin") or "").strip().rstrip("/")
    if not raw:
        try:
            parsed = urllib.parse.urlparse(request.headers.get("referer") or "")
            raw = f"{parsed.scheme}://{parsed.netloc}".rstrip("/") if parsed.scheme and parsed.netloc else ""
        except Exception:
            raw = ""
    return raw if _is_allowed_frontend_origin(raw) else configured


def _state_return_url(payload: Dict[str, Any]) -> str:
    value = str(payload.get("return_url") or "").strip().rstrip("/")
    return value if _is_allowed_frontend_origin(value) else FRONTEND_URL


def _configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI and CONNECTOR_STATE_SECRET)


def _box() -> SecretBox:
    raw = os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY", "").strip()
    if len(raw) < 32:
        raise HTTPException(status_code=503, detail="KZ connector encryption is not configured")
    return SecretBox(hashlib.sha256(raw.encode("utf-8")).digest())


def _encrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return base64.urlsafe_b64encode(bytes(_box().encrypt(str(value).encode("utf-8")))).decode("ascii")


def _decrypt(value: Optional[str]) -> str:
    if not value:
        return ""
    return _box().decrypt(base64.urlsafe_b64decode(str(value).encode("ascii"))).decode("utf-8")


def _sign_state(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(CONNECTOR_STATE_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def _verify_state(value: str) -> Dict[str, Any]:
    try:
        encoded, sig = str(value or "").split(".", 1)
        expected = hmac.new(CONNECTOR_STATE_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("signature")
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if payload.get("provider") != "google" or int(payload.get("exp") or 0) < _now():
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired Google authorization state") from exc


def _account(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT id, provider_account_id, display_name, scopes, token_expires_at, metadata,
                      access_token_encrypted, refresh_token_encrypted
               FROM web_connected_accounts
               WHERE user_id=%s AND provider='google' AND revoked_at IS NULL
               ORDER BY updated_at DESC LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(_row_value(row, "id", 0)),
        "provider": "google",
        "provider_account_id": str(_row_value(row, "provider_account_id", 1) or ""),
        "display_name": str(_row_value(row, "display_name", 2) or "Google"),
        "scopes": _row_value(row, "scopes", 3) or [],
        "token_expires_at": str(_row_value(row, "token_expires_at", 4) or "") or None,
        "metadata": _row_value(row, "metadata", 5) or {},
        "_access": _row_value(row, "access_token_encrypted", 6),
        "_refresh": _row_value(row, "refresh_token_encrypted", 7),
    }


def _save_account(user_id: str, profile: Dict[str, Any], token: Dict[str, Any], scopes: list[str]) -> None:
    expires_at = None
    if token.get("expires_in"):
        expires_at = datetime.fromtimestamp(_now() + int(token["expires_in"]), timezone.utc)
    account_id = str(profile.get("sub") or "")
    if not account_id:
        raise HTTPException(status_code=502, detail="Google did not return a stable account identifier")
    metadata = {
        "email": profile.get("email"),
        "email_verified": bool(profile.get("email_verified")),
        "picture": profile.get("picture"),
        "name": profile.get("name"),
    }
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO web_connected_accounts
              (user_id, provider, provider_account_id, display_name, scopes,
               access_token_encrypted, refresh_token_encrypted, token_expires_at, metadata, revoked_at)
              VALUES (%s,'google',%s,%s,%s::jsonb,%s,%s,%s,%s::jsonb,NULL)
              ON CONFLICT (user_id, provider, provider_account_id)
              DO UPDATE SET display_name=EXCLUDED.display_name,
                scopes=EXCLUDED.scopes,
                access_token_encrypted=EXCLUDED.access_token_encrypted,
                refresh_token_encrypted=COALESCE(EXCLUDED.refresh_token_encrypted,
                                                 web_connected_accounts.refresh_token_encrypted),
                token_expires_at=EXCLUDED.token_expires_at,
                metadata=EXCLUDED.metadata,
                revoked_at=NULL, updated_at=NOW()""",
            (
                user_id, account_id, str(profile.get("name") or profile.get("email") or "Google"),
                json.dumps(scopes), _encrypt(token.get("access_token")),
                _encrypt(token.get("refresh_token")), expires_at, json.dumps(metadata),
            ),
        )


def _refresh(user_id: str, account: Dict[str, Any]) -> str:
    refresh_token = _decrypt(account.get("_refresh"))
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Google authorization expired. Reconnect Google.")
    response = requests.post(
        GOOGLE_TOKEN,
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=25,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="Google authorization expired. Reconnect Google.")
    token = response.json()
    access_token = str(token.get("access_token") or "")
    if not access_token:
        raise HTTPException(status_code=401, detail="Google did not return a refreshed access token")
    expires_at = None
    if token.get("expires_in"):
        expires_at = datetime.fromtimestamp(_now() + int(token["expires_in"]), timezone.utc)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE web_connected_accounts
               SET access_token_encrypted=%s, token_expires_at=%s, updated_at=NOW()
               WHERE id=%s""",
            (_encrypt(access_token), expires_at, account["id"]),
        )
    return access_token


def _token(user_id: str) -> str:
    account = _account(user_id)
    if not account:
        raise HTTPException(status_code=401, detail="Google is not connected")
    access = _decrypt(account.get("_access"))
    if not access:
        return _refresh(user_id, account)
    return access


def _google_request(user_id: str, method: str, url: str, **kwargs: Any) -> requests.Response:
    token = _token(user_id)
    headers = dict(kwargs.pop("headers", {}) or {})
    headers["Authorization"] = f"Bearer {token}"
    headers.setdefault("Accept", "application/json")
    response = requests.request(method, url, headers=headers, timeout=25, **kwargs)
    if response.status_code == 401:
        account = _account(user_id)
        if account and account.get("_refresh"):
            token = _refresh(user_id, account)
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(method, url, headers=headers, timeout=25, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message") or response.json().get("error_description")
        except Exception:
            detail = None
        raise HTTPException(status_code=502, detail=f"Google request failed{': ' + str(detail) if detail else ''}"[:500])
    return response


def _audit(user_id: str, event: str, operation: str = "", target: str = "", approval_id: Optional[str] = None) -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO web_audit_logs
               (user_id,event,service,tool_name,approval_id,details)
               VALUES (%s,%s,'google','google_connector',%s,%s::jsonb)""",
            (user_id, event, approval_id, json.dumps({"operation": operation, "target": target[:500]})),
        )


def _fingerprint(operation: str, target: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps({"service": "google", "operation": operation, "target": target, "payload": payload},
                     sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _execute(user_id: str, operation: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    operation = str(operation or "").strip().lower()

    if operation == "list_gmail":
        q = str(payload.get("query") or "in:anywhere").strip()[:500]
        limit = max(1, min(int(payload.get("limit") or 20), 50))
        r = _google_request(
            user_id,
            "GET",
            GOOGLE_GMAIL + "/users/me/messages",
            params={"q": q, "maxResults": limit},
        )
        body = r.json()
        messages = body.get("messages") or []
        result_size_estimate = body.get("resultSizeEstimate")
        items = []
        for item in messages[:limit]:
            mid = str(item.get("id") or "")
            if not mid:
                continue
            m = _google_request(user_id, "GET", GOOGLE_GMAIL + f"/users/me/messages/{urllib.parse.quote(mid)}",
                                params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]}).json()
            headers = {str(x.get("name")): str(x.get("value") or "") for x in (m.get("payload", {}).get("headers") or [])}
            items.append({"id": mid, "thread_id": m.get("threadId"), "snippet": m.get("snippet"),
                           "from": headers.get("From"), "to": headers.get("To"),
                           "subject": headers.get("Subject"), "date": headers.get("Date")})
        return {"verified": True, "operation": operation, "messages": items,
                "result_size_estimate": result_size_estimate}

    if operation == "list_drive":
        q = str(payload.get("query") or "trashed = false").strip()[:1000]
        limit = max(1, min(int(payload.get("limit") or 30), 100))
        r = _google_request(user_id, "GET", GOOGLE_DRIVE + "/files",
                            params={"q": q, "pageSize": limit, "orderBy": "modifiedTime desc",
                                    "fields": "files(id,name,mimeType,modifiedTime,webViewLink,size),nextPageToken"})
        body = r.json()
        return {"verified": True, "operation": operation, "files": body.get("files") or [], "next_page_token": body.get("nextPageToken")}

    if operation == "list_calendar":
        limit = max(1, min(int(payload.get("limit") or 20), 50))
        r = _google_request(user_id, "GET", GOOGLE_CALENDAR + "/calendars/primary/events",
                            params={"singleEvents": "true", "orderBy": "startTime", "timeMin": datetime.now(timezone.utc).isoformat(), "maxResults": limit})
        return {"verified": True, "operation": operation,
                "events": [{"id": x.get("id"), "summary": x.get("summary"),
                            "start": x.get("start"), "end": x.get("end"),
                            "htmlLink": x.get("htmlLink")} for x in (r.json().get("items") or [])]}

    if operation == "send_gmail":
        to = str(payload.get("to") or "").strip()
        subject = str(payload.get("subject") or "").strip()[:300]
        body = str(payload.get("body") or "")[:20000]
        if not to or "@" not in to or not subject or not body:
            raise HTTPException(status_code=400, detail="to, subject and body are required")
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii").rstrip("=")
        r = _google_request(user_id, "POST", GOOGLE_GMAIL + "/users/me/messages/send",
                            headers={"Content-Type": "application/json"}, json={"raw": raw})
        data = r.json()
        message_id = str(data.get("id") or "").strip()
        thread_id = str(data.get("threadId") or "").strip()
        label_ids = data.get("labelIds") or []

        # A successful POST means Gmail accepted the submission, but KZ must
        # verify the exact message exists in the user's SENT mailbox before
        # claiming "email sent". Re-read the returned message and compare the
        # provider's To/Subject headers with the approved payload.
        verified = False
        verified_to = ""
        verified_subject = ""
        verified_labels = list(label_ids)
        if message_id:
            try:
                verify_r = _google_request(
                    user_id,
                    "GET",
                    GOOGLE_GMAIL + f"/users/me/messages/{urllib.parse.quote(message_id)}",
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["To", "Subject"],
                    },
                )
                verify_data = verify_r.json()
                verified_labels = verify_data.get("labelIds") or verified_labels
                headers = {
                    str(x.get("name") or "").lower(): str(x.get("value") or "").strip()
                    for x in (verify_data.get("payload", {}).get("headers") or [])
                }
                verified_to = headers.get("to", "")
                verified_subject = headers.get("subject", "")
                verified = (
                    "SENT" in {str(x).upper() for x in verified_labels}
                    and to.lower() in verified_to.lower()
                    and subject == verified_subject
                )
            except Exception as verify_exc:
                logger.warning(
                    "Gmail send verification failed for message %s: %s",
                    message_id,
                    type(verify_exc).__name__,
                )

        return {
            "verified": verified,
            "operation": operation,
            "message": {
                "id": message_id,
                "thread_id": thread_id,
                "label_ids": verified_labels,
                "to": verified_to,
                "subject": verified_subject,
            },
        }

    if operation == "create_calendar_event":
        summary = str(payload.get("summary") or "").strip()[:300]
        start = str(payload.get("start") or "").strip()
        end = str(payload.get("end") or "").strip()
        timezone_name = str(payload.get("timezone") or "UTC").strip()[:100]
        description = str(payload.get("description") or "")[:5000]
        if not summary or not start or not end:
            raise HTTPException(status_code=400, detail="summary, start and end are required")
        event = {"summary": summary, "description": description,
                 "start": {"dateTime": start, "timeZone": timezone_name},
                 "end": {"dateTime": end, "timeZone": timezone_name}}
        r = _google_request(user_id, "POST", GOOGLE_CALENDAR + "/calendars/primary/events",
                            headers={"Content-Type": "application/json"}, json=event)
        data = r.json()
        return {"verified": bool(data.get("id") and data.get("htmlLink")), "operation": operation,
                "event": {"id": data.get("id"), "summary": data.get("summary"),
                          "htmlLink": data.get("htmlLink"), "start": data.get("start"), "end": data.get("end")}}

    if operation == "upload_drive_text":
        name = str(payload.get("name") or "").strip()[:255]
        content = str(payload.get("content") or "")[:50000]
        mime_type = str(payload.get("mime_type") or "text/plain").strip()[:100]
        if not name or not content:
            raise HTTPException(status_code=400, detail="name and content are required")
        metadata = {"name": name, "mimeType": mime_type}
        boundary = "kz_" + secrets.token_hex(12)
        metadata_bytes = json.dumps(metadata).encode("utf-8")
        content_bytes = content.encode("utf-8")
        multipart = (
            b"--" + boundary.encode() + b"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" +
            metadata_bytes + b"\r\n--" + boundary.encode() +
            b"\r\nContent-Type: " + mime_type.encode() + b"\r\n\r\n" +
            content_bytes + b"\r\n--" + boundary.encode() + b"--\r\n"
        )
        # Re-issue against multipart endpoint. The preliminary request above
        # is avoided by requiring a normal 4xx path; kept separate for clarity.
        r = _google_request(user_id, "POST", "https://www.googleapis.com/upload/drive/v3/files",
                            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
                            params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"},
                            data=multipart)
        data = r.json()
        return {"verified": bool(data.get("id")), "operation": operation,
                "file": {"id": data.get("id"), "name": data.get("name"),
                         "mimeType": data.get("mimeType"), "webViewLink": data.get("webViewLink")}}

    raise HTTPException(status_code=400, detail=f"Unsupported Google operation: {operation}")


def _automatic_operation_name(operation: str) -> str:
    operation = str(operation or "").strip().lower()
    if operation == "send_gmail":
        return "send"
    if operation == "create_calendar_event":
        return "write"
    if operation == "upload_drive_text":
        return "write"
    return operation

def _has_automatic_permission(user_id: str, operation: str) -> bool:
    """Check the user's persistent 'allow always' permission for this Google action."""
    allowed_operation = _automatic_operation_name(operation)
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """SELECT permission_level, allowed_operations
                   FROM web_permissions
                   WHERE user_id=%s AND service='google' AND revoked_at IS NULL
                   LIMIT 1""",
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return False
        level = str(_row_value(row, "permission_level", 0) or "")
        raw_ops = _row_value(row, "allowed_operations", 1)
        if isinstance(raw_ops, str):
            try:
                raw_ops = json.loads(raw_ops)
            except Exception:
                raw_ops = []
        return level == "automatic_action" and allowed_operation in (raw_ops or [])
    except Exception as exc:
        logger.warning("Google automatic permission check failed: %s", type(exc).__name__)
        return False

def _grant_automatic_permission(user_id: str, operation: str) -> None:
    allowed_operation = _automatic_operation_name(operation)
    scope = {
        "send_gmail": "gmail.send",
        "create_calendar_event": "calendar.events",
        "upload_drive_text": "drive.file",
    }.get(str(operation), "google.action")
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO web_permissions
               (user_id, service, permission_level, scopes, allowed_operations, granted_at, updated_at, revoked_at)
               VALUES (%s,'google','automatic_action',%s::jsonb,%s::jsonb,NOW(),NOW(),NULL)
               ON CONFLICT (user_id, service)
               DO UPDATE SET
                 permission_level='automatic_action',
                 scopes=EXCLUDED.scopes,
                 allowed_operations=(
                   SELECT COALESCE(jsonb_agg(DISTINCT value), '[]'::jsonb)
                   FROM jsonb_array_elements_text(
                     COALESCE(web_permissions.allowed_operations, '[]'::jsonb) || EXCLUDED.allowed_operations
                   ) AS value
                 ),
                 granted_at=NOW(),
                 updated_at=NOW(),
                 revoked_at=NULL""",
            (user_id, json.dumps([scope]), json.dumps([allowed_operation])),
        )

def _approval(user_id: str, operation: str, target: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if _has_automatic_permission(user_id, operation):
        try:
            result = _execute(user_id, operation, payload)
            if result.get("verified"):
                return {
                    "status": "completed",
                    "verified": True,
                    "provider": "google",
                    "operation": operation,
                    "target": target,
                    "result": result,
                    "message": "Action completed using your saved Google permission.",
                }
        except Exception as exc:
            logger.warning("Saved Google permission execution failed: %s", type(exc).__name__)
            # Fail closed: if the saved permission cannot complete this action,
            # surface the normal approval card instead of claiming success.
    fingerprint = _fingerprint(operation, target, payload)
    approval_id = str(uuid.uuid4())
    exact = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO web_approvals
               (id,user_id,service,operation,target,exact_content,action_fingerprint,status)
               VALUES (%s,%s,'google',%s,%s,%s,%s,'pending') RETURNING id""",
            (approval_id, user_id, operation, target[:500], exact, fingerprint),
        )
        row = cur.fetchone()
        approval_id = str(_row_value(row, "id", 0) or approval_id)
    # The approval row is the source of truth. Audit logging is secondary:
    # a transient audit-table failure must never discard a valid approval or
    # prevent the user from approving the exact action.
    try:
        _audit(user_id, "connector_action_approval_created", operation, target, approval_id)
    except Exception as exc:
        logger.exception(
            "Google approval audit write failed approval=%s: %s",
            approval_id,
            type(exc).__name__,
        )
    return {"status": "waiting_for_approval", "approval_id": approval_id, "provider": "google",
            "operation": operation, "target": target, "preview": payload,
            "message": "Approval required. KZ will execute only this exact Google action after you approve it."}


@router.get("/status")
async def google_status(request: Request):
    user_id = _connector_user_id(request)
    account = _account(user_id)
    missing = []
    if not GOOGLE_CLIENT_ID: missing.append("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_SECRET: missing.append("GOOGLE_CLIENT_SECRET")
    if not GOOGLE_REDIRECT_URI: missing.append("GOOGLE_REDIRECT_URI")
    if not CONNECTOR_STATE_SECRET: missing.append("CONNECTOR_STATE_SECRET")
    if not os.getenv("KZ_CONNECTOR_ENCRYPTION_KEY", "").strip(): missing.append("KZ_CONNECTOR_ENCRYPTION_KEY")
    return {"configured": _configured(), "connected": bool(account),
            "account": {k:v for k,v in (account or {}).items() if not k.startswith("_")},
            "authorization_mode": "oauth", "scopes": GOOGLE_SCOPES.split(),
            "missing_configuration": missing}


@router.get("/start")
async def google_start(request: Request):
    user_id = _connector_user_id(request)
    if not _configured():
        raise HTTPException(status_code=503, detail="Google connector is not configured on KZ")
    state = _sign_state({"provider": "google", "user_id": user_id, "return_url": _oauth_return_url(request), "nonce": secrets.token_urlsafe(18), "exp": _now() + 600})

    # Always let Google show the account chooser. Do not send a login_hint:
    # users may have multiple Google accounts and should be able to tap the
    # account they want to connect instead of being forced into one email.
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "select_account consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return RedirectResponse(GOOGLE_AUTHORIZE + "?" + urllib.parse.urlencode(params))


@router.get("/callback")
async def google_callback(request: Request):
    state_value = request.query_params.get("state") or ""
    try:
        callback_frontend = _state_return_url(_verify_state(state_value))
    except Exception:
        callback_frontend = FRONTEND_URL
    try:
        if not _configured():
            return RedirectResponse(f"{callback_frontend}/dashboard?connector_error=google_not_configured")

        error = request.query_params.get("error")
        if error:
            detail = request.query_params.get("error_description") or error
            return RedirectResponse(
                f"{callback_frontend}/dashboard?connector_error=google_{urllib.parse.quote(str(detail)[:300])}"
            )

        payload = _verify_state(state_value)
        callback_frontend = _state_return_url(payload)
        user_id = str(payload.get("user_id") or "").strip()
        if not user_id:
            raise HTTPException(status_code=403, detail="Google authorization state has no KZ user")

        code = request.query_params.get("code") or ""
        if not code:
            raise HTTPException(status_code=400, detail="Google authorization code missing")

        response = requests.post(
            GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=25,
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("error_description") or response.json().get("error")
            except Exception:
                detail = None
            raise HTTPException(
                status_code=502,
                detail=f"Google token exchange failed{': ' + str(detail) if detail else ''}"
            )

        token = response.json()
        access = str(token.get("access_token") or "")
        if not access:
            raise HTTPException(status_code=502, detail="Google did not return an access token")

        profile_r = requests.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access}"},
            timeout=25,
        )
        if profile_r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Google profile verification failed")

        profile = profile_r.json()
        scopes = [x for x in str(token.get("scope") or GOOGLE_SCOPES).split() if x]
        _save_account(user_id, profile, token, scopes)
        _audit(
            user_id,
            "connector_connected",
            target=str(profile.get("email") or profile.get("sub") or "google"),
        )
        return RedirectResponse(
            f"{callback_frontend}/dashboard?connector=google&connected=1&email="
            f"{urllib.parse.quote(str(profile.get('email') or ''))}"
        )
    except HTTPException as exc:
        logger.warning("Google callback rejected: %s", str(exc.detail))
        return RedirectResponse(
            f"{callback_frontend}/dashboard?connector_error=google_{urllib.parse.quote(str(exc.detail or 'authorization_failed')[:300])}"
        )
    except Exception as exc:
        logger.exception("Google callback failed: %s", type(exc).__name__)
        return RedirectResponse(
            f"{callback_frontend}/dashboard?connector_error=google_callback_failed"
        )


@router.post("/disconnect")
async def google_disconnect(request: Request):
    user_id = _connector_user_id(request)
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_connected_accounts SET revoked_at=NOW(),updated_at=NOW() WHERE user_id=%s AND provider='google' AND revoked_at IS NULL", (user_id,))
    _audit(user_id, "connector_disconnected")
    return {"success": True, "provider": "google"}


@router.post("/action")
async def google_action(request: Request):
    user_id = _connector_user_id(request)
    body = await request.json()
    operation = str(body.get("operation") or "").strip().lower()
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    read_ops = {"list_gmail", "list_drive", "list_calendar"}
    if operation in read_ops:
        return {"status": "completed", "result": _execute(user_id, operation, payload)}
    if operation not in {"send_gmail", "create_calendar_event", "upload_drive_text"}:
        raise HTTPException(status_code=400, detail="Unsupported or unsafe Google operation")
    return await _approval(user_id, operation, str(payload.get("to") or payload.get("name") or payload.get("summary") or "google"), payload)


@router.post("/approve/{approval_id}")
async def google_approve(approval_id: str, request: Request):
    user_id = _connector_user_id(request)
    body = await request.json()
    approved = bool(body.get("approved"))
    remember = bool(body.get("remember"))
    with get_db_cursor(commit=False) as cur:
        cur.execute("""SELECT id,operation,target,exact_content,action_fingerprint,status
                       FROM web_approvals WHERE id=%s AND user_id=%s AND service='google' LIMIT 1""",
                    (approval_id, user_id))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    status = str(_row_value(row, "status", 5) or "")
    if status != "pending":
        raise HTTPException(status_code=409, detail=f"Approval is already {status}")
    operation = str(_row_value(row, "operation", 1) or "")
    target = str(_row_value(row, "target", 2) or "")
    exact = str(_row_value(row, "exact_content", 3) or "{}")
    fingerprint = str(_row_value(row, "action_fingerprint", 4) or "")
    payload = json.loads(exact)
    if _fingerprint(operation, target, payload) != fingerprint:
        raise HTTPException(status_code=409, detail="Approval fingerprint mismatch; action was not executed")
    if not approved:
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_approvals SET status='rejected',rejected_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
        _audit(user_id, "connector_action_rejected", operation, target, approval_id)
        return {"status": "rejected", "approval_id": approval_id}
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_approvals SET status='approved',approved_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
    try:
        result = _execute(user_id, operation, payload)
    except Exception:
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_approvals SET status='expired' WHERE id=%s AND status='approved'", (approval_id,))
        raise
    verified = bool(result.get("verified"))
    with get_db_cursor(commit=True) as cur:
        cur.execute("UPDATE web_approvals SET status=%s,executed_at=NOW() WHERE id=%s AND status='approved'",
                    ("executed" if verified else "expired", approval_id))
    _audit(user_id, "connector_action_verified" if verified else "connector_action_unverified", operation, target, approval_id)
    if not verified:
        raise HTTPException(status_code=502, detail="Google accepted the request but KZ could not verify the resulting resource")
    if remember:
        try:
            _grant_automatic_permission(user_id, operation)
        except Exception as exc:
            logger.warning("Google allow-always permission could not be saved after verified action: %s", type(exc).__name__)
            return {"status": "completed", "verified": True, "approval_id": approval_id, "result": result, "permission_saved": False}
    return {"status": "completed", "verified": True, "approval_id": approval_id, "result": result, "permission_saved": bool(remember)}
