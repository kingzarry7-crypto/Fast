"""
👑 KING ZARRY AI
Telegram Notification / Broadcast System

Features:
- /broadcast message
- /notify 5m message
- /notify 5h message
- /notify 1d message
- /notifications
- /cancelnotify ID
- /users
- Automatic user registration
- Persistent SQLite database
- Background scheduler
"""

import asyncio
import html
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.error import Forbidden, BadRequest, RetryAfter
from telegram.ext import CommandHandler, TypeHandler


# =========================================================
# CONFIG
# =========================================================

DB_PATH = os.environ.get(
    "NOTIFICATIONS_DB_PATH",
    "king_zarry_notifications.db"
)

BROADCAST_DELAY_SECONDS = 0.06

_scheduler_task = None


# =========================================================
# DATABASE
# =========================================================

def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    return conn


def init_notifications_db():
    with _connect() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                chat_type TEXT DEFAULT 'private',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                send_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_by INTEGER,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()


init_notifications_db()


# =========================================================
# ADMIN CHECK
# =========================================================

def get_admin_ids():
    """
    Reads ADMIN_IDS from Railway environment variables.

    Example:
    ADMIN_IDS=8137079113,6399410217
    """

    admin_ids = set()

    raw = os.getenv("ADMIN_IDS", "")

    for value in re.split(r"[,\s]+", raw):
        value = value.strip()

        if not value:
            continue

        try:
            admin_ids.add(int(value))
        except ValueError:
            pass

    # Also support subscription.py if it exists
    try:
        from subscription import ADMIN_IDS

        if isinstance(ADMIN_IDS, (list, tuple, set)):
            for admin_id in ADMIN_IDS:
                try:
                    admin_ids.add(int(admin_id))
                except (ValueError, TypeError):
                    pass

        elif isinstance(ADMIN_IDS, str):
            for value in re.split(r"[,\s]+", ADMIN_IDS):
                try:
                    admin_ids.add(int(value))
                except ValueError:
                    pass

    except Exception:
        pass

    return admin_ids


def is_admin(user_id):
    if not user_id:
        return False

    return int(user_id) in get_admin_ids()


# =========================================================
# USER REGISTRATION
# =========================================================

def register_user_from_update(update: Update) -> bool:

    user = update.effective_user

    if not user:
        return False

    chat = update.effective_chat

    chat_type = (
        getattr(chat, "type", "private")
        if chat
        else "private"
    )

    # Only private chats should receive broadcasts
    if chat_type != "private":
        return False

    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:

        conn.execute("""
            INSERT INTO notification_users (
                user_id,
                username,
                first_name,
                last_name,
                chat_type,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                chat_type=excluded.chat_type,
                is_active=1,
                updated_at=excluded.updated_at
        """, (
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            chat_type,
            now,
            now
        ))

        conn.commit()

    return True


async def track_user(update: Update, context):
    """
    Automatically registers users whenever they interact
    with the bot in a private chat.
    """

    try:
        register_user_from_update(update)
    except Exception as e:
        print(f"⚠️ Notification user tracking error: {e}")


def mark_user_inactive(user_id: int):

    with _connect() as conn:

        conn.execute("""
            UPDATE notification_users
            SET is_active=0,
                updated_at=?
            WHERE user_id=?
        """, (
            datetime.now(timezone.utc).isoformat(),
            user_id
        ))

        conn.commit()


def get_active_user_ids():

    with _connect() as conn:

        rows = conn.execute("""
            SELECT user_id
            FROM notification_users
            WHERE is_active=1
            AND chat_type='private'
            ORDER BY user_id
        """).fetchall()

    return [row[0] for row in rows]


def get_user_count():

    with _connect() as conn:

        row = conn.execute("""
            SELECT COUNT(*)
            FROM notification_users
            WHERE is_active=1
            AND chat_type='private'
        """).fetchone()

    return int(row[0] if row else 0)


# =========================================================
# TIME PARSER
# =========================================================

_TIME_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*"
    r"(seconds?|secs?|s|"
    r"minutes?|mins?|m|"
    r"hours?|hrs?|h|"
    r"days?|d)\s*$",
    re.I
)


def parse_delay(value: str):

    match = _TIME_PATTERN.match(value or "")

    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2).lower()

    if unit.startswith(("s", "sec")):
        seconds = amount

    elif unit.startswith(("m", "min")):
        seconds = amount * 60

    elif unit.startswith(("h", "hr")):
        seconds = amount * 3600

    else:
        seconds = amount * 86400

    if seconds <= 0:
        return None

    return timedelta(seconds=seconds)


def format_duration(delta: timedelta):

    total = max(
        0,
        int(delta.total_seconds())
    )

    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if seconds and len(parts) < 2:
        parts.append(f"{seconds}s")

    return " ".join(parts) or "now"


