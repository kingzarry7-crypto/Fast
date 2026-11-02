"""Contract tests for the isolated XAU/USD MTF research experiment."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research-data" / "scripts"))
from xau_mtf_robustness import Candidate, backtest, build_features, make_signals


def synthetic_ohlc(periods=1600):
    index = pd.date_range("2025-01-01 00:15:00", periods=periods, freq="15min", tz="UTC")
    close = 4000 + np.arange(periods) * 0.03 + np.sin(np.arange(periods) / 7) * 1.5
    return pd.DataFrame({
        "open": close - 0.05, "high": close + 0.5,
        "low": close - 0.5, "close": close,
    }, index=index)


class GoldMtfResearchTests(unittest.TestCase):
    def test_signal_values_are_only_long_short_or_wait_and_index_aligned(self):
        frame = synthetic_ohlc()
        features = build_features(frame, 960)
        candidate = Candidate("both", 0.0, 45, 68, 0.0035, 0.007, 8)
        signals = make_signals(features, candidate)
        self.assertTrue(signals.isin([-1, 0, 1]).all())
        self.assertTrue(signals.index.equals(frame.index))

    def test_backtest_applies_higher_costs_and_enters_after_signal_close(self):
        frame = synthetic_ohlc(100)
        candidate = Candidate("long_only", 0, 0, 100, 0.05, 0.50, 4)
        signals = pd.Series(1, index=frame.index)
        base = backtest(frame, signals, candidate, 5.0)
        stress = backtest(frame, signals, candidate, 10.0)
        self.assertEqual(base["trades"][0]["signal_time"], frame.index[0].isoformat())
        self.assertEqual(base["trades"][0]["entry_time"], frame.index[1].isoformat())
        self.assertGreater(base["trades"][0]["net_return"], stress["trades"][0]["net_return"])

    def test_no_trade_is_counted_without_full_holding_horizon(self):
        frame = synthetic_ohlc(5)
        candidate = Candidate("long_only", 0, 0, 100, 0.05, 0.50, 8)
        result = backtest(frame, pd.Series(1, index=frame.index), candidate, 5.0)
        self.assertEqual(result["trade_count"], 0)

    def test_baseline_tracks_are_distinct_from_mtf_candidate(self):
        from xau_mtf_robustness import build_baseline_signals
        frame = synthetic_ohlc()
        features = build_features(frame, 960)
        momentum = build_baseline_signals(features, "momentum")
        trend = build_baseline_signals(features, "trend")
        self.assertEqual(len(momentum), len(frame))
        self.assertEqual(len(trend), len(frame))
        self.assertTrue(momentum.isin([-1, 0, 1]).all())
        self.assertTrue(trend.isin([-1, 0, 1]).all())

    def test_invalid_cost_is_rejected(self):
        frame = synthetic_ohlc()
        candidate = Candidate("both", 0, 45, 68, 0.003, 0.006, 4)
        with self.assertRaises(ValueError):
            backtest(frame, pd.Series(0, index=frame.index), candidate, -1.0)


if __name__ == "__main__":
    unittest.main()
