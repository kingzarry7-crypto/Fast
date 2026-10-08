"""Persistent Neon/PostgreSQL storage for KZ workflows.

Falls back to an in-process store only when the database is unavailable, so a
database outage never crashes the existing application. Production workflows
should use Neon for resumability across Railway restarts.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from database import get_connection
except Exception:
    get_connection = None

_LOCK = threading.RLock()
_READY = False
_MEMORY: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    """Return a raw psycopg2 connection, never a context-manager wrapper."""
    if get_connection is None:
        return None
    try:
        return get_connection()
    except Exception:
        return None


def init_workflow_store() -> bool:
    global _READY
    if _READY:
        return True
    with _LOCK:
        if _READY:
            return True
        conn = _conn()
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS kz_workflows (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
                    plan_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    potential_revenue NUMERIC NOT NULL DEFAULT 0,
                    estimated_cost NUMERIC NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_kz_workflows_user
                    ON kz_workflows(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS kz_workflow_events (
                    id UUID PRIMARY KEY,
                    workflow_id UUID NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_kz_workflow_events_workflow
                    ON kz_workflow_events(workflow_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS kz_workflow_approvals (
                    id UUID PRIMARY KEY,
                    workflow_id UUID NOT NULL,
                    step_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'awaiting',
                    action_preview JSONB NOT NULL DEFAULT '{}'::jsonb,
                    decided_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_kz_workflow_approvals_user
                    ON kz_workflow_approvals(user_id, status);
                """)
            conn.commit()
            _READY = True
            return True
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return False
        finally:
            conn.close()


