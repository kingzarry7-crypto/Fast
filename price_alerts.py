"""
👑 KING ZARRY AI - Shared Personal Price Alerts
Reused by Telegram and Discord - single source of truth
Table: price_alerts in king_zarry.db (shared with king_zarry_memory.db fallback)
"""
import os
import re
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List

logger = logging.getLogger("king_zarry_price_alerts")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

DATABASE_PATH = clean_env_str(os.getenv("DATABASE_PATH"), "king_zarry.db")
# For Discord which uses king_zarry_memory.db for users, we ensure price_alerts table exists there too if DATABASE_PATH points elsewhere
# We will check both DBs, but primary is king_zarry.db

def db_connect(path: Optional[str] = None):
    p = path or DATABASE_PATH
    conn = sqlite3.connect(p, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_price_alerts_table(conn=None):
    """Ensure price_alerts exists"""
    close_conn = False
    if conn is None:
        conn = db_connect()
        close_conn = True
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            target_price REAL NOT NULL,
            condition TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            triggered INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            triggered_at TEXT,
            last_checked_price REAL,
            last_checked_at TEXT
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_alerts_user ON price_alerts(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(active, triggered)")
        conn.commit()
    finally:
        if close_conn:
            conn.close()

# Initialize on import
try:
    ensure_price_alerts_table()
    # Also ensure in memory db if different
    mem_path = clean_env_str(os.getenv("MEMORY_DB_PATH"), "king_zarry_memory.db")
    if mem_path != DATABASE_PATH:
        try:
            conn2 = db_connect(mem_path)
            ensure_price_alerts_table(conn2)
            conn2.close()
        except Exception:
            pass
except Exception as e:
    logger.warning(f"price_alerts table init warning: {e}")

def normalize_alert_symbol(raw: str) -> Optional[str]:
    upper = raw.upper().strip()
    mapping = {
        "XAU": "XAU/USD",
        "XAUUSD": "XAU/USD",
        "XAU/USD": "XAU/USD",
        "GOLD": "XAU/USD",
        "BTC": "BTC/USD",
        "BTCUSD": "BTC/USD",
        "BTC/USD": "BTC/USD",
        "ETH": "ETH/USD",
        "ETHUSD": "ETH/USD",
        "ETH/USD": "ETH/USD",
        "SOL": "SOL/USD",
        "SOLUSD": "SOL/USD",
        "SOL/USD": "SOL/USD",
    }
    if upper in mapping:
        return mapping[upper]
    for k, v in mapping.items():
        if k in upper:
            return v
    return None

def parse_alert_request(text: str) -> Optional[Dict]:
    if not text:
        return None
    original = text.strip()
    lower = original.lower()
    cleaned = re.sub(r"^/alert\s*", "", original, flags=re.IGNORECASE).strip()
    price_match = re.findall(r"(\d+(?:\.\d+)?)", cleaned)
    if not price_match:
        return None
    try:
        target_price = float(price_match[-1])
    except:
        return None
    if target_price <= 0:
        return None
    symbol = normalize_alert_symbol(cleaned)
    if not symbol:
        symbol = normalize_alert_symbol(original)
    if not symbol:
        return None
    condition = "REACHES"
    if re.search(r"\babove\b|\bgoes above\b|\bgo above\b|\b>\b|\bhigher than\b|\bover\b", lower):
        if re.search(r"\babove\b|\b>\b|\bhigher than\b|\bover\b|\bgoes above\b|\bgo above\b", lower):
            if "below" not in lower or (lower.index("above") < lower.index("below") if "above" in lower and "below" in lower else True):
                condition = "ABOVE"
    if re.search(r"\bbelow\b|\bgoes below\b|\bgo below\b|\b<\b|\blower than\b|\bunder\b|\bdrops below\b|\bfalls below\b", lower):
        if "above" in lower and "below" in lower:
            condition = "ABOVE" if lower.rfind("above") > lower.rfind("below") else "BELOW"
        else:
            condition = "BELOW"
    if re.search(r"\breaches\b|\breach\b|\bhits\b|\bhit\b", lower):
        if "above" not in lower and "below" not in lower:
            condition = "REACHES"
    cmd_match = re.search(r"(above|below|reaches|reach|hit|hits)", cleaned.lower())
    if cmd_match:
        word = cmd_match.group(1)
        if word in ["above"]:
            condition = "ABOVE"
        elif word in ["below"]:
            condition = "BELOW"
        else:
            condition = "REACHES"
    return {"symbol": symbol, "target_price": target_price, "condition": condition, "raw": original}

def create_price_alert(user_id: int, symbol: str, target_price: float, condition: str) -> Dict:
    now = datetime.now(timezone.utc).isoformat()
    conn = db_connect()
    try:
        ensure_price_alerts_table(conn)
        existing = conn.execute(
            "SELECT id FROM price_alerts WHERE user_id=? AND symbol=? AND target_price=? AND condition=? AND active=1",
            (user_id, symbol, target_price, condition)
        ).fetchone()
        if existing:
            return {"success": False, "duplicate": True, "id": existing["id"]}
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO price_alerts (user_id, symbol, target_price, condition, active, triggered, created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, symbol, target_price, condition, 1, 0, now)
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    finally:
        conn.close()

def get_user_price_alerts(user_id: int, active_only: bool = True):
    conn = db_connect()
    try:
        ensure_price_alerts_table(conn)
        if active_only:
            rows = conn.execute(
                "SELECT * FROM price_alerts WHERE user_id=? AND active=1 ORDER BY id ASC", (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM price_alerts WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def cancel_user_alert(user_id: int, alert_id: int) -> bool:
    conn = db_connect()
    try:
        ensure_price_alerts_table(conn)
        cur = conn.cursor()
        cur.execute("UPDATE price_alerts SET active=0 WHERE id=? AND user_id=?", (alert_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def cancel_all_user_alerts(user_id: int) -> int:
    conn = db_connect()
    try:
        ensure_price_alerts_table(conn)
        cur = conn.cursor()
        cur.execute("UPDATE price_alerts SET active=0 WHERE user_id=? AND active=1", (user_id,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

def get_all_active_price_alerts():
    conn = db_connect()
    try:
        ensure_price_alerts_table(conn)
        rows = conn.execute("SELECT * FROM price_alerts WHERE active=1 AND triggered=0").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_current_price_for_alert(symbol: str) -> Optional[float]:
    try:
        from market import get_price as market_get_price
        price = market_get_price(symbol)
        if price:
            return float(price)
    except Exception as e:
        logger.debug(f"market.get_price failed for {symbol}: {e}")
    # Fallback via TwelveData time_series 1min
    try:
        # Import here to avoid circular
        import requests
        api_key = clean_env_str(os.getenv("TWELVE_DATA_API_KEY"))
        if not api_key:
            return None
        resp = requests.get(
            "https://api.twelvedata.com/time_series",
            params={"symbol": symbol, "interval": "1min", "outputsize": 10, "apikey": api_key},
            timeout=15
        )
        data = resp.json()
        if data.get("values"):
            last = data["values"][0]  # Twelve returns newest first
            return float(last.get("close"))
    except Exception as e:
        logger.debug(f"fallback price failed for {symbol}: {e}")
    return None

def check_alert_triggered_v2(current_price: float, target_price: float, condition: str, last_price: Optional[float] = None) -> bool:
    if current_price is None or target_price is None:
        return False
    if condition == "ABOVE":
        return current_price >= target_price
    if condition == "BELOW":
        return current_price <= target_price
    tolerance = max(abs(target_price) * 0.002, 0.01)
    if abs(current_price - target_price) <= tolerance:
        return True
    if last_price is not None:
        if (last_price < target_price <= current_price) or (last_price > target_price >= current_price):
            return True
    return False
