import json
import os
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import SERVICE_EXPLANATION_PROMPT, _load_model, create_app, extract_final_response


class FakeModel:
    def __init__(self, summary=None, malformed=False):
        self.summary = summary or (
            "This explanation uses the supplied qualitative context and preserves Kitty's decision "
            "while noting the unresolved entry confirmation."
        )
        self.malformed = malformed
        self.last_messages = None
        self.last_response_format = None
        self.last_chat_template_kwargs = None

    def create_chat_completion(self, **kwargs):
        self.last_messages = kwargs["messages"]
        self.last_response_format = kwargs.get("response_format")
        self.last_chat_template_kwargs = kwargs.get("chat_template_kwargs")
        if self.malformed:
            content = '{"summary": , "uncertainty": "not valid JSON"}'
        else:
            content = json.dumps({
                "symbol": "XAUUSD",
                "decision": "SELL",
                "summary": self.summary,
                "uncertainty": "The model uncertainty is ignored by the service.",
                "cited_fields": ["invented_field"],
                "numeric_claims": [999999],
            })
        return {"choices": [{"message": {"content": content}}]}


class ZarryServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {"ZARRY_API_KEY": "test-secret", "ZARRY_MODEL_PATH": "/fake/model.gguf"},
            clear=False,
        )
        self.env.start()
        self.model = FakeModel()
        self.client = TestClient(create_app(model_loader=lambda *args: self.model))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()

    def payload(self):
        return {
            "symbol": "BTCUSD",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "trend_4h": "bullish",
                "direction_1h": "bearish",
                "setup_15m": "mixed",
                "entry_5m": "not_confirmed",
                "data_fresh": True,
                "last_price": 68000,
            },
            "expected_fields": ["trend_4h", "direction_1h", "setup_15m", "entry_5m", "data_fresh"],
            "kitty_assessment": {"decision": "WAIT", "reason_codes": ["TIMEFRAME_CONFLICT"]},
            "task": "explain",
        }

    def post_explain(self, payload=None, token="test-secret"):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.post("/v1/explain", json=payload or self.payload(), headers=headers)

    def test_root_health_and_readiness(self):
        root = self.client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["service"], "ZARRY")
        self.assertEqual(root.json()["mode"], "explanation_only")
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 200)

    def test_metrics_requires_auth_and_reports_operational_values(self):
        self.assertEqual(self.client.get("/metrics").status_code, 401)
        response = self.client.get("/metrics", headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("process_max_rss_mb", response.json())
        self.assertIn("disk_free_mb", response.json())
        self.assertIn("requests_total", response.json())

    def test_requires_bearer_secret(self):
        self.assertEqual(self.post_explain(token=None).status_code, 401)

    def test_model_cannot_change_symbol_decision_citations_or_numeric_claims(self):
        response = self.post_explain()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["symbol"], "BTCUSD")
        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["cited_fields"], self.payload()["expected_fields"])
        self.assertEqual(result["numeric_claims"], [])
        self.assertEqual(result["authority"], "KITTY_DETERMINISTIC_ENGINE")
        self.assertEqual(result["mode"], "explanation_only")
        self.assertEqual(result["explanation_source"], "model")

    def test_model_prompt_and_context_contain_no_numeric_digits(self):
        response = self.post_explain()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(char.isdigit() for char in SERVICE_EXPLANATION_PROMPT))
        user_message = self.model.last_messages[1]["content"]
        self.assertTrue(user_message.startswith("/no_think\n"))
        self.assertFalse(any(char.isdigit() for char in user_message))
        payload = json.loads(user_message.removeprefix("/no_think\n"))
        self.assertNotIn("expected_fields", payload)
        self.assertNotIn("timestamp", payload)
        self.assertEqual(payload["context"]["higher_timeframe_trend"], "bullish")
        self.assertEqual(payload["context"]["shorter_timeframe_direction"], "bearish")
        self.assertEqual(payload["context"]["entry"], "not_confirmed")

    def test_numeric_model_output_uses_transparent_fallback(self):
        self.model.summary = (
            "Explanation-only: the setup is more than 50% certain and the entry has a numeric value."
        )
        response = self.post_explain()
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["explanation_source"], "deterministic_fallback")
        self.assertIn("deterministic fallback", result["summary"].lower())
        self.assertFalse(any(char.isdigit() for char in result["summary"] + result["uncertainty"]))
        self.assertEqual(result["numeric_claims"], [])

    def test_malformed_model_output_uses_transparent_fallback(self):
        self.model.malformed = True
        response = self.post_explain()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["explanation_source"], "deterministic_fallback")
        self.assertEqual(response.json()["decision"], "WAIT")

    def test_missing_expected_context_field_fails_closed(self):
        payload = self.payload()
        payload["expected_fields"] = ["missing_field"]
        response = self.post_explain(payload)
        self.assertEqual(response.status_code, 502)

    def test_preserves_buy_sell_and_no_trade_decisions(self):
        for decision in ("BUY", "SELL", "NO TRADE"):
            with self.subTest(decision=decision):
                payload = self.payload()
                payload["kitty_assessment"]["decision"] = decision
                response = self.post_explain(payload)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["decision"], decision)

    def test_rejects_stale_and_timezone_free_timestamps(self):
        payload = self.payload()
        payload["timestamp"] = "2020-01-01T00:00:00Z"
        self.assertEqual(self.post_explain(payload).status_code, 422)
        payload = self.payload()
        payload["timestamp"] = "2026-10-30T12:00:00"
        self.assertEqual(self.post_explain(payload).status_code, 422)

    def test_rejects_oversized_or_nested_context(self):
        payload = self.payload()
        payload["context"]["nested"] = {"unsafe": "object"}
        self.assertEqual(self.post_explain(payload).status_code, 422)
        payload = self.payload()
        payload["context"]["note"] = "x" * 1001
        self.assertEqual(self.post_explain(payload).status_code, 422)

    def test_rejects_too_many_reason_codes(self):
        payload = self.payload()
        payload["kitty_assessment"]["reason_codes"] = [f"CODE_{index}" for index in range(41)]
        self.assertEqual(self.post_explain(payload).status_code, 422)

    def test_request_metadata_headers_are_returned(self):
        response = self.client.get("/", headers={"X-Request-ID": "zarry-test-123"})
        self.assertEqual(response.headers["X-Request-ID"], "zarry-test-123")
        self.assertIn("X-ZARRY-Latency-Ms", response.headers)
        self.assertEqual(response.headers["X-ZARRY-API-Version"], "1.0.0")

    def test_model_load_disables_qwen_thinking(self):
        with patch.dict(sys.modules, {"llama_cpp": SimpleNamespace(Llama=lambda **kwargs: kwargs)}):
            config = _load_model("/fake/model.gguf", 2, 4096)
        self.assertEqual(config["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(config["n_gpu_layers"], 0)

    def test_extract_final_response_discards_thinking_and_rejects_unterminated_block(self):
        self.assertEqual(extract_final_response("<think>private</think>final answer"), "final answer")
        with self.assertRaises(ValueError):
            extract_final_response("<think>unfinished reasoning")


if __name__ == "__main__":
    unittest.main()
