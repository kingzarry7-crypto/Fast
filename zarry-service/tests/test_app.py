import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import SYSTEM_PROMPT, create_app


class FakeModel:
    def __init__(self, changed_decision=False, bad_number=False, ungrounded_text_number=False):
        self.changed_decision = changed_decision
        self.bad_number = bad_number
        self.ungrounded_text_number = ungrounded_text_number
        self.last_response_format = None

    def create_chat_completion(self, **kwargs):
        import json
        self.last_response_format = kwargs.get("response_format")

        user = json.loads(kwargs["messages"][1]["content"])
        result = {
            "symbol": user["symbol"],
            "decision": "BUY" if self.changed_decision else user["kitty_assessment"]["decision"],
            "summary": (
                "Explanation-only: this is more than 50% certain."
                if self.ungrounded_text_number
                else "Explanation-only: the supplied timeframes are mixed."
            ),
            "uncertainty": "The entry is not confirmed.",
            "cited_fields": ["trend_4h", "entry_5m"],
            "numeric_claims": [999999 if self.bad_number else 68000],
        }
        return {"choices": [{"message": {"content": json.dumps(result)}}]}


class ZarryServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"ZARRY_API_KEY": "test-secret", "ZARRY_MODEL_PATH": "/fake/model.gguf"}, clear=False)
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
            "context": {"trend_4h": "bullish", "entry_5m": "not_confirmed", "last_price": 68000},
            "kitty_assessment": {"decision": "WAIT", "reason_codes": ["TIMEFRAME_CONFLICT"]},
            "task": "explain",
        }

    def test_root_status_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["service"], "ZARRY")
        self.assertEqual(body["status"], "alive")
        self.assertEqual(body["mode"], "explanation_only")
        self.assertIn("/ready", body["endpoints"]["readiness"])

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 200)

    def test_stale_timestamp_is_rejected(self):
        payload = self.payload()
        payload["timestamp"] = "2020-01-01T00:00:00Z"
        response = self.client.post(
            "/v1/explain", json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_timezone_free_timestamp_is_rejected(self):
        payload = self.payload()
        payload["timestamp"] = "2026-10-30T12:00:00"
        response = self.client.post(
            "/v1/explain", json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_request_metadata_headers_are_returned(self):
        response = self.client.get("/", headers={"X-Request-ID": "zarry-test-123"})
        self.assertEqual(response.headers["X-Request-ID"], "zarry-test-123")
        self.assertIn("X-ZARRY-Latency-Ms", response.headers)
        self.assertEqual(response.headers["X-ZARRY-API-Version"], "1.0.0")

    def test_metrics_endpoint_requires_authentication(self):
        self.assertEqual(self.client.get("/metrics").status_code, 401)

    def test_authenticated_metrics_report_operational_values(self):
        response = self.client.get("/metrics", headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["api_version"], "1.0.0")
        self.assertIn("process_max_rss_mb", body)
        self.assertIn("disk_free_mb", body)
        self.assertIn("requests_total", body)

    def test_preserves_buy_and_sell_decisions(self):
        for decision in ("BUY", "SELL"):
            with self.subTest(decision=decision):
                payload = self.payload()
                payload["kitty_assessment"]["decision"] = decision
                response = self.client.post(
                    "/v1/explain",
                    json=payload,
                    headers={"Authorization": "Bearer test-secret"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["decision"], decision)

    def test_rejects_too_many_kitty_reason_codes(self):
        payload = self.payload()
        payload["kitty_assessment"]["reason_codes"] = [f"CODE_{i}" for i in range(41)]
        response = self.client.post(
            "/v1/explain", json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_nested_context_values(self):
        payload = self.payload()
        payload["context"]["nested"] = {"unsafe": "object"}
        response = self.client.post(
            "/v1/explain", json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_rejects_oversized_context_strings(self):
        payload = self.payload()
        payload["context"]["note"] = "x" * 1001
        response = self.client.post(
            "/v1/explain", json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 422)

    def test_replaces_untrusted_request_id(self):
        response = self.client.get("/", headers={"X-Request-ID": "bad\\r\\ninjected"})
        self.assertNotEqual(response.headers["X-Request-ID"], "bad\\r\\ninjected")
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f-]{36}$")

    def test_requires_bearer_secret(self):
        self.assertEqual(self.client.post("/v1/explain", json=self.payload()).status_code, 401)

    def test_accepts_case_insensitive_bearer_scheme(self):
        response = self.client.post(
            "/v1/explain",
            json=self.payload(),
            headers={"Authorization": "bearer test-secret"},
        )
        self.assertEqual(response.status_code, 200)

    def test_preserves_kitty_decision_and_returns_explanation(self):
        response = self.client.post(
            "/v1/explain",
            json=self.payload(),
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "WAIT")
        self.assertEqual(response.json()["authority"], "KITTY_DETERMINISTIC_ENGINE")
        self.assertEqual(response.json()["mode"], "explanation_only")

    def test_model_receives_strict_schema_in_llama_cpp_response_format(self):
        response = self.client.post(
            "/v1/explain",
            json=self.payload(),
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 200)
        response_format = self.model.last_response_format
        self.assertEqual(response_format["type"], "json_object")
        self.assertIn("schema", response_format)
        schema = response_format["schema"]
        self.assertEqual(
            set(schema["required"]),
            {"symbol", "decision", "summary", "uncertainty", "cited_fields", "numeric_claims"},
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("NO TRADE", schema["properties"]["decision"]["enum"])

    def test_system_prompt_never_turns_context_warnings_into_wait(self):
        self.assertIn("Never turn a context warning into a new WAIT decision.", SYSTEM_PROMPT)
        self.assertNotIn("as reasons to WAIT", SYSTEM_PROMPT)
        self.assertIn("Never invent or estimate confidence percentages", SYSTEM_PROMPT)
        self.assertIn('exact literal phrase "explanation-only"', SYSTEM_PROMPT)

    def test_preserves_kitty_no_trade_decision(self):
        payload = self.payload()
        payload["kitty_assessment"]["decision"] = "NO TRADE"
        response = self.client.post(
            "/v1/explain",
            json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "NO TRADE")

    def test_rejects_invalid_model_decision(self):
        client = TestClient(create_app(model_loader=lambda *args: FakeModel(changed_decision=True)))
        with client:
            response = client.post(
                "/v1/explain",
                json=self.payload(),
                headers={"Authorization": "Bearer test-secret"},
            )
        self.assertEqual(response.status_code, 502)

    def test_rejects_ungrounded_numeric_claim_in_explanation_text(self):
        client = TestClient(
            create_app(model_loader=lambda *args: FakeModel(ungrounded_text_number=True))
        )
        with client:
            response = client.post(
                "/v1/explain",
                json=self.payload(),
                headers={"Authorization": "Bearer test-secret"},
            )
        self.assertEqual(response.status_code, 502)

    def test_rejects_ungrounded_numeric_claim(self):
        client = TestClient(create_app(model_loader=lambda *args: FakeModel(bad_number=True)))
        with client:
            response = client.post(
                "/v1/explain",
                json=self.payload(),
                headers={"Authorization": "Bearer test-secret"},
            )
        self.assertEqual(response.status_code, 502)

    def test_rejects_explanation_that_omits_an_expected_context_field(self):
        payload = self.payload()
        payload["expected_fields"] = ["last_price"]
        response = self.client.post(
            "/v1/explain",
            json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
        self.assertEqual(response.status_code, 502)


    def test_dockerfile_copies_the_shared_model_contract(self):
        dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
        self.assertIn("COPY app.py contract.py", dockerfile.read_text())


if __name__ == "__main__":
    unittest.main()
