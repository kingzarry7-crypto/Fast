"""Run Kitty's conservative 4-timeframe OHLC research backtest on 5-minute CSV data.

CSV contract: timestamp, open, high, low, close; timestamp is the candle CLOSE
time in UTC. The final 20% is a chronological holdout and is never used to tune
parameters. This command does not fetch data, place orders, or enable signals.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from kitty_realistic_backtest import BacktestConfig, backtest_ohlc, build_mtf_signals


def _filter_market_session(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Remove XAUUSD candles outside a conservative weekday trading session.

    Timestamps are candle close times in UTC. Gold/CFD broker availability is
    not continuous over weekends; do not trust vendor quotes while closed.
    """
    if symbol != "XAUUSD":
        return frame
    weekday = frame.index.dayofweek
    minute_of_day = frame.index.hour * 60 + frame.index.minute
    valid = weekday < 5
    valid &= ~((weekday == 4) & (minute_of_day >= 21 * 60))
    valid |= (weekday == 6) & (minute_of_day >= 22 * 60)
    return frame.loc[valid].copy()


def _candidate_stability_key(candidate: dict) -> tuple[float, float, float, float]:
    """Rank eligible candidates by validation-fold robustness, not peak return.

    All inputs are validation-only. The worst fold is prioritized first, then
    the median fold, profit factor, and aggregate validation return as tie-breaks.
    """
    fold_returns = [
        float(item["compounded_net_return"])
        for item in candidate["fold_results"]
    ]
    worst_fold = min(fold_returns, default=float("-inf"))
    ordered = sorted(fold_returns)
    if not ordered:
        median_fold = float("-inf")
    elif len(ordered) % 2:
        median_fold = ordered[len(ordered) // 2]
    else:
        middle = len(ordered) // 2
        median_fold = (ordered[middle - 1] + ordered[middle]) / 2
    profit_factor = candidate["validation"].get("profit_factor")
    if profit_factor is None:
        profit_factor = 0.0
    return (
        worst_fold,
        median_fold,
        float(profit_factor),
        float(candidate["validation"]["compounded_net_return"]),
    )


def evaluate_csv(path: str | Path, symbol: str, cost_bps_per_side: float) -> dict:
    frame = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{symbol}: CSV missing required columns: {sorted(missing)}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    raw_rows = len(frame)
    frame = _filter_market_session(frame, symbol)
    if len(frame) < 1500:
        raise ValueError(f"{symbol}: need at least 1200 5-minute candles for timeframe warm-up and evaluation; got {len(frame)}")
    # Keep only contiguous five-minute candles so indicators cannot bridge data outages.
    gaps = frame.index.to_series().diff().dropna()
    if (gaps <= pd.Timedelta(0)).any():
        raise ValueError(f"{symbol}: candle timestamps must be strictly increasing")
    # Session/weekend gaps are real market closures, not missing candles to
    # synthesize. Resampling drops empty intervals; retain prior completed
    # higher-timeframe context rather than suppressing ~5 days after every gap.
    train_end = int(len(frame) * 0.6)
    validation_end = int(len(frame) * 0.8)
    # Build causal indicators across the history, but report validation and the
    # final chronological holdout separately. Never tune on the final 20%.
    validation = frame.iloc[train_end:validation_end].copy()
    holdout = frame.iloc[validation_end:].copy()
    # Select risk parameters on validation only. The final holdout is evaluated
    # once with the selected parameters and never used to choose them.
    stop_grid, target_grid, hold_grid = (
        ([0.003, 0.005, 0.007], [0.006, 0.010, 0.014], [12, 24, 36])
        if symbol == "BTC"
        else ([0.002, 0.003, 0.004], [0.004, 0.006, 0.008], [12, 24, 36])
    )
    candidates = []
    base_strategy_signals = {
        strategy: build_mtf_signals(frame, strategy=strategy)
        for strategy in ("mtf_cross", "mtf_trend", "mtf_momentum")
    }
    strategy_signals = {}
    for strategy, base_signal in base_strategy_signals.items():
        strategy_signals[(strategy, "both")] = base_signal
        strategy_signals[(strategy, "long_only")] = base_signal.clip(lower=0)
        strategy_signals[(strategy, "short_only")] = base_signal.clip(upper=0)
    for (strategy, direction_mode), strategy_signal in strategy_signals.items():
      for stop_pct in stop_grid:
        for target_pct in target_grid:
            for max_hold_bars in hold_grid:
                candidate_config = BacktestConfig(
                    stop_pct=stop_pct,
                    target_pct=target_pct,
                    max_hold_bars=max_hold_bars,
                    spread_bps_per_side=cost_bps_per_side,
                    commission_bps_per_side=0.0,
                    slippage_bps_per_side=2.0,
                )
                validation_result = backtest_ohlc(
                    validation, strategy_signal.reindex(validation.index), candidate_config
                )
                # Avoid selecting a one-window fluke: candidate must show a
                # positive after-cost edge in at least two of three contiguous
                # validation folds. The final 20% holdout remains untouched.
                fold_results = []
                for fold_number in range(3):
                    fold_start = len(validation) * fold_number // 3
                    fold_end = len(validation) * (fold_number + 1) // 3
                    fold = validation.iloc[fold_start:fold_end]
                    fold_signals = strategy_signal.reindex(fold.index)
                    fold_result = backtest_ohlc(fold, fold_signals, candidate_config)
                    fold_results.append({
                        "trade_count": fold_result["trade_count"],
                        "compounded_net_return": fold_result["compounded_net_return"],
                        "profit_factor": fold_result["profit_factor"],
                        "max_drawdown": fold_result["max_drawdown"],
                    })
                positive_folds = sum(
                    item["trade_count"] >= 8
                    and item["compounded_net_return"] > 0
                    and item["profit_factor"] is not None
                    and item["profit_factor"] >= 1.0
                    for item in fold_results
                )
                eligible = (
                    validation_result["trade_count"] >= 20
                    and validation_result["compounded_net_return"] > 0
                    and validation_result["profit_factor"] is not None
                    and validation_result["profit_factor"] >= 1.10
                    and validation_result["max_drawdown"] >= -0.05
                    and positive_folds >= 2
                )
                candidates.append({
                    "strategy": strategy,
                    "direction_mode": direction_mode,
                    "signals": strategy_signal,
                    "config": candidate_config,
                    "validation": validation_result,
                    "positive_validation_folds": positive_folds,
                    "fold_results": fold_results,
                    "eligible": eligible,
                })
    eligible_candidates = [item for item in candidates if item["eligible"]]
    # Choose the most stable eligible candidate, not the one with the
    # highest aggregate validation return (which can reward one lucky fold).
    selected = max(
        eligible_candidates,
        key=_candidate_stability_key,
        default=None,
    )
    diagnostic_config = BacktestConfig(
        stop_pct=0.005 if symbol == "BTC" else 0.003,
        target_pct=0.010 if symbol == "BTC" else 0.006,
        max_hold_bars=24,
        spread_bps_per_side=cost_bps_per_side,
        commission_bps_per_side=0.0,
        slippage_bps_per_side=2.0,
    )
    chosen_config = selected["config"] if selected else diagnostic_config
    chosen_strategy = selected["strategy"] if selected else "mtf_cross"
    chosen_direction_mode = selected["direction_mode"] if selected else "both"
    chosen_signals = selected["signals"] if selected else strategy_signals[("mtf_cross", "both")]
    # Always compute the fallback for diagnostics, but never report it as the
    # selected holdout result when no candidate passes the validation edge gate.
    diagnostic_validation = backtest_ohlc(
        validation, chosen_signals.reindex(validation.index), chosen_config
    )
    diagnostic_holdout = backtest_ohlc(
        holdout, chosen_signals.reindex(holdout.index), chosen_config
    )
    if selected is not None:
        validation_full = diagnostic_validation
        result = diagnostic_holdout
    else:
        no_trade_validation = pd.Series(0, index=validation.index, dtype=int)
        no_trade_holdout = pd.Series(0, index=holdout.index, dtype=int)
        validation_full = backtest_ohlc(validation, no_trade_validation, chosen_config)
        result = backtest_ohlc(holdout, no_trade_holdout, chosen_config)
    candidate_selection = {
        "selected": selected is not None,
        "reason": "validation_edge_gate_passed" if selected else "no_validation_candidate_passed_edge_gate",
        "candidates_evaluated": len(candidates),
        "strategies_evaluated": ["mtf_cross", "mtf_trend", "mtf_momentum"],
        "direction_modes_evaluated": ["both", "long_only", "short_only"],
        "eligible_candidates": len(eligible_candidates),
        "minimum_validation_trades": 20,
        "validation_folds": 3,
        "minimum_trades_per_validation_fold": 8,
        "minimum_positive_validation_folds": 2,
        "minimum_validation_profit_factor": 1.10,
        "minimum_validation_compounded_return": 0.0,
        "maximum_validation_drawdown": -0.05,
        "parameter_tuning_on_holdout": False,
        "selected_config": ({
            "strategy": chosen_strategy,
            "direction_mode": chosen_direction_mode,
            "stop_pct": chosen_config.stop_pct,
            "target_pct": chosen_config.target_pct,
            "max_hold_bars": chosen_config.max_hold_bars,
        } if selected else None),
    }
    return {
        "symbol": symbol,
        "data_file": str(path),
        "raw_rows": raw_rows,
        "source_rows": len(frame),
        "source_start": frame.index[0].isoformat(),
        "source_end": frame.index[-1].isoformat(),
        "training_context_rows": train_end,
        "validation_start": validation.index[0].isoformat(),
        "validation_rows": len(validation),
        "validation_result": {key: value for key, value in validation_full.items() if key != "trades"},
        "diagnostic_validation_result": (
            {key: value for key, value in diagnostic_validation.items() if key != "trades"}
            if selected is None else None
        ),
        "candidate_selection": candidate_selection,
        "holdout_start": holdout.index[0].isoformat(),
        "holdout_rows": len(holdout),
        "holdout_fraction": 0.2,
        "parameter_tuning_on_holdout": False,
        "cost_assumptions": {
            "spread_bps_per_side": cost_bps_per_side,
            "commission_bps_per_side": 0.0,
            "slippage_bps_per_side": 2.0,
            "spread_is_measured_JustMarkets_spread": False,
        },
        "result": {key: value for key, value in result.items() if key != "trades"},
        "diagnostic_result": (
            {key: value for key, value in diagnostic_holdout.items() if key != "trades"}
            if selected is None else None
        ),
        "trade_log": result["trades"],
        "diagnostic_trade_log": diagnostic_holdout["trades"] if selected is None else [],
        "research_only": True,
        "holdout_edge_gate_passed": bool(
            selected is not None
            and result["trade_count"] >= 20
            and result["compounded_net_return"] > 0
            and result["profit_factor"] is not None
            and result["profit_factor"] >= 1.10
            and result["max_drawdown"] >= -0.05
        ),
        "production_ready": False,
        "automatic_order_execution_enabled": False,
    }


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not pd.notna(value):
        return None
    if isinstance(value, float) and value == float("inf"):
        return "Infinity"
    if isinstance(value, float) and value == float("-inf"):
        return "-Infinity"
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", choices=("BTC", "XAUUSD"), required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--spread-bps-per-side", type=float, required=True,
                        help="Measured or explicitly assumed spread per side; 2 bps slippage per side is added separately")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_csv(args.csv, args.symbol, args.spread_bps_per_side)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_json_safe(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({**report, "trade_log": f"{len(report['trade_log'])} trades saved in output"}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