# =========================================================
# BROADCAST ENGINE
# =========================================================

async def broadcast_message(bot, text: str):

    success = 0
    failed = 0

    user_ids = get_active_user_ids()

    print(
        f"📢 Starting broadcast to "
        f"{len(user_ids)} active users..."
    )

    for user_id in user_ids:

        try:

            await bot.send_message(
                chat_id=user_id,
                text=text,
                disable_web_page_preview=True
            )

            success += 1

        except RetryAfter as e:

            wait_time = float(e.retry_after) + 0.5

            print(
                f"⏳ Telegram rate limit. "
                f"Waiting {wait_time:.1f}s..."
            )

            await asyncio.sleep(wait_time)

            try:

                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    disable_web_page_preview=True
                )

                success += 1

            except Forbidden:
                failed += 1
                mark_user_inactive(user_id)

            except BadRequest:
                failed += 1

            except Exception:
                failed += 1

        except Forbidden:

            failed += 1
            mark_user_inactive(user_id)

        except BadRequest as e:

            failed += 1

            error = str(e).lower()

            if any(
                phrase in error
                for phrase in (
                    "chat not found",
                    "user is deactivated",
                    "bot was blocked",
                    "forbidden"
                )
            ):
                mark_user_inactive(user_id)

        except Exception as e:

            failed += 1

            print(
                f"⚠️ Broadcast error for "
                f"{user_id}: {e}"
            )

        await asyncio.sleep(
            BROADCAST_DELAY_SECONDS
        )

    print(
        f"📢 Broadcast finished: "
        f"{success} delivered, "
        f"{failed} failed"
    )

    return success, failed


# =========================================================
# SCHEDULED NOTIFICATIONS
# =========================================================

def create_scheduled_notification(
    message: str,
    delay: timedelta,
    created_by: int
):

    send_at = (
        datetime.now(timezone.utc)
        + delay
    )

    with _connect() as conn:

        cur = conn.execute("""
            INSERT INTO scheduled_notifications (
                message,
                send_at,
                status,
                created_by,
                created_at
            )
            VALUES (?, ?, 'pending', ?, ?)
        """, (
            message,
            send_at.isoformat(),
            created_by,
            datetime.now(timezone.utc).isoformat()
        ))

        conn.commit()

        return int(cur.lastrowid)


def get_pending_notifications():

    with _connect() as conn:

        return conn.execute("""
            SELECT
                id,
                message,
                send_at,
                created_by
            FROM scheduled_notifications
            WHERE status='pending'
            ORDER BY send_at ASC
        """).fetchall()


def cancel_scheduled_notification(
    notification_id: int
):

    with _connect() as conn:

        cur = conn.execute("""
            UPDATE scheduled_notifications
            SET status='cancelled'
            WHERE id=?
            AND status='pending'
        """, (notification_id,))

        conn.commit()

        return cur.rowcount > 0


def _claim_notification(notification_id: int):

    with _connect() as conn:

        cur = conn.execute("""
            UPDATE scheduled_notifications
            SET status='sending'
            WHERE id=?
            AND status='pending'
        """, (notification_id,))

        conn.commit()

        return cur.rowcount > 0


def _finish_notification(
    notification_id: int,
    success: int,
    failed: int
):

    with _connect() as conn:

        conn.execute("""
            UPDATE scheduled_notifications
            SET
                status='sent',
                sent_at=?,
                success_count=?,
                failed_count=?
            WHERE id=?
        """, (
            datetime.now(timezone.utc).isoformat(),
            success,
            failed,
            notification_id
        ))

        conn.commit()


def _reset_notification(notification_id: int):

    with _connect() as conn:

        conn.execute("""
            UPDATE scheduled_notifications
            SET status='pending'
            WHERE id=?
        """, (notification_id,))

        conn.commit()


# =========================================================
# BACKGROUND SCHEDULER
# =========================================================

