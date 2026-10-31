import tempfile
import unittest
from pathlib import Path

from download_model import resolve_model_file


class DownloadModelTests(unittest.TestCase):
    def test_resolves_the_single_matching_quantized_model(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "SmolLM3-3B-Q4_K_M.gguf"
            expected.touch()
            (Path(directory) / "README.md").touch()
            self.assertEqual(resolve_model_file(directory), expected)

    def test_fails_closed_when_model_file_is_missing_or_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                resolve_model_file(directory)
            (Path(directory) / "one-Q4_K_M.gguf").touch()
            (Path(directory) / "two-Q4_K_M.gguf").touch()
            with self.assertRaises(RuntimeError):
                resolve_model_file(directory)


if __name__ == "__main__":
    unittest.main()
