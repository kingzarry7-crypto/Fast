import requests
import config
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

# =========================================================
# 👑 KING ZARRY AI
# MARKET ENGINE - PRODUCTION MULTI-TIMEFRAME
# =========================================================
#
# Flow: 4H -> 1H -> 15M -> 5M -> News -> Late Entry -> Exhaustion -> Volatility -> Final Setup -> Entry/SL/TP
# Preserves backward compatibility with existing Telegram bot callers
#
# =========================================================

logger = logging.getLogger("king_zarry_market")

# =========================================================
# CONFIGURATION
# =========================================================

TWELVE_DATA_API_KEY = getattr(
    config,
    "TWELVE_DATA_API_KEY",
    None
)

TWELVE_DATA_URL = getattr(
    config,
    "TWELVE_DATA_URL",
    "https://api.twelvedata.com"
).rstrip("/")

# =========================================================
# TIMEFRAME MAP
# =========================================================

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

# Multi-timeframe weights - mathematically sensible: HTF dominates, LTF for timing only
MTF_WEIGHTS = {
    "4h": 0.35,
    "1h": 0.30,
    "15m": 0.25,
    "5m": 0.10,
}

PRIMARY_TF = "15m"

# =========================================================
# TIMEFRAME
# =========================================================

def normalize_timeframe(timeframe):
    timeframe = str(timeframe).lower().strip()
    return TIMEFRAME_MAP.get(timeframe, timeframe)

# =========================================================
# NUMBER HELPERS
# =========================================================

def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def round_price(price):
    if price is None:
        return None
    price = float(price)
    if abs(price) >= 1000:
        return round(price, 2)
    if abs(price) >= 100:
        return round(price, 3)
    if abs(price) >= 1:
        return round(price, 4)
    return round(price, 6)

# =========================================================
# GET CURRENT PRICE
# =========================================================

def get_price(symbol):
    if not TWELVE_DATA_API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is missing.")
    response = requests.get(
        f"{TWELVE_DATA_URL}/price",
        params={
            "symbol": symbol.upper().strip(),
            "apikey": TWELVE_DATA_API_KEY
        },
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

# =========================================================
# GET CANDLES
# =========================================================

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

# =========================================================
# EMA
# =========================================================

def calculate_ema(values, period):
    if not values:
        return None
    if len(values) < period:
        return sum(values) / len(values)
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result

# =========================================================
# RSI
# =========================================================

def calculate_rsi(values, period=14):
    if not values or len(values) < 2:
        return 50.0
    actual_period = min(period, len(values) - 1)
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
    avg_gain = sum(gains[:actual_period]) / actual_period
    avg_loss = sum(losses[:actual_period]) / actual_period
    for i in range(actual_period, len(gains)):
        avg_gain = ((avg_gain * (actual_period - 1)) + gains[i]) / actual_period
        avg_loss = ((avg_loss * (actual_period - 1)) + losses[i]) / actual_period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =========================================================
# ATR
# =========================================================

def calculate_atr(candles, period=14):
    if not candles or len(candles) < 2:
        return None
    true_ranges = []
    for i in range(1, len(candles)):
        high = safe_float(candles[i]["high"])
        low = safe_float(candles[i]["low"])
        previous_close = safe_float(candles[i - 1]["close"])
        if None in (high, low, previous_close):
            continue
        tr = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close)
        )
        true_ranges.append(tr)
    if not true_ranges:
        return safe_float(candles[-1]["close"], 1.0) * 0.005
    actual_period = min(period, len(true_ranges))
    atr = sum(true_ranges[:actual_period]) / actual_period
    for tr in true_ranges[actual_period:]:
        atr = (((atr * (actual_period - 1)) + tr) / actual_period)
    return atr

# =========================================================
# CANDLE BODY
# =========================================================

def candle_body(candle):
    open_price = safe_float(candle["open"])
    close_price = safe_float(candle["close"])
    if open_price is None or close_price is None:
        return 0
    return abs(close_price - open_price)

# =========================================================
# BULLISH / BEARISH CANDLE
# =========================================================

def is_bullish_candle(candle):
    open_price = safe_float(candle["open"])
    close_price = safe_float(candle["close"])
    return (
        open_price is not None
        and close_price is not None
        and close_price > open_price
    )

def is_bearish_candle(candle):
    open_price = safe_float(candle["open"])
    close_price = safe_float(candle["close"])
    return (
        open_price is not None
        and close_price is not None
        and close_price < open_price
    )

# =========================================================
# MARKET STRUCTURE - ORIGINAL PRESERVED
# =========================================================

def determine_structure(candles):
    if len(candles) < 10:
        return "NEUTRAL"
    recent = candles[-20:] if len(candles) >= 20 else candles
    highs = [safe_float(c["high"]) for c in recent]
    lows = [safe_float(c["low"]) for c in recent]
    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]
    if len(highs) < 4 or len(lows) < 4:
        return "NEUTRAL"
    mid = len(highs) // 2
    previous_high = max(highs[:mid])
    recent_high = max(highs[mid:])
    previous_low = min(lows[:mid])
    recent_low = min(lows[mid:])
    if recent_high > previous_high and recent_low > previous_low:
        return "BULLISH"
    if recent_high < previous_high and recent_low < previous_low:
        return "BEARISH"
    return "NEUTRAL"

# =========================================================
# SUPPORT / RESISTANCE - ORIGINAL PRESERVED
# =========================================================

def calculate_support_resistance(candles):
    recent = candles[-30:] if len(candles) >= 30 else candles
    highs = [safe_float(c["high"]) for c in recent]
    lows = [safe_float(c["low"]) for c in recent]
    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]
    if not highs or not lows:
        return None, None
    support = min(lows)
    resistance = max(highs)
    return support, resistance

# =========================================================
# MOMENTUM - ORIGINAL PRESERVED
# =========================================================

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

# =========================================================
# ADVANCED ANALYSIS - NEW PRODUCTION FEATURES
# =========================================================

def find_swing_points(candles: List[Dict], lookback: int = 5) -> Dict[str, Any]:
    """Find recent swing highs/lows using local extrema"""
    if len(candles) < lookback * 2 + 1:
        return {"swing_high": None, "swing_low": None, "recent_swing_high": None, "recent_swing_low": None}
    highs = [(i, safe_float(c["high"])) for i, c in enumerate(candles)]
    lows = [(i, safe_float(c["low"])) for i, c in enumerate(candles)]
    highs = [(i, v) for i, v in highs if v is not None]
    lows = [(i, v) for i, v in lows if v is not None]

    swing_highs = []
    swing_lows = []
    for i in range(lookback, len(candles) - lookback):
        # Swing high: higher than lookback each side
        window_h = [safe_float(candles[j]["high"]) for j in range(i-lookback, i+lookback+1)]
        window_h = [v for v in window_h if v is not None]
        curr_h = safe_float(candles[i]["high"])
        if curr_h is not None and curr_h == max(window_h):
            swing_highs.append((i, curr_h))
        window_l = [safe_float(candles[j]["low"]) for j in range(i-lookback, i+lookback+1)]
        window_l = [v for v in window_l if v is not None]
        curr_l = safe_float(candles[i]["low"])
        if curr_l is not None and curr_l == min(window_l):
            swing_lows.append((i, curr_l))

    swing_high = max([v for _, v in swing_highs]) if swing_highs else None
    swing_low = min([v for _, v in swing_lows]) if swing_lows else None
    recent_swing_high = swing_highs[-1][1] if swing_highs else swing_high
    recent_swing_low = swing_lows[-1][1] if swing_lows else swing_low

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "recent_swing_high": recent_swing_high,
        "recent_swing_low": recent_swing_low,
        "all_swing_highs": [v for _, v in swing_highs[-5:]],
        "all_swing_lows": [v for _, v in swing_lows[-5:]],
    }

