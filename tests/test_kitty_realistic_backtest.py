import unittest

import numpy as np
import pandas as pd

from kitty_realistic_backtest import BacktestConfig, backtest_ohlc, build_mtf_signals
from run_kitty_realistic_backtest import evaluate_csv


class KittyRealisticBacktestTests(unittest.TestCase):
    def candles(self, rows):
        idx = pd.date_range("2026-01-01", periods=len(rows), freq="5min", tz="UTC")
        return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"])

    def test_signal_enters_next_open_and_stop_wins_when_stop_and_target_both_hit(self):
        frame = self.candles([
            (100, 101, 99, 100),
            (100, 112, 89, 101),  # next-open entry; both brackets hit => stop-first
            (101, 102, 100, 101),
        ])
        signals = pd.Series([1, 0, 0], index=frame.index)
        result = backtest_ohlc(frame, signals, BacktestConfig(
            stop_pct=0.05, target_pct=0.10, max_hold_bars=2,
            spread_bps_per_side=0, commission_bps_per_side=0, slippage_bps_per_side=0,
        ))
        self.assertEqual(result["trade_count"], 1)
        self.assertEqual(result["trades"][0]["entry_price"], 100)
        self.assertEqual(result["trades"][0]["exit_reason"], "stop")
        self.assertAlmostEqual(result["trades"][0]["net_return"], -0.05)

    def test_gap_through_stop_fills_at_worse_open(self):
        frame = self.candles([
            (100, 101, 99, 100),
            (100, 101, 99, 100),  # entry at 100; stop is 95
            (90, 92, 88, 91),  # gap through stop fills at open 90
        ])
        result = backtest_ohlc(frame, pd.Series([1, 0, 0], index=frame.index),
            BacktestConfig(stop_pct=0.05, target_pct=0.10, max_hold_bars=2,
                           spread_bps_per_side=0, commission_bps_per_side=0, slippage_bps_per_side=0))
        self.assertEqual(result["trades"][0]["entry_price"], 100)
        self.assertEqual(result["trades"][0]["exit_price"], 90)
        self.assertEqual(result["trades"][0]["exit_reason"], "stop")

    def test_costs_reduce_returns_and_no_trades_are_not_called_profitable(self):
        frame = self.candles([(100, 101, 99, 100), (100, 102, 99, 101), (101, 103, 100, 102)])
        signals = pd.Series([1, 0, 0], index=frame.index)
        free = backtest_ohlc(frame, signals, BacktestConfig(stop_pct=.05, target_pct=.10,
            max_hold_bars=2, spread_bps_per_side=0, commission_bps_per_side=0, slippage_bps_per_side=0))
        costly = backtest_ohlc(frame, signals, BacktestConfig(stop_pct=.05, target_pct=.10,
            max_hold_bars=2, spread_bps_per_side=2, commission_bps_per_side=1, slippage_bps_per_side=2))
        self.assertGreater(free["compounded_net_return"], costly["compounded_net_return"])
        no_trade = backtest_ohlc(frame, pd.Series([0, 0, 0], index=frame.index))
        self.assertEqual(no_trade["trade_count"], 0)
        self.assertIsNone(no_trade["profit_factor"])

    def test_csv_runner_uses_chronological_holdout_and_keeps_orders_disabled(self):
        idx = pd.date_range("2026-01-01", periods=1200, freq="5min", tz="UTC")
        close = 100 + np.arange(len(idx)) * 0.005 + np.sin(np.arange(len(idx)) / 8) * 0.1
        frame = pd.DataFrame({
            "timestamp": idx,
            "open": close,
            "high": close + .05,
            "low": close - .05,
            "close": close,
        })
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            frame.to_csv(path, index=False)
            report = evaluate_csv(path, "BTC", 2.0)
        self.assertEqual(report["holdout_rows"], 240)
        self.assertFalse(report["parameter_tuning_on_holdout"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["automatic_order_execution_enabled"])
        self.assertIn("compounded_net_return", report["result"])

    def test_mtf_signals_are_valid_and_warmup_is_no_trade(self):
        idx = pd.date_range("2025-01-01", periods=1200, freq="5min", tz="UTC")
        close = 100 + np.arange(len(idx)) * 0.01 + np.sin(np.arange(len(idx)) / 8) * 0.1
        frame = pd.DataFrame({"open": close, "high": close + .05, "low": close - .05, "close": close}, index=idx)
        signals = build_mtf_signals(frame)
        self.assertEqual(len(signals), len(frame))
        self.assertTrue(signals.isin([-1, 0, 1]).all())
        self.assertTrue((signals.iloc[:500] == 0).all())


if __name__ == "__main__":
    unittest.main()
