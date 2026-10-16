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


if __name__ == "__main__":
    unittest.main()
