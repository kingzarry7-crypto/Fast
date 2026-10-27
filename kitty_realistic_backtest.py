"""Research-only OHLC backtester with conservative stop/target handling.

Input candles must be sorted and timestamp-indexed at candle close times. Signals
are observed at a candle close and entered at the next candle open, preventing
same-bar look-ahead. If both stop and target are touched in one candle, stop
wins because OHLC cannot reveal the intrabar path. This is a research tool, not
a broker fill simulator or order executor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    stop_pct: float = 0.005
    target_pct: float = 0.010
    max_hold_bars: int = 24
    spread_bps_per_side: float = 2.0
    commission_bps_per_side: float = 0.0
    slippage_bps_per_side: float = 2.0

    def __post_init__(self) -> None:
        if not (0 < self.stop_pct < 1 and 0 < self.target_pct < 1):
            raise ValueError("stop_pct and target_pct must be between 0 and 1")
        if self.max_hold_bars < 1:
            raise ValueError("max_hold_bars must be >= 1")
        if min(self.spread_bps_per_side, self.commission_bps_per_side, self.slippage_bps_per_side) < 0:
            raise ValueError("cost assumptions cannot be negative")


def _validate_candles(candles: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required - set(candles.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
    frame = candles.copy()
    if not isinstance(frame.index, pd.DatetimeIndex):
        if "timestamp" not in frame.columns:
            raise ValueError("Candles require a DatetimeIndex or timestamp column")
        frame = frame.set_index(pd.to_datetime(frame.pop("timestamp"), utc=True))
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Candle timestamps must be unique and sorted ascending")
    for col in required:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    if not np.isfinite(frame[list(required)].to_numpy(dtype=float)).all():
        raise ValueError("OHLC values must be finite")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC values must be positive")
    if (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("high must be >= open, low and close")
    if (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("low must be <= open, high and close")
    return frame


def backtest_ohlc(
    candles: pd.DataFrame,
    signals: pd.Series,
    config: BacktestConfig = BacktestConfig(),
) -> dict:
    """Backtest -1/0/+1 close-time signals, next-open entries and bracket exits.

    A single position is allowed. Signal values must be -1, 0, or +1. Net return
    is trade return less a fixed round-trip cost estimate in basis points. Stop
    gaps are filled at the worse opening price; targets are filled at target.
    """
    frame = _validate_candles(candles)
    aligned = pd.Series(signals, index=signals.index).reindex(frame.index)
    if aligned.isna().any() or not aligned.isin([-1, 0, 1]).all():
        raise ValueError("signals must align to every candle and contain only -1, 0, +1")
    o = frame["open"].to_numpy(float)
    h = frame["high"].to_numpy(float)
    l = frame["low"].to_numpy(float)
    c = frame["close"].to_numpy(float)
    sig = aligned.to_numpy(int)
    cost = 2 * (config.spread_bps_per_side + config.commission_bps_per_side + config.slippage_bps_per_side) / 10000
    trades: list[dict] = []
    i = 0
    while i < len(frame) - 1:
        direction = int(sig[i])
        if direction == 0:
            i += 1
            continue
        entry_i = i + 1
        entry = o[entry_i]
        stop = entry * (1 - direction * config.stop_pct)
        target = entry * (1 + direction * config.target_pct)
        last_i = min(len(frame) - 1, entry_i + config.max_hold_bars - 1)
        exit_i, exit_price, reason = last_i, c[last_i], "time"
        for j in range(entry_i, last_i + 1):
            if direction == 1:
                stop_hit, target_hit = l[j] <= stop, h[j] >= target
                if stop_hit:
                    exit_i, exit_price, reason = j, min(o[j], stop), "stop"
                    break
                if target_hit:
                    exit_i, exit_price, reason = j, target, "target"
                    break
            else:
                stop_hit, target_hit = h[j] >= stop, l[j] <= target
                if stop_hit:
                    exit_i, exit_price, reason = j, max(o[j], stop), "stop"
                    break
                if target_hit:
                    exit_i, exit_price, reason = j, target, "target"
                    break
        gross = direction * (exit_price / entry - 1)
        net = gross - cost
        trades.append({
            "signal_time": frame.index[i].isoformat(),
            "entry_time": frame.index[entry_i].isoformat(),
            "exit_time": frame.index[exit_i].isoformat(),
            "direction": "LONG" if direction == 1 else "SHORT",
            "entry_price": float(entry),
            "exit_price": float(exit_price),
            "exit_reason": reason,
            "gross_return": float(gross),
            "estimated_cost": float(cost),
            "net_return": float(net),
        })
        # Do not overlap trades or reuse a signal while a position is open.
        i = exit_i + 1
    returns = np.array([t["net_return"] for t in trades], dtype=float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    equity = np.cumprod(1 + returns) if len(returns) else np.array([], dtype=float)
    if len(equity):
        peak = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        drawdown = equity / peak - 1
        max_drawdown = float(min(0.0, drawdown.min()))
        compounded = float(equity[-1] - 1)
    else:
        max_drawdown, compounded = 0.0, 0.0
    gross_losses = abs(float(losses.sum()))
    return {
        "trade_count": len(trades),
        "win_rate": float((returns > 0).mean()) if len(returns) else None,
        "average_net_return": float(returns.mean()) if len(returns) else None,
        "profit_factor": float(wins.sum() / gross_losses) if gross_losses else (float("inf") if len(wins) else None),
        "compounded_net_return": compounded,
        "max_drawdown": max_drawdown,
        "estimated_round_trip_cost": float(cost),
        "same_bar_stop_target_policy": "stop_first",
        "trades": trades,
    }


def _completed_timeframe(frame: pd.DataFrame, rule: str, fast: int, slow: int, prefix: str) -> pd.DataFrame:
    """Calculate EMA direction on fully closed resampled candles."""
    bars = frame[["open", "high", "low", "close"]].resample(rule, closed="right", label="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    bars[f"{prefix}_fast"] = bars["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    bars[f"{prefix}_slow"] = bars["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    bars[f"{prefix}_direction"] = np.sign(bars[f"{prefix}_fast"] - bars[f"{prefix}_slow"]).astype(float)
    return bars[[f"{prefix}_direction"]].dropna()


def build_mtf_signals(candles_5m: pd.DataFrame) -> pd.Series:
    """Conservative 4H trend + 1H direction + 15M setup + 5M timing signals.

    Index timestamps represent candle close times. Higher-timeframe states are
    backward-asof joined only after those candles have closed. Signal at close
    executes no earlier than the next 5-minute candle open in backtest_ohlc.
    """
    frame = _validate_candles(candles_5m)
    base = frame[["open", "high", "low", "close"]].copy()
    contexts = [
        _completed_timeframe(base, "4h", 12, 26, "h4"),
        _completed_timeframe(base, "1h", 8, 21, "h1"),
        _completed_timeframe(base, "15min", 8, 20, "m15"),
    ]
    joined = base.reset_index(names="timestamp").sort_values("timestamp")
    for context in contexts:
        right = context.reset_index(names="timestamp").sort_values("timestamp")
        joined = pd.merge_asof(joined, right, on="timestamp", direction="backward", allow_exact_matches=True)
    close = joined["close"]
    ema5 = close.ewm(span=8, adjust=False, min_periods=8).mean()
    prior_close, prior_ema = close.shift(1), ema5.shift(1)
    timing_long = (close > ema5) & (prior_close <= prior_ema)
    timing_short = (close < ema5) & (prior_close >= prior_ema)
    rsi_delta = close.diff()
    gain = rsi_delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-rsi_delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    long_ok = (
        (joined["h4_direction"] > 0) & (joined["h1_direction"] > 0)
        & (joined["m15_direction"] > 0) & timing_long & rsi.between(45, 70)
    )
    short_ok = (
        (joined["h4_direction"] < 0) & (joined["h1_direction"] < 0)
        & (joined["m15_direction"] < 0) & timing_short & rsi.between(30, 55)
    )
    result = pd.Series(np.select([long_ok, short_ok], [1, -1], default=0), index=frame.index, name="signal")
    return result.astype(int)
