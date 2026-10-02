"""Admin Resend email broadcast routes (installed into FastAPI app)."""
from __future__ import annotations

import asyncio
import html as html_lib
import logging
import os
from typing import Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("king_zarry_api")


class AdminEmailBroadcastRequest(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=20000)
    audience: str = Field(default="active", max_length=32)
    html: Optional[str] = Field(default=None, max_length=50000)


def install_email_broadcast(
    app,
    *,
    require_admin,
    get_db_cursor,
    row_value,
    send_email_resend,
    resend_api_key: str,
    email_from: str,
):
    @app.post("/api/admin/email-broadcast")
    async def admin_email_broadcast(request: Request, body: AdminEmailBroadcastRequest):
        admin_row, admin_email = await asyncio.to_thread(require_admin, request)
        _ = admin_row

        if not resend_api_key:
            raise HTTPException(
                status_code=503,
                detail="RESEND_API_KEY not set on Railway — cannot send email",
            )
        if not email_from or "onboarding@resend.dev" in email_from.lower():
            raise HTTPException(
                status_code=503,
                detail="Set EMAIL_FROM to your verified domain, e.g. King Zarry AI <noreply@kingzarryai.online>",
            )

        subject = (body.subject or "").strip()
        message = (body.message or "").strip()
        audience = (body.audience or "active").strip().lower()
        if audience not in ("active", "all", "subscribers"):
            raise HTTPException(status_code=400, detail="audience must be active, all, or subscribers")
        if not subject or not message:
            raise HTTPException(status_code=400, detail="subject and message required")

        safe_subject = html_lib.escape(subject)
        safe_body = html_lib.escape(message).replace("\n", "<br/>")
        html_body = (body.html or "").strip() or (
            "<!DOCTYPE html>"
            '<html><body style="margin:0;padding:0;background:#0b1220;font-family:system-ui,sans-serif;color:#e2e8f0;">' 
            '<div style="max-width:560px;margin:24px auto;padding:28px;background:#111827;border-radius:12px;border:1px solid #1e3a5f;">' 
            '<p style="margin:0 0 8px;font-size:12px;letter-spacing:0.15em;color:#22d3ee;text-transform:uppercase;">King Zarry AI</p>'
            f'<h1 style="margin:0 0 16px;font-size:22px;color:#fff;">{safe_subject}</h1>'
            f'<div style="font-size:15px;line-height:1.6;color:#cbd5e1;">{safe_body}</div>'
            '<p style="margin:24px 0 0;font-size:11px;color:#64748b;">Not financial advice. Trading involves risk.</p>'
            "</div></body></html>"
        )
        text_body = message

        def _recipients():
            emails = []
            with get_db_cursor(commit=False) as cur:
                if audience == "all":
                    cur.execute(
                        """
                        SELECT email FROM web_users
                        WHERE email IS NOT NULL AND email <> ''
                          AND COALESCE(account_status, 'active') NOT IN ('banned', 'suspended')
                        ORDER BY created_at DESC NULLS LAST
                        LIMIT 500
                        """
                    )
                elif audience == "subscribers":
                    try:
                        cur.execute(
                            """
                            SELECT DISTINCT u.email
                            FROM web_users u
                            LEFT JOIN web_subscriptions s ON s.user_id = u.id
                            WHERE u.email IS NOT NULL AND u.email <> ''
                              AND COALESCE(u.account_status, 'active') NOT IN ('banned', 'suspended')
                              AND (
                                COALESCE(u.is_subscribed, FALSE) = TRUE
                                OR (s.status = 'active' AND (s.expires_at IS NULL OR s.expires_at > NOW()))
                              )
                            LIMIT 500
                            """
                        )
                    except Exception:
                        cur.execute(
                            """
                            SELECT email FROM web_users
                            WHERE email IS NOT NULL AND email <> ''
                              AND COALESCE(account_status, 'active') = 'active'
                            ORDER BY last_login_at DESC NULLS LAST
                            LIMIT 200
                            """
                        )
                else:
                    cur.execute(
                        """
                        SELECT email FROM web_users
                        WHERE email IS NOT NULL AND email <> ''
                          AND COALESCE(account_status, 'active') = 'active'
                        ORDER BY last_login_at DESC NULLS LAST, created_at DESC NULLS LAST
                        LIMIT 500
                        """
                    )
                for r in cur.fetchall() or []:
                    em = str(row_value(r, "email", 0) or "").strip().lower()
                    if em and "@" in em:
                        emails.append(em)
            seen = set()
            out = []
            for e in emails:
                if e not in seen:
                    seen.add(e)
                    out.append(e)
            return out

        try:
            recipients = await asyncio.to_thread(_recipients)
        except Exception as exc:
            logger.error("email-broadcast recipient query failed: %s", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Could not load recipients")

        if not recipients:
            return {
                "status": "success",
                "sent": 0,
                "failed": 0,
                "total": 0,
                "message": "No matching recipients",
                "audience": audience,
            }

        max_send = int(os.getenv("ADMIN_EMAIL_BROADCAST_MAX", "100") or "100")
        max_send = max(1, min(max_send, 300))
        recipients = recipients[:max_send]

        sent = 0
        failed = 0
        for em in recipients:
            ok = await asyncio.to_thread(send_email_resend, em, subject, text_body, html_body)
            if ok:
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.35)

        logger.info(
            "admin email-broadcast by %s audience=%s sent=%s failed=%s total=%s",
            admin_email,
            audience,
            sent,
            failed,
            len(recipients),
        )
        return {
            "status": "success",
            "sent": sent,
            "failed": failed,
            "total": len(recipients),
            "audience": audience,
            "from": email_from,
            "message": f"Broadcast finished: {sent} sent, {failed} failed",
        }

    return admin_email_broadcast
