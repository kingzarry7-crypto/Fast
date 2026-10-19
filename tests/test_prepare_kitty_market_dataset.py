import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

import prepare_kitty_market_dataset as builder


class KittyMarketDatasetTests(unittest.TestCase):
    def test_features_and_forward_labels_are_finite_and_chronological(self):
        rng = np.random.default_rng(2026)
        count = 1200
        returns = rng.normal(0.00005, 0.004, count)
        closes = 60_000 * np.cumprod(1 + returns)
        opens = np.concatenate(([closes[0] * (1 - returns[0]),], closes[:-1]))
        frame = pd.DataFrame({
            "timestamp": [datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(count)],
            "open": opens,
            "high": np.maximum(opens, closes) * 1.001,
            "low": np.minimum(opens, closes) * 0.999,
            "close": closes,
            "volume": rng.uniform(1, 100, count),
        })
        dataset = builder.build_dataset(frame)
        self.assertGreater(len(dataset), 1000)
        self.assertTrue(np.isfinite(dataset[builder.FEATURES].to_numpy()).all())
        self.assertEqual(set(dataset["target"].unique()), {0, 1, 2})
        self.assertLess(dataset["timestamp"].iloc[0], dataset["timestamp"].iloc[-1])
        self.assertTrue(np.isfinite(dataset["forward_return_6h"]).all())
        source = frame.set_index("timestamp")
        first = dataset.iloc[0]
        entry_time = first["timestamp"] + timedelta(hours=1)
        exit_time = first["timestamp"] + timedelta(hours=7)
        expected_entry = float(source.loc[entry_time, "open"])
        expected_exit = float(source.loc[exit_time, "close"])
        expected_return = expected_exit / expected_entry - 1.0
        self.assertAlmostEqual(float(first["entry_price_next_open"]), expected_entry, places=10)
        self.assertAlmostEqual(float(first["exit_price_after_6h"]), expected_exit, places=10)
        self.assertAlmostEqual(float(first["forward_return_6h"]), expected_return, places=10)
        self.assertTrue((dataset["timestamp"] < frame["timestamp"].iloc[-7]).all())


    @unittest.mock.patch("prepare_kitty_market_dataset.fetch_cryptocompare_hourly")
    @unittest.mock.patch("prepare_kitty_market_dataset.requests.Session.get", side_effect=requests.HTTPError("451 blocked"))
    def test_binance_http_451_uses_public_fallback(self, mock_get, mock_fallback):
        fallback = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=500, freq="h", tz="UTC"),
            "open": np.ones(500), "high": np.ones(500) * 1.01,
            "low": np.ones(500) * 0.99, "close": np.ones(500),
            "volume": np.ones(500),
        })
        mock_fallback.return_value = fallback
        result = builder.fetch_hourly_klines("BTC", 500)
        self.assertEqual(len(result), 500)
        mock_fallback.assert_called_once_with("BTC", 500)

    def test_rejects_short_and_unsupported_sources(self):
        with self.assertRaises(ValueError):
            builder.fetch_hourly_klines("XAU")
        short = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=80, freq="h", tz="UTC"),
            "open": np.ones(80), "high": np.ones(80) * 1.01,
            "low": np.ones(80) * 0.99, "close": np.ones(80),
        })
        with self.assertRaises(ValueError):
            builder.build_dataset(short)


if __name__ == "__main__":
    unittest.main()
