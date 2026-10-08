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


def channel_user_id(platform: str, external_id: str) -> str:
    """Return the shared workflow identity for any channel."""
    resolved = web_user_id(platform, external_id)
    if resolved:
        return resolved
    return f"{str(platform).strip().lower()}:{str(external_id).strip()}"

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

    # Browser-connected accounts are stored in Neon metadata so Telegram/Discord
    # can see the same web-connected session even though Playwright itself lives
    # in the FastAPI process.
    try:
        from browser_account_registry import list_browser_accounts
        for account in list_browser_accounts(str(user_id)):
            out.append({
                "id": f"browser:{account.get('account_id')}",
                "provider": "browser",
                "provider_account_id": str(account.get("account_id") or ""),
                "display_name": str(account.get("display_name") or account.get("url") or "Browser account"),
                "scopes": [],
                "metadata": {
                    "url": account.get("url"),
                    "status": account.get("status"),
                    "verified_at": account.get("verified_at"),
                },
                "revoked_at": None,
                "updated_at": account.get("last_seen_at"),
            })
    except Exception as exc:
        logger.warning("Browser account registry unavailable: %s", type(exc).__name__)

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


def account_context_for_ai(user_id: str) -> str:
    """Return non-secret connected-account capabilities for the LLM."""
    try:
        snapshot = account_snapshot(str(user_id))
        if not snapshot.get("connected"):
            return (
                "CONNECTED ACCOUNTS: none. "
                "Do not claim access to Gmail, Drive, Calendar, or other external accounts."
            )
        lines = [
            "CONNECTED ACCOUNTS (verified server-side; credentials are never exposed to the model):",
        ]
        for provider, accounts in snapshot.get("providers", {}).items():
            for account in accounts:
                scopes = account.get("scopes") or []
                scope_names = []
                for scope in scopes:
                    s = str(scope)
                    if "gmail.readonly" in s:
                        scope_names.append("gmail.read")
                    elif "gmail.send" in s:
                        scope_names.append("gmail.send")
                    elif "drive.metadata.readonly" in s:
                        scope_names.append("drive.read")
                    elif "drive.file" in s:
                        scope_names.append("drive.write")
                    elif "calendar.readonly" in s:
                        scope_names.append("calendar.read")
                    elif "calendar.events" in s:
                        scope_names.append("calendar.write")
                    elif "read_products" in s:
                        scope_names.append("shopify.products.read")
                    elif "write_products" in s:
                        scope_names.append("shopify.products.write")
                    elif "read_orders" in s:
                        scope_names.append("shopify.orders.read")
                    elif "write_inventory" in s:
                        scope_names.append("shopify.inventory.write")
                lines.append(
                    f"- {provider}: {account.get('account') or 'connected account'}"
                    + (f" [capabilities: {', '.join(sorted(set(scope_names)))}]" if scope_names else "")
                )
        lines.extend([
            "ACCOUNT-AWARE RULES:",
            "1. You may tell the user that KZ has verified access only to the capabilities listed above.",
            "2. For account work, route through KZ's connector/account agent; never invent completion.",
            "3. Read-only checks may execute immediately when the connector permits them.",
            "4. External sends, replies, writes, deletes, or other consequential actions require the existing approval gate.",
            "5. After execution, report only the provider's verified result/evidence.",
        ])
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Account context load failed: %s", type(exc).__name__)
        return "CONNECTED ACCOUNT CONTEXT: unavailable. Do not claim external account access."

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
    """Parse natural-language Gmail compose/send requests without falling through to the LLM."""
    raw = str(text or "").strip()
    if not re.search(r"\b(send|email|mail|compose|draft|write)\b", raw, re.I):
        return None

    match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", raw, re.I)
    if not match:
        return None
    to = match.group(0)

    sm = re.search(
        r"\bsubject\s*[:=-]\s*(.+?)(?=\n|\b(?:body|message|saying|tell|say|about|regarding)\b\s*[:=-]?|$)",
        raw, re.I | re.S,
    )
    bm = re.search(
        r"\b(?:body|message|saying|say|tell(?:\s+them)?(?:\s+that)?|about|regarding)\b\s*[:=-]?\s*(.+)$",
        raw, re.I | re.S,
    )
    subject = sm.group(1).strip() if sm else ""

    body = bm.group(1).strip() if bm else ""
    if not body:
        body = raw
        body = re.sub(r"^.*?\b(?:send|email|mail|compose|draft|write)\b", "", body, flags=re.I).strip()
        body = re.sub(re.escape(to), "", body, count=1, flags=re.I).strip()
        body = re.sub(r"^\b(?:an?\s+)?email\b", "", body, flags=re.I).strip()
        body = re.sub(r"^\b(?:to|for)\b", "", body, flags=re.I).strip()
        body = re.sub(r"^\b(?:subject)\s*[:=-]\s*[^\n]+", "", body, flags=re.I).strip()
        body = re.sub(r"^\b(?:saying|say|tell(?:\s+them)?(?:\s+that)?)\b\s*[:=-]?\s*", "", body, flags=re.I).strip()
        body = re.sub(r"^\b(?:about|regarding)\b\s*[:=-]?\s*", "", body, flags=re.I).strip()

    if not body:
        return None
    if not subject:
        subject = "Message from King Zarry AI"
    return {"to": to, "subject": subject[:300], "body": body[:20000]}



