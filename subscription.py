import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional


# =========================================================
# 👑 KING ZARRY AI
# SUBSCRIPTION + PAYMENT DATABASE
# =========================================================

# IMPORTANT:
# Use the SAME database as telegram_bot.py.
#
# Recommended Railway/Render variable:
#
# DATABASE_PATH=king_zarry.db
#
# Do NOT use a separate subscriptions.db unless you
# intentionally want a separate database.
DATABASE = os.getenv("DATABASE_PATH", "king_zarry.db")


# =========================================================
# ADMIN IDS
# =========================================================

def load_admin_ids() -> list[int]:
    """
    Reads:
        ADMIN_IDS=123456789,987654321
    """

    ids = []

    for value in os.getenv("ADMIN_IDS", "").split(","):
        value = value.strip()

        if not value:
            continue

        try:
            ids.append(int(value))
        except ValueError:
            print(f"⚠️ Invalid ADMIN_IDS value ignored: {value}")

    return ids


ADMIN_IDS = load_admin_ids()


# =========================================================
# SUBSCRIPTION DURATIONS
# =========================================================

MONTHLY_DAYS = 30
THREE_MONTH_DAYS = 90
YEARLY_DAYS = 365


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a reliable SQLite connection.
    """

    conn = sqlite3.connect(
        DATABASE,
        timeout=30.0,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    # Wait up to 30 seconds if another operation has the DB locked.
    conn.execute("PRAGMA busy_timeout = 30000")

    # Better concurrent read/write behavior.
    conn.execute("PRAGMA journal_mode = WAL")

    # Foreign-key enforcement.
    conn.execute("PRAGMA foreign_keys = ON")

    # Good balance between durability and performance.
    conn.execute("PRAGMA synchronous = NORMAL")

    return conn


# =========================================================
# TIME HELPERS
# =========================================================

def utc_now() -> datetime:
    """
    Current UTC time.
    """
    return datetime.now(timezone.utc)


def parse_iso_datetime(
    dt_str: Optional[str],
) -> Optional[datetime]:
    """
    Safely parse an ISO datetime and return UTC-aware datetime.
    """

    if not dt_str:
        return None

    try:
        dt = datetime.fromisoformat(str(dt_str))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return dt

    except (TypeError, ValueError):
        return None


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_subscription_db():
    """
    Create subscription/payment tables and indexes.

    Safe to call every time the bot starts.
    """

    with get_connection() as conn:

        # -------------------------------------------------
        # SUBSCRIPTIONS
        # -------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                status TEXT NOT NULL DEFAULT 'inactive',
                plan TEXT NOT NULL DEFAULT 'free',
                expires_at TEXT,
                payment_method TEXT,
                last_payment_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

        # -------------------------------------------------
        # PAYMENTS
        # -------------------------------------------------

        conn.execute(
            """
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
            """
        )

        # -------------------------------------------------
        # INDEXES
        # -------------------------------------------------

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_subscriptions_status
            ON subscriptions(status)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_subscriptions_expires
            ON subscriptions(expires_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_payments_user
            ON payments(user_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_payments_created
            ON payments(created_at)
            """
        )

        conn.commit()

    print(f"✅ Subscription database ready: {DATABASE}")


# =========================================================
# SUBSCRIPTION CHECK
# =========================================================

