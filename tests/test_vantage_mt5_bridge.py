import tempfile
import unittest
from pathlib import Path

from vantage_mt5_bridge import (
    BridgeState,
    APPROVED_SYMBOLS,
    resolve_symbols,
    verify_demo_account,
)


class VantageBridgeSafetyTests(unittest.TestCase):
    def test_only_gold_and_selected_forex_are_allowlisted(self):
        self.assertEqual(
            set(APPROVED_SYMBOLS),
            {"XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY"},
        )

    def test_unknown_or_ambiguous_broker_symbols_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "could not resolve"):
            resolve_symbols(["XAUUSD", "EURUSD", "GBPUSD"])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve_symbols(["XAUUSD", "XAUUSD.a", "EURUSD", "GBPUSD", "USDJPY"])

    def test_broker_symbol_names_are_resolved_only_when_unambiguous(self):
        resolved = resolve_symbols(["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"])
        self.assertEqual(resolved["XAU/USD"], "XAUUSD")
        self.assertEqual(resolved["EUR/USD"], "EURUSD")
        self.assertEqual(resolved["GBP/USD"], "GBPUSD")
        self.assertEqual(resolved["USD/JPY"], "USDJPY")

    def test_demo_account_is_verified_by_trade_mode_not_server_name(self):
        verify_demo_account({"trade_mode": 0}, demo_trade_mode=0)
        with self.assertRaisesRegex(PermissionError, "demo account"):
            verify_demo_account({"trade_mode": 2}, demo_trade_mode=0)
        with self.assertRaisesRegex(PermissionError, "cannot be verified"):
            verify_demo_account({}, demo_trade_mode=0)

    def test_restart_fails_stopped_and_emergency_stop_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "bridge.sqlite3")
            first = BridgeState(db)
            self.assertEqual(first.get_status()["mode"], "STOPPED")
            first.start_monitoring()
            self.assertEqual(first.get_status()["mode"], "MONITORING")
            first.emergency_stop("test")
            second = BridgeState(db)
            self.assertEqual(second.get_status()["mode"], "EMERGENCY_STOP")
            with self.assertRaisesRegex(PermissionError, "emergency stop"):
                second.start_monitoring()

    def test_pause_and_signal_deduplication_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "bridge.sqlite3")
            state = BridgeState(db)
            state.start_monitoring()
            state.pause()
            self.assertEqual(state.get_status()["mode"], "PAUSED")
            self.assertTrue(state.record_signal("signal-1", {"symbol": "XAU/USD"}))
            self.assertFalse(state.record_signal("signal-1", {"symbol": "XAU/USD"}))
            events = state.audit_events()
            self.assertTrue(any(item["event"] == "signal_duplicate_blocked" for item in events))


if __name__ == "__main__":
    unittest.main()
