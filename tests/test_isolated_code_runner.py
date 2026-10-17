import os
import unittest
from unittest.mock import Mock, patch

import isolated_code_runner as runner


class IsolatedRunnerGatewayTests(unittest.TestCase):
    def test_requires_https_and_token(self):
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_URL": "http://runner.example", "KZ_SANDBOX_RUNNER_TOKEN": "x"}):
            with self.assertRaises(runner.RunnerUnavailable):
                runner._runner_config()
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_URL": "https://runner.example", "KZ_SANDBOX_RUNNER_TOKEN": ""}):
            with self.assertRaises(runner.RunnerUnavailable):
                runner._runner_config()

    def test_never_falls_back_when_unconfigured(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(runner.RunnerUnavailable):
                runner.execute_project([{"path": "main.py", "content": "print('hi')"}])

    def test_rejects_path_traversal_and_shell_command(self):
        for path in ("../secret.py", "folder\\secret.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.execute_project([{"path": path, "content": "x"}])
        with self.assertRaises(ValueError):
            runner.execute_project([{"path": "main.py", "content": "x"}], command=["bash", "-c", "id"])

    def test_rejects_unsupported_file_types_and_env_files(self):
        for path in ("main.exe", "folder/.env.production", ".env.local"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.execute_project([{"path": path, "content": "x"}])

    def test_rejects_unapproved_command_executable(self):
        with self.assertRaises(ValueError):
            runner.execute_project([{"path": "main.py", "content": "x"}], command=["curl", "https://example.com"])
        with self.assertRaises(ValueError):
            runner.execute_project([{"path": "main.py", "content": "x"}], command=["python", "-c", "print(1)"])


    def test_accepts_dependency_and_config_manifests(self):
        with patch.dict(os.environ, {}, clear=True):
            for path in ("requirements.txt", "pyproject.toml", "config.yaml", "schema.sql"):
                with self.subTest(path=path), self.assertRaises(runner.RunnerUnavailable):
                    runner.execute_project([{"path": path, "content": "valid: true"}])

    @patch("isolated_code_runner.requests.post")
    def test_captures_actual_remote_exit_code_and_output(self, post):
        response = Mock()
        response.status_code = 200
        response.is_redirect = False
        response.json.return_value = {"exit_code": 1, "stdout": "3 tests", "stderr": "AssertionError", "duration_ms": 42}
        post.return_value = response
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_URL": "https://runner.example", "KZ_SANDBOX_RUNNER_TOKEN": "secret"}):
            result = runner.execute_project([{"path": "test.py", "content": "assert 1 == 2"}])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("AssertionError", result["stderr"])
        self.assertEqual(result["runner"], "remote_isolated")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])


if __name__ == "__main__":
    unittest.main()
