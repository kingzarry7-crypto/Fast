"""Isolated execution API for King Zarry AI, backed by E2B disposable sandboxes.

This service intentionally does not execute submitted code in its own process.
Each request gets a fresh provider-managed sandbox and bounded execution time.
"""
from __future__ import annotations

import hmac
import os
import re
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="King Zarry AI Isolated Runner", version="1.0.0")
MAX_FILES = 12
MAX_FILE_CHARS = 18_000
MAX_TOTAL_CHARS = 60_000
MAX_TIMEOUT = 60
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".svg", ".py", ".txt", ".toml", ".yaml", ".yml", ".sql", ".xml"}
ALLOWED_COMMANDS = {"python", "python3", "pytest", "node", "npm", "npx"}
SHELL_TOKENS = {"sh", "bash", "-c", "/bin/sh", "/bin/bash", "&&", "||", ";", "|", ">", "<", "`"}


class ProjectFile(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_FILE_CHARS)


class ExecuteRequest(BaseModel):
    files: list[ProjectFile] = Field(min_length=1, max_length=MAX_FILES)
    command: list[str] | None = Field(default=None, max_length=8)
    commands: list[list[str]] | None = Field(default=None, max_length=4)
    timeout_seconds: int = Field(default=30, ge=1, le=MAX_TIMEOUT)


def _validate(req: ExecuteRequest) -> list[dict[str, str]]:
    rows = []
    seen = set()
    total = 0
    for f in req.files:
        path = f.path
        if path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
            raise HTTPException(400, "Invalid project path")
        parts = path.split("/")
        if any(p in {"", ".", ".."} for p in parts):
            raise HTTPException(400, "Invalid project path")
        if any(p.lower() == ".env" or p.lower().startswith(".env.") for p in parts):
            raise HTTPException(400, "Environment files are not allowed")
        if any(p.lower() in {".git", "node_modules", "__pycache__"} for p in parts):
            raise HTTPException(400, "Restricted project path")
        suffix = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
        if suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(400, "Unsupported file type")
        if path in seen:
            raise HTTPException(400, "Duplicate project path")
        seen.add(path)
        total += len(f.content)
        rows.append({"path": path, "content": f.content})
    if total > MAX_TOTAL_CHARS:
        raise HTTPException(413, "Project exceeds total size limit")
    if req.command is not None and req.commands is not None:
        raise HTTPException(400, "Provide command or commands, not both")
    command_list = [req.command] if req.command is not None else (req.commands or [])
    if len(command_list) > 4:
        raise HTTPException(400, "Too many command steps")
    for cmd in command_list:
        if not cmd or len(cmd) > 8 or any(not isinstance(a, str) or len(a) > 200 for a in cmd):
            raise HTTPException(400, "Invalid command")
        if cmd[0] not in ALLOWED_COMMANDS:
            raise HTTPException(400, "Command executable is not permitted")
        if any(a in SHELL_TOKENS or a.startswith(("--eval", "-c")) for a in cmd[1:]):
            raise HTTPException(400, "Shell and inline-code execution are not permitted")
    return rows


def _auth(authorization: str | None) -> None:
    expected = os.getenv("KZ_SANDBOX_RUNNER_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Runner token is not configured")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "provider": "e2b", "execution": "isolated-provider-sandbox"}


@app.post("/v1/execute")
def execute(req: ExecuteRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _auth(authorization)
    rows = _validate(req)
    api_key = os.getenv("E2B_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "E2B_API_KEY is not configured")
    started = time.monotonic()
    sandbox = None
    try:
        # E2B supplies the isolation boundary; never run generated code in this API process.
        from e2b_code_interpreter import Sandbox
        requested_commands = req.commands or ([req.command] if req.command is not None else [])
        needs_package_network = any(cmd and cmd[0] in {"npm", "npx"} for cmd in requested_commands)
        sandbox = Sandbox.create(
            timeout=max(10, req.timeout_seconds + 5),
            api_key=api_key,
            allow_internet_access=needs_package_network,
        )
        for row in rows:
            safe_path = "/home/user/" + row["path"]
            sandbox.files.write(safe_path, row["content"])
        commands = req.commands or ([req.command] if req.command is not None else [])
        if not commands:
            py_files = [r["path"] for r in rows if r["path"].lower().endswith(".py")]
            if py_files:
                commands = [["python", py_files[0]]]
            else:
                return {
                    "exit_code": 0, "stdout": "Files staged in isolated sandbox; no executable test command was requested.",
                    "stderr": "", "duration_ms": int((time.monotonic() - started) * 1000),
                    "runner": "e2b", "execution": "staged_only",
                }
        stdout_parts, stderr_parts = [], []
        exit_code = 0
        for command in commands:
            result = sandbox.commands.run(
                " ".join(__import__("shlex").quote(part) for part in command),
                cwd="/home/user",
                timeout=req.timeout_seconds,
            )
            stdout_parts.append(str(getattr(result, "stdout", "")))
            stderr_parts.append(str(getattr(result, "stderr", "")))
            exit_code = int(getattr(result, "exit_code", 1))
            if exit_code != 0:
                break
        return {
            "exit_code": exit_code,
            "stdout": "\\n".join(part for part in stdout_parts if part)[-12000:],
            "stderr": "\\n".join(part for part in stderr_parts if part)[-12000:],
            "duration_ms": int((time.monotonic() - started) * 1000),
            "runner": "e2b",
            "commands_run": len(stdout_parts),
        }
    except Exception as exc:
        # Avoid returning provider internals, credentials, or environment details.
        return {
            "exit_code": 124 if "timeout" in type(exc).__name__.lower() else 1,
            "stdout": "",
            "stderr": f"Isolated execution failed: {type(exc).__name__}",
            "duration_ms": int((time.monotonic() - started) * 1000),
            "runner": "e2b",
        }
    finally:
        if sandbox is not None:
            try:
                sandbox.kill()
            except Exception:
                pass
