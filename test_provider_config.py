"""Regression tests for independent OpenAI and OpenRouter configuration."""
import importlib
import os
import unittest
from unittest.mock import patch

import config


class ProviderConfigurationTests(unittest.TestCase):
    def _load_with_env(self, values):
        with patch.dict(os.environ, values, clear=True):
            loaded = importlib.reload(config)
            snapshot = (
                loaded.OPENAI_API_KEY,
                loaded.OPENAI_BASE_URL,
                loaded.OPENAI_MODEL,
                loaded.OPENROUTER_API_KEY,
                loaded.OPENROUTER_BASE_URL,
                loaded.OPENROUTER_MODEL,
            )
        importlib.reload(config)
        return snapshot

    def test_openai_and_openrouter_credentials_are_independent(self):
        values = self._load_with_env({
            "OPENAI_API_KEY": "openai-secret",
            "OPENAI_MODEL": "gpt-test",
            "OPENROUTER_API_KEY": "router-secret",
            "OPENROUTER_MODEL": "router/test",
        })
        self.assertEqual(values, (
            "openai-secret",
            "https://api.openai.com/v1",
            "gpt-test",
            "router-secret",
            "https://openrouter.ai/api/v1",
            "router/test",
        ))

    def test_openrouter_only_does_not_enable_openai(self):
        values = self._load_with_env({"OPENROUTER_API_KEY": "router-secret"})
        self.assertIsNone(values[0])
        self.assertEqual(values[1], "https://api.openai.com/v1")
        self.assertEqual(values[2], "gpt-5.4-nano")
        self.assertEqual(values[3], "router-secret")


if __name__ == "__main__":
    unittest.main()
