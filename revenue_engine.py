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
