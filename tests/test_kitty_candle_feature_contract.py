"""Regression tests for the live-candle Kitty V3 feature contract."""
import math
import unittest

import kitty_v3_retrained as model
from kitty_api import _kitty_features


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


if __name__ == "__main__":
    unittest.main()