def determine_advanced_structure(candles: List[Dict]) -> Dict[str, Any]:
    """Advanced structure with HH/HL/LH/LL, breakouts"""
    if len(candles) < 15:
        return {"structure": "NEUTRAL", "detail": "Insufficient data", "swing_high": None, "swing_low": None, "breakout": False, "breakdown": False, "hh": False, "hl": False, "lh": False, "ll": False}

    swings = find_swing_points(candles, lookback=3)
    recent = candles[-30:] if len(candles) >= 30 else candles
    closes = [safe_float(c["close"]) for c in recent if safe_float(c["close"]) is not None]

    # Original simple structure
    base_structure = determine_structure(candles)

    # Analyze swing sequence for HH/HL etc
    all_highs = swings.get("all_swing_highs", [])
    all_lows = swings.get("all_swing_lows", [])

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

    # Breakout / breakdown detection
    price = closes[-1] if closes else None
    breakout = False
    breakdown = False
    if swings["swing_high"] and price and price > swings["swing_high"] * 1.001:
        breakout = True
        detail += " | Breakout above swing high"
    if swings["swing_low"] and price and price < swings["swing_low"] * 0.999:
        breakdown = True
        detail += " | Breakdown below swing low"

    if not detail:
        detail = f"{structure} structure"

    return {
        "structure": structure,
        "detail": detail,
        "structure_detail": detail,
        "swing_high": swings["swing_high"],
        "swing_low": swings["swing_low"],
        "recent_swing_high": swings["recent_swing_high"],
        "recent_swing_low": swings["recent_swing_low"],
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
    """Improved SR: nearest and major levels, not just min/max"""
    basic_support, basic_resistance = calculate_support_resistance(candles)
    if not candles:
        return {"nearest_support": basic_support, "nearest_resistance": basic_resistance, "major_support": basic_support, "major_resistance": basic_resistance, "support": basic_support, "resistance": basic_resistance}

    swings = find_swing_points(candles, lookback=3)
    all_highs = swings.get("all_swing_highs", [])
    all_lows = swings.get("all_swing_lows", [])
    price = safe_float(candles[-1]["close"])

    # Nearest support: highest swing low below price
    nearest_support = None
    nearest_resistance = None
    if price:
        below_lows = [l for l in all_lows if l < price] if all_lows else []
        above_highs = [h for h in all_highs if h > price] if all_highs else []
        if below_lows:
            nearest_support = max(below_lows)
        if above_highs:
            nearest_resistance = min(above_highs)

    # Fallback to basic if no swing levels found
    if nearest_support is None:
        nearest_support = basic_support
    if nearest_resistance is None:
        nearest_resistance = basic_resistance

    # Major levels: absolute min/max of recent 100 candles
    extended = candles[-100:] if len(candles) >= 100 else candles
    ex_highs = [safe_float(c["high"]) for c in extended if safe_float(c["high"]) is not None]
    ex_lows = [safe_float(c["low"]) for c in extended if safe_float(c["low"]) is not None]
    major_support = min(ex_lows) if ex_lows else basic_support
    major_resistance = max(ex_highs) if ex_highs else basic_resistance

    # Distance calculations
    dist_to_support = None
    dist_to_resistance = None
    if price and nearest_support:
        dist_to_support = ((price - nearest_support) / price) * 100 if price != 0 else 0
    if price and nearest_resistance:
        dist_to_resistance = ((nearest_resistance - price) / price) * 100 if price != 0 else 0

    return {
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "major_support": major_support,
        "major_resistance": major_resistance,
        "support": nearest_support or basic_support,
        "resistance": nearest_resistance or basic_resistance,
        "basic_support": basic_support,
        "basic_resistance": basic_resistance,
        "distance_to_support_pct": dist_to_support,
        "distance_to_resistance_pct": dist_to_resistance,
    }

def calculate_ema_alignment(ema9, ema21, ema50, price) -> Dict[str, Any]:
    """Detect bullish/bearish alignment, compression, expansion"""
    if None in (ema9, ema21, ema50):
        return {"alignment": "NEUTRAL", "bullish": False, "bearish": False, "compressed": False, "expanded": False}

    bullish = ema9 > ema21 > ema50 and price > ema9
    bearish = ema9 < ema21 < ema50 and price < ema9

    # Compression: EMAs within 0.5% of each other
    avg_ema = (ema9 + ema21 + ema50) / 3
    max_dev = max(abs(ema9 - avg_ema), abs(ema21 - avg_ema), abs(ema50 - avg_ema))
    compressed = (max_dev / avg_ema * 100) < 0.5 if avg_ema != 0 else False

    # Expansion: distance between 9 and 50 is large
    expansion_pct = abs(ema9 - ema50) / avg_ema * 100 if avg_ema != 0 else 0
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

    return {
        "alignment": alignment,
        "bullish": bullish,
        "bearish": bearish,
        "compressed": compressed,
        "expanded": expanded,
        "expansion_pct": expansion_pct,
    }

def analyze_ema_extended(price, ema21, ema50, atr) -> Dict[str, Any]:
    """Check if price extended too far from EMAs - prevents chasing"""
    if None in (price, ema21, ema50, atr) or atr == 0:
        return {"extended_from_21": False, "extended_from_50": False, "distance_21_atr": 0, "distance_50_atr": 0}

    dist_21 = abs(price - ema21) / atr if atr != 0 else 0
    dist_50 = abs(price - ema50) / atr if atr != 0 else 0

    extended_21 = dist_21 > 2.5  # More than 2.5 ATR from EMA21 is extended
    extended_50 = dist_50 > 3.5  # More than 3.5 ATR from EMA50 is very extended

    return {
        "extended_from_21": extended_21,
        "extended_from_50": extended_50,
        "distance_21_atr": dist_21,
        "distance_50_atr": dist_50,
        "distance_21_pct": ((price - ema21) / price * 100) if price != 0 else 0,
        "distance_50_pct": ((price - ema50) / price * 100) if price != 0 else 0,
    }

def analyze_rsi_state(rsi: float, closes: List[float]) -> Dict[str, Any]:
    """Improved RSI: momentum vs exhaustion, not auto bullish >70"""
    if rsi is None:
        return {"state": "NEUTRAL", "momentum": "NEUTRAL", "overbought": False, "oversold": False, "exhaustion_risk": "LOW"}

    # Momentum classification
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

    # Exhaustion risk based on RSI extremes + momentum weakening
    exhaustion_risk = "LOW"
    if rsi >= 78 or rsi <= 22:
        exhaustion_risk = "EXTREME"
    elif rsi >= 72 or rsi <= 28:
        exhaustion_risk = "HIGH"
    elif rsi >= 68 or rsi <= 32:
        exhaustion_risk = "MEDIUM"

    # Check for divergence (simplified)
    divergence = False
    if len(closes) >= 10:
        recent_rsi_trend = rsi - calculate_rsi(closes[:-3], 14) if len(closes) >= 17 else 0
        price_trend = closes[-1] - closes[-4]
        if (price_trend > 0 and recent_rsi_trend < -5) or (price_trend < 0 and recent_rsi_trend > 5):
            divergence = True

    return {
        "state": state,
        "momentum": momentum,
        "overbought": overbought,
        "oversold": oversold,
        "exhaustion_risk": exhaustion_risk,
        "divergence": divergence,
        "rsi": rsi,
    }

def classify_volatility(atr: Optional[float], price: Optional[float], candles: List[Dict]) -> Dict[str, Any]:
    """Classify volatility LOW/NORMAL/HIGH/EXTREME using ATR relative to price"""
    if atr is None or price is None or price == 0:
        return {"level": "NORMAL", "atr_pct": 0, "score": 50}

    atr_pct = (atr / price) * 100

    # Recent ATR behavior
    recent_atrs = []
    if len(candles) >= 20:
        for i in range(len(candles)-20, len(candles)):
            if i >= 14:
                sub_candles = candles[max(0, i-14):i+1]
                sub_atr = calculate_atr(sub_candles, 14)
                if sub_atr:
                    recent_atrs.append(sub_atr)

    avg_recent_atr = sum(recent_atrs) / len(recent_atrs) if recent_atrs else atr
    atr_expansion = (atr / avg_recent_atr) if avg_recent_atr != 0 else 1

    # Classification thresholds (adjust for crypto vs forex/gold)
    # Gold/crypto typically higher ATR%
    if atr_pct < 0.15:
        level = "LOW"
    elif atr_pct < 0.6:
        level = "NORMAL"
    elif atr_pct < 1.5:
        level = "HIGH"
    else:
        level = "EXTREME"

    # Adjust for expansion
    if atr_expansion > 1.8 and level != "EXTREME":
        # Sudden expansion -> bump level
        if level == "LOW":
            level = "NORMAL"
        elif level == "NORMAL":
            level = "HIGH"
        elif level == "HIGH":
            level = "EXTREME"

    score = min(100, int(atr_pct * 50 + (atr_expansion - 1) * 20))

    return {
        "level": level,
        "atr_pct": atr_pct,
        "atr_expansion": atr_expansion,
        "avg_atr": avg_recent_atr,
        "score": score,
        "current_atr": atr,
    }

def detect_exhaustion(candles: List[Dict], rsi_state: Dict, atr: float, ema21: float, support: float, resistance: float) -> Dict[str, Any]:
    """Exhaustion detection: extreme RSI, abnormal candle, wick rejection, consecutive candles, far from EMA, near SR"""
    if not candles or len(candles) < 5:
        return {"exhaustion": "NONE", "score": 0, "reasons": [], "level": "NONE"}

    reasons = []
    score = 0

    price = safe_float(candles[-1]["close"])
    last_candle = candles[-1]

    # 1. Extreme RSI
    rsi = rsi_state.get("rsi", 50)
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

    # 2. Abnormal candle body
    bodies = [candle_body(c) for c in candles[-10:]]
    avg_body = sum(bodies) / len(bodies) if bodies else 1
    last_body = candle_body(last_candle)
    if avg_body > 0 and last_body > avg_body * 2.5:
        score += 20
        reasons.append(f"Abnormal large candle body ({last_body/avg_body:.1f}x avg)")

    # 3. Long wick / rejection
    high = safe_float(last_candle["high"])
    low = safe_float(last_candle["low"])
    open_p = safe_float(last_candle["open"])
    close_p = safe_float(last_candle["close"])
    if None not in (high, low, open_p, close_p):
        total_range = high - low
        if total_range > 0:
            upper_wick = high - max(open_p, close_p)
            lower_wick = min(open_p, close_p) - low
            if upper_wick > total_range * 0.6:
                score += 15
                reasons.append("Long upper wick - bearish rejection")
            if lower_wick > total_range * 0.6:
                score += 15
                reasons.append("Long lower wick - bullish rejection")

    # 4. Consecutive directional candles
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
    if consecutive_bull >= 5:
        score += 15
        reasons.append(f"{consecutive_bull} consecutive bullish candles")
    if consecutive_bear >= 5:
        score += 15
        reasons.append(f"{consecutive_bear} consecutive bearish candles")

    # 5. Price far from EMA21
    if price and ema21 and atr:
        dist_atr = abs(price - ema21) / atr if atr != 0 else 0
        if dist_atr > 3.0:
            score += 20
            reasons.append(f"Price {dist_atr:.1f} ATR away from EMA21 - extended")
        elif dist_atr > 2.0:
            score += 10
            reasons.append(f"Price {dist_atr:.1f} ATR from EMA21 - stretched")

    # 6. Price near major SR
    if price and resistance and support:
        dist_res_pct = abs(resistance - price) / price * 100 if price != 0 else 0
        dist_sup_pct = abs(price - support) / price * 100 if price != 0 else 0
        if dist_res_pct < 0.3:
            score += 15
            reasons.append(f"Price very close to resistance ({dist_res_pct:.2f}% away)")
        if dist_sup_pct < 0.3:
            score += 15
            reasons.append(f"Price very close to support ({dist_sup_pct:.2f}% away)")

    # 7. ATR expansion
    vol = classify_volatility(atr, price, candles)
    if vol["level"] == "EXTREME":
        score += 15
        reasons.append(f"Extreme volatility (ATR {vol['atr_pct']:.2f}%)")
    elif vol["atr_expansion"] > 2.0:
        score += 10
        reasons.append(f"ATR expanding {vol['atr_expansion']:.1f}x")

    # 8. Weakening momentum (RSI divergence)
    if rsi_state.get("divergence"):
        score += 15
        reasons.append("RSI divergence - momentum weakening")

    score = min(100, score)

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

    return {
        "exhaustion": level,
        "level": level,
        "score": score,
        "exhaustion_score": score,
        "reasons": reasons,
        "exhaustion_reason": "; ".join(reasons) if reasons else "No exhaustion",
    }

def detect_late_entry(price: float, ema21: float, ema50: float, atr: float, rsi: float, candles: List[Dict], support: float, resistance: float, structure: str, volatility: Dict, exhaustion: Dict) -> Dict[str, Any]:
    """Late entry detection - critical to avoid chasing"""
    if None in (price, ema21, atr):
        return {"late_entry": False, "reason": "Insufficient data", "score": 0, "entry_quality": "UNKNOWN"}

    reasons = []
    late_score = 0

    # 1. Price too far above/below EMA21
    dist_21_atr = abs(price - ema21) / atr if atr != 0 else 0
    if dist_21_atr > 2.5:
        late_score += 30
        reasons.append(f"Price {dist_21_atr:.1f} ATR from EMA21 (too far)")

    # 2. Price too far from EMA50
    if ema50 and atr:
        dist_50_atr = abs(price - ema50) / atr if atr != 0 else 0
        if dist_50_atr > 3.5:
            late_score += 25
            reasons.append(f"Price {dist_50_atr:.1f} ATR from EMA50 (very extended)")

    # 3. Close to major resistance/support
    if price and resistance:
        dist_res_pct = (resistance - price) / price * 100 if price != 0 else 0
        if 0 < dist_res_pct < 0.4:
            late_score += 20
            reasons.append(f"Too close to resistance ({dist_res_pct:.2f}% away) - limited upside")
    if price and support:
        dist_sup_pct = (price - support) / price * 100 if price != 0 else 0
        if 0 < dist_sup_pct < 0.4:
            late_score += 20
            reasons.append(f"Too close to support ({dist_sup_pct:.2f}% away) - limited downside")

    # 4. Large impulsive candle already occurred
    if len(candles) >= 2:
        last_body = candle_body(candles[-1])
        prev_bodies = [candle_body(c) for c in candles[-6:-1]]
        avg_prev = sum(prev_bodies) / len(prev_bodies) if prev_bodies else last_body
        if avg_prev > 0 and last_body > avg_prev * 2.0:
            late_score += 20
            reasons.append(f"Large impulsive candle just occurred ({last_body/avg_prev:.1f}x avg)")

    # 5. ATR expansion extreme
    if volatility["level"] == "EXTREME":
        late_score += 15
        reasons.append("Extreme volatility - move may be over")
    elif volatility["atr_expansion"] > 2.2:
        late_score += 15
        reasons.append(f"Volatility spiked {volatility['atr_expansion']:.1f}x - late")

    # 6. RSI stretched
    if rsi >= 75 or rsi <= 25:
        late_score += 15
        reasons.append(f"RSI stretched at {rsi:.1f}")

    # 7. Several consecutive candles same direction
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
    if consecutive >= 4:
        late_score += 15
        reasons.append(f"{consecutive} consecutive {direction} candles - move extended")

    # 8. Exhaustion high
    if exhaustion["level"] in ["HIGH", "EXTREME"]:
        late_score += 20
        reasons.append(f"High exhaustion ({exhaustion['level']}) - late entry")

    late_score = min(100, late_score)
    is_late = late_score >= 45

    if late_score >= 70:
        quality = "LATE"
    elif late_score >= 45:
        quality = "RISKY"
    elif late_score >= 25:
        quality = "ACCEPTABLE"
    else:
        quality = "IDEAL"

    return {
        "late_entry": is_late,
        "late_entry_reason": "; ".join(reasons) if reasons else "Entry timing acceptable",
        "reason": "; ".join(reasons) if reasons else "Entry timing acceptable",
        "score": late_score,
        "entry_quality": quality,
        "quality": quality,
    }

def analyze_single_timeframe(candles: List[Dict], symbol: str, tf_name: str) -> Dict[str, Any]:
    """Analyze one timeframe comprehensively"""
    if not candles or len(candles) < 15:
        return {"trend": "NEUTRAL", "error": "Insufficient candles", "timeframe": tf_name}

    closes = [safe_float(c["close"]) for c in candles if safe_float(c["close"]) is not None]
    if len(closes) < 15:
        return {"trend": "NEUTRAL", "error": "Invalid close data", "timeframe": tf_name}

    price = closes[-1]
    ema9 = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)
    rsi = calculate_rsi(closes, 14)
    atr = calculate_atr(candles, 14)

    if None in (ema9, ema21, ema50, atr):
        return {"trend": "NEUTRAL", "error": "Indicator calc failed", "timeframe": tf_name}

    adv_structure = determine_advanced_structure(candles)
    adv_sr = calculate_advanced_sr(candles)
    ema_align = calculate_ema_alignment(ema9, ema21, ema50, price)
    ema_ext = analyze_ema_extended(price, ema21, ema50, atr)
    rsi_state = analyze_rsi_state(rsi, closes)
    volatility = classify_volatility(atr, price, candles)
    exhaustion = detect_exhaustion(candles, rsi_state, atr, ema21, adv_sr["support"], adv_sr["resistance"])

    # Trend determination per timeframe
    bullish_pts = 0
    bearish_pts = 0
    if ema_align["bullish"]:
        bullish_pts += 2
    if ema_align["bearish"]:
        bearish_pts += 2
    if adv_structure["structure"] == "BULLISH":
        bullish_pts += 2
    elif adv_structure["structure"] == "BEARISH":
        bearish_pts += 2
    if rsi_state["momentum"] in ["BULLISH", "STRONG_BULLISH"]:
        bullish_pts += 1
    elif rsi_state["momentum"] in ["BEARISH", "STRONG_BEARISH"]:
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

    return {
        "timeframe": tf_name,
        "trend": trend,
        "price": price,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "rsi": rsi,
        "atr": atr,
        "structure": adv_structure["structure"],
        "structure_detail": adv_structure["detail"],
        "structure_data": adv_structure,
        "support": adv_sr["support"],
        "resistance": adv_sr["resistance"],
        "sr_data": adv_sr,
        "ema_alignment": ema_align,
        "ema_extended": ema_ext,
        "rsi_state": rsi_state,
        "volatility": volatility,
        "exhaustion": exhaustion,
        "closes": closes,
        "candles": candles,
    }

