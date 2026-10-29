"""Safety tests for Kitty signals without proven per-market strategy edge."""
import unittest
from datetime import datetime, timedelta, timezone

from kitty_api import _technical_signal


def rising_candles(count=80):
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(count):
        close = 100.0 + i * 0.5
        rows.append({
            "datetime": (now - timedelta(hours=count - i)).isoformat(),
            "open": close - 0.1,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
            "volume": 100,
        })
    return rows


class KittyUnvalidatedSignalSafetyTests(unittest.TestCase):
    def test_strong_rule_based_setup_is_not_promoted_to_buy_without_validated_edge(self):
        result = _technical_signal(rising_candles(), "BTC/USD", "1h")
        self.assertEqual(result["candidate_signal"], "BUY")
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertFalse(result["strategy_edge_validated"])
        self.assertEqual(result["signal_gate_reason"], "no_validated_net_edge_for_rule_based_strategy")
        self.assertFalse(result["trading_enabled"])

    def test_rule_based_signal_explains_that_candidate_is_research_only(self):
        result = _technical_signal(rising_candles(), "XAU/USD", "1h")
        self.assertIn(result["candidate_signal"], {"BUY", "SELL", "NO TRADE"})
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertTrue(result["research_only"])


    def test_candidate_buy_includes_directional_atr_risk_references_but_stays_non_actionable(self):
        result = _technical_signal(rising_candles(), "BTC/USD", "1h")
        entry = result["price"]
        levels = result["candidate_risk_levels"]
        self.assertEqual(result["candidate_signal"], "BUY")
        self.assertLess(levels["stop_reference"], entry)
        self.assertGreater(levels["target_1_reference"], entry)
        self.assertGreater(levels["target_2_reference"], levels["target_1_reference"])
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertFalse(result["trading_enabled"])

if __name__ == "__main__":
    unittest.main()
