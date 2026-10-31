import os
import unittest
from unittest.mock import Mock, patch

import requests
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from zarry_api import create_router


class ZarryProxyTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ZARRY_ENABLED": "true",
            "ZARRY_SERVICE_URL": "https://zarry.internal",
            "ZARRY_API_KEY": "test-secret",
            "ZARRY_TIMEOUT_SECONDS": "9",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.upstream = Mock()
        self.authenticated = True

        def require_user(request):
            if not self.authenticated:
                raise HTTPException(status_code=401, detail="Authentication required")
            return {"id": "user-1"}

        self.require_user = require_user
        app = FastAPI()
        app.include_router(create_router(require_user, post=self.upstream))
        self.client = TestClient(app)
        self.payload = {
            "symbol": "BTCUSD",
            "timestamp": "2026-10-31T09:00:00Z",
            "context": {"close": 67000.0, "rsi_14": 54.2, "timeframe": "1h"},
            "kitty_assessment": {"decision": "NO TRADE", "reason_codes": ["edge_not_validated"]},
        }

    def valid_upstream(self, decision="NO TRADE"):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "symbol": "BTCUSD",
            "decision": decision,
            "summary": "This is an explanation-only account of Kitty's NO TRADE assessment.",
            "uncertainty": "The strategy has no validated net edge.",
            "cited_fields": ["rsi_14", "timeframe"],
            "numeric_claims": [54.2],
            "authority": "KITTY_DETERMINISTIC_ENGINE",
            "mode": "explanation_only",
        }
        self.upstream.return_value = response

    def test_proxy_forwards_authenticated_explanation_and_preserves_no_trade(self):
        self.valid_upstream()
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "NO TRADE")
        self.assertEqual(response.json()["mode"], "explanation_only")
        kwargs = self.upstream.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(kwargs["timeout"], 9)
        self.assertEqual(kwargs["json"]["kitty_assessment"]["decision"], "NO TRADE")

    def test_proxy_is_disabled_by_default(self):
        os.environ.pop("ZARRY_ENABLED", None)
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.upstream.assert_not_called()

    def test_proxy_requires_existing_web_session(self):
        self.authenticated = False
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 401)
        self.upstream.assert_not_called()

    def test_proxy_preserves_buy_and_sell_decisions(self):
        for decision in ("BUY", "SELL"):
            with self.subTest(decision=decision):
                payload = dict(self.payload)
                payload["kitty_assessment"] = {"decision": decision, "reason_codes": []}
                self.valid_upstream(decision=decision)
                response = self.client.post("/api/zarry/explain", json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["decision"], decision)

    def test_proxy_fails_closed_when_model_changes_kitty_decision(self):
        self.valid_upstream(decision="BUY")
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 502)
        self.upstream.assert_called_once()

    def test_proxy_maps_upstream_timeout_to_gateway_timeout(self):
        self.upstream.side_effect = requests.Timeout("slow model")
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 504)
        self.upstream.assert_called_once()

    def test_proxy_sanitizes_untrusted_request_id_before_forwarding(self):
        self.valid_upstream()
        response = self.client.post(
            "/api/zarry/explain",
            json=self.payload,
            headers={"X-Request-ID": "bad request id"},
        )
        self.assertEqual(response.status_code, 200)
        forwarded = self.upstream.call_args.kwargs["headers"]["X-Request-ID"]
        self.assertRegex(forwarded, r"^[0-9a-f-]{36}$")

    def test_proxy_retries_one_transient_connection_failure(self):
        self.valid_upstream()
        self.upstream.side_effect = [requests.ConnectionError("temporary"), self.upstream.return_value]
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.upstream.call_count, 2)

    def test_proxy_rejects_stale_market_context(self):
        payload = dict(self.payload)
        payload["timestamp"] = "2020-01-01T00:00:00Z"
        response = self.client.post("/api/zarry/explain", json=payload)
        self.assertEqual(response.status_code, 422)
        self.upstream.assert_not_called()

    def test_proxy_rejects_timezone_free_timestamp(self):
        payload = dict(self.payload)
        payload["timestamp"] = "2026-10-31T09:00:00"
        response = self.client.post("/api/zarry/explain", json=payload)
        self.assertEqual(response.status_code, 422)
        self.upstream.assert_not_called()

    def test_proxy_enforces_per_user_rate_limit(self):
        os.environ["ZARRY_MAX_REQUESTS_PER_MINUTE"] = "2"
        self.valid_upstream()
        self.assertEqual(self.client.post("/api/zarry/explain", json=self.payload).status_code, 200)
        self.assertEqual(self.client.post("/api/zarry/explain", json=self.payload).status_code, 200)
        limited = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.headers["Retry-After"], "60")
        self.assertEqual(self.upstream.call_count, 2)

    def test_proxy_rejects_plain_http_outside_railway_private_network(self):
        os.environ["ZARRY_SERVICE_URL"] = "http://untrusted.example"
        self.valid_upstream()
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.upstream.assert_not_called()

    def test_proxy_supports_existing_zarry_api_url_variable(self):
        os.environ.pop("ZARRY_SERVICE_URL", None)
        os.environ["ZARRY_API_URL"] = "https://zarry.internal"
        self.valid_upstream()
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.upstream.call_args.args[0], "https://zarry.internal/v1/explain")

    def test_proxy_rejects_unconfigured_service_credentials(self):
        os.environ.pop("ZARRY_API_KEY", None)
        response = self.client.post("/api/zarry/explain", json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.upstream.assert_not_called()


if __name__ == "__main__":
    unittest.main()