def fetch_mtf_candles(symbol: str) -> Dict[str, Any]:
    """Fetch 4H,1H,15M,5M - one request each, efficient, handles API limits"""
    timeframes = ["4h", "1h", "15m", "5m"]
    results = {}
    for tf in timeframes:
        try:
            # Use smaller outputsize for higher timeframes to save API credits
            size = 150 if tf in ["15m", "5m"] else 100
            candles = get_candles(symbol, tf, size)
            results[tf] = {"success": True, "candles": candles, "error": None}
        except Exception as e:
            logger.warning(f"MTF fetch failed for {symbol} {tf}: {e}")
            results[tf] = {"success": False, "candles": [], "error": str(e)}
    return results

def calculate_mtf_bias(mtf_analyses: Dict[str, Dict]) -> Dict[str, Any]:
    """Calculate MTF score and bias: 4H 35%, 1H 30%, 15M 25%, 5M 10%"""
    score = 0.0
    total_weight = 0.0
    trends = {}

    for tf, weight in MTF_WEIGHTS.items():
        analysis = mtf_analyses.get(tf)
        if not analysis or "trend" not in analysis:
            continue
        trend = analysis["trend"]
        trends[tf] = trend
        total_weight += weight
        if trend == "BULLISH":
            score += weight * 100
        elif trend == "BEARISH":
            score += weight * 0  # bearish = 0 points, bullish = 100
        else:
            score += weight * 50

    if total_weight == 0:
        mtf_score = 50
        bias = "NEUTRAL"
    else:
        mtf_score = (score / total_weight)  # 0-100, 0=strong bearish, 100=strong bullish
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

    # Alignment
    bullish_count = sum(1 for t in trends.values() if t == "BULLISH")
    bearish_count = sum(1 for t in trends.values() if t == "BEARISH")
    if bullish_count >= 3:
        alignment = "STRONG_BULLISH_ALIGNMENT"
    elif bearish_count >= 3:
        alignment = "STRONG_BEARISH_ALIGNMENT"
    elif bullish_count >= 2 and bearish_count == 0:
        alignment = "BULLISH_ALIGNMENT"
    elif bearish_count >= 2 and bullish_count == 0:
        alignment = "BEARISH_ALIGNMENT"
    elif bullish_count == 1 and bearish_count == 1:
        alignment = "MIXED"
    else:
        alignment = "NEUTRAL"

    # Individual trends
    h4_trend = trends.get("4h", "NEUTRAL")
    h1_trend = trends.get("1h", "NEUTRAL")
    m15_trend = trends.get("15m", "NEUTRAL")
    m5_trend = trends.get("5m", "NEUTRAL")

    # HTF trend = 4H + 1H combined
    if h4_trend == "BULLISH" and h1_trend == "BULLISH":
        htf_trend = "BULLISH"
    elif h4_trend == "BEARISH" and h1_trend == "BEARISH":
        htf_trend = "BEARISH"
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

    return {
        "mtf_bias": bias,
        "mtf_score": round(mtf_score, 1),
        "bias": bias,
        "score": round(mtf_score, 1),
        "htf_trend": htf_trend,
        "h4_trend": h4_trend,
        "h1_trend": h1_trend,
        "m15_trend": m15_trend,
        "m5_trend": m5_trend,
        "timeframe_alignment": alignment,
        "alignment": alignment,
        "trends": trends,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
    }

