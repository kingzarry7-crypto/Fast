import requests
import config
import math
import logging
import os
import re
import json
import sqlite3
import threading
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import uuid

logger = logging.getLogger("king_zarry_market")

TWELVE_DATA_API_KEY = getattr(config, "TWELVE_DATA_API_KEY", None)
TWELVE_DATA_URL = getattr(config, "TWELVE_DATA_URL", "https://api.twelvedata.com").rstrip("/")

TIMEFRAME_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1day",
}

MTF_WEIGHTS = {
    "4h": 0.35,
    "1h": 0.30,
    "15m": 0.25,
    "5m": 0.10,
}

PRIMARY_TF = "15m"

# ===================== DAILY PLAN CONFIG =====================
def _clean_env_str(v, default=""):
    if not v:
        return default
    try:
        v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    except Exception:
        v = str(v).strip()
    return v if v else default

TRADING_TZ_ENV = _clean_env_str(os.getenv("TRADING_TIMEZONE") or os.getenv("TIMEZONE"), "UTC")
DAILY_PLAN_DB_PATH = _clean_env_str(os.getenv("DAILY_PLAN_DB_PATH") or os.getenv("DATABASE_PATH"), "")
if not DAILY_PLAN_DB_PATH or DAILY_PLAN_DB_PATH == "king_zarry.db":
    # Keep daily plans separate from main bot db to avoid lock contention
    DAILY_PLAN_DB_PATH = "king_zarry_daily_plans.db"

# allow overriding db location via absolute path
if not os.path.isabs(DAILY_PLAN_DB_PATH):
    # Place next to this file if relative
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        DAILY_PLAN_DB_PATH = os.path.join(base_dir, DAILY_PLAN_DB_PATH)
    except Exception:
        pass

_daily_plan_lock = threading.RLock()

# ===================== TIMEZONE / TRADING DATE =====================
def get_trading_date(now: Optional[datetime] = None) -> str:
    """Return trading date string YYYY-MM-DD in configured timezone (default UTC)."""
    if now is None:
        now = datetime.now(timezone.utc)
    # Simple timezone handling: support UTC and common offsets without heavy pytz
    tz_name = TRADING_TZ_ENV.upper()
    if tz_name in ("UTC", "GMT", "Z"):
        dt = now.astimezone(timezone.utc)
    else:
        # Try parse like UTC+3 or +03:00 or Africa/Lagos naive fallback to UTC
        # For production, keep UTC to avoid DST complexity; env can still force UTC
        # If user set e.g. "UTC+1", apply offset
        m = re.match(r"UTC\s*([+-])\s*(\d+)(?::?(\d+))?", tz_name)
        if m:
            sign = 1 if m.group(1) == "+" else -1
            hours = int(m.group(2))
            mins = int(m.group(3) or 0)
            offset = timedelta(hours=sign*hours, minutes=sign*mins)
            dt = now.astimezone(timezone.utc) + offset
        else:
            # Fallback: UTC
            dt = now.astimezone(timezone.utc)
    return dt.date().isoformat()

def get_current_utc_iso():
    return datetime.now(timezone.utc).isoformat()

