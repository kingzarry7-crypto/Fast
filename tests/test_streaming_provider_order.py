"""Regression tests for the streaming chat provider fallback order."""
import os
import unittest
from unittest.mock import patch

import ai_engine
import streaming_chat


class StreamingProviderOrderTests(unittest.TestCase):
    def _configured_providers(self, preferred):
        env = {"AI_PROVIDER": preferred, "ZARRY_API_URL": "https://zarry.example/generate" if preferred == "AUTO" else ""}
        with patch.dict(os.environ, env, clear=False):
            with patch.multiple(
                ai_engine,
                HF_TOKEN="hf-test",
                HF_MODEL_ID="openai/gpt-oss-120b:cheapest",
                HF_FALLBACK_MODEL_ID="openai/gpt-oss-120b:cheapest",
                CLOUDFLARE_AI_TOKEN="cf-test",
                OPENAI_API_KEY="openai-test",
                GEMINI_API_KEY="gemini-test",
            ):
                with patch.multiple(
                    streaming_chat,
                    _GROQ_KEY="groq-test",
                    _OPENROUTER_KEY="router-test",
                    _CHUTES_KEY="chutes-test",
                ):
                    return [name for name, _stream in streaming_chat._provider_streams([])]

    def test_streaming_order_matches_normal_chat_fallback_priority(self):
        self.assertEqual(
            self._configured_providers("AUTO"),
            ["zarry", "openai", "groq", "gemini", "chutes", "openrouter", "cloudflare", "huggingface"],
        )

    def test_explicit_provider_is_first_but_fallbacks_remain_available(self):
        names = self._configured_providers("openrouter")
        self.assertEqual(names[0], "openrouter")
        self.assertIn("openai", names[1:])
        self.assertIn("groq", names[1:])


if __name__ == "__main__":
    unittest.main()
