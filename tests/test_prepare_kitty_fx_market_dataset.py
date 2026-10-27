import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import prepare_kitty_fx_market_dataset as builder


class KittyFxDatasetTests(unittest.TestCase):
    def test_require_spot_rejects_gold_futures_fallback_without_api_key(self):
        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": "", "TWELVE_DATA_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "XAU/USD spot training requires"):
                builder.fetch_hourly_candles("XAUUSD", require_spot=True)

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
            stamp = pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=500 - i)
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
    def test_twelve_data_uses_utc_and_drops_incomplete_hour(self, mock_get):
        now_hour = pd.Timestamp.now(tz="UTC").floor("h")
        timestamps = [
            now_hour - pd.Timedelta(hours=500 - i)
            for i in range(501)
        ]
        values = []
        for i, stamp in enumerate(timestamps):
            price = 2300.0 + i * 0.1
            values.append({
                "datetime": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": str(price), "high": str(price + 1),
                "low": str(price - 1), "close": str(price + 0.2),
            })
        response = Mock()
        response.json.return_value = {"values": values}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        frame = builder.fetch_hourly_candles("XAUUSD", api_key="test-key", outputsize=501)

        self.assertEqual(len(frame), 500)
        self.assertEqual(mock_get.call_args.kwargs["params"]["timezone"], "UTC")
        self.assertLess(frame["timestamp"].iloc[-1], now_hour)
        self.assertEqual(
            frame.attrs.get("data_source"),
            "Twelve Data XAU/USD",
        )

    @patch("prepare_kitty_fx_market_dataset.requests.get")
    def test_uses_free_yahoo_hourly_data_when_twelve_data_key_is_missing(self, mock_get):
        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": "", "TWELVE_DATA_API_KEY": ""}):
            start = int((pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(hours=500)).timestamp())
            timestamps = [start + i * 3600 for i in range(500)]
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

    @patch("prepare_kitty_fx_market_dataset.requests.get")
    def test_drops_the_current_incomplete_yahoo_hour(self, mock_get):
        now_hour = pd.Timestamp.now(tz="UTC").floor("h")
        timestamps = [int((now_hour - pd.Timedelta(hours=500 - i)).timestamp()) for i in range(501)]
        quotes = {
            "open": [2000.0 + i for i in range(501)],
            "high": [2001.0 + i for i in range(501)],
            "low": [1999.0 + i for i in range(501)],
            "close": [2000.5 + i for i in range(501)],
            "volume": [0 for _ in range(501)],
        }
        response = Mock()
        response.json.return_value = {"chart": {"result": [{
            "timestamp": timestamps, "indicators": {"quote": [quotes]}
        }], "error": None}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        with patch.dict(os.environ, {"TWELVEDATA_API_KEY": "", "TWELVE_DATA_API_KEY": ""}):
            frame = builder.fetch_hourly_candles("XAUUSD", outputsize=500)

        self.assertEqual(len(frame), 500)
        self.assertLess(frame["timestamp"].iloc[-1] + pd.Timedelta(hours=1), now_hour + pd.Timedelta(hours=1))
        self.assertEqual(
            frame.attrs.get("data_source"),
            "Yahoo Finance GC=F gold futures proxy (not XAU/USD spot)",
        )
    @patch("prepare_kitty_fx_market_dataset.requests.get")
    def test_twelve_data_rejects_stale_hourly_market_data(self, mock_get):
        values = []
        for i in range(600):
            stamp = pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(hours=i)
            values.append({
                "datetime": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                "open": "2300", "high": "2301", "low": "2299", "close": "2300.5",
            })
        response = Mock()
        response.json.return_value = {"values": values}
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        with self.assertRaisesRegex(RuntimeError, "stale hourly market data"):
            builder.fetch_hourly_candles("XAUUSD", api_key="test-key", outputsize=600, require_spot=True)


if __name__ == "__main__":
    unittest.main()
