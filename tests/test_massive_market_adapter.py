import unittest
from unittest.mock import Mock, patch

import market


class MassiveMarketAdapterTests(unittest.TestCase):
    def test_crypto_symbol_maps_to_massive_ticker(self):
        self.assertEqual(market._massive_symbol("BTC/USD"), "X:BTCUSD")
        self.assertEqual(market._massive_symbol("ETHUSDT"), "X:ETHUSD")
        self.assertEqual(market._massive_symbol("AAPL"), "AAPL")

    @patch.dict("os.environ", {"MASSIVE_API_KEY": "test-key"}, clear=False)
    @patch("market.requests.get")
    def test_aggregate_bars_normalize_to_app_candle_schema(self, get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "status": "OK",
            "results": [
                {"t": 1792000000000 + index * 60000, "o": 100 + index,
                 "h": 102 + index, "l": 99 + index, "c": 101 + index,
                 "v": 12 + index}
                for index in range(20)
            ],
        }
        get.return_value = response

        candles = market._massive_get_candles("BTC/USD", "1m", 20)

        self.assertEqual(len(candles), 20)
        self.assertEqual(set(candles[-1]), {"datetime", "open", "high", "low", "close", "volume"})
        self.assertEqual(candles[-1]["close"], "120")
        args, kwargs = get.call_args
        self.assertIn("/v2/aggs/ticker/X:BTCUSD/range/1/minute/", args[0])
        self.assertEqual(kwargs["params"]["apiKey"], "test-key")
        self.assertNotIn("test-key", args[0])

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "MASSIVE_API_KEY or POLYGON_API_KEY"):
            market._massive_get_candles("BTC/USD", "15m", 20)

    @patch.dict("os.environ", {"POLYGON_API_KEY": "polygon-test"}, clear=False)
    def test_polygon_key_alias_is_supported(self):
        self.assertEqual(market._massive_api_key(), "polygon-test")


if __name__ == "__main__":
    unittest.main()
