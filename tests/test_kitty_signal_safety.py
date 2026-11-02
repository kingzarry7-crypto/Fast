"""Safety tests for Kitty signals without proven per-market strategy edge."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import kitty_api
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

class KittyGoldEndpointContractTests(unittest.TestCase):
    def test_gold_hourly_signal_keeps_shared_technical_response_shape_and_no_trade_gate(self):
        app = FastAPI()
        app.include_router(kitty_api.router)
        prediction = {
            "signal": "NO TRADE",
            "class_prediction": "LONG",
            "confidence": 0.617235,
            "signal_edge_validated": False,
            "signal_block_reason": "Holdout diagnostics did not validate positive net edge",
        }
        with (
            patch("market.get_candles", return_value=rising_candles(80)),
            patch.object(kitty_api.gold_model, "status", return_value={"available": True}),
            patch.object(kitty_api.gold_model, "predict_features", return_value=prediction),
        ):
            response = TestClient(app).get("/api/kitty/signal?symbol=XAU%2FUSD&timeframe=1h")

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["symbol"], "XAU/USD")
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertFalse(result["trading_enabled"])
        self.assertFalse(result["automatic_order_execution_enabled"])
        self.assertIsInstance(result["price"], (int, float))
        self.assertIsInstance(result["indicators"], dict)
        self.assertIsInstance(result["risk_levels"], dict)
        self.assertIsInstance(result["reasons"], list)
        self.assertEqual(result["gold_model_candidate_signal"], "LONG")
        self.assertEqual(result["gold_model_confidence"], 0.617235)
        self.assertFalse(result["gold_model_signal_edge_validated"])


if __name__ == "__main__":
    unittest.main()
