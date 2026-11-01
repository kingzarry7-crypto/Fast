"""Durable account-monitor notifications shared across KZ channels."""
from __future__ import annotations

import json
import uuid
from typing import Any

from database import get_db_cursor


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value or "").strip())
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _ensure_table() -> None:
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kz_account_notifications (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                dedupe_key TEXT UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                telegram_delivered BOOLEAN NOT NULL DEFAULT FALSE,
                discord_delivered BOOLEAN NOT NULL DEFAULT FALSE,
                web_read BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)


def queue_account_notification(
    user_id: str, provider: str, event_type: str, payload: dict[str, Any],
    dedupe_key: str | None = None,
) -> str | None:
    """Persist an event for a linked web user; platform IDs are not UUIDs."""
    if not _is_uuid(user_id):
        return None
    try:
        _ensure_table()
        notification_id = str(uuid.uuid4())
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO kz_account_notifications
                   (id,user_id,provider,event_type,payload,dedupe_key)
                   VALUES(%s,%s,%s,%s,%s::jsonb,%s)
                   ON CONFLICT(dedupe_key) DO UPDATE SET dedupe_key=EXCLUDED.dedupe_key
                   RETURNING id""",
                (notification_id, str(user_id), str(provider), str(event_type),
                 json.dumps(payload, ensure_ascii=False, default=str), dedupe_key),
            )
            row = cur.fetchone()
        if not row:
            return None
        return str(row["id"] if hasattr(row, "keys") else row[0])
    except Exception:
        return None


def pending_account_notifications(user_id: str, channel: str, limit: int = 20) -> list[dict[str, Any]]:
    column = {"telegram": "telegram_delivered", "discord": "discord_delivered"}.get(channel)
    if not column or not _is_uuid(user_id):
        return []
    try:
        _ensure_table()
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                f"""SELECT id,provider,event_type,payload,created_at
                    FROM kz_account_notifications
                    WHERE user_id=%s AND {column}=FALSE
                    ORDER BY created_at ASC LIMIT %s""",
                (str(user_id), max(1, min(int(limit), 50))),
            )
            rows = cur.fetchall() or []
        result = []
        for row in rows:
            item = dict(row) if hasattr(row, "keys") else dict(zip(
                ("id", "provider", "event_type", "payload", "created_at"), row
            ))
            if isinstance(item.get("payload"), str):
                try:
                    item["payload"] = json.loads(item["payload"])
                except Exception:
                    item["payload"] = {}
            result.append(item)
        return result
    except Exception:
        return []


def mark_account_notification_delivered(notification_id: str, channel: str) -> bool:
    column = {"telegram": "telegram_delivered", "discord": "discord_delivered"}.get(channel)
    if not column or not _is_uuid(notification_id):
        return False
    try:
        _ensure_table()
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                f"UPDATE kz_account_notifications SET {column}=TRUE WHERE id=%s",
                (str(notification_id),),
            )
            return bool(cur.rowcount)
    except Exception:
        return False


def list_web_account_notifications(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    if not _is_uuid(user_id):
        return []
    try:
        _ensure_table()
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """SELECT id,provider,event_type,payload,created_at,web_read
                   FROM kz_account_notifications WHERE user_id=%s
                   ORDER BY created_at DESC LIMIT %s""",
                (str(user_id), max(1, min(int(limit), 100))),
            )
            rows = cur.fetchall() or []
        result = []
        for row in rows:
            item = dict(row) if hasattr(row, "keys") else dict(zip(
                ("id", "provider", "event_type", "payload", "created_at", "web_read"), row
            ))
            if isinstance(item.get("payload"), str):
                try:
                    item["payload"] = json.loads(item["payload"])
                except Exception:
                    item["payload"] = {}
            result.append(item)
        return result
    except Exception:
        return []


def mark_web_account_notification_read(user_id: str, notification_id: str) -> bool:
    if not _is_uuid(user_id) or not _is_uuid(notification_id):
        return False
    try:
        _ensure_table()
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE kz_account_notifications SET web_read=TRUE WHERE id=%s AND user_id=%s",
                (str(notification_id), str(user_id)),
            )
            return bool(cur.rowcount)
    except Exception:
        return False

def users_with_pending_account_notifications(channel: str, limit: int = 100) -> list[str]:
    column = {"telegram": "telegram_delivered", "discord": "discord_delivered"}.get(channel)
    if not column:
        return []
    try:
        _ensure_table()
        with get_db_cursor(commit=False) as cur:
            cur.execute(
                f"SELECT DISTINCT user_id FROM kz_account_notifications WHERE {column}=FALSE ORDER BY user_id LIMIT %s",
                (max(1, min(int(limit), 500)),),
            )
            rows = cur.fetchall() or []
        return [str(row["user_id"] if hasattr(row, "keys") else row[0]) for row in rows]
    except Exception:
        return []
