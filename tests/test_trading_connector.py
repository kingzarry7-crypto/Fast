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


if __name__ == "__main__":
    unittest.main()