def _gmail_read_intent(text: str) -> Optional[dict[str, str]]:
    """Recognize safe, read-only Gmail questions without sending them to the LLM."""
    raw = str(text or "").strip()
    lower = raw.lower()
    if not raw or not re.search(r"\b(gmail|email|emails|mail|inbox|message|messages)\b", lower):
        return None
    if re.search(r"\b(send|write|compose|draft|reply|forward|delete|remove|archive)\b", lower):
        return None
    if re.search(r"\b(how many|how much|count|number of|total)\b", lower):
        query = "is:unread" if re.search(r"\bunread\b", lower) else ("newer_than:1d" if re.search(r"\btoday|today's\b", lower) else "in:anywhere")
        kind = "gmail_unread_count" if "unread" in lower else ("gmail_today_count" if re.search(r"\btoday|today's\b", lower) else "gmail_count")
        return {"query": query, "kind": kind}
    if re.search(r"\bunread\b", lower) and re.search(r"\b(show|list|check|see|view|what|which|new)\b", lower):
        return {"query": "is:unread", "kind": "gmail_read"}
    if re.search(r"\b(today|today's|recent|latest|new)\b", lower) or lower in {"inbox", "my inbox", "my email", "my emails", "my gmail", "my mail"}:
        return {"query": "newer_than:1d" if re.search(r"\btoday|today's\b", lower) else "in:anywhere", "kind": "gmail_read"}
    if re.search(r"\b(check|show|list|see|view|read|what)\b", lower):
        return {"query": "in:anywhere", "kind": "gmail_read"}
    return None


def _format_gmail_count(result: dict[str, Any], kind: str) -> str:
    estimate = result.get("result_size_estimate")
    try:
        count = int(estimate) if estimate is not None else None
    except (TypeError, ValueError):
        count = None
    if count is None:
        return "📬 Gmail check completed, but Google did not return a message count."
    label = "unread" if kind == "gmail_unread_count" else "matching"
    return f"📬 Gmail reports approximately <b>{count}</b> {label} message(s) for that search."

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


def _shopify_read_intent(text: str, snapshot: dict[str, Any]) -> Optional[dict[str, str]]:
    """Recognize safe Shopify read requests and route them to the official connector."""
    raw = str(text or "").strip()
    lower = raw.lower()
    if not raw:
        return None

    if re.search(r"\b(shopify|my store|my shop|storefront)\b", lower):
        if re.search(r"\b(order|orders|sales|purchases)\b", lower):
            return {"operation": "orders", "kind": "shopify_orders"}
        if re.search(r"\b(product|products|inventory|stock|items)\b", lower):
            return {"operation": "products", "kind": "shopify_products"}
        return {"operation": "shop", "kind": "shopify_store"}

    if not any(p == "shopify" for p in (snapshot.get("providers") or {})):
        return None
    if re.search(r"\b(products|inventory|stock|items)\b", lower):
        return {"operation": "products", "kind": "shopify_products"}
    if re.search(r"\b(orders|sales|purchases)\b", lower):
        return {"operation": "orders", "kind": "shopify_orders"}
    return None


