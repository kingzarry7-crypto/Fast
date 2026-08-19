import requests
import config
import math


# =========================================================
# 👑 KING ZARRY AI
# MARKET ENGINE
# =========================================================
#
# Returns:
# BUY / SELL / WAIT
# Entry zone
# Stop Loss
# TP1 / TP2 / TP3
# Setup strength
# Trend
# Structure
# Support / Resistance
# EMA 9 / 21 / 50
# RSI
#
# Designed to plug into the existing King Zarry AI bot.
# =========================================================


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
    """
    Keeps gold/forex prices readable while also working
    with crypto and other instruments.
    """
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
        raise RuntimeError(
            f"Twelve Data HTTP error: {response.status_code}"
        )

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Twelve Data error.")
        )

    if "price" not in data:
        raise RuntimeError(
            f"Price unavailable: {data}"
        )

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
        raise RuntimeError(
            f"Twelve Data HTTP error: {response.status_code}"
        )

    data = response.json()

    if data.get("status") == "error":
        raise RuntimeError(
            data.get("message", "Twelve Data error.")
        )

    if "values" not in data:
        raise RuntimeError(
            f"No candle data returned: {data}"
        )

    candles = list(reversed(data["values"]))

    # LOWERED REQUIREMENT: Lowered threshold from 60 to 15 to handle API tier limits
    if not candles or len(candles) < 15:
        raise RuntimeError(
            f"Insufficient candle data returned for {symbol} (got {len(candles)} candles)."
        )

    return candles


# =========================================================
# EMA
# =========================================================

def calculate_ema(values, period):
    if not values:
        return None

    # Fallback to simple average if data length is smaller than period
    if len(values) < period:
        return sum(values) / len(values)

    multiplier = 2 / (period + 1)

    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (
            (price - result) * multiplier
        ) + result

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
        avg_gain = (
            (avg_gain * (actual_period - 1))
            + gains[i]
        ) / actual_period

        avg_loss = (
            (avg_loss * (actual_period - 1))
            + losses[i]
        ) / actual_period

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
        previous_close = safe_float(
            candles[i - 1]["close"]
        )

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
        atr = (
            ((atr * (actual_period - 1)) + tr)
            / actual_period
        )

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
# MARKET STRUCTURE
# =========================================================

def determine_structure(candles):
    """
    Basic structure detection using recent swing highs/lows.
    """

    if len(candles) < 10:
        return "NEUTRAL"

    recent = candles[-20:] if len(candles) >= 20 else candles

    highs = [
        safe_float(c["high"])
        for c in recent
    ]

    lows = [
        safe_float(c["low"])
        for c in recent
    ]

    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]

    if len(highs) < 4 or len(lows) < 4:
        return "NEUTRAL"

    mid = len(highs) // 2

    previous_high = max(highs[:mid])
    recent_high = max(highs[mid:])

    previous_low = min(lows[:mid])
    recent_low = min(lows[mid:])

    if (
        recent_high > previous_high
        and recent_low > previous_low
    ):
        return "BULLISH"

    if (
        recent_high < previous_high
        and recent_low < previous_low
    ):
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def calculate_support_resistance(candles):
    recent = candles[-30:] if len(candles) >= 30 else candles

    highs = [
        safe_float(c["high"])
        for c in recent
    ]

    lows = [
        safe_float(c["low"])
        for c in recent
    ]

    highs = [x for x in highs if x is not None]
    lows = [x for x in lows if x is not None]

    if not highs or not lows:
        return None, None

    support = min(lows)
    resistance = max(highs)

    return support, resistance


# =========================================================
# MOMENTUM
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
# SIGNAL ENGINE
# =========================================================