# ===================== PERSISTENCE LAYER =====================
def _connect_daily_db():
    directory = os.path.dirname(os.path.abspath(DAILY_PLAN_DB_PATH))
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(DAILY_PLAN_DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def _init_daily_db():
    with _daily_plan_lock:
        conn = _connect_daily_db()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_plans (
                    daily_plan_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_low REAL,
                    entry_high REAL,
                    stop_loss REAL,
                    tp1 REAL,
                    tp2 REAL,
                    tp3 REAL,
                    confidence INTEGER,
                    strength INTEGER,
                    timeframe TEXT,
                    mtf_bias TEXT,
                    mtf_score REAL,
                    h4_trend TEXT,
                    h1_trend TEXT,
                    m15_trend TEXT,
                    m5_trend TEXT,
                    timeframe_alignment TEXT,
                    structure TEXT,
                    structure_detail TEXT,
                    support REAL,
                    resistance REAL,
                    nearest_support REAL,
                    nearest_resistance REAL,
                    major_support REAL,
                    major_resistance REAL,
                    rsi REAL,
                    ema9 REAL,
                    ema21 REAL,
                    ema50 REAL,
                    atr REAL,
                    news_risk TEXT,
                    reason TEXT,
                    reasons_json TEXT,
                    entry_quality TEXT,
                    original_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    invalidated_at TEXT,
                    invalidation_reason TEXT,
                    replacement_of TEXT,
                    invalidated_direction TEXT,
                    raw_json TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_plans_symbol_date ON daily_plans(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_plans_status ON daily_plans(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_plans_date ON daily_plans(trading_date)")
            conn.commit()
        finally:
            conn.close()

_init_daily_db()

def _save_plan_row(plan: Dict[str, Any]):
    with _daily_plan_lock:
        conn = _connect_daily_db()
        try:
            conn.execute("""
                INSERT INTO daily_plans (
                    daily_plan_id, symbol, trading_date, status, direction,
                    entry_low, entry_high, stop_loss, tp1, tp2, tp3,
                    confidence, strength, timeframe, mtf_bias, mtf_score,
                    h4_trend, h1_trend, m15_trend, m5_trend, timeframe_alignment,
                    structure, structure_detail, support, resistance,
                    nearest_support, nearest_resistance, major_support, major_resistance,
                    rsi, ema9, ema21, ema50, atr, news_risk, reason, reasons_json,
                    entry_quality, original_price, created_at, updated_at,
                    invalidated_at, invalidation_reason, replacement_of,
                    invalidated_direction, raw_json
                ) VALUES (
                    :daily_plan_id, :symbol, :trading_date, :status, :direction,
                    :entry_low, :entry_high, :stop_loss, :tp1, :tp2, :tp3,
                    :confidence, :strength, :timeframe, :mtf_bias, :mtf_score,
                    :h4_trend, :h1_trend, :m15_trend, :m5_trend, :timeframe_alignment,
                    :structure, :structure_detail, :support, :resistance,
                    :nearest_support, :nearest_resistance, :major_support, :major_resistance,
                    :rsi, :ema9, :ema21, :ema50, :atr, :news_risk, :reason, :reasons_json,
                    :entry_quality, :original_price, :created_at, :updated_at,
                    :invalidated_at, :invalidation_reason, :replacement_of,
                    :invalidated_direction, :raw_json
                )
                ON CONFLICT(daily_plan_id) DO UPDATE SET
                    status=excluded.status,
                    entry_low=excluded.entry_low,
                    entry_high=excluded.entry_high,
                    stop_loss=excluded.stop_loss,
                    tp1=excluded.tp1,
                    tp2=excluded.tp2,
                    tp3=excluded.tp3,
                    confidence=excluded.confidence,
                    strength=excluded.strength,
                    mtf_bias=excluded.mtf_bias,
                    mtf_score=excluded.mtf_score,
                    h4_trend=excluded.h4_trend,
                    h1_trend=excluded.h1_trend,
                    m15_trend=excluded.m15_trend,
                    m5_trend=excluded.m5_trend,
                    timeframe_alignment=excluded.timeframe_alignment,
                    structure=excluded.structure,
                    structure_detail=excluded.structure_detail,
                    support=excluded.support,
                    resistance=excluded.resistance,
                    nearest_support=excluded.nearest_support,
                    nearest_resistance=excluded.nearest_resistance,
                    major_support=excluded.major_support,
                    major_resistance=excluded.major_resistance,
                    rsi=excluded.rsi,
                    ema9=excluded.ema9,
                    ema21=excluded.ema21,
                    ema50=excluded.ema50,
                    atr=excluded.atr,
                    news_risk=excluded.news_risk,
                    reason=excluded.reason,
                    reasons_json=excluded.reasons_json,
                    entry_quality=excluded.entry_quality,
                    original_price=excluded.original_price,
                    updated_at=excluded.updated_at,
                    invalidated_at=excluded.invalidated_at,
                    invalidation_reason=excluded.invalidation_reason,
                    replacement_of=excluded.replacement_of,
                    invalidated_direction=excluded.invalidated_direction,
                    raw_json=excluded.raw_json
            """, plan)
            conn.commit()
        finally:
            conn.close()

def _load_active_plan_for_today(symbol: str, trading_date: str) -> Optional[Dict[str, Any]]:
    with _daily_plan_lock:
        conn = _connect_daily_db()
        try:
            row = conn.execute("""
                SELECT * FROM daily_plans
                WHERE symbol = ? AND trading_date = ?
                ORDER BY 
                    CASE status
                        WHEN 'ACTIVE' THEN 0
                        WHEN 'WAIT' THEN 1
                        WHEN 'INVALIDATED' THEN 2
                        WHEN 'REPLACED' THEN 3
                        ELSE 4
                    END,
                    datetime(updated_at) DESC
                LIMIT 1
            """, (symbol, trading_date)).fetchone()
            if not row:
                return None
            d = dict(row)
            # Parse json fields
            try:
                d["reasons"] = json.loads(d.get("reasons_json") or "[]")
            except Exception:
                d["reasons"] = []
            try:
                d["raw"] = json.loads(d.get("raw_json") or "{}")
            except Exception:
                d["raw"] = {}
            return d
        finally:
            conn.close()

def _expire_old_plans(symbol: str, current_date: str):
    # Mark previous ACTIVE plans as EXPIRED if not today
    with _daily_plan_lock:
        conn = _connect_daily_db()
        try:
            conn.execute("""
                UPDATE daily_plans SET status='EXPIRED', updated_at=?
                WHERE symbol = ? AND trading_date != ? AND status = 'ACTIVE'
            """, (get_current_utc_iso(), symbol, current_date))
            conn.commit()
        finally:
            conn.close()

def normalize_timeframe(timeframe):
    timeframe = str(timeframe).lower().strip()
    return TIMEFRAME_MAP.get(timeframe, timeframe)

def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def round_price(price):
    if price is None:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if abs(price) >= 1000:
        return round(price, 2)
    if abs(price) >= 100:
        return round(price, 3)
    if abs(price) >= 1:
        return round(price, 4)
    return round(price, 6)

def get_price(symbol):
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing.")
    response = requests.get(
        f"{TWELVE_DATA_URL}/price",
        params={"symbol": symbol.upper().strip(), "apikey": TWELVE_DATA_API_KEY},
        timeout=30
    )
    if response.status_code != 200:
        raise RuntimeError(f"Twelve Data HTTP error: {response.status_code}")
    data = response.json()
    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Twelve Data error."))
    if "price" not in data:
        raise RuntimeError(f"Price unavailable: {data}")
    return float(data["price"])

def get_candles(symbol, timeframe="15m", outputsize=150):
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing.")
    interval = normalize_timeframe(timeframe)
    response = requests.get(
        f"{TWELVE_DATA_URL}/time_series",
        params={
            "symbol": symbol.upper().strip(),
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY
        },
        timeout=30
    )
    if response.status_code != 200:
        raise RuntimeError(f"Twelve Data HTTP error: {response.status_code}")
    data = response.json()
    if data.get("status") == "error":
        raise RuntimeError(data.get("message", "Twelve Data error."))
    if "values" not in data:
        raise RuntimeError(f"No candle data returned: {data}")
    candles = list(reversed(data["values"]))
    if not candles or len(candles) < 15:
        raise RuntimeError(f"Insufficient candle data returned for {symbol} (got {len(candles)} candles).")
    return candles

def calculate_ema(values, period):
    if not values:
        return None
    if len(values) < period:
        try:
            return sum(values) / len(values) if values else None
        except Exception:
            return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result

def calculate_rsi(values, period=14):
    if not values or len(values) < 2:
        return 50.0
    actual_period = min(period, len(values) - 1)
    if actual_period <= 0:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    if not gains or not losses:
        return 50.0
    avg_gain = sum(gains[:actual_period]) / actual_period if actual_period else 0
    avg_loss = sum(losses[:actual_period]) / actual_period if actual_period else 0
    for i in range(actual_period, len(gains)):
        avg_gain = ((avg_gain * (actual_period - 1)) + gains[i]) / actual_period
        avg_loss = ((avg_loss * (actual_period - 1)) + losses[i]) / actual_period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(candles, period=14):
    if not candles or len(candles) < 2:
        return None
    true_ranges = []
    for i in range(1, len(candles)):
        high = safe_float(candles[i].get("high"))
        low = safe_float(candles[i].get("low"))
        previous_close = safe_float(candles[i - 1].get("close"))
        if None in (high, low, previous_close):
            continue
        tr = max(high - low, abs(high - previous_close), abs(low - previous_close))
        true_ranges.append(tr)
    if not true_ranges:
        last_close = safe_float(candles[-1].get("close"))
        return (last_close * 0.005) if last_close is not None else None
    actual_period = min(period, len(true_ranges))
    if actual_period <= 0:
        return sum(true_ranges) / len(true_ranges) if true_ranges else None
    atr = sum(true_ranges[:actual_period]) / actual_period
    for tr in true_ranges[actual_period:]:
        atr = ((atr * (actual_period - 1)) + tr) / actual_period
    return atr

def candle_body(candle):
    open_price = safe_float(candle.get("open"))
    close_price = safe_float(candle.get("close"))
    if open_price is None or close_price is None:
        return 0
    return abs(close_price - open_price)

def is_bullish_candle(candle):
    open_price = safe_float(candle.get("open"))
    close_price = safe_float(candle.get("close"))
    return open_price is not None and close_price is not None and close_price > open_price

def is_bearish_candle(candle):
    open_price = safe_float(candle.get("open"))
    close_price = safe_float(candle.get("close"))
    return open_price is not None and close_price is not None and close_price < open_price

def determine_structure(candles):
    if len(candles) < 10:
        return "NEUTRAL"
    recent = candles[-20:] if len(candles) >= 20 else candles
    highs = [safe_float(c.get("high")) for c in recent]
    lows = [safe_float(c.get("low")) for c in recent]
    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]
    if len(highs) < 4 or len(lows) < 4:
        return "NEUTRAL"
    mid = len(highs) // 2
    if mid == 0:
        return "NEUTRAL"
    previous_high = max(highs[:mid])
    recent_high = max(highs[mid:])
    previous_low = min(lows[:mid])
    recent_low = min(lows[mid:])
    if recent_high > previous_high and recent_low > previous_low:
        return "BULLISH"
    if recent_high < previous_high and recent_low < previous_low:
        return "BEARISH"
    return "NEUTRAL"

def calculate_support_resistance(candles):
    recent = candles[-30:] if len(candles) >= 30 else candles
    highs = [safe_float(c.get("high")) for c in recent]
    lows = [safe_float(c.get("low")) for c in recent]
    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]
    if not highs or not lows:
        return None, None
    support = min(lows)
    resistance = max(highs)
    return support, resistance

def momentum_score(closes):
    if len(closes) < 3:
        return 0
    recent = closes[-6:] if len(closes) >= 6 else closes
    rising = 0
    falling = 0
    for i in range(1, len(recent)):
        if recent[i] > recent[i - 1]:
            rising += 1
        elif recent[i] < recent[i - 1]:
            falling += 1
    if rising >= len(recent) // 2 + 1:
        return 1
    if falling >= len(recent) // 2 + 1:
        return -1
    return 0

def find_swing_points(candles: List[Dict], lookback: int = 5) -> Dict[str, Any]:
    if not candles or len(candles) < lookback * 2 + 1:
        return {
            "swing_high": None,
            "swing_low": None,
            "recent_swing_high": None,
            "recent_swing_low": None,
            "all_swing_highs": [],
            "all_swing_lows": [],
        }
    swing_highs: List[Tuple[int, float]] = []
    swing_lows: List[Tuple[int, float]] = []
    for i in range(lookback, len(candles) - lookback):
        curr_high = safe_float(candles[i].get("high"))
        curr_low = safe_float(candles[i].get("low"))
        window_highs = []
        window_lows = []
        for j in range(i - lookback, i + lookback + 1):
            h = safe_float(candles[j].get("high"))
            l = safe_float(candles[j].get("low"))
            if h is not None:
                window_highs.append(h)
            if l is not None:
                window_lows.append(l)
        if not window_highs or not window_lows:
            continue
        if curr_high is not None and curr_high == max(window_highs):
            swing_highs.append((i, curr_high))
        if curr_low is not None and curr_low == min(window_lows):
            swing_lows.append((i, curr_low))
    swing_high = max([v for _, v in swing_highs]) if swing_highs else None
    swing_low = min([v for _, v in swing_lows]) if swing_lows else None
    recent_swing_high = swing_highs[-1][1] if swing_highs else None
    recent_swing_low = swing_lows[-1][1] if swing_lows else None
    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "recent_swing_high": recent_swing_high,
        "recent_swing_low": recent_swing_low,
        "all_swing_highs": [v for _, v in swing_highs[-5:]],
        "all_swing_lows": [v for _, v in swing_lows[-5:]],
    }

def determine_advanced_structure(candles: List[Dict]) -> Dict[str, Any]:
    if len(candles) < 15:
        return {
            "structure": "NEUTRAL",
            "detail": "Insufficient data",
            "structure_detail": "Insufficient data",
            "swing_high": None,
            "swing_low": None,
            "recent_swing_high": None,
            "recent_swing_low": None,
            "breakout": False,
            "breakdown": False,
            "hh": False,
            "hl": False,
            "lh": False,
            "ll": False,
            "all_swing_highs": [],
            "all_swing_lows": [],
        }
    swings = find_swing_points(candles, lookback=3)
    recent = candles[-30:] if len(candles) >= 30 else candles
    closes = [safe_float(c.get("close")) for c in recent]
    closes = [c for c in closes if c is not None]
    base_structure = determine_structure(candles)
    all_highs = swings.get("all_swing_highs") or []
    all_lows = swings.get("all_swing_lows") or []
    hh = hl = lh = ll = False
    if len(all_highs) >= 2:
        if all_highs[-1] > all_highs[-2]:
            hh = True
        elif all_highs[-1] < all_highs[-2]:
            lh = True
    if len(all_lows) >= 2:
        if all_lows[-1] > all_lows[-2]:
            hl = True
        elif all_lows[-1] < all_lows[-2]:
            ll = True
    structure = base_structure
    detail = ""
    if hh and hl:
        structure = "BULLISH"
        detail = "HH + HL - bullish structure"
    elif lh and ll:
        structure = "BEARISH"
        detail = "LH + LL - bearish structure"
    elif hh and ll:
        detail = "Mixed - HH but LL, potential transition"
    elif lh and hl:
        detail = "Mixed - LH but HL, consolidation"
    price = closes[-1] if closes else None
    breakout = False
    breakdown = False
    recent_high = swings.get("recent_swing_high")
    recent_low = swings.get("recent_swing_low")
    if recent_high is not None and price is not None:
        try:
            break_pct = (price - recent_high) / recent_high * 100 if recent_high != 0 else 0
            if break_pct > 0.15:
                breakout = True
                detail += f" | Breakout above recent swing high ({recent_high})"
        except Exception:
            pass
    if recent_low is not None and price is not None:
        try:
            break_pct = (recent_low - price) / recent_low * 100 if recent_low != 0 else 0
            if break_pct > 0.15:
                breakdown = True
                detail += f" | Breakdown below recent swing low ({recent_low})"
        except Exception:
            pass
    if not detail:
        detail = f"{structure} structure"
    return {
        "structure": structure,
        "detail": detail,
        "structure_detail": detail,
        "swing_high": swings.get("swing_high"),
        "swing_low": swings.get("swing_low"),
        "recent_swing_high": recent_high,
        "recent_swing_low": recent_low,
        "breakout": breakout,
        "breakdown": breakdown,
        "hh": hh,
        "hl": hl,
        "lh": lh,
        "ll": ll,
        "all_swing_highs": all_highs,
        "all_swing_lows": all_lows,
    }

def calculate_advanced_sr(candles: List[Dict]) -> Dict[str, Any]:
    basic_support, basic_resistance = calculate_support_resistance(candles)
    if not candles:
        return {
            "nearest_support": basic_support,
            "nearest_resistance": basic_resistance,
            "major_support": basic_support,
            "major_resistance": basic_resistance,
            "support": basic_support,
            "resistance": basic_resistance,
            "basic_support": basic_support,
            "basic_resistance": basic_resistance,
            "distance_to_support_pct": None,
            "distance_to_resistance_pct": None,
        }
    swings = find_swing_points(candles, lookback=3)
    all_highs = swings.get("all_swing_highs") or []
    all_lows = swings.get("all_swing_lows") or []
    price = safe_float(candles[-1].get("close"))
    nearest_support = None
    nearest_resistance = None
    if price is not None:
        below_lows = [l for l in all_lows if l is not None and l < price]
        above_highs = [h for h in all_highs if h is not None and h > price]
        if below_lows:
            nearest_support = max(below_lows)
        if above_highs:
            nearest_resistance = min(above_highs)
    if nearest_support is None:
        if basic_support is not None and price is not None:
            if basic_support < price:
                nearest_support = basic_support
        else:
            nearest_support = basic_support
    if nearest_resistance is None:
        if basic_resistance is not None and price is not None:
            if basic_resistance > price:
                nearest_resistance = basic_resistance
        else:
            nearest_resistance = basic_resistance
    extended = candles[-100:] if len(candles) >= 100 else candles
    ex_highs = [safe_float(c.get("high")) for c in extended if safe_float(c.get("high")) is not None]
    ex_lows = [safe_float(c.get("low")) for c in extended if safe_float(c.get("low")) is not None]
    major_support = min(ex_lows) if ex_lows else basic_support
    major_resistance = max(ex_highs) if ex_highs else basic_resistance
    dist_to_support = None
    dist_to_resistance = None
    if price is not None and price != 0:
        if nearest_support is not None:
            try:
                dist_to_support = ((price - nearest_support) / price) * 100
                if dist_to_support < 0:
                    dist_to_support = None
            except Exception:
                dist_to_support = None
        if nearest_resistance is not None:
            try:
                dist_to_resistance = ((nearest_resistance - price) / price) * 100
                if dist_to_resistance < 0:
                    dist_to_resistance = None
            except Exception:
                dist_to_resistance = None
    return {
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "major_support": major_support,
        "major_resistance": major_resistance,
        "support": nearest_support if nearest_support is not None else basic_support,
        "resistance": nearest_resistance if nearest_resistance is not None else basic_resistance,
        "basic_support": basic_support,
        "basic_resistance": basic_resistance,
        "distance_to_support_pct": dist_to_support,
        "distance_to_resistance_pct": dist_to_resistance,
    }

def calculate_ema_alignment(ema9, ema21, ema50, price) -> Dict[str, Any]:
    if None in (ema9, ema21, ema50):
        return {"alignment": "NEUTRAL","bullish": False,"bearish": False,"compressed": False,"expanded": False,"expansion_pct": 0}
    try:
        bullish = ema9 > ema21 > ema50 and (price is None or price > ema9)
        bearish = ema9 < ema21 < ema50 and (price is None or price < ema9)
        avg_ema = (ema9 + ema21 + ema50) / 3
        if avg_ema == 0:
            return {"alignment": "NEUTRAL","bullish": False,"bearish": False,"compressed": False,"expanded": False,"expansion_pct": 0}
        max_dev = max(abs(ema9 - avg_ema), abs(ema21 - avg_ema), abs(ema50 - avg_ema))
        compressed = (max_dev / abs(avg_ema) * 100) < 0.5
        expansion_pct = abs(ema9 - ema50) / abs(avg_ema) * 100
        expanded = expansion_pct > 2.0
        if bullish:
            alignment = "BULLISH_ALIGNED"
        elif bearish:
            alignment = "BEARISH_ALIGNED"
        elif compressed:
            alignment = "COMPRESSED"
        elif expanded:
            alignment = "EXPANDED"
        else:
            alignment = "MIXED"
        return {"alignment": alignment,"bullish": bullish,"bearish": bearish,"compressed": compressed,"expanded": expanded,"expansion_pct": expansion_pct}
    except Exception:
        return {"alignment": "NEUTRAL","bullish": False,"bearish": False,"compressed": False,"expanded": False,"expansion_pct": 0}

def analyze_ema_extended(price, ema21, ema50, atr) -> Dict[str, Any]:
    if None in (price, ema21, ema50, atr) or atr == 0:
        return {"extended_from_21": False,"extended_from_50": False,"distance_21_atr": 0,"distance_50_atr": 0,"distance_21_pct": 0,"distance_50_pct": 0}
    try:
        dist_21 = abs(price - ema21) / atr if atr != 0 else 0
        dist_50 = abs(price - ema50) / atr if atr != 0 else 0
        extended_21 = dist_21 > 2.5
        extended_50 = dist_50 > 3.5
        return {"extended_from_21": extended_21,"extended_from_50": extended_50,"distance_21_atr": dist_21,"distance_50_atr": dist_50,"distance_21_pct": ((price - ema21) / price * 100) if price != 0 else 0,"distance_50_pct": ((price - ema50) / price * 100) if price != 0 else 0}
    except Exception:
        return {"extended_from_21": False,"extended_from_50": False,"distance_21_atr": 0,"distance_50_atr": 0,"distance_21_pct": 0,"distance_50_pct": 0}

def analyze_rsi_state(rsi: float, closes: List[float]) -> Dict[str, Any]:
    if rsi is None:
        return {"state": "NEUTRAL","momentum": "NEUTRAL","overbought": False,"oversold": False,"exhaustion_risk": "LOW","divergence": False,"rsi": 50.0}
    try:
        if 50 <= rsi < 65:
            momentum = "BULLISH"
            state = "BULLISH_MOMENTUM"
        elif 65 <= rsi < 75:
            momentum = "STRONG_BULLISH"
            state = "STRONG_BULLISH"
        elif rsi >= 75:
            momentum = "OVERBOUGHT"
            state = "OVERBOUGHT"
        elif 35 < rsi < 50:
            momentum = "BEARISH"
            state = "BEARISH_MOMENTUM"
        elif 25 < rsi <= 35:
            momentum = "STRONG_BEARISH"
            state = "STRONG_BEARISH"
        elif rsi <= 25:
            momentum = "OVERSOLD"
            state = "OVERSOLD"
        else:
            momentum = "NEUTRAL"
            state = "NEUTRAL"
        overbought = rsi >= 70
        oversold = rsi <= 30
        exhaustion_risk = "LOW"
        if rsi >= 78 or rsi <= 22:
            exhaustion_risk = "EXTREME"
        elif rsi >= 72 or rsi <= 28:
            exhaustion_risk = "HIGH"
        elif rsi >= 68 or rsi <= 32:
            exhaustion_risk = "MEDIUM"
        divergence = False
        if len(closes) >= 10:
            try:
                if len(closes) >= 17:
                    prev_rsi = calculate_rsi(closes[:-3], 14)
                    recent_rsi_trend = rsi - prev_rsi
                    price_trend = closes[-1] - closes[-4]
                    if (price_trend > 0 and recent_rsi_trend < -5) or (price_trend < 0 and recent_rsi_trend > 5):
                        divergence = True
            except Exception:
                divergence = False
        return {"state": state,"momentum": momentum,"overbought": overbought,"oversold": oversold,"exhaustion_risk": exhaustion_risk,"divergence": divergence,"rsi": rsi}
    except Exception:
        return {"state": "NEUTRAL","momentum": "NEUTRAL","overbought": False,"oversold": False,"exhaustion_risk": "LOW","divergence": False,"rsi": rsi}

def classify_volatility(atr: Optional[float], price: Optional[float], candles: List[Dict]) -> Dict[str, Any]:
    if atr is None or price is None or price == 0:
        return {"level": "NORMAL","atr_pct": 0,"atr_expansion": 1.0,"avg_atr": atr,"score": 50,"current_atr": atr}
    try:
        atr_pct = abs((atr / price) * 100)
        recent_atrs = []
        if len(candles) >= 20:
            for i in range(len(candles)-20, len(candles)):
                if i >= 14:
                    sub_candles = candles[max(0, i-14):i+1]
                    sub_atr = calculate_atr(sub_candles, 14)
                    if sub_atr is not None and sub_atr > 0:
                        recent_atrs.append(sub_atr)
        avg_recent_atr = sum(recent_atrs) / len(recent_atrs) if recent_atrs else atr
        if avg_recent_atr is None or avg_recent_atr == 0:
            avg_recent_atr = atr
            atr_expansion = 1.0
        else:
            atr_expansion = (atr / avg_recent_atr) if avg_recent_atr != 0 else 1.0
        if atr_pct < 0.15:
            level = "LOW"
        elif atr_pct < 0.6:
            level = "NORMAL"
        elif atr_pct < 1.5:
            level = "HIGH"
        else:
            level = "EXTREME"
        if atr_expansion > 1.8 and level != "EXTREME":
            if level == "LOW":
                level = "NORMAL"
            elif level == "NORMAL":
                level = "HIGH"
            elif level == "HIGH":
                level = "EXTREME"
        try:
            raw_score = atr_pct * 50 + (atr_expansion - 1) * 20
            score = max(0, min(100, int(raw_score)))
        except Exception:
            score = 50
        return {"level": level,"atr_pct": atr_pct,"atr_expansion": atr_expansion,"avg_atr": avg_recent_atr,"score": score,"current_atr": atr}
    except Exception:
        return {"level": "NORMAL","atr_pct": 0,"atr_expansion": 1.0,"avg_atr": atr,"score": 50,"current_atr": atr}

def detect_exhaustion(candles: List[Dict], rsi_state: Dict, atr: float, ema21: float, support: float, resistance: float) -> Dict[str, Any]:
    if not candles or len(candles) < 5:
        return {"exhaustion": "NONE","level": "NONE","score": 0,"exhaustion_score": 0,"reasons": [],"exhaustion_reason": "No exhaustion - insufficient data"}
    reasons = []
    score = 0
    price = safe_float(candles[-1].get("close"))
    last_candle = candles[-1]
    rsi = rsi_state.get("rsi", 50) if isinstance(rsi_state, dict) else 50
    try:
        if rsi >= 78:
            score += 25
            reasons.append(f"RSI extremely overbought ({rsi:.1f})")
        elif rsi >= 72:
            score += 15
            reasons.append(f"RSI overbought ({rsi:.1f})")
        elif rsi <= 22:
            score += 25
            reasons.append(f"RSI extremely oversold ({rsi:.1f})")
        elif rsi <= 28:
            score += 15
            reasons.append(f"RSI oversold ({rsi:.1f})")
    except Exception:
        pass
    try:
        bodies = [candle_body(c) for c in candles[-10:]]
        bodies = [b for b in bodies if b is not None and b > 0]
        if bodies:
            avg_body = sum(bodies) / len(bodies)
            last_body = candle_body(last_candle)
            if avg_body > 0 and last_body > avg_body * 2.5:
                score += 20
                reasons.append(f"Abnormal large candle body ({last_body/avg_body:.1f}x avg)")
    except Exception:
        pass
    try:
        high = safe_float(last_candle.get("high"))
        low = safe_float(last_candle.get("low"))
        open_p = safe_float(last_candle.get("open"))
        close_p = safe_float(last_candle.get("close"))
        if None not in (high, low, open_p, close_p):
            total_range = high - low
            if total_range > 0:
                upper_wick = high - max(open_p, close_p)
                lower_wick = min(open_p, close_p) - low
                if upper_wick > total_range * 0.6 and upper_wick > lower_wick:
                    score += 15
                    reasons.append("Long upper wick - bearish rejection")
                elif lower_wick > total_range * 0.6 and lower_wick > upper_wick:
                    score += 15
                    reasons.append("Long lower wick - bullish rejection")
    except Exception:
        pass
    try:
        consecutive_bull = 0
        consecutive_bear = 0
        for c in reversed(candles[-7:]):
            if is_bullish_candle(c):
                if consecutive_bear == 0:
                    consecutive_bull += 1
                else:
                    break
            elif is_bearish_candle(c):
                if consecutive_bull == 0:
                    consecutive_bear += 1
                else:
                    break
            else:
                break
        if consecutive_bull >= 5:
            score += 15
            reasons.append(f"{consecutive_bull} consecutive bullish candles")
        elif consecutive_bear >= 5:
            score += 15
            reasons.append(f"{consecutive_bear} consecutive bearish candles")
    except Exception:
        pass
    try:
        if price is not None and ema21 is not None and atr is not None and atr != 0:
            dist_atr = abs(price - ema21) / atr
            if dist_atr > 3.0:
                score += 20
                reasons.append(f"Price {dist_atr:.1f} ATR away from EMA21 - extended")
            elif dist_atr > 2.0:
                score += 10
                reasons.append(f"Price {dist_atr:.1f} ATR from EMA21 - stretched")
    except Exception:
        pass
    try:
        if price is not None and resistance is not None and price != 0:
            dist_res_pct = abs(resistance - price) / price * 100
            if 0 <= dist_res_pct < 0.3 and resistance > price:
                score += 15
                reasons.append(f"Price very close to resistance ({dist_res_pct:.2f}% away)")
        if price is not None and support is not None and price != 0:
            dist_sup_pct = abs(price - support) / price * 100
            if 0 <= dist_sup_pct < 0.3 and support < price:
                score += 15
                reasons.append(f"Price very close to support ({dist_sup_pct:.2f}% away)")
    except Exception:
        pass
    try:
        vol = classify_volatility(atr, price, candles)
        if vol.get("level") == "EXTREME":
            score += 15
            reasons.append(f"Extreme volatility (ATR {vol.get('atr_pct',0):.2f}%)")
        elif vol.get("atr_expansion",1) > 2.0:
            score += 10
            reasons.append(f"ATR expanding {vol.get('atr_expansion',1):.1f}x")
    except Exception:
        pass
    try:
        if isinstance(rsi_state, dict) and rsi_state.get("divergence"):
            score += 15
            reasons.append("RSI divergence - momentum weakening")
    except Exception:
        pass
    score = max(0, min(100, score))
    if score >= 75:
        level = "EXTREME"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    elif score >= 15:
        level = "LOW"
    else:
        level = "NONE"
    return {"exhaustion": level,"level": level,"score": score,"exhaustion_score": score,"reasons": reasons,"exhaustion_reason": "; ".join(reasons) if reasons else "No exhaustion"}

def detect_late_entry(price: float, ema21: float, ema50: float, atr: float, rsi: float, candles: List[Dict], support: float, resistance: float, structure: str, volatility: Dict, exhaustion: Dict) -> Dict[str, Any]:
    if None in (price, ema21, atr):
        return {"late_entry": False,"late_entry_reason": "Insufficient data","reason": "Insufficient data","score": 0,"entry_quality": "UNKNOWN","quality": "UNKNOWN"}
    reasons = []
    late_score = 0
    try:
        is_bullish_structure = structure == "BULLISH" if isinstance(structure, str) else False
        is_bearish_structure = structure == "BEARISH" if isinstance(structure, str) else False
    except Exception:
        is_bullish_structure = False
        is_bearish_structure = False
    try:
        dist_21_atr = abs(price - ema21) / atr if atr != 0 else 0
        if dist_21_atr > 2.5:
            late_score += 30
            reasons.append(f"Price {dist_21_atr:.1f} ATR from EMA21 (too far)")
    except Exception:
        pass
    try:
        if ema50 is not None and atr is not None and atr != 0:
            dist_50_atr = abs(price - ema50) / atr
            if dist_50_atr > 3.5:
                late_score += 25
                reasons.append(f"Price {dist_50_atr:.1f} ATR from EMA50 (very extended)")
    except Exception:
        pass
    try:
        if price is not None and resistance is not None and price != 0:
            dist_res_pct = (resistance - price) / price * 100
            if 0 < dist_res_pct < 0.4:
                if is_bullish_structure or (isinstance(volatility, dict) and volatility.get("level") != "LOW"):
                    late_score += 20
                    reasons.append(f"Too close to resistance ({dist_res_pct:.2f}% away) - limited upside for BUY")
        if price is not None and support is not None and price != 0:
            dist_sup_pct = (price - support) / price * 100
            if 0 < dist_sup_pct < 0.4:
                if is_bearish_structure:
                    late_score += 20
                    reasons.append(f"Too close to support ({dist_sup_pct:.2f}% away) - limited downside for SELL")
    except Exception:
        pass
    try:
        if len(candles) >= 2:
            last_body = candle_body(candles[-1])
            prev_bodies = [candle_body(c) for c in candles[-6:-1]]
            prev_bodies = [b for b in prev_bodies if b > 0]
            if prev_bodies:
                avg_prev = sum(prev_bodies) / len(prev_bodies)
                if avg_prev > 0 and last_body > avg_prev * 2.0:
                    late_score += 20
                    reasons.append(f"Large impulsive candle just occurred ({last_body/avg_prev:.1f}x avg)")
    except Exception:
        pass
    try:
        if isinstance(volatility, dict):
            if volatility.get("level") == "EXTREME":
                late_score += 15
                reasons.append("Extreme volatility - move may be over")
            elif volatility.get("atr_expansion",1) > 2.2:
                late_score += 15
                reasons.append(f"Volatility spiked {volatility.get('atr_expansion',1):.1f}x - late")
    except Exception:
        pass
    try:
        if rsi is not None:
            if rsi >= 75 or rsi <= 25:
                if (rsi >= 75 and is_bullish_structure) or (rsi <= 25 and is_bearish_structure):
                    late_score += 15
                    reasons.append(f"RSI stretched at {rsi:.1f} in trending direction")
    except Exception:
        pass
    try:
        consecutive = 0
        direction = None
        for c in reversed(candles[-6:]):
            if is_bullish_candle(c):
                if direction is None or direction == "bull":
                    direction = "bull"
                    consecutive += 1
                else:
                    break
            elif is_bearish_candle(c):
                if direction is None or direction == "bear":
                    direction = "bear"
                    consecutive += 1
                else:
                    break
            else:
                break
        if consecutive >= 4:
            if consecutive >= 5 or (isinstance(exhaustion, dict) and exhaustion.get("level") in ["HIGH","EXTREME"]):
                late_score += 15
                reasons.append(f"{consecutive} consecutive {direction} candles - move extended")
    except Exception:
        pass
    try:
        if isinstance(exhaustion, dict) and exhaustion.get("level") in ["HIGH", "EXTREME"]:
            late_score += 20
            reasons.append(f"High exhaustion ({exhaustion.get('level')}) - late entry")
    except Exception:
        pass
    late_score = max(0, min(100, late_score))
    is_late = late_score >= 45
    if late_score >= 70:
        quality = "LATE"
    elif late_score >= 45:
        quality = "RISKY"
    elif late_score >= 25:
        quality = "ACCEPTABLE"
    else:
        quality = "IDEAL"
    return {"late_entry": is_late,"late_entry_reason": "; ".join(reasons) if reasons else "Entry timing acceptable","reason": "; ".join(reasons) if reasons else "Entry timing acceptable","score": late_score,"entry_quality": quality,"quality": quality}

def analyze_single_timeframe(candles: List[Dict], symbol: str, tf_name: str) -> Dict[str, Any]:
    if not candles or len(candles) < 15:
        return {"trend": "NEUTRAL","error": "Insufficient candles","timeframe": tf_name,"success": False}
    closes = [safe_float(c.get("close")) for c in candles if safe_float(c.get("close")) is not None]
    if len(closes) < 15:
        return {"trend": "NEUTRAL","error": "Invalid close data","timeframe": tf_name,"success": False}
    price = closes[-1]
    ema9 = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    rsi = calculate_rsi(closes, 14)
    atr = calculate_atr(candles, 14)
    if None in (ema9, ema21, ema50, atr):
        return {"trend": "NEUTRAL","error": "Indicator calc failed","timeframe": tf_name,"success": False}
    adv_structure = determine_advanced_structure(candles)
    adv_sr = calculate_advanced_sr(candles)
    ema_align = calculate_ema_alignment(ema9, ema21, ema50, price)
    ema_ext = analyze_ema_extended(price, ema21, ema50, atr)
    rsi_state = analyze_rsi_state(rsi, closes)
    volatility = classify_volatility(atr, price, candles)
    exhaustion = detect_exhaustion(candles, rsi_state, atr, ema21, adv_sr.get("support"), adv_sr.get("resistance"))
    bullish_pts = 0
    bearish_pts = 0
    if ema_align.get("bullish"):
        bullish_pts += 2
    if ema_align.get("bearish"):
        bearish_pts += 2
    if adv_structure.get("structure") == "BULLISH":
        bullish_pts += 2
    elif adv_structure.get("structure") == "BEARISH":
        bearish_pts += 2
    if rsi_state.get("momentum") in ["BULLISH", "STRONG_BULLISH"]:
        bullish_pts += 1
    elif rsi_state.get("momentum") in ["BEARISH", "STRONG_BEARISH"]:
        bearish_pts += 1
    if price > ema21:
        bullish_pts += 1
    elif price < ema21:
        bearish_pts += 1
    if bullish_pts >= bearish_pts + 2:
        trend = "BULLISH"
    elif bearish_pts >= bullish_pts + 2:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    return {"timeframe": tf_name,"trend": trend,"price": price,"ema9": ema9,"ema21": ema21,"ema50": ema50,"rsi": rsi,"atr": atr,"structure": adv_structure.get("structure", "NEUTRAL"),"structure_detail": adv_structure.get("detail", ""),"structure_data": adv_structure,"support": adv_sr.get("support"),"resistance": adv_sr.get("resistance"),"sr_data": adv_sr,"ema_alignment": ema_align,"ema_extended": ema_ext,"rsi_state": rsi_state,"volatility": volatility,"exhaustion": exhaustion,"closes": closes,"candles": candles,"success": True}

def fetch_mtf_candles(symbol: str) -> Dict[str, Any]:
    timeframes = ["4h", "1h", "15m", "5m"]
    results: Dict[str, Any] = {}
    for tf in timeframes:
        try:
            size = 150 if tf in ["15m", "5m"] else 100
            candles = get_candles(symbol, tf, size)
            results[tf] = {"success": True,"candles": candles,"error": None}
        except Exception as e:
            logger.warning(f"MTF fetch failed for {symbol} {tf}: {e}")
            results[tf] = {"success": False,"candles": [],"error": str(e)}
    return results

def calculate_mtf_bias(mtf_analyses: Dict[str, Dict]) -> Dict[str, Any]:
    score = 0.0
    total_weight = 0.0
    trends: Dict[str, str] = {}
    successful_tfs: List[str] = []
    for tf, weight in MTF_WEIGHTS.items():
        analysis = mtf_analyses.get(tf)
        if not analysis:
            trends[tf] = "UNAVAILABLE"
            continue
        if not analysis.get("success", True):
            trends[tf] = "UNAVAILABLE"
            continue
        trend = analysis.get("trend", "NEUTRAL")
        if "error" in analysis and not analysis.get("success"):
            trends[tf] = "UNAVAILABLE"
            continue
        trends[tf] = trend
        successful_tfs.append(tf)
        total_weight += weight
        if trend == "BULLISH":
            score += weight * 100
        elif trend == "BEARISH":
            score += weight * 0
        else:
            score += weight * 50
    if total_weight == 0:
        mtf_score = 50
        bias = "NEUTRAL"
    else:
        mtf_score = (score / total_weight)
        if mtf_score >= 75:
            bias = "STRONG_BULLISH"
        elif mtf_score >= 60:
            bias = "BULLISH"
        elif mtf_score >= 40:
            bias = "MIXED"
        elif mtf_score >= 25:
            bias = "BEARISH"
        else:
            bias = "STRONG_BEARISH"
    bullish_count = sum(1 for t in trends.values() if t == "BULLISH")
    bearish_count = sum(1 for t in trends.values() if t == "BEARISH")
    available_trends = {k: v for k, v in trends.items() if v != "UNAVAILABLE"}
    avail_bullish = sum(1 for t in available_trends.values() if t == "BULLISH")
    avail_bearish = sum(1 for t in available_trends.values() if t == "BEARISH")
    avail_total = len(available_trends)
    if avail_total == 0:
        alignment = "UNAVAILABLE"
    elif avail_bullish >= 3 or (avail_total >= 3 and avail_bullish == avail_total):
        alignment = "STRONG_BULLISH_ALIGNMENT"
    elif avail_bearish >= 3 or (avail_total >= 3 and avail_bearish == avail_total):
        alignment = "STRONG_BEARISH_ALIGNMENT"
    elif avail_bullish >= 2 and avail_bearish == 0:
        alignment = "BULLISH_ALIGNMENT"
    elif avail_bearish >= 2 and avail_bullish == 0:
        alignment = "BEARISH_ALIGNMENT"
    elif avail_bullish >= 1 and avail_bearish >= 1:
        alignment = "MIXED"
    else:
        alignment = "NEUTRAL"
    h4_trend = trends.get("4h", "UNAVAILABLE")
    h1_trend = trends.get("1h", "UNAVAILABLE")
    m15_trend = trends.get("15m", "UNAVAILABLE")
    m5_trend = trends.get("5m", "UNAVAILABLE")
    if h4_trend == "BULLISH" and h1_trend == "BULLISH":
        htf_trend = "BULLISH"
    elif h4_trend == "BEARISH" and h1_trend == "BEARISH":
        htf_trend = "BEARISH"
    elif h4_trend == "UNAVAILABLE" and h1_trend == "UNAVAILABLE":
        htf_trend = "UNAVAILABLE"
    elif h4_trend == "BULLISH" or h1_trend == "BULLISH":
        if h4_trend != "BEARISH" and h1_trend != "BEARISH":
            htf_trend = "BULLISH"
        else:
            htf_trend = "MIXED"
    elif h4_trend == "BEARISH" or h1_trend == "BEARISH":
        if h4_trend != "BULLISH" and h1_trend != "BULLISH":
            htf_trend = "BEARISH"
        else:
            htf_trend = "MIXED"
    else:
        htf_trend = "NEUTRAL"
    return {"mtf_bias": bias,"mtf_score": round(mtf_score, 1),"bias": bias,"score": round(mtf_score, 1),"htf_trend": htf_trend,"h4_trend": h4_trend,"h1_trend": h1_trend,"m15_trend": m15_trend,"m5_trend": m5_trend,"timeframe_alignment": alignment,"alignment": alignment,"trends": trends,"bullish_count": bullish_count,"bearish_count": bearish_count,"successful_timeframes": successful_tfs}

def get_news_risk_safe(symbol: str) -> Dict[str, Any]:
    try:
        import importlib.util
        import os
        news_mod = None
        try:
            import news as news_module
            news_mod = news_module
        except ImportError:
            possible_paths = ["/mnt/data/news.py", "news.py", "./news.py"]
            for p in possible_paths:
                if os.path.exists(p):
                    try:
                        spec = importlib.util.spec_from_file_location("news", p)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            news_mod = mod
                            break
                    except Exception:
                        continue
        if news_mod and hasattr(news_mod, "get_news_for_asset"):
            try:
                data = news_mod.get_news_for_asset(symbol)
                return {"news_risk": data.get("risk", "LOW") if isinstance(data, dict) else "LOW","news_available": data.get("news_available", False) or data.get("headlines_available", False) or data.get("calendar_available", False) if isinstance(data, dict) else False,"news_summary": data.get("summary", "No news") if isinstance(data, dict) else "No news","news_events": data.get("events", [])[:3] if isinstance(data, dict) else [],"news_headlines": data.get("headlines", [])[:2] if isinstance(data, dict) else [],"calendar_available": data.get("calendar_available", False) if isinstance(data, dict) else False,"headlines_available": data.get("headlines_available", False) if isinstance(data, dict) else False}
            except Exception as e:
                logger.debug(f"News get_news_for_asset failed: {e}")
    except Exception as e:
        logger.debug(f"News integration failed (safe): {e}")
    return {"news_risk": "UNKNOWN","news_available": False,"news_summary": "News module unavailable","news_events": [],"news_headlines": [],"calendar_available": False,"headlines_available": False}

# ===================== FRESH MARKET ANALYSIS (INTERNAL) =====================
def _analyze_market_fresh(symbol, timeframe="15m"):
    """Original market analysis without daily plan wrapper - produces fresh BUY/SELL/WAIT"""
    primary_tf_input = timeframe
    primary_tf = normalize_timeframe(timeframe)
    symbol = symbol.upper().strip()
    mtf_raw = fetch_mtf_candles(symbol)
    if primary_tf not in mtf_raw:
        try:
            primary_candles = get_candles(symbol, primary_tf, 150)
            mtf_raw[primary_tf] = {"success": True,"candles": primary_candles,"error": None}
        except Exception as e:
            if "15m" in mtf_raw and mtf_raw["15m"].get("success"):
                primary_candles = mtf_raw["15m"]["candles"]
                primary_tf = "15m"
            else:
                raise RuntimeError(f"Failed to fetch primary timeframe {primary_tf}: {e}")
    if primary_tf in mtf_raw and mtf_raw[primary_tf].get("success"):
        candles = mtf_raw[primary_tf]["candles"]
    else:
        if "15m" in mtf_raw and mtf_raw["15m"].get("success"):
            candles = mtf_raw["15m"]["candles"]
            primary_tf = "15m"
        else:
            successful = [k for k, v in mtf_raw.items() if v.get("success")]
            if not successful:
                raise RuntimeError(f"No candle data available for {symbol} on any timeframe")
            candles = mtf_raw[successful[0]]["candles"]
            primary_tf = successful[0]
    mtf_analyses: Dict[str, Dict] = {}
    for tf, data in mtf_raw.items():
        if data.get("success") and data.get("candles"):
            try:
                analysis = analyze_single_timeframe(data["candles"], symbol, tf)
                mtf_analyses[tf] = analysis
            except Exception as e:
                logger.warning(f"Failed to analyze {tf}: {e}")
                mtf_analyses[tf] = {"trend": "UNAVAILABLE","error": str(e),"timeframe": tf,"success": False}
    primary_analysis = mtf_analyses.get(primary_tf)
    if not primary_analysis or not primary_analysis.get("success"):
        primary_analysis = analyze_single_timeframe(candles, symbol, primary_tf)
        mtf_analyses[primary_tf] = primary_analysis
    closes = primary_analysis.get("closes")
    if not closes:
        closes = [safe_float(c.get("close")) for c in candles if safe_float(c.get("close")) is not None]
    if not closes:
        raise RuntimeError(f"Invalid close data for {symbol}")
    price = primary_analysis.get("price", closes[-1] if closes else 0)
    # Zero-data safety
    if price is None or price <= 0:
        raise RuntimeError(f"Invalid price {price} for {symbol}")
    ema9 = primary_analysis.get("ema9")
    ema21 = primary_analysis.get("ema21")
    ema50 = primary_analysis.get("ema50")
    rsi = primary_analysis.get("rsi", 50.0)
    atr = primary_analysis.get("atr")
    if None in (ema9, ema21, ema50, atr):
        raise RuntimeError("Unable to calculate technical indicators.")
    if atr is None or atr <= 0:
        raise RuntimeError(f"Invalid ATR {atr} for {symbol}")
    if ema9 <= 0 or ema21 <= 0 or ema50 <= 0:
        raise RuntimeError("Invalid EMA values")
    mtf = calculate_mtf_bias(mtf_analyses)
    adv_structure = primary_analysis.get("structure_data") or determine_advanced_structure(candles)
    adv_sr = primary_analysis.get("sr_data") or calculate_advanced_sr(candles)
    ema_align = primary_analysis.get("ema_alignment") or calculate_ema_alignment(ema9, ema21, ema50, price)
    ema_ext = primary_analysis.get("ema_extended") or analyze_ema_extended(price, ema21, ema50, atr)
    rsi_state = primary_analysis.get("rsi_state") or analyze_rsi_state(rsi, closes)
    volatility = primary_analysis.get("volatility") or classify_volatility(atr, price, candles)
    exhaustion = primary_analysis.get("exhaustion") or detect_exhaustion(candles, rsi_state, atr, ema21, adv_sr.get("support"), adv_sr.get("resistance"))
    support = adv_sr.get("support")
    resistance = adv_sr.get("resistance")
    nearest_support = adv_sr.get("nearest_support")
    nearest_resistance = adv_sr.get("nearest_resistance")
    major_support = adv_sr.get("major_support")
    major_resistance = adv_sr.get("major_resistance")
    if support is None or resistance is None:
        support = price - (atr * 2) if price and atr else price * 0.99 if price else None
        resistance = price + (atr * 2) if price and atr else price * 1.01 if price else None
    # Validate SR
    if support is not None and support <= 0:
        support = price - (atr * 2)
    if resistance is not None and resistance <= 0:
        resistance = price + (atr * 2)
    structure = adv_structure.get("structure", "NEUTRAL")
    late_entry_data = detect_late_entry(price, ema21, ema50, atr, rsi, candles, support, resistance, structure, volatility, exhaustion)
    news_data = get_news_risk_safe(symbol)
    news_risk = news_data.get("news_risk", "UNKNOWN")
    bullish_score = 0
    bearish_score = 0
    reasons = []
    mtf_score_val = mtf.get("mtf_score", 50)
    if mtf_score_val >= 60:
        bullish_score += int((mtf_score_val - 50) * 0.8)
        reasons.append(f"MTF bullish alignment {mtf_score_val:.0f}/100 ({mtf.get('alignment')})")
    elif mtf_score_val <= 40:
        bearish_score += int((50 - mtf_score_val) * 0.8)
        reasons.append(f"MTF bearish alignment {mtf_score_val:.0f}/100 ({mtf.get('alignment')})")
    if mtf.get("htf_trend") == "BULLISH":
        bullish_score += 15
        reasons.append(f"HTF bullish (4H:{mtf.get('h4_trend')} 1H:{mtf.get('h1_trend')})")
    elif mtf.get("htf_trend") == "BEARISH":
        bearish_score += 15
        reasons.append(f"HTF bearish (4H:{mtf.get('h4_trend')} 1H:{mtf.get('h1_trend')})")
    if ema_align.get("bullish"):
        bullish_score += 15
        reasons.append("EMA 9>21>50 bullish alignment")
    elif ema_align.get("bearish"):
        bearish_score += 15
        reasons.append("EMA 9<21<50 bearish alignment")
    elif ema_align.get("compressed"):
        reasons.append("EMA compressed - potential breakout soon")
    if not ema_ext.get("extended_from_21") and not ema_ext.get("extended_from_50"):
        if ema9 > ema21:
            bullish_score += 10
        elif ema9 < ema21:
            bearish_score += 10
        if ema21 > ema50:
            bullish_score += 10
        elif ema21 < ema50:
            bearish_score += 10
    if price > ema21 and not ema_ext.get("extended_from_21"):
        bullish_score += 8
    elif price < ema21 and not ema_ext.get("extended_from_21"):
        bearish_score += 8
    rsi_mom = rsi_state.get("momentum", "NEUTRAL")
    if rsi_mom == "BULLISH":
        bullish_score += 12
        reasons.append(f"RSI bullish momentum ({rsi:.1f})")
    elif rsi_mom == "STRONG_BULLISH":
        bullish_score += 8
        reasons.append(f"RSI strong bullish but watching for exhaustion ({rsi:.1f})")
    elif rsi_mom == "BEARISH":
        bearish_score += 12
        reasons.append(f"RSI bearish momentum ({rsi:.1f})")
    elif rsi_mom == "STRONG_BEARISH":
        bearish_score += 8
        reasons.append(f"RSI strong bearish but watching for exhaustion ({rsi:.1f})")
    elif rsi_mom == "OVERBOUGHT":
        reasons.append(f"RSI overbought ({rsi:.1f}) - potential exhaustion")
    elif rsi_mom == "OVERSOLD":
        reasons.append(f"RSI oversold ({rsi:.1f}) - potential exhaustion")
    if adv_structure.get("structure") == "BULLISH":
        bullish_score += 15
        reasons.append(f"Bullish structure: {adv_structure.get('detail')}")
    elif adv_structure.get("structure") == "BEARISH":
        bearish_score += 15
        reasons.append(f"Bearish structure: {adv_structure.get('detail')}")
    if adv_structure.get("breakout"):
        bullish_score += 10
        reasons.append("Breakout above recent swing high")
    if adv_structure.get("breakdown"):
        bearish_score += 10
        reasons.append("Breakdown below recent swing low")
    mom = momentum_score(closes)
    if mom > 0 and exhaustion.get("level") not in ["HIGH", "EXTREME"]:
        bullish_score += 8
        reasons.append("Recent momentum bullish")
    elif mom < 0 and exhaustion.get("level") not in ["HIGH", "EXTREME"]:
        bearish_score += 8
        reasons.append("Recent momentum bearish")
    penalty_bull = 0
    penalty_bear = 0
    if late_entry_data.get("late_entry"):
        if bullish_score > bearish_score:
            penalty_bull += late_entry_data.get("score", 0) // 2
        else:
            penalty_bear += late_entry_data.get("score", 0) // 2
        reasons.append(f"Late entry warning: {late_entry_data.get('reason')}")
    if exhaustion.get("level") == "EXTREME":
        if bullish_score > bearish_score:
            penalty_bull += 30
        else:
            penalty_bear += 30
        reasons.append(f"Exhaustion {exhaustion.get('level')}: {exhaustion.get('exhaustion_reason')}")
    elif exhaustion.get("level") == "HIGH":
        if bullish_score > bearish_score:
            penalty_bull += 20
        else:
            penalty_bear += 20
    elif exhaustion.get("level") == "MEDIUM":
        if bullish_score > bearish_score:
            penalty_bull += 10
        else:
            penalty_bear += 10
    if volatility.get("level") == "EXTREME":
        penalty_bull += 15
        penalty_bear += 15
        reasons.append(f"Extreme volatility ({volatility.get('atr_pct',0):.2f}% ATR)")
    if ema_ext.get("extended_from_21"):
        if price > ema21:
            penalty_bull += 15
        else:
            penalty_bear += 15
        reasons.append(f"Price extended {ema_ext.get('distance_21_atr',0):.1f} ATR from EMA21")
    if news_risk in ["HIGH", "EXTREME"]:
        penalty_bull += 15
        penalty_bear += 15
        reasons.append(f"News risk {news_risk} - high volatility expected")
    if mtf.get("alignment") == "MIXED":
        penalty_bull += 10
        penalty_bear += 10
        reasons.append("Mixed timeframe alignment")
    # Countertrend penalty: if 4H bearish but bullish setup, reduce bullish score
    if mtf.get("h4_trend") == "BEARISH" and bullish_score > bearish_score:
        penalty_bull += 12
        reasons.append("Countertrend: 4H bearish vs bullish setup - confidence reduced")
    if mtf.get("h4_trend") == "BULLISH" and bearish_score > bullish_score:
        penalty_bear += 12
        reasons.append("Countertrend: 4H bullish vs bearish setup - confidence reduced")
    if mtf.get("h1_trend") == "BEARISH" and bullish_score > bearish_score and mtf.get("h4_trend") == "BEARISH":
        penalty_bull += 10
        reasons.append("HTF bearish double confirmation against BUY")
    if mtf.get("h1_trend") == "BULLISH" and bearish_score > bullish_score and mtf.get("h4_trend") == "BULLISH":
        penalty_bear += 10
        reasons.append("HTF bullish double confirmation against SELL")
    if adv_sr.get("distance_to_resistance_pct") is not None and 0 < adv_sr.get("distance_to_resistance_pct") < 0.5:
        if bullish_score > bearish_score:
            penalty_bull += 10
            reasons.append(f"Close to major resistance ({adv_sr.get('distance_to_resistance_pct'):.2f}% away)")
    if adv_sr.get("distance_to_support_pct") is not None and 0 < adv_sr.get("distance_to_support_pct") < 0.5:
        if bearish_score > bullish_score:
            penalty_bear += 10
            reasons.append(f"Close to major support ({adv_sr.get('distance_to_support_pct'):.2f}% away)")
    bullish_score = max(0, bullish_score - penalty_bull)
    bearish_score = max(0, bearish_score - penalty_bear)
    if bullish_score >= bearish_score + 15:
        trend = "BULLISH"
    elif bearish_score >= bullish_score + 15:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    raw_strength = max(bullish_score, bearish_score)
    if mtf.get("alignment") in ["STRONG_BULLISH_ALIGNMENT", "STRONG_BEARISH_ALIGNMENT"]:
        raw_strength += 10
    elif mtf.get("alignment") == "MIXED":
        raw_strength -= 10
    if exhaustion.get("level") in ["HIGH", "EXTREME"]:
        raw_strength -= 15
    if late_entry_data.get("late_entry"):
        raw_strength -= 20
    setup_strength = min(100, max(0, int(raw_strength)))
    signal = "WAIT"
    trigger_condition = None
    news_blocks = (news_risk == "EXTREME" and not (mtf.get("mtf_score", 50) >= 95 or mtf.get("mtf_score", 50) <= 5))
    if not news_blocks:
        if bullish_score >= 60 and bullish_score >= bearish_score + 15:
            if mtf.get("mtf_score", 50) >= 55 and mtf.get("htf_trend") != "BEARISH":
                if not late_entry_data.get("late_entry") or late_entry_data.get("score",0) < 70:
                    if exhaustion.get("level") not in ["EXTREME"]:
                        room_ok = True
                        if adv_sr.get("distance_to_resistance_pct") is not None:
                            if 0 < adv_sr.get("distance_to_resistance_pct") < 0.3:
                                room_ok = False
                        if room_ok:
                            if resistance is not None and price is not None and resistance <= price:
                                trigger_condition = f"No realistic upside - price at/above resistance {round_price(resistance)} - wait for breakout"
                            else:
                                signal = "BUY"
                        else:
                            trigger_condition = f"Wait for break above {round_price(resistance)} resistance before BUY"
                    else:
                        trigger_condition = "Exhaustion high - wait for pullback toward EMA21 before BUY"
                else:
                    trigger_condition = f"Late entry - wait for pullback toward EMA21 ({round_price(ema21)}) before BUY"
            else:
                if mtf.get("htf_trend") == "BEARISH":
                    trigger_condition = f"HTF bearish ({mtf.get('h4_trend')}/{mtf.get('h1_trend')}) conflicts with bullish setup - wait for HTF alignment"
                else:
                    trigger_condition = f"MTF score {mtf.get('mtf_score',50):.0f} not strong enough for BUY - need >=55"
        elif bearish_score >= 60 and bearish_score >= bullish_score + 15:
            if mtf.get("mtf_score", 50) <= 45 and mtf.get("htf_trend") != "BULLISH":
                if not late_entry_data.get("late_entry") or late_entry_data.get("score",0) < 70:
                    if exhaustion.get("level") not in ["EXTREME"]:
                        room_ok = True
                        if adv_sr.get("distance_to_support_pct") is not None:
                            if 0 < adv_sr.get("distance_to_support_pct") < 0.3:
                                room_ok = False
                        if room_ok:
                            if support is not None and price is not None and support >= price:
                                trigger_condition = f"No realistic downside - price at/below support {round_price(support)} - wait for breakdown"
                            else:
                                signal = "SELL"
                        else:
                            trigger_condition = f"Wait for breakdown below {round_price(support)} support before SELL"
                    else:
                        trigger_condition = "Exhaustion high - wait for bounce toward EMA21 before SELL"
                else:
                    trigger_condition = f"Late entry - wait for bounce toward EMA21 ({round_price(ema21)}) before SELL"
            else:
                if mtf.get("htf_trend") == "BULLISH":
                    trigger_condition = f"HTF bullish ({mtf.get('h4_trend')}/{mtf.get('h1_trend')}) conflicts with bearish setup - wait for HTF alignment"
                else:
                    trigger_condition = f"MTF score {mtf.get('mtf_score',50):.0f} not strong enough for SELL - need <=45"
    else:
        trigger_condition = f"News risk {news_risk} EXTREME - avoid new entries, wait for volatility to settle"
    if signal == "WAIT" and not trigger_condition:
        if trend == "BULLISH":
            if late_entry_data.get("late_entry"):
                trigger_condition = f"Wait for pullback toward EMA21 ({round_price(ema21)}) or support ({round_price(support)}) before considering BUY"
            else:
                trigger_condition = f"Wait for 15M close above {round_price(resistance)} or EMA alignment confirmation for BUY"
        elif trend == "BEARISH":
            if late_entry_data.get("late_entry"):
                trigger_condition = f"Wait for bounce toward EMA21 ({round_price(ema21)}) or resistance ({round_price(resistance)}) before considering SELL"
            else:
                trigger_condition = f"Wait for 15M close below {round_price(support)} or EMA alignment confirmation for SELL"
        else:
            if mtf.get("alignment") == "MIXED":
                trigger_condition = f"Mixed MTF (4H:{mtf.get('h4_trend')} 1H:{mtf.get('h1_trend')} 15M:{mtf.get('m15_trend')}) - wait for alignment"
            else:
                trigger_condition = "Market structure mixed - wait for stronger directional confirmation and EMA alignment"
    entry_low = None
    entry_high = None
    stop_loss = None
    tp1 = None
    tp2 = None
    tp3 = None
    risk_distance = None
    risk_percent = None
    if signal == "BUY":
        support_level = nearest_support if nearest_support is not None else support
        base_low = price - (atr * 0.5) if atr else price * 0.995
        if support_level is not None and support_level < price:
            base_low = max(support_level, base_low)
        if ema21 is not None and ema21 < price and atr:
            if (price - ema21) / atr <= 1.5:
                base_low = max(base_low, ema21 - (atr * 0.15))
        entry_low = base_low
        entry_high = price - (atr * 0.05) if atr else price * 0.999
        if entry_low is None:
            entry_low = price - (atr * 0.35) if atr else price * 0.995
        if entry_high is None:
            entry_high = price - (atr * 0.05) if atr else price * 0.999
        if entry_low > price:
            entry_low = price - (atr * 0.3) if atr else price * 0.995
        if entry_high > price:
            entry_high = price - (atr * 0.05) if atr else price * 0.999
        if entry_low is not None and entry_high is not None and entry_high < entry_low:
            entry_high = entry_low + (atr * 0.2) if atr else entry_low * 1.001
            if entry_high > price:
                entry_high = price - (atr * 0.05) if atr else price
        swing_low = adv_structure.get("recent_swing_low") or adv_structure.get("swing_low")
        atr_stop = price - (atr * 1.4) if atr else price * 0.98
        candidates = []
        for c in [support_level, swing_low, atr_stop, nearest_support]:
            if c is not None and c < price:
                candidates.append(c)
        stop_loss = min(candidates) if candidates else atr_stop
        if stop_loss is not None:
            if entry_low is not None and stop_loss >= entry_low:
                stop_loss = entry_low - (atr * 0.5) if atr else entry_low * 0.998
            if stop_loss >= price:
                stop_loss = price - (atr * 1.0) if atr else price * 0.99
        risk = (price - stop_loss) if stop_loss is not None and price is not None else None
        if risk is None or risk <= 0:
            risk = (atr * 1.2) if atr else (price * 0.01 if price else 1)
            stop_loss = price - risk if price is not None else None
        if price is not None and risk is not None and risk > 0:
            tp1 = price + (risk * 1.0)
            tp2 = price + (risk * 2.0)
            tp3 = price + (risk * 3.0)
            if resistance is not None and resistance > price:
                if tp1 is not None and tp1 > resistance * 1.01:
                    tp1 = resistance
                if tp2 is not None and resistance * 0.98 <= tp2 <= resistance * 1.02:
                    tp2 = resistance
                if tp1 is not None and entry_high is not None and tp1 <= entry_high:
                    tp1 = None
                if tp2 is not None and entry_high is not None and tp2 <= entry_high:
                    tp2 = None
                if tp3 is not None and entry_high is not None and tp3 <= entry_high:
                    tp3 = None
    elif signal == "SELL":
        resistance_level = nearest_resistance if nearest_resistance is not None else resistance
        base_high = price + (atr * 0.5) if atr else price * 1.005
        if resistance_level is not None and resistance_level > price:
            base_high = min(resistance_level, base_high)
        if ema21 is not None and ema21 > price and atr:
            if (ema21 - price) / atr <= 1.5:
                base_high = min(base_high, ema21 + (atr * 0.15))
        entry_high = base_high
        entry_low = price + (atr * 0.05) if atr else price * 1.001
        if entry_high is None:
            entry_high = price + (atr * 0.35) if atr else price * 1.005
        if entry_low is None:
            entry_low = price + (atr * 0.05) if atr else price * 1.001
        if entry_high < price:
            entry_high = price + (atr * 0.3) if atr else price * 1.005
        if entry_low < price:
            entry_low = price + (atr * 0.05) if atr else price * 1.001
        if entry_low is not None and entry_high is not None and entry_low > entry_high:
            entry_low = entry_high - (atr * 0.2) if atr else entry_high * 0.999
            if entry_low < price:
                entry_low = price + (atr * 0.05) if atr else price
        swing_high = adv_structure.get("recent_swing_high") or adv_structure.get("swing_high")
        atr_stop = price + (atr * 1.4) if atr else price * 1.02
        candidates = []
        for c in [resistance_level, swing_high, atr_stop, nearest_resistance]:
            if c is not None and c > price:
                candidates.append(c)
        stop_loss = max(candidates) if candidates else atr_stop
        if stop_loss is not None:
            if entry_high is not None and stop_loss <= entry_high:
                stop_loss = entry_high + (atr * 0.5) if atr else entry_high * 1.002
            if stop_loss <= price:
                stop_loss = price + (atr * 1.0) if atr else price * 1.01
        risk = (stop_loss - price) if stop_loss is not None and price is not None else None
        if risk is None or risk <= 0:
            risk = (atr * 1.2) if atr else (price * 0.01 if price else 1)
            stop_loss = price + risk if price is not None else None
        if price is not None and risk is not None and risk > 0:
            tp1 = price - (risk * 1.0)
            tp2 = price - (risk * 2.0)
            tp3 = price - (risk * 3.0)
            if support is not None and support < price:
                if tp1 is not None and tp1 < support * 0.99:
                    tp1 = support
                if tp2 is not None and support * 0.98 <= tp2 <= support * 1.02:
                    tp2 = support
                if tp1 is not None and entry_low is not None and tp1 >= entry_low:
                    tp1 = None
                if tp2 is not None and entry_low is not None and tp2 >= entry_low:
                    tp2 = None
                if tp3 is not None and entry_low is not None and tp3 >= entry_low:
                    tp3 = None
    else:
        stop_loss = None
        tp1 = None
        tp2 = None
        tp3 = None
        if trend == "BULLISH":
            entry_low = max(nearest_support or support or (price - atr if atr and price else price * 0.99), price - (atr * 1.0) if atr and price else price * 0.99) if price else None
            entry_high = price
        elif trend == "BEARISH":
            entry_low = price
            entry_high = min(nearest_resistance or resistance or (price + atr if atr and price else price * 1.01), price + (atr * 1.0) if atr and price else price * 1.01) if price else None
        else:
            entry_low = nearest_support or support
            entry_high = nearest_resistance or resistance
    rr_tp1 = rr_tp2 = rr_tp3 = None
    if signal in ["BUY", "SELL"]:
        if stop_loss is not None and price is not None and atr is not None:
            try:
                if signal == "BUY":
                    risk_distance = price - stop_loss
                else:
                    risk_distance = stop_loss - price
                if risk_distance is not None and risk_distance <= 0:
                    risk_distance = None
                    risk_percent = None
                else:
                    if price != 0 and risk_distance is not None:
                        risk_percent = (risk_distance / abs(price)) * 100
                        if risk_percent < 0:
                            risk_percent = None
                            risk_distance = None
                    if risk_distance is not None and risk_distance > 0:
                        if tp1 is not None and price is not None:
                            rr_tp1 = abs(tp1 - price) / risk_distance if risk_distance != 0 else None
                            if rr_tp1 is not None and rr_tp1 < 0:
                                rr_tp1 = None
                        if tp2 is not None and price is not None:
                            rr_tp2 = abs(tp2 - price) / risk_distance if risk_distance != 0 else None
                            if rr_tp2 is not None and rr_tp2 < 0:
                                rr_tp2 = None
                        if tp3 is not None and price is not None:
                            rr_tp3 = abs(tp3 - price) / risk_distance if risk_distance != 0 else None
                            if rr_tp3 is not None and rr_tp3 < 0:
                                rr_tp3 = None
            except Exception:
                risk_distance = None
                risk_percent = None
    else:
        risk_distance = None
        risk_percent = None
    if signal == "BUY":
        setup = f"Bullish confirmation: MTF {mtf.get('mtf_score',0):.0f} ({mtf.get('alignment')}), HTF {mtf.get('htf_trend')}, {adv_structure.get('detail')}. Entry quality: {late_entry_data.get('quality')}."
    elif signal == "SELL":
        setup = f"Bearish confirmation: MTF {mtf.get('mtf_score',0):.0f} ({mtf.get('alignment')}), HTF {mtf.get('htf_trend')}, {adv_structure.get('detail')}. Entry quality: {late_entry_data.get('quality')}."
    elif trigger_condition:
        setup = trigger_condition
    elif trend == "BULLISH":
        setup = f"Bullish bias (MTF {mtf.get('mtf_score',0):.0f}) but entry confirmation not strong enough. {trigger_condition or ''}"
    elif trend == "BEARISH":
        setup = f"Bearish bias (MTF {mtf.get('mtf_score',0):.0f}) but entry confirmation not strong enough. {trigger_condition or ''}"
    else:
        setup = f"Market mixed (MTF {mtf.get('mtf_score',0):.0f} {mtf.get('alignment')}). Wait for stronger alignment. {trigger_condition or ''}"
    return {"symbol": symbol,"timeframe": primary_tf,"price": round_price(price),"signal": signal,"trend": trend,"structure": structure,"setup_strength": setup_strength,"support": round_price(support),"resistance": round_price(resistance),"ema9": round_price(ema9),"ema21": round_price(ema21),"ema50": round_price(ema50),"rsi": round(rsi, 2) if rsi is not None else None,"atr": round_price(atr),"entry_low": round_price(entry_low),"entry_high": round_price(entry_high),"entry_zone": (f"{round_price(entry_low)} - {round_price(entry_high)}" if entry_low is not None and entry_high is not None else None),"stop_loss": round_price(stop_loss) if stop_loss is not None else None,"tp1": round_price(tp1) if tp1 is not None else None,"tp2": round_price(tp2) if tp2 is not None else None,"tp3": round_price(tp3) if tp3 is not None else None,"take_profit": round_price(tp2) if tp2 is not None else None,"reason": setup,"reasons": reasons,"mtf_bias": mtf.get("mtf_bias"),"mtf_score": mtf.get("mtf_score"),"htf_trend": mtf.get("htf_trend"),"h4_trend": mtf.get("h4_trend"),"h1_trend": mtf.get("h1_trend"),"m15_trend": mtf.get("m15_trend"),"m5_trend": mtf.get("m5_trend"),"timeframe_alignment": mtf.get("timeframe_alignment"),"mtf_data": mtf,"structure_detail": adv_structure.get("detail"),"structure_data": adv_structure,"swing_high": round_price(adv_structure.get("swing_high")),"swing_low": round_price(adv_structure.get("swing_low")),"recent_swing_high": round_price(adv_structure.get("recent_swing_high")),"recent_swing_low": round_price(adv_structure.get("recent_swing_low")),"breakout": adv_structure.get("breakout", False),"breakdown": adv_structure.get("breakdown", False),"nearest_support": round_price(nearest_support),"nearest_resistance": round_price(nearest_resistance),"major_support": round_price(major_support),"major_resistance": round_price(major_resistance),"sr_data": adv_sr,"ema_alignment": ema_align.get("alignment"),"ema_alignment_data": ema_align,"ema_extended": ema_ext.get("extended_from_21") or ema_ext.get("extended_from_50"),"ema_extended_data": ema_ext,"rsi_state": rsi_state.get("state"),"rsi_state_data": rsi_state,"volatility": volatility.get("level"),"volatility_data": volatility,"exhaustion": exhaustion.get("level"),"exhaustion_score": exhaustion.get("score"),"exhaustion_reason": exhaustion.get("exhaustion_reason"),"exhaustion_data": exhaustion,"late_entry": late_entry_data.get("late_entry"),"late_entry_reason": late_entry_data.get("late_entry_reason"),"late_entry_data": late_entry_data,"entry_quality": late_entry_data.get("quality"),"risk_distance": round_price(risk_distance) if risk_distance is not None else None,"risk_percent": round(risk_percent, 3) if risk_percent is not None else None,"risk_reward_tp1": round(rr_tp1, 2) if rr_tp1 is not None else None,"risk_reward_tp2": round(rr_tp2, 2) if rr_tp2 is not None else None,"risk_reward_tp3": round(rr_tp3, 2) if rr_tp3 is not None else None,"news_risk": news_risk,"news_data": news_data,"trigger_condition": trigger_condition,"ideal_entry": (round_price((entry_low + entry_high) / 2) if entry_low is not None and entry_high is not None else round_price(price))}

# ===================== DAILY PLAN LOGIC =====================
def _validate_fresh_result(fresh: Dict[str, Any]) -> Optional[str]:
    """Zero-data safety: return error string if invalid, else None"""
    if not fresh:
        return "Empty analysis result"
    price = fresh.get("price")
    if price is None or not isinstance(price, (int, float)) or price <= 0:
        return f"Invalid price {price}"
    if fresh.get("ema9") is None or fresh.get("ema21") is None or fresh.get("ema50") is None:
        return "Missing EMA values"
    if fresh.get("atr") is None or fresh.get("atr") <= 0:
        return "Invalid ATR"
    if fresh.get("rsi") is None:
        return "Missing RSI"
    if fresh.get("support") is None or fresh.get("resistance") is None:
        # Not fatal if ATR fallback, but flag
        pass
    return None

def _should_invalidate_plan(active_plan: Dict[str, Any], fresh: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Decide if ACTIVE plan thesis is materially broken.
    Returns (should_invalidate, reason)
    """
    if not active_plan or not fresh:
        return False, ""
    direction = active_plan.get("direction") or active_plan.get("signal") or active_plan.get("status")
    # If active plan is WAIT, don't invalidate as BUY/SELL
    if direction not in ("BUY", "SELL"):
        return False, ""
    fresh_price = safe_float(fresh.get("price"))
    fresh_mtf = fresh.get("mtf_data") or {}
    fresh_htf_trend = fresh.get("htf_trend") or fresh_mtf.get("htf_trend") or "UNKNOWN"
    fresh_h4 = fresh.get("h4_trend") or fresh_mtf.get("h4_trend")
    fresh_h1 = fresh.get("h1_trend") or fresh_mtf.get("h1_trend")
    fresh_structure = fresh.get("structure_data") or {}
    fresh_breakdown = fresh_structure.get("breakdown", False) if isinstance(fresh_structure, dict) else False
    fresh_breakout = fresh_structure.get("breakout", False) if isinstance(fresh_structure, dict) else False
    fresh_news_risk = fresh.get("news_risk", "UNKNOWN")
    fresh_support = safe_float(fresh.get("support"))
    fresh_resistance = safe_float(fresh.get("resistance"))
    fresh_exhaustion = fresh.get("exhaustion_data") or {}
    fresh_exhaustion_level = fresh_exhaustion.get("level") if isinstance(fresh_exhaustion, dict) else fresh.get("exhaustion")
    orig_entry_low = safe_float(active_plan.get("entry_low"))
    orig_entry_high = safe_float(active_plan.get("entry_high"))
    orig_sl = safe_float(active_plan.get("stop_loss"))
    # Material change checks
    reasons = []
    # 1. HTF trend reversal - 4H and 1H both flipped opposite to plan
    if direction == "BUY":
        if fresh_h4 == "BEARISH" and fresh_h1 == "BEARISH" and fresh_htf_trend == "BEARISH":
            reasons.append(f"HTF reversal: 4H {fresh_h4} + 1H {fresh_h1} bearish vs BUY plan")
        # Support break invalidates BUY
        if fresh_breakdown and fresh_support is not None and fresh_price is not None and fresh_price < fresh_support:
            reasons.append(f"Support failure and breakdown below {fresh_support}")
        # SL area invalidated before entry: price already far below SL
        if orig_sl is not None and fresh_price is not None and fresh_price < orig_sl * 0.998:
            reasons.append(f"Price {fresh_price} below original SL {orig_sl} - thesis invalidated")
    elif direction == "SELL":
        if fresh_h4 == "BULLISH" and fresh_h1 == "BULLISH" and fresh_htf_trend == "BULLISH":
            reasons.append(f"HTF reversal: 4H {fresh_h4} + 1H {fresh_h1} bullish vs SELL plan")
        if fresh_breakout and fresh_resistance is not None and fresh_price is not None and fresh_price > fresh_resistance:
            reasons.append(f"Resistance break and breakout above {fresh_resistance}")
        if orig_sl is not None and fresh_price is not None and fresh_price > orig_sl * 1.002:
            reasons.append(f"Price {fresh_price} above original SL {orig_sl} - thesis invalidated")
    # 2. News risk EXTREME change
    old_news = active_plan.get("news_risk")
    if old_news not in ("HIGH", "EXTREME") and fresh_news_risk == "EXTREME":
        reasons.append(f"News risk escalated to EXTREME (was {old_news}) - high volatility")
    # 3. Strong opposite momentum confirmed across timeframes
    mtf_score = fresh.get("mtf_score") or fresh_mtf.get("mtf_score") or 50
    if direction == "BUY" and mtf_score <= 25 and fresh.get("timeframe_alignment") == "STRONG_BEARISH_ALIGNMENT":
        reasons.append(f"MTF strongly bearish {mtf_score}/100 vs BUY plan")
    if direction == "SELL" and mtf_score >= 75 and fresh.get("timeframe_alignment") == "STRONG_BULLISH_ALIGNMENT":
        reasons.append(f"MTF strongly bullish {mtf_score}/100 vs SELL plan")
    # 4. Structure break opposite
    if direction == "BUY" and fresh.get("structure") == "BEARISH" and fresh_breakdown:
        reasons.append("Bearish structure break + breakdown - BUY thesis no longer valid")
    if direction == "SELL" and fresh.get("structure") == "BULLISH" and fresh_breakout:
        reasons.append("Bullish structure break + breakout - SELL thesis no longer valid")
    # 5. Exhaustion EXTREME against plan
    if fresh_exhaustion_level == "EXTREME":
        if direction == "BUY" and fresh.get("rsi", 0) >= 78:
            reasons.append(f"Exhaustion EXTREME with RSI {fresh.get('rsi')} - BUY extended")
        if direction == "SELL" and fresh.get("rsi", 100) <= 22:
            reasons.append(f"Exhaustion EXTREME with RSI {fresh.get('rsi')} - SELL extended")
    # Require material reason
    if reasons:
        return True, "; ".join(reasons)
    return False, ""

def _calculate_entry_status(active_plan: Dict[str, Any], current_price: float, atr: float) -> Dict[str, Any]:
    """Return entry status for ACTIVE plan"""
    entry_low = safe_float(active_plan.get("entry_low"))
    entry_high = safe_float(active_plan.get("entry_high"))
    direction = active_plan.get("direction")
    if None in (entry_low, entry_high, current_price):
        return {"status": "UNKNOWN", "label": "UNKNOWN", "missed": False, "reason": "Missing entry zone or price"}
    # Normalize low/high
    low = min(entry_low, entry_high)
    high = max(entry_low, entry_high)
    if direction == "BUY":
        # BUY entry should be at or below current price ideally, or price retracing into zone
        if current_price > high + (atr * 2.5 if atr else (high*0.005)):
            distance = current_price - high
            return {"status": "MISSED", "label": "MISSED", "missed": True, "distance": distance, "reason": f"Price moved beyond entry zone by {round_price(distance)}"}
        elif current_price >= low and current_price <= high:
            return {"status": "GOOD_ENTRY_WINDOW", "label": "GOOD ENTRY WINDOW", "missed": False, "reason": "Price inside entry zone"}
        elif current_price < low and current_price >= low - (atr * 0.8 if atr else 0):
            return {"status": "EARLY_ENTRY", "label": "EARLY / WAITING FOR CONFIRMATION", "missed": False, "reason": "Price below entry, waiting for bullish confirmation"}
        elif current_price < low:
            return {"status": "WAITING_FOR_CONFIRMATION", "label": "WAITING FOR PULLBACK", "missed": False, "reason": f"Waiting for pullback to {low}-{high}"}
        else:
            return {"status": "WAITING", "label": "WAITING", "missed": False, "reason": "Monitoring"}
    else:  # SELL
        if current_price < low - (atr * 2.5 if atr else (low*0.005)):
            distance = low - current_price
            return {"status": "MISSED", "label": "MISSED", "missed": True, "distance": distance, "reason": f"Price moved beyond entry zone by {round_price(distance)}"}
        elif current_price >= low and current_price <= high:
            return {"status": "GOOD_ENTRY_WINDOW", "label": "GOOD ENTRY WINDOW", "missed": False, "reason": "Price inside entry zone"}
        elif current_price > high and current_price <= high + (atr * 0.8 if atr else 0):
            return {"status": "EARLY_ENTRY", "label": "EARLY / WAITING FOR CONFIRMATION", "missed": False, "reason": "Price above entry, waiting for bearish confirmation"}
        elif current_price > high:
            return {"status": "WAITING_FOR_CONFIRMATION", "label": "WAITING FOR BOUNCE", "missed": False, "reason": f"Waiting for bounce to {low}-{high}"}
        else:
            return {"status": "WAITING", "label": "WAITING", "missed": False, "reason": "Monitoring"}

def _create_daily_plan_from_fresh(fresh: Dict[str, Any], trading_date: str, replacement_of: Optional[str] = None) -> Dict[str, Any]:
    """Convert fresh analysis into persistent daily plan row"""
    signal = fresh.get("signal", "WAIT")
    direction = signal if signal in ("BUY", "SELL") else "WAIT"
    plan_id = str(uuid.uuid4())
    now_iso = get_current_utc_iso()
    # Confidence is setup_strength with HTF penalty already applied in fresh
    confidence = fresh.get("setup_strength", 0)
    # Clamp confidence for countertrend
    h4 = fresh.get("h4_trend")
    h1 = fresh.get("h1_trend")
    if direction == "BUY" and h4 == "BEARISH" and h1 == "BEARISH":
        confidence = min(confidence, 65)
    if direction == "SELL" and h4 == "BULLISH" and h1 == "BULLISH":
        confidence = min(confidence, 65)
    if fresh.get("timeframe_alignment") == "MIXED":
        confidence = min(confidence, 70)
    raw_json_str = json.dumps(fresh, default=str)
    row = {
        "daily_plan_id": plan_id,
        "symbol": fresh.get("symbol"),
        "trading_date": trading_date,
        "status": "ACTIVE" if direction in ("BUY", "SELL") else "WAIT",
        "direction": direction,
        "entry_low": fresh.get("entry_low"),
        "entry_high": fresh.get("entry_high"),
        "stop_loss": fresh.get("stop_loss"),
        "tp1": fresh.get("tp1"),
        "tp2": fresh.get("tp2"),
        "tp3": fresh.get("tp3"),
        "confidence": int(confidence) if confidence is not None else 0,
        "strength": int(fresh.get("setup_strength", 0) or 0),
        "timeframe": fresh.get("timeframe"),
        "mtf_bias": fresh.get("mtf_bias"),
        "mtf_score": fresh.get("mtf_score"),
        "h4_trend": fresh.get("h4_trend"),
        "h1_trend": fresh.get("h1_trend"),
        "m15_trend": fresh.get("m15_trend"),
        "m5_trend": fresh.get("m5_trend"),
        "timeframe_alignment": fresh.get("timeframe_alignment"),
        "structure": fresh.get("structure"),
        "structure_detail": fresh.get("structure_detail"),
        "support": fresh.get("support"),
        "resistance": fresh.get("resistance"),
        "nearest_support": fresh.get("nearest_support"),
        "nearest_resistance": fresh.get("nearest_resistance"),
        "major_support": fresh.get("major_support"),
        "major_resistance": fresh.get("major_resistance"),
        "rsi": fresh.get("rsi"),
        "ema9": fresh.get("ema9"),
        "ema21": fresh.get("ema21"),
        "ema50": fresh.get("ema50"),
        "atr": fresh.get("atr"),
        "news_risk": fresh.get("news_risk"),
        "reason": fresh.get("reason"),
        "reasons_json": json.dumps(fresh.get("reasons", []), default=str),
        "entry_quality": fresh.get("entry_quality"),
        "original_price": fresh.get("price"),
        "created_at": now_iso,
        "updated_at": now_iso,
        "invalidated_at": None,
        "invalidation_reason": None,
        "replacement_of": replacement_of,
        "invalidated_direction": None,
        "raw_json": raw_json_str,
    }
    return row

def _build_result_from_plan(plan_row: Dict[str, Any], fresh: Dict[str, Any], current_price_override: Optional[float] = None) -> Dict[str, Any]:
    """Build final analyze_market result from stored plan + current monitoring"""
    # Use stored plan values for entry/SL/TP but use fresh for current price monitoring
    raw = plan_row.get("raw") or {}
    if not raw:
        try:
            raw = json.loads(plan_row.get("raw_json") or "{}")
        except Exception:
            raw = {}
    # Determine current price
    current_price = current_price_override
    if current_price is None:
        current_price = fresh.get("price") if fresh else plan_row.get("original_price")
    atr = plan_row.get("atr") or fresh.get("atr") if fresh else None
    entry_status = _calculate_entry_status(plan_row, safe_float(current_price), safe_float(atr))
    # Build output preserving all legacy fields from raw, but overriding with stored plan
    result = dict(raw)  # start from original fresh analysis
    # Override persistent fields
    result["symbol"] = plan_row.get("symbol")
    result["trading_date"] = plan_row.get("trading_date")
    result["daily_plan_id"] = plan_row.get("daily_plan_id")
    result["plan_status"] = plan_row.get("status")
    result["daily_plan_status"] = plan_row.get("status")
    result["status"] = plan_row.get("status")
    result["direction"] = plan_row.get("direction")
    result["signal"] = plan_row.get("direction")
    # Keep original entry/SL/TP
    result["entry_low"] = round_price(plan_row.get("entry_low"))
    result["entry_high"] = round_price(plan_row.get("entry_high"))
    result["entry_zone"] = f"{round_price(plan_row.get('entry_low'))} - {round_price(plan_row.get('entry_high'))}" if plan_row.get("entry_low") is not None and plan_row.get("entry_high") is not None else None
    result["stop_loss"] = round_price(plan_row.get("stop_loss"))
    result["tp1"] = round_price(plan_row.get("tp1"))
    result["tp2"] = round_price(plan_row.get("tp2"))
    result["tp3"] = round_price(plan_row.get("tp3"))
    result["take_profit"] = round_price(plan_row.get("tp2"))
    result["setup_strength"] = plan_row.get("strength") or plan_row.get("confidence") or result.get("setup_strength")
    result["confidence"] = plan_row.get("confidence")
    result["strength"] = plan_row.get("strength")
    # Preserve original reasoning
    result["reason"] = plan_row.get("reason") or result.get("reason")
    try:
        result["reasons"] = json.loads(plan_row.get("reasons_json") or "[]") or result.get("reasons", [])
    except Exception:
        result["reasons"] = result.get("reasons", [])
    # MTF fields from plan
    result["mtf_bias"] = plan_row.get("mtf_bias") or result.get("mtf_bias")
    result["mtf_score"] = plan_row.get("mtf_score") or result.get("mtf_score")
    result["h4_trend"] = plan_row.get("h4_trend") or result.get("h4_trend")
    result["h1_trend"] = plan_row.get("h1_trend") or result.get("h1_trend")
    result["m15_trend"] = plan_row.get("m15_trend") or result.get("m15_trend")
    result["m5_trend"] = plan_row.get("m5_trend") or result.get("m5_trend")
    result["timeframe_alignment"] = plan_row.get("timeframe_alignment") or result.get("timeframe_alignment")
    result["htf_trend"] = result.get("htf_trend") or f"{plan_row.get('h4_trend')}/{plan_row.get('h1_trend')}"
    # Keep current price monitoring
    result["price"] = round_price(current_price)
    result["current_price"] = round_price(current_price)
    result["original_price"] = round_price(plan_row.get("original_price"))
    # Entry status
    result["entry_status"] = entry_status.get("status")
    result["entry_status_label"] = entry_status.get("label")
    result["entry_status_reason"] = entry_status.get("reason")
    result["is_entry_missed"] = entry_status.get("missed", False)
    # Ideal entry is original
    result["ideal_entry"] = round_price((plan_row.get("entry_low") + plan_row.get("entry_high")) / 2) if plan_row.get("entry_low") is not None and plan_row.get("entry_high") is not None else result.get("ideal_entry")
    # Daily plan meta
    result["daily_plan_id"] = plan_row.get("daily_plan_id")
    result["trading_date"] = plan_row.get("trading_date")
    result["created_at"] = plan_row.get("created_at")
    result["updated_at"] = plan_row.get("updated_at")
    result["invalidated_at"] = plan_row.get("invalidated_at")
    result["invalidation_reason"] = plan_row.get("invalidation_reason")
    result["replacement_of"] = plan_row.get("replacement_of")
    result["plan_created_at"] = plan_row.get("created_at")
    # Preserve other fields from fresh that are monitoring
    if fresh:
        # Update volatility, rsi_state etc for monitoring but keep original thesis fields untouched for ACTIVE
        result["rsi"] = round(fresh.get("rsi"), 2) if fresh.get("rsi") is not None else result.get("rsi")
        result["atr"] = round_price(fresh.get("atr")) or result.get("atr")
        result["news_risk"] = fresh.get("news_risk") or result.get("news_risk")
        result["news_data"] = fresh.get("news_data") or result.get("news_data")
        result["mtf_data"] = fresh.get("mtf_data") or result.get("mtf_data")
        # Current triggers for monitoring
        result["current_trigger"] = fresh.get("trigger_condition")
        # Keep fresh price for display
        result["fresh_price"] = round_price(fresh.get("price"))
    # Ensure all legacy fields exist
    result.setdefault("timeframe", plan_row.get("timeframe") or "15m")
    result.setdefault("ema9", round_price(plan_row.get("ema9")))
    result.setdefault("ema21", round_price(plan_row.get("ema21")))
    result.setdefault("ema50", round_price(plan_row.get("ema50")))
    result.setdefault("support", round_price(plan_row.get("support")))
    result.setdefault("resistance", round_price(plan_row.get("resistance")))
    return result

def _build_wait_result(symbol: str, trading_date: str, reason: str, fresh: Optional[Dict] = None, existing_plan: Optional[Dict] = None, status: str = "WAIT") -> Dict[str, Any]:
    """Build WAIT / INVALIDATED result"""
    price = None
    if fresh:
        price = fresh.get("price")
    elif existing_plan:
        price = existing_plan.get("original_price")
    base = fresh or {}
    if not base and existing_plan and existing_plan.get("raw"):
        base = existing_plan.get("raw")
    result = dict(base) if base else {}
    result["symbol"] = symbol
    result["trading_date"] = trading_date
    result["signal"] = "WAIT"
    result["direction"] = "WAIT"
    result["plan_status"] = status
    result["daily_plan_status"] = status
    result["status"] = status
    result["reason"] = reason
    result["trigger_condition"] = reason
    result["price"] = round_price(price) if price else (round_price(base.get("price")) if base else None)
    if status == "INVALIDATED":
        result["plan_status"] = "INVALIDATED"
        result["daily_plan_status"] = "INVALIDATED"
        if existing_plan:
            result["previous_plan"] = existing_plan.get("direction")
            result["invalidated_direction"] = existing_plan.get("direction")
            result["previous_daily_plan_id"] = existing_plan.get("daily_plan_id")
            result["original_entry_low"] = round_price(existing_plan.get("entry_low"))
            result["original_entry_high"] = round_price(existing_plan.get("entry_high"))
            result["original_stop_loss"] = round_price(existing_plan.get("stop_loss"))
    result.setdefault("setup_strength", 0)
    result.setdefault("confidence", 0)
    result.setdefault("strength", 0)
    result.setdefault("timeframe", "15m")
    result.setdefault("ema9", None)
    result.setdefault("ema21", None)
    result.setdefault("ema50", None)
    result.setdefault("rsi", None)
    result.setdefault("atr", None)
    result.setdefault("support", None)
    result.setdefault("resistance", None)
    result.setdefault("entry_low", None)
    result.setdefault("entry_high", None)
    result.setdefault("entry_zone", None)
    result.setdefault("stop_loss", None)
    result.setdefault("tp1", None)
    result.setdefault("tp2", None)
    result.setdefault("tp3", None)
    result.setdefault("take_profit", None)
    result.setdefault("reasons", [reason])
    result.setdefault("mtf_bias", base.get("mtf_bias"))
    result.setdefault("mtf_score", base.get("mtf_score"))
    result.setdefault("htf_trend", base.get("htf_trend"))
    result.setdefault("h4_trend", base.get("h4_trend"))
    result.setdefault("h1_trend", base.get("h1_trend"))
    result.setdefault("m15_trend", base.get("m15_trend"))
    result.setdefault("m5_trend", base.get("m5_trend"))
    result.setdefault("timeframe_alignment", base.get("timeframe_alignment"))
    result.setdefault("structure", base.get("structure", "NEUTRAL"))
    result.setdefault("structure_detail", base.get("structure_detail"))
    result.setdefault("nearest_support", base.get("nearest_support"))
    result.setdefault("nearest_resistance", base.get("nearest_resistance"))
    result.setdefault("major_support", base.get("major_support"))
    result.setdefault("major_resistance", base.get("major_resistance"))
    result.setdefault("news_risk", base.get("news_risk", "UNKNOWN"))
    result.setdefault("news_data", base.get("news_data"))
    result.setdefault("entry_quality", base.get("entry_quality", "UNKNOWN"))
    result.setdefault("ideal_entry", base.get("price"))
    # Entry status for WAIT -> always WAITING
    result.setdefault("entry_status", "WAITING" if status == "WAIT" else "INVALIDATED")
    result.setdefault("entry_status_label", "WAITING" if status == "WAIT" else "PLAN INVALIDATED")
    result.setdefault("entry_status_reason", reason)
    result.setdefault("is_entry_missed", False)
    result.setdefault("current_price", result.get("price"))
    result.setdefault("original_price", result.get("price"))
    if existing_plan:
        result["daily_plan_id"] = existing_plan.get("daily_plan_id")
        result["created_at"] = existing_plan.get("created_at")
        result["updated_at"] = get_current_utc_iso()
        result["invalidated_at"] = existing_plan.get("invalidated_at") or get_current_utc_iso()
        result["invalidation_reason"] = reason
    return result


# ===================== PUBLIC API: analyze_market =====================
def analyze_market(symbol, timeframe="15m"):
    """
    Persistent Daily Trade Plan System
    - One ACTIVE plan per symbol per trading date
    - Returns same plan on repeated calls
    - Invalidates on material market change
    - Preserves original entry/SL/TP
    """
    symbol = symbol.upper().strip()
    trading_date = get_trading_date()
    # Expire old plans for this symbol
    try:
        _expire_old_plans(symbol, trading_date)
    except Exception as e:
        logger.debug(f"Expire old plans failed: {e}")
    # Load existing plan for today
    existing_plan = None
    try:
        existing_plan = _load_active_plan_for_today(symbol, trading_date)
    except Exception as e:
        logger.warning(f"Failed to load daily plan for {symbol} {trading_date}: {e}")
        existing_plan = None
    # Try fresh analysis for monitoring / validation
    fresh = None
    fresh_error = None
    try:
        fresh = _analyze_market_fresh(symbol, timeframe)
    except Exception as e:
        fresh_error = str(e)
        logger.warning(f"Fresh market analysis failed for {symbol}: {e}")
    # Zero-data safety
    if fresh is None and existing_plan is None:
        # No data and no plan -> WAIT DATA UNAVAILABLE
        return _build_wait_result(
            symbol=symbol,
            trading_date=trading_date,
            reason=f"DATA UNAVAILABLE: {fresh_error or 'Market data fetch failed - Twelve Data API error or timeout'}",
            fresh=None,
            existing_plan=None,
            status="WAIT"
        )
    if fresh is not None:
        validation_error = _validate_fresh_result(fresh)
        if validation_error:
            # If we have existing ACTIVE plan, keep it but note data issue
            if existing_plan and existing_plan.get("status") == "ACTIVE":
                # Return existing plan with warning
                result = _build_result_from_plan(existing_plan, fresh)
                result["data_warning"] = f"Fresh validation failed: {validation_error} - showing stored ACTIVE plan"
                return result
            # No valid existing plan -> WAIT
            return _build_wait_result(
                symbol=symbol,
                trading_date=trading_date,
                reason=f"DATA UNAVAILABLE: {validation_error} - {fresh_error or ''}".strip(),
                fresh=fresh,
                existing_plan=existing_plan,
                status="WAIT"
            )
    # Case 1: Existing ACTIVE plan
    if existing_plan and existing_plan.get("status") == "ACTIVE":
        # Check if market materially changed -> invalidate
        if fresh:
            should_invalidate, invalidation_reason = _should_invalidate_plan(existing_plan, fresh)
            if should_invalidate:
                # Mark as INVALIDATED
                try:
                    with _daily_plan_lock:
                        conn = _connect_daily_db()
                        try:
                            conn.execute("""
                                UPDATE daily_plans SET status='INVALIDATED', invalidated_at=?, invalidation_reason=?, updated_at=?, invalidated_direction=?
                                WHERE daily_plan_id=?
                            """, (get_current_utc_iso(), invalidation_reason, get_current_utc_iso(), existing_plan.get("direction"), existing_plan.get("daily_plan_id")))
                            conn.commit()
                        finally:
                            conn.close()
                    existing_plan["status"] = "INVALIDATED"
                    existing_plan["invalidated_at"] = get_current_utc_iso()
                    existing_plan["invalidation_reason"] = invalidation_reason
                except Exception as e:
                    logger.warning(f"Failed to mark plan invalidated: {e}")
                # Return WAIT / PLAN INVALIDATED, not immediate opposite trade
                return _build_wait_result(
                    symbol=symbol,
                    trading_date=trading_date,
                    reason=f"PLAN INVALIDATED: Previous {existing_plan.get('direction')} plan invalidated. Reason: {invalidation_reason}. Action: WAIT for new confirmed setup.",
                    fresh=fresh,
                    existing_plan=existing_plan,
                    status="INVALIDATED"
                )
            else:
                # Still valid -> return same ACTIVE plan with updated monitoring
                return _build_result_from_plan(existing_plan, fresh)
        else:
            # No fresh data, return stored plan
            return _build_result_from_plan(existing_plan, existing_plan.get("raw") or {}, current_price_override=existing_plan.get("original_price"))
    # Case 2: Existing WAIT or INVALIDATED plan - check if new confirmed setup exists
    if existing_plan and existing_plan.get("status") in ("WAIT", "INVALIDATED"):
        if fresh and fresh.get("signal") in ("BUY", "SELL"):
            # Only create replacement if fresh signal is strong and not counter to strong HTF without justification
            # Require setup_strength >= 60 and not late entry
            if fresh.get("setup_strength", 0) >= 60 and not fresh.get("late_entry"):
                # Create REPLACED new plan
                try:
                    # Mark old as REPLACED
                    with _daily_plan_lock:
                        conn = _connect_daily_db()
                        try:
                            conn.execute("""
                                UPDATE daily_plans SET status='REPLACED', updated_at=?
                                WHERE daily_plan_id=?
                            """, (get_current_utc_iso(), existing_plan.get("daily_plan_id")))
                            conn.commit()
                        finally:
                            conn.close()
                except Exception as e:
                    logger.warning(f"Failed to mark old plan REPLACED: {e}")
                new_plan_row = _create_daily_plan_from_fresh(fresh, trading_date, replacement_of=existing_plan.get("daily_plan_id"))
                try:
                    _save_plan_row(new_plan_row)
                except Exception as e:
                    logger.warning(f"Failed to save new replacement plan: {e}")
                # Return new ACTIVE plan
                return _build_result_from_plan(new_plan_row, fresh)
            else:
                # Fresh not strong enough -> keep WAIT
                return _build_wait_result(
                    symbol=symbol,
                    trading_date=trading_date,
                    reason=f"WAIT: Previous plan {existing_plan.get('status')} - no strong new setup confirmed yet. {fresh.get('trigger_condition') or fresh.get('reason') or 'Waiting for confirmation'}",
                    fresh=fresh,
                    existing_plan=existing_plan,
                    status="WAIT"
                )
        else:
            # No new setup -> keep WAIT
            return _build_wait_result(
                symbol=symbol,
                trading_date=trading_date,
                reason=existing_plan.get("invalidation_reason") or existing_plan.get("reason") or (fresh.get("trigger_condition") if fresh else "Waiting for valid setup"),
                fresh=fresh,
                existing_plan=existing_plan,
                status=existing_plan.get("status", "WAIT")
            )
    # Case 3: No existing plan for today -> create new daily plan from fresh
    if fresh:
        if fresh.get("signal") in ("BUY", "SELL"):
            new_plan_row = _create_daily_plan_from_fresh(fresh, trading_date)
            try:
                _save_plan_row(new_plan_row)
            except Exception as e:
                logger.warning(f"Failed to save new daily plan: {e}")
            return _build_result_from_plan(new_plan_row, fresh)
        else:
            # Fresh says WAIT -> create WAIT plan for today to avoid re-analyzing constantly
            wait_plan = _create_daily_plan_from_fresh(fresh, trading_date)
            # Override status to WAIT
            wait_plan["status"] = "WAIT"
            wait_plan["direction"] = "WAIT"
            try:
                _save_plan_row(wait_plan)
            except Exception as e:
                logger.warning(f"Failed to save WAIT daily plan: {e}")
            return _build_wait_result(
                symbol=symbol,
                trading_date=trading_date,
                reason=fresh.get("trigger_condition") or fresh.get("reason") or "Market conditions do not provide valid entry - WAIT",
                fresh=fresh,
                existing_plan=wait_plan,
                status="WAIT"
            )
    # Fallback
    return _build_wait_result(
        symbol=symbol,
        trading_date=trading_date,
        reason=f"DATA UNAVAILABLE: {fresh_error or 'Unknown error'}",
        fresh=None,
        existing_plan=existing_plan,
        status="WAIT"
    )

# ===================== ADDITIONAL HELPERS FOR TELEGRAM BOT COMPAT =====================
def get_daily_plan(symbol: str, trading_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Helper for bot to fetch daily plan without triggering new analysis"""
    if trading_date is None:
        trading_date = get_trading_date()
    symbol = symbol.upper().strip()
    try:
        return _load_active_plan_for_today(symbol, trading_date)
    except Exception:
        return None

def get_all_daily_plans(trading_date: Optional[str] = None) -> List[Dict[str, Any]]:
    if trading_date is None:
        trading_date = get_trading_date()
    with _daily_plan_lock:
        conn = _connect_daily_db()
        try:
            rows = conn.execute("SELECT * FROM daily_plans WHERE trading_date = ? ORDER BY datetime(updated_at) DESC", (trading_date,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def invalidate_daily_plan(symbol: str, reason: str = "Manual invalidation") -> bool:
    symbol = symbol.upper().strip()
    trading_date = get_trading_date()
    plan = _load_active_plan_for_today(symbol, trading_date)
    if not plan:
        return False
    try:
        with _daily_plan_lock:
            conn = _connect_daily_db()
            try:
                conn.execute("""
                    UPDATE daily_plans SET status='INVALIDATED', invalidated_at=?, invalidation_reason=?, updated_at=?
                    WHERE daily_plan_id=?
                """, (get_current_utc_iso(), reason, get_current_utc_iso(), plan.get("daily_plan_id")))
                conn.commit()
            finally:
                conn.close()
        return True
    except Exception:
        return False