def _format_shopify_result(result: dict[str, Any], kind: str) -> str:
    if kind == "shopify_store":
        shop = result.get("shop") or {}
        return (
            "🛍️ SHOPIFY CHECK COMPLETE\n\n"
            f"Store: {shop.get('name') or shop.get('myshopifyDomain') or 'Connected Shopify store'}\n"
            f"Domain: {shop.get('myshopifyDomain') or 'unknown'}"
        )
    if kind == "shopify_products":
        products = ((result.get("products") or {}).get("nodes") or [])
        if not products:
            return "🛍️ SHOPIFY PRODUCTS CHECK COMPLETE — no products were returned."
        lines = [f"🛍️ SHOPIFY PRODUCTS — {len(products)} returned", ""]
        for item in products[:20]:
            lines.append(
                f"• {item.get('title') or '(untitled)'} — "
                f"{item.get('status') or 'unknown'} — {item.get('handle') or ''}"
            )
        return "\n".join(lines)
    if kind == "shopify_orders":
        orders = ((result.get("orders") or {}).get("nodes") or [])
        if not orders:
            return "🛍️ SHOPIFY ORDERS CHECK COMPLETE — no orders were returned."
        lines = [f"🛍️ SHOPIFY ORDERS — {len(orders)} returned", ""]
        for item in orders[:20]:
            lines.append(
                f"• {item.get('name') or '(unnamed order)'} — "
                f"{item.get('displayFinancialStatus') or 'unknown payment'} — "
                f"{item.get('displayFulfillmentStatus') or 'unknown fulfillment'}"
            )
        return "\n".join(lines)
    return "🛍️ Shopify check completed."


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

    approval_match = re.match(
        r"^(approve|reject|send it|send the email|send the email now)(?:\s+([0-9a-fA-F-]{36}))?\s*$",
        raw,
        re.I,
    )
    if approval_match:
        approval_action = approval_match.group(1).lower()
        requested_approval_id = str(approval_match.group(2) or "").strip()
        from google_connector import _account, _execute, _fingerprint, _audit
        with get_db_cursor(commit=False) as cur:
            if requested_approval_id:
                cur.execute(
                    """SELECT id,operation,target,exact_content,action_fingerprint,status
                       FROM web_approvals
                       WHERE id=%s AND user_id=%s AND service='google' AND operation='send_gmail'
                       LIMIT 1""",
                    (requested_approval_id, user_id),
                )
            else:
                cur.execute(
                    """SELECT id,operation,target,exact_content,action_fingerprint,status
                       FROM web_approvals
                       WHERE user_id=%s AND service='google' AND operation='send_gmail' AND status='pending'
                       ORDER BY created_at DESC LIMIT 1""",
                    (user_id,),
                )
            row = cur.fetchone()
        if not row:
            await update.message.reply_text("ℹ️ KZ has no pending Google action waiting for approval.")
            return {"status": "no_pending_approval"}
        approval_id = str(row[0])
        operation = str(row[1] or "")
        target = str(row[2] or "")
        payload = json.loads(str(row[3] or "{}"))
        fingerprint = str(row[4] or "")
        if _fingerprint(operation, target, payload) != fingerprint:
            await update.message.reply_text("🛑 KZ rejected the action because its approval fingerprint no longer matches.")
            return {"status": "fingerprint_mismatch"}
        if approval_action == "reject":
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE web_approvals SET status='rejected',rejected_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
            _audit(user_id, "connector_action_rejected", operation, target, approval_id)
            await update.message.reply_text("🛑 REJECTED — KZ did not send or modify anything.")
            return {"status": "rejected", "approval_id": approval_id}
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_approvals SET status='approved',approved_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
        await update.message.reply_text("⚙️ APPROVED — KZ is executing the exact approved action and checking the provider result...")
        try:
            result = await _run_sync(_execute, user_id, operation, payload)
        except Exception as exc:
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE web_approvals SET status='expired' WHERE id=%s AND status='approved'", (approval_id,))
            logger.warning("Approved Google action failed: %s", exc)
            await update.message.reply_text("❌ EXECUTION FAILED — KZ did not claim success.")
            return {"status": "failed", "approval_id": approval_id}
        verified = bool(result.get("verified"))
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE web_approvals SET status=%s,executed_at=NOW() WHERE id=%s AND status='approved'",
                        ("executed" if verified else "expired", approval_id))
        _audit(user_id, "connector_action_verified" if verified else "connector_action_unverified", operation, target, approval_id)
        if verified:
            evidence = result.get("message") or result.get("event") or result.get("file") or {}
            await update.message.reply_text(
                "✅ <b>WORK COMPLETED & VERIFIED</b>\n\n"
                f"Provider: Google\nOperation: {html_escape(operation)}\n"
                f"Evidence ID: <code>{html_escape(evidence.get('id') or evidence.get('htmlLink') or 'verified')}</code>",
                parse_mode="HTML",
            )
            return {"status": "completed", "verified": True, "approval_id": approval_id, "result": result}
        await update.message.reply_text("⚠️ Google responded, but KZ could not verify the result. It is marked unverified.")
        return {"status": "unverified", "approval_id": approval_id}

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

    if lower in {"check my drive", "check drive", "show my drive files"}:
        from google_connector import _account, _execute
        if not _account(user_id):
            await update.message.reply_text("🔌 KZ checked your account: Google Drive is not connected.")
            return {"status": "not_connected"}
        await update.message.reply_text("🧠 KZ is checking the connected Google Drive...")
        result = await _run_sync(_execute, user_id, "list_drive", {"query": "trashed = false", "limit": 10})
        files = result.get("files") or []
        if not files:
            await update.message.reply_text("📁 Drive check complete — no files found.")
        else:
            lines = ["📁 <b>DRIVE CHECK COMPLETE</b>", ""]
            for item in files[:10]:
                lines.append("• " + html_escape(item.get("name") or "(unnamed)") + " — " + html_escape(item.get("mimeType") or ""))
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return {"status": "completed", "kind": "drive_read", "result": result}

    if lower in {"check my calendar", "check calendar", "what is on my calendar", "show my calendar"}:
        from google_connector import _account, _execute
        if not _account(user_id):
            await update.message.reply_text("🔌 KZ checked your account: Google Calendar is not connected.")
            return {"status": "not_connected"}
        await update.message.reply_text("🧠 KZ is checking your connected Google Calendar...")
        result = await _run_sync(_execute, user_id, "list_calendar", {"limit": 10})
        events = result.get("events") or []
        if not events:
            await update.message.reply_text("🗓️ Calendar check complete — no upcoming events found.")
        else:
            lines = ["🗓️ <b>CALENDAR CHECK COMPLETE</b>", ""]
            for item in events[:10]:
                lines.append("• " + html_escape(item.get("summary") or "(untitled)") + " — " + html_escape(str(item.get("start") or "")))
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return {"status": "completed", "kind": "calendar_read", "result": result}

    shopify_intent = _shopify_read_intent(raw, snapshot)
    if shopify_intent:
        try:
            from connector_api import _provider_account, _shopify_request, _shopify_token

            account = _provider_account(uid, "shopify")
            if not account:
                return {
                    "status": "not_connected",
                    "kind": shopify_intent["kind"],
                    "reply": "🔌 KZ checked the account registry: Shopify is not connected to this KZ account.",
                }

            store, token = _shopify_token(uid, "")
            operation = shopify_intent["operation"]
            if operation == "shop":
                result = _shopify_request(
                    store, token,
                    "query { shop { id name myshopifyDomain } }",
                )
            elif operation == "products":
                result = _shopify_request(
                    store, token,
                    "query { products(first: 20) { nodes { id title status handle } } }",
                )
            elif operation == "orders":
                result = _shopify_request(
                    store, token,
                    "query { orders(first: 20, sortKey: CREATED_AT, reverse: true) { nodes { id name createdAt displayFinancialStatus displayFulfillmentStatus } } }",
                )
            else:
                return None

            data = result.get("data") or {}
            return {
                "status": "completed",
                "kind": shopify_intent["kind"],
                "provider": "shopify",
                "operation": operation,
                "target": store,
                "reply": _format_shopify_result(data, shopify_intent["kind"]),
                "result": data,
            }
        except Exception as exc:
            logger.warning("Web Shopify read failed: %s", type(exc).__name__)
            detail = getattr(exc, "detail", None)
            return {
                "status": "failed",
                "kind": shopify_intent["kind"],
                "provider": "shopify",
                "reply": "❌ KZ could not complete the Shopify check. No success was claimed."
                        + (f"\nReason: {str(detail)[:220]}" if detail else ""),
                "error": type(exc).__name__,
            }

    gmail_intent = _gmail_read_intent(raw)
    if gmail_intent:
        from google_connector import _account, _execute
        if not _account(user_id):
            await update.message.reply_text("🔌 KZ checked your account connections: Google Gmail is not connected to this KZ account.")
            return {"status": "not_connected", "kind": gmail_intent["kind"]}
        await update.message.reply_text("🧠 KZ is securely checking the connected Gmail account...")
        result = await _run_sync(_execute, user_id, "list_gmail", {"query": gmail_intent["query"], "limit": 10})
        reply = _format_gmail_count(result, gmail_intent["kind"]) if gmail_intent["kind"].endswith("count") else _format_gmail_result(result)
        await update.message.reply_text(reply, parse_mode="HTML" if gmail_intent["kind"].endswith("count") else None)
        return {"status": "completed", "kind": gmail_intent["kind"], "result": result}

    email_action_requested = bool(
        re.search(r"\b(send|email|mail|compose|draft|write)\b", lower)
    )
    email_address_present = bool(
        re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", raw, re.I)
    )
    payload = _parse_email_request(raw)
    if email_action_requested:
        try:
            from google_connector import _account
            if not _account(uid):
                return {
                    "status": "not_connected",
                    "kind": "send_gmail",
                    "reply": "🔌 KZ checked the account registry: Gmail is not connected to this KZ account.",
                }
        except Exception:
            return {
                "status": "failed",
                "kind": "send_gmail",
                "reply": "❌ KZ could not verify the Gmail connection. No email was sent.",
            }
        if not email_address_present:
            return {
                "status": "needs_details",
                "kind": "send_gmail",
                "reply": "📧 Gmail is connected. Tell me the recipient email address, then I can prepare the email for your approval.",
            }
        if not payload:
            return {
                "status": "needs_details",
                "kind": "send_gmail",
                "reply": "📧 I found the recipient, but I still need the email content. Tell me what you want the message to say, and KZ will prepare it for your approval.",
            }

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