async def notification_scheduler(bot):

    print("📢 Notification scheduler started.")

    while True:

        try:

            now = datetime.now(timezone.utc)

            rows = get_pending_notifications()

            for (
                notification_id,
                message,
                send_at_text,
                created_by
            ) in rows:

                try:

                    send_at = datetime.fromisoformat(
                        send_at_text
                    )

                    if send_at.tzinfo is None:
                        send_at = send_at.replace(
                            tzinfo=timezone.utc
                        )

                except Exception:

                    print(
                        f"⚠️ Invalid schedule "
                        f"#{notification_id}"
                    )

                    _finish_notification(
                        notification_id,
                        0,
                        0
                    )

                    continue

                # Not due yet
                if send_at > now:
                    continue

                # Another worker already claimed it
                if not _claim_notification(
                    notification_id
                ):
                    continue

                try:

                    print(
                        f"📢 Sending scheduled "
                        f"notification #{notification_id}"
                    )

                    success, failed = (
                        await broadcast_message(
                            bot,
                            message
                        )
                    )

                    _finish_notification(
                        notification_id,
                        success,
                        failed
                    )

                    print(
                        f"✅ Notification "
                        f"#{notification_id} complete"
                    )

                except Exception as e:

                    print(
                        f"⚠️ Scheduled notification "
                        f"#{notification_id} failed: {e}"
                    )

                    _reset_notification(
                        notification_id
                    )

            await asyncio.sleep(5)

        except asyncio.CancelledError:

            print(
                "🛑 Notification scheduler stopped."
            )

            raise

        except Exception as e:

            print(
                f"⚠️ Notification scheduler error: {e}"
            )

            await asyncio.sleep(10)


def start_notification_scheduler(application):

    global _scheduler_task

    if (
        _scheduler_task
        and not _scheduler_task.done()
    ):
        return

    _scheduler_task = application.create_task(
        notification_scheduler(
            application.bot
        ),
        name="king-zarry-notification-scheduler"
    )

    print(
        "📢 Notification scheduler: ENABLED"
    )


async def stop_notification_scheduler(
    application
):

    global _scheduler_task

    if (
        _scheduler_task
        and not _scheduler_task.done()
    ):

        _scheduler_task.cancel()

        try:
            await _scheduler_task

        except asyncio.CancelledError:
            pass

    _scheduler_task = None

    print(
        "📢 Notification scheduler: STOPPED"
    )


# =========================================================
# HELP
# =========================================================

def build_notification_help():

    return (
        "👑 <b>KING ZARRY AI • NOTIFICATIONS</b>\n\n"

        "📢 <b>Broadcast now</b>\n"
        "/broadcast Your message here\n\n"

        "⏰ <b>Schedule</b>\n"
        "/notify 5m We will be back in 5 minutes.\n"
        "/notify 5h We will be back in 5 hours.\n"
        "/notify 30m Maintenance starts soon.\n"
        "/notify 1d Big update tomorrow 👑\n\n"

        "📋 <b>View scheduled</b>\n"
        "/notifications\n\n"

        "❌ <b>Cancel</b>\n"
        "/cancelnotify ID\n\n"

        "👥 <b>User count</b>\n"
        "/users\n\n"

        "Supported time formats:\n"
        "30s • 5m • 30m • 2h • 1d"
    )


# =========================================================
# /broadcast
# =========================================================

async def broadcast_command(
    update: Update,
    context
):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):

        await message.reply_text(
            "⛔ Admin only."
        )

        return

    text = " ".join(
        context.args
    ).strip()

    if not text:

        await message.reply_text(
            "⚠️ Usage:\n\n"
            "/broadcast Your message here"
        )

        return

    status = await message.reply_text(
        "📢 <b>BROADCAST STARTED</b>\n\n"
        "Sending your message to active users...",
        parse_mode="HTML"
    )

    try:

        success, failed = await broadcast_message(
            context.bot,
            text
        )

        await status.edit_text(
            "📢 <b>BROADCAST COMPLETE</b>\n\n"
            f"✅ Delivered: <b>{success}</b>\n"
            f"❌ Failed/removed: <b>{failed}</b>\n"
            f"👥 Active users: <b>{get_user_count()}</b>",
            parse_mode="HTML"
        )

    except Exception as e:

        print(
            f"❌ Broadcast command error: {e}"
        )

        await status.edit_text(
            "❌ Broadcast failed.\n\n"
            f"<code>{html.escape(str(e))}</code>",
            parse_mode="HTML"
        )


# =========================================================
# /notify
# =========================================================

async def notify_command(
    update: Update,
    context
):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):

        await message.reply_text(
            "⛔ Admin only."
        )

        return

    if len(context.args) < 2:

        await message.reply_text(
            build_notification_help(),
            parse_mode="HTML"
        )

        return

    delay = parse_delay(
        context.args[0]
    )

    if delay is None:

        await message.reply_text(
            "❌ Invalid time.\n\n"
            "Examples:\n"
            "/notify 5m We will be back in 5 minutes.\n"
            "/notify 5h We will be back in 5 hours.\n"
            "/notify 1d Big update tomorrow."
        )

        return

    notification_message = " ".join(
        context.args[1:]
    ).strip()

    if not notification_message:

        await message.reply_text(
            "⚠️ Please provide the notification message."
        )

        return

    notification_id = (
        create_scheduled_notification(
            notification_message,
            delay,
            user.id
        )
    )

    send_at = (
        datetime.now(timezone.utc)
        + delay
    )

    await message.reply_text(
        "⏰ <b>NOTIFICATION SCHEDULED</b>\n\n"
        f"🆔 ID: <code>{notification_id}</code>\n"
        f"⏳ In: <b>{format_duration(delay)}</b>\n"
        f"🕐 UTC: <code>"
        f"{send_at.strftime('%Y-%m-%d %H:%M:%S')}"
        f"</code>\n\n"
        "📢 <b>Message:</b>\n"
        f"{html.escape(notification_message)}\n\n"
        "Use /cancelnotify ID to cancel it.",
        parse_mode="HTML"
    )


