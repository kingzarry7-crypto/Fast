"""Safe first-pass engineering executor for generated project drafts.

Generated files are stored in the workflow result for the authenticated user.
No generated code is deployed or executed as part of this step.
"""
from __future__ import annotations

import json
import re
from typing import Any

MAX_FILES = 12
MAX_FILE_CHARS = 18000
MAX_TOTAL_CHARS = 60000
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".svg", ".py", ".txt", ".toml", ".yaml", ".yml", ".sql", ".xml"}


def _safe_path(value: Any) -> str:
    path = str(value or "").replace("\\", "/").strip()
    if not path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError("Invalid project file path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Invalid project file path")
    if parts[0].lower() in {".git", ".env", "node_modules", "__pycache__"}:
        raise ValueError("Restricted project path")
    if "." not in parts[-1] or "." + parts[-1].rsplit(".", 1)[-1].lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported project file type")
    return "/".join(parts)


def generate_project(goal: str) -> dict[str, Any]:
    """Generate an inspectable project draft and run non-executing checks."""
    from llm_client import ask

    prompt = (
        "You are a senior software engineer. Build the project the user actually requested; "
        "do not assume every request is a website. First infer the appropriate project type and stack "
        "(for example static website, React/TypeScript frontend, Python tool/API, or full-stack prototype), "
        "then return a coherent set of source files and a concise README with setup/test instructions. "
        "Return ONLY valid JSON with shape "
        '{"files":[{"path":"relative/path.ext","content":"..."}],"summary":"..."} . '
        "Include a minimal test when practical and a package/dependency manifest when needed. "
        "Use relative paths. Never include secrets, .env files, credentials, or real user data. "
        "Do not claim external services are connected, production deployment happened, or features work "
        "without implementation. Do not include shell scripts or instructions that execute commands on the API server. "
        "Keep the project focused, complete, and within the file/character limits. No markdown fences.\nUSER REQUEST:\n" + goal[:3500]
    )
    raw = ask([
        {"role": "system", "content": "Return strict JSON only. Never include secrets or instructions to execute shell commands."},
        {"role": "user", "content": prompt},
    ], max_tokens=9000)
    try:
        data = json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise ValueError("The model did not return a valid project-file JSON document")
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("The model response must be a JSON object")
    rows = data.get("files")
    if not isinstance(rows, list) or not rows:
        raise ValueError("The model returned no project files")
    if len(rows) > MAX_FILES:
        raise ValueError(f"Project exceeded the {MAX_FILES}-file safety limit")

    files: dict[str, str] = {}
    total = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed file entry in generated project")
        path = _safe_path(row.get("path"))
        content = row.get("content")
        if not isinstance(content, str):
            raise ValueError(f"Missing text content for {path}")
        if len(content) > MAX_FILE_CHARS:
            raise ValueError(f"Generated file {path} exceeds the per-file limit")
        if path in files:
            raise ValueError(f"Duplicate generated path: {path}")
        total += len(content)
        files[path] = content
    if total > MAX_TOTAL_CHARS:
        raise ValueError("Generated project exceeds the total size limit")

    checks = []
    index = files.get("index.html", "")
    web_project = any(path.lower().endswith((".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".svg")) for path in files)
    if web_project:
        html_ok = bool(index and "<html" in index.lower() and "</html>" in index.lower())
        checks.append({
            "name": "HTML document structure",
            "status": "passed" if html_ok else "failed",
            "note": None if html_ok else "Web projects must include index.html with opening and closing html tags.",
        })
    for path, content in files.items():
        if path.endswith((".js", ".jsx", ".ts", ".tsx")):
            # This is a lightweight guard, not a JavaScript runtime test.
            balanced = content.count("{") == content.count("}") and content.count("(") == content.count(")")
            checks.append({
                "name": f"Basic delimiter check: {path}",
                "status": "passed" if balanced else "warning",
                "note": None if balanced else "Delimiter counts differ; this is a heuristic, not a parser.",
            })
    # Execute only through the separate authenticated sandbox gateway. Never fall
    # back to local execution when the runner is missing or unavailable.
    execution: dict[str, Any] = {
        "status": "not_run",
        "note": "Isolated runner is not configured; generated source has not been executed.",
    }
    try:
        from isolated_code_runner import RunnerUnavailable, execute_project

        try:
            # Compile Python without running app entrypoints. For JavaScript
            # projects, execute an explicit build/test script when the manifest
            # declares one. All commands run in the separate E2B sandbox.
            python_paths = [path for path in files if path.lower().endswith(".py")]
            js_paths = [path for path in files if path.lower().endswith(".js")]
            command = ["python", "-m", "compileall", "-q", "."] if python_paths else None
            commands = []
            validation_name = "Isolated Python compile check" if python_paths else "Isolated project validation"
            manifest = files.get("package.json")
            if manifest:
                try:
                    package_data = json.loads(manifest)
                    scripts = package_data.get("scripts", {}) if isinstance(package_data, dict) else {}
                except Exception:
                    scripts = {}
                if isinstance(scripts, dict) and isinstance(scripts.get("build"), str):
                    commands = [
                        ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"],
                        ["npm", "run", "build"],
                    ]
                    command = None
                    validation_name = "Isolated JavaScript build"
                elif isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
                    commands = [
                        ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"],
                        ["npm", "test"],
                    ]
                    command = None
                    validation_name = "Isolated JavaScript tests"
            elif js_paths and not python_paths:
                command = ["node", "--check", js_paths[0]]
                validation_name = "Isolated JavaScript syntax check"
            execution = execute_project(
                [{"path": path, "content": content} for path, content in files.items()],
                command=command,
                commands=commands or None,
                timeout_seconds=60 if commands else 30,
            )
            if execution.get("status") == "failed":
                checks.append({
                    "name": "Isolated project validation",
                    "status": "failed",
                    "note": str(execution.get("stderr") or "Isolated validation failed")[:500],
                })
            elif execution.get("runner") == "remote_isolated" and (command or commands):
                checks.append({
                    "name": validation_name,
                    "status": "passed",
                    "note": str(execution.get("stdout") or "The isolated validation command completed successfully.")[:500],
                })
            else:
                checks.append({
                    "name": "Isolated project staging",
                    "status": "not_run",
                    "note": "Files reached the isolated runner, but no runtime test was run for this project type.",
                })
        except RunnerUnavailable as exc:
            execution = {"status": "not_run", "note": str(exc)[:300]}
    except Exception as exc:
        # Optional runner failures must never cause unsafe local execution.
        execution = {"status": "not_run", "note": f"Isolated validation unavailable ({type(exc).__name__})."}

    structural_passed = not any(item["status"] == "failed" for item in checks)
    execution_status = "generated_not_executed"
    if execution.get("status") == "failed":
        execution_status = "validation_failed"
    elif execution.get("runner") == "remote_isolated" and execution.get("status") == "passed":
        execution_status = "validated" if execution.get("execution") != "staged_only" else "staged_only"
    passed = structural_passed and execution_status != "validation_failed"
    checks.append({
        "name": "Isolated execution status",
        "status": "passed" if execution_status == "validated" else ("failed" if execution_status == "validation_failed" else "not_run"),
        "note": str(execution.get("note") or execution.get("stderr") or execution.get("stdout") or execution_status)[:500],
    })
    return {
        "success": passed,
        "summary": str(data.get("summary") or "Generated project"),
        "files": [{"path": path, "content": content} for path, content in files.items()],
        "file_count": len(files),
        "total_characters": total,
        "checks": checks,
        "execution": execution,
        "execution_status": execution_status if structural_passed else "draft_needs_revision",
        "note": (
            "Generated files are returned for review. No GitHub repository or production deployment was changed. "
            "Execution and tests are reported only when the separately configured isolated runner provides evidence."
        ),
    }
