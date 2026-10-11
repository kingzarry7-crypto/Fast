import unittest
from unittest.mock import patch

import agent_router


class AgentRouterTests(unittest.TestCase):
    def test_general_chat_is_not_intercepted(self):
        self.assertIsNone(agent_router.route_agent_request("Hello, how are you?", "u1"))

    def test_market_intent_routes_to_market_agent(self):
        analysis = {
            "symbol": "XAU/USD", "timeframe": "1h", "price": 4312.5,
            "signal": "WAIT", "trend": "mixed", "confidence": 52,
            "entry": None, "stop_loss": None, "tp1": None, "tp2": None, "tp3": None,
            "reasons": ["mixed timeframes"], "data_ok": True,
        }
        with patch("agent_core.tool_analyze_symbol", return_value=analysis), \
             patch("agent_core.tool_news_risk", return_value={"level": "LOW"}), \
             patch("agent_core.tool_learn", return_value="learning-id"):
            result = agent_router.route_agent_request("Analyze gold on the 1h timeframe", "u1")
        self.assertEqual(result["provider"], "market_agent")
        self.assertIn("XAU/USD", result["reply"])
        self.assertIn("4312.5", result["reply"])
        self.assertIn("No trade was placed", result["reply"])

    def test_market_data_failure_is_reported_without_fabrication(self):
        with patch("agent_core.tool_analyze_symbol", return_value={
            "symbol": "BTC/USD", "signal": "WAIT", "data_ok": False, "error": "provider timeout"
        }), patch("agent_core.tool_news_risk", return_value={}):
            result = agent_router.route_agent_request("Give me a BTC signal", "u1")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("will not invent", result["reply"])

    def test_capability_report_does_not_claim_unverified_accounts(self):
        with patch("agent_router._connected_accounts", return_value=[]):
            result = agent_router.route_agent_request("What access do you have?", "u1")
        self.assertIn("No connected provider accounts were verified", result["reply"])
        self.assertIn("approval", result["reply"].lower())


if __name__ == "__main__":
    unittest.main()
