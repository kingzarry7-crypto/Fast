import os
import unittest
from unittest.mock import patch

import trading_connector as trading


class BinanceDemoModeTests(unittest.TestCase):
    def test_demo_url_is_used_without_duplicate_api_prefix(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "demo",
            "BINANCE_API_URL": "https://demo-api.binance.com/api",
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
        }):
            with patch.object(trading, "_http_json", return_value={"balances": []}) as http:
                trading._binance_request("GET", "/api/v3/account", signed=True)
        self.assertEqual(
            http.call_args.args[1],
            "https://demo-api.binance.com/api/v3/account",
        )

    def test_demo_mode_rejects_live_host(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "demo",
            "BINANCE_API_URL": "https://api.binance.com",
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
        }):
            with self.assertRaisesRegex(RuntimeError, "only permits"):
                trading._binance_request("GET", "/api/v3/account", signed=True)

    def test_demo_order_is_blocked_while_kill_switch_is_on(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "demo",
            "TRADING_PROVIDER": "binance",
            "TRADING_ENABLED": "true",
            "AGENT_TRADING_KILL_SWITCH": "true",
            "TRADING_MAX_NOTIONAL": "100",
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
        }):
            self.assertFalse(trading.status()["demo_ready"])
            with self.assertRaisesRegex(RuntimeError, "kill switch is ON"):
                trading.place_market_order("BTC/USD", "BUY", 0.001, price=50000)


    def test_kitty_order_is_demo_only_and_does_not_require_global_trading_enable(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "demo",
            "TRADING_PROVIDER": "binance",
            "TRADING_ENABLED": "false",
            "AGENT_TRADING_KILL_SWITCH": "false",
            "TRADING_MAX_NOTIONAL": "25",
            "BINANCE_API_URL": "https://demo-api.binance.com/api",
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
        }):
            with patch.object(trading, "_binance_request", return_value={"status": "FILLED", "orderId": 123}) as call:
                result = trading.place_kitty_demo_order("BTC/USD", "BUY", 0.0001, 50000, 25)
        self.assertEqual(result["mode"], "demo")
        self.assertEqual(result["order_id"], 123)
        self.assertEqual(call.call_args.args[1], "/api/v3/order")
        self.assertEqual(call.call_args.kwargs["params"]["symbol"], "BTCUSDT")

    def test_kitty_demo_order_rejects_live_mode(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "live",
            "TRADING_PROVIDER": "binance",
            "AGENT_TRADING_KILL_SWITCH": "false",
            "BINANCE_API_KEY": "key",
            "BINANCE_API_SECRET": "secret",
        }):
            with self.assertRaisesRegex(RuntimeError, "TRADING_MODE=demo"):
                trading.place_kitty_demo_order("BTC/USD", "BUY", 0.0001, 50000, 25)

    def test_kitty_demo_order_enforces_notional_cap(self):
        with patch.dict(os.environ, {
            "TRADING_MODE": "demo",
            "TRADING_PROVIDER": "binance",
            "AGENT_TRADING_KILL_SWITCH": "false",
            "BINANCE_API_URL": "https://demo-api.binance.com",
            "BINANCE_API_KEY": "key",
            "BINANCE_API_SECRET": "secret",
        }):
            with self.assertRaisesRegex(ValueError, "notional limit"):
                trading.place_kitty_demo_order("BTC/USD", "BUY", 0.001, 50000, 25)


if __name__ == "__main__":
    unittest.main()
