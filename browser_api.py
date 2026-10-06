"""Authenticated API endpoints for the KZ browser operator."""
from __future__ import annotations

import base64
import asyncio
import hashlib
import json
from typing import Any, Dict

from fastapi import HTTPException, Request


# Playwright Sync API must never run on FastAPI's asyncio event-loop thread.
# Keep one dedicated browser thread so persistent Playwright objects retain thread affinity.
async def _browser_call(fn, *args, **kwargs):
    from browser_operator import run_in_browser_thread
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: run_in_browser_thread(fn, *args, **kwargs))

def _snapshot(user_id: str):
    from browser_operator import inspect, screenshot, viewport
    page = inspect(user_id)
    image = base64.b64encode(screenshot(user_id)).decode("ascii")
    page["screenshot"] = "data:image/png;base64," + image
    page["viewport"] = viewport(user_id)
    return page


def _external_browser_action(action: Any) -> bool:
    if not isinstance(action, dict):
        return False
    kind = str(action.get("type") or "").lower()
    if kind in {"submit", "post", "publish", "send"}:
        return True
    if kind == "click":
        target = (str(action.get("text") or "") + " " + str(action.get("selector") or "")).lower()
        return any(word in target for word in (
            "send", "submit", "apply", "place bid", "send proposal", "publish"
        ))
    return False

