import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from kitty_realistic_backtest import BacktestConfig, backtest_ohlc, build_mtf_signals, _completed_timeframe
from run_kitty_realistic_backtest import _candidate_stability_key, _json_safe, evaluate_csv


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
        idx = pd.date_range("2026-01-01", periods=1600, freq="5min", tz="UTC")
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
        self.assertEqual(report["holdout_rows"], 320)
        self.assertFalse(report["parameter_tuning_on_holdout"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["automatic_order_execution_enabled"])
        self.assertIn("compounded_net_return", report["result"])


    def test_normal_market_session_gaps_do_not_disable_signals_for_days(self):
        idx = list(pd.date_range("2026-01-01", periods=1600, freq="5min", tz="UTC"))
        idx[1400:] = list(pd.date_range(idx[1400] + pd.Timedelta(days=2), periods=200, freq="5min", tz="UTC"))
        close = np.full(len(idx), 100.0)
        frame = pd.DataFrame({
            "timestamp": idx, "open": close, "high": close + .01,
            "low": close - .01, "close": close,
        })
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gap.csv"
            frame.to_csv(path, index=False)
            forced_signals = pd.Series(1, index=pd.DatetimeIndex(idx))
            with patch("run_kitty_realistic_backtest.build_mtf_signals", return_value=forced_signals):
                report = evaluate_csv(path, "BTC", 2.0)
        effective_or_diagnostic = (
            report["result"] if report["candidate_selection"]["selected"]
            else report["diagnostic_result"]
        )
        self.assertGreater(effective_or_diagnostic["trade_count"], 0)


    def test_xauusd_filters_weekend_quotes_and_does_not_hold_through_closure(self):
        idx = pd.date_range("2026-10-19", periods=2400, freq="5min", tz="UTC")
        close = np.full(len(idx), 4100.0)
        frame = pd.DataFrame({
            "timestamp": idx, "open": close, "high": close + .05,
            "low": close - .05, "close": close,
        })
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.csv"
            frame.to_csv(path, index=False)
            forced_signals = pd.Series(1, index=idx)
            with patch("run_kitty_realistic_backtest.build_mtf_signals", return_value=forced_signals):
                report = evaluate_csv(path, "XAUUSD", 5.0)
        self.assertLess(report["source_rows"], report["raw_rows"])
        effective_or_diagnostic = (
            report["result"] if report["candidate_selection"]["selected"]
            else report["diagnostic_result"]
        )
        self.assertGreater(effective_or_diagnostic["trade_count"], 0)
        for trade in report["trade_log"]:
            signal_time = pd.Timestamp(trade["signal_time"])
            entry_time = pd.Timestamp(trade["entry_time"])
            exit_time = pd.Timestamp(trade["exit_time"])
            self.assertLess(signal_time.dayofweek, 5)
            self.assertEqual(entry_time - signal_time, pd.Timedelta(minutes=5))
            self.assertLessEqual(exit_time - entry_time, pd.Timedelta(hours=2))



    def test_candidate_selection_prioritizes_worst_validation_fold_over_peak_return(self):
        stable = {
            "fold_results": [
                {"compounded_net_return": 0.004},
                {"compounded_net_return": 0.006},
                {"compounded_net_return": 0.003},
            ],
            "validation": {"profit_factor": 1.25, "compounded_net_return": 0.018},
        }
        volatile = {
            "fold_results": [
                {"compounded_net_return": -0.025},
                {"compounded_net_return": 0.030},
                {"compounded_net_return": 0.040},
            ],
            "validation": {"profit_factor": 1.8, "compounded_net_return": 0.060},
        }
        self.assertGreater(_candidate_stability_key(stable), _candidate_stability_key(volatile))

    def test_runner_selects_parameters_only_on_validation_and_fails_closed_without_edge(self):
        idx = pd.date_range("2026-01-01", periods=1800, freq="5min", tz="UTC")
        close = 100 + np.sin(np.arange(len(idx)) / 5) * 0.1
        frame = pd.DataFrame({
            "timestamp": idx, "open": close, "high": close + .03,
            "low": close - .03, "close": close,
        })
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            frame.to_csv(path, index=False)
            forced = pd.Series(0, index=idx)
            with patch("run_kitty_realistic_backtest.build_mtf_signals", return_value=forced):
                report = evaluate_csv(path, "BTC", 2.0)
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["automatic_order_execution_enabled"])
        self.assertFalse(report["candidate_selection"]["selected"])
        self.assertEqual(report["candidate_selection"]["reason"], "no_validation_candidate_passed_edge_gate")
        self.assertEqual(report["candidate_selection"]["candidates_evaluated"], 324)
        self.assertEqual(report["candidate_selection"]["validation_folds"], 3)
        self.assertEqual(report["candidate_selection"]["minimum_positive_validation_folds"], 3)
        self.assertTrue(report["candidate_selection"]["cost_stress_test"]["enabled"])
        self.assertEqual(report["candidate_selection"]["cost_stress_test"]["spread_multiplier"], 1.5)
        self.assertEqual(report["candidate_selection"]["cost_stress_test"]["slippage_bps_per_side"], 3.0)
        self.assertTrue(report["candidate_selection"]["cost_stress_test"]["stress_gate_required_for_selection"])
        self.assertIsNone(report["candidate_selection"]["selected_candidate_validation_folds"])
        self.assertIsNone(report["candidate_selection"]["selected_candidate_stress_validation_folds"])
        self.assertEqual(report["candidate_selection"]["strategies_evaluated"], ["mtf_cross", "mtf_trend", "mtf_momentum", "mtf_pullback"])
        self.assertEqual(report["candidate_selection"]["direction_modes_evaluated"], ["both", "long_only", "short_only"])
        self.assertFalse(report["holdout_edge_gate_passed"])
        self.assertTrue(report["candidate_selection"]["parameter_tuning_on_holdout"] is False)
        self.assertEqual(report["result"]["trade_count"], 0)

    def test_mtf_signals_are_valid_and_warmup_is_no_trade(self):
        idx = pd.date_range("2025-01-01", periods=1200, freq="5min", tz="UTC")
        close = 100 + np.arange(len(idx)) * 0.01 + np.sin(np.arange(len(idx)) / 8) * 0.1
        frame = pd.DataFrame({"open": close, "high": close + .05, "low": close - .05, "close": close}, index=idx)
        signals = build_mtf_signals(frame)
        self.assertEqual(len(signals), len(frame))
        self.assertTrue(signals.isin([-1, 0, 1]).all())
        self.assertTrue((signals.iloc[:500] == 0).all())
        for strategy in ("mtf_cross", "mtf_trend", "mtf_momentum"):
            candidate = build_mtf_signals(frame, strategy=strategy)
            self.assertEqual(len(candidate), len(frame))
            self.assertTrue(candidate.isin([-1, 0, 1]).all())


    def test_unvalidated_fallback_is_diagnostic_only_and_never_reported_as_selected_result(self):
        idx = pd.date_range("2026-01-01", periods=1800, freq="5min", tz="UTC")
        close = 100 + np.sin(np.arange(len(idx)) / 5) * 0.1
        frame = pd.DataFrame({
            "timestamp": idx,
            "open": close,
            "high": close + .03,
            "low": close - .03,
            "close": close,
        })
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            frame.to_csv(path, index=False)
            forced = pd.Series(1, index=idx)
            with patch("run_kitty_realistic_backtest.build_mtf_signals", return_value=forced):
                report = evaluate_csv(path, "BTC", 2.0)
        self.assertFalse(report["candidate_selection"]["selected"])
        self.assertEqual(report["result"]["trade_count"], 0)
        self.assertIsNone(report["result"]["profit_factor"])
        self.assertIn("diagnostic_result", report)
        self.assertGreater(report["diagnostic_result"]["trade_count"], 0)
        self.assertFalse(report["holdout_edge_gate_passed"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["automatic_order_execution_enabled"])


    def test_higher_timeframe_context_rejects_partial_bars_after_data_gaps(self):
        idx = pd.date_range("2026-01-01", periods=24 * 12, freq="5min", tz="UTC")
        # Simulate a one-hour data outage. A partially populated 1h candle
        # must not be treated as a completed higher-timeframe candle.
        kept = idx.delete(np.arange(12 * 12 + 1, 12 * 12 + 12))
        close = 100 + np.arange(len(kept)) * 0.01
        frame = pd.DataFrame({
            "open": close, "high": close + .02, "low": close - .02, "close": close
        }, index=kept)
        context = _completed_timeframe(frame, "1h", 2, 3, "h1")
        # Every emitted context row must be backed by all twelve 5-minute bars.
        expected = []
        for label in pd.date_range(kept[0].ceil("1h"), kept[-1].floor("1h"), freq="1h", tz="UTC"):
            count = int(((kept > label - pd.Timedelta(hours=1)) & (kept <= label)).sum())
            if count == 12:
                expected.append(label)
        # The slow EMA requires three complete hourly candles to warm up.
        self.assertEqual(list(context.index), expected[2:])


    def test_pullback_strategy_is_supported_and_emits_only_valid_signal_values(self):
        idx = pd.date_range("2026-01-01", periods=1200, freq="5min", tz="UTC")
        close = 100 + np.arange(len(idx)) * 0.002 + np.sin(np.arange(len(idx)) / 9) * 0.08
        frame = pd.DataFrame({
            "open": close, "high": close + .03, "low": close - .03, "close": close
        }, index=idx)
        signals = build_mtf_signals(frame, strategy="mtf_pullback")
        self.assertEqual(len(signals), len(frame))
        self.assertTrue(signals.isin([-1, 0, 1]).all())


    def test_json_safe_converts_infinite_and_nan_metrics_for_console_output(self):
        report = {
            "profit_factor": float("inf"),
            "nan_metric": float("nan"),
            "nested": [{"ratio": float("-inf")}],
        }
        safe = _json_safe(report)
        self.assertEqual(safe["profit_factor"], "Infinity")
        self.assertIsNone(safe["nan_metric"])
        self.assertEqual(safe["nested"][0]["ratio"], "-Infinity")
        # The same strict JSON mode used by the CLI must now serialize safely.
        import json
        json.dumps(safe, allow_nan=False)


    def test_short_timeframe_indicators_warm_up_again_after_data_gap(self):
        first = pd.date_range("2026-01-01", periods=1200, freq="5min", tz="UTC")
        second = pd.date_range(first[-1] + pd.Timedelta(days=2), periods=100, freq="5min", tz="UTC")
        idx = first.append(second)
        close = 100 + np.arange(len(idx)) * 0.01 + np.sin(np.arange(len(idx)) / 8) * 0.1
        frame = pd.DataFrame({
            "open": close, "high": close + .05, "low": close - .05, "close": close
        }, index=idx)
        signals = build_mtf_signals(frame, strategy="mtf_cross")
        # RSI/EMA state must warm up from the post-gap segment, not leak the
        # pre-gap state into its first bars.
        self.assertTrue((signals.loc[second[:13]] == 0).all())



    def test_entries_without_full_holding_horizon_are_excluded(self):
        frame = self.candles([
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
            (100, 101, 99, 100),
        ])
        signals = pd.Series([0, 0, 1, 0], index=frame.index)
        result = backtest_ohlc(frame, signals, BacktestConfig(
            stop_pct=.05, target_pct=.10, max_hold_bars=3,
            spread_bps_per_side=0, commission_bps_per_side=0, slippage_bps_per_side=0,
        ))
        self.assertEqual(result["trade_count"], 0)


if __name__ == "__main__":
    unittest.main()
