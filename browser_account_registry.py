"""Persistent registry for browser-connected accounts shared by Web, Telegram, and Discord.

The live Playwright session remains in the FastAPI process. This table stores only
non-secret connection metadata so other processes can see that the account is
connected without exposing cookies, passwords, or browser state.
"""
from __future__ import annotations
from typing import Any
from database import get_db_cursor

def ensure_table() -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kz_browser_accounts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                account_id VARCHAR(160) NOT NULL,
                display_name VARCHAR(255),
                url TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'login_required',
                verified_at TIMESTAMPTZ,
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                UNIQUE(user_id, account_id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_kz_browser_accounts_user
            ON kz_browser_accounts(user_id, status)
        """)

def upsert_browser_account(user_id: str, account_id: str, *, display_name: str = "",
                           url: str = "", status: str = "login_required",
                           verified: bool = False, metadata: dict[str, Any] | None = None) -> None:
    ensure_table()
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO kz_browser_accounts
                (user_id, account_id, display_name, url, status, verified_at, last_seen_at, metadata)
            VALUES (%s,%s,%s,%s,%s,CASE WHEN %s THEN NOW() ELSE NULL END,NOW(),%s::jsonb)
            ON CONFLICT(user_id, account_id) DO UPDATE SET
                display_name=COALESCE(NULLIF(EXCLUDED.display_name,''), kz_browser_accounts.display_name),
                url=COALESCE(NULLIF(EXCLUDED.url,''), kz_browser_accounts.url),
                status=EXCLUDED.status,
                verified_at=CASE WHEN EXCLUDED.verified_at IS NOT NULL
                                 THEN EXCLUDED.verified_at
                                 ELSE kz_browser_accounts.verified_at END,
                last_seen_at=NOW(),
                metadata=CASE WHEN EXCLUDED.metadata <> '{}'::jsonb
                              THEN EXCLUDED.metadata ELSE kz_browser_accounts.metadata END
        """, (
            str(user_id), str(account_id)[:160], str(display_name or "")[:255],
            str(url or "")[:4000], str(status or "login_required")[:50],
            bool(verified), __import__("json").dumps(metadata or {})
        ))

def list_browser_accounts(user_id: str) -> list[dict[str, Any]]:
    ensure_table()
    with get_db_cursor(commit=False) as cur:
        cur.execute("""
            SELECT account_id, display_name, url, status, verified_at, last_seen_at, metadata
            FROM kz_browser_accounts
            WHERE user_id=%s
            ORDER BY last_seen_at DESC
        """, (str(user_id),))
        rows = cur.fetchall() or []
    out=[]
    for row in rows:
        if hasattr(row, "keys"):
            out.append(dict(row))
        else:
            out.append({
                "account_id": row[0], "display_name": row[1], "url": row[2],
                "status": row[3], "verified_at": row[4], "last_seen_at": row[5], "metadata": row[6],
            })
    return out
