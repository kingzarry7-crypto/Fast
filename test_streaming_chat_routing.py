"""Regression tests ensuring streaming chat uses specialist intent routing."""

import json
import unittest
from unittest.mock import patch

from streaming_chat import _build_stream_generator


class _Memory:
    def add_message(self, *args, **kwargs):
        return None


def _events(chunks):
    parsed = []
    for chunk in chunks:
        for line in str(chunk).splitlines():
            if line.startswith("data: "):
                parsed.append(json.loads(line[6:]))
    return parsed


class StreamingIntentRoutingTests(unittest.TestCase):
    def test_media_request_routes_before_coding_and_connector_agents(self):
        with patch("ai_engine.AIEngine._route_media_request", return_value="Please attach the image you want edited."), \
             patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request") as coding, \
             patch("account_agent.handle_web_request") as connector:
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Edit this picture of my gold chart",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertTrue(any(e.get("provider") == "media_agent" for e in events))
        self.assertTrue(any("attach the image" in e.get("text", "").lower() for e in events))
        coding.assert_not_called()
        connector.assert_not_called()

    def test_market_request_uses_specialist_agent_in_streaming_path(self):
        specialist = {
            "status": "completed",
            "provider": "market_agent",
            "operation": "analyze_market",
            "target": "XAU/USD",
            "reply": "Market Agent report — XAU/USD (1h). Signal: WAIT. No trade was placed.",
        }
        with patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", return_value=specialist):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Analyze gold on the 1h timeframe",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertTrue(any(e.get("provider") == "market_agent" for e in events))
        self.assertTrue(any("XAU/USD" in e.get("text", "") for e in events))

    def test_market_router_failure_is_not_replaced_with_generic_guess(self):
        with patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", side_effect=RuntimeError("provider failure")):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Give me a BTC signal",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        done = [e for e in events if e.get("type") == "done"]
        self.assertTrue(done)
        self.assertEqual(done[-1].get("status"), "unavailable")
        self.assertIn("No price or signal was invented", done[-1].get("text", ""))


if __name__ == "__main__":
    unittest.main()
