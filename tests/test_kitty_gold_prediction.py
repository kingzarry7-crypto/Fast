"""Regression tests for gold/crypto candle timestamps used by Kitty signals."""
import unittest
from datetime import datetime, timezone

from kitty_features import normalize_candle_timestamp


class KittyGoldPredictionTests(unittest.TestCase):
    def test_unix_seconds_string_normalizes_to_utc_iso8601(self):
        value = str(datetime.now(timezone.utc).timestamp())
        result = normalize_candle_timestamp(value)
        self.assertTrue(result.endswith("+00:00"))
        self.assertIn("T", result)

    def test_unix_milliseconds_string_normalizes_to_utc_iso8601(self):
        value = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        result = normalize_candle_timestamp(value)
        self.assertTrue(result.endswith("+00:00"))
        self.assertIn("T", result)

    def test_iso_timestamp_normalizes_to_utc(self):
        result = normalize_candle_timestamp("2026-10-22T12:00:00Z")
        self.assertEqual(result, "2026-10-22T12:00:00+00:00")

    def test_invalid_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ISO-8601 or Unix"):
            normalize_candle_timestamp("not-a-time")


if __name__ == "__main__":
    unittest.main()
