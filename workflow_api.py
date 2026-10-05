from fastapi import Request

def install_workflow_api(app, require_current_user, row_value=None):
    from workflow_engine import create_workflow, list_workflows, get_workflow, approve_workflow, workflow_snapshot
    def uid(row):
        try:
            return str(row_value(row, 'id', 0)) if row_value else str(row.get('id') if isinstance(row, dict) else row[0])
        except Exception:
            return ''
    @app.post('/api/workflows')
    async def create_workflow_route(request: Request):
        row=require_current_user(request); user_id=uid(row)
        body=await request.json(); goal=str((body or {}).get('goal') or '').strip()
        if not goal: return {'status':'error','detail':'goal is required'}
        return {'status':'ok','workflow':create_workflow(user_id,goal)}
    @app.get('/api/workflows')
    def list_workflows_route(request: Request):
        row=require_current_user(request); return {'status':'ok','workflows':list_workflows(uid(row),50)}
    @app.get('/api/workflows/snapshot')
    def snapshot_route(request: Request):
        row=require_current_user(request); return {'status':'ok','snapshot':workflow_snapshot(uid(row))}
    @app.get('/api/workflows/{workflow_id}')
    def get_route(workflow_id: str, request: Request):
        row=require_current_user(request); return {'status':'ok','workflow':get_workflow(workflow_id,uid(row))}
    @app.post('/api/workflows/{workflow_id}/approve')
    async def approve_route(workflow_id: str, request: Request):
        row=require_current_user(request); body=await request.json(); approved=bool((body or {}).get('approved'))
        return {'status':'ok','workflow':approve_workflow(workflow_id,uid(row),approved)}
    print('KZ_WORKFLOW_API_INSTALLED', flush=True)
