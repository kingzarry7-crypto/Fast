import json
import sys
import types
import unittest
from unittest.mock import patch

import engineering_executor


class EngineeringExecutorTests(unittest.TestCase):
    def _generate(self, payload):
        fake = types.ModuleType("llm_client")
        fake.ask = lambda *args, **kwargs: json.dumps(payload)
        with patch.dict(sys.modules, {"llm_client": fake}):
            return engineering_executor.generate_project("Build a minimal page")

    def test_rejects_path_traversal_and_secret_directories(self):
        for path in ("../app.py", "/tmp/app.py", "C:/app.py", ".env/keys.json", "node_modules/pkg.js"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    engineering_executor._safe_path(path)

    def test_rejects_unsupported_extensions(self):
        with self.assertRaises(ValueError):
            engineering_executor._safe_path("run.sh")

    def test_project_generation_does_not_execute_generated_code(self):
        result = self._generate({
            "summary": "Minimal page",
            "files": [{"path": "index.html", "content": "<html><body>Hello</body></html>"}],
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["execution_status"], "generated_not_executed")
        self.assertTrue(any(
            item.get("name") == "Isolated execution status" and item.get("status") == "not_run"
            for item in result["checks"]
        ))


    def test_uses_remote_isolated_runner_for_python_validation(self):
        fake_llm = types.ModuleType("llm_client")
        fake_llm.ask = lambda *args, **kwargs: json.dumps({
            "summary": "Python project",
            "files": [{"path": "main.py", "content": "print('safe')"}],
        })
        fake_runner = types.ModuleType("isolated_code_runner")
        fake_runner.RunnerUnavailable = type("RunnerUnavailable", (RuntimeError,), {})
        calls = []
        fake_runner.execute_project = lambda files, **kwargs: (
            calls.append((files, kwargs)) or {
                "status": "passed", "exit_code": 0, "stdout": "compiled",
                "stderr": "", "runner": "remote_isolated", "execution": "executed",
            }
        )
        with patch.dict(sys.modules, {"llm_client": fake_llm, "isolated_code_runner": fake_runner}):
            result = engineering_executor.generate_project("Build a Python project")
        self.assertEqual(result["execution_status"], "validated")
        self.assertEqual(calls[0][1]["command"], ["python", "-m", "compileall", "-q", "."])
        self.assertTrue(any(item["name"] == "Isolated Python compile check" and item["status"] == "passed" for item in result["checks"]))

    def test_runs_npm_build_for_javascript_projects_with_build_script(self):
        fake_llm = types.ModuleType("llm_client")
        fake_llm.ask = lambda *args, **kwargs: json.dumps({
            "summary": "Web project",
            "files": [
                {"path": "package.json", "content": '{"scripts":{"build":"next build"},"dependencies":{"next":"15.5.27"}}'},
                {"path": "index.html", "content": "<html><body>Preview</body></html>"},
                {"path": "index.js", "content": "console.log('hello')"},
            ],
        })
        fake_runner = types.ModuleType("isolated_code_runner")
        fake_runner.RunnerUnavailable = type("RunnerUnavailable", (RuntimeError,), {})
        calls = []
        fake_runner.execute_project = lambda files, **kwargs: (
            calls.append((files, kwargs)) or {
                "status": "passed", "exit_code": 0, "stdout": "build successful",
                "stderr": "", "runner": "remote_isolated", "execution": "executed",
            }
        )
        with patch.dict(sys.modules, {"llm_client": fake_llm, "isolated_code_runner": fake_runner}):
            result = engineering_executor.generate_project("Build a web app")
        self.assertEqual(result["execution_status"], "validated")
        self.assertEqual(calls[0][1]["commands"], [
            ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"],
            ["npm", "run", "build"],
        ])
        self.assertTrue(any(item["name"] == "Isolated JavaScript build" and item["status"] == "passed" for item in result["checks"]))

    def test_rejects_duplicate_paths(self):
        with self.assertRaisesRegex(ValueError, "Duplicate generated path"):
            self._generate({"files": [
                {"path": "index.html", "content": "<html></html>"},
                {"path": "index.html", "content": "<html>duplicate</html>"},
            ]})

    def test_missing_opening_html_tag_is_not_success(self):
        result = self._generate({
            "files": [{"path": "index.html", "content": "<body>Hello</body></html>"}],
        })
        self.assertFalse(result["success"])
        self.assertEqual(result["execution_status"], "draft_needs_revision")
        self.assertTrue(any(item["status"] == "failed" for item in result["checks"]))

    def test_non_object_json_is_rejected_cleanly(self):
        fake = types.ModuleType("llm_client")
        fake.ask = lambda *args, **kwargs: "[]"
        with patch.dict(sys.modules, {"llm_client": fake}):
            with self.assertRaisesRegex(ValueError, "JSON object"):
                engineering_executor.generate_project("Build a minimal page")


if __name__ == "__main__":
    unittest.main()
