import json
import sys
import types
import unittest
from unittest.mock import patch

import engineering_executor


class EngineeringExecutorTests(unittest.TestCase):
    def test_rejects_path_traversal_and_secret_directories(self):
        for path in ("../app.py", "/tmp/app.py", "C:/app.py", ".env/keys.json", "node_modules/pkg.js"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    engineering_executor._safe_path(path)

    def test_rejects_unsupported_extensions(self):
        with self.assertRaises(ValueError):
            engineering_executor._safe_path("run.sh")

    def test_project_generation_does_not_execute_generated_code(self):
        response = json.dumps({
            "summary": "Minimal page",
            "files": [{"path": "index.html", "content": "<html><body>Hello</body></html>"}],
        })
        fake = types.ModuleType("llm_client")
        fake.ask = lambda *args, **kwargs: response
        with patch.dict(sys.modules, {"llm_client": fake}):
            result = engineering_executor.generate_project("Build a minimal page")
        self.assertTrue(result["success"])
        self.assertEqual(result["file_count"], 1)
        self.assertTrue(any(
            item.get("name") == "Generated code execution" and item.get("status") == "not_run"
            for item in result["checks"]
        ))

    def test_rejects_duplicate_paths(self):
        response = json.dumps({
            "files": [
                {"path": "index.html", "content": "<html></html>"},
                {"path": "index.html", "content": "<html>duplicate</html>"},
            ],
        })
        fake = types.ModuleType("llm_client")
        fake.ask = lambda *args, **kwargs: response
        with patch.dict(sys.modules, {"llm_client": fake}):
            with self.assertRaisesRegex(ValueError, "Duplicate generated path"):
                engineering_executor.generate_project("Build a minimal page")


if __name__ == "__main__":
    unittest.main()
