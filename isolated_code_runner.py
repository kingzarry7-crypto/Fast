"""Authenticated gateway to a separately deployed isolated code runner.

This API process never executes generated code locally. The remote service must
provide the documented POST /v1/execute contract and run each job in a disposable,
resource-limited sandbox with network disabled and no application secrets mounted.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

import requests

MAX_FILES = 12
MAX_FILE_CHARS = 18000
MAX_OUTPUT_CHARS = 12000
MAX_TIMEOUT_SECONDS = 60


class RunnerUnavailable(RuntimeError):
    """Raised when an isolated runner is not configured or not trustworthy."""


def _runner_config() -> tuple[str, str]:
    base_url = os.getenv("KZ_SANDBOX_RUNNER_URL", "").strip().rstrip("/")
    token = os.getenv("KZ_SANDBOX_RUNNER_TOKEN", "").strip()
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise RunnerUnavailable("Isolated runner URL must be a configured HTTPS URL")
    if not token:
        raise RunnerUnavailable("KZ_SANDBOX_RUNNER_TOKEN is not configured")
    return base_url, token


def execute_project(files: list[dict[str, Any]], *, command: list[str] | None = None,
                    timeout_seconds: int = 30) -> dict[str, Any]:
    """Send project files to an external sandbox; never fall back to local execution."""
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise ValueError(f"files must contain between 1 and {MAX_FILES} entries")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")
    normalized = []
    seen = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Each file must be an object")
        path, content = item.get("path"), item.get("content")
        if not isinstance(path, str) or not path or path.startswith("/") or "\\\\" in path or any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError("Invalid project path")
        if path.split("/")[0].lower() in {".git", ".env", "node_modules", "__pycache__"}:
            raise ValueError("Restricted project path")
        if path in seen:
            raise ValueError(f"Duplicate project path: {path}")
        if not isinstance(content, str) or len(content) > MAX_FILE_CHARS:
            raise ValueError(f"Invalid or oversized content for {path}")
        seen.add(path)
        normalized.append({"path": path, "content": content})
    if command is not None:
        if not isinstance(command, list) or not command or len(command) > 8 or any(not isinstance(arg, str) or len(arg) > 200 for arg in command):
            raise ValueError("command must be a short list of strings")
        # Command policy is enforced by the runner too; never accept a shell string.
        if any(arg in {"sh", "bash", "-c", "/bin/sh", "/bin/bash"} for arg in command):
            raise ValueError("Shell execution is not permitted")
    base_url, token = _runner_config()
    payload = {"files": normalized, "command": command, "timeout_seconds": timeout_seconds}
    try:
        response = requests.post(
            base_url + "/v1/execute",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=(3, timeout_seconds + 5),
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise RunnerUnavailable("Isolated runner request failed; no local execution was attempted") from exc
    if response.is_redirect:
        raise RunnerUnavailable("Runner redirects are not accepted")
    if response.status_code != 200:
        raise RunnerUnavailable(f"Isolated runner returned HTTP {response.status_code}")
    try:
        result = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise RunnerUnavailable("Isolated runner returned invalid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("exit_code"), int):
        raise RunnerUnavailable("Runner response must include an integer exit_code")
    stdout, stderr = result.get("stdout", ""), result.get("stderr", "")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise RunnerUnavailable("Runner stdout/stderr must be strings")
    return {
        "status": "passed" if result["exit_code"] == 0 else "failed",
        "exit_code": result["exit_code"],
        "stdout": stdout[:MAX_OUTPUT_CHARS],
        "stderr": stderr[:MAX_OUTPUT_CHARS],
        "duration_ms": result.get("duration_ms") if isinstance(result.get("duration_ms"), (int, float)) else None,
        "runner": "remote_isolated",
    }
