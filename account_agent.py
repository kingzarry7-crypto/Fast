"""KZ Account Agent V1.

Central account-aware orchestration for Telegram and future channels.
Identity is resolved once, then official connectors are used. Consequential
actions always go through the connector approval/evidence path.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database import get_db_cursor
from memory_link_bridge import resolve_platform_identity

logger = logging.getLogger("king_zarry_account_agent")

_SLEEP_START = os.getenv("KZ_SLEEP_START", "23:00")
_SLEEP_END = os.getenv("KZ_SLEEP_END", "07:00")


def web_user_id(platform: str, external_id: str) -> Optional[str]:
    """Resolve a channel identity to the UUID used by web_connected_accounts."""
    raw = resolve_platform_identity(platform, str(external_id))
    if not raw:
        return None
    value = str(raw).strip()
    if value.startswith("web:"):
        value = value[4:]
    return value or None


def _ensure_monitor_table() -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kz_account_monitors (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                provider VARCHAR(100) NOT NULL,
                monitor_type VARCHAR(100) NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                last_checked_at TIMESTAMPTZ,
                last_event_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, provider, monitor_type)
            )
            """
        )


def connected_accounts(user_id: str) -> list[dict[str, Any]]:
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT id, provider, provider_account_id, display_name, scopes,
                      metadata, revoked_at, updated_at
               FROM web_connected_accounts
               WHERE user_id=%s AND revoked_at IS NULL
               ORDER BY updated_at DESC""",
            (str(user_id),),
        )
        rows = cur.fetchall() or []
    out = []
    for row in rows:
        if hasattr(row, "keys"):
            out.append(dict(row))
        else:
            out.append({
                "id": row[0], "provider": row[1], "provider_account_id": row[2],
                "display_name": row[3], "scopes": row[4], "metadata": row[5],
                "revoked_at": row[6], "updated_at": row[7],
            })
    return out


def account_snapshot(user_id: str) -> dict[str, Any]:
    accounts = connected_accounts(user_id)
    by_provider: dict[str, Any] = {}
    for account in accounts:
        provider = str(account.get("provider") or "")
        by_provider.setdefault(provider, []).append({
            "id": str(account.get("id") or ""),
            "account": str(account.get("display_name") or account.get("provider_account_id") or ""),
            "scopes": account.get("scopes") or [],
        })
    return {
        "connected": bool(accounts),
        "count": len(accounts),
        "providers": by_provider,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _sleeping() -> bool:
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(os.getenv("KZ_TIMEZONE", "Africa/Lagos")))
        start_h, start_m = [int(x) for x in _SLEEP_START.split(":")]
        end_h, end_m = [int(x) for x in _SLEEP_END.split(":")]
        cur = now.hour * 60 + now.minute
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        return (cur >= start or cur < end) if start >= end else (start <= cur < end)
    except Exception:
        return False


def _send_gmail_preview(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from google_connector import _account, _approval
    account = _account(user_id)
    if not account:
        return {"status": "not_connected"}
    approval = _approval(user_id, "send_gmail", payload["to"], payload)
    return {
        "status": "waiting_for_approval",
        "approval_id": approval["approval_id"],
        "account": account.get("display_name") or account.get("provider_account_id"),
        "payload": payload,
    }


def _parse_email_request(text: str) -> Optional[dict[str, str]]:
    raw = str(text or "").strip()
    if not re.search(r"\b(send|email|mail)\b", raw, re.I):
        return None
    match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", raw, re.I)
    if not match:
        return None
    to = match.group(0)
    sm = re.search(
        r"\bsubject\s*[:=-]\s*(.+?)(?=\n|\b(?:body|message|saying|tell)\b\s*[:=-]|$)",
        raw, re.I | re.S,
    )
    bm = re.search(r"\b(?:body|message|saying|tell)\s*[:=-]\s*(.+)$", raw, re.I | re.S)
    subject = sm.group(1).strip() if sm else "Message from King Zarry AI"
    body = bm.group(1).strip() if bm else ""
    if not body:
        body = re.sub(r"^.*?\b(?:send|email|mail)\b", "", raw, flags=re.I).strip()
        body = re.sub(r"\bsubject\s*[:=-].*$", "", body, flags=re.I | re.S).strip()
        body = re.sub(r"^\b(?:an?\s+)?email\b", "", body, flags=re.I).strip()
        body = re.sub(r"^\b(?:to|for)\b", "", body, flags=re.I).strip()
    if not body:
        return None
    return {"to": to, "subject": subject[:300], "body": body[:20000]}


def _format_gmail_result(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return "📭 Gmail check complete — no matching messages found."
    lines = [f"📬 Gmail check complete — {len(messages)} message(s):", ""]
    for item in messages[:8]:
        subject = str(item.get("subject") or "(no subject)")
        sender = str(item.get("from") or "unknown sender")
        date = str(item.get("date") or "")
        snippet = str(item.get("snippet") or "").replace("\n", " ")[:180]
        lines.append(f"• {subject}\n  From: {sender}\n  {date}\n  {snippet}")
    return "\n".join(lines)


def _format_accounts(snapshot: dict[str, Any]) -> str:
    if not snapshot["connected"]:
        return "🔌 ACCOUNT CHECK COMPLETE — no official accounts are connected to this KZ account."
    lines = [f"🔌 ACCOUNT CHECK COMPLETE — {snapshot['count']} connected account(s)."]
    for provider, accounts in snapshot["providers"].items():
        for account in accounts:
            lines.append(f"• {provider}: {account['account']}")
    lines.append("KZ can use these connections only within their granted permissions.")
    return "\n".join(lines)


def _monitor_upsert(user_id: str, provider: str = "google", monitor_type: str = "gmail") -> None:
    _ensure_monitor_table()
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO kz_account_monitors(user_id,provider,monitor_type,active,updated_at)
               VALUES(%s,%s,%s,TRUE,NOW())
               ON CONFLICT(user_id,provider,monitor_type)
               DO UPDATE SET active=TRUE,updated_at=NOW()""",
            (user_id, provider, monitor_type),
        )


