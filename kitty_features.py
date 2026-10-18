"""Canonical candle-to-feature transform for Kitty V3 inference.

The retraining script currently consumes a precomputed feature CSV; this module
is the runtime transform. Training-data parity must be established from the
original CSV-generation recipe before retraining or promoting a checkpoint.
"""

FEATURE_NAMES = (
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
)


def _ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * float(value) + (1.0 - alpha) * result[-1])
    return result


def compute_kitty_features(candles):
    """Build the exact 18-feature contract expected by the retrained BTC model."""
    import math
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    if len(closes) < 55:
        raise ValueError(f"At least 55 candles are required for Kitty V3; received {len(closes)}")
    arrays = closes + opens + highs + lows
    if not all(math.isfinite(v) and v > 0 for v in arrays):
        raise ValueError("Candles contain invalid OHLC prices")
    def ret(period):
        return closes[-1] / closes[-1-period] - 1.0
    def sma(period, end=None):
        seq = closes if end is None else closes[:end]
        return sum(seq[-period:]) / period
    sma6, sma20, sma50 = sma(6), sma(20), sma(50)
    changes = [closes[i] / closes[i-1] - 1.0 for i in range(1, len(closes))]
    gains = [max(v, 0.0) for v in changes[-14:]]
    losses = [max(-v, 0.0) for v in changes[-14:]]
    avg_gain = sum(gains) / 14.0
    avg_loss = sum(losses) / 14.0
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (50.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss))
    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_series = [a - b for a, b in zip(ema12, ema26)]
    macd_signal_series = _ema_series(macd_series, 9)
    macd = macd_series[-1] / closes[-1]
    macd_signal = macd_signal_series[-1] / closes[-1]
    macd_hist = (macd_series[-1] - macd_signal_series[-1]) / closes[-1]
    returns = changes
    vol6 = (sum((v - sum(returns[-6:]) / 6.0) ** 2 for v in returns[-6:]) / 6.0) ** 0.5
    vol24 = (sum((v - sum(returns[-24:]) / 24.0) ** 2 for v in returns[-24:]) / 24.0) ** 0.5
    candle_range = highs[-1] - lows[-1]
    return {
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


