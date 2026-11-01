import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


class FakeModel:
    def __init__(self, changed_decision=False, bad_number=False):
        self.changed_decision = changed_decision
        self.bad_number = bad_number

    def create_chat_completion(self, **kwargs):
        import json

        user = json.loads(kwargs["messages"][1]["content"])
        result = {
            "symbol": user["symbol"],
            "decision": "BUY" if self.changed_decision else user["kitty_assessment"]["decision"],
            "summary": "Explanation-only: the supplied timeframes are mixed.",
            "uncertainty": "The entry is not confirmed.",
            "cited_fields": ["trend_4h", "entry_5m"],
            "numeric_claims": [999999 if self.bad_number else 68000],
        }
        return {"choices": [{"message": {"content": json.dumps(result)}}]}


class ZarryServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"ZARRY_API_KEY": "test-secret", "ZARRY_MODEL_PATH": "/fake/model.gguf"}, clear=False)
        self.env.start()
        self.client = TestClient(create_app(model_loader=lambda *args: FakeModel()))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()

    def payload(self):
        return {
            "symbol": "BTCUSD",
            "timestamp": "2026-10-30T12:00:00Z",
            "context": {"trend_4h": "bullish", "entry_5m": "not_confirmed", "last_price": 68000},
            "kitty_assessment": {"decision": "WAIT", "reason_codes": ["TIMEFRAME_CONFLICT"]},
            "task": "explain",
        }

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 200)

    def test_requires_bearer_secret(self):
        self.assertEqual(self.client.post("/v1/explain", json=self.payload()).status_code, 401)

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

    def test_rejects_ungrounded_numeric_claim(self):
        client = TestClient(create_app(model_loader=lambda *args: FakeModel(bad_number=True)))
        with client:
            response = client.post(
                "/v1/explain",
                json=self.payload(),
                headers={"Authorization": "Bearer test-secret"},
            )
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
