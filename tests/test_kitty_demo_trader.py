import os
import tempfile
import unittest
from unittest.mock import patch

import kitty_demo_trader as demo


class KittyDemoTraderSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "KITTY_DEMO_DB_PATH": os.path.join(self.tmp.name, "kitty-demo.db"),
            "TRADING_MODE": "demo",
            "TRADING_PROVIDER": "binance",
            "TRADING_ENABLED": "false",
            "AGENT_TRADING_KILL_SWITCH": "true",
            "BINANCE_API_URL": "https://demo-api.binance.com/api",
            "BINANCE_API_KEY": "demo-key",
            "BINANCE_API_SECRET": "demo-secret",
        })
        self.env.start()
        with demo._settings_lock:
            demo._settings.update({"enabled": False, "order_btc": 0.0001, "max_notional_usd": 25.0})

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_disabled_cycle_never_calls_market_data_or_connector(self):
        with patch.dict(os.environ, {"AGENT_TRADING_KILL_SWITCH": "false"}):
            with patch("market.get_candles", side_effect=AssertionError("must not fetch candles")):
                result = demo.run_cycle()
        self.assertEqual(result["status"], "disabled")

    def test_status_is_not_ready_while_kill_switch_is_on(self):
        self.assertFalse(demo._trading_status()["ready"])

    def test_status_ready_only_for_demo_mode_with_kill_switch_off_and_keys(self):
        with patch.dict(os.environ, {"AGENT_TRADING_KILL_SWITCH": "false"}):
            self.assertTrue(demo._trading_status()["ready"])
        with patch.dict(os.environ, {"TRADING_MODE": "live", "AGENT_TRADING_KILL_SWITCH": "false"}):
            self.assertFalse(demo._trading_status()["ready"])


if __name__ == "__main__":
    unittest.main()
