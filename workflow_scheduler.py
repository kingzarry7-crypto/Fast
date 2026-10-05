"""Conservative background worker for approved/resumable KZ workflows."""
from __future__ import annotations

import threading
import time

_STARTED = False
_LOCK = threading.Lock()


def start(interval_seconds: int = 30) -> None:
    global _STARTED
    with _LOCK:
        if _STARTED:
            return
        _STARTED = True

    def loop():
        while True:
            try:
                from database import get_db_connection
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT id, user_id
                            FROM kz_workflows
                            WHERE status IN ('approved','executing','researching','verifying')
                            ORDER BY updated_at ASC
                            LIMIT 25
                            """
                        )
                        rows = cur.fetchall()
                finally:
                    conn.close()

                from workflow_engine import run_workflow
                for row in rows:
                    workflow_id = row[0]
                    user_id = row[1]
                    try:
                        run_workflow(str(workflow_id), str(user_id))
                    except Exception:
                        # A single workflow must never kill the worker.
                        continue
            except Exception:
                # Database may be temporarily unavailable; retry next interval.
                pass
            time.sleep(max(10, int(interval_seconds)))

    threading.Thread(target=loop, name="kz-workflow-scheduler", daemon=True).start()
