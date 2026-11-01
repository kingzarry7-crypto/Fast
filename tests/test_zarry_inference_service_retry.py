"""Regression tests for the bounded ZARRY explanation correction retry."""
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "zarry-service"))
from app import create_app


class RetryModel:
    def __init__(self):
        self.calls = 0

    def create_chat_completion(self, **kwargs):
        self.calls += 1
        request = json.loads(kwargs["messages"][1]["content"].removeprefix("/no_think\n"))
        summary = (
            "Explanation-only: the supplied evidence is more than 50% certain."
            if self.calls == 1
            else "Explanation-only: Kitty's decision is preserved because the supplied timeframes conflict and entry confirmation remains unresolved."
        )
        result = {
            "symbol": request["symbol"],
            "decision": request["kitty_assessment"]["decision"],
            "summary": summary,
            "uncertainty": "The supplied context leaves entry confirmation unresolved.",
            "cited_fields": request["expected_fields"],
            "numeric_claims": [],
        }
        return {"choices": [{"message": {"content": json.dumps(result)}}]}


class ZarryValidationRetryTests(unittest.TestCase):
    def test_retries_once_after_ungrounded_numeric_text_without_relaxing_contract(self):
        with patch.dict(os.environ, {
            "ZARRY_API_KEY": "retry-test-secret",
            "ZARRY_MODEL_PATH": "/fake/model.gguf",
        }):
            model = RetryModel()
            client = TestClient(create_app(model_loader=lambda *args: model))
            with client:
                payload = {
                    "symbol": "BTCUSD",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": {
                        "trend_4h": "bullish",
                        "direction_1h": "bearish",
                        "entry_5m": "not_confirmed",
                    },
                    "expected_fields": ["trend_4h", "direction_1h", "entry_5m"],
                    "kitty_assessment": {"decision": "WAIT", "reason_codes": ["TIMEFRAME_CONFLICT"]},
                    "task": "explain",
                }
                response = client.post(
                    "/v1/explain",
                    json=payload,
                    headers={"Authorization": "Bearer retry-test-secret"},
                )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(model.calls, 2)
        result = response.json()
        self.assertEqual(result["symbol"], "BTCUSD")
        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["authority"], "KITTY_DETERMINISTIC_ENGINE")
        self.assertEqual(result["mode"], "explanation_only")
        self.assertEqual(result["cited_fields"], payload["expected_fields"])
        self.assertEqual(result["numeric_claims"], [])
        self.assertNotRegex(result["summary"] + result["uncertainty"], r"\d")


if __name__ == "__main__":
    unittest.main()
