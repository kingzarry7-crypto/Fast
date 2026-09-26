"""Stripe web billing + admin stats for King Zarry AI."""
from __future__ import annotations

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from database import get_db_cursor, is_database_configured

logger = logging.getLogger("king_zarry_billing")

STRIPE_SECRET_KEY = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
STRIPE_WEBHOOK_SECRET = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
ADMIN_EMAILS = {
    e.strip().lower()
    for e in (os.getenv("ADMIN_EMAILS") or os.getenv("ADMIN_EMAIL") or "").split(",")
    if e.strip()
}
FRONTEND_URL = (
    os.getenv("FRONTEND_URL") or os.getenv("FRONTEND_ORIGIN") or "http://localhost:3000"
).strip().rstrip("/")

STRIPE_AMOUNT_MONTHLY = int(os.getenv("STRIPE_AMOUNT_MONTHLY", "999"))
STRIPE_AMOUNT_QUARTERLY = int(os.getenv("STRIPE_AMOUNT_QUARTERLY", "2499"))
STRIPE_AMOUNT_YEARLY = int(os.getenv("STRIPE_AMOUNT_YEARLY", "7999"))

WEB_PLAN_CATALOG = {
    "monthly": {"name": "Monthly VIP", "days": 30, "amount": STRIPE_AMOUNT_MONTHLY},
    "quarterly": {"name": "90-Day VIP", "days": 90, "amount": STRIPE_AMOUNT_QUARTERLY},
    "3month": {"name": "90-Day VIP", "days": 90, "amount": STRIPE_AMOUNT_QUARTERLY},
    "yearly": {"name": "Yearly VIP", "days": 365, "amount": STRIPE_AMOUNT_YEARLY},
}

_row_value: Optional[Callable] = None
_require_current_user: Optional[Callable] = None
_redact: Optional[Callable] = None


def _rv(row: Any, key: str, index: int = 0) -> Any:
    if _row_value:
        return _row_value(row, key, index)
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[index]
    except Exception:
        return None


