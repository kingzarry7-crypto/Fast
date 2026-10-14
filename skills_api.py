"""Authenticated skills API.

This module only exposes capability metadata and routes requested work through the
existing user-scoped agent workflow. It does not execute submitted code itself.
"""
from fastapi import HTTPException, Request


def install_skills_api(app, require_current_user, row_value=None):
    from skill_registry import list_skills, get_skill, classify_skill_request

    def user_id_for(request: Request) -> str:
        row = require_current_user(request)
        try:
            value = row_value(row, "id", 0) if row_value else (
                row.get("id") if isinstance(row, dict) else row[0]
            )
            user_id = str(value or "").strip()
        except Exception:
            user_id = ""
        if not user_id:
            raise HTTPException(status_code=401, detail="Authenticated user required")
        return user_id

    @app.get("/api/skills")
    def skills_list(request: Request):
        user_id_for(request)
        return {"status": "ok", "skills": list_skills()}

    @app.get("/api/skills/{skill_id}")
    def skills_detail(skill_id: str, request: Request):
        user_id_for(request)
        skill = get_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return {"status": "ok", "skill": skill}

    @app.post("/api/skills/run")
    async def skills_run(request: Request):
        user_id = user_id_for(request)
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Request body must be valid JSON") from exc
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        goal = str(body.get("goal") or "").strip()
        skill_id = str(body.get("skill_id") or "").strip().lower()
        if not goal:
            raise HTTPException(status_code=400, detail="goal is required")
        if len(goal) > 4000:
            raise HTTPException(status_code=400, detail="goal must be 4000 characters or fewer")
        run_now = body.get("run_now", True)
        if not isinstance(run_now, bool):
            raise HTTPException(status_code=400, detail="run_now must be a boolean")
        account_id = body.get("account_id")
        if account_id is not None and not isinstance(account_id, (str, int)):
            raise HTTPException(status_code=400, detail="account_id must be a string or integer")
        skill = get_skill(skill_id) if skill_id else get_skill(classify_skill_request(goal))
        if not skill:
            raise HTTPException(status_code=404, detail="Unknown skill")
        # The existing agent is the execution coordinator; it owns workflow
        # persistence, approvals, and external-action policy.
        from kz_agent import run
        result = run(
            user_id,
            goal,
            account_id=str(account_id or "").strip() or None,
            run_now=run_now,
            requested_skill=skill["id"],
        )
        return {
            "status": "ok",
            "skill": {
                "id": skill["id"],
                "name": skill["name"],
                "availability": skill.get("availability", "unverified"),
                "available": bool(skill.get("available", False)),
            },
            "execution": "existing_agent_workflow",
            "note": "The requested skill is recorded in the workflow for audit. The current executor still uses the general agent plan; provider-specific execution is not yet implemented.",
            "agent": result,
        }
