"""KING ZARRY AI — Job Outreach Agent.

Autonomous, read-only opportunity discovery plus approval-ready application
preparation. It never submits an application, sends outreach, spends money,
or claims revenue without an explicitly approved workflow and supported
execution path.
"""
from __future__ import annotations

from typing import Any, Dict, List

import opportunity_hunter
import client_acquisition


def scan(
    user_id: str,
    *,
    query: str = "",
    category: str = "jobs",
    max_results: int = 12,
) -> Dict[str, Any]:
    """Research current public opportunities and rank them for the user."""
    result = opportunity_hunter.hunt(
        str(user_id),
        category=category if category in {"clients", "jobs", "saas", "news"} else "jobs",
        query=str(query or "").strip(),
        max_results=max(3, min(int(max_results), 30)),
    )
    opportunities = result.get("opportunities") or []
    for item in opportunities:
        is_news = str(item.get("category") or "").lower() == "news"
        item["application_ready"] = not is_news
        item["approval_required"] = False if is_news else True
        item["execution_status"] = "report_only" if is_news else "draft_only"
    return {
        "success": bool(result.get("success")),
        "opportunities": opportunities,
        "count": len(opportunities),
        "searched_queries": result.get("searched_queries") or [],
        "sources": result.get("sources") or [],
        "report": _report(opportunities),
        "disclaimer": result.get("disclaimer"),
        "mode": "news_report" if str(category).lower() == "news" else "opportunity_scan",
    }


def prepare_application(
    user_id: str,
    opportunity: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a truthful, source-aware application draft and workflow."""
    if not opportunity.get("url") or not opportunity.get("title"):
        raise ValueError("opportunity title and url are required")

    acquisition = client_acquisition.prepare(str(user_id), dict(opportunity))

    from workflow_engine import create_workflow

    source_kind = str(
        opportunity.get("source_kind")
        or acquisition.get("qualification", {}).get("source_kind")
        or "unknown"
    ).strip().lower()

    goal = (
        f"Prepare an approval-ready application for the {source_kind} opportunity "
        f'"{opportunity.get("title")}". Source: {opportunity.get("url")}. '
        "Verify the opportunity is still open and review its requirements. "
        "Use the prepared application draft. Do not send, submit, publish, "
        "contact anyone, spend money, or claim success until explicit user approval."
    )
    workflow = create_workflow(str(user_id), goal)

    workflow["context"] = {
        **(workflow.get("context") or {}),
        "job_outreach": True,
        "opportunity": opportunity,
        "acquisition": acquisition,
    }

    # Persist the acquisition package into the workflow so the approval
    # screen/report has the exact draft that the user is approving.
    from workflow_store import save_workflow
    save_workflow(workflow)

    return {
        "status": "draft_ready",
        "approval_required": True,
        "source_kind": source_kind,
        "opportunity": opportunity,
        "acquisition": acquisition,
        "workflow": workflow,
        "execution_status": "draft_only",
    }


def approval_report(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact approval/report object for UI, Telegram, or Discord."""
    context = workflow.get("context") or {}
    opportunity = context.get("opportunity") or {}
    acquisition = context.get("acquisition") or {}
    qualification = acquisition.get("qualification") or {}
    outreach = acquisition.get("outreach") or {}
    return {
        "workflow_id": workflow.get("id"),
        "status": workflow.get("status"),
        "title": opportunity.get("title"),
        "url": opportunity.get("url"),
        "source_kind": (
            opportunity.get("source_kind")
            or qualification.get("source_kind")
            or "unknown"
        ),
        "fit_score": qualification.get("fit_score"),
        "estimated_value": opportunity.get("estimated_value"),
        "proposal": {
            "subject": outreach.get("subject"),
            "message": outreach.get("message"),
        },
        "approval_required": True,
        "execution_status": _execution_status(workflow),
        "confirmed_revenue": 0.0,
        "note": (
            "Estimated value is not income. Confirmed revenue remains zero "
            "until a real payment/receipt source confirms it."
        ),
    }


def _execution_status(workflow: Dict[str, Any]) -> str:
    result = workflow.get("result") or {}
    browser = result.get("browser_execute") or {}
    verification = browser.get("verification") or {}
    status = verification.get("verification_status")
    if status == "verified_sent":
        return "verified_sent"
    if status == "not_verified":
        return "sent_not_verified"
    if workflow.get("status") == "waiting_for_approval":
        return "awaiting_approval"
    if workflow.get("status") == "completed":
        return "completed"
    return "draft_only"


def _report(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    high = [
        item for item in opportunities
        if str(item.get("confidence") or "").lower() == "high"
        or int(item.get("score") or 0) >= 70
    ]
    estimated = round(
        sum(float(item.get("estimated_value") or 0) for item in high),
        2,
    )
    return {
        "headline": f"{len(opportunities)} opportunities found; {len(high)} high-match",
        "high_match_count": len(high),
        "estimated_value": estimated,
        "top_opportunities": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "score": item.get("score"),
                "estimated_value": item.get("estimated_value"),
                "source_kind": item.get("source_kind"),
                "next_action": item.get("next_action"),
            }
            for item in opportunities[:5]
        ],
        "warning": "Estimated opportunity value is not guaranteed income.",
    }
