"""Regression tests for OpenAI Realtime credential selection."""

import importlib
import os
import unittest
from unittest.mock import patch


class RealtimeVoiceConfigTests(unittest.TestCase):
    def test_standard_openai_key_enables_realtime_when_dedicated_key_missing(self):
        original = os.environ.copy()
        try:
            with patch.dict(os.environ, {
                "OPENAI_REALTIME_API_KEY": "",
                "OPENAI_API_KEY": "test-openai-key",
            }, clear=False):
                import realtime_voice
                importlib.reload(realtime_voice)
                self.assertEqual(realtime_voice.REALTIME_KEY, "test-openai-key")
        finally:
            with patch.dict(os.environ, original, clear=True):
                if "realtime_voice" in __import__("sys").modules:
                    importlib.reload(__import__("sys").modules["realtime_voice"])

    def test_dedicated_realtime_key_takes_precedence(self):
        original = os.environ.copy()
        try:
            with patch.dict(os.environ, {
                "OPENAI_REALTIME_API_KEY": "dedicated-realtime-key",
                "OPENAI_API_KEY": "standard-openai-key",
            }, clear=False):
                import realtime_voice
                importlib.reload(realtime_voice)
                self.assertEqual(realtime_voice.REALTIME_KEY, "dedicated-realtime-key")
        finally:
            with patch.dict(os.environ, original, clear=True):
                if "realtime_voice" in __import__("sys").modules:
                    importlib.reload(__import__("sys").modules["realtime_voice"])


if __name__ == "__main__":
    unittest.main()