def get_news_risk_safe(symbol: str) -> Dict[str, Any]:
    """Optional news integration - safe, never breaks market engine"""
    try:
        # Try to import news engine without circular import
        import importlib.util
        import os
        # Check if news.py exists in same dir or in path
        news_mod = None
        try:
            import news as news_module
            news_mod = news_module
        except ImportError:
            # Try local file
            if os.path.exists("/mnt/data/news.py") or os.path.exists("news.py"):
                spec = importlib.util.spec_from_file_location("news", "/mnt/data/news.py" if os.path.exists("/mnt/data/news.py") else "news.py")
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    news_mod = mod

        if news_mod and hasattr(news_mod, "get_news_for_asset"):
            data = news_mod.get_news_for_asset(symbol)
            return {
                "news_risk": data.get("risk", "LOW"),
                "news_available": data.get("news_available", False) or data.get("headlines_available", False) or data.get("calendar_available", False),
                "news_summary": data.get("summary", "No news"),
                "news_events": data.get("events", [])[:3],
                "news_headlines": data.get("headlines", [])[:2],
                "calendar_available": data.get("calendar_available", False),
                "headlines_available": data.get("headlines_available", False),
            }
    except Exception as e:
        logger.debug(f"News integration failed (safe): {e}")

    return {
        "news_risk": "UNKNOWN",
        "news_available": False,
        "news_summary": "News module unavailable",
        "news_events": [],
        "news_headlines": [],
        "calendar_available": False,
        "headlines_available": False,
    }

