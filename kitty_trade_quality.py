"""Leakage-aware, research-only trade-quality confirmation for Kitty.

Features use only information available at the signal candle close. Labels are
created from subsequent OHLC bars by the existing next-open, stop-first
backtester and include estimated spread, commission, and slippage. This module
never places orders and does not persist a production model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from kitty_realistic_backtest import BacktestConfig, backtest_ohlc

MIN_TRAIN_TRADES = 40
MIN_SAMPLES_PER_CLASS = 10
DEFAULT_THRESHOLDS = (0.50, 0.55, 0.60, 0.65, 0.70)


def _aligned_signals(candles: pd.DataFrame, signals: pd.Series) -> pd.Series:
    aligned = pd.Series(signals, index=signals.index).reindex(candles.index)
    if aligned.isna().any() or not aligned.isin([-1, 0, 1]).all():
        raise ValueError("signals must align to every candle and contain only -1, 0, +1")
    return aligned.astype(int)


def build_quality_features(candles: pd.DataFrame, signals: pd.Series) -> pd.DataFrame:
    """Build causal, scale-normalized technical features at each candle close."""
    required = {"open", "high", "low", "close"}
    missing = required - set(candles.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
    frame = candles.copy()
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(frame[["open", "high", "low", "close"]].to_numpy(float)).all():
        raise ValueError("OHLC values must be finite")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC values must be positive")
    direction = _aligned_signals(frame, signals)
    close, high, low, open_ = frame["close"], frame["high"], frame["low"], frame["open"]
    returns = close.pct_change()
    ema8 = close.ewm(span=8, adjust=False, min_periods=8).mean()
    ema21 = close.ewm(span=21, adjust=False, min_periods=21).mean()
    ema50 = close.ewm(span=50, adjust=False, min_periods=50).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low, (high - previous_close).abs(), (low - previous_close).abs()
    ], axis=1).max(axis=1)
    atr = true_range.rolling(14, min_periods=14).mean()
    candle_range = (high - low).replace(0, np.nan)
    features = pd.DataFrame({
        "direction": direction.astype(float),
        "return_1": returns,
        "return_3": close.pct_change(3),
        "return_6": close.pct_change(6),
        "return_12": close.pct_change(12),
        "return_24": close.pct_change(24),
        "ema_gap_8_21": ema8 / ema21 - 1,
        "ema_gap_21_50": ema21 / ema50 - 1,
        "close_gap_ema8": close / ema8 - 1,
        "rsi_14": rsi,
        "atr_pct_14": atr / close,
        "volatility_12": returns.rolling(12, min_periods=12).std(),
        "volatility_48": returns.rolling(48, min_periods=48).std(),
        "candle_body_pct": (close - open_) / open_,
        "candle_range_pct": (high - low) / close,
        "close_position": (close - low) / candle_range,
    }, index=frame.index)
    return features.replace([np.inf, -np.inf], np.nan)


def label_trade_outcomes(
    candles: pd.DataFrame,
    signals: pd.Series,
    config: BacktestConfig,
) -> pd.Series:
    """Return labels only for trades actually completed by the backtester.

    1 means positive estimated net return after costs; 0 means zero/negative.
    Unexecuted signals and signals without a completed simulated trade stay NaN.
    """
    aligned = _aligned_signals(candles, signals)
    result = pd.Series(np.nan, index=candles.index, dtype=float, name="profitable")
    trades = backtest_ohlc(candles, aligned, config)["trades"]
    for trade in trades:
        signal_time = pd.Timestamp(trade["signal_time"])
        if signal_time in result.index:
            result.loc[signal_time] = float(trade["net_return"] > 0)
    return result


def train_quality_model(features: pd.DataFrame, labels: pd.Series):
    """Fit only with enough past, executed trades and balanced outcome examples.

    Returns None rather than a weak/unstable model when the sample is too small.
    """
    aligned_labels = pd.Series(labels, index=labels.index).reindex(features.index)
    valid = aligned_labels.notna() & features.notna().all(axis=1)
    x = features.loc[valid]
    y = aligned_labels.loc[valid].astype(int)
    if len(y) < MIN_TRAIN_TRADES:
        return None
    counts = y.value_counts()
    if any(int(counts.get(label, 0)) < MIN_SAMPLES_PER_CLASS for label in (0, 1)):
        return None
    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=4,
        min_samples_leaf=max(5, int(np.ceil(len(y) * 0.03))),
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=1,
    )
    model.fit(x, y)
    return model


def predict_quality(model, features: pd.DataFrame) -> pd.Series:
    """Predict estimated probability of a positive after-cost trade outcome."""
    probabilities = pd.Series(np.nan, index=features.index, dtype=float, name="quality_probability")
    valid = features.notna().all(axis=1)
    if model is not None and valid.any():
        probabilities.loc[valid] = model.predict_proba(features.loc[valid])[:, 1]
    return probabilities


def filter_signals(
    signals: pd.Series,
    probabilities: pd.Series,
    threshold: float,
) -> pd.Series:
    """Keep candidate BUY/SELL directions only when the quality score passes."""
    if not 0 < threshold < 1:
        raise ValueError("threshold must be strictly between 0 and 1")
    aligned = pd.Series(signals, index=signals.index).astype(int)
    scores = pd.Series(probabilities, index=probabilities.index).reindex(aligned.index)
    keep = aligned.ne(0) & scores.ge(threshold).fillna(False)
    return aligned.where(keep, 0).astype(int)
