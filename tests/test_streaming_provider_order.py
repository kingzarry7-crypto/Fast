"""Regression tests for the streaming chat provider fallback order."""
import os
import unittest
from unittest.mock import patch

import ai_engine
import streaming_chat


class StreamingProviderOrderTests(unittest.TestCase):
    def test_streaming_order_matches_normal_chat_fallback_priority(self):
        env = {"AI_PROVIDER": "AUTO", "ZARRY_API_URL": "https://zarry.example/generate"}
        with patch.dict(os.environ, env, clear=False), \\
             patch.object(ai_engine, "HF_TOKEN", "hf-test"), \\
             patch.object(ai_engine, "CLOUDFLARE_AI_TOKEN", "cf-test"), \\
             patch.object(ai_engine, "OPENAI_API_KEY", "openai-test"), \\
             patch.object(ai_engine, "GEMINI_API_KEY", "gemini-test"), \\
             patch.object(streaming_chat, "_GROQ_KEY", "groq-test"), \\
             patch.object(streaming_chat, "_OPENROUTER_KEY", "router-test"), \\
             patch.object(streaming_chat, "_CHUTES_KEY", "chutes-test"):
            names = [name for name, _stream in streaming_chat._provider_streams([])]

        self.assertEqual(
            names,
            ["zarry", "openai", "groq", "gemini", "chutes", "openrouter", "cloudflare", "huggingface"],
        )

    def test_explicit_provider_is_first_but_fallbacks_remain_available(self):
        env = {"AI_PROVIDER": "openrouter", "ZARRY_API_URL": ""}
        with patch.dict(os.environ, env, clear=False), \\
             patch.object(ai_engine, "HF_TOKEN", "hf-test"), \\
             patch.object(ai_engine, "CLOUDFLARE_AI_TOKEN", "cf-test"), \\
             patch.object(ai_engine, "OPENAI_API_KEY", "openai-test"), \\
             patch.object(ai_engine, "GEMINI_API_KEY", "gemini-test"), \\
             patch.object(streaming_chat, "_GROQ_KEY", "groq-test"), \\
             patch.object(streaming_chat, "_OPENROUTER_KEY", "router-test"), \\
             patch.object(streaming_chat, "_CHUTES_KEY", "chutes-test"):
            names = [name for name, _stream in streaming_chat._provider_streams([])]

        self.assertEqual(names[0], "openrouter")
        self.assertIn("openai", names[1:])
        self.assertIn("groq", names[1:])


if __name__ == "__main__":
    unittest.main()
