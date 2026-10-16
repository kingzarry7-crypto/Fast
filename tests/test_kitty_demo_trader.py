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
        demo._settings_loaded = False

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

    def test_settings_survive_process_restart(self):
        with patch.dict(os.environ, {"AGENT_TRADING_KILL_SWITCH": "false"}):
            demo._init_db()
            with demo._settings_lock:
                demo._settings.update({"enabled": True, "order_btc": 0.0002, "max_notional_usd": 20.0})
            demo._persist_settings()
            with demo._settings_lock:
                demo._settings.update({"enabled": False, "order_btc": 0.0001, "max_notional_usd": 25.0})
            demo._settings_loaded = False
            demo._restore_settings()
        self.assertTrue(demo._settings["enabled"])
        self.assertEqual(demo._settings["order_btc"], 0.0002)
        self.assertEqual(demo._settings["max_notional_usd"], 20.0)

    def test_startup_restores_enabled_worker_only_when_demo_ready(self):
        with patch.dict(os.environ, {"AGENT_TRADING_KILL_SWITCH": "false"}):
            demo._init_db()
            with demo._settings_lock:
                demo._settings.update({"enabled": True, "order_btc": 0.0001, "max_notional_usd": 25.0})
            demo._persist_settings()
            demo._settings_loaded = False
            with patch.object(demo, "start_worker") as start_worker:
                demo.initialize_worker()
                start_worker.assert_called_once()
        with patch.dict(os.environ, {"TRADING_MODE": "live", "AGENT_TRADING_KILL_SWITCH": "false"}):
            demo._settings_loaded = False
            with patch.object(demo, "start_worker") as start_worker:
                demo.initialize_worker()
                start_worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
