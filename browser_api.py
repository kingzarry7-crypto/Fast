"""Authenticated API endpoints for the KZ browser operator."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, Request


def install_browser_api(app, require_current_user, row_value=None):
    def uid(row):
        try:
            value = row_value(row, "id", 0) if row_value else row.get("id")
            return str(value or "")
        except Exception:
            return ""

    @app.get("/api/browser/status")
    def browser_status(request: Request):
        row = require_current_user(request)
        if not uid(row):
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import status
        return {"status": "ok", "browser": status()}

    @app.get("/api/browser/inspect")
    def browser_inspect(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        from browser_operator import inspect
        try:
            return {"status": "ok", "page": inspect(user_id)}
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
        approved = bool(body.get("approved"))
        if not isinstance(actions, list) or not actions:
            raise HTTPException(status_code=400, detail="actions are required")
        external = any(str(a.get("type") or "").lower() in {"submit","post","publish","send"} for a in actions if isinstance(a, dict))
        if external and not approved:
            return {"status": "awaiting_approval", "approval_required": True, "actions": actions}
        from browser_operator import execute_plan
        try:
            result = execute_plan(user_id, actions, allow_external=approved)
            return {"status": "ok", "result": result}
        except Exception as exc:
            return {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)[:500]}"}

    return app