def handle_web_request(user_id: str, text: str) -> Optional[dict[str, Any]]:
    """Account-aware web-chat router shared with the normal AI chat path."""
    uid = str(user_id)
    raw = str(text or "").strip()
    lower = raw.lower()
    if not raw:
        return None

    snapshot = account_snapshot(uid)

    approval_match = re.match(
        r"^(approve|reject|send it|send the email|send the email now)(?:\s+([0-9a-fA-F-]{36}))?\s*$",
        raw,
        re.I,
    )
    if approval_match:
        approval_action = approval_match.group(1).lower()
        requested_approval_id = str(approval_match.group(2) or "").strip()
        from google_connector import _execute, _fingerprint, _audit
        with get_db_cursor(commit=False) as cur:
            if requested_approval_id:
                cur.execute(
                    """SELECT id,operation,target,exact_content,action_fingerprint,status
                       FROM web_approvals
                       WHERE id=%s AND user_id=%s AND service='google' AND operation='send_gmail'
                       LIMIT 1""",
                    (requested_approval_id, uid),
                )
            else:
                cur.execute(
                    """SELECT id,operation,target,exact_content,action_fingerprint,status
                       FROM web_approvals
                       WHERE user_id=%s AND service='google' AND operation='send_gmail' AND status='pending'
                       ORDER BY created_at DESC LIMIT 1""",
                    (uid,),
                )
            row = cur.fetchone()
        if not row:
            return {"status": "no_pending_approval", "kind": "approval",
                    "reply": "ℹ️ KZ has no pending Google action waiting for permission."}
        approval_id = str(row[0])
        approval_status = str(row[5] or "").strip().lower()
        if approval_status != "pending":
            return {"status": "approval_already_processed", "kind": "approval",
                    "approval_id": approval_id,
                    "reply": f"ℹ️ This approval has already been processed ({approval_status}). KZ will not send the email again."}
        operation = str(row[1] or "")
        target = str(row[2] or "")
        payload = json.loads(str(row[3] or "{}"))
        fingerprint = str(row[4] or "")
        if _fingerprint(operation, target, payload) != fingerprint:
            return {"status": "fingerprint_mismatch", "kind": "approval",
                    "reply": "🛑 KZ blocked the action because its approved payload no longer matches."}
        if lower == "reject":
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE web_approvals SET status='rejected',rejected_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
            _audit(uid, "connector_action_rejected", operation, target, approval_id)
            return {"status": "rejected", "kind": "approval",
                    "reply": f"🛑 REJECTED — KZ did not execute the Google action. Approval ID: {approval_id}"}
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE web_approvals SET status='approved',approved_at=NOW() WHERE id=%s AND status='pending'", (approval_id,))
            result = _execute(uid, operation, payload)
        except Exception as exc:
            logger.exception("Web approved Google action failed approval=%s operation=%s: %s", approval_id, operation, type(exc).__name__)
            try:
                with get_db_cursor(commit=True) as cur:
                    cur.execute("UPDATE web_approvals SET status='expired' WHERE id=%s AND status='approved'", (approval_id,))
            except Exception as db_exc:
                logger.exception("Could not mark failed Google approval expired: %s", type(db_exc).__name__)
            detail = getattr(exc, "detail", None)
            safe_detail = str(detail or "").strip()[:300]
            return {"status": "failed", "kind": "approval",
                    "reply": "❌ EXECUTION FAILED — KZ did not claim the action was completed."
                            + (f"\nReason: {safe_detail}" if safe_detail else ""),
                    "approval_id": approval_id}
        verified = bool(result.get("verified"))
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE web_approvals SET status=%s,executed_at=NOW() WHERE id=%s AND status='approved'",
                            ("executed" if verified else "expired", approval_id))
            _audit(uid, "connector_action_verified" if verified else "connector_action_unverified", operation, target, approval_id)
        except Exception as audit_exc:
            logger.exception("Google approval result persistence failed approval=%s: %s", approval_id, type(audit_exc).__name__)
        if verified:
            evidence = result.get("message") or result.get("event") or result.get("file") or {}
            evidence_id = evidence.get("id") or evidence.get("htmlLink") or "verified"
            return {"status": "completed", "kind": "approval", "approval_id": approval_id,
                    "reply": f"✅ WORK COMPLETED & VERIFIED\n\nProvider: Google\nOperation: {operation}\nEvidence: {evidence_id}",
                    "result": result}
        return {"status": "unverified", "kind": "approval", "approval_id": approval_id,
                "reply": "⚠️ Google responded, but KZ could not verify the resulting resource. It is marked unverified."}

    if lower in {
        "account status", "check connected accounts", "what accounts are connected",
        "show connected accounts", "check my connections", "monitor account status",
    }:
        return {
            "status": "completed",
            "kind": "account_status",
            "reply": "🧠 KZ checked your connected accounts.\n\n" + _format_accounts(snapshot),
            "result": snapshot,
        }

    if lower.startswith("monitor my account") or lower.startswith("monitor my gmail") or lower.startswith("watch my gmail"):
        account = None
        try:
            from google_connector import _account
            account = _account(uid)
        except Exception:
            account = None
        if not account:
            return {
                "status": "not_connected",
                "kind": "monitor",
                "reply": "🔌 KZ checked the connected-account registry, but no active Google account is available for this user. Connect Google first.",
            }
        _monitor_upsert(uid)
        return {
            "status": "monitoring",
            "kind": "monitor",
            "reply": (
                "👁️ ACCOUNT MONITOR ENABLED\n\n"
                "KZ verified the connected Google account and will monitor Gmail for new unread mail. "
                f"Sleep window: {_SLEEP_START}–{_SLEEP_END} {_sleep_timezone_label()}. "
                "During sleep, important events are buffered; KZ will report them in the morning and ask before taking consequential action."
            ),
            "result": {"provider": "google", "monitor_type": "gmail"},
        }

    if lower.startswith("stop monitoring"):
        _monitor_disable(uid)
        return {
            "status": "stopped",
            "kind": "monitor",
            "reply": "🛑 Account monitoring stopped. KZ will no longer perform background Gmail checks for this account.",
        }

    shopify_intent = _shopify_read_intent(raw, snapshot)
    if shopify_intent:
        try:
            from connector_api import _provider_account, _shopify_request, _shopify_token
            account = _provider_account(uid, "shopify")
            if not account:
                return {
                    "status": "not_connected",
                    "kind": shopify_intent["kind"],
                    "provider": "shopify",
                    "reply": "🔌 KZ checked the account registry: Shopify is not connected to this KZ account.",
                }
            store, token = _shopify_token(uid, "")
            operation = shopify_intent["operation"]
            queries = {
                "shop": "query { shop { id name myshopifyDomain } }",
                "products": "query { products(first: 20) { nodes { id title status handle } } }",
                "orders": "query { orders(first: 20, sortKey: CREATED_AT, reverse: true) { nodes { id name createdAt displayFinancialStatus displayFulfillmentStatus } } }",
            }
            result = _shopify_request(store, token, queries[operation])
            data = result.get("data") or {}
            return {
                "status": "completed",
                "kind": shopify_intent["kind"],
                "provider": "shopify",
                "operation": operation,
                "target": store,
                "reply": _format_shopify_result(data, shopify_intent["kind"]),
                "result": data,
            }
        except Exception as exc:
            logger.warning("Web Shopify read failed: %s", type(exc).__name__)
            detail = getattr(exc, "detail", None)
            return {
                "status": "failed",
                "kind": shopify_intent["kind"],
                "provider": "shopify",
                "reply": "❌ KZ could not complete the Shopify check. No success was claimed."
                        + (f"\nReason: {str(detail)[:220]}" if detail else ""),
                "error": type(exc).__name__,
            }

    gmail_intent = _gmail_read_intent(raw)
    if gmail_intent:
        try:
            from google_connector import _account, _execute
            if not _account(uid):
                return {"status": "not_connected", "kind": gmail_intent["kind"],
                        "reply": "🔌 KZ checked the account registry: Gmail is not connected to this KZ account."}
            result = _execute(uid, "list_gmail", {"query": gmail_intent["query"], "limit": 10})
            reply = _format_gmail_count(result, gmail_intent["kind"]) if gmail_intent["kind"].endswith("count") else _format_gmail_result(result)
            return {"status": "completed", "kind": gmail_intent["kind"], "reply": reply, "result": result}
        except Exception as exc:
            logger.warning("Web Gmail read failed: %s", type(exc).__name__)
            return {"status": "failed", "kind": gmail_intent["kind"],
                    "reply": "❌ KZ could not complete the Gmail check. No success was claimed.", "error": type(exc).__name__}

    if lower in {"check my drive", "check drive", "show my drive files"}:
        try:
            from google_connector import _account, _execute
            if not _account(uid):
                return {"status": "not_connected", "kind": "drive_read",
                        "reply": "🔌 KZ checked the account registry: Google Drive is not connected."}
            result = _execute(uid, "list_drive", {"query": "trashed = false", "limit": 10})
            files = result.get("files") or []
            lines = ["📁 DRIVE CHECK COMPLETE", ""]
            lines.extend(f"• {x.get('name') or '(unnamed)'} — {x.get('mimeType') or ''}" for x in files[:10])
            if not files:
                lines.append("No files found.")
            return {"status": "completed", "kind": "drive_read", "reply": "\n".join(lines), "result": result}
        except Exception as exc:
            return {"status": "failed", "kind": "drive_read",
                    "reply": "❌ KZ could not complete the Drive check. No success was claimed.", "error": type(exc).__name__}

    if lower in {"check my calendar", "check calendar", "what is on my calendar", "show my calendar"}:
        try:
            from google_connector import _account, _execute
            if not _account(uid):
                return {"status": "not_connected", "kind": "calendar_read",
                        "reply": "🔌 KZ checked the account registry: Google Calendar is not connected."}
            result = _execute(uid, "list_calendar", {"limit": 10})
            events = result.get("events") or []
            lines = ["🗓️ CALENDAR CHECK COMPLETE", ""]
            lines.extend(f"• {x.get('summary') or '(untitled)'} — {x.get('start') or ''}" for x in events[:10])
            if not events:
                lines.append("No upcoming events found.")
            return {"status": "completed", "kind": "calendar_read", "reply": "\n".join(lines), "result": result}
        except Exception as exc:
            return {"status": "failed", "kind": "calendar_read",
                    "reply": "❌ KZ could not complete the Calendar check. No success was claimed.", "error": type(exc).__name__}

    payload = _parse_email_request(raw)
    if payload:
        result = _send_gmail_preview(uid, payload)
        if result.get("status") == "not_connected":
            return {
                "status": "not_connected", "kind": "send_gmail",
                "reply": "🔌 KZ checked the account registry: Gmail is not connected to this KZ account."
            }
        return {
            **result,
            "kind": "send_gmail",
            "reply": (
                "✉️ EMAIL PREPARED\n\n"
                f"To: {payload['to']}\n"
                f"Subject: {payload['subject']}\n"
                f"Message: {payload['body']}\n\n"
                f"🛡️ Permission required before sending. Approval ID: {result['approval_id']}. "
                "Approve this exact action; KZ will then send it through Google and report verified evidence."
            ),
            "connector_action": {
                "provider": "google",
                "operation": "send_gmail",
                "status": "waiting_for_approval",
                "approval_id": result["approval_id"],
                "target": payload["to"],
                "payload": payload,
            },
        }

    return None


