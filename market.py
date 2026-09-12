"""Market-data access and pure intraday analysis helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence

import requests

import config

TWELVE_DATA_URL = getattr(config, "TWELVE_DATA_URL", "https://api.twelvedata.com").rstrip("/")


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _series(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    values = [_number(row.get(key)) for row in rows]
    return [value for value in values if value is not None]


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    result = mean(values[:period])
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        result = (value - result) * multiplier + result
    return result


def _rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = mean(gains[:period])
    average_loss = mean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
    if average_loss == 0:
        return 100.0 if average_gain else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _atr(rows: Sequence[Mapping[str, Any]], period: int = 14) -> float | None:
    if len(rows) <= period:
        return None
    true_ranges: list[float] = []
    previous_close = _number(rows[0].get("close"))
    for row in rows[1:]:
        high, low, close = (_number(row.get(key)) for key in ("high", "low", "close"))
        if high is None or low is None or close is None:
            continue
        true_ranges.append(max(high - low, abs(high - (previous_close or close)), abs(low - (previous_close or close))))
        previous_close = close
    if len(true_ranges) < period:
        return None
    return mean(true_ranges[-period:])


def _swing_points(rows: Sequence[Mapping[str, Any]], window: int = 2) -> tuple[list[float], list[float]]:
    highs: list[float] = []
    lows: list[float] = []
    for index in range(window, len(rows) - window):
        high = _number(rows[index].get("high"))
        low = _number(rows[index].get("low"))
        surrounding_highs = [_number(rows[item].get("high")) for item in range(index - window, index + window + 1)]
        surrounding_lows = [_number(rows[item].get("low")) for item in range(index - window, index + window + 1)]
        if high is not None and all(item is not None for item in surrounding_highs) and high == max(surrounding_highs):
            highs.append(high)
        if low is not None and all(item is not None for item in surrounding_lows) and low == min(surrounding_lows):
            lows.append(low)
    return highs, lows


@dataclass(frozen=True)
class MarketAnalysis:
    market: str
    bias: str | None
    action: str
    setup: str | None
    timeframe: str
    current_price: float | None
    entry_zone: tuple[float, float] | None
    stop_loss: float | None
    tp1: float | None
    tp2: float | None
    tp3: float | None
    risk_reward: float | None
    confidence: str
    strength: int | None
    invalidation: str | None
    reasoning: str
    indicators: dict[str, float | None]
    market_structure: dict[str, Any]
    data_provenance: dict[str, Any]
    available: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_time_series(symbol: str, interval: str = "1h", outputsize: int | None = None, timeout: int = 15) -> list[dict[str, Any]]:
    """Fetch candles from the existing Twelve Data integration; return [] on unavailable data."""
    api_key = getattr(config, "TWELVE_DATA_API_KEY", None) or __import__("os").getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return []
    try:
        response = requests.get(
            f"{TWELVE_DATA_URL}/time_series",
            params={"symbol": symbol, "interval": interval, "outputsize": outputsize or config.ANALYSIS_LOOKBACK_BARS, "apikey": api_key, "format": "JSON"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        values = payload.get("values", [])
        return list(reversed(values)) if isinstance(values, list) else []
    except (requests.RequestException, ValueError, TypeError):
        return []


def build_intraday_analysis(symbol: str, rows: Iterable[Mapping[str, Any]], timeframe: str | None = None) -> MarketAnalysis:
    """Build a conservative, machine-readable analysis from supplied candles only."""
    candles = [dict(row) for row in rows]
    timeframe = timeframe or config.ANALYSIS_DEFAULT_TIMEFRAME
    closes = _series(candles, "close")
    if not closes:
        return MarketAnalysis(symbol, None, "WAIT", None, timeframe, None, None, None, None, None, None, None, "LOW", None, "Live candle data is unavailable.", {}, {}, {"source": "unavailable"}, False)
    current = closes[-1]
    ema9, ema21, ema50 = (_ema(closes, period) for period in (9, 21, 50))
    rsi, atr = _rsi(closes), _atr(candles)
    recent = closes[-min(20, len(closes)):]
    volatility = pstdev(recent) if len(recent) > 1 else None
    momentum = current - closes[-min(10, len(closes))] if len(closes) >= 10 else None
    swing_highs, swing_lows = _swing_points(candles)
    support = max(swing_lows[-3:], default=None)
    resistance = min(swing_highs[-3:], default=None)
    bullish = bool(ema9 and ema21 and ema50 and ema9 > ema21 > ema50 and momentum is not None and momentum > 0)
    bearish = bool(ema9 and ema21 and ema50 and ema9 < ema21 < ema50 and momentum is not None and momentum < 0)
    bias = "BULLISH" if bullish else "BEARISH" if bearish else "NEUTRAL"
    extended = bool(atr and abs(current - (ema21 or current)) > atr * 2)
    action = "WAIT" if extended or bias == "NEUTRAL" else ("BUY" if bullish else "SELL")
    setup = "extended/unclear" if action == "WAIT" else "trend continuation"
    entry = (min(current, ema9 or current), max(current, ema9 or current)) if action != "WAIT" else None
    stop = ((entry[0] - atr) if action == "BUY" and entry and atr else (entry[1] + atr) if action == "SELL" and entry and atr else None)
    risk = abs((entry[0] if entry else current) - stop) if stop is not None and entry else None
    tp1 = (current + risk if action == "BUY" and risk else current - risk if action == "SELL" and risk else None)
    tp2 = (current + risk * 2 if action == "BUY" and risk else current - risk * 2 if action == "SELL" and risk else None)
    tp3 = (current + risk * 3 if action == "BUY" and risk else current - risk * 3 if action == "SELL" and risk else None)
    strength = int(max(0, min(100, abs((ema9 or current) - (ema21 or current)) / current * 10000))) if current else None
    return MarketAnalysis(symbol, bias, action, setup, timeframe, current, entry, stop, tp1, tp2, tp3, 2.0 if risk and tp2 else None, "MEDIUM" if action != "WAIT" else "LOW", strength, "Break of the recent swing structure or a move beyond the ATR-based stop.", {"ema9": ema9, "ema21": ema21, "ema50": ema50, "rsi14": rsi, "atr14": atr, "momentum": momentum, "volatility": volatility, "support": support, "resistance": resistance}, {"swing_highs": swing_highs[-5:], "swing_lows": swing_lows[-5:], "trend": bias}, {"source": "Twelve Data candles supplied to function", "live_price": True}, True)
