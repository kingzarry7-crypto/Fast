import requests

from config import (
    TWELVE_DATA_API_KEY,
    TWELVE_DATA_URL
)


# =========================================================
# KING ZARRY AI 👑
# MARKET ENGINE
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

    return TIMEFRAME_MAP.get(
        timeframe,
        timeframe
    )


# =========================================================
# GET CURRENT PRICE
# =========================================================

def get_price(symbol):

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing."
        )

    response = requests.get(

        f"{TWELVE_DATA_URL}/price",

        params={
            "symbol": symbol,
            "apikey": TWELVE_DATA_API_KEY
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Twelve Data HTTP error: "
            f"{response.status_code}"
        )

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error."
            )
        )

    if "price" not in data:

        raise RuntimeError(
            f"Price unavailable: {data}"
        )

    return float(
        data["price"]
    )


# =========================================================
# GET CANDLES
# =========================================================

def get_candles(
    symbol,
    timeframe="15m",
    outputsize=100
):

    if not TWELVE_DATA_API_KEY:

        raise RuntimeError(
            "TWELVE_DATA_API_KEY is missing."
        )

    interval = normalize_timeframe(
        timeframe
    )

    response = requests.get(

        f"{TWELVE_DATA_URL}/time_series",

        params={
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVE_DATA_API_KEY
        },

        timeout=30
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Twelve Data HTTP error: "
            f"{response.status_code}"
        )

    data = response.json()

    if data.get("status") == "error":

        raise RuntimeError(
            data.get(
                "message",
                "Twelve Data error."
            )
        )

    if "values" not in data:

        raise RuntimeError(
            f"No candle data returned: {data}"
        )

    candles = list(
        reversed(
            data["values"]
        )
    )

    if len(candles) < 50:

        raise RuntimeError(
            "Not enough market data."
        )

    return candles


# =========================================================
# EMA
# =========================================================

def calculate_ema(
    values,
    period
):

    if len(values) < period:

        return None

    multiplier = 2 / (
        period + 1
    )

    result = sum(
        values[:period]
    ) / period

    for price in values[period:]:

        result = (
            (
                price - result
            ) * multiplier
        ) + result

    return result


# =========================================================
# RSI
# =========================================================

def calculate_rsi(
    values,
    period=14
):

    if len(values) < period + 1:

        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(values)
    ):

        change = (
            values[i]
            - values[i - 1]
        )

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(
                abs(change)
            )

    avg_gain = (
        sum(gains[:period])
        / period
    )

    avg_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains)
    ):

        avg_gain = (
            (
                avg_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        avg_loss = (
            (
                avg_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if avg_loss == 0:

        return 100.0

    rs = (
        avg_gain
        / avg_loss
    )

    return 100 - (
        100 / (1 + rs)
    )


# =========================================================
# MARKET ANALYSIS
# =========================================================

def analyze_market(
    symbol,
    timeframe="15m"
):

    candles = get_candles(
        symbol,
        timeframe,
        100
    )

    closes = [
        float(candle["close"])
        for candle in candles
    ]

    highs = [
        float(candle["high"])
        for candle in candles
    ]

    lows = [
        float(candle["low"])
        for candle in candles
    ]

    price = closes[-1]

    # -----------------------------------------------------
    # INDICATORS
    # -----------------------------------------------------

    ema9 = calculate_ema(
        closes,
        9
    )

    ema21 = calculate_ema(
        closes,
        21
    )

    ema50 = calculate_ema(
        closes,
        50
    )

    rsi = calculate_rsi(
        closes,
        14
    )

    if None in (
        ema9,
        ema21,
        ema50,
        rsi
    ):

        raise RuntimeError(
            "Unable to calculate indicators."
        )

    # -----------------------------------------------------
    # SUPPORT / RESISTANCE
    # -----------------------------------------------------

    support = min(
        lows[-20:]
    )

    resistance = max(
        highs[-20:]
    )

    # -----------------------------------------------------
    # TREND SCORE
    # -----------------------------------------------------

    score = 0

    if ema9 > ema21:

        score += 1

    else:

        score -= 1

    if ema21 > ema50:

        score += 1

    else:

        score -= 1

    if price > ema21:

        score += 1

    else:

        score -= 1

    if rsi > 50:

        score += 1

    else:

        score -= 1

    # -----------------------------------------------------
    # SIGNAL
    # -----------------------------------------------------

    if score >= 3:

        signal = "BUY"
        trend = "BULLISH"

    elif score <= -3:

        signal = "SELL"
        trend = "BEARISH"

    else:

        signal = "WAIT"
        trend = "NEUTRAL"

    # -----------------------------------------------------
    # STOP LOSS / TAKE PROFIT
    # -----------------------------------------------------

    if signal == "BUY":

        stop_loss = support

        risk = price - stop_loss

        # Safety fallback if support is
        # too close or above the entry.

        if risk <= 0:

            stop_loss = price * 0.995

            risk = (
                price
                - stop_loss
            )

        take_profit = (
            price
            + (risk * 2)
        )

    elif signal == "SELL":

        stop_loss = resistance

        risk = (
            stop_loss
            - price
        )

        # Safety fallback if resistance
        # is too close or below the entry.

        if risk <= 0:

            stop_loss = price * 1.005

            risk = (
                stop_loss
                - price
            )

        take_profit = (
            price
            - (risk * 2)
        )

    else:

        stop_loss = None

        take_profit = None

    # -----------------------------------------------------
    # RETURN COMPLETE MARKET DATA
    # -----------------------------------------------------

    return {

        "symbol":
            symbol,

        "timeframe":
            timeframe,

        "price":
            price,

        "signal":
            signal,

        "trend":
            trend,

        "support":
            support,

        "resistance":
            resistance,

        "ema9":
            ema9,

        "ema21":
            ema21,

        "ema50":
            ema50,

        "rsi":
            rsi,

        "stop_loss":
            stop_loss,

        "take_profit":
            take_profit
    }
