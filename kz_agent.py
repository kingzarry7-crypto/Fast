"""KZ AGENT — central mission orchestrator.

This layer coordinates the existing workflow engine with the KZ Brain planner,
tool registry, approval gateway, browser operator, research engine, shared
memory and learning loop. Consequential actions remain approval-gated.
"""
from __future__ import annotations

from typing import Any, Dict

import workflow_engine as engine
import kz_brain


_ACTIVITY = {
    "planning": "Understanding the goal and building a safe plan",
    "researching": "Researching current information and opportunities",
    "waiting_for_approval": "Waiting for your approval before taking the external action",
    "waiting_for_human": "Waiting for you to complete the browser verification step",
    "approved": "Approval received; preparing the next execution step",
    "executing": "Executing the approved work",
    "verifying": "Checking the result and collecting evidence",
    "completed": "Work completed and verified",
    "failed": "Work stopped because a step failed",
    "paused": "Work paused by the user",
}


def _activity(status: str) -> str:
    return _ACTIVITY.get(str(status), "Working on the mission")


def snapshot(item: Dict[str, Any] | None) -> Dict[str, Any]:
    if not item:
        return {"status": "not_found", "activity": "Mission not found"}
    plan_steps = item.get("plan") or []
    current = next(
        (s for s in plan_steps if s.get("status") in {
            "running", "waiting_for_approval", "waiting_for_human"
        }),
        None,
    )
    completed = sum(1 for s in plan_steps if s.get("status") == "completed")
    brain = item.get("context", {}).get("brain") or {}
    return {
        "id": str(item.get("id")),
        "goal": str(item.get("goal") or ""),
        "status": str(item.get("status") or "unknown"),
        "activity": _activity(str(item.get("status") or "")),
        "risk": str(item.get("risk") or brain.get("risk") or "green"),
        "completed_steps": completed,
        "total_steps": len(plan_steps),
        "current_step": {
            "id": current.get("id"),
            "title": current.get("title"),
            "action": current.get("action"),
            "status": current.get("status"),
            "risk": current.get("risk"),
            "requires_approval": bool(current.get("requires_approval")),
            "approval_id": current.get("approval_id"),
        } if current else None,
        "requires_approval": bool(item.get("requires_approval") or brain.get("approval_required")),
        "potential_revenue": float(item.get("potential_revenue") or 0),
        "brain": {
            "kind": brain.get("kind"),
            "tools": brain.get("tools") or [],
            "approval_tools": brain.get("approval_tools") or [],
            "reasoning": brain.get("reasoning") or [],
        },
        "result": item.get("result") or {},
        "updated_at": item.get("updated_at"),
    }


def run(user_id: str, goal: str, *, account_id: str | None = None,
        run_now: bool = True) -> Dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("goal is required")

    brain_plan = kz_brain.plan(goal)
    item = engine.create_workflow(
        str(user_id), goal, account_id=account_id, run_now=False
    )

    # Persist the brain's decision alongside the workflow so every mission
    # has an inspectable plan and the executor can never silently lose context.
    item.setdefault("context", {})["brain"] = brain_plan
    item["context"]["agent_version"] = "brain-v1"
    item["risk"] = brain_plan["risk"]
    item["requires_approval"] = bool(
        item.get("requires_approval") or brain_plan["approval_required"]
    )
    from workflow_store import save_workflow
    save_workflow(item)

    if run_now:
        item = engine.run_workflow(str(item["id"]), str(user_id))

    result = snapshot(item)
    result["workflow"] = item
    return result


def get(user_id: str, workflow_id: str) -> Dict[str, Any]:
    return snapshot(engine.get_workflow(str(workflow_id), str(user_id)))


def approve(user_id: str, workflow_id: str, approved: bool) -> Dict[str, Any]:
    item = engine.approve_workflow(
        str(workflow_id), str(user_id), bool(approved)
    )
    return snapshot(item)


def resume_human_verification(user_id: str, workflow_id: str) -> Dict[str, Any]:
    item = engine.resume_human_verification(
        str(workflow_id), str(user_id)
    )
    return snapshot(item)


def list_recent(user_id: str, limit: int = 20) -> Dict[str, Any]:
    rows = engine.list_workflows(str(user_id), max(1, min(int(limit), 50)))
    return {
        "count": len(rows),
        "missions": [snapshot(row) for row in rows],
    }


def plan_preview(goal: str) -> Dict[str, Any]:
    """Preview the brain decision without creating a workflow."""
    return kz_brain.plan(goal)


def watch_catalog() -> Dict[str, Any]:
    return {"categories": kz_brain.watch_categories()}
