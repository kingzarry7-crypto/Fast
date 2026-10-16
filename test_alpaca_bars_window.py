"""Regression coverage for Alpaca's historical crypto-bars query window."""
import unittest
from datetime import datetime
from unittest.mock import patch

import market


class AlpacaBarsWindowTests(unittest.TestCase):
    def test_historical_window_covers_requested_candle_count(self):
        bars = [
            {
                "t": f"2026-10-15T00:{i:02d}:00Z",
                "o": 100 + i,
                "h": 101 + i,
                "l": 99 + i,
                "c": 100.5 + i,
                "v": 10,
            }
            for i in range(15)
        ]
        with patch.object(
            market,
            "_alpaca_request",
            return_value={"bars": {"BTC/USD": bars}},
        ) as request:
            result = market._alpaca_get_candles("BTC/USD", "15m", 20)

        self.assertEqual(len(result), 15)
        params = request.call_args.args[1]
        self.assertIn("start", params)
        self.assertIn("end", params)
        start = datetime.fromisoformat(params["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(params["end"].replace("Z", "+00:00"))
        self.assertGreaterEqual((end - start).total_seconds(), 30 * 15 * 60)
        self.assertEqual(params["sort"], "asc")


    def test_unsupported_bnb_skips_alpaca_and_uses_fallback(self):
        candles = [{"datetime": "2026-10-16T00:00:00Z", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "1"}] * 15
        with (
            patch.object(market, "_should_try_alpaca_market_data", return_value=True),
            patch.object(market, "_alpaca_get_candles") as alpaca,
            patch.object(market, "_should_try_massive_market_data", return_value=False),
            patch.object(market, "binance_pair", return_value="BNBUSDT"),
            patch.object(market, "_binance_get_candles", return_value=candles),
        ):
            result = market.get_candles("BNB/USD", "15m", 15)

        alpaca.assert_not_called()
        self.assertEqual(len(result), 15)


if __name__ == "__main__":
    unittest.main()
