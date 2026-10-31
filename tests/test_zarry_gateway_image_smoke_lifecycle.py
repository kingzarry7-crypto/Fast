import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from zarry_gateway.router import create_general_router


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.last_sql = ""

    def execute(self, sql, params=None):
        self.last_sql = sql
        if "INSERT INTO zarry_image_smoke_test_lock" in sql:
            if self.state["claimed"]:
                self.state["insert_won"] = False
            else:
                self.state["claimed"] = True
                self.state["insert_won"] = True
                self.state["request_id"] = params[0]

        if "UPDATE zarry_image_smoke_test_lock" in sql:
            self.state["outcomes"].append(tuple(params[i] if i < len(params) else None for i in range(7)))

    def fetchone(self):
        if "INSERT INTO zarry_image_smoke_test_lock" in self.last_sql and self.state.get("insert_won"):
            self.state["insert_won"] = False
            return {"lock_key": "replicate-one-shot-v1"}
        return None


class FakeStorage:
    public_host = "images.example.test"


class FakeImageProvider:
    storage = FakeStorage()

    def __init__(self):
        self.calls = []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {
            "provider": "replicate-test",
            "image_url": "https://images.example.test/smoke.png",
        }


class SmokeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.state = {"claimed": False, "outcomes": []}
        self.provider = FakeImageProvider()
        self.gateway = type("Gateway", (), {})()
        self.gateway.image_provider = self.provider

        @contextmanager
        def cursor_context():
            yield FakeCursor(self.state)

        self.cursor_context = cursor_context
        self.app = FastAPI()
        self.app.include_router(
            create_general_router(
                lambda request: {"id": "test-user"},
                self.gateway,
                admin_check=lambda request: ({"id": "admin"}, "admin"),
            )
        )
        self.client = TestClient(self.app)

    def test_success_records_outcome_and_returns_verified_public_image(self):
        import requests
        class PublicResponse:
            content = bytes([0x89]) + b"PNG\r\n\x1a\nimage-bytes"
            def raise_for_status(self):
                return None

        with patch("database.get_db_cursor", self.cursor_context), patch.object(
            requests, "get", return_value=PublicResponse()
        ):
            response = self.client.post("/api/assistant/admin/image-generation-smoke-test")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["public_retrieval"], "verified")
        self.assertFalse(body["public_generation_enabled"])
        self.assertEqual(len(self.provider.calls), 1)
        self.assertEqual(self.state["outcomes"][-1][0], "succeeded")
        self.assertEqual(self.state["outcomes"][-1][2], "replicate-test")
        self.assertEqual(self.state["outcomes"][-1][3], "https://images.example.test/smoke.png")
        self.assertEqual(str(self.provider.calls[0][1]["request_id"]), body["request_id"])

    def test_already_claimed_lock_rejects_before_provider_call(self):
        self.state["claimed"] = True
        with patch("database.get_db_cursor", self.cursor_context):
            response = self.client.post("/api/assistant/admin/image-generation-smoke-test")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.provider.calls, [])

    def test_provider_failure_is_recorded_and_lock_stays_consumed(self):
        import requests
        class BrokenProvider(FakeImageProvider):
            def generate(self, prompt, **kwargs):
                raise TimeoutError("private provider details")

        self.gateway.image_provider = BrokenProvider()
        with patch("database.get_db_cursor", self.cursor_context), patch.object(
            requests, "get"
        ) as public_get:
            response = self.client.post(
                "/api/assistant/admin/image-generation-smoke-test",
                headers={"content-type": "application/json"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private provider details", response.text)
        self.assertEqual(self.state["outcomes"][-1][0], "failed")
        self.assertEqual(self.state["outcomes"][-1][4], "TimeoutError")
        self.assertEqual(self.state["outcomes"][-1][5], "provider_generate_other")
        self.assertIsNone(self.state["outcomes"][-1][6])
        self.assertFalse(public_get.called)


if __name__ == "__main__":
    unittest.main()