def is_subscribed(user_id: int) -> bool:
    """
    Check whether a user currently has an active subscription.

    Admins automatically have access.
    """

    user_id = int(user_id)

    # Admin bypass.
    if user_id in ADMIN_IDS:
        return True

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT status, expires_at
            FROM subscriptions
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    if not row:
        return False

    status = row["status"]
    expires_at = row["expires_at"]

    if status != "active":
        return False

    expiry = parse_iso_datetime(expires_at)

    if expiry is None:
        return False

    # Automatically expire subscriptions.
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
    payment_id: Optional[str] = None,
) -> datetime:
    """
    Activate a subscription or extend an existing subscription.

    If the user still has time remaining, the new days are
    added to the existing expiration date.
    """

    user_id = int(user_id)

    username = str(username or "")
    plan = str(plan or "VIP")
    payment_method = str(payment_method or "admin")

    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("days must be an integer")

    if days <= 0:
        raise ValueError("days must be greater than zero")

    now = utc_now()

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT expires_at
            FROM subscriptions
            WHERE user_id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

        existing_expiry = None

        if row and row["expires_at"]:
            existing_expiry = parse_iso_datetime(
                row["expires_at"]
            )

        # Extend existing subscription.
        if existing_expiry and existing_expiry > now:
            expires_at = (
                existing_expiry +
                timedelta(days=days)
            )

        # Otherwise start from now.
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
            VALUES (
                ?,
                ?,
                'active',
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )

            ON CONFLICT(user_id)
            DO UPDATE SET
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
            ),
        )

        conn.commit()

    return expires_at


# =========================================================
# ACTIVATE UNTIL EXACT DATE
# =========================================================

def activate_until(
    user_id: int,
    username: str,
    expires_at: datetime,
    plan: str = "VIP",
    payment_method: str = "admin",
    payment_id: Optional[str] = None,
) -> datetime:
    """
    Activate a subscription until an exact date/time.
    """

    user_id = int(user_id)

    username = str(username or "")
    plan = str(plan or "VIP")
    payment_method = str(payment_method or "admin")

    if not isinstance(expires_at, datetime):
        raise TypeError(
            "expires_at must be a datetime"
        )

    # Force UTC.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )
    else:
        expires_at = expires_at.astimezone(
            timezone.utc
        )

    now = utc_now()

    if expires_at <= now:
        raise ValueError(
            "expires_at must be in the future"
        )

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
            VALUES (
                ?,
                ?,
                'active',
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )

            ON CONFLICT(user_id)
            DO UPDATE SET
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
            ),
        )

        conn.commit()

    return expires_at


# =========================================================
# DEACTIVATE
# =========================================================

def deactivate_subscription(user_id: int):
    """
    Mark a subscription inactive.
    """

    with get_connection() as conn:

        conn.execute(
            """
            UPDATE subscriptions
            SET
                status = 'inactive',
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                utc_now().isoformat(),
                int(user_id),
            ),
        )

        conn.commit()


# =========================================================
# GET SUBSCRIPTION
# =========================================================

def get_subscription(
    user_id: int,
) -> Optional[dict]:
    """
    Get complete subscription information.
    """

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
                last_payment_id,
                created_at,
                updated_at
            FROM subscriptions
            WHERE user_id = ?
            LIMIT 1
            """,
            (int(user_id),),
        ).fetchone()

    if not row:
        return None

    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "status": row["status"],
        "plan": row["plan"],
        "expires_at": row["expires_at"],
        "payment_method": row["payment_method"],
        "last_payment_id": row["last_payment_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
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
    """
    Record a successful payment.

    Returns:
        True  = newly recorded
        False = payment already exists
    """

    if not payment_id:
        raise ValueError(
            "payment_id is required"
        )

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
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    int(user_id),
                    str(username or ""),
                    str(plan or ""),
                    str(payment_method or ""),
                    str(payment_id),
                    int(amount),
                    str(currency or ""),
                    str(payload or ""),
                    utc_now().isoformat(),
                ),
            )

            conn.commit()

        return True

    except sqlite3.IntegrityError as e:

        # Duplicate Telegram payment.
        if "payment_id" in str(e).lower():
            return False

        raise


# =========================================================
# PAYMENT HISTORY
# =========================================================