def _ensure_billing_tables() -> None:
    if not is_database_configured():
        return
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_subscriptions (
                    user_id TEXT PRIMARY KEY,
                    plan TEXT,
                    is_subscribed BOOLEAN NOT NULL DEFAULT FALSE,
                    stripe_customer_id TEXT,
                    stripe_subscription_id TEXT,
                    expires_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS web_payments (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT,
                    email TEXT,
                    plan TEXT,
                    amount_cents INTEGER,
                    currency TEXT DEFAULT 'usd',
                    stripe_session_id TEXT,
                    stripe_payment_intent TEXT,
                    status TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
    except Exception as exc:
        logger.warning("ensure billing tables failed: %s", type(exc).__name__)


def get_web_subscription(user_id: str) -> Dict[str, Any]:
    out = {"is_subscribed": False, "plan": None, "expires_at": None}
    if not user_id or not is_database_configured():
        return out
    try:
        _ensure_billing_tables()
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT plan, is_subscribed, expires_at
                FROM web_subscriptions WHERE user_id = %s LIMIT 1
                """,
                (str(user_id),),
            )
            row = cur.fetchone()
        if not row:
            return out
        plan = _rv(row, "plan", 0)
        is_sub = _rv(row, "is_subscribed", 1)
        exp = _rv(row, "expires_at", 2)
        active = bool(is_sub)
        if exp is not None:
            try:
                if hasattr(exp, "tzinfo") and exp.tzinfo is None:
                    exp_aware = exp.replace(tzinfo=timezone.utc)
                else:
                    exp_aware = exp
                if exp_aware < datetime.now(timezone.utc):
                    active = False
            except Exception:
                pass
        out["is_subscribed"] = active
        out["plan"] = plan
        out["expires_at"] = str(exp) if exp is not None else None
        return out
    except Exception as exc:
        logger.warning("get web subscription failed: %s", type(exc).__name__)
        return out


def _activate_web_subscription(
    user_id: str,
    plan: str,
    days: int,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> None:
    _ensure_billing_tables()
    expires = datetime.now(timezone.utc) + timedelta(days=max(1, days))
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_subscriptions (
                user_id, plan, is_subscribed, stripe_customer_id,
                stripe_subscription_id, expires_at, updated_at
            ) VALUES (%s, %s, TRUE, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                is_subscribed = TRUE,
                stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, web_subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, web_subscriptions.stripe_subscription_id),
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
            """,
            (str(user_id), plan, stripe_customer_id, stripe_subscription_id, expires),
        )


def _record_web_payment(
    user_id: str,
    email: str,
    plan: str,
    amount_cents: int,
    session_id: str,
    payment_intent: Optional[str],
    status: str,
) -> None:
    _ensure_billing_tables()
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO web_payments (
                user_id, email, plan, amount_cents, currency,
                stripe_session_id, stripe_payment_intent, status
            ) VALUES (%s, %s, %s, %s, 'usd', %s, %s, %s)
            """,
            (str(user_id), email, plan, amount_cents, session_id, payment_intent, status),
        )


def _is_admin_email(email: Optional[str]) -> bool:
    if not email or not ADMIN_EMAILS:
        return False
    return str(email).strip().lower() in ADMIN_EMAILS


class CheckoutRequest(BaseModel):
    plan: str = Field(..., min_length=2, max_length=32)


def install_billing(app: FastAPI, row_value=None, require_user=None, redact=None) -> None:
    global _row_value, _require_current_user, _redact
    _row_value = row_value
    _require_current_user = require_user
    _redact = redact or (lambda s: str(s)[:200])

    @app.post("/api/billing/create-checkout-session")
    async def create_checkout_session(payload: CheckoutRequest, request: Request):
        if not STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=503,
                detail="Stripe is not configured. Set STRIPE_SECRET_KEY on the API server.",
            )
        if not _require_current_user:
            raise HTTPException(status_code=500, detail="Auth not wired")
        user_row = await asyncio.to_thread(_require_current_user, request)
        user_id = str(_rv(user_row, "id", 0))
        email = str(_rv(user_row, "email", 1) or "")
        plan_key = (payload.plan or "").strip().lower()
        if plan_key not in WEB_PLAN_CATALOG:
            raise HTTPException(status_code=400, detail="Invalid plan")
        plan = WEB_PLAN_CATALOG[plan_key]
        success_url = f"{FRONTEND_URL}/settings?checkout=success&plan={plan_key}"
        cancel_url = f"{FRONTEND_URL}/pricing?checkout=cancel"

        def _create():
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            return stripe.checkout.Session.create(
                mode="payment",
                customer_email=email or None,
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": plan["amount"],
                            "product_data": {
                                "name": f"King Zarry AI — {plan['name']}",
                                "description": f"{plan['days']} days VIP web access",
                            },
                        },
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": user_id,
                    "plan": plan_key,
                    "days": str(plan["days"]),
                },
                client_reference_id=user_id,
            )

        try:
            session = await asyncio.to_thread(_create)
        except Exception as exc:
            logger.error("Stripe checkout failed: %s: %s", type(exc).__name__, _redact(str(exc)))
            raise HTTPException(status_code=500, detail="Could not start Stripe checkout")
        return {
            "status": "success",
            "checkout_url": session.url,
            "session_id": session.id,
        }

    @app.post("/api/billing/webhook")
    async def stripe_webhook(request: Request):
        if not STRIPE_SECRET_KEY:
            raise HTTPException(status_code=503, detail="Stripe not configured")
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")

        def _handle():
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
            else:
                event = stripe.Event.construct_from(json.loads(payload.decode("utf-8")), STRIPE_SECRET_KEY)
            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                meta = session.get("metadata") or {}
                user_id = meta.get("user_id") or session.get("client_reference_id")
                plan = (meta.get("plan") or "monthly").lower()
                days = int(meta.get("days") or WEB_PLAN_CATALOG.get(plan, {}).get("days", 30))
                email = (
                    (session.get("customer_details") or {}).get("email")
                    or session.get("customer_email")
                    or ""
                )
                amount = int(session.get("amount_total") or 0)
                if user_id:
                    _activate_web_subscription(
                        str(user_id),
                        plan,
                        days,
                        stripe_customer_id=session.get("customer"),
                        stripe_subscription_id=session.get("subscription"),
                    )
                    _record_web_payment(
                        str(user_id),
                        email,
                        plan,
                        amount,
                        session.get("id") or "",
                        session.get("payment_intent"),
                        "paid",
                    )
            return {"received": True}

        try:
            return await asyncio.to_thread(_handle)
        except Exception as exc:
            logger.error("Stripe webhook error: %s: %s", type(exc).__name__, _redact(str(exc)))
            raise HTTPException(status_code=400, detail="Webhook error")

    @app.get("/api/admin/stats")
    async def admin_stats(request: Request):
        if not _require_current_user:
            raise HTTPException(status_code=500, detail="Auth not wired")
        user_row = await asyncio.to_thread(_require_current_user, request)
        email = str(_rv(user_row, "email", 1) or "")
        if not _is_admin_email(email):
            raise HTTPException(status_code=403, detail="Admin access required")
        _ensure_billing_tables()

        def _load():
            with get_db_cursor(commit=False) as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM web_subscriptions
                    WHERE is_subscribed = TRUE
                      AND (expires_at IS NULL OR expires_at > NOW())
                    """
                )
                active = _rv(cur.fetchone(), "c", 0) or 0
                cur.execute(
                    "SELECT COUNT(*) AS c, COALESCE(SUM(amount_cents),0) AS s FROM web_payments WHERE status = 'paid'"
                )
                pay = cur.fetchone()
                payments = _rv(pay, "c", 0) or 0
                revenue_cents = _rv(pay, "s", 1) or 0
                cur.execute(
                    """
                    SELECT email, plan, amount_cents, status, created_at
                    FROM web_payments ORDER BY created_at DESC LIMIT 50
                    """
                )
                rows = cur.fetchall() or []
            recent = []
            for r in rows:
                recent.append(
                    {
                        "email": _rv(r, "email", 0),
                        "plan": _rv(r, "plan", 1),
                        "amount_cents": _rv(r, "amount_cents", 2),
                        "status": _rv(r, "status", 3),
                        "created_at": str(_rv(r, "created_at", 4)),
                    }
                )
            return {
                "status": "success",
                "active_subscribers": int(active),
                "payments_count": int(payments),
                "revenue_cents": int(revenue_cents),
                "revenue_usd": round(int(revenue_cents) / 100.0, 2),
                "recent_payments": recent,
            }

        try:
            return await asyncio.to_thread(_load)
        except Exception as exc:
            logger.error("admin stats failed: %s", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Could not load admin stats")

    logger.info("Stripe billing routes installed")
