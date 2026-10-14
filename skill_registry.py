"""Skill catalogue and routing policy for King Zarry AI.

The catalogue describes supported capabilities; it never claims a tool or provider
is connected just because a skill exists. Execution remains delegated to the existing
authenticated agent/workflow APIs and connector-specific permission boundaries.
"""
from __future__ import annotations

SKILLS = (
    {
        "id": "coding",
        "name": "Coding & App Building",
        "description": "Plan and create applications, APIs, components, and code changes.",
        "icon": "code",
        "task_types": ["engineering", "website_build"],
        "tools": ["repository_files", "agent_workflow"],
        "execution": "isolated_runner_required_for_project_execution",
        "approval": "Review changes before merging or deploying.",
        "available": False,
        "availability": "unverified",
    },
    {
        "id": "web",
        "name": "Web Research",
        "description": "Research current information and summarize evidence with sources.",
        "icon": "globe",
        "task_types": ["research", "browser"],
        "tools": ["configured_web_search", "browser_operator"],
        "execution": "existing_research_workflow",
        "approval": "Authenticated sessions and consequential actions require approval.",
        "available": True,
    },
    {
        "id": "images",
        "name": "Images & Media",
        "description": "Prepare image or video generation/editing requests using configured media providers.",
        "icon": "image",
        "task_types": ["image_generation", "media_editing"],
        "tools": ["configured_media_providers"],
        "execution": "provider_dependent",
        "approval": "Confirm paid or external publishing actions before execution.",
        "available": True,
    },
    {
        "id": "github",
        "name": "GitHub & Delivery",
        "description": "Inspect repository files, prepare code changes, and check CI/deployment evidence.",
        "icon": "github",
        "task_types": ["github", "engineering", "deployment"],
        "tools": ["github_connector_when_authorized", "workflow_engine"],
        "execution": "repository_actions_are_permission_gated",
        "approval": "Require review before merge, release, or production deployment.",
        "available": True,
    },
    {
        "id": "testing",
        "name": "Testing & Debugging",
        "description": "Create test plans, diagnose errors, and report verified test results.",
        "icon": "flask",
        "task_types": ["testing", "debugging"],
        "tools": ["configured_test_runner", "workflow_engine"],
        "execution": "isolated_runner_required_for_untrusted_code",
        "approval": "Never report a test as passing without captured test evidence.",
        "available": True,
    },
    {
        "id": "data",
        "name": "Data & Machine Learning",
        "description": "Analyze datasets, validate features, train models, and evaluate results.",
        "icon": "chart",
        "task_types": ["data_analysis", "machine_learning"],
        "tools": ["python_runner_for_supported_snippets", "configured_data_tools"],
        "execution": "browser_wasm_for_supported_python; isolated_runner_for_full_jobs",
        "approval": "Distinguish measured results from estimates; protect uploaded data.",
        "available": True,
    },
)

_SKILL_BY_ID = {skill["id"]: skill for skill in SKILLS}


def list_skills():
    """Return safe metadata. Provider readiness must be verified separately."""
    return [dict(skill, tools=list(skill["tools"]), task_types=list(skill["task_types"])) for skill in SKILLS]


def get_skill(skill_id: str):
    """Get one known skill or None."""
    return _SKILL_BY_ID.get((skill_id or "").strip().lower())


def classify_skill_request(text: str) -> str:
    """Best-effort task routing hint; callers must still check tool availability."""
    value = (text or "").lower()
    if any(word in value for word in ("csv", "dataset", "dataframe", "train model", "machine learning", "model accuracy", "analyze data")):
        return "data"
    if any(word in value for word in ("test", "debug", "traceback", "failing build", "unit test", "regression")):
        return "testing"
    if any(word in value for word in ("github", "pull request", "commit", "merge", "deploy", "repository", "repo")):
        return "github"
    if any(word in value for word in ("image", "picture", "photo", "video", "thumbnail", "illustration")):
        return "images"
    if any(word in value for word in ("research", "search the web", "latest", "look up", "compare sources", "browse")):
        return "web"
    if any(word in value for word in ("build", "code", "website", "app", "api", "program", "script", "component")):
        return "coding"
    return "coding"