def get_payment_history(
    user_id: int,
    limit: int = 10,
) -> list:
    """
    Get recent payments for a user.
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 10

    # Prevent huge queries.
    limit = max(1, min(limit, 100))

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                plan,
                payment_method,
                payment_id,
                amount,
                currency,
                payload,
                created_at
            FROM payments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                int(user_id),
                limit,
            ),
        ).fetchall()

    return [dict(row) for row in rows]


# =========================================================
# ACTIVE SUBSCRIBERS
# =========================================================

def get_active_subscribers() -> list:
    """
    Return only currently active subscribers.
    """

    now = utc_now()

    with get_connection() as conn:

        rows = conn.execute(
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
            WHERE status = 'active'
            ORDER BY expires_at ASC
            """
        ).fetchall()

    subscribers = []

    for row in rows:

        expiry = parse_iso_datetime(
            row["expires_at"]
        )

        if expiry and expiry > now:

            subscribers.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "status": row["status"],
                "plan": row["plan"],
                "expires_at": row["expires_at"],
                "payment_method": row["payment_method"],
                "last_payment_id": row["last_payment_id"],
            })

    return subscribers


# =========================================================
# ALL SUBSCRIPTIONS
# =========================================================

def get_all_subscriptions() -> list:
    """
    Return all subscription records.
    """

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                user_id,
                username,
                status,
                plan,
                expires_at,
                payment_method,
                last_payment_id,
                created_at,
                updated_at
            FROM subscriptions
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


# =========================================================
# PAYMENT STATS
# =========================================================

def get_payment_stats() -> dict:
    """
    Payment totals.
    """

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_payments,
                COALESCE(SUM(amount), 0) AS total_amount
            FROM payments
            """
        ).fetchone()

    return {
        "total_payments": int(
            row["total_payments"]
        ),
        "total_amount": int(
            row["total_amount"]
        ),
    }


# =========================================================
# SUBSCRIPTION STATS
# =========================================================

def get_subscription_stats() -> dict:
    """
    Return active, expired and inactive counts.
    """

    now = utc_now()

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                status,
                expires_at
            FROM subscriptions
            """
        ).fetchall()

    active = 0
    expired = 0
    inactive = 0

    for row in rows:

        status = row["status"]

        expiry = parse_iso_datetime(
            row["expires_at"]
        )

        if (
            status == "active"
            and expiry
            and expiry > now
        ):
            active += 1

        elif (
            status == "active"
            and expiry
            and expiry <= now
        ):
            expired += 1

        else:
            inactive += 1

    return {
        "total_subscriptions": len(rows),
        "active": active,
        "expired": expired,
        "inactive": inactive,
    }


# =========================================================
# EXPIRE OLD SUBSCRIPTIONS
# =========================================================

def expire_old_subscriptions() -> int:
    """
    Mark all expired active subscriptions as inactive.

    Returns number of subscriptions changed.
    """

    now = utc_now().isoformat()

    with get_connection() as conn:

        cursor = conn.execute(
            """
            UPDATE subscriptions
            SET
                status = 'inactive',
                updated_at = ?
            WHERE status = 'active'
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (
                now,
                now,
            ),
        )

        conn.commit()

        return cursor.rowcount


# =========================================================
# DATABASE HEALTH CHECK
# =========================================================

def database_health_check() -> bool:
    """
    Check that SQLite is working.
    """

    try:

        with get_connection() as conn:
            conn.execute("SELECT 1")

        return True

    except Exception as e:

        print(
            f"❌ Subscription DB health check failed: {e}"
        )

        return False


# =========================================================
# AUTOMATIC INITIALIZATION
# =========================================================

# This is important.
#
# The database is initialized even when this module is
# imported by telegram_bot.py.
try:
    init_subscription_db()
except Exception as e:
    print(
        f"❌ Subscription DB initialization failed: {e}"
    )


# =========================================================
# DIRECT EXECUTION
# =========================================================

if __name__ == "__main__":

    print("")
    print("👑 KING ZARRY AI")
    print("Subscription database")
    print("--------------------------------")
    print(f"Database: {DATABASE}")
    print(f"Admins: {len(ADMIN_IDS)}")
    print(
        f"Healthy: {database_health_check()}"
    )
    print(
        f"Subscriptions: {get_subscription_stats()}"
    )
    print(
        f"Payments: {get_payment_stats()}"
    )
    print("")
