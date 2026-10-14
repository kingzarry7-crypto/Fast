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
ALLOWED_SUFFIXES = {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".svg", ".py"}


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
        "You are a senior web engineer. Create a useful, responsive website project "
        "for the user's request. Return ONLY valid JSON with shape "
        '{"files":[{"path":"index.html","content":"..."}],"summary":"..."} . '
        "Include all files needed for a self-contained frontend (HTML/CSS/JS as appropriate). "
        "Use relative paths, no external secrets, no deployment, no backend credentials. "
        "Keep total output concise and do not use markdown fences.\nUSER REQUEST:\n" + goal[:3500]
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
    html_ok = bool(index and "<html" in index.lower() and "</html>" in index.lower())
    checks.append({
        "name": "HTML document structure",
        "status": "passed" if html_ok else "failed",
        "note": None if html_ok else "index.html must contain both opening and closing html tags.",
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
    checks.append({
        "name": "Generated code execution",
        "status": "not_run",
        "note": "Generated code is not executed on the API server for safety.",
    })
    # A draft must not be reported as successful when a required structural check fails.
    passed = all(item["status"] != "failed" for item in checks)
    return {
        "success": passed,
        "summary": str(data.get("summary") or "Generated project draft"),
        "files": [{"path": path, "content": content} for path, content in files.items()],
        "file_count": len(files),
        "total_characters": total,
        "checks": checks,
        "execution_status": "draft_generated" if passed else "draft_needs_revision",
        "note": "Files are included in this workflow result. No live repository, deployment, or production service was changed.",
    }
