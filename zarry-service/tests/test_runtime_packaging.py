import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))
from app import create_app


class ChatModel:
    def __init__(self):
        self.messages = None

    def create_chat_completion(self, **kwargs):
        self.messages = kwargs["messages"]
        return {"choices": [{"message": {"content": "Hello. I can help with general questions."}}]}


class ZarryRuntimePackagingTests(unittest.TestCase):
    def test_general_chat_is_authenticated_and_uses_the_loaded_model(self):
        model = ChatModel()
        with patch.dict(os.environ, {"ZARRY_API_KEY": "test-secret", "ZARRY_MODEL_PATH": "/fake/model.gguf"}):
            with TestClient(create_app(model_loader=lambda *args: model)) as client:
                payload = {
                    "request_id": "general-chat-test-001",
                    "messages": [{"role": "user", "content": "Hello ZARRY"}],
                }
                self.assertEqual(client.post("/v1/chat", json=payload).status_code, 401)
                response = client.post(
                    "/v1/chat",
                    json=payload,
                    headers={"Authorization": "Bearer test-secret"},
                )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["request_id"], payload["request_id"])
        self.assertEqual(response.json()["response"], "Hello. I can help with general questions.")
        self.assertEqual(model.messages[-1], {"role": "user", "content": "Hello ZARRY"})
        self.assertIn("Kitty remains the sole trading authority", model.messages[0]["content"])

    def test_docker_image_copies_every_runtime_module(self):
        dockerfile = (SERVICE_DIR / "Dockerfile").read_text()
        copy_lines = [line for line in dockerfile.splitlines() if line.strip().startswith("COPY ")]
        copied = " ".join(copy_lines)
        for required in ("app.py", "contract.py", "general_chat.py", "download_model.py", "start.sh", "smoke_test.py"):
            with self.subTest(module=required):
                self.assertIn(required, copied, f"Docker image does not copy required runtime module: {required}")


if __name__ == "__main__":
    unittest.main()
