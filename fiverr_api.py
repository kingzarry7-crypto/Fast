"""KING ZARRY AI — Fiverr Agent API.

Additive Railway API layer for the separate Fiverr Agent.
This API exposes the existing task/workspace/approval system without
automating unauthorized Fiverr browser actions.
"""

from __future__ import annotations

import hmac
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

import fiverr_agent

router = APIRouter(prefix="/api/fiverr", tags=["Fiverr Agent"])

FIVERR_AGENT_API_KEY = (os.getenv("FIVERR_AGENT_API_KEY") or "").strip()


def _authorize(x_fiverr_agent_key: Optional[str]) -> None:
    if not FIVERR_AGENT_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="FIVERR_AGENT_API_KEY is not configured on Railway",
        )
    if not x_fiverr_agent_key or not hmac.compare_digest(
        str(x_fiverr_agent_key), FIVERR_AGENT_API_KEY
    ):
        raise HTTPException(status_code=401, detail="Invalid Fiverr Agent API key")


class TaskRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    data: Dict[str, Any] = Field(default_factory=dict)


class TaskUpdateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    status: Optional[str] = Field(default=None, max_length=80)
    title: Optional[str] = Field(default=None, max_length=200)
    data: Optional[Dict[str, Any]] = None


class WorkspaceRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    workspace: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    approved: bool


class PolicyRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=30000)


class DraftRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=1, max_length=12000)


@router.get("/health")
def health(x_fiverr_agent_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {
        "status": "ok",
        "agent": "FIVERR AGENT",
        "api": "railway",
        "skills": len(fiverr_agent.SKILLS),
        "supported_actions": sorted(fiverr_agent.SUPPORTED_ACTIONS),
        "execution_mode": "approval_gated_supported_integration_only",
    }


@router.get("/skills")
def skills(x_fiverr_agent_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {"status": "success", "skills": fiverr_agent.SKILLS}


@router.get("/workspace/{user_id}")
def workspace(
    user_id: str,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    value = fiverr_agent.get_workspace(user_id)
    return {"status": "success", "workspace": value}


@router.post("/workspace")
def save_workspace(
    body: WorkspaceRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    value = fiverr_agent.save_workspace(body.user_id, body.workspace)
    return {"status": "success", "workspace": value}


@router.get("/tasks/{user_id}")
def tasks(
    user_id: str,
    limit: int = 20,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {
        "status": "success",
        "tasks": fiverr_agent.list_tasks(user_id, max(1, min(limit, 50))),
    }


@router.get("/tasks/{user_id}/open")
def open_task(
    user_id: str,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {"status": "success", "task": fiverr_agent.get_open_task(user_id)}


@router.post("/tasks")
def create_task(
    body: TaskRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    task = fiverr_agent.create_task(body.user_id, body.kind, body.title, body.data)
    return {"status": "success", "task": task}


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    task = fiverr_agent.update_task(
        task_id,
        body.user_id,
        status=body.status,
        title=body.title,
        data=body.data,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Fiverr task not found")
    return {"status": "success", "task": task}


@router.post("/approvals")
def create_approval(
    body: ApprovalRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    approval = fiverr_agent.create_approval(body.user_id, body.action, body.payload)
    return {"status": "awaiting_approval", "approval": approval}


@router.get("/approvals/{approval_id}/{user_id}")
def get_approval(
    approval_id: str,
    user_id: str,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    approval = fiverr_agent.get_approval(approval_id, user_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Fiverr approval not found")
    return {"status": "success", "approval": approval}


@router.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    body: DecisionRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    approval = fiverr_agent.decide_approval(
        approval_id, body.user_id, body.approved
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Fiverr approval not found")
    return {"status": approval.get("status"), "approval": approval}


@router.post("/policy-check")
def policy_check(
    body: PolicyRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {"status": "success", **fiverr_agent.policy_check(body.draft)}


@router.get("/checklist")
def checklist(x_fiverr_agent_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _authorize(x_fiverr_agent_key)
    return {"status": "success", "checklist": fiverr_agent.gig_checklist()}


@router.post("/draft")
def draft(
    body: DraftRequest,
    x_fiverr_agent_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Use the existing AI engine to prepare Fiverr work; never publishes it."""
    _authorize(x_fiverr_agent_key)
    try:
        from ai_engine import AIEngine

        engine = AIEngine(memory=None)
        prompt = (
            f"{fiverr_agent.agent_system_instructions()}\n\n"
            "Prepare a Fiverr work draft from this instruction. "
            "If information is missing, clearly list the questions instead of inventing facts. "
            "Return only the useful draft/questions.\n\n"
            f"USER INSTRUCTION:\n{body.instruction}"
        )
        result = engine.ask(
            user_id=f"fiverr-agent:{body.user_id}",
            prompt=prompt,
            image=None,
        )
        if not result:
            raise RuntimeError("AI returned an empty draft")
        check = fiverr_agent.policy_check(result)
        task = fiverr_agent.create_task(
            body.user_id,
            "ai_draft",
            "Fiverr Agent AI draft",
            {"instruction": body.instruction, "draft": result, "policy": check},
        )
        return {
            "status": "draft_ready" if check["ok"] else "manual_review_required",
            "draft": result,
            "policy": check,
            "task": task,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Fiverr draft failed: {type(exc).__name__}",
        )