def analyze_market(symbol, timeframe="15m"):

    candles = get_candles(
        symbol,
        timeframe,
        150
    )

    closes = [
        float(c["close"])
        for c in candles
    ]

    highs = [
        float(c["high"])
        for c in candles
    ]

    lows = [
        float(c["low"])
        for c in candles
    ]

    price = closes[-1]

    # =====================================================
    # INDICATORS
    # =====================================================

    ema9 = calculate_ema(closes, 9)
    ema21 = calculate_ema(closes, 21)
    ema50 = calculate_ema(closes, 50)

    rsi = calculate_rsi(closes, 14)
    atr = calculate_atr(candles, 14)

    if None in (ema9, ema21, ema50, rsi, atr):
        raise RuntimeError("Unable to calculate technical indicators.")

    # =====================================================
    # SUPPORT / RESISTANCE
    # =====================================================

    support, resistance = calculate_support_resistance(candles)

    if support is None or resistance is None:
        support = price - (atr * 2)
        resistance = price + (atr * 2)

    # =====================================================
    # MARKET STRUCTURE
    # =====================================================

    structure = determine_structure(candles)

    # =====================================================
    # SCORE
    # =====================================================

    bullish_score = 0
    bearish_score = 0

    reasons = []

    # -----------------------------------------------------
    # EMA 9 vs EMA 21
    # -----------------------------------------------------

    if ema9 > ema21:
        bullish_score += 15
        reasons.append("EMA 9 above EMA 21")

    elif ema9 < ema21:
        bearish_score += 15
        reasons.append("EMA 9 below EMA 21")

    # -----------------------------------------------------
    # EMA 21 vs EMA 50
    # -----------------------------------------------------

    if ema21 > ema50:
        bullish_score += 15
        reasons.append("EMA 21 above EMA 50")

    elif ema21 < ema50:
        bearish_score += 15
        reasons.append("EMA 21 below EMA 50")

    # -----------------------------------------------------
    # PRICE VS EMA 21
    # -----------------------------------------------------

    if price > ema21:
        bullish_score += 10

    elif price < ema21:
        bearish_score += 10

    # -----------------------------------------------------
    # PRICE VS EMA 50
    # -----------------------------------------------------

    if price > ema50:
        bullish_score += 10

    elif price < ema50:
        bearish_score += 10

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    if 50 <= rsi < 70:
        bullish_score += 15
        reasons.append("RSI supports bullish momentum")

    elif 30 < rsi < 50:
        bearish_score += 15
        reasons.append("RSI supports bearish momentum")

    elif rsi >= 70:
        bullish_score += 8
        reasons.append("Strong bullish RSI momentum")

    elif rsi <= 30:
        bearish_score += 8
        reasons.append("Strong bearish RSI momentum")

    # -----------------------------------------------------
    # STRUCTURE
    # -----------------------------------------------------

    if structure == "BULLISH":
        bullish_score += 15
        reasons.append("Bullish market structure")

    elif structure == "BEARISH":
        bearish_score += 15
        reasons.append("Bearish market structure")

    # -----------------------------------------------------
    # RECENT MOMENTUM
    # -----------------------------------------------------

    momentum = momentum_score(closes)

    if momentum > 0:
        bullish_score += 10
        reasons.append("Recent price momentum is bullish")

    elif momentum < 0:
        bearish_score += 10
        reasons.append("Recent price momentum is bearish")

    # =====================================================
    # DETERMINE TREND
    # =====================================================

    if bullish_score >= bearish_score + 10:
        trend = "BULLISH"

    elif bearish_score >= bullish_score + 10:
        trend = "BEARISH"

    else:
        trend = "NEUTRAL"

    # =====================================================
    # SETUP STRENGTH
    # =====================================================

    setup_strength = max(bullish_score, bearish_score)
    setup_strength = min(100, max(0, int(setup_strength)))

    # =====================================================
    # DETERMINE SIGNAL
    # =====================================================

    if bullish_score >= 60 and bullish_score >= bearish_score + 10:
        signal = "BUY"

    elif bearish_score >= 60 and bearish_score >= bullish_score + 10:
        signal = "SELL"

    else:
        signal = "WAIT"

    # =====================================================
    # ENTRY / SL / TP
    # =====================================================

    entry_low = None
    entry_high = None
    stop_loss = None
    tp1 = None
    tp2 = None
    tp3 = None

    # =====================================================
    # BUY SETUP
    # =====================================================

    if signal == "BUY":
        entry_low = max(support, price - (atr * 0.35))
        entry_high = price + (atr * 0.15)

        atr_stop = price - (atr * 1.2)
        stop_loss = min(support, atr_stop)

        if stop_loss >= price:
            stop_loss = price - atr

        risk = price - stop_loss

        if risk <= 0:
            risk = atr
            stop_loss = price - risk

        tp1 = price + (risk * 1.0)
        tp2 = price + (risk * 2.0)
        tp3 = price + (risk * 3.0)

        if resistance > price:
            if tp2 < resistance:
                tp2 = resistance

            if tp3 < resistance:
                tp3 = max(tp3, resistance + atr * 0.5)

    # =====================================================
    # SELL SETUP
    # =====================================================

    elif signal == "SELL":
        entry_low = price - (atr * 0.15)
        entry_high = min(resistance, price + (atr * 0.35))

        atr_stop = price + (atr * 1.2)
        stop_loss = max(resistance, atr_stop)

        if stop_loss <= price:
            stop_loss = price + atr

        risk = stop_loss - price

        if risk <= 0:
            risk = atr
            stop_loss = price + risk

        tp1 = price - (risk * 1.0)
        tp2 = price - (risk * 2.0)
        tp3 = price - (risk * 3.0)

        if support < price:
            if tp2 > support:
                tp2 = support

            if tp3 > support:
                tp3 = min(tp3, support - atr * 0.5)

    # =====================================================
    # WAIT SETUP
    # =====================================================

    else:
        if trend == "BULLISH":
            entry_low = max(support, price - atr)
            entry_high = price

        elif trend == "BEARISH":
            entry_low = price
            entry_high = min(resistance, price + atr)

        else:
            entry_low = support
            entry_high = resistance

    # =====================================================
    # SETUP DESCRIPTION
    # =====================================================

    if signal == "BUY":
        setup = "Bullish confirmation detected from trend, momentum and technical structure."

    elif signal == "SELL":
        setup = "Bearish confirmation detected from trend, momentum and technical structure."

    elif trend == "BULLISH":
        setup = "Bullish bias detected, but entry confirmation is not strong enough yet."

    elif trend == "BEARISH":
        setup = "Bearish bias detected, but entry confirmation is not strong enough yet."

    else:
        setup = "Market structure is mixed. Wait for stronger directional confirmation."

    # =====================================================
    # RETURN COMPLETE MARKET DATA
    # =====================================================

    return {
        "symbol": symbol.upper().strip(),
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
    }
