"""KZ Business Command Center.

Aggregates existing workflow, revenue, opportunity and delivery signals into one
authenticated dashboard response. It does not create a second business ledger.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _status(rows: List[Dict[str, Any]], name: str) -> int:
    return sum(1 for x in rows if str(x.get("status") or "") == name)


def build_business_dashboard(workflows: List[Dict[str, Any]], opportunities: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    rows = list(workflows or [])
    opportunities = list(opportunities or [])
    potential = round(sum(float(x.get("potential_revenue") or 0) for x in rows), 2)
    costs = round(sum(float(x.get("estimated_cost") or 0) for x in rows), 2)
    completed = _status(rows, "completed")
    active = sum(1 for x in rows if str(x.get("status") or "") not in {"completed", "failed", "paused"})
    approval = _status(rows, "waiting_for_approval")
    failed = _status(rows, "failed")
    high_value = sorted(
        [x for x in rows if float(x.get("potential_revenue") or 0) > 0],
        key=lambda x: float(x.get("potential_revenue") or 0),
        reverse=True,
    )[:5]

    return {
        "potential_revenue": potential,
        "confirmed_revenue": 0.0,
        "estimated_cost": costs,
        "confirmed_profit": round(-costs, 2),
        "kpis": {
            "active_work": active,
            "waiting_for_approval": approval,
            "completed_work": completed,
            "failed_work": failed,
            "opportunities_seen": len(opportunities),
            "delivery_ready": completed,
        },
        "funnel": {
            "opportunities": len(opportunities),
            "prepared_work": len(rows),
            "active": active,
            "completed": completed,
            "failed": failed,
        },
        "priority_work": [
            {
                "workflow_id": x.get("id"),
                "goal": x.get("goal"),
                "status": x.get("status"),
                "potential_revenue": float(x.get("potential_revenue") or 0),
                "risk": x.get("risk"),
            }
            for x in high_value
        ],
        "next_actions": (
            ["Review pending approvals"] if approval else []
        ) + (
            ["Run Opportunity Hunt to find new business"] if not opportunities else []
        ) + (
            ["Prepare completed work for delivery"] if completed else []
        ),
        "warning": "Potential revenue is a forecast. Confirmed revenue remains zero until a supported payment record confirms receipt.",
    }