def _encode(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    return value


def save_workflow(item: Dict[str, Any]) -> Dict[str, Any]:
    workflow_id = str(item["id"])
    payload = dict(item)
    payload["updated_at"] = _now()
    with _LOCK:
        conn = _conn()
        if conn is None or not init_workflow_store():
            _MEMORY[workflow_id] = payload
            return dict(payload)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO kz_workflows
                (id,user_id,goal,status,risk,requires_approval,plan_json,context_json,
                 result_json,potential_revenue,estimated_cost,created_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  status=EXCLUDED.status,
                  risk=EXCLUDED.risk,
                  requires_approval=EXCLUDED.requires_approval,
                  plan_json=EXCLUDED.plan_json,
                  context_json=EXCLUDED.context_json,
                  result_json=EXCLUDED.result_json,
                  potential_revenue=EXCLUDED.potential_revenue,
                  estimated_cost=EXCLUDED.estimated_cost,
                  updated_at=EXCLUDED.updated_at
                """, (
                    workflow_id, str(item["user_id"]), str(item["goal"]),
                    str(item["status"]), str(item["risk"]), bool(item.get("requires_approval")),
                    json.dumps(_encode(item.get("plan", []))),
                    json.dumps(_encode(item.get("context", {}))),
                    json.dumps(_encode(item.get("result", {}))),
                    float(item.get("potential_revenue") or 0),
                    float(item.get("estimated_cost") or 0),
                    item.get("created_at") or payload["updated_at"],
                    payload["updated_at"],
                ))
            conn.commit()
            return payload
        except Exception:
            try: conn.rollback()
            except Exception: pass
            _MEMORY[workflow_id] = payload
            return dict(payload)
        finally:
            conn.close()


def get_workflow(workflow_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with _LOCK:
        conn = _conn()
        if conn is not None and init_workflow_store():
            try:
                with conn.cursor() as cur:
                    if user_id is None:
                        cur.execute("SELECT * FROM kz_workflows WHERE id=%s", (str(workflow_id),))
                    else:
                        cur.execute("SELECT * FROM kz_workflows WHERE id=%s AND user_id=%s", (str(workflow_id), str(user_id)))
                    row = cur.fetchone()
                    if row:
                        cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
                        data = dict(zip(cols, row))
                        for key in ("plan_json","context_json","result_json"):
                            value = data.pop(key, None)
                            if isinstance(value, str):
                                value = json.loads(value or ("[]" if key=="plan_json" else "{}"))
                            data[key.replace("_json","")] = value or ([] if key=="plan_json" else {})
                        return data
            except Exception:
                pass
            finally:
                conn.close()
        item = _MEMORY.get(str(workflow_id))
        if item and (user_id is None or str(item.get("user_id")) == str(user_id)):
            return dict(item)
        return None


def list_workflows(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    with _LOCK:
        conn = _conn()
        if conn is not None and init_workflow_store():
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM kz_workflows WHERE user_id=%s ORDER BY updated_at DESC LIMIT %s", (str(user_id), max(1,min(int(limit),100))))
                    rows = cur.fetchall()
                    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
                    out=[]
                    for row in rows:
                        data=dict(zip(cols,row))
                        for key in ("plan_json","context_json","result_json"):
                            value=data.pop(key,None)
                            if isinstance(value,str): value=json.loads(value or ("[]" if key=="plan_json" else "{}"))
                            data[key.replace("_json","")]=value or ([] if key=="plan_json" else {})
                        out.append(data)
                    return out
            except Exception:
                pass
            finally:
                conn.close()
        return [dict(x) for x in sorted(_MEMORY.values(), key=lambda v: v.get("updated_at",""), reverse=True)
                if str(x.get("user_id")) == str(user_id)][:max(1,min(int(limit),100))]


def add_event(workflow_id: str, user_id: str, event_type: str, payload: Dict[str, Any] | None = None) -> None:
    conn = _conn()
    if conn is None or not init_workflow_store():
        return
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO kz_workflow_events(id,workflow_id,user_id,event_type,payload_json) VALUES (%s,%s,%s,%s,%s::jsonb)",
                (str(uuid.uuid4()), str(workflow_id), str(user_id), str(event_type), json.dumps(payload or {})),
            )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        conn.close()


def list_events(workflow_id: str, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return user-scoped workflow events for live agent progress/evidence."""
    limit = max(1, min(int(limit), 200))
    conn = _conn()
    if conn is None or not init_workflow_store():
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id,workflow_id,user_id,event_type,payload_json,created_at
                   FROM kz_workflow_events
                   WHERE workflow_id=%s AND user_id=%s
                   ORDER BY created_at ASC LIMIT %s""",
                (str(workflow_id), str(user_id), limit),
            )
            rows = cur.fetchall()
            out = []
            for row in rows:
                payload = row[4]
                if isinstance(payload, str):
                    payload = json.loads(payload or "{}")
                out.append({
                    "id": str(row[0]),
                    "workflow_id": str(row[1]),
                    "user_id": str(row[2]),
                    "event_type": str(row[3]),
                    "payload": payload or {},
                    "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                })
            return out
    except Exception:
        return []
    finally:
        conn.close()



def create_approval(workflow_id: str, step_id: str, user_id: str, preview: Dict[str, Any]) -> str:
    approval_id = str(uuid.uuid4())
    conn = _conn()
    if conn is not None and init_workflow_store():
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO kz_workflow_approvals(id,workflow_id,step_id,user_id,status,action_preview) VALUES (%s,%s,%s,%s,'awaiting',%s::jsonb)",
                    (approval_id,str(workflow_id),str(step_id),str(user_id),json.dumps(preview)),
                )
            conn.commit()
            return approval_id
        except Exception:
            try: conn.rollback()
            except Exception: pass
        finally:
            conn.close()
    return approval_id


def decide_approval(approval_id: str, user_id: str, approved: bool) -> bool:
    conn = _conn()
    if conn is None or not init_workflow_store():
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE kz_workflow_approvals SET status=%s,decided_at=NOW() WHERE id=%s AND user_id=%s AND status='awaiting'",
                ("approved" if approved else "rejected", str(approval_id), str(user_id)),
            )
            changed = cur.rowcount > 0
        conn.commit()
        return changed
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        conn.close()


def list_workflows_for_worker(limit: int = 25) -> List[Dict[str, Any]]:
    """Return resumable workflows across users for the background worker.

    Only statuses that are already safe to resume are returned. Approval-pending
    workflows are deliberately excluded so the worker can never auto-approve them.
    """
    allowed = ("planning", "approved", "executing", "researching", "verifying")
    with _LOCK:
        conn = _conn()
        if conn is not None and init_workflow_store():
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM kz_workflows WHERE status = ANY(%s) ORDER BY updated_at ASC LIMIT %s",
                        (list(allowed), max(1, min(int(limit), 100))),
                    )
                    rows = cur.fetchall()
                    cols = [d.name if hasattr(d, "name") else d[0] for d in cur.description]
                    out=[]
                    for row in rows:
                        data=dict(zip(cols,row))
                        for key in ("plan_json","context_json","result_json"):
                            value=data.pop(key,None)
                            if isinstance(value,str): value=json.loads(value or ("[]" if key=="plan_json" else "{}"))
                            data[key.replace("_json","")]=value or ([] if key=="plan_json" else {})
                        out.append(data)
                    return out
            except Exception:
                pass
            finally:
                conn.close()
        return [dict(x) for x in sorted(_MEMORY.values(), key=lambda v: v.get("updated_at",""))
                if str(x.get("status")) in allowed][:max(1, min(int(limit),100))]
