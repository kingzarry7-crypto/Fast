import unittest
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


if __name__ == "__main__":
    unittest.main()
