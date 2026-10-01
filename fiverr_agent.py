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
    "inbox_manager": "Store and triage Fiverr inbox events supplied by a supported integration.",
    "gig_manager": "Track Gig creation and optimization work as persistent tasks.",
    "offer_manager": "Track Custom Offer preparation and approval.",
    "order_manager": "Track buyer/order intake and requirements.",
    "delivery_manager": "Track delivery preparation and QA.",
    "integration_bridge": "Receive structured events from an official/supported integration without credentials or session cookies.",
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
    """Initialize the Fiverr Agent SQLite store safely across Railway processes."""
    last_error = None
    for attempt in range(6):
        conn = None
        try:
            with _LOCK:
                conn = _connect()
                conn.execute("PRAGMA busy_timeout=30000")
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

                CREATE TABLE IF NOT EXISTS fiverr_agent_inbox (
                    id TEXT PRIMARY KEY,
                    telegram_user_id TEXT NOT NULL,
                    external_id TEXT,
                    conversation_id TEXT,
                    sender_name TEXT,
                    sender_username TEXT,
                    subject TEXT,
                    message TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unread',
                    raw_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_fiverr_inbox_user
                    ON fiverr_agent_inbox(telegram_user_id, received_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_fiverr_inbox_external
                    ON fiverr_agent_inbox(telegram_user_id, external_id)
                    WHERE external_id IS NOT NULL;
                """)
                conn.commit()
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            if attempt < 5:
                import time
                time.sleep(0.5 * (attempt + 1))
        finally:
            if conn is not None:
                conn.close()
    if last_error is not None:
        raise last_error

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

def ingest_inbox_message(user_id: str, message: str, external_id: Optional[str] = None,
                         conversation_id: Optional[str] = None, sender_name: Optional[str] = None,
                         sender_username: Optional[str] = None, subject: Optional[str] = None,
                         received_at: Optional[str] = None, raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store an inbox event supplied by an official/supported integration."""
    item_id = str(uuid.uuid4())
    now = received_at or _now()
    with _LOCK:
        conn = _connect()
        try:
            if external_id:
                old = conn.execute("SELECT * FROM fiverr_agent_inbox WHERE telegram_user_id=? AND external_id=? LIMIT 1",
                                   (str(user_id), str(external_id))).fetchone()
                if old:
                    item = dict(old)
                    item["raw"] = json.loads(item.pop("raw_json") or "{}")
                    return item
            conn.execute("""INSERT INTO fiverr_agent_inbox
                (id,telegram_user_id,external_id,conversation_id,sender_name,sender_username,subject,message,received_at,status,raw_json)
                VALUES(?,?,?,?,?,?,?,?,?,'unread',?)""",
                (item_id, str(user_id), str(external_id) if external_id else None,
                 str(conversation_id) if conversation_id else None, str(sender_name or "")[:200],
                 str(sender_username or "")[:200], str(subject or "")[:300], str(message)[:12000],
                 str(now), json.dumps(raw or {}, ensure_ascii=False)))
            conn.commit()
            row = conn.execute("SELECT * FROM fiverr_agent_inbox WHERE id=?", (item_id,)).fetchone()
            item = dict(row)
            item["raw"] = json.loads(item.pop("raw_json") or "{}")
            return item
        finally:
            conn.close()

def list_inbox(user_id: str, limit: int = 20, unread_only: bool = False) -> List[Dict[str, Any]]:
    with _LOCK:
        conn = _connect()
        try:
            sql = "SELECT * FROM fiverr_agent_inbox WHERE telegram_user_id=?"
            params: List[Any] = [str(user_id)]
            if unread_only:
                sql += " AND status='unread'"
            sql += " ORDER BY received_at DESC LIMIT ?"
            params.append(max(1, min(int(limit), 50)))
            rows = conn.execute(sql, params).fetchall()
            out = []
            for row in rows:
                item = dict(row)
                item["raw"] = json.loads(item.pop("raw_json") or "{}")
                out.append(item)
            return out
        finally:
            conn.close()

def mark_inbox_read(item_id: str, user_id: str) -> bool:
    with _LOCK:
        conn = _connect()
        try:
            cur = conn.execute("UPDATE fiverr_agent_inbox SET status='read' WHERE id=? AND telegram_user_id=?",
                               (str(item_id), str(user_id)))
            conn.commit()
            return bool(cur.rowcount)
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

def workspace_missing(workspace: Dict[str, Any]) -> List[str]:
    required = [
        ("profile_url", "Fiverr profile URL or username"),
        ("seller_name", "seller/display name"),
        ("main_service", "main service"),
        ("target_buyer", "target buyer"),
        ("starting_price", "starting price/package range"),
    ]
    return [label for key, label in required if not str(workspace.get(key) or "").strip()]


def task_context(task: Dict[str, Any]) -> str:
    data = task.get("data") or {}
    messages = data.get("messages") or []
    if not messages:
        return ""
    lines = []
    for item in messages[-12:]:
        role = str(item.get("role") or "user").upper()
        content = str(item.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def is_missing_information_response(answer: str) -> bool:
    text = (answer or "").strip().lower()
    if not text:
        return True
    markers = (
        "i need more information",
        "please provide",
        "please tell me",
        "i need the following",
        "missing information",
        "before i can",
        "a few questions",
        "questions:",
    )
    question_count = (answer or "").count("?")
    return any(marker in text for marker in markers) or question_count >= 1 and question_count <= 8


def render_manual_execution_pack(task: Dict[str, Any]) -> str:
    data = task.get("data") or {}
    draft = str(data.get("draft") or "").strip()
    policy = data.get("policy_check") or {}
    lines = [
        "FIVERR AGENT — MANUAL EXECUTION PACK",
        f"Task: {task.get('id', '')}",
        f"Type: {task.get('kind', '')}",
        f"Status: {task.get('status', '')}",
        "",
        "DRAFT",
        draft,
        "",
        "POLICY CHECK",
        policy.get("message", "Not checked."),
        "",
        "EXECUTION",
        "Copy the approved draft into Fiverr manually. Do not share passwords, 2FA codes, recovery codes or session cookies.",
    ]
    return "\n".join(lines)


def agent_system_instructions() -> str:
    return """You are FIVERR AGENT, a separate professional specialist inside KING ZARRY AI.
Your job is to help the user operate a Fiverr freelance business from Telegram.
You are a workflow assistant, copywriter, planner, researcher and quality-control layer.

OPERATING STANDARD
1. Never invent qualifications, portfolio items, client facts, account data, prices,
   delivery promises, reviews, certifications or permissions.
2. Use the user's saved Fiverr workspace as context, but ask focused questions when
   important information is missing.
3. Build professional, ready-to-paste drafts with clear headings and complete fields.
4. For a Gig, normally include: title, category/subcategory, search tags, packages,
   delivery time, revisions, description, FAQs, requirements, gallery/media checklist
   and a final quality-control checklist.
5. For Buyer replies, keep the tone concise, professional and human. Never promise
   work or results the user has not authorized.
6. For Custom Offers, clearly separate scope, deliverables, exclusions, price,
   delivery time, revisions and buyer requirements.
7. For order intake, identify ambiguities before proposing a delivery plan.
8. Keep Fiverr buyer communication on Fiverr.
9. Do not bypass CAPTCHA, 2FA, anti-bot controls, account restrictions or platform rules.
10. Never claim that something was published, sent, edited or completed on Fiverr unless
    a supported integration actually returned success.
11. Without an official/supported Fiverr execution integration, produce an approved
    manual execution pack instead of pretending to perform the action.
12. Before approval, show the user the actual draft and policy-check result.\n13. Supported integration events may be stored and routed to Telegram; never fabricate them.\n14. Never request or store Fiverr passwords, 2FA codes, recovery codes or session cookies.
"""
