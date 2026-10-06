"""Persistent, conservative KZ background scheduler."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_STARTED = False
_LOCK = threading.Lock()
_LAST_RUN = None
_LAST_ERROR = None
_RUN_COUNT = 0


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
    try:
        from workflow_store import list_workflows_for_worker
        from workflow_engine import run_workflow
        rows = list_workflows_for_worker(limit)
        for row in rows:
            try:
                run_workflow(str(row["id"]), str(row["user_id"]))
                resumed += 1
            except Exception:
                errors += 1
        _LAST_ERROR = None if errors == 0 else f"{errors} workflow(s) failed to resume"
    except Exception as exc:
        errors += 1
        _LAST_ERROR = type(exc).__name__
    _RUN_COUNT += 1
    return {"resumed": resumed, "errors": errors, "checked": resumed + errors}


def start(interval_seconds: int = 30) -> None:
    global _STARTED
    with _LOCK:
        if _STARTED:
            return
        _STARTED = True

    def loop():
        while True:
            try:
                run_once()
            except Exception:
                pass
            time.sleep(max(10, int(interval_seconds)))

    threading.Thread(target=loop, name="kz-workflow-scheduler", daemon=True).start()
