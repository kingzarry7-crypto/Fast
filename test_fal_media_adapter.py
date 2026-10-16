"""Regression tests for FAL media routing and provider credential classification."""
import os
import sys
import types
import unittest
from unittest.mock import patch

import ai_engine
import provider_registry


class FalMediaAdapterTests(unittest.TestCase):
    def test_image_generation_returns_valid_image_url(self):
        fake_client = types.SimpleNamespace(
            subscribe=lambda model, arguments, with_logs=False: {
                "images": [{"url": "https://cdn.example.test/generated.png"}]
            }
        )
        with patch.object(ai_engine, "FAL_KEY", "test-key"), patch.dict(
            sys.modules, {"fal_client": fake_client}
        ):
            result = ai_engine.fal_generate_image("a blue bird")

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://cdn.example.test/generated.png")
        self.assertEqual(result["provider"], "fal")

    def test_missing_fal_key_is_reported_without_calling_provider(self):
        with patch.object(ai_engine, "FAL_KEY", ""):
            result = ai_engine.fal_generate_image("a blue bird")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "fal_not_configured")

    def test_edit_rejects_non_http_image_url(self):
        with patch.object(ai_engine, "FAL_KEY", "test-key"):
            result = ai_engine.fal_edit_image("make it brighter", "file:///etc/passwd")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "invalid_image_url")

    def test_malformed_fal_response_is_not_reported_as_success(self):
        fake_client = types.SimpleNamespace(
            subscribe=lambda model, arguments, with_logs=False: {"images": []}
        )
        with patch.object(ai_engine, "FAL_KEY", "test-key"), patch.dict(
            sys.modules, {"fal_client": fake_client}
        ):
            result = ai_engine.fal_generate_image("a blue bird")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "fal_response_missing_image_url")


class ProviderCredentialClassificationTests(unittest.TestCase):
    def test_groq_key_does_not_make_xai_appear_configured(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "groq-test-key"}, clear=True):
            snapshot = provider_registry.snapshot()

        ids = {item["id"] for item in snapshot["providers"]}
        self.assertIn("groq", ids)
        self.assertNotIn("xai", ids)

    def test_xai_key_is_reported_as_native_integration(self):
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test-key"}, clear=True):
            snapshot = provider_registry.snapshot()

        xai = next(item for item in snapshot["providers"] if item["id"] == "xai")
        self.assertEqual(xai["adapter"], "native")
        self.assertFalse(xai["needs_code"])


if __name__ == "__main__":
    unittest.main()
