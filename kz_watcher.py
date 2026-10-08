"""KZ WATCHER — persistent, read-only signal watcher.

The watcher observes public opportunities, relevant news, and service health.
It never sends messages, submits applications, changes code, trades, or spends
money. Findings are deduplicated and stored so KZ can report them and prepare
an approval-gated mission later.

Enable the background loop explicitly with:
  KZ_WATCH_ENABLED=true
  KZ_WATCH_USER_IDS=<comma-separated user ids>
  KZ_WATCH_INTERVAL_SEC=900
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("kz_watcher")
_LOCK = threading.RLock()
_READY = False
_THREAD: threading.Thread | None = None
_STOP = threading.Event()

CATEGORIES = ("clients", "jobs", "news", "website_health")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn():
    try:
        from database import get_connection
        return get_connection()
    except Exception:
        return None


def init() -> bool:
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
                CREATE TABLE IF NOT EXISTS kz_watch_findings (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    confidence TEXT NOT NULL DEFAULT 'low',
                    estimated_value NUMERIC NOT NULL DEFAULT 0,
                    source_kind TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'new',
                    suggested_action TEXT NOT NULL DEFAULT '',
                    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, fingerprint)
                );
                CREATE INDEX IF NOT EXISTS idx_kz_watch_user_status
                    ON kz_watch_findings(user_id, status, updated_at DESC);
                CREATE TABLE IF NOT EXISTS kz_watch_runs (
                    id UUID PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    categories_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                    found_count INTEGER NOT NULL DEFAULT 0,
                    new_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '',
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_kz_watch_runs_user
                    ON kz_watch_runs(user_id, started_at DESC);
                """)
            conn.commit()
            _READY = True
            return True
        except Exception:
            try: conn.rollback()
            except Exception: pass
            return False
        finally:
            conn.close()


def _fingerprint(item: dict[str, Any]) -> str:
    basis = "|".join([
        str(item.get("category") or ""),
        str(item.get("url") or ""),
        str(item.get("title") or ""),
    ]).lower().strip()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _save_finding(user_id: str, item: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    fid = hashlib.sha1((_fingerprint(item) + str(user_id)).encode()).hexdigest()[:32]
    fingerprint = _fingerprint(item)
    payload = dict(item)
    conn = _conn()
    if conn is None or not init():
        return ({**item, "id": fid, "status": "new", "new": True}, True)
    try:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO kz_watch_findings
              (id,user_id,fingerprint,category,title,summary,url,score,confidence,
               estimated_value,source_kind,status,suggested_action,payload_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'new',%s,%s::jsonb)
            ON CONFLICT (user_id,fingerprint) DO UPDATE SET
              title=EXCLUDED.title, summary=EXCLUDED.summary, url=EXCLUDED.url,
              score=EXCLUDED.score, confidence=EXCLUDED.confidence,
              estimated_value=EXCLUDED.estimated_value,
              source_kind=EXCLUDED.source_kind,
              suggested_action=EXCLUDED.suggested_action,
              payload_json=EXCLUDED.payload_json,
              updated_at=NOW()
            RETURNING id, status, created_at, updated_at
            """, (
                fid, str(user_id), fingerprint,
                str(item.get("category") or "unknown"),
                str(item.get("title") or "KZ Watch finding"),
                str(item.get("summary") or ""),
                str(item.get("url") or ""),
                int(item.get("score") or 0),
                str(item.get("confidence") or "low"),
                float(item.get("estimated_value") or 0),
                str(item.get("source_kind") or ""),
                str(item.get("suggested_action") or ""),
                json.dumps(payload),
            ))
            row = cur.fetchone()
        conn.commit()
        is_new = bool(row and row[0] == fid and row[2] == row[3])
        return ({**item, "id": fid, "status": str(row[1]) if row else "new", "new": is_new}, is_new)
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        logger.warning("watch finding persistence failed: %s", type(exc).__name__)
        return ({**item, "id": fid, "status": "new", "new": True}, True)
    finally:
        conn.close()


def _save_run(user_id: str, status: str, categories: list[str], found: int, new: int, error: str = "") -> None:
    conn = _conn()
    if conn is None or not init():
        return
    try:
        import uuid
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO kz_watch_runs
              (id,user_id,status,categories_json,found_count,new_count,error,started_at,finished_at)
            VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,NOW(),NOW())
            """, (str(uuid.uuid4()), str(user_id), status, json.dumps(categories), found, new, error[:500]))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        conn.close()


