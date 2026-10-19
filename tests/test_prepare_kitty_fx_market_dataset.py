import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import prepare_kitty_fx_market_dataset as builder


class KittyFxDatasetTests(unittest.TestCase):
    def test_rejects_missing_api_key_and_unsupported_symbol(self):
        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "TWELVEDATA_API_KEY"):
                builder.fetch_hourly_candles("XAUUSD")
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

if __name__ == "__main__":
    unittest.main()
