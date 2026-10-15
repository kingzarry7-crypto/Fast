import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from llm_client import _configured_providers, ask


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

    def test_huggingface_http_400_retries_with_fallback_model(self):
        class BadRequest(Exception):
            status_code = 400

        response = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content='{"files": []}'))
        ])
        client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=unittest.mock.Mock(
                side_effect=[BadRequest("model rejected"), response]
            ))
        ))
        with patch.dict(os.environ, {
            "AI_PROVIDER": "HF",
            "HF_TOKEN": "test-token",
            "HF_MODEL_ID": "KINGZARRY3/zarry-coder-model",
        }, clear=True), patch("llm_client.OpenAI", return_value=client):
            result = ask([{"role": "user", "content": "build a page"}], max_tokens=100)

        self.assertEqual(result, '{"files": []}')
        calls = client.chat.completions.create.call_args_list
        self.assertEqual(calls[0].kwargs["model"], "KINGZARRY3/zarry-coder-model")
        self.assertEqual(calls[1].kwargs["model"], "openai/gpt-oss-120b:cheapest")

    def test_huggingface_fallback_model_can_be_overridden(self):
        class BadRequest(Exception):
            status_code = 400

        response = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content="ok"))
        ])
        client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=unittest.mock.Mock(
                side_effect=[BadRequest("model rejected"), response]
            ))
        ))
        with patch.dict(os.environ, {
            "AI_PROVIDER": "HF",
            "HF_TOKEN": "test-token",
            "HF_MODEL_ID": "owner/custom-model",
            "HF_FALLBACK_MODEL_ID": "provider/available-model",
        }, clear=True), patch("llm_client.OpenAI", return_value=client):
            self.assertEqual(ask([{"role": "user", "content": "hello"}]), "ok")

        self.assertEqual(
            client.chat.completions.create.call_args_list[1].kwargs["model"],
            "provider/available-model",
        )


if __name__ == "__main__":
    unittest.main()
