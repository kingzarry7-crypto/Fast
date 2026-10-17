"""Explicit coding-intent detection and safe website draft generation."""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger("kz_coding_agent")

_EMAIL_INTENT = re.compile(
    r"\b(?:send|compose|draft|write|reply to|forward)\b.{0,50}\b(?:email|e-mail|gmail|message)\b|"
    r"\b(?:email|e-mail|gmail)\b.{0,50}\b(?:send|compose|draft|write|reply)\b",
    re.I | re.S,
)
_CODE_VERB = re.compile(
    r"\b(?:build|create|make|develop|code|program|implement|generate|scaffold)\b",
    re.I,
)
_CODE_TARGET = re.compile(
    r"\b(?:website|web ?app|app|application|platform|frontend|landing page|"
    r"dashboard|social network|facebook|instagram|twitter|tiktok|marketplace|"
    r"clone|site|software|tool|game|calculator|portfolio|blog|chat ?app)\b",
    re.I,
)


def is_coding_request(message: str) -> bool:
    """Only claim clear build requests; never hijack email or account actions."""
    text = str(message or "").strip()
    if not text or len(text) > 4000:
        return False
    if _EMAIL_INTENT.search(text):
        return False
    return bool(_CODE_VERB.search(text) and _CODE_TARGET.search(text))


def _format_project(project: dict[str, Any], max_chars: int = 16000) -> str:
    files = project.get("files") or []
    names = [str(item.get("path") or "unnamed") for item in files if isinstance(item, dict)]
    lines = [
        "CODING AGENT — PROJECT GENERATION RESULT",
        "",
        str(project.get("summary") or "Project draft generated."),
        f"Files created: {len(files)}",
        *[f"- {name}" for name in names],
        "",
        f"Execution status: {project.get('execution_status') or 'unknown'}",
        "",
        "Validation:",
    ]
    for check in project.get("checks") or []:
        if isinstance(check, dict):
            lines.append(f"- {check.get('status', 'unknown')}: {check.get('name', 'check')}")
    lines.extend(["", "Project source files:"])
    remaining = max_chars - sum(len(line) + 1 for line in lines)
    language_by_suffix = {
        ".html": "html", ".htm": "html", ".css": "css", ".js": "javascript",
        ".jsx": "jsx", ".ts": "typescript", ".tsx": "tsx", ".py": "python",
        ".json": "json", ".md": "markdown", ".svg": "xml", ".xml": "xml",
        ".sql": "sql", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".txt": "text",
    }
    for item in files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "file.txt")
        content = str(item.get("content") or "")
        suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        language = language_by_suffix.get(suffix, "text")
        # MessageContent.tsx renders its code controls and HTML preview only for
        # fenced blocks. Choose a fence longer than any run inside generated
        # content so source files cannot accidentally terminate their own block.
        backtick_runs = [len(match.group(0)) for match in re.finditer(r"`+", content)]
        fence = "`" * max(3, max(backtick_runs, default=0) + 1)
        block = f"\n**{path}**\n\n{fence}{language}\n{content}\n{fence}\n"
        if len(block) > remaining:
            lines.append(f"\n**{path}**\n[Source omitted from chat because the response size limit was reached.]")
            continue
        lines.append(block)
        remaining -= len(block)
    execution = project.get("execution") or {}
    lines.extend([
        "",
        str(project.get("note") or "No live repository or deployment was changed."),
        f"Runner result: {execution.get('status', 'not_run')}. {execution.get('note', '')}".strip(),
        "A generated project is not considered deployed. GitHub changes and production deployments require their own configured integration and verification.",
    ])
    return "\n".join(lines)[:max_chars + 1200]


def _safe_error_detail(exc: Exception) -> str:
    """Expose useful diagnostic labels without returning credentials or raw responses."""
    detail = str(exc).strip()
    detail = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redacted]", detail)
    detail = re.sub(r"(?i)(api[_-]?key[=: ]+)\S+", r"\1[redacted]", detail)
    detail = re.sub(r"\b(?:sk|gsk|hf|xai)-[A-Za-z0-9_-]{8,}\b", "[redacted]", detail)
    detail = re.sub(r"\s+", " ", detail)
    return detail[:240] or type(exc).__name__


def handle_coding_request(message: str) -> Optional[dict[str, Any]]:
    """Generate a safe, inspectable project draft for explicit coding requests."""
    if not is_coding_request(message):
        return None
    from engineering_executor import generate_project

    try:
        project = generate_project(str(message).strip())
    except Exception as exc:
        detail = _safe_error_detail(exc)
        logger.error("Coding project generation failed (%s): %s", type(exc).__name__, detail)
        return {
            "status": "error",
            "provider": "coding_agent",
            "operation": "generate_project",
            "reply": (
                "I routed this request to the Coding Agent, but project generation failed. "
                f"Reason: {type(exc).__name__} — {detail}. "
                "No project files were created or deployed."
            ),
            "project": None,
        }
    execution_status = str(project.get("execution_status") or "generated_not_executed")
    response_status = (
        "error" if not project.get("success")
        else "completed" if execution_status == "validated"
        else "generated_not_executed" if execution_status in {"generated_not_executed", "staged_only"}
        else "needs_revision" if execution_status == "validation_failed"
        else "generated"
    )
    return {
        "status": response_status,
        "provider": "coding_agent",
        "operation": "generate_project",
        "reply": _format_project(project),
        "project": project,
    }
