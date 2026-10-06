"""KZ Layer 11 — long-term learning loop.

Turns verified workflow outcomes into small, durable, user-scoped lessons.
It never learns secrets, credentials, approval tokens, or raw external messages.
"""
from __future__ import annotations
from typing import Any, Dict, List


def _clean(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]



def _verified_outcome(workflow: Dict[str, Any]) -> bool:
    """Return True only when the workflow contains explicit outcome evidence."""
    result = workflow.get("result") or {}
    verification = result.get("verification") or {}
    if verification.get("verification_status") == "verified_sent" or verification.get("verified") is True:
        return True

    browser_result = result.get("browser_execute") or {}
    verification = browser_result.get("verification") or {}
    if verification.get("verification_status") == "verified_sent" or verification.get("verified") is True:
        return True

    for step in workflow.get("plan") or []:
        output = step.get("output") or {}
        verification = output.get("verification") or {}
        if verification.get("verification_status") == "verified_sent" or verification.get("verified") is True:
            return True
        if step.get("action") == "browser_verify" and output.get("success") is True:
            return True

    # Non-external workflows can be learned from their completed/failed
    # execution state; consequential outcomes require explicit evidence above.
    has_external = any(
        step.get("action") in {"browser_execute", "external_action"}
        or step.get("requires_approval") is True
        for step in (workflow.get("plan") or [])
    )
    return not has_external and workflow.get("status") == "completed"

def extract_lessons(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    goal = _clean(workflow.get("goal"), 240)
    status = _clean(workflow.get("status"))
    result = workflow.get("result") or {}
    lessons: List[Dict[str, Any]] = []

    if not goal:
        return lessons

    if status == "completed" and _verified_outcome(workflow):
        lessons.append({
            "type": "workflow_success",
            "lesson": f"Successful workflow pattern: {goal}",
            "confidence": 0.85,
        })
    elif status == "failed":
        failed = [s for s in (workflow.get("plan") or []) if s.get("status") == "failed"]
        action = failed[0].get("action") if failed else "unknown"
        lessons.append({
            "type": "workflow_failure",
            "lesson": f"Workflow failure pattern for '{goal}'; failed action: {_clean(action, 120)}",
            "confidence": 0.75,
        })
    elif result.get("approval_rejected"):
        lessons.append({
            "type": "approval_feedback",
            "lesson": f"Approval was rejected for workflow: {goal}",
            "confidence": 0.70,
        })

    if result.get("research") and (status != "completed" or _verified_outcome(workflow)):
        lessons.append({
            "type": "research_pattern",
            "lesson": f"Research-backed workflow: {goal}",
            "confidence": 0.65,
        })
    return lessons[:4]


def learn_from_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(workflow.get("user_id") or "").strip()
    lessons = extract_lessons(workflow)
    stored = 0
    if user_id and lessons:
        try:
            from shared_memory import SharedMemory
            memory = SharedMemory("workflow")
            for lesson in lessons:
                memory.add_fact(
                    user_id,
                    lesson["lesson"],
                    category="workflow_lesson",
                    source="verified_workflow",
                )
                stored += 1
        except Exception:
            # Learning must never break workflow completion.
            stored = 0
    return {
        "learned": len(lessons),
        "stored": stored,
        "lesson_types": [x["type"] for x in lessons],
    }


def learning_snapshot(user_id: str, limit: int = 20) -> Dict[str, Any]:
    try:
        from shared_memory import SharedMemory
        memory = SharedMemory("workflow")
        facts = memory.get_facts(str(user_id), category="workflow_lesson", limit=limit)
        return {"count": len(facts), "lessons": facts}
    except Exception as exc:
        return {"count": 0, "lessons": [], "error": type(exc).__name__}
