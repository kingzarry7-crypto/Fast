"""KING ZARRY AI — delivery agent.

Turns verified workflow results into a client-ready delivery package.
No client-facing delivery is sent automatically; final handoff remains approval-gated.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, List


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any, limit: int = 800) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:48] or "delivery"


def _hash(workflow_id: str, goal: str) -> str:
    return hashlib.sha256(f"{workflow_id}:{goal}".encode()).hexdigest()[:16]


def _status(workflow: Dict[str, Any]) -> str:
    return str(workflow.get("status") or "").lower()


def _verification(workflow: Dict[str, Any]) -> Dict[str, Any]:
    result = workflow.get("result") or {}
    completed = _status(workflow) == "completed"
    explicit = bool(result.get("verified") or result.get("delivery_verified"))
    failed = _status(workflow) == "failed"
    return {
        "eligible": completed and not failed,
        "workflow_completed": completed,
        "explicit_verification": explicit,
        "verification_required": not explicit,
        "note": "Delivery must not be marked complete until the underlying result is verified.",
    }


def build_package(workflow: Dict[str, Any]) -> Dict[str, Any]:
    if not workflow.get("id") or not workflow.get("goal"):
        raise ValueError("workflow id and goal are required")

    verification = _verification(workflow)
    goal = _clean(workflow["goal"], 1200)
    result = workflow.get("result") or {}

    deliverables: List[Dict[str, str]] = [
        {"name": "Project summary", "status": "ready", "description": goal},
        {"name": "Work result", "status": "ready" if verification["eligible"] else "pending_verification",
         "description": "Compiled from the verified workflow result."},
        {"name": "QA / verification report", "status": "ready" if verification["eligible"] else "pending",
         "description": "Checks performed and remaining verification requirements."},
        {"name": "Client handoff notes", "status": "draft", "description": "Client-facing summary, usage notes, and next steps."},
    ]

    artifact_id = "DEL-" + _hash(str(workflow["id"]), goal)
    return {
        "delivery_id": artifact_id,
        "workflow_id": str(workflow["id"]),
        "package_name": _slug(goal) + "-delivery",
        "status": "ready_for_approval" if verification["eligible"] else "blocked_pending_verification",
        "approval_required": True,
        "verification": verification,
        "deliverables": deliverables,
        "handoff": {
            "summary": f"Delivery package prepared for: {goal}",
            "next_steps": ["Review deliverables", "Approve external handoff", "Send/share through an approved channel"],
            "send_status": "draft_only",
        },
        "source_result": {
            "workflow_status": _status(workflow),
            "result_keys": sorted(str(k) for k in result.keys()),
        },
        "created_at": _now(),
        "safety": "No client message is sent, no payment is claimed, and no delivery is marked final without verification and approval.",
    }


def prepare(user_id: str, workflow: Dict[str, Any]) -> Dict[str, Any]:
    if str(workflow.get("user_id")) != str(user_id):
        raise PermissionError("workflow does not belong to user")
    return build_package(workflow)


def verify(package: Dict[str, Any], checks: Dict[str, Any] | None = None) -> Dict[str, Any]:
    checks = checks or {}
    required = ("deliverables_reviewed", "result_checked")
    missing = [key for key in required if not bool(checks.get(key))]
    passed = not missing
    return {
        **package,
        "status": "verified_ready_for_approval" if passed else "blocked_pending_qa",
        "verification": {
            **(package.get("verification") or {}),
            "explicit_verification": passed,
            "qa_passed": passed,
            "missing_checks": missing,
            "verified_at": _now() if passed else None,
        },
        "handoff": {
            **(package.get("handoff") or {}),
            "send_status": "draft_only",
        },
    }
