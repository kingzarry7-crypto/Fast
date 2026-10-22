"""Regression coverage for Kitty market candle timestamps and gold signals."""
import unittest
from datetime import datetime, timezone

from kitty_api import _technical_signal, _validate_candles


def _candles(latest_timestamp):
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(60):
        close = 2400.0 + i * 0.25 + (i % 4) * 0.03
        rows.append({
            "datetime": now.isoformat() if i == 59 else (now.replace(minute=0, second=0, microsecond=0)).isoformat(),
            "open": close - 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
        })
    rows[-1]["datetime"] = latest_timestamp
    return rows


class KittyGoldPredictionTests(unittest.TestCase):
    def test_validator_accepts_unix_seconds_returned_as_numeric_string(self):
        now = datetime.now(timezone.utc).timestamp()
        rows = _candles(str(now))
        result = _validate_candles(rows, "1h", "XAU/USD")
        self.assertTrue(result.endswith("+00:00"))

    def test_validator_accepts_unix_milliseconds_returned_as_numeric_string(self):
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        rows = _candles(str(now_ms))
        result = _validate_candles(rows, "1h", "XAU/USD")
        self.assertTrue(result.endswith("+00:00"))

    def test_signal_normalizes_numeric_string_timestamp_to_iso8601(self):
        rows = _candles(str(int(datetime.now(timezone.utc).timestamp() * 1000)))
        result = _technical_signal(rows, "XAU/USD", "1h")
        self.assertIn("T", result["completed_candle_time"])
        self.assertTrue(result["completed_candle_time"].endswith("+00:00"))

    def test_gold_technical_prediction_is_explicitly_research_only(self):
        rows = _candles(datetime.now(timezone.utc).isoformat())
        # Signal calculation itself does not need the model checkpoint.
        result = _technical_signal(rows, "XAU/USD", "1h")
        self.assertEqual(result["symbol"], "XAU/USD")
        self.assertIn(result["signal"], {"BUY", "SELL", "NO TRADE"})
        self.assertEqual(result["signal_type"], "rule_based_technical_confluence")
        self.assertFalse(result["model_used"])
        self.assertTrue(result["research_only"])
        self.assertFalse(result["trading_enabled"])


if __name__ == "__main__":
    unittest.main()
