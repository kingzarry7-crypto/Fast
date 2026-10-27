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


def evaluate_csv(path: str | Path, symbol: str, cost_bps_per_side: float) -> dict:
    frame = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{symbol}: CSV missing required columns: {sorted(missing)}")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    if len(frame) < 1500:
        raise ValueError(f"{symbol}: need at least 1200 5-minute candles for timeframe warm-up and evaluation; got {len(frame)}")
    # Keep only contiguous five-minute candles so indicators cannot bridge data outages.
    gaps = frame.index.to_series().diff().dropna()
    if (gaps <= pd.Timedelta(0)).any():
        raise ValueError(f"{symbol}: candle timestamps must be strictly increasing")
    # Gaps are permitted for exchange closures, but suppress signals for 26
    # completed 4H bars after each gap so the slow trend EMA is not trusted on
    # a discontinuous history. This is intentionally conservative.
    split = int(len(frame) * 0.8)
    # Generate indicators over prior history for realistic warm-up, but evaluate
    # only signals observed in the final holdout. Entries still occur next open.
    signals = build_mtf_signals(frame)
    gap_rows = frame.index.to_series().diff().gt(pd.Timedelta(minutes=5))
    if gap_rows.any():
        gap_positions = [i for i, value in enumerate(gap_rows.to_numpy()) if value]
        signal_values = signals.to_numpy(copy=True)
        for gap_i in gap_positions:
            signal_values[gap_i:min(len(signal_values), gap_i + 26 * 48)] = 0
        signals = pd.Series(signal_values, index=frame.index, name="signal")
    holdout = frame.iloc[split:].copy()
    holdout_signals = signals.reindex(holdout.index).copy()
    if len(holdout_signals):
        # The first holdout row's signal was formed using history before split;
        # this is causal, but no trade may be open from the validation segment.
        pass
    result = backtest_ohlc(
        holdout,
        holdout_signals,
        BacktestConfig(
            stop_pct=0.005 if symbol == "BTC" else 0.003,
            target_pct=0.010 if symbol == "BTC" else 0.006,
            max_hold_bars=24,
            spread_bps_per_side=cost_bps_per_side,
            commission_bps_per_side=0.0,
            slippage_bps_per_side=2.0,
        ),
    )
    return {
        "symbol": symbol,
        "data_file": str(path),
        "source_rows": len(frame),
        "source_start": frame.index[0].isoformat(),
        "source_end": frame.index[-1].isoformat(),
        "holdout_start": holdout.index[0].isoformat(),
        "holdout_rows": len(holdout),
        "holdout_fraction": 0.2,
        "parameter_tuning_on_holdout": False,
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
    args.output.write_text(json.dumps(_json_safe(report), indent=2, allow_nan=False) + "\\n", encoding="utf-8")
    print(json.dumps({**report, "trade_log": f"{len(report['trade_log'])} trades saved in output"}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
