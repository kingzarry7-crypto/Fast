from fastapi import Request, HTTPException

def install_workflow_api(app, require_current_user, row_value=None):
    import workflow_engine as engine
    from workflow_store import save_workflow

    # Prefer the existing Tavily integration when SearXNG is not configured.
    original_research = engine._research
    def research_with_fallback(goal):
        result = original_research(goal)
        if result.get("success"):
            return result
        try:
            from tavily_search import search_web
            tavily = search_web(goal, max_results=6, search_depth="advanced", include_answer=True)
            if tavily.get("success"):
                return {"success": True, "research": tavily, "provider": "tavily"}
        except Exception:
            pass
        return result
    engine._research = research_with_fallback

    # Prepare supported external actions before the approval card is shown.
    original_create = engine.create_workflow
    def create_with_action_preview(user_id, goal):
        item = original_create(user_id, goal)
        try:
            from agent_action_gateway import plan_action_from_goal
            for step in item.get("plan", []):
                if step.get("action") == "external_action" and step.get("status") == "waiting_for_approval":
                    action_plan = plan_action_from_goal(goal, str(user_id))
                    if action_plan.get("status") == "awaiting_approval":
                        step["output"] = {
                            "supported_action": True,
                            "action": action_plan.get("action"),
                            "message": action_plan.get("message"),
                        }
                    else:
                        step["output"] = {
                            "supported_action": False,
                            "message": action_plan.get("detail") or "This goal needs a connector-specific execution adapter.",
                        }
            save_workflow(item)
        except Exception:
            pass
        return item
    engine.create_workflow = create_with_action_preview

    # After the user approves, execute a prepared Action Gateway action.
    original_execute = engine._execute_step
    def execute_with_gateway(item, step):
        if step.get("action") == "external_action":
            action = (step.get("output") or {}).get("action") or {}
            action_id = action.get("id")
            if action_id:
                from agent_action_gateway import approve_action
                result = approve_action(action_id, str(item["user_id"]))
                return {"success": result.get("status") == "completed", "action": result}
            return original_execute(item, step)
        return original_execute(item, step)
    engine._execute_step = execute_with_gateway

    def uid(row):
        try:
            value = row_value(row, 'id', 0) if row_value else (row.get('id') if isinstance(row, dict) else row[0])
            return str(value or '')
        except Exception:
            return ''

    @app.post('/api/workflows')
    async def create_workflow_route(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        body = await request.json()
        goal = str((body or {}).get('goal') or '').strip()
        if not goal:
            raise HTTPException(status_code=400, detail='goal is required')
        if len(goal) > 4000:
            raise HTTPException(status_code=400, detail='goal is too long')
        return {'status':'ok','workflow':engine.create_workflow(user_id,goal)}

    @app.get('/api/workflows')
    def list_workflows_route(request: Request):
        row=require_current_user(request)
        return {'status':'ok','workflows':engine.list_workflows(uid(row),50)}

    @app.get('/api/workflows/snapshot')
    def snapshot_route(request: Request):
        row=require_current_user(request)
        return {'status':'ok','snapshot':engine.workflow_snapshot(uid(row))}

    @app.get('/api/workflows/{workflow_id}')
    def get_route(workflow_id: str, request: Request):
        row=require_current_user(request)
        item=engine.get_workflow(workflow_id,uid(row))
        if not item: raise HTTPException(status_code=404, detail='Workflow not found')
        return {'status':'ok','workflow':item}

    @app.post('/api/workflows/{workflow_id}/approve')
    async def approve_route(workflow_id: str, request: Request):
        row=require_current_user(request)
        body=await request.json()
        approved=bool((body or {}).get('approved'))
        try:
            result=engine.approve_workflow(workflow_id,uid(row),approved)
        except ValueError:
            raise HTTPException(status_code=404, detail='Workflow not found')
        return {'status':'ok','workflow':result}

    print('KZ_WORKFLOW_API_INSTALLED', flush=True)
