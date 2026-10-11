"""Runtime inventory for King Zarry AI's own repository.

This is deliberately a small, file-backed catalogue: it reports only paths that
exist in the deployed checkout and never claims a provider account is connected
merely because its integration module exists.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent

# These entries describe the repository's own components and their practical use.
# Presence is checked at runtime so stale documentation does not appear as a feature.
_COMPONENTS = (
    ("api.py", "Authenticated web API and chat entry point", "Use the web app for signed-in chat; API routes enforce the web session."),
    ("agent_router.py", "Intent routing for explicit market and capability requests", "Ask for a gold/BTC signal or ask what access is verified; other chat continues through the normal AI path."),
    ("agent_core.py", "Market analysis, news-risk and learning tools", "Use market requests through King Zarry AI; if provider data is stale or unavailable it should say so."),
    ("workflow_engine.py", "Workflow planning, execution states and outcome evidence", "Describe a task; review its plan and approve consequential actions before execution."),
    ("workflow_api.py", "Authenticated workflow API endpoints", "Use the dashboard/workflow interface to inspect and approve workflows; endpoint access remains user-scoped."),
    ("workflow_store.py", "Durable workflow and approval persistence", "Stores workflow state for the API/worker; do not edit its database manually while jobs are running."),
    ("workflow_models.py", "Workflow and step status/risk definitions", "Defines shared states used by the engine and API."),
    ("agent_action_gateway.py", "Action approval and provider execution boundary", "External actions must pass through the gateway and its approval policy."),
    ("learning_loop.py", "Learning from recorded workflow outcomes", "Lessons should be based on recorded outcomes, not assumed success."),
    ("reliability_guardian.py", "Workflow reliability and recovery checks", "Use workflow/reliability status to identify stalled or failed work."),
    ("revenue_engine.py", "Revenue opportunity and pipeline logic", "Use the opportunity/revenue views; estimates must be distinguished from confirmed income."),
    ("browser_operator.py", "Browser automation operations", "Use only after the relevant site session is authenticated; human verification may still be required."),
    ("connector_api.py", "Official connected-account connector routes", "Connect accounts in Settings, then verify the account status before asking for actions."),
    ("google_connector.py", "Google/Gmail integration routes", "Connect Google and grant the scopes required for the requested task; email sending still requires approval."),
    ("bot.py", "Telegram bot entry point", "Use the configured Telegram bot commands; connector state must be verified before acting."),
    ("discord_bot.py", "Discord bot entry point", "Use the registered Discord commands; sensitive actions remain approval-gated."),
    ("frontend", "Web frontend application", "Open the Cloudflare-hosted web app for chat, dashboard and connector settings."),
    ("frontend/public/sw.js", "Frontend service worker and offline shell cache", "Controls install/offline behavior; page navigation prefers the live deployment to avoid stale app bundles."),
)

def get_project_inventory() -> dict[str, Any]:
    """Return verified source paths and deployment identity, without exposing secrets."""
    components = []
    for path, purpose, usage in _COMPONENTS:
        exists = (_ROOT / path).exists()
        components.append({
            "path": path,
            "purpose": purpose,
            "how_to_use": usage,
            "present": exists,
            "status": "present in this runtime checkout" if exists else "not found in this runtime checkout",
        })
    commit = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GIT_COMMIT_SHA")
        or os.getenv("CF_PAGES_COMMIT_SHA")
        or os.getenv("VERCEL_GIT_COMMIT_SHA")
    )
    present = sum(1 for item in components if item["present"])
    return {
        "project": "King Zarry AI",
        "runtime_root": str(_ROOT),
        "deployment_commit": commit or None,
        "component_count": len(components),
        "present_count": present,
        "components": components,
    }

def format_project_inventory() -> str:
    """Produce a user-facing report about this project, not a generic JARVIS product."""
    inventory = get_project_inventory()
    commit = inventory["deployment_commit"] or "not exposed by the current runtime"
    lines = [
        "King Zarry AI — your project files and current runtime report",
        f"Runtime checkout: {inventory['present_count']}/{inventory['component_count']} catalogued components found",
        f"Deployment commit: {commit}",
        "",
        "YOUR COMPONENTS AND HOW TO USE THEM",
    ]
    for item in inventory["components"]:
        marker = "FOUND" if item["present"] else "NOT FOUND"
        lines.append(f"- {marker} — {item['path']}: {item['purpose']}. How to use: {item['how_to_use']}")
    lines.extend([
        "",
        "IMPORTANT STATUS RULES",
        "- A file being present does not mean its API key, provider account, permission, or remote service is connected.",
        "- A feature is usable only when its required configuration and live provider checks succeed.",
        "- For email, publishing, browser actions or other consequential tasks, approve the exact proposed action first.",
        "- I can report a deployment version only when the runtime exposes its commit identifier; I will not invent a latest commit.",
        "",
        "TRY ASKING:",
        "- 'Show my project files and how to use them.'",
        "- 'Give me a King Zarry AI project update.'",
        "- 'What is present in the runtime, and what is missing?'",
        "- 'Check my connected accounts and tell me what still needs setup.'",
    ])
    return "\n".join(lines)
