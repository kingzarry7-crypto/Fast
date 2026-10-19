"""Regression tests for legacy Railway env names that contain trailing spaces."""
import importlib
import os
import unittest
from unittest.mock import patch

import ai_engine


class LegacyRailwayEnvNameTests(unittest.TestCase):
    def test_provider_keys_and_voice_model_accept_legacy_whitespace_names(self):
        legacy = {
            "GROQ_API_KEY ": "gsk-test-value",
            "ELEVENLABS_MODEL_ID ": "eleven-test-model",
            "FAL_KEY ": "fal-test-value",
        }
        # Isolate the import-time configuration and then restore it so these
        # values cannot leak into other tests in this process.
        try:
            with patch.dict(os.environ, legacy, clear=True):
                loaded = importlib.reload(ai_engine)
                self.assertEqual(loaded.GROQ_API_KEY, "gsk-test-value")
                self.assertEqual(loaded.ELEVENLABS_MODEL_ID, "eleven-test-model")
                self.assertEqual(loaded.FAL_KEY, "fal-test-value")
        finally:
            importlib.reload(ai_engine)


if __name__ == "__main__":
    unittest.main()