def _health_finding(user_id: str) -> dict[str, Any] | None:
    try:
        from reliability_guardian import snapshot
        health = snapshot()
        problems = health.get("alerts") or health.get("issues") or []
        if not problems:
            return None
        text = "; ".join(str(x.get("message") if isinstance(x, dict) else x) for x in problems[:3])
        return {
            "category": "website_health",
            "title": "KZ detected a service reliability issue",
            "summary": text[:1000],
            "url": "",
            "score": 85,
            "confidence": "high",
            "estimated_value": 0,
            "source_kind": "system_health",
            "suggested_action": "Inspect the failing service and prepare a safe repair plan; require approval before code or deployment changes.",
            "payload": health,
        }
    except Exception:
        return None


def scan_user(user_id: str, categories: list[str] | None = None, max_results: int = 6) -> dict[str, Any]:
    """Run one read-only watch cycle for one user."""
    user_id = str(user_id or "").strip()
    if not user_id:
        raise ValueError("user_id is required")
    wanted = [c for c in (categories or ["clients", "jobs", "news", "website_health"]) if c in CATEGORIES]
    found: list[dict[str, Any]] = []
    new: list[dict[str, Any]] = []
    errors: list[str] = []

    for category in wanted:
        try:
            if category == "website_health":
                item = _health_finding(user_id)
                if item:
                    saved, is_new = _save_finding(user_id, item)
                    found.append(saved)
                    if is_new: new.append(saved)
                continue
            from opportunity_hunter import hunt
            result = hunt(user_id, category=category, max_results=max(3, min(int(max_results), 12)))
            for item in result.get("opportunities") or []:
                saved, is_new = _save_finding(user_id, item)
                found.append(saved)
                if is_new:
                    new.append(saved)
        except Exception as exc:
            logger.exception("KZ Watch category failed: %s", category)
            errors.append(f"{category}: {type(exc).__name__}")

    # Highest-value signals first. News has zero estimated revenue by design.
    found.sort(key=lambda x: (int(x.get("score") or 0), float(x.get("estimated_value") or 0)), reverse=True)
    _save_run(user_id, "partial" if errors and found else "failed" if errors else "completed",
              wanted, len(found), len(new), "; ".join(errors))
    return {
        "status": "partial" if errors and found else "failed" if errors else "completed",
        "user_id": user_id,
        "categories": wanted,
        "found_count": len(found),
        "new_count": len(new),
        "findings": found[:30],
        "new_findings": new[:30],
        "errors": errors,
        "checked_at": _now(),
    }


def list_findings(user_id: str, limit: int = 30, status: str = "") -> list[dict[str, Any]]:
    conn = _conn()
    if conn is None or not init():
        return []
    try:
        with conn.cursor() as cur:
            if status:
                cur.execute("""
                  SELECT id,user_id,category,title,summary,url,score,confidence,
                         estimated_value,source_kind,status,suggested_action,payload_json,
                         created_at,updated_at
                  FROM kz_watch_findings
                  WHERE user_id=%s AND status=%s
                  ORDER BY score DESC, updated_at DESC LIMIT %s
                """, (str(user_id), status, max(1, min(int(limit), 100))))
            else:
                cur.execute("""
                  SELECT id,user_id,category,title,summary,url,score,confidence,
                         estimated_value,source_kind,status,suggested_action,payload_json,
                         created_at,updated_at
                  FROM kz_watch_findings
                  WHERE user_id=%s
                  ORDER BY score DESC, updated_at DESC LIMIT %s
                """, (str(user_id), max(1, min(int(limit), 100))))
            rows = cur.fetchall()
        out = []
        for row in rows:
            data = dict(zip([
                "id","user_id","category","title","summary","url","score","confidence",
                "estimated_value","source_kind","status","suggested_action","payload",
                "created_at","updated_at"
            ], row))
            if isinstance(data.get("payload"), str):
                try: data["payload"] = json.loads(data["payload"])
                except Exception: pass
            out.append(data)
        return out
    except Exception:
        return []
    finally:
        conn.close()


