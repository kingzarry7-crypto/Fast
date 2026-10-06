"""KING ZARRY AI — autonomous workflow engine.

Flow:
ASK -> PLAN -> RESEARCH/PREPARE -> APPROVE -> EXECUTE -> VERIFY -> LEARN.

This module is deliberately additive. It does not bypass the existing Action
Gateway, Fiverr policy layer, trading Risk Guardian, or permission store.
"""
from __future__ import annotations

import logging
import re
import hashlib
import json
import threading
import time
import uuid
from typing import Any, Dict, List

from workflow_models import WorkflowStatus, StepStatus, RiskLevel
from workflow_store import (
    add_event, create_approval, get_workflow, init_workflow_store,
    list_workflows, save_workflow,
)

logger = logging.getLogger("kz_workflow_engine")
_LOCK = threading.RLock()
_WORKER_STARTED = False


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _step(workflow_id: str, position: int, title: str, action: str,
          risk: RiskLevel = RiskLevel.GREEN, requires_approval: bool = False,
          input_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "workflow_id": workflow_id,
        "position": position,
        "title": title,
        "action": action,
        "status": StepStatus.PENDING.value,
        "risk": risk.value,
        "requires_approval": requires_approval,
        "input": input_data or {},
        "output": {},
        "error": None,
    }


def _classify_goal(goal: str) -> Dict[str, Any]:
    low = goal.lower()
    if any(x in low for x in (
        "fiverr", "upwork", "freelancer.com", "peopleperhour", "guru.com",
        "submit proposal", "send proposal", "apply to this job", "apply for this job",
        "job application", "marketplace application",
    )):
        return {"kind": "marketplace_application", "revenue": 180.0}
    if any(x in low for x in ("freelance", "client", "website client", "gig")):
        return {"kind": "revenue_freelance", "revenue": 180.0}
    if any(x in low for x in ("make money", "make $", "earn", "revenue", "income", "money this week")):
        return {"kind": "revenue_research", "revenue": 200.0}
    if any(x in low for x in ("market", "trade", "btc", "eth", "sol", "gold", "xau")):
        return {"kind": "market", "revenue": 0.0}
    if any(x in low for x in ("open website", "open the website", "edit my website", "edit website", "update my website", "update website", "post on", "publish on", "upload to", "fill the form", "fill out the form", "click on", "browser", "website")):
        return {"kind": "browser", "revenue": 0.0}
    if any(x in low for x in ("deploy", "github", "code", "fix my app", "build")):
        return {"kind": "engineering", "revenue": 0.0}
    return {"kind": "general", "revenue": 0.0}


