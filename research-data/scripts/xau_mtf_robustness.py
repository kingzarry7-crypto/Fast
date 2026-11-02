"""Research-only XAU/USD multi-timeframe robustness experiment.

Input: 15-minute OHLC CSV with candle-close UTC timestamps and columns
timestamp,open,high,low,close. No network access, model promotion, production
signal changes, broker access, or order execution occurs in this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HOLDING_PERIODS = (4, 8, 16, 32)  # 1h, 2h, 4h, 8h on 15m candles
COST_MULTIPLIERS = (1.0, 1.5, 2.0)
MOMENTUM_THRESHOLDS = (0.0, 0.0005, 0.0010)
RSI_BANDS = ((45.0, 68.0), (48.0, 65.0))
RISK_PAIRS = ((0.0025, 0.0050), (0.0035, 0.0070), (0.0050, 0.0100))
MIN_FOLD_TRADES = 8


@dataclass(frozen=True)
class Candidate:
    direction: str
    momentum_threshold: float
    rsi_low: float
    rsi_high: float
    stop_pct: float
    target_pct: float
    max_hold_bars: int


def load_ohlc(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame = frame.sort_values("timestamp", kind="stable").set_index("timestamp")
    if frame.index.has_duplicates:
        raise ValueError("duplicate candle timestamps")
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("OHLC values must be finite and positive")
    if (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("invalid high")
    if (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("invalid low")
    if len(frame) < 1200:
        raise ValueError("at least 1200 15-minute candles are required")
    if not frame.index.is_monotonic_increasing:
        raise ValueError("timestamps must be ascending")
    return frame


def _complete_context(frame: pd.DataFrame, rule: str, expected: int, fast: int, slow: int, prefix: str) -> pd.DataFrame:
    resampler = frame[["open", "high", "low", "close"]].resample(rule, closed="right", label="right")
    counts = resampler["close"].count()
    bars = resampler.agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    bars = bars.loc[counts.reindex(bars.index).eq(expected)].copy()
    bars[f"{prefix}_fast"] = bars["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    bars[f"{prefix}_slow"] = bars["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    bars[f"{prefix}_direction"] = np.sign(bars[f"{prefix}_fast"] - bars[f"{prefix}_slow"])
    bars[f"{prefix}_momentum"] = bars["close"].pct_change(4)
    return bars[[f"{prefix}_direction", f"{prefix}_momentum"]].dropna()


def build_features(frame: pd.DataFrame, train_end: int) -> pd.DataFrame:
    """Causal 4H trend + 1H momentum + 15M setup; context joins after close."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("frame requires a DatetimeIndex")
    base = frame[["open", "high", "low", "close"]].copy()
    joined = base.reset_index(names="timestamp").sort_values("timestamp")
    for context in (
        _complete_context(base, "4h", 16, 12, 26, "h4"),
        _complete_context(base, "1h", 4, 8, 21, "h1"),
    ):
        right = context.reset_index(names="timestamp").sort_values("timestamp")
        joined = pd.merge_asof(joined, right, on="timestamp", direction="backward", allow_exact_matches=True)
    close = joined["close"]
    # Reset short-timeframe indicators at any missing 15-minute candle.
    gap = joined["timestamp"].diff().gt(pd.Timedelta(minutes=15)).fillna(False)
    segment = gap.cumsum()
    grouped = close.groupby(segment)
    ema8 = grouped.transform(lambda x: x.ewm(span=8, adjust=False, min_periods=8).mean())
    ema21 = grouped.transform(lambda x: x.ewm(span=21, adjust=False, min_periods=21).mean())
    delta = grouped.diff()
    gain = delta.clip(lower=0).groupby(segment).transform(lambda x: x.ewm(alpha=1/14, adjust=False, min_periods=14).mean())
    loss = (-delta.clip(upper=0)).groupby(segment).transform(lambda x: x.ewm(alpha=1/14, adjust=False, min_periods=14).mean())
    rs = gain / loss.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).mask((loss == 0) & (gain > 0), 100.0).mask((loss == 0) & (gain == 0), 50.0)
    returns = close.pct_change()
    volatility = returns.groupby(segment).transform(lambda x: x.rolling(96, min_periods=48).std())
    result = joined[["timestamp", "open", "high", "low", "close", "h4_direction", "h1_momentum"]].copy()
    result["h4_direction"] = result["h4_direction"]
    result["h1_momentum"] = result["h1_momentum"]
    result["ema8"] = ema8
    result["ema21"] = ema21
    result["rsi"] = rsi
    result["volatility"] = volatility
    # Volatility regime boundaries are fitted only on the training partition.
    train_vol = result.loc[: max(0, train_end - 1), "volatility"].dropna()
    if len(train_vol) < 100:
        raise ValueError("insufficient training volatility observations")
    low_cut, high_cut = train_vol.quantile([1/3, 2/3]).tolist()
    result["volatility_regime"] = np.select(
        [result["volatility"] <= low_cut, result["volatility"] <= high_cut],
        ["low", "medium"], default="high"
    )
    return result.set_index(pd.DatetimeIndex(result.pop("timestamp")))


