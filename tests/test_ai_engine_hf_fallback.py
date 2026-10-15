import unittest
from unittest.mock import Mock, patch

import ai_engine


class HuggingFaceFallbackTests(unittest.TestCase):
    def test_invalid_custom_model_retries_configured_fallback(self):
        engine = ai_engine.AIEngine.__new__(ai_engine.AIEngine)
        engine._build_openai_messages = Mock(return_value=[{"role": "user", "content": "hello"}])
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "fallback answer"}}]
        }
        engine._request_with_retry = Mock(
            side_effect=[RuntimeError("HTTP 400: requested model not found"), response]
        )

        with patch.object(ai_engine, "HF_TOKEN", "test-token"), \
             patch.object(ai_engine, "HF_MODEL_ID", "owner/missing-model"), \
             patch.object(ai_engine, "HF_FALLBACK_MODEL_ID", "openai/gpt-oss-120b:cheapest"):
            answer = engine._huggingface("hello", [], None)

        self.assertEqual(answer, "fallback answer")
        self.assertEqual(engine._request_with_retry.call_count, 2)
        first_payload = engine._request_with_retry.call_args_list[0].args[2]
        fallback_payload = engine._request_with_retry.call_args_list[1].args[2]
        self.assertEqual(first_payload["model"], "owner/missing-model")
        self.assertEqual(fallback_payload["model"], "openai/gpt-oss-120b:cheapest")

    def test_non_400_error_does_not_retry_with_fallback(self):
        engine = ai_engine.AIEngine.__new__(ai_engine.AIEngine)
        engine._build_openai_messages = Mock(return_value=[{"role": "user", "content": "hello"}])
        engine._request_with_retry = Mock(side_effect=RuntimeError("HTTP 503: unavailable"))

        with patch.object(ai_engine, "HF_TOKEN", "test-token"), \
             patch.object(ai_engine, "HF_MODEL_ID", "owner/model"), \
             patch.object(ai_engine, "HF_FALLBACK_MODEL_ID", "openai/gpt-oss-120b:cheapest"):
            with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
                engine._huggingface("hello", [], None)

        self.assertEqual(engine._request_with_retry.call_count, 1)


if __name__ == "__main__":
    unittest.main()
