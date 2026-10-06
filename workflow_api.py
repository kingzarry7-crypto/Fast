from fastapi import Request, HTTPException

def install_workflow_api(app, require_current_user, row_value=None):
    import workflow_engine as engine
    from workflow_store import save_workflow, decide_approval

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

    original_create = engine.create_workflow
    def create_with_action_preview(user_id, goal):
        item = original_create(user_id, goal)
        try:
            from agent_action_gateway import plan_action_from_goal
            for step in item.get("plan", []):
                if step.get("action") == "external_action" and step.get("status") == "waiting_for_approval":
                    action_plan = plan_action_from_goal(goal, str(user_id))
                    step["output"] = {
                        "supported_action": action_plan.get("status") == "awaiting_approval",
                        "action": action_plan.get("action"),
                        "message": action_plan.get("message") or action_plan.get("detail"),
                    }
            save_workflow(item)
        except Exception:
            pass
        return item
    engine.create_workflow = create_with_action_preview

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
    engine._execute_step = execute_with_gateway

    original_approve = engine.approve_workflow
    def approve_with_persistence(workflow_id, user_id, approved):
        current = engine.get_workflow(workflow_id, user_id)
        if current:
            for step in current.get("plan", []):
                approval_id = step.get("approval_id")
                if approval_id:
                    decide_approval(approval_id, str(user_id), bool(approved))
                    break
        return original_approve(workflow_id, user_id, approved)
    engine.approve_workflow = approve_with_persistence

    def uid(row):
        try:
            value = row_value(row, 'id', 0) if row_value else (row.get('id') if isinstance(row, dict) else row[0])
            return str(value or '')
        except Exception:
            return ''

    @app.post('/api/workflows')
    async def create_workflow_route(request: Request):
        row=require_current_user(request); user_id=uid(row)
        if not user_id: raise HTTPException(status_code=401, detail='Authenticated user required')
        body=await request.json(); goal=str((body or {}).get('goal') or '').strip()
        if not goal: raise HTTPException(status_code=400, detail='goal is required')
        if len(goal) > 4000: raise HTTPException(status_code=400, detail='goal is too long')
        return {'status':'ok','workflow':engine.create_workflow(user_id,goal)}

    @app.get('/api/business/dashboard')
    def business_dashboard_route(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        from business_dashboard import build_business_dashboard
        workflows = engine.list_workflows(user_id, 50)
        return {'status': 'ok', 'dashboard': build_business_dashboard(workflows)}

    @app.get('/api/revenue')
    def revenue_dashboard_route(request: Request):
        row=require_current_user(request)
        user_id=uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        from revenue_engine import revenue_dashboard
        workflows=engine.list_workflows(user_id,50)
        return {'status':'ok','revenue':revenue_dashboard(workflows)}

    @app.get('/api/opportunities/hunt')
    def opportunities_hunt_route(request: Request, category: str = 'clients', query: str = '', max_results: int = 12):
        row = require_current_user(request); user_id = uid(row)
        if not user_id: raise HTTPException(status_code=401, detail='Authenticated user required')
        from opportunity_hunter import hunt
        return hunt(user_id, category=category, query=query, max_results=max_results)

    @app.post('/api/opportunities/{opportunity_id}/prepare')
    async def opportunity_prepare_route(opportunity_id: str, request: Request):
        row = require_current_user(request); user_id = uid(row)
        body = await request.json(); opportunity = dict((body or {}).get('opportunity') or {})
        if str(opportunity.get('id') or '') != str(opportunity_id):
            raise HTTPException(status_code=400, detail='Opportunity id mismatch')
        from opportunity_hunter import create_work_for_opportunity
        return {'status':'ok','workflow':create_work_for_opportunity(user_id, opportunity)}

    @app.post('/api/acquisition/prepare')
    async def acquisition_prepare_route(request: Request):
        row=require_current_user(request); user_id=uid(row)
        if not user_id: raise HTTPException(status_code=401, detail='Authenticated user required')
        body=await request.json()
        opportunity=dict((body or {}).get('opportunity') or {})
        if not opportunity.get('url') or not opportunity.get('title'):
            raise HTTPException(status_code=400, detail='opportunity title and url are required')
        from client_acquisition import prepare
        return {'status':'ok','acquisition':prepare(user_id,opportunity)}

    @app.post('/api/delivery/package')
    async def delivery_package_route(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        body = await request.json()
        workflow_id = str((body or {}).get('workflow_id') or '')
        if not workflow_id:
            raise HTTPException(status_code=400, detail='workflow_id is required')
        workflow = engine.get_workflow(workflow_id, user_id)
        if not workflow:
            raise HTTPException(status_code=404, detail='Workflow not found')
        from delivery_agent import prepare
        return {'status': 'ok', 'delivery': prepare(user_id, workflow)}

    @app.post('/api/delivery/verify')
    async def delivery_verify_route(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        body = await request.json()
        package = dict((body or {}).get('delivery') or {})
        if str(package.get('workflow_id') or '') == '':
            raise HTTPException(status_code=400, detail='delivery.workflow_id is required')
        workflow = engine.get_workflow(str(package.get('workflow_id')), user_id)
        if not workflow:
            raise HTTPException(status_code=404, detail='Workflow not found')
        from delivery_agent import prepare, verify
        fresh = prepare(user_id, workflow)
        checks = dict((body or {}).get('checks') or {})
        return {'status': 'ok', 'delivery': verify(fresh, checks)}

    @app.get('/api/workflows/worker/status')
    def worker_status_route(request: Request):
        row = require_current_user(request)
        if not uid(row):
            raise HTTPException(status_code=401, detail='Authenticated user required')
        from workflow_scheduler import status
        return {'status': 'ok', 'worker': status()}

    @app.get('/api/learning')
    def learning_route(request: Request):
        row = require_current_user(request)
        user_id = uid(row)
        if not user_id:
            raise HTTPException(status_code=401, detail='Authenticated user required')
        from learning_loop import learning_snapshot
        return {'status': 'ok', 'learning': learning_snapshot(user_id)}

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
        row=require_current_user(request); body=await request.json()
        approved=bool((body or {}).get('approved'))
        try:
            result=engine.approve_workflow(workflow_id,uid(row),approved)
        except ValueError:
            raise HTTPException(status_code=404, detail='Workflow not found')
        return {'status':'ok','workflow':result}

    try:
        from workflow_scheduler import start
        start()
    except Exception as exc:
        print('KZ_WORKFLOW_SCHEDULER_FAILED', type(exc).__name__, flush=True)
    print('KZ_WORKFLOW_API_INSTALLED', flush=True)
