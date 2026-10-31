import unittest
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from zarry_gateway.router import create_general_router


class FakeGateway:
    def chat(self, principal, payload):
        return {
            "request_id": str(payload.request_id),
            "conversation_id": str(payload.conversation_id or uuid4()),
            "response": "Hello from ZARRY", "provider": "local",
        }


class GatewayRouterTests(unittest.TestCase):
    def setUp(self):
        self.authenticated = True
        def require_user(request):
            if not self.authenticated:
                raise HTTPException(status_code=401, detail="Authentication required")
            return {"id": "user-123"}
        self.app = FastAPI()
        self.app.include_router(create_general_router(require_user, FakeGateway(), enabled_check=lambda: True))
        self.client = TestClient(self.app)

    def test_chat_requires_authenticated_web_session(self):
        self.authenticated = False
        response = self.client.post("/api/assistant/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 401)

    def test_chat_passes_authenticated_principal_and_returns_contract(self):
        response = self.client.post("/api/assistant/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Hello from ZARRY")

    def test_chat_is_disabled_by_default(self):
        app = FastAPI()
        app.include_router(create_general_router(lambda request: {"id": "u"}, FakeGateway(), enabled_check=lambda: False))
        response = TestClient(app).post("/api/assistant/chat", json={"message": "hi"})
        self.assertEqual(response.status_code, 503)

    def test_invalid_request_is_rejected_before_gateway(self):
        response = self.client.post("/api/assistant/chat", json={"message": "x" * 8001})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
