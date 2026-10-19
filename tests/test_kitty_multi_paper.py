import os
import tempfile
import unittest
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import kitty_multi_paper as paper


def candles(count=60):
    now = datetime.now(timezone.utc)
    result = []
    for i in range(count):
        close = 60_000.0 + i * 5.0
        stamp = now - timedelta(hours=count - i - 1)
        result.append({
            "datetime": stamp.isoformat(),
            "open": close - 2, "high": close + 8,
            "low": close - 8, "close": close, "volume": 10,
        })
    return result


class KittyMultiPaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "KITTY_MULTI_PAPER_DB_PATH": os.path.join(self.tmp.name, "multi-paper.db"),
            "KITTY_MULTI_PAPER_POLL_SECONDS": "900",
        })
        self.env.start()
        self.kitty_api_stub = types.ModuleType("kitty_api")
        def validate_candles(rows, timeframe, symbol):
            if not isinstance(rows, list) or len(rows) < 35:
                raise ValueError("insufficient candles")
            for row in rows[-35:]:
                for key in ("open", "high", "low", "close"):
                    value = float(row[key])
                    if not value > 0:
                        raise ValueError("invalid candle")
            return str(rows[-1].get("datetime") or rows[-1].get("time"))
        self.kitty_api_stub._validate_candles = validate_candles
        self.kitty_api_stub._technical_signal = lambda rows, symbol, timeframe: {}
        self.modules = patch.dict(sys.modules, {"kitty_api": self.kitty_api_stub})
        self.modules.start()
        paper._loaded = False
        paper._settings.update({
            "enabled": False,
            "symbols": ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD", "EUR/USD"],
            "timeframe": "1h",
            "max_order_notional_usd": 25.0,
        })
        paper._restore_settings()

    def tearDown(self):
        with paper._settings_lock:
            paper._settings["enabled"] = False
        paper._loaded = False
        self.modules.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_disabled_cycle_does_not_fetch_market_data(self):
        with patch("market.get_candles", side_effect=AssertionError("should not fetch")):
            result = paper.run_cycle()
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["live_trading_enabled"])

    def test_buy_signal_creates_only_paper_order_and_duplicate_is_blocked(self):
        rows = candles()
        closed = rows[-2]
        signal = {
            "symbol": "BTC/USD", "timeframe": "1h", "signal": "BUY",
            "price": float(closed["close"]), "completed_candle_time": closed["datetime"],
            "confidence_score": 0.8, "research_only": True, "trading_enabled": False,
            "reasons": ["test fixture"],
        }
        with paper._settings_lock:
            paper._settings.update({"enabled": True, "symbols": ["BTC/USD"], "timeframe": "1h", "max_order_notional_usd": 25.0})
        with patch("market.get_candles", return_value=rows), \
             patch.object(self.kitty_api_stub, "_technical_signal", return_value=signal), \
             patch("trading_connector.place_market_order", side_effect=AssertionError("paper must never call broker")):
            first = paper.run_cycle()
            second = paper.run_cycle()
        self.assertEqual(first["results"][0]["status"], "simulated_order")
        self.assertEqual(first["results"][0]["side"], "BUY")
        self.assertEqual(second["results"][0]["status"], "already_processed")
        state = paper.status()
        self.assertEqual(len(state["recent_orders"]), 1)
        self.assertFalse(state["live_trading_enabled"])
        self.assertFalse(state["exchange_connector_used"])
        self.assertLess(state["cash_usd"], 10_000)

    def test_sell_signal_closes_open_position_without_broker(self):
        rows = candles()
        closed = rows[-2]
        with paper._lock:
            conn = paper._connect()
            try:
                conn.execute(
                    "INSERT INTO kitty_multi_paper_positions(symbol,quantity,avg_entry,mark_price,updated_at) VALUES(?,?,?,?,?)",
                    ("XAU/USD", 0.02, 2000.0, 2000.0, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
            finally:
                conn.close()
        signal = {
            "symbol": "XAU/USD", "timeframe": "1h", "signal": "SELL",
            "price": float(closed["close"]), "completed_candle_time": closed["datetime"],
            "confidence_score": 0.8, "research_only": True, "trading_enabled": False,
            "reasons": ["test fixture"],
        }
        with paper._settings_lock:
            paper._settings.update({"enabled": True, "symbols": ["XAU/USD"], "timeframe": "1h", "max_order_notional_usd": 25.0})
        with patch("market.get_candles", return_value=rows), \
             patch.object(self.kitty_api_stub, "_technical_signal", return_value=signal), \
             patch("trading_connector.place_market_order", side_effect=AssertionError("paper must never call broker")):
            result = paper.run_cycle()
        self.assertEqual(result["results"][0]["side"], "SELL")
        self.assertEqual(paper.status()["positions"], [])

    def test_rejects_unsupported_symbols_and_timeframes(self):
        with self.assertRaises(ValueError):
            paper._normalize_symbols(["DOGE/USD"])
        from kitty_multi_paper import MultiPaperSettingsRequest
        from fastapi import HTTPException
        request = object()
        with patch.object(paper, "_require_user"):
            with self.assertRaises(HTTPException):
                paper.update_settings(request, MultiPaperSettingsRequest(enabled=True, symbols=["BTC/USD"], timeframe="3m"))

    def test_settings_persist_and_only_allow_approved_symbols(self):
        with paper._settings_lock:
            paper._settings.update({"enabled": True, "symbols": ["BTC/USD", "XAU/USD"], "timeframe": "15m", "max_order_notional_usd": 50.0})
        paper._persist_settings()
        paper._loaded = False
        with paper._settings_lock:
            paper._settings.update({"enabled": False, "symbols": ["BTC/USD"], "timeframe": "1h", "max_order_notional_usd": 25.0})
        paper._restore_settings()
        self.assertTrue(paper._settings["enabled"])
        self.assertEqual(paper._settings["symbols"], ["BTC/USD", "XAU/USD"])
        self.assertEqual(paper._settings["timeframe"], "15m")


if __name__ == "__main__":
    unittest.main()