def install_browser_api(app, require_current_user, row_value=None):
    def uid(row):
        try:
            value = row_value(row, "id", 0) if row_value else row.get("id")
            return str(value or "")
        except Exception:
            return ""

    @app.post("/api/browser/connect/start")
    async def browser_connect_start(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        body = await request.json()
        url = str(body.get("url") or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="url is required")
        from browser_operator import navigate
        try:
            page = await _browser_call(navigate, user_id, url)
            return {
                "status": "ok",
                "connection": {
                    "url": page["url"],
                    "title": page["title"],
                    "message": "Login yourself in the KZ browser session. Credentials are not stored by KZ.",
                },
                "page": await _browser_call(_snapshot, user_id),
            }
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"{type(exc).__name__}: {str(exc)[:300]}")

    @app.get("/api/browser/connect/status")
    async def browser_connect_status(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import connection_status
        try:
            return {"status": "ok", "connection": await _browser_call(connection_status, user_id)}
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"{type(exc).__name__}: {str(exc)[:300]}")

    @app.post("/api/browser/connect/confirm")
    async def browser_connect_confirm(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import confirm_connection
        try:
            connection = await _browser_call(confirm_connection, user_id)
            return {"status": "ok", "connection": connection}
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"{type(exc).__name__}: {str(exc)[:300]}")

    @app.post("/api/browser/connect/task")
    async def browser_connect_task(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        body = await request.json()
        goal = str((body or {}).get("goal") or "").strip()
        if not goal:
            raise HTTPException(status_code=400, detail="goal is required")
        if len(goal) > 4000:
            raise HTTPException(status_code=400, detail="goal is too long")
        from browser_operator import connection_status
        connection = await _browser_call(connection_status, user_id)
        if connection.get("status") != "connected":
            raise HTTPException(status_code=409, detail="Connect the account first. Complete login, then confirm the connected session.")
        from workflow_engine import create_workflow
        workflow = create_workflow(user_id, goal)
        return {"status": "ok", "workflow": workflow}

    @app.post("/api/browser/connect/action")
    async def browser_connect_action(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        body = await request.json()
        kind = str(body.get("type") or "").lower()
        from browser_operator import click, fill, select, inspect
        try:
            if kind == "click":
                target = (str(body.get("text") or "") + " " + str(body.get("selector") or "")).lower()
                if any(word in target for word in ("send", "submit", "apply", "place bid", "send proposal", "publish")):
                    raise PermissionError("Consequential marketplace/browser clicks require an approved workflow.")
                result = await _browser_call(click, user_id, body.get("selector"), body.get("text"))
            elif kind == "fill":
                result = await _browser_call(fill, user_id, str(body.get("selector") or ""), str(body.get("value") or ""))
            elif kind == "select":
                result = await _browser_call(select, user_id, str(body.get("selector") or ""), str(body.get("value") or ""))
            elif kind == "refresh":
                result = await _browser_call(inspect, user_id)
            elif kind == "human_click":
                from browser_operator import human_click
                result = await _browser_call(
                    human_click, user_id, float(body.get("x")), float(body.get("y"))
                )
            elif kind == "manual_click":
                from browser_operator import manual_click
                result = await _browser_call(
                    manual_click, user_id, float(body.get("x")), float(body.get("y"))
                )
            elif kind == "human_down":
                from browser_operator import human_down
                result = await _browser_call(
                    human_down, user_id, float(body.get("x")), float(body.get("y"))
                )
            elif kind == "human_up":
                from browser_operator import human_up
                result = await _browser_call(
                    human_up, user_id, float(body.get("x")), float(body.get("y"))
                )
            elif kind == "human_press":
                from browser_operator import human_press
                result = await _browser_call(
                    human_press,
                    user_id,
                    float(body.get("x")),
                    float(body.get("y")),
                    int(body.get("duration_ms") or 1000),
                )
            elif kind == "human_move":
                from browser_operator import human_move
                result = await _browser_call(
                    human_move, user_id, float(body.get("x")), float(body.get("y"))
                )
            elif kind == "human_verify":
                from browser_operator import check_human_verification
                result = await _browser_call(check_human_verification, user_id)
            else:
                raise ValueError("unsupported connection action")
            return {"status": "ok", "result": result, "page": await _browser_call(_snapshot, user_id)}
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"{type(exc).__name__}: {str(exc)[:400]}")

    @app.post("/api/browser/connect/close")
    async def browser_connect_close(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import close
        await _browser_call(close, user_id)
        return {"status": "ok", "message": "Browser session closed. Persistent session data remains on the configured browser profile volume."}

    @app.get("/api/browser/status")
    def browser_status(request: Request):
        row = require_current_user(request)
        if not uid(row):
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import status
        return {"status": "ok", "browser": status()}

    @app.get("/api/browser/inspect")
    async def browser_inspect(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        try:
            return {"status": "ok", "page": await _browser_call(_snapshot, user_id)}
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"{type(exc).__name__}: {str(exc)[:300]}")

    @app.post("/api/browser/run")
    async def browser_run(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        body: Dict[str, Any] = await request.json()
        actions = body.get("actions") or []
        workflow_id = str(body.get("workflow_id") or "").strip()
        if not isinstance(actions, list) or not actions:
            raise HTTPException(status_code=400, detail="actions are required")
        external = any(_external_browser_action(a) for a in actions)

        # Never trust a client-supplied approved=true for consequential browser actions.
        if external:
            if not workflow_id:
                raise HTTPException(status_code=403, detail="External browser actions require an approved workflow_id.")
            try:
                from workflow_engine import get_workflow
                workflow = get_workflow(workflow_id, user_id)
            except Exception:
                workflow = None
            if not workflow:
                raise HTTPException(status_code=404, detail="Approved workflow not found")

            canonical = json.dumps(actions, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            matched = None
            for step in workflow.get("plan") or []:
                if step.get("action") == "browser_execute" and step.get("approval_id") and step.get("browser_action_fingerprint") == fingerprint:
                    matched = step
                    break
            if not matched:
                raise HTTPException(status_code=409, detail="Browser actions do not match the exact approved workflow plan.")

            if matched.get("status") == "waiting_for_approval" or workflow.get("status") in {"waiting_for_approval", "paused"}:
                return {"status": "awaiting_approval", "approval_required": True, "workflow_id": workflow_id}
            if workflow.get("status") not in {"approved", "executing", "verifying", "completed"}:
                raise HTTPException(status_code=409, detail=f"Workflow is not in an approved execution state: {workflow.get('status')}")

        from browser_operator import execute_plan
        try:
            result = await _browser_call(execute_plan, user_id, actions, allow_external=external)
            return {
                "status": "ok",
                "workflow_id": workflow_id or None,
                "approval_source": "workflow" if external else "none",
                "result": result,
            }
        except Exception as exc:
            return {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)[:500]}"}

    return app