# =========================================================
# /notifications
# =========================================================

async def notifications_command(
    update: Update,
    context
):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):

        await message.reply_text(
            "⛔ Admin only."
        )

        return

    rows = get_pending_notifications()

    if not rows:

        await message.reply_text(
            "📋 No pending notifications."
        )

        return

    now = datetime.now(timezone.utc)

    lines = [
        "📋 <b>PENDING NOTIFICATIONS</b>\n"
    ]

    for (
        notification_id,
        notification_message,
        send_at_text,
        created_by
    ) in rows:

        try:

            send_at = datetime.fromisoformat(
                send_at_text
            )

            if send_at.tzinfo is None:
                send_at = send_at.replace(
                    tzinfo=timezone.utc
                )

            remaining = send_at - now

            if remaining.total_seconds() <= 0:
                remaining_text = "sending soon"
            else:
                remaining_text = format_duration(
                    remaining
                )

        except Exception:

            remaining_text = "invalid schedule"

        preview = notification_message.replace(
            "\n",
            " "
        )

        if len(preview) > 100:
            preview = preview[:100] + "..."

        lines.append(
            f"🆔 <code>{notification_id}</code> "
            f"• <b>{html.escape(remaining_text)}</b>\n"
            f"📝 {html.escape(preview)}\n"
        )

    await message.reply_text(
        "\n".join(lines),
        parse_mode="HTML"
    )


# =========================================================
# /cancelnotify
# =========================================================

async def cancel_notify_command(
    update: Update,
    context
):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):

        await message.reply_text(
            "⛔ Admin only."
        )

        return

    if not context.args:

        await message.reply_text(
            "Usage:\n"
            "/cancelnotify ID\n\n"
            "Example:\n"
            "/cancelnotify 12"
        )

        return

    try:

        notification_id = int(
            context.args[0]
        )

    except ValueError:

        await message.reply_text(
            "❌ Notification ID must be a number."
        )

        return

    if cancel_scheduled_notification(
        notification_id
    ):

        await message.reply_text(
            f"✅ Notification "
            f"<code>{notification_id}</code> "
            f"cancelled.",
            parse_mode="HTML"
        )

    else:

        await message.reply_text(
            "❌ Notification not found "
            "or already sent/cancelled."
        )


# =========================================================
# /users
# =========================================================

async def users_command(
    update: Update,
    context
):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):

        await message.reply_text(
            "⛔ Admin only."
        )

        return

    await message.reply_text(
        "👑 <b>KING ZARRY AI USERS</b>\n\n"
        f"🟢 Active notification users: "
        f"<b>{get_user_count()}</b>\n\n"
        "Users are automatically registered "
        "when they interact with the bot "
        "in a private chat.",
        parse_mode="HTML"
    )


# =========================================================
# INSTALL ALL NOTIFICATION HANDLERS
# =========================================================

def setup_notification_handlers(application):

    """
    Call this ONCE after creating your Telegram Application.
    """

    init_notifications_db()

    # Automatically register users
    application.add_handler(
        TypeHandler(
            Update,
            track_user
        ),
        group=-100
    )

    # Admin notification commands
    application.add_handler(
        CommandHandler(
            "broadcast",
            broadcast_command
        )
    )

    application.add_handler(
        CommandHandler(
            "notify",
            notify_command
        )
    )

    application.add_handler(
        CommandHandler(
            "notifications",
            notifications_command
        )
    )

    application.add_handler(
        CommandHandler(
            "cancelnotify",
            cancel_notify_command
        )
    )

    application.add_handler(
        CommandHandler(
            "users",
            users_command
        )
    )

    print(
        "📢 Notification handlers: ENABLED"
    )


# =========================================================
# STARTUP / SHUTDOWN
# =========================================================

async def notifications_post_init(
    application
):

    init_notifications_db()

    start_notification_scheduler(
        application
    )

    print(
        "👑 KING ZARRY NOTIFICATION SYSTEM ONLINE"
    )


async def notifications_post_shutdown(
    application
):

    await stop_notification_scheduler(
        application
    )
