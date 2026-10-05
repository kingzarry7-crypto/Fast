"""Channel adapters for the persistent KZ Work Engine.

This module contains no platform credentials and delegates all consequential
actions to workflow_engine / Action Gateway.
"""
from __future__ import annotations
from typing import Any

def create(user_id: str, goal: str) -> dict[str, Any]:
    from workflow_engine import create_workflow
    return create_workflow(str(user_id), goal)

def list_recent(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    from workflow_engine import list_workflows
    return list_workflows(str(user_id), max(1, min(int(limit), 20)))

def get(user_id: str, workflow_id: str) -> dict[str, Any] | None:
    from workflow_engine import get_workflow
    return get_workflow(str(workflow_id), str(user_id))

def approve(user_id: str, workflow_id: str, approved: bool) -> dict[str, Any]:
    from workflow_engine import approve_workflow
    return approve_workflow(str(workflow_id), str(user_id), bool(approved))

def format_workflow(item: dict[str, Any]) -> str:
    status = str(item.get("status", "unknown")).replace("_", " ").upper()
    risk = str(item.get("risk", "green")).upper()
    potential = float(item.get("potential_revenue") or 0)
    lines = ["🤖 <b>KZ WORK</b>", "", f"<b>Goal:</b> {item.get('goal', '')[:900]}", f"<b>Status:</b> {status}", f"<b>Risk:</b> {risk}", f"<b>Potential:</b> ${potential:.0f}", f"<b>ID:</b> <code>{item.get('id', '')}</code>"]
    waiting = next((s for s in item.get("plan", []) if s.get("status") == "waiting_for_approval"), None)
    if waiting:
        lines += ["", "🟡 <b>APPROVAL REQUIRED</b>", str(waiting.get("title", "Consequential action"))[:700], f"Use <code>/work approve {item.get('id')}</code> to approve.", f"Use <code>/work reject {item.get('id')}</code> to reject."]
    return "\n".join(lines)

def format_recent(items: list[dict[str, Any]]) -> str:
    if not items:
        return "🤖 <b>KZ WORK</b>\n\nNo workflows yet.\nUse <code>/work Find me 5 legitimate website clients this week</code>."
    lines = ["🤖 <b>RECENT KZ WORK</b>", ""]
    for item in items[:5]:
        lines.append(f"• <code>{item.get('id','')[:8]}</code> {str(item.get('status','')).replace('_',' ')} — {str(item.get('goal',''))[:120]}")
    return "\n".join(lines)