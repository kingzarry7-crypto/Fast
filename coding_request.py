"""Explicit coding-intent detection and safe website draft generation."""
from __future__ import annotations

import re
from typing import Any, Optional

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
        "CODING AGENT — WEBSITE DRAFT GENERATED",
        "",
        str(project.get("summary") or "Project draft generated."),
        f"Files created: {len(files)}",
        *[f"- {name}" for name in names],
        "",
        "Validation:",
    ]
    for check in project.get("checks") or []:
        if isinstance(check, dict):
            lines.append(f"- {check.get('status', 'unknown')}: {check.get('name', 'check')}")
    lines.extend(["", "Project source files:"])
    remaining = max_chars - sum(len(line) + 1 for line in lines)
    for item in files:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "file.txt")
        content = str(item.get("content") or "")
        block = f"\n--- {path} ---\n\n{content}\n"
        if len(block) > remaining:
            lines.append(f"\n--- {path} ---\n[Source omitted from chat because the response size limit was reached.]")
            continue
        lines.append(block)
        remaining -= len(block)
    lines.extend([
        "",
        "This is a generated draft, not a deployed website. The server did not execute the generated code or change a live repository."
    ])
    return "\n".join(lines)[:max_chars + 1200]


def handle_coding_request(message: str) -> Optional[dict[str, Any]]:
    """Generate a safe, inspectable project draft for explicit coding requests."""
    if not is_coding_request(message):
        return None
    from engineering_executor import generate_project

    try:
        project = generate_project(str(message).strip())
    except Exception as exc:
        # Do not fall through to general chat and imply that the build happened.
        return {
            "status": "error",
            "provider": "coding_agent",
            "operation": "generate_project",
            "reply": (
                "I routed this request to the Coding Agent, but project generation failed. "
                f"Reason: {type(exc).__name__}. No project files were created or deployed. "
                "Please retry; if this persists, check the configured AI provider and Railway logs."
            ),
            "project": None,
        }
    return {
        "status": "completed" if project.get("success") else "needs_revision",
        "provider": "coding_agent",
        "operation": "generate_project",
        "reply": _format_project(project),
        "project": project,
    }
