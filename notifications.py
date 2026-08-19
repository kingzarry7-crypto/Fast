"""King Zarry AI Telegram notification and broadcast system."""
import asyncio
import re
import html
import os
import sqlite3
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.error import Forbidden, BadRequest, RetryAfter

DB_PATH = os.environ.get("NOTIFICATIONS_DB_PATH", "king_zarry_notifications.db")
BROADCAST_DELAY_SECONDS = 0.06
_scheduler_task = None


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_notifications_db():
    with _connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS notification_users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            last_name TEXT, chat_type TEXT DEFAULT 'private',
            is_active INTEGER DEFAULT 1, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT NOT NULL,
            send_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_by INTEGER, created_at TEXT NOT NULL, sent_at TEXT,
            success_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0)""")
        conn.commit()


init_notifications_db()


def register_user_from_update(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    chat = update.effective_chat
    chat_type = getattr(chat, "type", "private") if chat else "private"
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""INSERT INTO notification_users
            (user_id, username, first_name, last_name, chat_type,
             is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username, first_name=excluded.first_name,
            last_name=excluded.last_name, chat_type=excluded.chat_type,
            is_active=1, updated_at=excluded.updated_at""",
            (user.id, user.username, user.first_name, user.last_name,
             chat_type, now, now))
        conn.commit()
    return True


def mark_user_inactive(user_id: int):
    with _connect() as conn:
        conn.execute("UPDATE notification_users SET is_active=0, updated_at=? WHERE user_id=?",
                     (datetime.now(timezone.utc).isoformat(), user_id))
        conn.commit()


def get_active_user_ids():
    with _connect() as conn:
        rows = conn.execute("SELECT user_id FROM notification_users WHERE is_active=1 AND chat_type='private' ORDER BY user_id").fetchall()
    return [r[0] for r in rows]


def get_user_count():
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM notification_users WHERE is_active=1 AND chat_type='private'").fetchone()
    return int(row[0] if row else 0)


_TIME_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d)\s*$", re.I)


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
    return timedelta(seconds=seconds) if seconds > 0 else None


def format_duration(delta: timedelta) -> str:
    total = max(0, int(delta.total_seconds()))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds and len(parts) < 2: parts.append(f"{seconds}s")
    return " ".join(parts) or "now"


async def broadcast_message(bot, text: str):
    success = failed = 0
    for user_id in get_active_user_ids():
        try:
            await bot.send_message(chat_id=user_id, text=text, disable_web_page_preview=True)
            success += 1
        except RetryAfter as e:
            await asyncio.sleep(float(e.retry_after) + 0.5)
            try:
                await bot.send_message(chat_id=user_id, text=text, disable_web_page_preview=True)
                success += 1
            except (Forbidden, BadRequest):
                failed += 1; mark_user_inactive(user_id)
            except Exception:
                failed += 1
        except Forbidden:
            failed += 1; mark_user_inactive(user_id)
        except BadRequest as e:
            failed += 1
            msg = str(e).lower()
            if any(x in msg for x in ("chat not found", "user is deactivated", "bot was blocked")):
                mark_user_inactive(user_id)
        except Exception:
            failed += 1
        await asyncio.sleep(BROADCAST_DELAY_SECONDS)
    return success, failed