def _sleep_timezone_label() -> str:
    return os.getenv("KZ_TIMEZONE", "Africa/Lagos")

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


async def account_monitor_job(context: Any) -> None:
    """Background account watcher: immediate daytime feedback, morning buffering during sleep."""
    try:
        events = await _run_sync(monitor_tick)
        if not events:
            return
        from neon_memory import NeonMemory
        mem = NeonMemory()
        with mem.lock:
            conn = mem._connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT platform,external_id,user_id FROM kz_memory_identities WHERE platform='telegram'")
                identities = cur.fetchall() or []
            finally:
                conn.close()
        targets = {}
        for row in identities:
            raw_user = str(row[2] or "")
            if raw_user.startswith("web:"):
                raw_user = raw_user[4:]
            targets[raw_user] = str(row[1])
        for event in events:
            if event.get("sleep_buffered"):
                continue
            chat_id = targets.get(str(event.get("user_id") or ""))
            if not chat_id:
                continue
            items = event.get("items") or []
            await context.bot.send_message(
                chat_id=chat_id,
                text="👁️ <b>KZ ACCOUNT MONITOR</b>\n\n"
                     f"Google Gmail: {len(items)} new unread message(s) detected.\n"
                     "KZ has not replied, sent, deleted, or modified anything.\n"
                     "Say <code>CHECK MY EMAIL</code> to inspect them.",
                parse_mode="HTML",
            )
    except Exception as exc:
        logger.warning("Account monitor job failed: %s", exc)



def html_escape(value: Any) -> str:
    import html
    return html.escape(str(value or ""))
