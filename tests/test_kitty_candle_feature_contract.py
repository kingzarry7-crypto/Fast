"""Regression tests for the live-candle Kitty V3 feature contract."""
import math
import unittest
from datetime import datetime, timedelta, timezone

import kitty_v3_retrained as model
from kitty_api import _kitty_features, _validate_candles


class KittyCandleFeatureContractTests(unittest.TestCase):
    def test_live_candle_features_match_model_order_and_are_finite(self):
        candles = []
        for index in range(80):
            close = 60000.0 + index * 17.0 + (index % 5) * 3.0
            candles.append({
                "open": close - 4.0,
                "high": close + 12.0,
                "low": close - 11.0,
                "close": close,
            })

        features = _kitty_features(candles)

        self.assertEqual(list(features), model.EXPECTED_FEATURES)
        self.assertEqual(len(features), 18)
        self.assertTrue(all(math.isfinite(value) for value in features.values()))

    def test_live_candle_feature_builder_rejects_insufficient_history(self):
        candles = [
            {"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0}
            for _ in range(54)
        ]
        with self.assertRaisesRegex(ValueError, "At least 55 candles"):
            _kitty_features(candles)


    def test_reversed_provider_candles_are_sorted_before_freshness_validation(self):
        newest = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        candles = []
        for index in range(60):
            stamp = newest - timedelta(hours=index)
            close = 60000.0 + index
            candles.append({
                "datetime": stamp.isoformat(),
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 100,
            })
        # Providers may return newest-first; the contract must normalize to oldest-first.
        latest = _validate_candles(candles, "1h", "BTC/USDT")
        self.assertEqual(candles[0]["datetime"], (newest - timedelta(hours=59)).isoformat())
        self.assertEqual(candles[-1]["datetime"], newest.isoformat())
        self.assertEqual(latest, newest.isoformat())

    def test_runtime_candle_validator_rejects_impossible_ohlc_bounds(self):
        newest = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        candles = []
        for index in range(60):
            stamp = newest - timedelta(hours=59 - index)
            close = 60000.0 + index * 2
            candles.append({
                "datetime": stamp.isoformat(),
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 100,
            })
        candles[-1]["high"] = candles[-1]["close"] - 1
        with self.assertRaisesRegex(ValueError, "invalid OHLC bounds"):
            _validate_candles(candles, "1h", "BTC/USDT")


if __name__ == "__main__":
    unittest.main()