def make_signals(features: pd.DataFrame, candidate: Candidate) -> pd.Series:
    long_setup = (
        (features["h4_direction"] > 0)
        & (features["h1_momentum"] > candidate.momentum_threshold)
        & (features["ema8"] > features["ema21"])
        & (features["close"] > features["ema8"])
        & features["rsi"].between(candidate.rsi_low, candidate.rsi_high)
    )
    short_setup = (
        (features["h4_direction"] < 0)
        & (features["h1_momentum"] < -candidate.momentum_threshold)
        & (features["ema8"] < features["ema21"])
        & (features["close"] < features["ema8"])
        & features["rsi"].between(100 - candidate.rsi_high, 100 - candidate.rsi_low)
    )
    signal = np.zeros(len(features), dtype=int)
    if candidate.direction in ("long_only", "both"):
        signal[long_setup.fillna(False).to_numpy()] = 1
    if candidate.direction in ("short_only", "both"):
        signal[short_setup.fillna(False).to_numpy()] = -1
    return pd.Series(signal, index=features.index, dtype=int)


def _metrics(trades: list[dict], cost: float) -> dict:
    returns = np.asarray([t["net_return"] for t in trades], dtype=float)
    wins, losses = returns[returns > 0], returns[returns < 0]
    equity = np.cumprod(1 + returns) if len(returns) else np.asarray([])
    if len(equity):
        peak = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        drawdown = float(min(0.0, (equity / peak - 1).min()))
        compounded = float(equity[-1] - 1)
    else:
        drawdown, compounded = 0.0, 0.0
    return {
        "trade_count": len(trades),
        "average_net_return": float(returns.mean()) if len(returns) else None,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) else (float("inf") if len(wins) else None),
        "compounded_net_return": compounded,
        "max_drawdown": drawdown,
        "estimated_round_trip_cost": cost,
    }


def backtest(frame: pd.DataFrame, signals: pd.Series, candidate: Candidate, round_trip_cost_bps: float) -> dict:
    """One-position OHLC simulator; next-open entry, stop-first intrabar policy."""
    if not signals.index.equals(frame.index):
        raise ValueError("signals must align exactly to the evaluation candles")
    if not signals.isin([-1, 0, 1]).all():
        raise ValueError("signals must be -1, 0, or +1")
    if not np.isfinite(round_trip_cost_bps) or round_trip_cost_bps < 0:
        raise ValueError("round-trip cost bps must be finite and non-negative")
    cost = round_trip_cost_bps / 10000.0
    trades: list[dict] = []
    i = 0
    while i < len(frame) - 1:
        direction = int(signals.iloc[i])
        if direction == 0:
            i += 1
            continue
        entry_i = i + 1
        last_i = entry_i + candidate.max_hold_bars - 1
        if last_i >= len(frame):
            i += 1
            continue
        entry_time = frame.index[entry_i]
        if entry_time - frame.index[i] > pd.Timedelta(minutes=15):
            i += 1
            continue
        entry = float(frame["open"].iloc[entry_i])
        stop = entry * (1 - direction * candidate.stop_pct)
        target = entry * (1 + direction * candidate.target_pct)
        exit_i, exit_price, reason = last_i, float(frame["close"].iloc[last_i]), "time"
        for j in range(entry_i, last_i + 1):
            high, low, opening = float(frame["high"].iloc[j]), float(frame["low"].iloc[j]), float(frame["open"].iloc[j])
            if direction == 1:
                if low <= stop:
                    exit_i, exit_price, reason = j, min(opening, stop), "stop"
                    break
                if high >= target:
                    exit_i, exit_price, reason = j, target, "target"
                    break
            else:
                if high >= stop:
                    exit_i, exit_price, reason = j, max(opening, stop), "stop"
                    break
                if low <= target:
                    exit_i, exit_price, reason = j, target, "target"
                    break
            if j < len(frame) - 1 and frame.index[j + 1] - frame.index[j] > pd.Timedelta(minutes=15):
                exit_i, exit_price, reason = j, float(frame["close"].iloc[j]), "session_gap"
                break
        gross = direction * (exit_price / entry - 1)
        trades.append({
            "signal_time": frame.index[i].isoformat(),
            "entry_time": entry_time.isoformat(),
            "exit_time": frame.index[exit_i].isoformat(),
            "direction": "LONG" if direction == 1 else "SHORT",
            "exit_reason": reason,
            "gross_return": gross,
            "estimated_cost": cost,
            "net_return": gross - cost,
            "volatility_regime": None,
        })
        i = exit_i
    return {**_metrics(trades, cost), "trades": trades}


