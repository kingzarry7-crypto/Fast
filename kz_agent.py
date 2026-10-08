"""KZ AGENT — central mission orchestrator.

This layer is intentionally additive. It coordinates the existing workflow engine,
approval gateway, browser operator, research engine, shared memory and learning
loop without replacing any of them.

The agent never grants itself permission for consequential actions.
"""
from __future__ import annotations

from typing import Any, Dict

import workflow_engine as engine


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
    plan = item.get("plan") or []
    current = next(
        (s for s in plan if s.get("status") in {
            "running", "waiting_for_approval", "waiting_for_human"
        }),
        None,
    )
    completed = sum(1 for s in plan if s.get("status") == "completed")
    return {
        "id": str(item.get("id")),
        "goal": str(item.get("goal") or ""),
        "status": str(item.get("status") or "unknown"),
        "activity": _activity(str(item.get("status") or "")),
        "risk": str(item.get("risk") or "green"),
        "completed_steps": completed,
        "total_steps": len(plan),
        "current_step": {
            "id": current.get("id"),
            "title": current.get("title"),
            "action": current.get("action"),
            "status": current.get("status"),
            "risk": current.get("risk"),
            "requires_approval": bool(current.get("requires_approval")),
            "approval_id": current.get("approval_id"),
        } if current else None,
        "requires_approval": bool(item.get("requires_approval")),
        "potential_revenue": float(item.get("potential_revenue") or 0),
        "result": item.get("result") or {},
        "updated_at": item.get("updated_at"),
    }


def run(user_id: str, goal: str, *, account_id: str | None = None,
        run_now: bool = True) -> Dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("goal is required")
    item = engine.create_workflow(
        str(user_id), goal, account_id=account_id, run_now=run_now
    )
    result = snapshot(item)
    result["workflow"] = item
    return result


def get(user_id: str, workflow_id: str) -> Dict[str, Any]:
    return snapshot(engine.get_workflow(str(workflow_id), str(user_id)))


def approve(user_id: str, workflow_id: str, approved: bool) -> Dict[str, Any]:
    item = engine.approve_workflow(
        str(workflow_id), str(user_id), bool(approved)
    )
    # Approval only changes the persisted state. The existing worker remains
    # responsible for execution, so this call cannot bypass the worker safety
    # rules or execute an unapproved plan.
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
