"""
KING ZARRY AI — Safe Agent Task Engine (V5.3)

Turns one natural-language goal into a persisted sequence of bounded agent
steps. It reuses the existing agent_core planner/tools and never introduces
arbitrary code execution or bypasses approval gates.

Safe work can auto-run. Risky work remains approval-gated by the existing
agent_core / action gateway.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_DB_LOCK = threading.Lock()
_TASK_THREADS: Dict[str, threading.Thread] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> str:
    explicit = (os.getenv("AGENT_TASK_DB_PATH") or "").strip()
    if explicit:
        return os.path.abspath(explicit)
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if data_dir and not data_dir.endswith(".db"):
        return os.path.abspath(os.path.join(data_dir, "king_zarry_agent_tasks.db"))
    return os.path.abspath(os.path.join(os.getcwd(), "king_zarry_agent_tasks.db"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_task_db() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    current_step INTEGER NOT NULL DEFAULT 0,
                    total_steps INTEGER NOT NULL DEFAULT 0,
                    steps_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_agent_tasks_user
                    ON agent_tasks(user_id, created_at);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _load(task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_task_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            if user_id is None:
                row = conn.execute(
                    "SELECT * FROM agent_tasks WHERE id=?", (task_id,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM agent_tasks WHERE id=? AND user_id=?",
                    (task_id, str(user_id)),
                ).fetchone()
            if not row:
                return None
            data = dict(row)
            for key in ("steps_json", "result_json"):
                raw = data.get(key)
                try:
                    data[key[:-5] if key.endswith("_json") else key] = json.loads(raw) if raw else None
                except Exception:
                    data[key[:-5] if key.endswith("_json") else key] = None
            data.pop("steps_json", None)
            data.pop("result_json", None)
            return data
        finally:
            conn.close()


def _save(task_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    with _DB_LOCK:
        conn = _connect()
        try:
            assignments = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [task_id]
            conn.execute(f"UPDATE agent_tasks SET {assignments} WHERE id=?", values)
            conn.commit()
        finally:
            conn.close()


def _split_goal(goal: str, max_steps: int) -> List[str]:
    text = " ".join((goal or "").strip().split())
    if not text:
        return []
    # Only split explicit sequencing language; ordinary prompts stay one step.
    separators = (" then ", " and then ", ";")
    parts = [text]
    for sep in separators:
        next_parts: List[str] = []
        for part in parts:
            next_parts.extend(part.split(sep))
        parts = next_parts
    clean = [p.strip(" .") for p in parts if p.strip(" .")]
    return clean[:max(1, min(max_steps, 8))]


def create_task(user_id: str, goal: str, max_steps: int = 6) -> Dict[str, Any]:
    steps = _split_goal(goal, max_steps)
    if not steps:
        raise ValueError("Goal is required")
    task_id = str(uuid.uuid4())
    now = _now()
    init_task_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO agent_tasks
                (id,user_id,goal,status,current_step,total_steps,steps_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    task_id,
                    str(user_id),
                    " ".join((goal or "").strip().split()),
                    "queued",
                    0,
                    len(steps),
                    json.dumps([{"index": i, "goal": s, "status": "queued"} for i, s in enumerate(steps)]),
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return _load(task_id, str(user_id)) or {"id": task_id}


def list_tasks(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    init_task_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT id FROM agent_tasks WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (str(user_id), max(1, min(int(limit), 50))),
            ).fetchall()
        finally:
            conn.close()
    return [x for x in (_load(r["id"], str(user_id)) for r in rows) if x]


def cancel_task(task_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    task = _load(task_id, str(user_id))
    if not task:
        return None
    if task["status"] in {"completed", "failed", "cancelled", "awaiting_approval"}:
        return task
    _save(task_id, status="cancelled", finished_at=_now())
    return _load(task_id, str(user_id))


def _set_step(task_id: str, step_index: int, status: str, **extra: Any) -> None:
    task = _load(task_id)
    if not task:
        return
    steps = task.get("steps") or []
    if 0 <= step_index < len(steps):
        steps[step_index]["status"] = status
        steps[step_index].update(extra)
    _save(task_id, steps_json=json.dumps(steps), current_step=step_index)


def _worker(task_id: str, user_id: str) -> None:
    try:
        task = _load(task_id, user_id)
        if not task:
            return
        _save(task_id, status="running", started_at=_now())
        from agent_core import plan_and_run

        results: List[Dict[str, Any]] = []
        for i, step in enumerate(task.get("steps") or []):
            latest = _load(task_id, user_id)
            if not latest or latest["status"] == "cancelled":
                return
            goal = str(step.get("goal") or "").strip()
            _set_step(task_id, i, "running")
            try:
                result = plan_and_run(goal, user_id=user_id, auto_approve_safe=True)
            except Exception as exc:
                result = {"status": "error", "detail": f"{type(exc).__name__}: {str(exc)[:300]}"}
            results.append({"step": i, "goal": goal, "result": result})
            step_status = str(result.get("status") or "completed")
            _set_step(task_id, i, step_status, result=result)
            if step_status in {"awaiting_approval", "needs_details"}:
                _save(
                    task_id,
                    status="awaiting_approval",
                    current_step=i,
                    result_json=json.dumps({"steps": results}),
                )
                return
            if step_status in {"error", "failed"}:
                _save(
                    task_id,
                    status="failed",
                    current_step=i,
                    result_json=json.dumps({"steps": results}),
                    error=str(result.get("detail") or result.get("message") or "Step failed")[:1000],
                    finished_at=_now(),
                )
                return
        _save(
            task_id,
            status="completed",
            current_step=len(results),
            result_json=json.dumps({"steps": results}),
            finished_at=_now(),
        )
    except Exception as exc:
        _save(
            task_id,
            status="failed",
            error=f"{type(exc).__name__}: {str(exc)[:1000]}",
            finished_at=_now(),
        )
    finally:
        _TASK_THREADS.pop(task_id, None)


def start_task(task_id: str, user_id: str) -> Dict[str, Any]:
    task = _load(task_id, str(user_id))
    if not task:
        raise ValueError("Task not found")
    if task["status"] in {"running", "completed", "failed", "cancelled", "awaiting_approval"}:
        return task
    if len(_TASK_THREADS) >= 2:
        raise RuntimeError("Agent task capacity is full; try again in a moment")
    thread = threading.Thread(target=_worker, args=(task_id, str(user_id)), daemon=True)
    _TASK_THREADS[task_id] = thread
    thread.start()
    return _load(task_id, str(user_id)) or task


def run_task(user_id: str, goal: str, max_steps: int = 6) -> Dict[str, Any]:
    task = create_task(user_id, goal, max_steps=max_steps)
    return start_task(task["id"], str(user_id))


def task_status() -> Dict[str, Any]:
    init_task_db()
    return {
        "enabled": True,
        "max_steps": 8,
        "max_concurrent_tasks": 2,
        "approval_gated": True,
        "executor": "existing-agent-core",
    }
