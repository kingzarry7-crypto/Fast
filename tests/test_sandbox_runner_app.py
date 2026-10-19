"""Unit tests for the isolated E2B runner's request validation and lifecycle."""
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from sandbox_runner import app as runner_app


class SandboxRunnerValidationTests(unittest.TestCase):
    def _request(self, path="main.py", content="print(2 + 2)", command=None):
        return runner_app.ExecuteRequest(
            files=[runner_app.ProjectFile(path=path, content=content)],
            command=command,
            timeout_seconds=10,
        )

    def test_rejects_traversal_absolute_paths_env_files_and_unsupported_suffixes(self):
        for path in ("../secret.py", "/tmp/main.py", "folder/../secret.py", ".env", "folder/.env.production", "main.exe"):
            with self.subTest(path=path), self.assertRaises(HTTPException):
                runner_app._validate(self._request(path=path))

    def test_rejects_duplicate_paths_and_total_project_size(self):
        duplicate = runner_app.ExecuteRequest(files=[
            runner_app.ProjectFile(path="main.py", content="print(1)"),
            runner_app.ProjectFile(path="main.py", content="print(2)"),
        ])
        with self.assertRaisesRegex(HTTPException, "Duplicate"):
            runner_app._validate(duplicate)

        too_large = runner_app.ExecuteRequest(files=[
            runner_app.ProjectFile(path=f"file{i}.txt", content="x" * 18000)
            for i in range(4)
        ])
        with self.assertRaises(HTTPException):
            runner_app._validate(too_large)

    def test_rejects_unapproved_and_shell_commands(self):
        for command in (["bash", "-c", "id"], ["python", "-c", "print(1)"], ["curl", "https://example.com"]):
            with self.subTest(command=command), self.assertRaises(HTTPException):
                runner_app._validate(self._request(command=command))

    def test_requires_configured_token_and_constant_time_auth_match(self):
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": ""}, clear=False):
            with self.assertRaises(HTTPException) as missing:
                runner_app._auth("Bearer token")
            self.assertEqual(missing.exception.status_code, 503)

        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": "expected-token"}, clear=False):
            with self.assertRaises(HTTPException) as denied:
                runner_app._auth("Bearer wrong-token")
            self.assertEqual(denied.exception.status_code, 401)
            runner_app._auth("Bearer expected-token")

    def test_executes_only_through_sdk_and_kills_disposable_sandbox(self):
        sandbox = Mock()
        sandbox.commands.run.return_value = types.SimpleNamespace(exit_code=0, stdout="4\n", stderr="")
        sdk = types.SimpleNamespace(Sandbox=Mock())
        sdk.Sandbox.create.return_value = sandbox

        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": "token", "E2B_API_KEY": "e2b-test"}, clear=False), \
             patch.dict(sys.modules, {"e2b_code_interpreter": sdk}):
            result = runner_app.execute(self._request(command=["python", "main.py"]), "Bearer token")

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "4\n")
        sdk.Sandbox.create.assert_called_once()
        sandbox.files.write.assert_called_once_with("/home/user/main.py", "print(2 + 2)")
        sandbox.commands.run.assert_called_once()
        self.assertFalse(sdk.Sandbox.create.call_args.kwargs["allow_internet_access"])
        sandbox.kill.assert_called_once()

    def test_runs_allowlisted_command_steps_sequentially(self):
        sandbox = Mock()
        sandbox.commands.run.side_effect = [
            types.SimpleNamespace(exit_code=0, stdout="installed", stderr=""),
            types.SimpleNamespace(exit_code=0, stdout="built", stderr=""),
        ]
        sdk = types.SimpleNamespace(Sandbox=Mock())
        sdk.Sandbox.create.return_value = sandbox
        req = runner_app.ExecuteRequest(
            files=[runner_app.ProjectFile(path="package.json", content='{"scripts":{"build":"next build"}}')],
            commands=[["npm", "install"], ["npm", "run", "build"]],
            timeout_seconds=20,
        )
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": "token", "E2B_API_KEY": "e2b-test"}, clear=False), \
             patch.dict(sys.modules, {"e2b_code_interpreter": sdk}):
            result = runner_app.execute(req, "Bearer token")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["commands_run"], 2)
        self.assertTrue(sdk.Sandbox.create.call_args.kwargs["allow_internet_access"])
        self.assertEqual(sandbox.commands.run.call_count, 2)
        sandbox.kill.assert_called_once()

    def test_invalid_auth_never_creates_sandbox(self):
        sdk = types.SimpleNamespace(Sandbox=Mock())
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": "expected", "E2B_API_KEY": "e2b-test"}, clear=False), \
             patch.dict(sys.modules, {"e2b_code_interpreter": sdk}):
            with self.assertRaises(HTTPException):
                runner_app.execute(self._request(), "Bearer wrong")
        sdk.Sandbox.create.assert_not_called()

    def test_sandbox_exception_is_sanitized_and_sandbox_is_killed(self):
        sandbox = Mock()
        sandbox.commands.run.side_effect = TimeoutError("private provider detail")
        sdk = types.SimpleNamespace(Sandbox=Mock(return_value=None))
        sdk.Sandbox.create.return_value = sandbox
        with patch.dict(os.environ, {"KZ_SANDBOX_RUNNER_TOKEN": "token", "E2B_API_KEY": "e2b-test"}, clear=False), \
             patch.dict(sys.modules, {"e2b_code_interpreter": sdk}):
            result = runner_app.execute(self._request(command=["python", "main.py"]), "Bearer token")
        self.assertEqual(result["exit_code"], 124)
        self.assertNotIn("private provider detail", result["stderr"])
        sandbox.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
