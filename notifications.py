import asyncio
import os
import re
import sqlite3
import time

from telegram import Update
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import ContextTypes
from subscription import ADMIN_IDS

DB_PATH = os.getenv("NOTIFICATIONS_DB", "notifications.db")
TASKS = {}

def db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init_notifications_db():
    c = db()
    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS notification_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                send_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                sent_at REAL
            )
        """)
        c.commit()
    finally:
        c.close()

def register_user(update: Update):
    user = update.effective_user
    if not user:
        return
    now = time.time()
    c = db()
    try:
        c.execute("""
            INSERT INTO notification_users
            (user_id, username, first_name, last_name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                is_active=1,
                updated_at=excluded.updated_at
        """, (
            user.id, user.username or "", user.first_name or "",
            user.last_name or "", now, now
        ))
        c.commit()
    finally:
        c.close()

def active_user_ids():
    c = db()
    try:
        return [r["user_id"] for r in c.execute(
            "SELECT user_id FROM notification_users WHERE is_active=1"
        ).fetchall()]
    finally:
        c.close()

def deactivate_user(user_id):
    c = db()
    try:
        c.execute(
            "UPDATE notification_users SET is_active=0, updated_at=? WHERE user_id=?",
            (time.time(), user_id)
        )
        c.commit()
    finally:
        c.close()

def user_counts():
    c = db()
    try:
        total = c.execute("SELECT COUNT(*) FROM notification_users").fetchone()[0]
        active = c.execute(
            "SELECT COUNT(*) FROM notification_users WHERE is_active=1"
        ).fetchone()[0]
        return total, active, total - active
    finally:
        c.close()

async def broadcast_message(bot, text):
    text = (text or "").strip()
    result = {"sent": 0, "failed": 0, "removed": 0}

    for user_id in active_user_ids():
        try:
            await bot.send_message(chat_id=user_id, text=text)
            result["sent"] += 1
            await asyncio.sleep(0.04)
        except RetryAfter as e:
            await asyncio.sleep(max(float(e.retry_after), 1))
            try:
                await bot.send_message(chat_id=user_id, text=text)
                result["sent"] += 1
            except (Forbidden, BadRequest):
                deactivate_user(user_id)
                result["removed"] += 1
            except TelegramError:
                result["failed"] += 1
        except (Forbidden, BadRequest):
            deactivate_user(user_id)
            result["removed"] += 1
        except TelegramError as e:
            print(f"Broadcast error for {user_id}: {e}")
            result["failed"] += 1
        except Exception as e:
            print(f"Broadcast error for {user_id}: {e}")
            result["failed"] += 1

    return result

DURATION_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$",
    re.I
)

def parse_duration(value):
    m = DURATION_RE.match((value or "").strip())
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("s"):
        seconds = n
    elif unit.startswith("m"):
        seconds = n * 60
    elif unit.startswith("h"):
        seconds = n * 3600
    else:
        seconds = n * 86400
    if seconds <= 0 or seconds > 365 * 86400:
        return None
    return seconds

def add_scheduled(message, send_at):
    c = db()
    try:
        cur = c.execute("""
            INSERT INTO scheduled_notifications
            (message, send_at, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (message, send_at, time.time()))
        c.commit()
        return cur.lastrowid
    finally:
        c.close()

def get_pending():
    c = db()
    try:
        return c.execute("""
            SELECT id, message, send_at, status
            FROM scheduled_notifications
            WHERE status='pending'
            ORDER BY send_at
        """).fetchall()
    finally:
        c.close()

def get_notification(notification_id):
    c = db()
    try:
        return c.execute("""
            SELECT id, message, send_at, status
            FROM scheduled_notifications WHERE id=?
        """, (notification_id,)).fetchone()
    finally:
        c.close()

def mark_sent(notification_id):
    c = db()
    try:
        c.execute("""
            UPDATE scheduled_notifications
            SET status='sent', sent_at=? WHERE id=?
        """, (time.time(), notification_id))
        c.commit()
    finally:
        c.close()

def mark_cancelled(notification_id):
    c = db()
    try:
        c.execute(
            "UPDATE scheduled_notifications SET status='cancelled' WHERE id=?",
            (notification_id,)
        )
        c.commit()
    finally:
        c.close()

def remaining_text(seconds):
    seconds = max(0, int(seconds))
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not d and not h: parts.append(f"{s}s")
    return " ".join(parts) or "0s"

async def run_scheduled(application, notification_id, message, send_at):
    try:
        delay = send_at - time.time()
        if delay > 0:
            await asyncio.sleep(delay)
        row = get_notification(notification_id)
        if not row or row["status"] != "pending":
            return
        result = await broadcast_message(application.bot, message)
        mark_sent(notification_id)
        print(
            f"📢 Scheduled #{notification_id}: "
            f"sent={result['sent']} failed={result['failed']} removed={result['removed']}"
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"❌ Scheduled notification #{notification_id} failed: {e}")
    finally:
        TASKS.pop(notification_id, None)

async def schedule_notification(application, delay_seconds, message):
    send_at = time.time() + delay_seconds
    notification_id = add_scheduled(message, send_at)
    TASKS[notification_id] = asyncio.create_task(
        run_scheduled(application, notification_id, message, send_at)
    )
    return notification_id

async def restore_scheduled_notifications(application):
    rows = get_pending()
    for row in rows:
        notification_id = row["id"]
        if notification_id not in TASKS:
            TASKS[notification_id] = asyncio.create_task(
                run_scheduled(
                    application, notification_id,
                    row["message"], float(row["send_at"])
                )
            )
    print(f"📢 Restored {len(rows)} pending notification(s).")

def is_admin(update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)

async def track_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        register_user(update)
    except Exception as e:
        print(f"⚠️ User registration error: {e}")

async def broadcast_command(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text(
            "Usage:\n/broadcast Your message here"
        )
        return
    await update.message.reply_text("📢 Broadcasting to all active users...")
    r = await broadcast_message(context.application.bot, text)
    await update.message.reply_text(
        f"✅ Broadcast complete\n\n"
        f"📨 Sent: {r['sent']}\n"
        f"⚠️ Failed: {r['failed']}\n"
        f"🚫 Removed: {r['removed']}"
    )

async def notify_command(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n/notify 5m Your message\n/notify 5h Your message\n/notify 2d Your message"
        )
        return
    delay = parse_duration(context.args[0])
    if delay is None:
        await update.message.reply_text("❌ Invalid time. Use 30s, 5m, 5h or 2d.")
        return
    text = " ".join(context.args[1:]).strip()
    notification_id = await schedule_notification(
        context.application, delay, text
    )
    await update.message.reply_text(
        f"⏰ Scheduled!\n\nID: {notification_id}\n"
        f"Send in: {remaining_text(delay)}\n\n📢 {text}"
    )

async def users_command(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    total, active, inactive = user_counts()
    await update.message.reply_text(
        f"👑 Notification users\n\n"
        f"👥 Total: {total}\n🟢 Active: {active}\n🔴 Inactive: {inactive}"
    )

async def notifications_command(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    rows = get_pending()
    if not rows:
        await update.message.reply_text("📭 No pending notifications.")
        return
    now = time.time()
    lines = ["⏰ Pending notifications:"]
    for row in rows:
        lines.append(
            f"\n🆔 {row['id']} | in {remaining_text(float(row['send_at'])-now)}\n"
            f"📢 {row['message']}"
        )
    await update.message.reply_text("\n".join(lines))

async def cancelnotify_command(update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /cancelnotify ID")
        return
    try:
        notification_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid notification ID.")
        return
    row = get_notification(notification_id)
    if not row:
        await update.message.reply_text("❌ Notification not found.")
        return
    if row["status"] != "pending":
        await update.message.reply_text(
            f"⚠️ Notification #{notification_id} is already {row['status']}."
        )
        return
    task = TASKS.get(notification_id)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    mark_cancelled(notification_id)
    await update.message.reply_text(
        f"🛑 Notification #{notification_id} cancelled."
    )

async def shutdown_notifications():
    tasks = list(TASKS.values())
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    TASKS.clear()

init_notifications_db()
