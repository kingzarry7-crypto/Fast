"""Regression tests for the live Kitty V3 candle feature transform."""
import math
import unittest

from kitty_features import FEATURE_NAMES, compute_kitty_features


def sample_candles(count=80):
    candles = []
    price = 60_000.0
    for i in range(count):
        previous = price
        price *= 1.0 + (0.0007 if i % 3 else -0.0004)
        candles.append({
            "open": previous,
            "high": max(previous, price) * 1.001,
            "low": min(previous, price) * 0.999,
            "close": price,
        })
    return candles


class KittyFeatureTests(unittest.TestCase):
    def test_feature_names_and_order_match_retrained_model_contract(self):
        expected = [
            "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
            "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
            "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
            "macd_hist_norm", "volatility_6h", "volatility_24h",
            "range_pct", "body_pct", "close_position",
        ]
        self.assertEqual(list(FEATURE_NAMES), expected)
        self.assertEqual(list(compute_kitty_features(sample_candles())), expected)

    def test_features_are_finite_for_valid_candles(self):
        features = compute_kitty_features(sample_candles())
        self.assertTrue(all(math.isfinite(value) for value in features.values()))
        self.assertGreaterEqual(features["close_position"], 0.0)
        self.assertLessEqual(features["close_position"], 1.0)
        self.assertGreaterEqual(features["rsi_14"], 0.0)
        self.assertLessEqual(features["rsi_14"], 100.0)

    def test_insufficient_candles_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "At least 55 candles"):
            compute_kitty_features(sample_candles(54))

    def test_invalid_ohlc_prices_fail_closed(self):
        candles = sample_candles()
        candles[-1]["close"] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid OHLC"):
            compute_kitty_features(candles)

    def test_invalid_high_low_bounds_fail_closed(self):
        candles = sample_candles()
        candles[-1]["high"] = min(candles[-1]["open"], candles[-1]["close"]) - 1.0
        with self.assertRaisesRegex(ValueError, "invalid OHLC candle range"):
            compute_kitty_features(candles)


if __name__ == "__main__":
    unittest.main()
