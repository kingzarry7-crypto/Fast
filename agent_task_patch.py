"""Additive FastAPI patch for the V5.3 Agent Task Engine."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field


class AgentTaskCreateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    max_steps: int = Field(default=6, ge=1, le=8)


def install_agent_task_api(app: Any, require_current_user: Any, require_vip: Any) -> None:
    if app is None or require_current_user is None or require_vip is None:
        raise RuntimeError("agent task patch requires app and current-user auth")

    from agent_task_engine import (
        cancel_task,
        create_task,
        list_tasks,
        run_task,
        task_status,
        _load,
    )

    @app.get("/api/agent/tasks/status")
    async def agent_task_status_endpoint(request: Request):
        try:
            user_row = require_current_user(request)
            require_vip(user_row)
            return {"status": "success", **task_status()}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Task status failed: {type(exc).__name__}")

    @app.get("/api/agent/tasks")
    async def agent_task_list_endpoint(request: Request):
        try:
            user_row = require_current_user(request)
            user_id = str(require_vip(user_row))
            return {"status": "success", "tasks": list_tasks(user_id)}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Task list failed: {type(exc).__name__}")

    @app.post("/api/agent/tasks")
    async def agent_task_create_endpoint(request: Request, body: AgentTaskCreateRequest):
        try:
            user_row = require_current_user(request)
            user_id = str(require_vip(user_row))
            task = run_task(user_id, body.goal, max_steps=body.max_steps)
            return {"status": "success", "task": task}
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RuntimeError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Task create failed: {type(exc).__name__}")

    @app.get("/api/agent/tasks/{task_id}")
    async def agent_task_get_endpoint(request: Request, task_id: str):
        try:
            user = require_current_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            user_id = str(user.get("id") if isinstance(user, dict) else getattr(user, "id", user))
            task = _load(task_id, user_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"status": "success", "task": task}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Task read failed: {type(exc).__name__}")

    @app.post("/api/agent/tasks/{task_id}/cancel")
    async def agent_task_cancel_endpoint(request: Request, task_id: str):
        try:
            user = require_current_user(request)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            user_id = str(user.get("id") if isinstance(user, dict) else getattr(user, "id", user))
            task = cancel_task(task_id, user_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"status": "success", "task": task}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Task cancel failed: {type(exc).__name__}")

    print("AGENT_TASK_ENGINE_PATCH_INSTALLED", flush=True)