def create_scheduled_notification(message: str, delay: timedelta, created_by: int) -> int:
    send_at = datetime.now(timezone.utc) + delay
    with _connect() as conn:
        cur = conn.execute("""INSERT INTO scheduled_notifications
            (message, send_at, status, created_by, created_at)
            VALUES (?, ?, 'pending', ?, ?)""",
            (message, send_at.isoformat(), created_by, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return int(cur.lastrowid)


def get_pending_notifications():
    with _connect() as conn:
        return conn.execute("SELECT id, message, send_at, created_by FROM scheduled_notifications WHERE status='pending' ORDER BY send_at ASC").fetchall()


def cancel_scheduled_notification(notification_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("UPDATE scheduled_notifications SET status='cancelled' WHERE id=? AND status='pending'", (notification_id,))
        conn.commit()
        return cur.rowcount > 0


def _claim_notification(notification_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("UPDATE scheduled_notifications SET status='sending' WHERE id=? AND status='pending'", (notification_id,))
        conn.commit()
        return cur.rowcount > 0


def _finish_notification(notification_id: int, success: int, failed: int):
    with _connect() as conn:
        conn.execute("UPDATE scheduled_notifications SET status='sent', sent_at=?, success_count=?, failed_count=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), success, failed, notification_id))
        conn.commit()


def _reset_notification(notification_id: int):
    with _connect() as conn:
        conn.execute("UPDATE scheduled_notifications SET status='pending' WHERE id=?", (notification_id,))
        conn.commit()


async def notification_scheduler(bot):
    while True:
        try:
            now = datetime.now(timezone.utc)
            for notification_id, message, send_at_text, _ in get_pending_notifications():
                try:
                    send_at = datetime.fromisoformat(send_at_text)
                    if send_at.tzinfo is None:
                        send_at = send_at.replace(tzinfo=timezone.utc)
                except Exception:
                    _finish_notification(notification_id, 0, 0)
                    continue
                if send_at > now or not _claim_notification(notification_id):
                    continue
                try:
                    success, failed = await broadcast_message(bot, message)
                    _finish_notification(notification_id, success, failed)
                    print(f"📢 Scheduled notification #{notification_id}: {success} delivered, {failed} failed")
                except Exception as e:
                    print(f"⚠️ Scheduled notification #{notification_id} failed: {e}")
                    _reset_notification(notification_id)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"⚠️ Notification scheduler error: {e}")
            await asyncio.sleep(10)


def start_notification_scheduler(application):
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = application.create_task(notification_scheduler(application.bot), name="king-zarry-notification-scheduler")
    print("📢 Notification scheduler: ENABLED")


async def stop_notification_scheduler(application):
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None
    print("📢 Notification scheduler: STOPPED")


def build_notification_help():
    return ("👑 KING ZARRY AI • NOTIFICATIONS\n\n"
            "📢 /broadcast Your message here\n\n"
            "⏰ /notify 5m We will be back in 5 minutes.\n"
            "/notify 5h We will be back in 5 hours.\n"
            "/notify 30m Maintenance starts soon.\n"
            "/notify 1d Big update tomorrow 👑\n\n"
            "📋 /notifications\n"
            "❌ /cancelnotify ID\n"
            "👥 /users\n\n"
            "Supported: 30s • 5m • 30m • 2h • 1d")


async def broadcast_command(update: Update, context):
    from subscription import ADMIN_IDS
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("⚠️ Usage:\n/broadcast Your message here"); return
    status = await update.message.reply_text("📢 <b>Broadcast started...</b>\nSending to active users.", parse_mode="HTML")
    success, failed = await broadcast_message(context.bot, text)
    await status.edit_text("📢 <b>BROADCAST COMPLETE</b>\n\n"
                           f"✅ Delivered: <b>{success}</b>\n❌ Failed/removed: <b>{failed}</b>\n"
                           f"👥 Active users: <b>{get_user_count()}</b>", parse_mode="HTML")


async def notify_command(update: Update, context):
    from subscription import ADMIN_IDS
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if len(context.args) < 2:
        await update.message.reply_text(build_notification_help()); return
    delay = parse_delay(context.args[0])
    message = " ".join(context.args[1:]).strip()
    if delay is None:
        await update.message.reply_text("❌ Invalid time. Use /notify 5m message, /notify 5h message, /notify 30s message, or /notify 1d message.")
        return
    notification_id = create_scheduled_notification(message, delay, user.id)
    send_at = datetime.now(timezone.utc) + delay
    await update.message.reply_text("⏰ <b>NOTIFICATION SCHEDULED</b>\n\n"
        f"🆔 ID: <code>{notification_id}</code>\n⏳ In: <b>{format_duration(delay)}</b>\n"
        f"🕐 UTC: <code>{send_at.strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n📢 Message:\n{html.escape(message)}\n\n"
        "Use /cancelnotify ID to cancel it.", parse_mode="HTML")


async def notifications_command(update: Update, context):
    from subscription import ADMIN_IDS
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    rows = get_pending_notifications()
    if not rows:
        await update.message.reply_text("📋 No pending notifications."); return
    now = datetime.now(timezone.utc)
    lines = ["📋 <b>PENDING NOTIFICATIONS</b>\n"]
    for notification_id, message, send_at_text, _ in rows:
        try:
            send_at = datetime.fromisoformat(send_at_text)
            if send_at.tzinfo is None: send_at = send_at.replace(tzinfo=timezone.utc)
            remaining = send_at - now
            rem = "ready" if remaining.total_seconds() <= 0 else format_duration(remaining)
        except Exception:
            rem = "invalid schedule"
        preview = message.replace("\n", " ")
        if len(preview) > 100: preview = preview[:100] + "..."
        lines.append(f"🆔 <code>{notification_id}</code> • <b>{html.escape(rem)}</b>\n📝 {html.escape(preview)}\n")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cancel_notify_command(update: Update, context):
    from subscription import ADMIN_IDS
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    if not context.args:
        await update.message.reply_text("Usage:\n/cancelnotify ID\n\nExample:\n/cancelnotify 12"); return
    try:
        notification_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Notification ID must be a number."); return
    if cancel_scheduled_notification(notification_id):
        await update.message.reply_text(f"✅ Notification <code>{notification_id}</code> cancelled.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Notification not found or already sent/cancelled.")


async def users_command(update: Update, context):
    from subscription import ADMIN_IDS
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only."); return
    await update.message.reply_text("👥 <b>KING ZARRY AI USERS</b>\n\n"
        f"🟢 Active notification users: <b>{get_user_count()}</b>\n\n"
        "Users are automatically registered when they interact with the bot in a private chat.", parse_mode="HTML")
