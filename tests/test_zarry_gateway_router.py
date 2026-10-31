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
    def test_admin_connection_test_requires_admin(self):
        app=FastAPI()
        def deny_admin(request):
            raise HTTPException(status_code=403, detail="Admin access denied")
        app.include_router(create_general_router(lambda request: {"id":"u"}, FakeGateway(), admin_check=deny_admin))
        response=TestClient(app).post("/api/assistant/admin/connection-test")
        self.assertEqual(response.status_code,403)

    def test_admin_connection_test_calls_model_and_returns_safe_metadata(self):
        gateway=FakeGateway()
        app=FastAPI()
        app.include_router(create_general_router(lambda request: {"id":"u"}, gateway, admin_check=lambda request: ({"id":"admin-1"}, "admin@example.com")))
        response=TestClient(app).post("/api/assistant/admin/connection-test")
        self.assertEqual(response.status_code,200)
        body=response.json()
        self.assertEqual(body["status"],"ok")
        self.assertEqual(body["provider"],"local")
        self.assertNotIn("response",body)

    def test_admin_connection_test_fails_closed_on_provider_error(self):
        class BrokenGateway(FakeGateway):
            def chat(self, principal, payload):
                raise TimeoutError("secret provider details")
        app=FastAPI()
        app.include_router(create_general_router(lambda request: {"id":"u"}, BrokenGateway(), admin_check=lambda request: ({"id":"admin-1"}, "admin@example.com")))
        response=TestClient(app, raise_server_exceptions=False).post("/api/assistant/admin/connection-test")
        self.assertEqual(response.status_code,502)
        self.assertNotIn("secret provider details",response.text)

    def test_admin_image_storage_test_verifies_storage_without_generation(self):
        class Storage:
            def verify_public_round_trip(self):
                return {"status":"ok","public_host":"images.kingzarry.bid","upload":"ok","public_retrieval":"ok","cleanup":"ok"}
        class ImageProvider:
            storage=Storage()
            def generate(self, *args, **kwargs):
                raise AssertionError("diagnostic must not generate an image")
        gateway=FakeGateway()
        gateway.image_provider=ImageProvider()
        app=FastAPI()
        app.include_router(create_general_router(lambda request: {"id":"u"}, gateway, admin_check=lambda request: ({"id":"admin-1"}, "admin")))
        response=TestClient(app).post("/api/assistant/admin/image-storage-test")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["public_retrieval"],"ok")

    def test_admin_image_storage_test_rejects_non_admin(self):
        app=FastAPI()
        def deny_admin(request):
            raise HTTPException(status_code=403, detail="Admin access denied")
        app.include_router(create_general_router(lambda request: {"id":"u"}, FakeGateway(), admin_check=deny_admin))
        response=TestClient(app).post("/api/assistant/admin/image-storage-test")
        self.assertEqual(response.status_code,403)

    def test_admin_image_storage_test_fails_when_storage_is_missing(self):
        app=FastAPI()
        app.include_router(create_general_router(lambda request: {"id":"u"}, FakeGateway(), admin_check=lambda request: ({"id":"admin-1"}, "admin")))
        response=TestClient(app).post("/api/assistant/admin/image-storage-test")
        self.assertEqual(response.status_code,503)

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
        self.assertEqual(response.json()["detail"], "ZARRY image generation is not enabled")
    def test_image_provider_failure_returns_controlled_502(self):
        class BrokenImageGateway(FakeGateway):
            def image(self, principal, payload):
                raise RuntimeError("provider details must not escape")
        app=FastAPI(); app.include_router(create_general_router(lambda request:{"id":"u"},BrokenImageGateway(),enabled_check=lambda:True,image_enabled_check=lambda:True))
        response=TestClient(app, raise_server_exceptions=False).post("/api/assistant/image",json={"prompt":"a red kite"})
        self.assertEqual(response.status_code,502)
        self.assertEqual(response.json()["detail"],"ZARRY image request failed")
    def test_oversized_request_rejected(self): self.assertEqual(self.client.post("/api/assistant/chat",json={"message":"x"*8001}).status_code,422)
if __name__ == "__main__": unittest.main()
