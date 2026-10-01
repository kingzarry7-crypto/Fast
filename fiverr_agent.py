"""KING ZARRY AI — Separate Fiverr Agent.

Safe Fiverr workspace assistant. It does not bypass Fiverr protections or automate
unauthorized browser actions. It prepares, validates, stores and routes Fiverr work;
account-changing/public actions require an explicit user approval and a supported
Fiverr integration before execution.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.getenv("FIVERR_AGENT_DB_PATH") or os.getenv("DATA_DIR") or "king_zarry_fiverr_agent.db"
if os.path.isdir(DB_PATH):
    DB_PATH = os.path.join(DB_PATH, "king_zarry_fiverr_agent.db")

_LOCK = threading.RLock()

SKILLS = {
    "gig_creator": "Create complete Gig drafts: title, category, tags, packages, description, FAQ, requirements and gallery checklist.",
    "gig_optimizer": "Review and improve existing Gig copy, tags, packages, FAQs and requirements.",
    "profile_builder": "Prepare truthful freelancer profile copy, bio, skills, portfolio descriptions and intro-video script.",
    "seo_research": "Prepare Fiverr keyword/tag research and search-intent clusters from supplied or permitted research data.",
    "client_reply": "Draft professional Buyer replies while keeping communication on Fiverr.",
    "custom_offer": "Prepare custom-offer drafts with scope, price, delivery, revisions and requirements.",
    "order_intake": "Turn Buyer requirements into a structured delivery checklist and clarification questions.",
    "delivery_planner": "Break an order into milestones, deliverables, QA checks and client update messages.",
    "portfolio_builder": "Create portfolio case-study drafts and gallery copy from the user's own work.",
    "pricing": "Compare scope against the user's pricing rules and prepare package/offer options.",
    "policy_guard": "Check drafts for common Fiverr policy risks and flag items needing manual review.",
    "analytics": "Interpret seller metrics supplied by the user and propose factual experiments.",
    "fiverr_brief": "Produce a daily/weekly Fiverr workspace brief from supplied account data.",
    "workflow": "Remember an open Fiverr task and ask the user for missing information through Telegram.",
}

SUPPORTED_ACTIONS = {
    "prepare_gig",
    "prepare_reply",
    "prepare_custom_offer",
    "prepare_order_plan",
    "prepare_profile",
    "review_draft",
    "policy_check",
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _connect():
    path = os.path.abspath(DB_PATH)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS fiverr_agent_tasks (
                id TEXT PRIMARY KEY,
                telegram_user_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT,
                data_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_fiverr_tasks_user
                ON fiverr_agent_tasks(telegram_user_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS fiverr_agent_approvals (
                id TEXT PRIMARY KEY,
                telegram_user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT
            );
            """)
            conn.commit()
        finally:
            conn.close()

init_db()

def _task(row) -> Dict[str, Any]:
    item = dict(row)
    try:
        item["data"] = json.loads(item.pop("data_json") or "{}")
    except Exception:
        item["data"] = {}
    return item

