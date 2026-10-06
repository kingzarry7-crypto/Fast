"""Authenticated API endpoints for the KZ browser operator."""
from __future__ import annotations

import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from fastapi import HTTPException, Request


# Playwright Sync API must never run on FastAPI's asyncio event-loop thread.
# Keep one dedicated browser thread so persistent Playwright objects retain thread affinity.
_BROWSER_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kz-playwright")

async def _browser_call(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_BROWSER_EXECUTOR, lambda: fn(*args, **kwargs))

def _snapshot(user_id: str):
    from browser_operator import inspect, screenshot
    page = inspect(user_id)
    image = base64.b64encode(screenshot(user_id)).decode("ascii")
    page["screenshot"] = "data:image/png;base64," + image
    return page


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
                result = await _browser_call(click, user_id, body.get("selector"), body.get("text"))
            elif kind == "fill":
                result = await _browser_call(fill, user_id, str(body.get("selector") or ""), str(body.get("value") or ""))
            elif kind == "select":
                result = await _browser_call(select, user_id, str(body.get("selector") or ""), str(body.get("value") or ""))
            elif kind == "refresh":
                result = await _browser_call(inspect, user_id)
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
        approved = bool(body.get("approved"))
        if not isinstance(actions, list) or not actions:
            raise HTTPException(status_code=400, detail="actions are required")
        external = any(str(a.get("type") or "").lower() in {"submit", "post", "publish", "send"} for a in actions if isinstance(a, dict))
        if external and not approved:
            return {"status": "awaiting_approval", "approval_required": True, "actions": actions}
        from browser_operator import execute_plan
        try:
            result = await _browser_call(execute_plan, user_id, actions, allow_external=approved)
            return {"status": "ok", "result": result}
        except Exception as exc:
            return {"status": "failed", "error": f"{type(exc).__name__}: {str(exc)[:500]}"}

    return app
