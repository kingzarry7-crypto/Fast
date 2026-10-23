from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def ensure_delivery_table(conn: sqlite3.Connection) -> None:
    """Create durable per-recipient alert deduplication state."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kitty_watch_deliveries (
            symbol TEXT NOT NULL,
            candle_time TEXT NOT NULL,
            recipient_id TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            PRIMARY KEY (symbol, candle_time, recipient_id)
        )
        """
    )
    conn.commit()


def is_delivered(
    conn: sqlite3.Connection, symbol: str, candle_time: str, recipient_id: str
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM kitty_watch_deliveries "
        "WHERE symbol=? AND candle_time=? AND recipient_id=?",
        (str(symbol), str(candle_time), str(recipient_id)),
    ).fetchone()
    return row is not None


def mark_delivered(
    conn: sqlite3.Connection, symbol: str, candle_time: str, recipient_id: str
) -> None:
    """Record only successful deliveries; repeated writes are idempotent."""
    conn.execute(
        "INSERT INTO kitty_watch_deliveries "
        "(symbol, candle_time, recipient_id, sent_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(symbol, candle_time, recipient_id) DO NOTHING",
        (
            str(symbol),
            str(candle_time),
            str(recipient_id),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def all_recipients_delivered(
    conn: sqlite3.Connection,
    symbol: str,
    candle_time: str,
    recipients: list[str],
) -> bool:
    """True only when every configured recipient already received this candle alert."""
    if not recipients:
        return False
    return all(
        is_delivered(conn, symbol, candle_time, str(recipient))
        for recipient in recipients
    )
