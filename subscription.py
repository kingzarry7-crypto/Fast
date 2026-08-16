import os
import sqlite3
from datetime import datetime, timedelta, timezone

# =========================================================
# 👑 KING ZARRY AI - SUBSCRIPTION + PAYMENT DATABASE
# =========================================================

DATABASE = os.getenv("SUBSCRIPTION_DATABASE", "subscriptions.db")

ADMIN_IDS = [
    int(i)
    for i in os.environ.get("ADMIN_IDS", "").split(",")
    if i.strip().isdigit()
]

MONTHLY_DAYS = 30
THREE_MONTH_DAYS = 90
YEARLY_DAYS = 365


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DATABASE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_subscription_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                status TEXT NOT NULL DEFAULT 'inactive',
                plan TEXT DEFAULT 'free',
                expires_at TEXT,
                payment_method TEXT,
                last_payment_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                plan TEXT,
                payment_method TEXT,
                payment_id TEXT UNIQUE,
                amount INTEGER,
                currency TEXT,
                payload TEXT,
                created_at TEXT
            )
        """)


# =========================================================
# TIME HELPERS
# =========================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso_datetime(dt_str: str) -> datetime | None:
    """Safely parse ISO datetime string and enforce UTC timezone."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# =========================================================
# SUBSCRIPTION CHECK
# =========================================================

def is_subscribed(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT status, expires_at
            FROM subscriptions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

    if not row:
        return False

    status, expires_at_str = row

    if status != "active" or not expires_at_str:
        return False

    expiry = parse_iso_datetime(expires_at_str)
    if not expiry:
        return False

    if expiry <= utc_now():
        deactivate_subscription(user_id)
        return False

    return True


# =========================================================
# ACTIVATE / EXTEND
# =========================================================

def activate_subscription(
    user_id: int,
    username: str,
    days: int,
    plan: str = "VIP",
    payment_method: str = "admin",
    payment_id: str | None = None,
) -> datetime:
    """
    Activate or extend a subscription.

    If the user already has time remaining,
    the new period is added on top of the existing expiry.
    """
    now = utc_now()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT expires_at
            FROM subscriptions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        existing_expiry = parse_iso_datetime(row[0]) if row and row[0] else None

        if existing_expiry and existing_expiry > now:
            expires_at = existing_expiry + timedelta(days=days)
        else:
            expires_at = now + timedelta(days=days)

        conn.execute(
            """
            INSERT INTO subscriptions (
                user_id,
                username,
                status,
                plan,
                expires_at,
                payment_method,
                last_payment_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                status = 'active',
                plan = excluded.plan,
                expires_at = excluded.expires_at,
                payment_method = excluded.payment_method,
                last_payment_id = excluded.last_payment_id,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                username,
                plan,
                expires_at.isoformat(),
                payment_method,
                payment_id,
                now.isoformat(),
                now.isoformat(),
            )
        )

    return expires_at


# =========================================================
# ACTIVATE UNTIL EXACT DATE
# =========================================================

def activate_until(
    user_id: int,
    username: str,
    expires_at: datetime,
    plan: str,
    payment_method: str,
    payment_id: str,
):
    now = utc_now()

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (
                user_id,
                username,
                status,
                plan,
                expires_at,
                payment_method,
                last_payment_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                status = 'active',
                plan = excluded.plan,
                expires_at = excluded.expires_at,
                payment_method = excluded.payment_method,
                last_payment_id = excluded.last_payment_id,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                username,
                plan,
                expires_at.isoformat(),
                payment_method,
                payment_id,
                now.isoformat(),
                now.isoformat(),
            )
        )


# =========================================================
# DEACTIVATE
# =========================================================

def deactivate_subscription(user_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE subscriptions
            SET status = 'inactive',
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                utc_now().isoformat(),
                user_id,
            )
        )


# =========================================================
# GET SUBSCRIPTION
# =========================================================

def get_subscription(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                user_id,
                username,
                status,
                plan,
                expires_at,
                payment_method,
                last_payment_id
            FROM subscriptions
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

    if not row:
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "status": row[2],
        "plan": row[3],
        "expires_at": row[4],
        "payment_method": row[5],
        "last_payment_id": row[6],
    }


# =========================================================
# RECORD PAYMENT
# =========================================================

def record_payment(
    user_id: int,
    username: str,
    plan: str,
    payment_method: str,
    payment_id: str,
    amount: int,
    currency: str,
    payload: str,
) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO payments (
                    user_id,
                    username,
                    plan,
                    payment_method,
                    payment_id,
                    amount,
                    currency,
                    payload,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    plan,
                    payment_method,
                    payment_id,
                    amount,
                    currency,
                    payload,
                    utc_now().isoformat(),
                )
            )
        return True
    except sqlite3.IntegrityError:
        # Payment ID already recorded
        return False


# =========================================================
# PAYMENT HISTORY
# =========================================================

def get_payment_history(user_id: int, limit: int = 10) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                plan,
                payment_method,
                amount,
                currency,
                created_at
            FROM payments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()

    return rows


# Run initialization when module is executed directly
if __name__ == "__main__":
    init_subscription_db()
