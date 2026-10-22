"""Regression tests for the live Kitty V3 candle feature transform."""
import math
import unittest

from kitty_features import FEATURE_NAMES, compute_kitty_features


def sample_candles(count=80, timestamps=False, interval_seconds=3600):
    candles = []
    price = 60_000.0
    start = 1_735_689_600
    for i in range(count):
        previous = price
        price *= 1.0 + (0.0007 if i % 3 else -0.0004)
        candle = {
            "open": previous,
            "high": max(previous, price) * 1.001,
            "low": min(previous, price) * 0.999,
            "close": price,
        }
        if timestamps:
            candle["timestamp"] = start + i * interval_seconds
        candles.append(candle)
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

    def test_inconsistent_ohlc_bounds_fail_closed(self):
        candles = sample_candles()
        candles[-1]["high"] = candles[-1]["low"] * 0.5
        with self.assertRaisesRegex(ValueError, "inconsistent OHLC"):
            compute_kitty_features(candles)

    def test_hourly_timestamped_candles_are_accepted(self):
        features = compute_kitty_features(sample_candles(timestamps=True))
        self.assertEqual(list(features), list(FEATURE_NAMES))

    def test_non_hourly_candles_are_rejected_instead_of_mislabelled(self):
        with self.assertRaisesRegex(ValueError, "requires consecutive hourly candles"):
            compute_kitty_features(sample_candles(timestamps=True, interval_seconds=900))

    def test_missing_or_duplicate_timestamp_intervals_fail_closed(self):
        candles = sample_candles(timestamps=True)
        candles[40]["timestamp"] = candles[39]["timestamp"]
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            compute_kitty_features(candles)


if __name__ == "__main__":
    unittest.main()