def _monitor_disable(user_id: str, provider: str = "google", monitor_type: str = "gmail") -> None:
    _ensure_monitor_table()
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE kz_account_monitors SET active=FALSE,updated_at=NOW()
               WHERE user_id=%s AND provider=%s AND monitor_type=%s""",
            (user_id, provider, monitor_type),
        )


def _monitor_rows() -> list[dict[str, Any]]:
    _ensure_monitor_table()
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """SELECT id,user_id,provider,monitor_type,active,state_json
               FROM kz_account_monitors WHERE active=TRUE"""
        )
        rows = cur.fetchall() or []
    result = []
    for row in rows:
        if hasattr(row, "keys"):
            result.append(dict(row))
        else:
            result.append({
                "id": row[0], "user_id": row[1], "provider": row[2],
                "monitor_type": row[3], "active": row[4], "state_json": row[5],
            })
    return result


def _monitor_gmail(user_id: str, previous: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from google_connector import _execute
    result = _execute(user_id, "list_gmail", {"query": "is:unread newer_than:1d", "limit": 20})
    messages = result.get("messages") or []
    previous_ids = set(previous.get("message_ids") or [])
    current_ids = [str(x.get("id") or "") for x in messages if x.get("id")]
    new_items = [x for x in messages if str(x.get("id") or "") not in previous_ids]
    return {"message_ids": current_ids[:50]}, new_items


def monitor_tick() -> list[dict[str, Any]]:
    """Check enabled account monitors. During sleep, store events; never act."""
    events: list[dict[str, Any]] = []
    for monitor in _monitor_rows():
        user_id = str(monitor["user_id"])
        state = monitor.get("state_json") or {}
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except Exception:
                state = {}
        try:
            if monitor["provider"] == "google" and monitor["monitor_type"] == "gmail":
                new_state, new_items = _monitor_gmail(user_id, state)
                now = datetime.now(timezone.utc)
                with get_db_cursor(commit=True) as cur:
                    cur.execute(
                        """UPDATE kz_account_monitors
                           SET state_json=%s::jsonb,last_checked_at=NOW(),
                               last_event_at=CASE WHEN %s THEN NOW() ELSE last_event_at END,
                               updated_at=NOW()
                           WHERE id=%s""",
                        (json.dumps(new_state), bool(new_items), monitor["id"]),
                    )
                if new_items:
                    event = {
                        "user_id": user_id,
                        "provider": "google",
                        "type": "new_gmail",
                        "count": len(new_items),
                        "items": new_items[:8],
                        "sleep_buffered": _sleeping(),
                        "at": now.isoformat(),
                    }
                    events.append(event)
        except Exception as exc:
            logger.warning("Account monitor failed user=%s: %s", user_id, exc)
    return events


def morning_account_digest(user_id: str) -> dict[str, Any]:
    """Fresh morning check: account status + monitored Gmail + permission prompt."""
    snapshot = account_snapshot(user_id)
    result: dict[str, Any] = {"snapshot": snapshot, "permission_needed": False, "messages": []}
    if not snapshot["connected"]:
        return result
    try:
        from google_connector import _execute
        gmail = _execute(user_id, "list_gmail", {"query": "is:unread newer_than:1d", "limit": 10})
        result["messages"] = gmail.get("messages") or []
        result["permission_needed"] = bool(result["messages"])
    except Exception as exc:
        result["error"] = str(exc)[:300]
    return result


def _identity_for_telegram(update: Any) -> Optional[str]:
    return web_user_id("telegram", str(update.effective_user.id))


async def handle_telegram_request(update: Any, text: str) -> Optional[dict[str, Any]]:
    """Return a result when this is an account/work request; otherwise None."""
    user_id = _identity_for_telegram(update)
    if not user_id:
        return None
    raw = str(text or "").strip()
    lower = raw.lower()

    if lower in {"account status", "check connected accounts", "what accounts are connected",
                 "show connected accounts", "monitor account status"}:
        await update.message.reply_text("🧠 KZ is checking your connected accounts...")
        result = account_snapshot(user_id)
        await update.message.reply_text(_format_accounts(result))
        return {"status": "completed", "kind": "account_status", "result": result}

    if lower.startswith("monitor my account") or lower.startswith("monitor my gmail") or lower.startswith("watch my gmail"):
        _monitor_upsert(user_id)
        await update.message.reply_text(
            "👁️ <b>ACCOUNT MONITOR ENABLED</b>\n\n"
            "KZ will check the connected Gmail account for new unread mail. "
            "During sleep hours it will buffer important changes and report them in the morning. "
            "KZ will not send, delete, reply, or modify anything just because monitoring is enabled.",
            parse_mode="HTML",
        )
        return {"status": "monitoring", "provider": "google", "monitor_type": "gmail"}

    if lower.startswith("stop monitoring"):
        _monitor_disable(user_id)
        await update.message.reply_text("🛑 Account monitoring stopped. No background Gmail checks will be performed.")
        return {"status": "stopped"}

    if lower in {"check my email", "check my gmail", "check my inbox", "check email", "check gmail"}:
        from google_connector import _account, _execute
        if not _account(user_id):
            await update.message.reply_text("🔌 KZ checked your account connections: Google Gmail is not connected to this KZ account.")
            return {"status": "not_connected"}
        await update.message.reply_text("🧠 KZ is securely checking the connected Gmail account...")
        result = await _run_sync(_execute, user_id, "list_gmail", {"query": "in:anywhere", "limit": 10})
        await update.message.reply_text(_format_gmail_result(result))
        return {"status": "completed", "kind": "gmail_read", "result": result}

    payload = _parse_email_request(raw)
    if payload:
        from google_connector import _account
        if not _account(user_id):
            await update.message.reply_text("🔌 KZ found no connected Google account for this KZ identity. Connect Google Workspace first.")
            return {"status": "not_connected"}
        await update.message.reply_text("🧠 KZ found your connected Google account and prepared the requested action. Checking the exact approval...")
        result = _send_gmail_preview(user_id, payload)
        await update.message.reply_text(
            "📧 <b>READY — YOUR PERMISSION IS REQUIRED</b>\n\n"
            f"To: {payload['to']}\nSubject: {payload['subject']}\n\n"
            f"{payload['body'][:4000]}\n\n"
            f"Approval ID: <code>{result.get('approval_id','')}</code>\n"
            "Reply <code>APPROVE</code> to send, or <code>REJECT</code> to cancel.",
            parse_mode="HTML",
        )
        return result

    return None


async def _run_sync(fn: Any, *args: Any) -> Any:
    import asyncio
    return await asyncio.to_thread(fn, *args)


async def morning_telegram_digest(bot: Any) -> dict[str, int]:
    """Send morning account feedback to Telegram identities linked to KZ web users."""
    from neon_memory import NeonMemory
    mem = NeonMemory()
    sent = failed = 0
    with mem.lock:
        conn = mem._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT platform,external_id,user_id FROM kz_memory_identities WHERE platform='telegram'")
            identities = cur.fetchall() or []
        finally:
            conn.close()
    for row in identities:
        platform, external_id, raw_user = row[0], row[1], row[2]
        user_id = str(raw_user)
        if user_id.startswith("web:"):
            user_id = user_id[4:]
        try:
            digest = morning_account_digest(user_id)
            if not digest.get("snapshot", {}).get("connected"):
                continue
            messages = digest.get("messages") or []
            text = [
                "🌅 <b>KZ MORNING ACCOUNT CHECK</b>",
                "",
                _format_accounts(digest["snapshot"]),
                "",
                f"📬 Unread/new Gmail found: <b>{len(messages)}</b>",
            ]
            if messages:
                text.append("")
                for item in messages[:5]:
                    text.append(f"• {html_escape(item.get('subject') or '(no subject)')} — {html_escape(item.get('from') or '')}")
                text.extend([
                    "",
                    "🛡️ <b>PERMISSION:</b> I will not reply or send anything automatically.",
                    "If you want KZ to prepare responses, say <code>PREPARE REPLIES</code>.",
                ])
            else:
                text.extend(["", "✅ Nothing requiring your permission was found."])
            await bot.send_message(chat_id=external_id, text="\n".join(text), parse_mode="HTML")
            sent += 1
        except Exception as exc:
            failed += 1
            logger.warning("Morning account digest failed for %s: %s", external_id, exc)
    return {"sent": sent, "failed": failed}


def html_escape(value: Any) -> str:
    import html
    return html.escape(str(value or ""))


