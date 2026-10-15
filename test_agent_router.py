import unittest
from unittest.mock import patch

import agent_router
from system_inventory import format_project_inventory, get_project_inventory


class AgentRouterTests(unittest.TestCase):
    def test_general_chat_is_not_intercepted(self):
        self.assertIsNone(agent_router.route_agent_request("Hello, how are you?", "u1"))

    def test_image_edit_with_market_words_is_not_routed_to_market_agent(self):
        result = agent_router.route_agent_request("Edit this picture of my gold chart", "u1")
        self.assertIsNone(result)

    def test_image_generation_is_not_routed_to_market_agent(self):
        result = agent_router.route_agent_request("Create an image of a gold trader", "u1")
        self.assertIsNone(result)

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


    def test_project_update_request_reports_king_zarry_files(self):
        result = agent_router.route_agent_request("Give me my own updates and show my files", "u1")
        self.assertEqual(result["provider"], "project_inventory")
        self.assertIn("King Zarry AI", result["reply"])
        self.assertIn("workflow_engine.py", result["reply"])
        self.assertIn("How to use", result["reply"])

    def test_inventory_does_not_equate_file_presence_with_connected_accounts(self):
        report = format_project_inventory()
        self.assertIn("does not mean its API key", report)
        self.assertIn("will not invent a latest commit", report)

    def test_inventory_checks_paths_in_runtime_checkout(self):
        inventory = get_project_inventory()
        self.assertGreater(inventory["component_count"], 0)
        self.assertEqual(inventory["component_count"], len(inventory["components"]))
        self.assertTrue(all("present" in item and "path" in item for item in inventory["components"]))


if __name__ == "__main__":
    unittest.main()