# =========================================================
# SIGNAL ENGINE - PRODUCTION UPGRADE
# =========================================================

def analyze_market(symbol, timeframe="15m"):

    # =====================================================
    # FETCH MTF CANDLES - Efficient, one per timeframe
    # =====================================================

    primary_tf = timeframe
    symbol = symbol.upper().strip()

    # Cache for this call
    mtf_raw = fetch_mtf_candles(symbol)

    # Ensure primary timeframe exists - if user requested something other than 4 standard, fetch it
    if primary_tf not in mtf_raw:
        try:
            primary_candles = get_candles(symbol, primary_tf, 150)
            mtf_raw[primary_tf] = {"success": True, "candles": primary_candles, "error": None}
        except Exception as e:
            # Fallback to 15m if primary fails
            if "15m" in mtf_raw and mtf_raw["15m"]["success"]:
                primary_candles = mtf_raw["15m"]["candles"]
                primary_tf = "15m"
            else:
                raise RuntimeError(f"Failed to fetch primary timeframe {timeframe}: {e}")

    # Get primary candles
    if primary_tf in mtf_raw and mtf_raw[primary_tf]["success"]:
        candles = mtf_raw[primary_tf]["candles"]
    else:
        # Try 15m as fallback
        if "15m" in mtf_raw and mtf_raw["15m"]["success"]:
            candles = mtf_raw["15m"]["candles"]
            primary_tf = "15m"
        else:
            # Find any successful
            successful = [k for k, v in mtf_raw.items() if v["success"]]
            if not successful:
                raise RuntimeError(f"No candle data available for {symbol} on any timeframe")
            candles = mtf_raw[successful[0]]["candles"]
            primary_tf = successful[0]

    # =====================================================
    # ANALYZE EACH TIMEFRAME
    # =====================================================

    mtf_analyses: Dict[str, Dict] = {}
    for tf, data in mtf_raw.items():
        if data["success"] and data["candles"]:
            try:
                analysis = analyze_single_timeframe(data["candles"], symbol, tf)
                mtf_analyses[tf] = analysis
            except Exception as e:
                logger.warning(f"Failed to analyze {tf}: {e}")
                mtf_analyses[tf] = {"trend": "NEUTRAL", "error": str(e), "timeframe": tf}

    # Primary analysis is the main one for entry
    primary_analysis = mtf_analyses.get(primary_tf)
    if not primary_analysis:
        # Analyze primary candles directly
        primary_analysis = analyze_single_timeframe(candles, symbol, primary_tf)
        mtf_analyses[primary_tf] = primary_analysis

    # Extract primary values for backward compat
    closes = primary_analysis.get("closes", [safe_float(c["close"]) for c in candles if safe_float(c["close"]) is not None])
    price = primary_analysis.get("price", closes[-1] if closes else 0)
    ema9 = primary_analysis.get("ema9")
    ema21 = primary_analysis.get("ema21")
    ema50 = primary_analysis.get("ema50")
    rsi = primary_analysis.get("rsi", 50.0)
    atr = primary_analysis.get("atr", price * 0.005 if price else 1)

    if None in (ema9, ema21, ema50):
        raise RuntimeError("Unable to calculate technical indicators.")

    # =====================================================
    # MTF BIAS
    # =====================================================

    mtf = calculate_mtf_bias(mtf_analyses)

    # =====================================================
    # ADVANCED COMPONENTS FROM PRIMARY
    # =====================================================

    adv_structure = primary_analysis.get("structure_data", determine_advanced_structure(candles))
    adv_sr = primary_analysis.get("sr_data", calculate_advanced_sr(candles))
    ema_align = primary_analysis.get("ema_alignment", calculate_ema_alignment(ema9, ema21, ema50, price))
    ema_ext = primary_analysis.get("ema_extended", analyze_ema_extended(price, ema21, ema50, atr))
    rsi_state = primary_analysis.get("rsi_state", analyze_rsi_state(rsi, closes))
    volatility = primary_analysis.get("volatility", classify_volatility(atr, price, candles))
    exhaustion = primary_analysis.get("exhaustion", detect_exhaustion(candles, rsi_state, atr, ema21, adv_sr["support"], adv_sr["resistance"]))

    support = adv_sr["support"]
    resistance = adv_sr["resistance"]
    nearest_support = adv_sr["nearest_support"]
    nearest_resistance = adv_sr["nearest_resistance"]
    major_support = adv_sr["major_support"]
    major_resistance = adv_sr["major_resistance"]

    if support is None or resistance is None:
        support = price - (atr * 2) if price and atr else price * 0.99
        resistance = price + (atr * 2) if price and atr else price * 1.01

    structure = adv_structure["structure"]

    # =====================================================
    # LATE ENTRY & EXHAUSTION
    # =====================================================

    late_entry_data = detect_late_entry(price, ema21, ema50, atr, rsi, candles, support, resistance, structure, volatility, exhaustion)

    # =====================================================
    # NEWS RISK - Optional, safe
    # =====================================================

    news_data = get_news_risk_safe(symbol)
    news_risk = news_data["news_risk"]

    # =====================================================
    # SCORE - Multi-factor 0-100
    # =====================================================

    bullish_score = 0
    bearish_score = 0
    reasons = []

    # MTF contribution (35+30+25+10 already weighted in mtf_score, but we add detailed scoring)
    mtf_score_val = mtf["mtf_score"]  # 0-100, 0 bearish, 100 bullish
    if mtf_score_val >= 60:
        bullish_score += int((mtf_score_val - 50) * 0.8)  # up to 40 points
        reasons.append(f"MTF bullish alignment {mtf_score_val:.0f}/100 ({mtf['alignment']})")
    elif mtf_score_val <= 40:
        bearish_score += int((50 - mtf_score_val) * 0.8)
        reasons.append(f"MTF bearish alignment {mtf_score_val:.0f}/100 ({mtf['alignment']})")

    # HTF trend bonus
    if mtf["htf_trend"] == "BULLISH":
        bullish_score += 15
        reasons.append(f"HTF bullish (4H:{mtf['h4_trend']} 1H:{mtf['h1_trend']})")
    elif mtf["htf_trend"] == "BEARISH":
        bearish_score += 15
        reasons.append(f"HTF bearish (4H:{mtf['h4_trend']} 1H:{mtf['h1_trend']})")

    # EMA alignment
    if ema_align["bullish"]:
        bullish_score += 15
        reasons.append("EMA 9>21>50 bullish alignment")
    elif ema_align["bearish"]:
        bearish_score += 15
        reasons.append("EMA 9<21<50 bearish alignment")
    elif ema_align["compressed"]:
        reasons.append("EMA compressed - potential breakout soon")
    # Penalize extended price - do NOT add bullish points if extended
    if not ema_ext["extended_from_21"] and not ema_ext["extended_from_50"]:
        if ema9 > ema21:
            bullish_score += 10
        elif ema9 < ema21:
            bearish_score += 10
        if ema21 > ema50:
            bullish_score += 10
        elif ema21 < ema50:
            bearish_score += 10

    # Price vs EMA
    if price > ema21 and not ema_ext["extended_from_21"]:
        bullish_score += 8
    elif price < ema21 and not ema_ext["extended_from_21"]:
        bearish_score += 8

    # RSI - improved: not auto bullish >70
    rsi_mom = rsi_state["momentum"]
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
        # Do NOT add bullish points for overbought, actually caution
        reasons.append(f"RSI overbought ({rsi:.1f}) - potential exhaustion")
    elif rsi_mom == "OVERSOLD":
        reasons.append(f"RSI oversold ({rsi:.1f}) - potential exhaustion")

    # Structure
    if adv_structure["structure"] == "BULLISH":
        bullish_score += 15
        reasons.append(f"Bullish structure: {adv_structure['detail']}")
    elif adv_structure["structure"] == "BEARISH":
        bearish_score += 15
        reasons.append(f"Bearish structure: {adv_structure['detail']}")

    if adv_structure["breakout"]:
        bullish_score += 10
        reasons.append("Breakout above recent swing high")
    if adv_structure["breakdown"]:
        bearish_score += 10
        reasons.append("Breakdown below recent swing low")

    # Momentum
    mom = momentum_score(closes)
    if mom > 0 and not exhaustion["level"] in ["HIGH", "EXTREME"]:
        bullish_score += 8
        reasons.append("Recent momentum bullish")
    elif mom < 0 and not exhaustion["level"] in ["HIGH", "EXTREME"]:
        bearish_score += 8
        reasons.append("Recent momentum bearish")

    # =====================================================
    # PENALTIES: Late entry, exhaustion, volatility, news
    # =====================================================

    penalty_bull = 0
    penalty_bear = 0

    # Late entry penalty
    if late_entry_data["late_entry"]:
        # Penalize both sides, but more the dominant direction
        if bullish_score > bearish_score:
            penalty_bull += late_entry_data["score"] // 2
        else:
            penalty_bear += late_entry_data["score"] // 2
        reasons.append(f"Late entry warning: {late_entry_data['reason']}")

    # Exhaustion penalty
    if exhaustion["level"] == "EXTREME":
        if bullish_score > bearish_score:
            penalty_bull += 30
        else:
            penalty_bear += 30
        reasons.append(f"Exhaustion {exhaustion['level']}: {exhaustion['exhaustion_reason']}")
    elif exhaustion["level"] == "HIGH":
        if bullish_score > bearish_score:
            penalty_bull += 20
        else:
            penalty_bear += 20
    elif exhaustion["level"] == "MEDIUM":
        if bullish_score > bearish_score:
            penalty_bull += 10
        else:
            penalty_bear += 10

    # Volatility penalty
    if volatility["level"] == "EXTREME":
        penalty_bull += 15
        penalty_bear += 15
        reasons.append(f"Extreme volatility ({volatility['atr_pct']:.2f}% ATR)")

    # EMA extended penalty
    if ema_ext["extended_from_21"]:
        if price > ema21:
            penalty_bull += 15
        else:
            penalty_bear += 15
        reasons.append(f"Price extended {ema_ext['distance_21_atr']:.1f} ATR from EMA21")

    # News risk penalty
    if news_risk in ["HIGH", "EXTREME"]:
        penalty_bull += 15
        penalty_bear += 15
        reasons.append(f"News risk {news_risk} - high volatility expected")

    # Conflicting timeframes penalty
    if mtf["alignment"] == "MIXED":
        penalty_bull += 10
        penalty_bear += 10
        reasons.append("Mixed timeframe alignment")

    # Nearby major SR penalty
    if adv_sr["distance_to_resistance_pct"] is not None and 0 < adv_sr["distance_to_resistance_pct"] < 0.5:
        if bullish_score > bearish_score:
            penalty_bull += 10
            reasons.append(f"Close to major resistance ({adv_sr['distance_to_resistance_pct']:.2f}% away)")
    if adv_sr["distance_to_support_pct"] is not None and 0 < adv_sr["distance_to_support_pct"] < 0.5:
        if bearish_score > bullish_score:
            penalty_bear += 10
            reasons.append(f"Close to major support ({adv_sr['distance_to_support_pct']:.2f}% away)")

    bullish_score = max(0, bullish_score - penalty_bull)
    bearish_score = max(0, bearish_score - penalty_bear)

    # =====================================================
    # TREND
    # =====================================================

    if bullish_score >= bearish_score + 15:
        trend = "BULLISH"
    elif bearish_score >= bullish_score + 15:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    # =====================================================
    # SETUP STRENGTH 0-100
    # =====================================================

    raw_strength = max(bullish_score, bearish_score)
    # Adjust for MTF alignment
    if mtf["alignment"] in ["STRONG_BULLISH_ALIGNMENT", "STRONG_BEARISH_ALIGNMENT"]:
        raw_strength += 10
    elif mtf["alignment"] == "MIXED":
        raw_strength -= 10

    # Adjust for exhaustion/late
    if exhaustion["level"] in ["HIGH", "EXTREME"]:
        raw_strength -= 15
    if late_entry_data["late_entry"]:
        raw_strength -= 20

    setup_strength = min(100, max(0, int(raw_strength)))

    # =====================================================
    # SIGNAL LOGIC - Requires MTF agreement
    # =====================================================

    signal = "WAIT"
    trigger_condition = None

    # Requirements for BUY:
    # - MTF score >= 60 (bullish)
    # - HTF not bearish
    # - 15M bullish or breakout
    # - Not late entry extreme
    # - Not exhaustion extreme
    # - Bullish score >= 60 and >= bearish +15
    # - RSI not extremely overbought without strong structure

    # Requirements for SELL opposite

    # Check news extreme blocks trading
    news_blocks = news_risk in ["EXTREME"] and mtf["mtf_score"] not in [0, 100]  # Extreme news blocks unless perfect alignment

    if not news_blocks:
        if bullish_score >= 60 and bullish_score >= bearish_score + 15:
            # Additional MTF filters
            if mtf["mtf_score"] >= 55 and mtf["htf_trend"] != "BEARISH":
                if not late_entry_data["late_entry"] or late_entry_data["score"] < 70:
                    if exhaustion["level"] not in ["EXTREME"]:
                        # Check if not too close to resistance
                        if not (adv_sr["distance_to_resistance_pct"] is not None and 0 < adv_sr["distance_to_resistance_pct"] < 0.3):
                            signal = "BUY"
                        else:
                            trigger_condition = f"Wait for break above {round_price(resistance)} resistance before BUY"
                    else:
                        trigger_condition = "Exhaustion high - wait for pullback toward EMA21 before BUY"
                else:
                    trigger_condition = f"Late entry - wait for pullback toward EMA21 ({round_price(ema21)}) before BUY"
            else:
                if mtf["htf_trend"] == "BEARISH":
                    trigger_condition = f"HTF bearish ({mtf['h4_trend']}/{mtf['h1_trend']}) conflicts with bullish setup - wait for HTF alignment"
                else:
                    trigger_condition = f"MTF score {mtf['mtf_score']:.0f} not strong enough for BUY - need >=55"

        elif bearish_score >= 60 and bearish_score >= bullish_score + 15:
            if mtf["mtf_score"] <= 45 and mtf["htf_trend"] != "BULLISH":
                if not late_entry_data["late_entry"] or late_entry_data["score"] < 70:
                    if exhaustion["level"] not in ["EXTREME"]:
                        if not (adv_sr["distance_to_support_pct"] is not None and 0 < adv_sr["distance_to_support_pct"] < 0.3):
                            signal = "SELL"
                        else:
                            trigger_condition = f"Wait for breakdown below {round_price(support)} support before SELL"
                    else:
                        trigger_condition = "Exhaustion high - wait for bounce toward EMA21 before SELL"
                else:
                    trigger_condition = f"Late entry - wait for bounce toward EMA21 ({round_price(ema21)}) before SELL"
            else:
                if mtf["htf_trend"] == "BULLISH":
                    trigger_condition = f"HTF bullish ({mtf['h4_trend']}/{mtf['h1_trend']}) conflicts with bearish setup - wait for HTF alignment"
                else:
                    trigger_condition = f"MTF score {mtf['mtf_score']:.0f} not strong enough for SELL - need <=45"
    else:
        trigger_condition = f"News risk {news_risk} EXTREME - avoid new entries, wait for volatility to settle"

    # If still WAIT, create helpful trigger
    if signal == "WAIT" and not trigger_condition:
        if trend == "BULLISH":
            if late_entry_data["late_entry"]:
                trigger_condition = f"Wait for pullback toward EMA21 ({round_price(ema21)}) or support ({round_price(support)}) before considering BUY"
            else:
                trigger_condition = f"Wait for 15M close above {round_price(resistance)} or EMA alignment confirmation for BUY"
        elif trend == "BEARISH":
            if late_entry_data["late_entry"]:
                trigger_condition = f"Wait for bounce toward EMA21 ({round_price(ema21)}) or resistance ({round_price(resistance)}) before considering SELL"
            else:
                trigger_condition = f"Wait for 15M close below {round_price(support)} or EMA alignment confirmation for SELL"
        else:
            if mtf["alignment"] == "MIXED":
                trigger_condition = f"Mixed MTF (4H:{mtf['h4_trend']} 1H:{mtf['h1_trend']} 15M:{mtf['m15_trend']}) - wait for alignment"
            else:
                trigger_condition = "Market structure mixed - wait for stronger directional confirmation and EMA alignment"

    # =====================================================
    # ENTRY / SL / TP - Intelligent
    # =====================================================

    entry_low = None
    entry_high = None
    stop_loss = None
    tp1 = None
    tp2 = None
    tp3 = None
    risk_distance = None
    risk_percent = None

    # Entry logic prefers EMA21, support/resistance, structure
    if signal == "BUY":
        # Ideal entry around EMA21 or recent breakout retest
        # For bullish, prefer lower part of range
        ema_pullback = ema21
        support_level = nearest_support or support

        # Entry zone: between support and EMA21, or around price - 0.35 ATR
        ideal_low = max(support_level, price - (atr * 0.5)) if support_level else price - (atr * 0.5)
        # Don't let entry_low be above price for BUY
        ideal_low = min(ideal_low, price - (atr * 0.1))

        # Prefer EMA21 if it's below price and not too far
        if ema21 < price and (price - ema21) / atr <= 1.5:
            ideal_low = max(ideal_low, ema21 - (atr * 0.15))
            entry_low = ideal_low
            entry_high = min(price, ema21 + (atr * 0.4))
        else:
            entry_low = max(support_level, price - (atr * 0.35)) if support_level else price - (atr * 0.35)
            entry_high = price + (atr * 0.15)

        # Ensure entry zone is below price and ordered
        if entry_low > price:
            entry_low = price - (atr * 0.3)
        if entry_high < entry_low:
            entry_high = entry_low + (atr * 0.3)
        if entry_high > price + (atr * 0.2):
            entry_high = price + (atr * 0.15)

        # SL: below recent swing low or support, using ATR and structure
        swing_low = adv_structure.get("recent_swing_low") or adv_structure.get("swing_low")
        atr_stop = price - (atr * 1.4)
        candidates = [c for c in [support_level, swing_low, atr_stop, nearest_support] if c is not None]
        stop_loss = min(candidates) if candidates else atr_stop

        if stop_loss >= entry_low:
            stop_loss = entry_low - (atr * 0.5)

        risk = price - stop_loss
        if risk <= 0:
            risk = atr * 1.2
            stop_loss = price - risk

        tp1 = price + (risk * 1.0)
        tp2 = price + (risk * 2.0)
        tp3 = price + (risk * 3.0)

        # Adjust TP if resistance makes them unrealistic
        if resistance and resistance > price:
            if tp1 > resistance * 1.01:
                tp1 = resistance
            if tp2 < resistance and tp2 > resistance * 0.98:
                tp2 = resistance
            if tp3 < resistance:
                tp3 = max(tp3, resistance + atr * 0.5)

    elif signal == "SELL":
        resistance_level = nearest_resistance or resistance

        ideal_high = min(resistance_level, price + (atr * 0.5)) if resistance_level else price + (atr * 0.5)
        ideal_high = max(ideal_high, price + (atr * 0.1))

        if ema21 > price and (ema21 - price) / atr <= 1.5:
            ideal_high = min(ideal_high, ema21 + (atr * 0.15))
            entry_high = ideal_high
            entry_low = max(price, ema21 - (atr * 0.4))
        else:
            entry_low = price - (atr * 0.15)
            entry_high = min(resistance_level, price + (atr * 0.35)) if resistance_level else price + (atr * 0.35)

        if entry_high < price:
            entry_high = price + (atr * 0.3)
        if entry_low > entry_high:
            entry_low = entry_high - (atr * 0.3)
        if entry_low < price - (atr * 0.2):
            entry_low = price - (atr * 0.15)

        swing_high = adv_structure.get("recent_swing_high") or adv_structure.get("swing_high")
        atr_stop = price + (atr * 1.4)
        candidates = [c for c in [resistance_level, swing_high, atr_stop, nearest_resistance] if c is not None]
        stop_loss = max(candidates) if candidates else atr_stop

        if stop_loss <= entry_high:
            stop_loss = entry_high + (atr * 0.5)

        risk = stop_loss - price
        if risk <= 0:
            risk = atr * 1.2
            stop_loss = price + risk

        tp1 = price - (risk * 1.0)
        tp2 = price - (risk * 2.0)
        tp3 = price - (risk * 3.0)

        if support and support < price:
            if tp1 < support * 0.99:
                tp1 = support
            if tp2 > support and tp2 < support * 1.02:
                tp2 = support
            if tp3 > support:
                tp3 = min(tp3, support - atr * 0.5)

    else:  # WAIT
        if trend == "BULLISH":
            entry_low = max(nearest_support or support, price - atr) if (nearest_support or support) else price - atr
            entry_high = price
        elif trend == "BEARISH":
            entry_low = price
            entry_high = min(nearest_resistance or resistance, price + atr) if (nearest_resistance or resistance) else price + atr
        else:
            entry_low = nearest_support or support
            entry_high = nearest_resistance or resistance

    # Risk calculations
    if stop_loss is not None and price:
        if signal == "BUY":
            risk_distance = price - stop_loss
        elif signal == "SELL":
            risk_distance = stop_loss - price
        else:
            risk_distance = abs(price - stop_loss) if stop_loss else atr

        if price != 0 and risk_distance:
            risk_percent = (risk_distance / price) * 100

    # Risk/Reward
    rr_tp1 = rr_tp2 = rr_tp3 = None
    if risk_distance and risk_distance > 0:
        if tp1 and price:
            rr_tp1 = abs(tp1 - price) / risk_distance
        if tp2 and price:
            rr_tp2 = abs(tp2 - price) / risk_distance
        if tp3 and price:
            rr_tp3 = abs(tp3 - price) / risk_distance

    # =====================================================
    # SETUP DESCRIPTION
    # =====================================================

    if signal == "BUY":
        setup = f"Bullish confirmation: MTF {mtf['mtf_score']:.0f} ({mtf['alignment']}), HTF {mtf['htf_trend']}, {adv_structure['detail']}. Entry quality: {late_entry_data['quality']}."
    elif signal == "SELL":
        setup = f"Bearish confirmation: MTF {mtf['mtf_score']:.0f} ({mtf['alignment']}), HTF {mtf['htf_trend']}, {adv_structure['detail']}. Entry quality: {late_entry_data['quality']}."
    elif trigger_condition:
        setup = trigger_condition
    elif trend == "BULLISH":
        setup = f"Bullish bias (MTF {mtf['mtf_score']:.0f}) but entry confirmation not strong enough. {trigger_condition or ''}"
    elif trend == "BEARISH":
        setup = f"Bearish bias (MTF {mtf['mtf_score']:.0f}) but entry confirmation not strong enough. {trigger_condition or ''}"
    else:
        setup = f"Market mixed (MTF {mtf['mtf_score']:.0f} {mtf['alignment']}). Wait for stronger alignment. {trigger_condition or ''}"

    # =====================================================
    # RETURN COMPLETE MARKET DATA - BACKWARD COMPATIBLE + NEW FIELDS
    # =====================================================

    return {
        # Original fields preserved exactly
        "symbol": symbol,
        "timeframe": timeframe,
        "price": round_price(price),
        "signal": signal,
        "trend": trend,
        "structure": structure,
        "setup_strength": setup_strength,
        "support": round_price(support),
        "resistance": round_price(resistance),
        "ema9": round_price(ema9),
        "ema21": round_price(ema21),
        "ema50": round_price(ema50),
        "rsi": round(rsi, 2),
        "atr": round_price(atr),
        "entry_low": round_price(entry_low),
        "entry_high": round_price(entry_high),
        "entry_zone": (
            f"{round_price(entry_low)} - {round_price(entry_high)}"
            if entry_low is not None and entry_high is not None
            else None
        ),
        "stop_loss": round_price(stop_loss) if stop_loss is not None else None,
        "tp1": round_price(tp1) if tp1 is not None else None,
        "tp2": round_price(tp2) if tp2 is not None else None,
        "tp3": round_price(tp3) if tp3 is not None else None,
        "take_profit": round_price(tp2) if tp2 is not None else None,
        "reason": setup,
        "reasons": reasons,

        # NEW: Multi-timeframe
        "mtf_bias": mtf["mtf_bias"],
        "mtf_score": mtf["mtf_score"],
        "htf_trend": mtf["htf_trend"],
        "h4_trend": mtf["h4_trend"],
        "h1_trend": mtf["h1_trend"],
        "m15_trend": mtf["m15_trend"],
        "m5_trend": mtf["m5_trend"],
        "timeframe_alignment": mtf["timeframe_alignment"],
        "mtf_data": mtf,

        # NEW: Advanced structure
        "structure_detail": adv_structure["detail"],
        "structure_data": adv_structure,
        "swing_high": round_price(adv_structure["swing_high"]),
        "swing_low": round_price(adv_structure["swing_low"]),
        "recent_swing_high": round_price(adv_structure.get("recent_swing_high")),
        "recent_swing_low": round_price(adv_structure.get("recent_swing_low")),
        "breakout": adv_structure["breakout"],
        "breakdown": adv_structure["breakdown"],

        # NEW: Advanced SR
        "nearest_support": round_price(nearest_support),
        "nearest_resistance": round_price(nearest_resistance),
        "major_support": round_price(major_support),
        "major_resistance": round_price(major_resistance),
        "sr_data": adv_sr,

        # NEW: EMA analysis
        "ema_alignment": ema_align["alignment"],
        "ema_alignment_data": ema_align,
        "ema_extended": ema_ext["extended_from_21"] or ema_ext["extended_from_50"],
        "ema_extended_data": ema_ext,

        # NEW: RSI advanced
        "rsi_state": rsi_state["state"],
        "rsi_state_data": rsi_state,

        # NEW: Volatility
        "volatility": volatility["level"],
        "volatility_data": volatility,

        # NEW: Exhaustion
        "exhaustion": exhaustion["level"],
        "exhaustion_score": exhaustion["score"],
        "exhaustion_reason": exhaustion["exhaustion_reason"],
        "exhaustion_data": exhaustion,

        # NEW: Late entry
        "late_entry": late_entry_data["late_entry"],
        "late_entry_reason": late_entry_data["late_entry_reason"],
        "late_entry_data": late_entry_data,
        "entry_quality": late_entry_data["quality"],

        # NEW: Risk
        "risk_distance": round_price(risk_distance),
        "risk_percent": round(risk_percent, 3) if risk_percent is not None else None,
        "risk_reward_tp1": round(rr_tp1, 2) if rr_tp1 is not None else None,
        "risk_reward_tp2": round(rr_tp2, 2) if rr_tp2 is not None else None,
        "risk_reward_tp3": round(rr_tp3, 2) if rr_tp3 is not None else None,

        # NEW: News
        "news_risk": news_risk,
        "news_data": news_data,

        # NEW: Triggers
        "trigger_condition": trigger_condition,
        "ideal_entry": round_price((entry_low + entry_high) / 2) if entry_low and entry_high else round_price(price),
    }