def create_task(user_id: str, kind: str, title: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    task_id = str(uuid.uuid4())
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO fiverr_agent_tasks
                (id,telegram_user_id,kind,status,title,data_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (task_id, str(user_id), str(kind), "waiting_for_user", str(title),
                 json.dumps(data or {}), now, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM fiverr_agent_tasks WHERE id=?", (task_id,)).fetchone()
            return _task(row)
        finally:
            conn.close()

def update_task(task_id: str, user_id: str, status: Optional[str] = None,
                data: Optional[Dict[str, Any]] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM fiverr_agent_tasks WHERE id=? AND telegram_user_id=?",
                (str(task_id), str(user_id)),
            ).fetchone()
            if not row:
                return None
            current = _task(row)
            merged = dict(current["data"])
            if data:
                merged.update(data)
            conn.execute(
                """UPDATE fiverr_agent_tasks SET status=?, title=?, data_json=?, updated_at=?
                   WHERE id=? AND telegram_user_id=?""",
                (status or current["status"], title or current["title"], json.dumps(merged),
                 _now(), str(task_id), str(user_id)),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM fiverr_agent_tasks WHERE id=?", (task_id,)).fetchone()
            return _task(row)
        finally:
            conn.close()

def get_open_task(user_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                """SELECT * FROM fiverr_agent_tasks
                   WHERE telegram_user_id=? AND status IN ('waiting_for_user','draft_ready','awaiting_approval')
                   ORDER BY updated_at DESC LIMIT 1""",
                (str(user_id),),
            ).fetchone()
            return _task(row) if row else None
        finally:
            conn.close()

def list_tasks(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT * FROM fiverr_agent_tasks WHERE telegram_user_id=? ORDER BY updated_at DESC LIMIT ?",
                (str(user_id), max(1, min(int(limit), 50))),
            ).fetchall()
            return [_task(r) for r in rows]
        finally:
            conn.close()

def create_approval(user_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    approval_id = str(uuid.uuid4())
    now = _now()
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO fiverr_agent_approvals
                (id,telegram_user_id,action,payload_json,status,created_at)
                VALUES(?,?,?,?,?,?)""",
                (approval_id, str(user_id), str(action), json.dumps(payload or {}),
                 "awaiting_approval", now),
            )
            conn.commit()
        finally:
            conn.close()
    return {"id": approval_id, "status": "awaiting_approval", "action": action, "payload": payload}

def get_approval(approval_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM fiverr_agent_approvals WHERE id=? AND telegram_user_id=?",
                (str(approval_id), str(user_id)),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            return item
        finally:
            conn.close()

def decide_approval(approval_id: str, user_id: str, approved: bool) -> Optional[Dict[str, Any]]:
    status = "approved" if approved else "rejected"
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute(
                """UPDATE fiverr_agent_approvals
                   SET status=?, decided_at=?
                   WHERE id=? AND telegram_user_id=? AND status='awaiting_approval'""",
                (status, _now(), str(approval_id), str(user_id)),
            )
            conn.commit()
            if not cur.rowcount:
                return get_approval(approval_id, user_id)
            row = conn.execute("SELECT * FROM fiverr_agent_approvals WHERE id=?", (approval_id,)).fetchone()
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            return item
        finally:
            conn.close()

def get_workspace(user_id: str) -> Dict[str, Any]:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT data_json FROM fiverr_agent_tasks WHERE telegram_user_id=? AND kind='workspace_setup' ORDER BY updated_at DESC LIMIT 1",
                (str(user_id),),
            ).fetchone()
            if not row:
                return {}
            try:
                data = json.loads(row["data_json"] or "{}")
                return dict(data.get("workspace") or {})
            except Exception:
                return {}
        finally:
            conn.close()

def save_workspace(user_id: str, workspace: Dict[str, Any]) -> Dict[str, Any]:
    existing = get_workspace(user_id)
    merged = dict(existing)
    merged.update({k: v for k, v in (workspace or {}).items() if v not in (None, "")})
    task = create_task(user_id, "workspace_setup", "Fiverr workspace connection", {"workspace": merged, "step": "connected"})
    update_task(task["id"], user_id, status="connected", data={"workspace": merged, "step": "connected"})
    return merged

def workspace_text(workspace: Dict[str, Any]) -> str:
    if not workspace:
        return "🧑‍💻 <b>FIVERR WORKSPACE</b>\n\nNot configured yet. Use <code>/fiverr setup</code>."
    lines = ["🧑‍💻 <b>FIVERR WORKSPACE</b>", ""]
    labels = [
        ("profile_url", "Profile"),
        ("username", "Username"),
        ("seller_name", "Seller name"),
        ("main_service", "Main service"),
        ("target_buyer", "Target buyer"),
        ("starting_price", "Starting price"),
    ]
    for key, label in labels:
        value = workspace.get(key)
        if value:
            lines.append(f"• <b>{label}:</b> {value}")
    lines += ["", "🟢 Agent workspace is ready for Telegram-controlled Fiverr work.",
              "🔐 Fiverr account/public actions still require supported integration and approval."]
    return "\n".join(lines)

def skills_text() -> str:
    return "\n".join(f"• <b>{k}</b> — {v}" for k, v in SKILLS.items())

def policy_check(draft: str) -> Dict[str, Any]:
    text = (draft or "").strip()
    lower = text.lower()
    flags = []
    patterns = [
        ("off-platform contact", ("telegram", "whatsapp", "contact me outside", "pay me directly", "email me")),
        ("guaranteed outcome", ("guaranteed income", "guaranteed profit", "100% guaranteed", "guaranteed results")),
        ("deceptive identity", ("pretend to be", "impersonate", "fake identity")),
        ("prohibited/regulated service", ("hack into", "steal account", "bypass 2fa", "fake review")),
    ]
    for label, needles in patterns:
        if any(n in lower for n in needles):
            flags.append(label)
    return {
        "ok": not flags,
        "flags": flags,
        "message": "No obvious rule-risk phrase found." if not flags else "Manual review required: " + ", ".join(flags),
    }

def gig_checklist() -> List[str]:
    return [
        "Truthful service and category",
        "Title and up to 5 relevant search tags",
        "1–3 pricing packages with delivery/revisions",
        "Description and FAQ",
        "Client requirements",
        "Owned/authorized gallery assets",
        "Profile/identity/phone verification complete",
        "Final Fiverr policy review before publishing",
    ]

def agent_system_instructions() -> str:
    return """You are FIVERR AGENT, a separate specialist inside KING ZARRY AI.
Your job is to help the user run their Fiverr freelance business.
Skills: gig creation/optimization, profile, SEO/tag research, client replies,
custom offers, order intake, delivery planning, portfolio, pricing, analytics,
policy checking and workflow management.
Never invent the user's qualifications, portfolio, client facts, pricing rules,
Fiverr account data or permissions. Ask the user on Telegram when information is
missing. Keep Fiverr buyer communication on Fiverr. Do not bypass CAPTCHA, 2FA,
anti-bot controls, account restrictions, or platform rules.
Prepare drafts first. Any public/account-changing action requires explicit user
approval and a supported integration. Never claim an action was completed unless
the connected integration returned success.
"""
