import os
import unittest
from unittest.mock import patch

from llm_client import _configured_providers


class ConfiguredProviderTests(unittest.TestCase):
    def test_cloudflare_token_is_supported_when_pinned(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "CLOUDFLARE",
            "CLOUDFLARE_AI_TOKEN": "test-token",
            "CLOUDFLARE_AI_URL": "https://example.workers.dev/v1/chat/completions",
            "CLOUDFLARE_AI_MODEL": "test-model",
        }, clear=True):
            providers = _configured_providers()
        self.assertEqual(providers, [(
            "cloudflare", "test-token", "https://example.workers.dev/v1", "test-model"
        )])

    def test_huggingface_alias_is_supported(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "HF",
            "HF_TOKEN": "test-token",
            "HF_INFERENCE_URL": "https://router.huggingface.co/v1/chat/completions",
            "HF_MODEL_ID": "owner/model",
        }, clear=True):
            providers = _configured_providers()
        self.assertEqual(providers, [(
            "huggingface", "test-token", "https://router.huggingface.co/v1", "owner/model"
        )])

    def test_auto_prefers_paid_openai_and_falls_back_to_cloudflare(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "AUTO",
            "OPENAI_API_KEY": "openai-test",
            "CLOUDFLARE_AI_TOKEN": "cf-test",
        }, clear=True):
            providers = _configured_providers()
        self.assertEqual([item[0] for item in providers], ["openai", "cloudflare"])

    def test_pinned_unconfigured_provider_is_explicit(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "DEEPSEEK"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DEEPSEEK"):
                _configured_providers()


if __name__ == "__main__":
    unittest.main()
