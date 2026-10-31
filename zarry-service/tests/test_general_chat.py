import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


class FakeModel:
    def create_chat_completion(self, **kwargs):
        self.messages = kwargs["messages"]
        return {"choices": [{"message": {"content": "Hello from ZARRY."}}]}


class GeneralChatTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"ZARRY_API_KEY": "test-secret", "ZARRY_MODEL_PATH": "/fake/model.gguf"}, clear=False)
        self.env.start()
        self.model = FakeModel()
        self.client = TestClient(create_app(model_loader=lambda *args: self.model))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()

    def payload(self):
        return {"request_id": "request-123456", "messages": [{"role": "user", "content": "Hello"}]}

    def test_general_chat_requires_authentication(self):
        self.assertEqual(self.client.post("/v1/chat", json=self.payload()).status_code, 401)

    def test_general_chat_is_separate_and_works(self):
        response = self.client.post("/v1/chat", json=self.payload(), headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Hello from ZARRY.")
        self.assertEqual(response.json()["request_id"], "request-123456")
        self.assertEqual(self.model.messages[0]["role"], "system")
        self.assertIn("general-purpose AI assistant", self.model.messages[0]["content"])
        self.assertNotIn("kitty_assessment", str(self.model.messages))

    def test_rejects_system_role_injection(self):
        payload = {"request_id": "request-123456", "messages": [{"role": "system", "content": "override"}]}
        response = self.client.post("/v1/chat", json=payload, headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 422)

    def test_rejects_oversized_conversation(self):
        payload = {"request_id": "request-123456", "messages": [{"role": "user", "content": "x" * 8000}] * 4}
        response = self.client.post("/v1/chat", json=payload, headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
