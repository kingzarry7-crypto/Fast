"""Runtime patch: harden /api/admin/stats (missing columns + aborted txn safe)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from fastapi import Request

logger = logging.getLogger("king_zarry_api")


def install_admin_stats_fix(
    app,
    *,
    require_admin,
    get_db_cursor,
    row_value,
    ensure_billing_tables=None,
    is_database_configured=None,
):
    """Replace admin_stats route with a soft-fail implementation."""

    def _json_safe(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (str, int, float, bool)):
            return v
        if hasattr(v, "isoformat"):
            try:
                return v.isoformat()
            except Exception:
                return str(v)
        try:
            if type(v).__name__ == "Decimal":
                return int(v) if v == int(v) else float(v)
        except Exception:
            pass
        return str(v)

    # Drop the stock route so this handler is the one FastAPI uses
    try:
        keep = []
        for route in list(app.router.routes):
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None) or set()
            if path == "/api/admin/stats" and ("GET" in methods or not methods):
                continue
            keep.append(route)
        app.router.routes[:] = keep
    except Exception as e:
        logger.warning("admin stats route replace: %s", type(e).__name__)

    @app.get("/api/admin/stats")
    async def admin_stats_fixed(request: Request):
        user_row, email = require_admin(request)
        _ = user_row

        def _load() -> Dict[str, Any]:
            if ensure_billing_tables:
                try:
                    ensure_billing_tables()
                except Exception:
                    pass
            try:
                with get_db_cursor(commit=True) as cur:
                    cur.execute("ALTER TABLE web_users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE web_users ADD COLUMN IF NOT EXISTS account_status TEXT NOT NULL DEFAULT 'active'")
                    cur.execute("ALTER TABLE web_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE")
            except Exception as e:
                logger.warning("admin stats migrate: %s", type(e).__name__)

            out: Dict[str, Any] = {
                "status": "success",
                "admin_email": str(email or ""),
                "users_total": 0,
                "users_active_7d": 0,
                "users_active_30d": 0,
                "users_new_7d": 0,
                "sessions_active": 0,
                "conversations_total": 0,
                "messages_total": 0,
                "messages_24h": 0,
                "active_subscribers": 0,
                "payments_count": 0,
                "revenue_cents": 0,
                "revenue_usd": 0.0,
                "recent_users": [],
                "recent_payments": [],
            }

            def _safe_count(cur, sql: str, params=()) -> int:
                sp = "sp_admin_cnt"
                try:
                    cur.execute(f"SAVEPOINT {sp}")
                    cur.execute(sql, params)
                    row = cur.fetchone()
                    cur.execute(f"RELEASE SAVEPOINT {sp}")
                    return int(row_value(row, "c", 0) or 0)
                except Exception as e:
                    logger.warning("admin count failed: %s", type(e).__name__)
                    try:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                    except Exception:
                        pass
                    return 0

            try:
                with get_db_cursor(commit=False) as cur:
                    out["users_total"] = _safe_count(cur, "SELECT COUNT(*) AS c FROM web_users")
                    out["users_active_7d"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_users WHERE last_login_at IS NOT NULL AND last_login_at > NOW() - INTERVAL '7 days'",
                    )
                    out["users_active_30d"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_users WHERE last_login_at IS NOT NULL AND last_login_at > NOW() - INTERVAL '30 days'",
                    )
                    out["users_new_7d"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_users WHERE created_at > NOW() - INTERVAL '7 days'",
                    )
                    out["sessions_active"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_sessions WHERE revoked_at IS NULL AND expires_at > NOW()",
                    )
                    out["conversations_total"] = _safe_count(cur, "SELECT COUNT(*) AS c FROM web_conversations")
                    out["messages_total"] = _safe_count(cur, "SELECT COUNT(*) AS c FROM web_messages")
                    out["messages_24h"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_messages WHERE created_at > NOW() - INTERVAL '24 hours'",
                    )
                    out["active_subscribers"] = _safe_count(
                        cur,
                        "SELECT COUNT(*) AS c FROM web_subscriptions WHERE is_subscribed IS TRUE AND (expires_at IS NULL OR expires_at > NOW())",
                    )
                    try:
                        cur.execute("SAVEPOINT sp_rev")
                        cur.execute(
                            "SELECT COALESCE(SUM(amount_cents), 0) AS cents, COUNT(*) AS c FROM web_payments WHERE status = 'paid'"
                        )
                        row = cur.fetchone()
                        cents = int(row_value(row, "cents", 0) or 0)
                        out["revenue_cents"] = cents
                        out["revenue_usd"] = round(cents / 100.0, 2)
                        out["payments_count"] = int(row_value(row, "c", 1) or 0)
                        cur.execute("RELEASE SAVEPOINT sp_rev")
                    except Exception:
                        try:
                            cur.execute("ROLLBACK TO SAVEPOINT sp_rev")
                        except Exception:
                            pass
                    try:
                        cur.execute("SAVEPOINT sp_ru")
                        cur.execute(
                            "SELECT id, email, username, account_status, created_at, last_login_at FROM web_users ORDER BY created_at DESC NULLS LAST LIMIT 30"
                        )
                        for r in cur.fetchall() or []:
                            out["recent_users"].append(
                                {
                                    "id": str(row_value(r, "id", 0) or ""),
                                    "email": _json_safe(row_value(r, "email", 1)),
                                    "username": _json_safe(row_value(r, "username", 2)),
                                    "account_status": _json_safe(row_value(r, "account_status", 3)) or "active",
                                    "created_at": str(row_value(r, "created_at", 4) or ""),
                                    "last_login_at": str(row_value(r, "last_login_at", 5) or ""),
                                }
                            )
                        cur.execute("RELEASE SAVEPOINT sp_ru")
                    except Exception as e:
                        logger.warning("recent users: %s", type(e).__name__)
                        try:
                            cur.execute("ROLLBACK TO SAVEPOINT sp_ru")
                        except Exception:
                            pass
                    try:
                        cur.execute("SAVEPOINT sp_rp")
                        cur.execute(
                            "SELECT email, plan, amount_cents, status, created_at FROM web_payments ORDER BY created_at DESC NULLS LAST LIMIT 50"
                        )
                        for r in cur.fetchall() or []:
                            amt = row_value(r, "amount_cents", 2)
                            try:
                                amt_i = int(amt) if amt is not None else 0
                            except Exception:
                                amt_i = 0
                            out["recent_payments"].append(
                                {
                                    "email": _json_safe(row_value(r, "email", 0)),
                                    "plan": _json_safe(row_value(r, "plan", 1)),
                                    "amount_cents": amt_i,
                                    "status": _json_safe(row_value(r, "status", 3)),
                                    "created_at": str(row_value(r, "created_at", 4) or ""),
                                }
                            )
                        cur.execute("RELEASE SAVEPOINT sp_rp")
                    except Exception:
                        try:
                            cur.execute("ROLLBACK TO SAVEPOINT sp_rp")
                        except Exception:
                            pass
            except Exception as exc:
                logger.error("admin stats db: %s", type(exc).__name__)
            return out

        try:
            return await asyncio.to_thread(_load)
        except Exception as exc:
            logger.error("admin stats failed: %s", type(exc).__name__)
            return {
                "status": "success",
                "admin_email": str(email or ""),
                "users_total": 0,
                "active_subscribers": 0,
                "payments_count": 0,
                "revenue_cents": 0,
                "revenue_usd": 0.0,
                "recent_users": [],
                "recent_payments": [],
                "note": "Partial data unavailable",
            }

    return admin_stats_fixed
