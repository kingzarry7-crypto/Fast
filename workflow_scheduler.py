"""Persistent, conservative KZ background scheduler."""
from __future__ import annotations

import threading
import time
import hashlib
from typing import Any, Dict

_STARTED = False
_LOCK = threading.Lock()
_LAST_RUN = None
_LAST_ERROR = None
_RUN_COUNT = 0


def _acquire_distributed_lock():
    """Prevent multiple Railway replicas from executing the same workflows."""
    try:
        from database import get_connection
        conn = get_connection()
        key = int.from_bytes(
            hashlib.sha256(b"king-zarry-workflow-worker").digest()[:8],
            "big",
            signed=True,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (key,))
            acquired = bool(cur.fetchone()[0])
        if not acquired:
            conn.close()
            return False, None
        return True, conn
    except Exception:
        # Preserve the existing single-process fallback when PostgreSQL is unavailable.
        return True, None


def status() -> Dict[str, Any]:
    return {
        "running": _STARTED,
        "last_run": _LAST_RUN,
        "last_error": _LAST_ERROR,
        "runs": _RUN_COUNT,
        "policy": "resume approved/safe workflows only; never auto-approve",
    }


def run_once(limit: int = 25) -> Dict[str, Any]:
    global _LAST_RUN, _LAST_ERROR, _RUN_COUNT
    from datetime import datetime, timezone

    _LAST_RUN = datetime.now(timezone.utc).isoformat()
    resumed = 0
    errors = 0
    lock_conn = None

    try:
        acquired, lock_conn = _acquire_distributed_lock()
        if not acquired:
            return {
                "resumed": 0,
                "errors": 0,
                "checked": 0,
                "skipped": True,
                "reason": "another workflow worker holds the distributed lock",
            }

        from workflow_store import list_workflows_for_worker
        from workflow_engine import run_workflow

        rows = list_workflows_for_worker(limit)
        for row in rows:
            try:
                workflow_id = str(row.get("id") or "")
                user_id = str(row.get("user_id") or "")
                if not workflow_id or not user_id:
                    raise ValueError("workflow row missing id or user_id")
                run_workflow(workflow_id, user_id)
                resumed += 1
            except Exception as exc:
                errors += 1
                _LAST_ERROR = f"{type(exc).__name__}: {str(exc)[:240]}"

        try:
            from reliability_guardian import record_success, record_failure
            if errors == 0:
                record_success()
            else:
                record_failure(
                    RuntimeError("workflow resume failures"),
                    risk="green",
                    attempts=1,
                )
        except Exception:
            pass

        _LAST_ERROR = None if errors == 0 else f"{errors} workflow(s) failed to resume"
    except Exception as exc:
        errors += 1
        _LAST_ERROR = f"{type(exc).__name__}: {str(exc)[:240]}"
    finally:
        if lock_conn is not None:
            try:
                with lock_conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (
                        int.from_bytes(hashlib.sha256(b"king-zarry-workflow-worker").digest()[:8], "big", signed=True),
                    ))
            except Exception:
                pass
            try:
                lock_conn.close()
            except Exception:
                pass

    _RUN_COUNT += 1
    return {
        "resumed": resumed,
        "errors": errors,
        "checked": resumed + errors,
    }


def start(interval_seconds: int = 30) -> None:
    global _STARTED

    with _LOCK:
        if _STARTED:
            return
        _STARTED = True

    def loop() -> None:
        while True:
            try:
                run_once()
            except Exception:
                pass
            time.sleep(max(10, int(interval_seconds)))

    threading.Thread(
        target=loop,
        name="kz-workflow-scheduler",
        daemon=True,
    ).start()
