import tempfile
import unittest
from pathlib import Path

from download_model import (
    DEFAULT_PATTERN,
    DEFAULT_REPO,
    DEFAULT_REVISION,
    clear_obsolete_model_cache,
)


class QwenModelSelectionTests(unittest.TestCase):
    def test_default_model_is_pinned_qwen3_17b_q4(self):
        self.assertEqual(DEFAULT_REPO, "unsloth/Qwen3-1.7B-GGUF")
        self.assertEqual(DEFAULT_PATTERN, "Qwen3-1.7B-Q4_K_M.gguf")
        self.assertEqual(
            DEFAULT_REVISION,
            "b2d17796e6fd93c353a0415a3abd8b7f801701de",
        )

    def test_removes_only_obsolete_smollm3_cache_when_switching_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            old = hub / "models--unsloth--SmolLM3-3B-GGUF"
            keep = hub / "models--unsloth--Qwen3-1.7B-GGUF"
            old.mkdir(parents=True)
            keep.mkdir(parents=True)
            (old / "old.gguf").write_text("old")
            (keep / "qwen.gguf").write_text("qwen")

            removed = clear_obsolete_model_cache(tmp, DEFAULT_REPO)

            self.assertTrue(removed)
            self.assertFalse(old.exists())
            self.assertTrue((keep / "qwen.gguf").exists())

    def test_does_not_remove_cache_when_smollm3_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "hub" / "models--unsloth--SmolLM3-3B-GGUF"
            old.mkdir(parents=True)
            self.assertFalse(
                clear_obsolete_model_cache(tmp, "unsloth/SmolLM3-3B-GGUF")
            )
            self.assertTrue(old.exists())


if __name__ == "__main__":
    unittest.main()
