import unittest
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from zarry_gateway.router import create_general_router
class FakeGateway:
    def chat(self, principal, payload): return {"request_id":str(payload.request_id),"conversation_id":str(payload.conversation_id or uuid4()),"response":"Hello from ZARRY","provider":"local"}
class GatewayRouterTests(unittest.TestCase):
    def setUp(self):
        self.authenticated=True
        def require_user(request):
            if not self.authenticated: raise HTTPException(status_code=401,detail="Authentication required")
            return {"id":"user-123"}
        self.app=FastAPI(); self.app.include_router(create_general_router(require_user,FakeGateway(),enabled_check=lambda:True)); self.client=TestClient(self.app)
    def test_chat_requires_authenticated_web_session(self):
        self.authenticated=False; self.assertEqual(self.client.post("/api/assistant/chat",json={"message":"hi"}).status_code,401)
    def test_chat_returns_contract(self):
        response=self.client.post("/api/assistant/chat",json={"message":"hi"}); self.assertEqual(response.status_code,200); self.assertEqual(response.json()["response"],"Hello from ZARRY")
    def test_chat_disabled_returns_503(self):
        app=FastAPI(); app.include_router(create_general_router(lambda request:{"id":"u"},FakeGateway(),enabled_check=lambda:False))
        self.assertEqual(TestClient(app).post("/api/assistant/chat",json={"message":"hi"}).status_code,503)
    def test_image_generation_stays_unavailable_without_configured_provider(self):
        response = self.client.post("/api/assistant/image", json={"prompt": "a red kite"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Image generation is unavailable")
    def test_image_provider_failure_returns_controlled_502(self):
        class BrokenImageGateway(FakeGateway):
            def image(self, principal, payload):
                raise RuntimeError("provider details must not escape")
        app=FastAPI(); app.include_router(create_general_router(lambda request:{"id":"u"},BrokenImageGateway(),enabled_check=lambda:True))
        response=TestClient(app, raise_server_exceptions=False).post("/api/assistant/image",json={"prompt":"a red kite"})
        self.assertEqual(response.status_code,502)
        self.assertEqual(response.json()["detail"],"ZARRY image request failed")
    def test_oversized_request_rejected(self): self.assertEqual(self.client.post("/api/assistant/chat",json={"message":"x"*8001}).status_code,422)
if __name__ == "__main__": unittest.main()
