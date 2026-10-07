            cur.execute(
                """SELECT id,operation,target,exact_content,action_fingerprint,status
                   FROM web_approvals
                   WHERE id IN (SELECT id FROM web_approvals
                                WHERE user_id=%s AND service='google' AND operation='send_gmail'
                                  AND status='pending')
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
        if lower == "reject":
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