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
    signals = build_mtf_signals(frame)
    validation = frame.iloc[train_end:validation_end].copy()
    holdout = frame.iloc[validation_end:].copy()
    config = BacktestConfig(
        stop_pct=0.005 if symbol == "BTC" else 0.003,
        target_pct=0.010 if symbol == "BTC" else 0.006,
        max_hold_bars=24,
        spread_bps_per_side=cost_bps_per_side,
        commission_bps_per_side=0.0,
        slippage_bps_per_side=2.0,
    )
    validation_full = backtest_ohlc(validation, signals.reindex(validation.index), config)
    result = backtest_ohlc(holdout, signals.reindex(holdout.index), config)
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
        "trade_log": result["trades"],
        "research_only": True,
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
