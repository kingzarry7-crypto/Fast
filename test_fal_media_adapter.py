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

    def test_video_generation_returns_valid_video_url(self):
        fake_client = types.SimpleNamespace(
            subscribe=lambda model, arguments, with_logs=False: {
                "video": {"url": "https://cdn.example.test/generated.mp4"}
            }
        )
        with patch.object(ai_engine, "FAL_KEY", "test-key"), patch.dict(
            sys.modules, {"fal_client": fake_client}
        ):
            result = ai_engine.fal_generate_video("a river flowing through a forest")

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://cdn.example.test/generated.mp4")
        self.assertEqual(result["provider"], "fal")

    def test_missing_fal_key_does_not_call_video_provider(self):
        fake_client = types.SimpleNamespace(
            subscribe=lambda *args, **kwargs: self.fail("fal client must not be called")
        )
        with patch.object(ai_engine, "FAL_KEY", "") , patch.dict(
            sys.modules, {"fal_client": fake_client}
        ):
            result = ai_engine.fal_generate_video("a river flowing through a forest")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "fal_not_configured")

    def test_malformed_fal_video_response_is_not_reported_as_success(self):
        fake_client = types.SimpleNamespace(
            subscribe=lambda model, arguments, with_logs=False: {"video": {}}
        )
        with patch.object(ai_engine, "FAL_KEY", "test-key"), patch.dict(
            sys.modules, {"fal_client": fake_client}
        ):
            result = ai_engine.fal_generate_video("a river flowing through a forest")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "fal_response_missing_video_url")

    def test_shared_media_router_uses_fal_when_video_providers_are_unavailable(self):
        engine = ai_engine.AIEngine.__new__(ai_engine.AIEngine)
        engine._save_memory = lambda *args, **kwargs: None
        with patch.object(ai_engine, "AGNES_API_KEY", ""), patch.object(
            ai_engine, "ACEDATA_API_KEY", ""
        ), patch.object(ai_engine, "FAL_KEY", "test-key"), patch.object(
            ai_engine, "fal_generate_video",
            return_value={
                "success": True,
                "url": "https://cdn.example.test/fallback.mp4",
                "model": "fal-test-model",
                "provider": "fal",
            },
        ) as generate:
            reply = engine._route_media_request(
                "user-1",
                "make a video of a forest",
                {"kind": "video", "prompt": "a forest moving in the wind"},
                None,
            )

        self.assertIn("https://cdn.example.test/fallback.mp4", reply)
        self.assertIn("(fal)", reply)
        generate.assert_called_once()

    def test_shared_media_router_uses_fal_when_image_providers_are_unavailable(self):
        engine = ai_engine.AIEngine.__new__(ai_engine.AIEngine)
        engine._save_memory = lambda *args, **kwargs: None
        with patch.object(ai_engine, "AGNES_API_KEY", ""), patch.object(
            ai_engine, "ACEDATA_API_KEY", ""
        ), patch.object(ai_engine, "FAL_KEY", "test-key"), patch.object(
            ai_engine, "fal_generate_image",
            return_value={
                "success": True,
                "url": "https://cdn.example.test/fallback.png",
                "model": "fal-test-model",
                "provider": "fal",
            },
        ) as generate:
            reply = engine._route_media_request(
                "user-1",
                "make an image of a forest",
                {"kind": "image", "prompt": "a forest"},
                None,
            )

        self.assertIn("https://cdn.example.test/fallback.png", reply)
        self.assertIn("(fal)", reply)
        generate.assert_called_once()


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

    def test_native_provider_report_does_not_claim_live_health(self):
        report = provider_registry.format_admin_report({
            "providers": [{
                "id": "groq",
                "name": "Groq",
                "adapter": "native",
                "skills": ["text_ai"],
                "needs_code": False,
                "what_it_can_do": "text_ai",
                "integration_hint": "Test model access with a live request.",
            }],
            "configured_count": 1,
            "service_credentials": [],
            "unknown_env_keys": [],
            "web_research": {},
        })

        self.assertIn("live authentication", report)
        self.assertNotIn("ready through existing integration", report)


if __name__ == "__main__":
    unittest.main()
