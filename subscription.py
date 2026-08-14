import sqlite3
import os
import re
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# =========================================================
# 👑 KING ZARRY AI - VIP SUBSCRIPTION SYSTEM
# =========================================================

DATABASE = "subscriptions.db"

# Admin Telegram IDs allowed to give/revoke subscriptions (Add your Telegram User ID here)
ADMIN_IDS = [int(i) for i in os.environ.get("ADMIN_IDS", "").split(",") if i.strip().isdigit()]


# =========================================================
# DATABASE SETUP
# =========================================================

def init_subscription_db():
    """Create the subscription database table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT NOT NULL DEFAULT 'inactive',
            expires_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on module load
init_subscription_db()


# =========================================================
# SUBSCRIPTION MANAGEMENT LOGIC
# =========================================================

def is_subscribed(user_id: int) -> bool:
    """Return True if the user has an active, non-expired subscription."""
    # Allow bot admins free access
    if user_id in ADMIN_IDS:
        return True

    conn = sqlite3.connect(DATABASE)
    row = conn.execute(
        "SELECT status, expires_at FROM subscriptions WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return False

    status, expires_at = row
    if status != "active" or not expires_at:
        return False

    try:
        expiry = datetime.fromisoformat(expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        if expiry <= now:
            deactivate_subscription(user_id)
            return False

        return True
    except Exception:
        return False


def activate_subscription(user_id: int, username: str, days: int):
    """Activate or renew a user's subscription for a set number of days."""
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        """
        INSERT INTO subscriptions (user_id, username, status, expires_at)
        VALUES (?, ?, 'active', ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            status = 'active',
            expires_at = excluded.expires_at
        """,
        (user_id, username, expires_at.isoformat())
    )
    conn.commit()
    conn.close()


def deactivate_subscription(user_id: int):
    """Deactivate a user's subscription."""
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        "UPDATE subscriptions SET status = 'inactive' WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def get_subscription(user_id: int):
    """Return subscription info dictionary for a user."""
    conn = sqlite3.connect(DATABASE)
    row = conn.execute(
        "SELECT user_id, username, status, expires_at FROM subscriptions WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "user_id": row[0],
        "username": row[1],
        "status": row[2],
        "expires_at": row[3],
    }


# =========================================================
# TELEGRAM UI & GATEKEEPING HANDLERS
# =========================================================

async def send_subscription_gate(update: Update):
    """Prompt unpaid users with instructions to purchase VIP."""
    payment_link = os.environ.get("PAYMENT_LINK", "https://t.me/your_admin_username")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Get King Zarry VIP Pass", url=payment_link)],
        [InlineKeyboardButton("🔄 Check Status", callback_data="check_vip_sub")]
    ])

    text = (
        "👑 *VIP ACCESS REQUIRED*\n\n"
        "To access **King Zarry AI** signals, technical chart analysis, and AI commands, "
        "you need an active VIP subscription.\n\n"
        "💳 Contact the Admin to get your access key!"
    )

    if update.callback_query:
        await update.callback_query.answer("❌ Your VIP pass is not active or has expired.", show_alert=True)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def check_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for the 'Check Status' inline button."""
    query = update.callback_query
    user_id = query.from_user.id

    if is_subscribed(user_id):
        sub_info = get_subscription(user_id)
        exp_date = sub_info['expires_at'].split('T')[0] if sub_info and sub_info['expires_at'] else "Lifetime"
        await query.answer("✅ Active VIP Membership Confirmed!", show_alert=True)
        await query.edit_message_text(
            f"👑 *ACCESS GRANTED*\n\n"
            f"Your VIP membership is active until: `{exp_date}`\n"
            f"Use `/signal BTC` or `/ask` to run your queries.",
            parse_mode="Markdown"
        )
    else:
        await send_subscription_gate(update)


# =========================================================
# ADMIN COMMANDS (GRANT / REVOKE ACCESS)
# =========================================================

async def grant_vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /grant <user_id> <days> (e.g. /grant 123456789 30)"""
    sender_id = update.effective_user.id
    if sender_id not in ADMIN_IDS:
        return  # Silently ignore non-admins

    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
        activate_subscription(target_user_id, "GrantedByAdmin", days)
        await update.message.reply_text(f"✅ Successfully granted **{days} days** VIP access to `{target_user_id}`.", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/grant <user_id> <days>`\nExample: `/grant 123456789 30`", parse_mode="Markdown")


async def revoke_vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: /revoke <user_id>"""
    sender_id = update.effective_user.id
    if sender_id not in ADMIN_IDS:
        return

    try:
        target_user_id = int(context.args[0])
        deactivate_subscription(target_user_id)
        await update.message.reply_text(f"🛑 Revoked VIP access for `{target_user_id}`.", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("⚠️ Usage: `/revoke <user_id>`", parse_mode="Markdown")
