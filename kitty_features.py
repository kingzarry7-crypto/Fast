"""Canonical hourly candle-to-feature transform for Kitty V3 inference.

The model contract is hourly. Candle validation rejects malformed OHLC bars and,
when timestamps are supplied, missing/duplicate/out-of-order/non-hourly bars.
The training-data builder must preserve this same feature contract.
"""

from datetime import datetime, timezone
import math

FEATURE_NAMES = (
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
)


def normalize_candle_timestamp(raw):
    """Normalize ISO timestamps and Unix seconds/milliseconds to UTC ISO-8601."""
    if raw is None:
        raise ValueError("Candle timestamp is missing")
    value = str(raw).strip()
    if not value:
        raise ValueError("Candle timestamp is empty")
    try:
        epoch = float(value)
        if not math.isfinite(epoch):
            raise ValueError("Candle timestamp must be finite")
        if abs(epoch) > 10_000_000_000:
            epoch /= 1000.0
        stamp = datetime.fromtimestamp(epoch, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Candle timestamp must be ISO-8601 or Unix seconds/milliseconds") from exc
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat()


def _ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * float(value) + (1.0 - alpha) * result[-1])
    return result


def _validate_candles(candles, expected_interval_seconds=3600):
    if len(candles) < 55:
        raise ValueError(f"At least 55 candles are required for Kitty V3; received {len(candles)}")
    opens, highs, lows, closes = [], [], [], []
    for index, candle in enumerate(candles):
        try:
            opn, high, low, close = (
                float(candle["open"]), float(candle["high"]),
                float(candle["low"]), float(candle["close"]),
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Candle {index} is missing valid OHLC prices") from exc
        if not all(math.isfinite(v) and v > 0 for v in (opn, high, low, close)):
            raise ValueError("Candles contain invalid OHLC prices")
        if high < max(opn, close, low) or low > min(opn, close, high) or high < low:
            raise ValueError(f"Candle {index} has inconsistent OHLC bounds")
        opens.append(opn)
        highs.append(high)
        lows.append(low)
        closes.append(close)

    has_timestamp = ["timestamp" in candle or "datetime" in candle or "time" in candle for candle in candles]
    if any(has_timestamp) and not all(has_timestamp):
        raise ValueError("Candle timestamps must be present on every row or none")
    if all(has_timestamp):
        stamps = []
        for candle in candles:
            raw = candle.get("timestamp", candle.get("datetime", candle.get("time")))
            stamps.append(datetime.fromisoformat(normalize_candle_timestamp(raw).replace("Z", "+00:00")).timestamp())
        for previous, current in zip(stamps, stamps[1:]):
            delta = current - previous
            if delta <= 0:
                raise ValueError("Candle timestamps must be strictly increasing with no duplicates")
            if delta != expected_interval_seconds:
                raise ValueError(
                    f"Kitty V3 requires consecutive hourly candles ({expected_interval_seconds}s); "
                    f"found a {delta:g}s interval"
                )
    return opens, highs, lows, closes


def compute_kitty_features(candles):
    """Build the exact 18-feature contract expected by the retrained BTC model."""
    opens, highs, lows, closes = _validate_candles(candles)
    def ret(period):
        return closes[-1] / closes[-1-period] - 1.0
    def sma(period):
        return sum(closes[-period:]) / period

    sma6, sma20, sma50 = sma(6), sma(20), sma(50)
    changes = [closes[i] / closes[i-1] - 1.0 for i in range(1, len(closes))]
    gains = [max(v, 0.0) for v in changes[-14:]]
    losses = [max(-v, 0.0) for v in changes[-14:]]
    avg_gain = sum(gains) / 14.0
    avg_loss = sum(losses) / 14.0
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (
        50.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    )
    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_series = [a - b for a, b in zip(ema12, ema26)]
    macd_signal_series = _ema_series(macd_series, 9)
    macd = macd_series[-1] / closes[-1]
    macd_signal = macd_signal_series[-1] / closes[-1]
    macd_hist = (macd_series[-1] - macd_signal_series[-1]) / closes[-1]
    vol6 = (sum((v - sum(changes[-6:]) / 6.0) ** 2 for v in changes[-6:]) / 6.0) ** 0.5
    vol24 = (sum((v - sum(changes[-24:]) / 24.0) ** 2 for v in changes[-24:]) / 24.0) ** 0.5
    candle_range = highs[-1] - lows[-1]
    features = {
        "ret_1h": ret(1), "ret_3h": ret(3), "ret_6h": ret(6),
        "ret_12h": ret(12), "ret_24h": ret(24),
        "close_vs_sma6": closes[-1] / sma6 - 1.0,
        "close_vs_sma20": closes[-1] / sma20 - 1.0,
        "close_vs_sma50": closes[-1] / sma50 - 1.0,
        "sma6_vs_sma20": sma6 / sma20 - 1.0,
        "rsi_14": rsi,
        "macd_norm": macd, "macd_signal_norm": macd_signal,
        "macd_hist_norm": macd_hist, "volatility_6h": vol6,
        "volatility_24h": vol24,
        "range_pct": candle_range / closes[-1],
        "body_pct": (closes[-1] - opens[-1]) / opens[-1],
        "close_position": (closes[-1] - lows[-1]) / candle_range if candle_range > 0 else 0.5,
    }
    if list(features) != list(FEATURE_NAMES) or not all(math.isfinite(v) for v in features.values()):
        raise ValueError("Kitty feature transform returned an invalid feature contract")
    return features