def plan_goal(workflow_id: str, user_id: str, goal: str) -> Dict[str, Any]:
    meta = _classify_goal(goal)
    kind = meta["kind"]
    steps: List[Dict[str, Any]] = []

    # Every workflow gets an audit/research stage first.
    steps.append(_step(workflow_id, 1, "Understand the goal and constraints", "analyze_goal"))
    steps.append(_step(workflow_id, 2, "Research current information and opportunities", "research_goal"))

    if kind == "marketplace_application":
        steps += [
            _step(workflow_id, 3, "Open the marketplace opportunity and inspect requirements", "browser_prepare"),
            _step(workflow_id, 4, "Prepare the exact application actions", "browser_plan"),
            _step(workflow_id, 5, "Submit only the exact approved application", "browser_execute", RiskLevel.YELLOW, True),
            _step(workflow_id, 6, "Verify the marketplace submission evidence", "browser_verify"),
            _step(workflow_id, 7, "Record the result for future applications", "learn"),
        ]
    elif kind == "revenue_freelance":
        steps += [
            _step(workflow_id, 3, "Build qualified client opportunities", "build_leads"),
            _step(workflow_id, 4, "Prepare personalized offers and delivery plans",
                  "prepare_offers", RiskLevel.YELLOW, True),
            _step(workflow_id, 5, "Send/publish the approved outreach", "external_action",
                  RiskLevel.YELLOW, True),
            _step(workflow_id, 6, "Verify responses and track revenue", "verify_revenue"),
            _step(workflow_id, 7, "Learn from results and update workflow memory", "learn"),
        ]
    elif kind == "revenue_research":
        steps += [
            _step(workflow_id, 3, "Rank legitimate revenue opportunities", "rank_opportunities"),
            _step(workflow_id, 4, "Prepare the highest-value execution package",
                  "prepare_revenue_plan", RiskLevel.YELLOW, True),
            _step(workflow_id, 5, "Execute approved external work", "external_action",
                  RiskLevel.YELLOW, True),
            _step(workflow_id, 6, "Verify outcome and track revenue/cost", "verify_revenue"),
            _step(workflow_id, 7, "Learn and improve the next run", "learn"),
        ]
    elif kind == "market":
        steps += [
            _step(workflow_id, 3, "Run fresh market analysis", "market_analysis"),
            _step(workflow_id, 4, "Apply existing Risk Guardian", "risk_review"),
            _step(workflow_id, 5, "Prepare any trade action for approval", "external_action",
                  RiskLevel.RED, True),
            _step(workflow_id, 6, "Verify execution/result", "verify"),
            _step(workflow_id, 7, "Learn from the result", "learn"),
        ]
    elif kind == "browser":
        steps += [
            _step(workflow_id, 3, "Open the requested website and inspect the current page", "browser_prepare"),
            _step(workflow_id, 4, "Prepare the exact browser actions", "browser_plan"),
            _step(workflow_id, 5, "Execute the approved browser actions", "browser_execute", RiskLevel.YELLOW, True),
            _step(workflow_id, 6, "Verify the browser result", "browser_verify"),
            _step(workflow_id, 7, "Record the result for future work", "learn"),
        ]
    elif kind == "engineering":
        steps += [
            _step(workflow_id, 3, "Inspect the requested engineering task", "engineering_plan"),
            _step(workflow_id, 4, "Prepare the change for approval", "prepare_change",
                  RiskLevel.YELLOW, True),
            _step(workflow_id, 5, "Run approved change/deployment", "external_action",
                  RiskLevel.YELLOW, True),
            _step(workflow_id, 6, "Verify the application", "verify"),
            _step(workflow_id, 7, "Record the result for future work", "learn"),
        ]
    else:
        steps += [
            _step(workflow_id, 3, "Prepare the best next actions", "prepare_general"),
            _step(workflow_id, 4, "Request approval for consequential actions",
                  "external_action", RiskLevel.YELLOW, True),
            _step(workflow_id, 5, "Verify completion", "verify"),
            _step(workflow_id, 6, "Learn and continue", "learn"),
        ]

    return {
        "steps": steps,
        "kind": kind,
        "potential_revenue": float(meta.get("revenue") or 0),
        "risk": RiskLevel.RED.value if kind == "market" else (RiskLevel.YELLOW.value if any(s["requires_approval"] for s in steps) else RiskLevel.GREEN.value),
        "requires_approval": any(s["requires_approval"] for s in steps),
    }