def build_baseline_signals(features: pd.DataFrame, kind: str) -> pd.Series:
    """Frozen comparison rules: 1H momentum-only and 4H/1H trend alignment."""
    if kind == "momentum":
        direction = np.sign(features["h1_momentum"].fillna(0))
    elif kind == "trend":
        direction = np.where(
            (features["h4_direction"] > 0) & (features["h1_momentum"] > 0), 1,
            np.where((features["h4_direction"] < 0) & (features["h1_momentum"] < 0), -1, 0),
        )
    else:
        raise ValueError("kind must be momentum or trend")
    return pd.Series(direction, index=features.index, dtype=int)


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if not np.isfinite(value):
            return "Infinity" if value > 0 else ("-Infinity" if value < 0 else None)
        return float(value)
    return value


def _candidate_grid() -> list[Candidate]:
    candidates = []
    for direction in ("long_only", "short_only", "both"):
        for momentum in MOMENTUM_THRESHOLDS:
            for rsi_low, rsi_high in RSI_BANDS:
                for stop, target in RISK_PAIRS:
                    for holding in HOLDING_PERIODS:
                        candidates.append(Candidate(direction, momentum, rsi_low, rsi_high, stop, target, holding))
    return candidates


def _fold_slices(start: int, end: int) -> list[tuple[int, int]]:
    return [(start + (end - start) * i // 3, start + (end - start) * (i + 1) // 3) for i in range(3)]


def evaluate(path: str | Path, round_trip_cost_bps: float = 5.0) -> dict:
    if not np.isfinite(round_trip_cost_bps) or round_trip_cost_bps < 0:
        raise ValueError("round-trip cost bps must be finite and non-negative")
    frame = load_ohlc(path)
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    n = len(frame)
    train_end, validation_end = int(n * .60), int(n * .80)
    # Purge the longest 8-hour holding horizon around split boundaries.
    features = build_features(frame, train_end)
    validation = frame.iloc[train_end + max(HOLDING_PERIODS):validation_end].copy()
    test = frame.iloc[validation_end + max(HOLDING_PERIODS):].copy()
    feature_validation = features.reindex(validation.index)
    feature_test = features.reindex(test.index)
    folds = _fold_slices(0, len(validation))
    candidates = []
    for candidate in _candidate_grid():
        signal = make_signals(features, candidate)
        fold_metrics = []
        stress_fold_metrics = {str(mult): [] for mult in COST_MULTIPLIERS}
        for a, b in folds:
            fold_frame = validation.iloc[a:b]
            fold_signal = signal.reindex(fold_frame.index).fillna(0).astype(int)
            for mult in COST_MULTIPLIERS:
                result = backtest(fold_frame, fold_signal, candidate, round_trip_cost_bps * mult)
                stress_fold_metrics[str(mult)].append(result)
            fold_metrics.append(stress_fold_metrics["1.0"][-1])
        # Selection sees validation folds only, including the most severe cost scenario.
        two_x = stress_fold_metrics["2.0"]
        eligible = all(
            item["trade_count"] >= MIN_FOLD_TRADES
            and item["compounded_net_return"] > 0
            and item["profit_factor"] is not None
            and item["profit_factor"] >= 1.05
            and item["max_drawdown"] >= -0.08
            for item in two_x
        )
        candidates.append({
            "candidate": candidate,
            "eligible": eligible,
            "folds": fold_metrics,
            "stress_folds": stress_fold_metrics,
            "score": min((m["compounded_net_return"] for m in two_x), default=float("-inf")),
        })
    eligible = [item for item in candidates if item["eligible"]]
    selected = max(eligible, key=lambda item: item["score"], default=None)
    # Benchmarks are frozen, non-tuned rule baselines and are reported separately.
    benchmark_candidates = {
        "momentum": Candidate("both", 0.0, 45, 68, 0.0035, 0.007, 8),
        "trend": Candidate("both", 0.0, 48, 65, 0.0025, 0.005, 8),
    }
    benchmarks = {}
    for name, candidate in benchmark_candidates.items():
        sig = build_baseline_signals(features, name)
        benchmarks[name] = {
            str(mult): backtest(test, sig.reindex(test.index).fillna(0).astype(int), candidate, round_trip_cost_bps * mult)
            for mult in COST_MULTIPLIERS
        }
    if selected is None:
        selected_report = None
        candidate_test = None
    else:
        candidate = selected["candidate"]
        sig = make_signals(features, candidate)
        selected_report = {
            "direction": candidate.direction,
            "momentum_threshold": candidate.momentum_threshold,
            "rsi_band": [candidate.rsi_low, candidate.rsi_high],
            "stop_pct": candidate.stop_pct,
            "target_pct": candidate.target_pct,
            "max_hold_bars_15m": candidate.max_hold_bars,
            "validation_folds": selected["folds"],
            "validation_stress_folds": selected["stress_folds"],
        }
        candidate_test = {
            str(mult): backtest(test, sig.reindex(test.index).fillna(0).astype(int), candidate, round_trip_cost_bps * mult)
            for mult in COST_MULTIPLIERS
        }
    # Regime report is descriptive only; it cannot be used to retune the candidate.
    regime_metrics = {}
    if candidate_test is not None:
        for regime in ("low", "medium", "high"):
            subset = test.loc[feature_test["volatility_regime"].eq(regime)]
            regime_metrics[regime] = {
                str(mult): backtest(
                    subset,
                    make_signals(features, selected["candidate"]).reindex(subset.index).fillna(0).astype(int),
                    selected["candidate"],
                    round_trip_cost_bps * mult,
                ) if len(subset) else _metrics([], round_trip_cost_bps * mult / 10000)
                for mult in COST_MULTIPLIERS
            }
    return {
        "run_id": "xau-mtf-robustness-run-001",
        "symbol": "XAUUSD",
        "timeframe": "15m execution; completed 4h trend and 1h momentum context",
        "dataset_sha256": digest,
        "rows": n,
        "first_candle_close_utc": frame.index[0].isoformat(),
        "last_candle_close_utc": frame.index[-1].isoformat(),
        "split": {"train_end_index": train_end, "validation_start_index": train_end, "validation_end_index": validation_end, "test_start_index": validation_end, "purge_bars": max(HOLDING_PERIODS), "selection_uses_test": False},
        "cost_assumptions": {"base_round_trip_bps": round_trip_cost_bps, "multipliers": list(COST_MULTIPLIERS), "source": "explicit CLI assumption; not verified broker fills"},
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "selected_candidate": selected_report,
        "selected_candidate_test": candidate_test,
        "frozen_baseline_test": benchmarks,
        "selected_candidate_test_by_volatility_regime": regime_metrics,
        "candidate_screen_validation_only": [
            {"direction": item["candidate"].direction, "momentum_threshold": item["candidate"].momentum_threshold, "rsi_band": [item["candidate"].rsi_low, item["candidate"].rsi_high], "stop_pct": item["candidate"].stop_pct, "target_pct": item["candidate"].target_pct, "max_hold_bars_15m": item["candidate"].max_hold_bars, "eligible_at_2x_all_folds": item["eligible"], "worst_2x_validation_fold_return": item["score"]}
            for item in sorted(candidates, key=lambda x: x["score"], reverse=True)[:20]
        ],
        "safety": {"research_only": True, "production_ready": False, "production_checkpoint_modified": False, "production_signal_logic_modified": False, "approval_gate_modified": False, "broker_or_orders_touched": False, "automatic_order_execution_enabled": False, "live_trading_enabled": False, "btc_track_modified": False},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path, help="15-minute XAU/USD OHLC CSV")
    parser.add_argument("--output", type=Path, default=Path("xau-mtf-robustness-report.json"))
    parser.add_argument("--round-trip-cost-bps", type=float, default=5.0)
    args = parser.parse_args()
    report = evaluate(args.csv, args.round_trip_cost_bps)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_json_safe(report), indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "candidate_count": report["candidate_count"], "eligible_candidate_count": report["eligible_candidate_count"], "selected_candidate": report["selected_candidate"] is not None, "research_only": True}, indent=2))


if __name__ == "__main__":
    main()
