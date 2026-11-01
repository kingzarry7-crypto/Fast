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

    def test_admin_image_storage_test_logs_safe_failure_context(self):
        import logging
        class BrokenStorage:
            def verify_public_round_trip(self):
                raise RuntimeError("secret endpoint credentials must not be logged")
        gateway=FakeGateway()
        gateway.image_storage=BrokenStorage()
        app=FastAPI()
        app.include_router(create_general_router(lambda request: {"id":"u"}, gateway, admin_check=lambda request: ({"id":"admin-1"}, "admin")))
        with self.assertLogs("zarry_gateway.router", level="ERROR") as captured:
            response=TestClient(app, raise_server_exceptions=False).post("/api/assistant/admin/image-storage-test")
        self.assertEqual(response.status_code,502)
        self.assertIn("RuntimeError", "\n".join(captured.output))
        self.assertNotIn("secret endpoint credentials", "\n".join(captured.output))
        self.assertNotIn("secret endpoint credentials", response.text)

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
    def test_image_route_returns_only_strict_authenticated_image_contract(self):
        class ImageGateway(FakeGateway):
            def __init__(self):
                self.received = None
            def image(self, principal, payload):
                self.received = (principal, payload)
                return {
                    "request_id": payload.request_id,
                    "image_url": "https://images.example/generated.png",
                    "provider": "huggingface-fal-z-image-turbo",
                    "fallback_used": False,
                }
        gateway = ImageGateway()
        app = FastAPI()
        app.include_router(create_general_router(
            lambda request: {"id": "user-456"},
            gateway,
            enabled_check=lambda: True,
            image_enabled_check=lambda: True,
        ))
        response = TestClient(app).post(
            "/api/assistant/image",
            json={"prompt": "a lighthouse", "size": "1024x768"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["provider"], "huggingface-fal-z-image-turbo")
        self.assertEqual(body["image_url"], "https://images.example/generated.png")
        self.assertFalse(body["fallback_used"])
        self.assertNotIn("budget_reserved_usd", body)
        self.assertEqual(gateway.received[0].platform_user_id, "user-456")
        self.assertEqual(gateway.received[1].size, "1024x768")

    def test_image_route_requires_authenticated_web_session_when_enabled(self):
        app = FastAPI()
        def require_user(request):
            raise HTTPException(status_code=401, detail="Authentication required")
        app.include_router(create_general_router(
            require_user,
            FakeGateway(),
            enabled_check=lambda: True,
            image_enabled_check=lambda: True,
        ))
        response = TestClient(app).post(
            "/api/assistant/image", json={"prompt": "a lighthouse"}
        )
        self.assertEqual(response.status_code, 401)

    def test_oversized_request_rejected(self): self.assertEqual(self.client.post("/api/assistant/chat",json={"message":"x"*8001}).status_code,422)
if __name__ == "__main__": unittest.main()
