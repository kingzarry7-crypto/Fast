import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_model import (
    DEFAULT_PATTERN,
    DEFAULT_REPO,
    DEFAULT_REVISION,
    cache_diagnostics,
    clear_incomplete_model_downloads,
    clear_obsolete_model_cache,
    resolve_cache_dir,
    resolve_model_file,
)


class DownloadModelTests(unittest.TestCase):
    def test_default_model_is_pinned_qwen3_17b_q4(self):
        self.assertEqual(DEFAULT_REPO, "unsloth/Qwen3-1.7B-GGUF")
        self.assertEqual(DEFAULT_PATTERN, "Qwen3-1.7B-Q4_K_M.gguf")
        self.assertEqual(
            DEFAULT_REVISION,
            "b2d17796e6fd93c353a0415a3abd8b7f801701de",
        )

    def test_resolves_the_exact_qwen_quantized_model(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "Qwen3-1.7B-Q4_K_M.gguf"
            expected.touch()
            (Path(directory) / "README.md").touch()
            self.assertEqual(resolve_model_file(directory), expected)

    def test_fails_closed_when_model_file_is_missing_or_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                resolve_model_file(directory)
            (Path(directory) / "Qwen3-1.7B-Q4_K_M.gguf").touch()
            (Path(directory) / "copy-Qwen3-1.7B-Q4_K_M.gguf").touch()
            with self.assertRaises(RuntimeError):
                resolve_model_file(directory, "*Q4_K_M.gguf")

    def test_cache_diagnostics_report_free_space_and_model_cache_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "models--unsloth--SmolLM3-3B-GGUF").mkdir()
            diagnostics = cache_diagnostics(tmp)
            self.assertGreaterEqual(diagnostics["free_bytes"], 0)
            self.assertTrue(diagnostics["smol_cache_present"])
            self.assertFalse(diagnostics["qwen_cache_present"])

    def test_resolves_cache_from_railway_volume_when_hf_home_is_missing(self):
        self.assertEqual(
            resolve_cache_dir({"RAILWAY_VOLUME_MOUNT_PATH": "/models"}),
            Path("/models/hf-cache"),
        )

    def test_prefers_explicit_hf_home(self):
        self.assertEqual(
            resolve_cache_dir({
                "HF_HOME": "/custom/hf-cache",
                "RAILWAY_VOLUME_MOUNT_PATH": "/models",
            }),
            Path("/custom/hf-cache"),
        )

    def test_removes_only_incomplete_files_from_selected_model_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            blobs = Path(tmp) / "models--unsloth--Qwen3-1.7B-GGUF" / "blobs"
            blobs.mkdir(parents=True)
            partial = blobs / "incomplete.download.incomplete"
            complete = blobs / "complete.gguf"
            partial.write_text("partial")
            complete.write_text("complete")
            self.assertEqual(
                clear_incomplete_model_downloads(tmp, DEFAULT_REPO),
                1,
            )
            self.assertFalse(partial.exists())
            self.assertTrue(complete.exists())

    def test_removes_only_obsolete_smollm3_cache_when_switching_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "models--unsloth--SmolLM3-3B-GGUF"
            keep = Path(tmp) / "models--unsloth--Qwen3-1.7B-GGUF"
            old.mkdir(parents=True)
            keep.mkdir(parents=True)
            (old / "old.gguf").write_text("old")
            (keep / "qwen.gguf").write_text("qwen")

            removed = clear_obsolete_model_cache(tmp, DEFAULT_REPO)

            self.assertTrue(removed)
            self.assertFalse(old.exists())
            self.assertTrue((keep / "qwen.gguf").exists())

    def test_removes_legacy_nested_hub_cache_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "hub" / "models--unsloth--SmolLM3-3B-GGUF"
            old.mkdir(parents=True)
            self.assertTrue(clear_obsolete_model_cache(tmp, DEFAULT_REPO))
            self.assertFalse(old.exists())

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
