import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from zarry_gateway.router import create_general_router


class SmokeGateTests(unittest.TestCase):
    def test_non_admin_cannot_reach_one_shot_image_smoke_endpoint(self):
        app = FastAPI()

        def deny_admin(request):
            raise HTTPException(status_code=403, detail="Admin access denied")

        app.include_router(
            create_general_router(
                lambda request: {"id": "user-1"},
                object(),
                admin_check=deny_admin,
            )
        )
        response = TestClient(app).post(
            "/api/assistant/admin/image-generation-smoke-test"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin access denied")

    def test_admin_can_read_sanitized_one_shot_image_smoke_diagnostic(self):
        app = FastAPI()
        row = {
            "status": "failed",
            "request_id": "safe-request-id",
            "provider": None,
            "error_type": "TypeError",
            "failure_stage": "provider_generate_other",
            "http_status_code": None,
            "completed_at": "2026-11-02T09:43:00+00:00",
        }

        class Cursor:
            def execute(self, query, params):
                self.query = query
                self.params = params

            def fetchone(self):
                return row

        @contextmanager
        def cursor_context():
            yield Cursor()

        fake_database = types.ModuleType("database")
        fake_database.get_db_cursor = cursor_context

        app.include_router(
            create_general_router(
                lambda request: {"id": "user-1"},
                object(),
                admin_check=lambda request: {"id": "admin-1"},
            )
        )
        with patch.dict(sys.modules, {"database": fake_database}):
            response = TestClient(app).get(
                "/api/assistant/admin/image-generation-smoke-status"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "failed")
        self.assertEqual(response.json()["error_type"], "TypeError")
        self.assertEqual(response.json()["failure_stage"], "provider_generate_other")
        self.assertNotIn("image_url", response.json())
        self.assertNotIn("prompt", response.json())

    def test_non_admin_cannot_read_one_shot_image_smoke_diagnostic(self):
        app = FastAPI()

        def deny_admin(request):
            raise HTTPException(status_code=403, detail="Admin access denied")

        app.include_router(
            create_general_router(
                lambda request: {"id": "user-1"},
                object(),
                admin_check=deny_admin,
            )
        )
        response = TestClient(app).get(
            "/api/assistant/admin/image-generation-smoke-status"
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