def get_finding(user_id: str, finding_id: str) -> dict[str, Any] | None:
    for item in list_findings(user_id, 100):
        if str(item.get("id")) == str(finding_id):
            return item
    return None


def mark_status(user_id: str, finding_id: str, status: str) -> dict[str, Any]:
    allowed = {"new", "seen", "dismissed", "actioned"}
    if status not in allowed:
        raise ValueError("invalid watcher finding status")
    conn = _conn()
    if conn is None or not init():
        raise RuntimeError("watch storage unavailable")
    try:
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE kz_watch_findings SET status=%s, updated_at=NOW()
              WHERE id=%s AND user_id=%s
              RETURNING id,status
            """, (status, str(finding_id), str(user_id)))
            row = cur.fetchone()
        conn.commit()
        if not row:
            raise ValueError("finding not found")
        return {"id": str(row[0]), "status": str(row[1])}
    finally:
        conn.close()


def prepare(user_id: str, finding_id: str) -> dict[str, Any]:
    """Turn a finding into an approval-gated KZ Agent mission."""
    item = get_finding(user_id, finding_id)
    if not item:
        raise ValueError("finding not found")
    if item.get("status") == "dismissed":
        raise ValueError("finding is dismissed")
    from kz_agent import run
    title = str(item.get("title") or "KZ Watch finding")
    summary = str(item.get("summary") or "")
    url = str(item.get("url") or "")
    action = str(item.get("suggested_action") or "Research the finding and prepare the safest useful next step.")
    goal = (
        f"Investigate this KZ Watch finding: {title}. "
        f"Summary: {summary}. Source: {url}. "
        f"Next action: {action} "
        "Research first. Do not send, submit, publish, spend money, trade, or modify external systems "
        "until the user explicitly approves the consequential step."
    )
    result = run(str(user_id), goal, run_now=True)
    mark_status(str(user_id), finding_id, "actioned")
    return {"status": "ok", "finding": item, "agent": result}


def configured_user_ids() -> list[str]:
    raw = os.getenv("KZ_WATCH_USER_IDS", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def status() -> dict[str, Any]:
    return {
        "enabled": os.getenv("KZ_WATCH_ENABLED", "false").lower() in {"1","true","yes","on"},
        "interval_sec": max(300, int(os.getenv("KZ_WATCH_INTERVAL_SEC", "900") or 900)),
        "configured_user_count": len(configured_user_ids()),
        "running": bool(_THREAD and _THREAD.is_alive()),
    }


def _loop() -> None:
    interval = status()["interval_sec"]
    while not _STOP.wait(interval):
        for user_id in configured_user_ids():
            try:
                scan_user(user_id)
            except Exception:
                logger.exception("KZ Watch cycle failed for user %s", user_id)


def start() -> dict[str, Any]:
    global _THREAD
    if not status()["enabled"] or not configured_user_ids():
        return status()
    with _LOCK:
        if _THREAD and _THREAD.is_alive():
            return status()
        _STOP.clear()
        _THREAD = threading.Thread(target=_loop, name="kz-watcher", daemon=True)
        _THREAD.start()
        logger.info("KZ WATCHER STARTED | users=%d interval=%ss",
                    len(configured_user_ids()), status()["interval_sec"])
        return status()


def stop() -> dict[str, Any]:
    _STOP.set()
    return status()
