import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import prepare_kitty_fx_market_dataset as builder


class KittyFxDatasetTests(unittest.TestCase):
    def test_falls_back_without_api_key_and_rejects_unsupported_symbol(self):
        expected = pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-01", tz="UTC")]})
        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": "", "TWELVE_DATA_API_KEY": ""}):
            with patch.object(builder, "_fetch_yahoo_hourly_candles", return_value=expected) as fallback:
                self.assertIs(builder.fetch_hourly_candles("XAUUSD"), expected)
                fallback.assert_called_once_with("XAUUSD", 5000)
        with self.assertRaises(ValueError):
            builder.fetch_hourly_candles("AUDCAD", api_key="test-key")

    @patch("prepare_kitty_fx_market_dataset.requests.get")
    def test_normalizes_twelve_data_ohlc_and_missing_volume(self, mock_get):
        values = []
        for i in range(500):
            stamp = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i)
            price = 100 + i * 0.1
            values.append({"datetime": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                           "open": str(price), "high": str(price + 1),
                           "low": str(price - 1), "close": str(price + 0.2)})
        response = Mock()
        response.json.return_value = {"values": values}
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        frame = builder.fetch_hourly_candles("EURUSD", api_key="test-key")
        self.assertEqual(len(frame), 500)
        self.assertEqual(list(frame.columns), ["timestamp", "open", "high", "low", "close", "volume"])
        self.assertTrue((frame["volume"] == 0).all())
        self.assertTrue(frame["timestamp"].is_monotonic_increasing)


    @patch("prepare_kitty_fx_market_dataset.requests.get")
    def test_uses_free_yahoo_hourly_data_when_twelve_data_key_is_missing(self, mock_get):
        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": "", "TWELVE_DATA_API_KEY": ""}):
            timestamps = [1704067200 + i * 3600 for i in range(500)]
            quotes = {
                "open": [100.0 + i * 0.1 for i in range(500)],
                "high": [101.0 + i * 0.1 for i in range(500)],
                "low": [99.0 + i * 0.1 for i in range(500)],
                "close": [100.2 + i * 0.1 for i in range(500)],
                "volume": [0 for _ in range(500)],
            }
            response = Mock()
            response.json.return_value = {"chart": {"result": [{
                "timestamp": timestamps, "indicators": {"quote": [quotes]}
            }], "error": None}}
            response.raise_for_status.return_value = None
            mock_get.return_value = response

            frame = builder.fetch_hourly_candles("EURUSD", outputsize=500)

        self.assertEqual(len(frame), 500)
        self.assertEqual(list(frame.columns), ["timestamp", "open", "high", "low", "close", "volume"])
        self.assertTrue(frame["timestamp"].is_monotonic_increasing)
        self.assertAlmostEqual(frame.iloc[0]["close"], 100.2)
        self.assertIn("query1.finance.yahoo.com", mock_get.call_args.args[0])

if __name__ == "__main__":
    unittest.main()
