"""KZ Revenue Engine.

Tracks opportunity value separately from confirmed revenue. It never fabricates
payments and never performs money movement.
"""
from __future__ import annotations

from typing import Any, Dict, List


def rank_opportunities(rows: List[Dict[str, Any]], target: float = 200.0) -> List[Dict[str, Any]]:
    ranked = []
    for row in rows or []:
        title = str(row.get("title") or "Untitled opportunity")
        text = str(row.get("content") or row.get("reason") or "")
        score = float(row.get("score") or 0)
        if any(k in (title + " " + text).lower() for k in ("client", "freelance", "website", "contract", "project", "service")):
            score += 0.25
        ranked.append({**row, "opportunity_score": round(score, 4), "target_revenue": float(target)})
    return sorted(ranked, key=lambda x: x.get("opportunity_score", 0), reverse=True)


def revenue_summary(workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
    potential = sum(float(x.get("potential_revenue") or 0) for x in workflows)
    confirmed = 0.0
    costs = sum(float(x.get("estimated_cost") or 0) for x in workflows)
    return {
        "potential_revenue": round(potential, 2),
        "confirmed_revenue": round(confirmed, 2),
        "estimated_cost": round(costs, 2),
        "profit_confirmed": round(confirmed - costs, 2),
        "warning": "Potential revenue is not income until a supported payment record confirms receipt.",
    }


def revenue_dashboard(workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a conservative revenue pipeline view from persistent workflows."""
    rows = list(workflows or [])
    active = [x for x in rows if x.get("status") not in {"completed", "failed", "paused"}]
    completed = [x for x in rows if x.get("status") == "completed"]
    waiting = [x for x in rows if x.get("status") == "waiting_for_approval"]
    potential = sum(float(x.get("potential_revenue") or 0) for x in rows)
    costs = sum(float(x.get("estimated_cost") or 0) for x in rows)
    return {
        "potential_revenue": round(potential, 2),
        "confirmed_revenue": 0.0,
        "estimated_cost": round(costs, 2),
        "confirmed_profit": round(-costs, 2),
        "active_work": len(active),
        "waiting_for_approval": len(waiting),
        "completed_work": len(completed),
        "pipeline": [
            {
                "workflow_id": x.get("id"),
                "goal": x.get("goal"),
                "status": x.get("status"),
                "potential_revenue": float(x.get("potential_revenue") or 0),
                "risk": x.get("risk"),
            }
            for x in rows[:20]
        ],
        "warning": "Potential revenue is a forecast, not income. Confirmed revenue remains zero until a supported payment record confirms receipt.",
    }
