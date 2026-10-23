"""Regression tests for market-data fallback behavior."""
import unittest
from unittest.mock import patch

import market


class MarketEmptyFallbackTests(unittest.TestCase):
    def test_empty_paid_market_responses_fall_through_to_public_binance(self):
        from datetime import datetime, timezone
        candles = [{
            "time": datetime.now(timezone.utc).isoformat(),
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
        }]
        with (
            patch.object(market, "_is_gold_symbol", return_value=False),
            patch.object(market, "_should_try_alpaca_market_data", return_value=True),
            patch.object(market, "_alpaca_supports_symbol", return_value=True),
            patch.object(market, "_alpaca_get_candles", return_value=[]),
            patch.object(market, "_should_try_massive_market_data", return_value=True),
            patch.object(market, "_massive_get_candles", return_value=[]),
            patch.object(market, "binance_pair", return_value="BTCUSDT"),
            patch.object(market, "_binance_get_candles", return_value=candles),
            patch.object(market, "_twelve_get_candles", side_effect=AssertionError("should not need Twelve Data")),
        ):
            result = market.get_candles("BTC/USD", "1h", 100)
        self.assertEqual(result, candles)

    def test_stale_preferred_provider_falls_through_to_fresh_binance(self):
        from datetime import datetime, timedelta, timezone
        fresh = [{
            "time": datetime.now(timezone.utc).isoformat(),
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10.0,
        }]
        stale = [{
            "time": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10.0,
        }]
        with (
            patch.object(market, "_is_gold_symbol", return_value=False),
            patch.object(market, "_should_try_alpaca_market_data", return_value=True),
            patch.object(market, "_alpaca_supports_symbol", return_value=True),
            patch.object(market, "_alpaca_get_candles", return_value=stale),
            patch.object(market, "_should_try_massive_market_data", return_value=False),
            patch.object(market, "binance_pair", return_value="BTCUSDT"),
            patch.object(market, "_binance_get_candles", return_value=fresh) as binance,
            patch.object(market, "_twelve_get_candles", side_effect=AssertionError("fresh Binance should be used")),
        ):
            result = market.get_candles("BTC/USD", "1h", 100)
        self.assertEqual(result, fresh)
        binance.assert_called_once()

    def test_stale_candles_are_not_returned_when_all_providers_are_stale(self):
        from datetime import datetime, timedelta, timezone
        stale = [{
            "time": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10.0,
        }]
        with (
            patch.object(market, "_is_gold_symbol", return_value=False),
            patch.object(market, "_should_try_alpaca_market_data", return_value=False),
            patch.object(market, "_should_try_massive_market_data", return_value=False),
            patch.object(market, "binance_pair", return_value="BTCUSDT"),
            patch.object(market, "_binance_get_candles", return_value=stale),
            patch.object(market, "_twelve_get_candles", return_value=stale),
        ):
            with self.assertRaisesRegex(RuntimeError, "No fresh candle provider returned data"):
                market.get_candles("BTC/USD", "1h", 100)

    def test_market_data_does_not_return_empty_candles(self):
        with (
            patch.object(market, "_is_gold_symbol", return_value=False),
            patch.object(market, "_should_try_alpaca_market_data", return_value=False),
            patch.object(market, "_alpaca_supports_symbol", return_value=False),
            patch.object(market, "_should_try_massive_market_data", return_value=False),
            patch.object(market, "binance_pair", return_value=None),
            patch.object(market, "_twelve_get_candles", return_value=[]),
        ):
            with self.assertRaisesRegex(RuntimeError, "No fresh candle provider returned data"):
                market.get_candles("UNKNOWN/USD", "1h", 100)


if __name__ == "__main__":
    unittest.main()