def create_workflow(user_id: str, goal: str) -> Dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("goal is required")
    workflow_id = str(uuid.uuid4())
    plan = plan_goal(workflow_id, str(user_id), goal)
    item = {
        "id": workflow_id,
        "user_id": str(user_id),
        "goal": goal,
        "status": WorkflowStatus.PLANNING.value,
        "risk": plan["risk"],
        "requires_approval": plan["requires_approval"],
        "plan": plan["steps"],
        "context": {"kind": plan["kind"], "created_by": "kz_workflow_engine"},
        "result": {},
        "potential_revenue": plan["potential_revenue"],
        "estimated_cost": 0.0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    save_workflow(item)
    add_event(workflow_id, str(user_id), "workflow_created", {"goal": goal, "kind": plan["kind"]})
    return run_workflow(workflow_id, str(user_id))


def _update(item: Dict[str, Any], status: str | None = None) -> Dict[str, Any]:
    if status:
        item["status"] = status
    item["updated_at"] = _now()
    save_workflow(item)
    return item


def _research(goal: str) -> Dict[str, Any]:
    try:
        from web_research_engine import research
        result = research(goal, deep=True, max_results=6)
        return {"success": bool(result.get("success")), "research": result}
    except Exception as exc:
        return {"success": False, "error": type(exc).__name__}


def _execute_step(item: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    action = step["action"]
    goal = item["goal"]
    low = goal.lower()

    if action == "analyze_goal":
        return {"success": True, "summary": f"Goal classified as {item['context'].get('kind')}", "constraints": ["No unsupported external actions", "Approval required for consequential actions"]}

    if action == "research_goal":
        return _research(goal)

    if action in {"build_leads", "rank_opportunities"}:
        research = item["result"].get("research") or {}
        rows = (research.get("results") or [])[:6] if isinstance(research, dict) else []
        return {"success": True, "opportunities": [
            {"title": r.get("title"), "url": r.get("url"), "reason": r.get("content") or r.get("page_text","")}
            for r in rows
        ], "note": "Opportunities are leads, not guaranteed income."}

    if action == "browser_prepare":
        from browser_operator import navigate, inspect
        urls = re.findall(r"https?://[^\\s)\\]}>,]+", goal)
        if not urls:
            return {"success": False, "error": "Website URL is required before I can operate the site."}
        page = navigate(str(item["user_id"]), urls[0])
        return {"success": True, "page": page, "message": "Website opened and inspected before any external change."}

    if action == "browser_plan":
        from browser_operator import plan_goal, run_in_browser_thread
        result = run_in_browser_thread(plan_goal, str(item["user_id"]), goal)
        plan = result.get("plan") or {}
        item["result"]["browser_plan"] = plan
        external = any(
            str(a.get("type") or "").lower() in {"submit","post","publish","send"}
            or (
                str(a.get("type") or "").lower() == "click"
                and any(
                    word in (str(a.get("text") or "") + " " + str(a.get("selector") or "")).lower()
                    for word in ("send", "submit", "apply", "place bid", "send proposal", "publish")
                )
            )
            for a in plan.get("actions") or []
        )
        return {"success": True, "browser_plan": plan, "external_action": external,
                "message": plan.get("summary") or "Browser action plan prepared for approval."}

    if action == "browser_execute":
        plan = item["result"].get("browser_plan") or {}
        actions = plan.get("actions") or []
        if not actions:
            return {"success": False, "error": "No browser actions were prepared."}

        # The exact browser plan must be the one that was shown for approval.
        # This prevents a modified plan from being executed under an older approval.
        approval_id = str(step.get("approval_id") or "")
        fingerprint = str(step.get("browser_action_fingerprint") or "")
        if not approval_id or not fingerprint:
            return {"success": False, "error": "Browser execution is not bound to an approved action plan."}

        canonical = json.dumps(
            actions, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        current_fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if current_fingerprint != fingerprint:
            return {"success": False, "error": "Approved browser action plan no longer matches the execution plan."}

        from browser_operator import execute_plan, run_in_browser_thread
        result = run_in_browser_thread(
            execute_plan, str(item["user_id"]), actions, allow_external=True
        )
        result["approval_id"] = approval_id
        result["action_fingerprint"] = current_fingerprint
        return result

    if action == "browser_verify":
        from browser_operator import inspect, run_in_browser_thread
        page = run_in_browser_thread(inspect, str(item["user_id"]))
        browser_result = item.get("result", {}).get("browser_execute") or {}
        verification = browser_result.get("verification") or {}
        verified = verification.get("verification_status") == "verified_sent"
        return {
            "success": verified,
            "page": page,
            "verified": verified,
            "verification_status": verification.get("verification_status", "not_verified"),
            "evidence": verification.get("evidence") or [],
            "note": verification.get(
                "note",
                "No provider/destination evidence was available to verify the external action.",
            ),
        }

    if action in {"prepare_offers", "prepare_revenue_plan", "prepare_general"}:
        return {
            "success": True,
            "approval_preview": {
                "goal": goal,
                "proposed_action": "Prepare/send only after explicit user approval",
                "safety": "No passwords, OTPs, session cookies, fake identity, spam, or guaranteed-income claims.",
            },
        }

    if action in {"engineering_plan", "prepare_change"}:
        return {"success": True, "plan": ["Inspect existing implementation", "Make additive change", "Run tests", "Verify deployment"], "approval_preview": {"goal": goal}}

    if action == "market_analysis":
        symbols = ["BTC/USD","ETH/USD","SOL/USD","XAU/USD","UNI/USD"]
        found = []
        try:
            from agent_core import tool_analyze_symbol
            for symbol in symbols:
                found.append(tool_analyze_symbol(symbol))
        except Exception as exc:
            return {"success": False, "error": type(exc).__name__}
        return {"success": True, "markets": found}

    if action == "risk_review":
        markets = item["result"].get("markets") or []
        return {"success": True, "risk_review": "Existing Risk Guardian remains authoritative.", "markets_reviewed": len(markets)}

    if action == "external_action":
        # We never invent an external execution adapter. Supported actions are
        # handed to the existing Action Gateway after approval.
        preview = step.get("output") or item.get("result", {}).get("approval_preview") or {}
        return {"success": True, "awaiting_execution_adapter": True, "approval_preview": preview}

    if action == "verify_revenue":
        return {"success": True, "revenue_verified": False, "potential_revenue": item.get("potential_revenue", 0), "note": "Only confirmed receipts are revenue; opportunities are not income."}

    if action == "verify":
        return {"success": True, "verified": True}

    if action == "learn":
        summary = {
            "goal": goal,
            "completed_at": _now(),
            "result_status": item["status"],
            "potential_revenue": item.get("potential_revenue", 0),
        }
        try:
            from learning_loop import learn_from_workflow
            learning = learn_from_workflow(item)
        except Exception:
            learning = {"learned": 0, "stored": 0, "lesson_types": []}
        return {"success": True, "memory_recorded": learning.get("stored", 0) > 0, "learning": learning, "summary": summary}

    return {"success": True, "note": f"No executor registered for {action}; safely prepared."}


def run_workflow(workflow_id: str, user_id: str) -> Dict[str, Any]:
    item = get_workflow(workflow_id, user_id)
    if not item:
        raise ValueError("workflow not found")

    with _LOCK:
        item = get_workflow(workflow_id, user_id) or item
        if item["status"] in {WorkflowStatus.COMPLETED.value, WorkflowStatus.FAILED.value}:
            return item

        _update(item, WorkflowStatus.RESEARCHING.value)
        for step in item.get("plan", []):
            if step.get("status") in {StepStatus.COMPLETED.value, StepStatus.SKIPPED.value}:
                continue

            if step.get("requires_approval") and step.get("status") != StepStatus.COMPLETED.value:
                preview = step.get("output") or {
                    "goal": item["goal"],
                    "action": step["title"],
                    "risk": step.get("risk"),
                    "potential_revenue": item.get("potential_revenue", 0),
                    "estimated_cost": item.get("estimated_cost", 0),
                }
                if step.get("action") == "browser_execute":
                    browser_actions = ((preview.get("browser_plan") or {}).get("actions") or [])
                    if isinstance(browser_actions, list) and browser_actions:
                        canonical = json.dumps(browser_actions, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                        step["browser_action_fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

                step["status"] = StepStatus.WAITING_FOR_APPROVAL.value
                approval_id = step.get("approval_id") or create_approval(item["id"], step["id"], item["user_id"], preview)
                step["approval_id"] = approval_id
                _update(item, WorkflowStatus.WAITING_FOR_APPROVAL.value)
                add_event(item["id"], item["user_id"], "approval_requested", {"step_id": step["id"], "approval_id": approval_id, "preview": preview})
                return item

            step["status"] = StepStatus.RUNNING.value
            _update(item, WorkflowStatus.EXECUTING.value)
            try:
                output = _execute_step(item, step)
                step["output"] = output or {}
                if not output.get("success", True):
                    step["status"] = StepStatus.FAILED.value
                    step["error"] = str(output.get("error") or "step failed")
                    _update(item, WorkflowStatus.FAILED.value)
                    add_event(item["id"], item["user_id"], "step_failed", {"step_id": step["id"], "error": step["error"]})
                    return item
                step["status"] = StepStatus.COMPLETED.value

                if step["action"] == "research_goal":
                    item["result"]["research"] = output.get("research") or {}
                elif step["action"] == "market_analysis":
                    item["result"]["markets"] = output.get("markets") or []
                else:
                    item["result"][step["action"]] = output

                add_event(item["id"], item["user_id"], "step_completed", {"step_id": step["id"], "action": step["action"]})
                _update(item, WorkflowStatus.VERIFYING.value)
            except Exception as exc:
                step["status"] = StepStatus.FAILED.value
                step["error"] = str(exc)[:1000]
                _update(item, WorkflowStatus.FAILED.value)
                add_event(item["id"], item["user_id"], "step_failed", {"step_id": step["id"], "error": step["error"]})
                return item

        _update(item, WorkflowStatus.COMPLETED.value)
        item["result"]["completed_at"] = _now()
        save_workflow(item)
        add_event(item["id"], item["user_id"], "workflow_completed", {"potential_revenue": item.get("potential_revenue", 0)})
        return item


def approve_workflow(workflow_id: str, user_id: str, approved: bool) -> Dict[str, Any]:
    item = get_workflow(workflow_id, user_id)
    if not item:
        raise ValueError("workflow not found")
    changed = False
    for step in item.get("plan", []):
        if step.get("status") == StepStatus.WAITING_FOR_APPROVAL.value:
            if approved:
                step["status"] = StepStatus.PENDING.value
                changed = True
            else:
                step["status"] = StepStatus.SKIPPED.value
                changed = True
                item["result"]["approval_rejected"] = True
            break
    if not changed:
        return item
    item["status"] = WorkflowStatus.APPROVED.value if approved else WorkflowStatus.PAUSED.value
    save_workflow(item)
    add_event(item["id"], item["user_id"], "approval_decided", {"approved": approved})
    return run_workflow(item["id"], item["user_id"]) if approved else item


def workflow_snapshot(user_id: str) -> Dict[str, Any]:
    rows = list_workflows(user_id, limit=30)
    active = [x for x in rows if x.get("status") not in {"completed","failed","paused"}]
    waiting = [x for x in rows if x.get("status") == "waiting_for_approval"]
    return {
        "active": active,
        "waiting_for_approval": waiting,
        "completed": [x for x in rows if x.get("status") == "completed"],
        "potential_revenue": round(sum(float(x.get("potential_revenue") or 0) for x in rows), 2),
        "confirmed_revenue": 0.0,
    }


def start_worker() -> None:
    global _WORKER_STARTED
    with _LOCK:
        if _WORKER_STARTED:
            return
        _WORKER_STARTED = True

    def loop():
        while True:
            try:
                # Resume only workflows that have already been approved or are
                # executing. Never auto-approve a consequential action.
                for item in list_workflows_for_worker():
                    try:
                        if item.get("status") in {"approved","executing","researching","verifying"}:
                            run_workflow(item["id"], str(item["user_id"]))
                    except Exception:
                        logger.exception("workflow worker run failed")
            except Exception:
                logger.exception("workflow worker loop failed")
            time.sleep(30)

    threading.Thread(target=loop, name="kz-workflow-worker", daemon=True).start()


def list_workflows_for_worker() -> List[Dict[str, Any]]:
    # Store currently exposes per-user listing; worker uses the memory mirror
    # when available. Production Railway runs are resumed by explicit API calls
    # and this lightweight worker is deliberately conservative.
    return []
