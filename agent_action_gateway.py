"""
KING ZARRY AI — Action Gateway.

This is the single enforcement layer between the Agent and external actions.
The LLM/planner never receives raw broker or WhatsApp credentials.

Safe defaults:
- Trades are approval-gated.
- WhatsApp outbound messages are approval-gated.
- Only five approved markets may reach trading execution.
- Live trading is opt-in and kill-switched by environment variables.
- Every action is audited in SQLite.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from trading_connector import APPROVED_SYMBOLS, normalize_symbol, get_account, list_positions, place_market_order, close_position, status as trading_status
from whatsapp_connector import send_text as whatsapp_send_text, status as whatsapp_status
from action_risk_policy import risk_for_action, requires_approval, validate_payload

logger = logging.getLogger("king_zarry_action_gateway")

ACTION_TYPES = {
    "trade.place_order",
    "trade.close_position",
    "whatsapp.send",
}

RISK_LEVELS = {action: risk_for_action(action) for action in ACTION_TYPES}

_LOCK = threading.Lock()


def _db_path() -> str:
    explicit = (os.getenv("AGENT_ACTION_DB_PATH") or "").strip()
    if explicit:
        return os.path.abspath(explicit)
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if data_dir:
        return os.path.abspath(os.path.join(data_dir, "king_zarry_actions.db"))
    return os.path.abspath(os.path.join(os.getcwd(), "king_zarry_actions.db"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    needs_approval INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    approved_at TEXT,
                    executed_at TEXT,
                    result_json TEXT,
                    error TEXT,
                    risk_level TEXT NOT NULL DEFAULT 'red',
                    approval_fingerprint TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_agent_actions_user ON agent_actions(user_id, created_at);
                CREATE TABLE IF NOT EXISTS agent_action_events (
                    id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_action_events_action ON agent_action_events(action_id, created_at);
                """
            )
            for migration in (
                "ALTER TABLE agent_actions ADD COLUMN risk_level TEXT NOT NULL DEFAULT 'red'",
                "ALTER TABLE agent_actions ADD COLUMN approval_fingerprint TEXT",
            ):
                try:
                    conn.execute(migration)
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        finally:
            conn.close()


def _audit(action_id: str, user_id: str, event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
    try:
        init_db()
        safe = _sanitize_payload(dict(details or {}))
        with _LOCK:
            conn = _connect()
            try:
                conn.execute(
                    "INSERT INTO agent_action_events (id, action_id, user_id, event_type, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), str(action_id), str(user_id), str(event_type), json.dumps(safe), _now()),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception as exc:
        logger.warning("Action audit write failed: %s", type(exc).__name__)


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {})
    for key in list(data):
        if "token" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "api_key" in key.lower():
            data[key] = "***REDACTED***"
    return data


def _job_type(action_type: str) -> str:
    return {
        "trade.place_order": "trade_order",
        "trade.close_position": "trade_order",
        "whatsapp.send": "whatsapp_send",
    }[action_type]


def create_action(
    user_id: str,
    action_type: str,
    payload: Dict[str, Any],
    title: str,
) -> Dict[str, Any]:
    init_db()
    action_type = str(action_type or "").strip()
    if action_type not in ACTION_TYPES:
        raise ValueError("unsupported action type")
    if not user_id:
        raise ValueError("user_id required")

    clean = validate_payload(action_type, dict(payload or {}))
    clean.pop("_risk_level", None)
    clean.pop("_approval_required", None)
    if action_type.startswith("trade."):
        symbol = normalize_symbol(str(clean.get("symbol") or ""))
        if symbol not in APPROVED_SYMBOLS:
            raise ValueError("trade symbol must be one of BTC/USD, ETH/USD, SOL/USD, XAU/USD, UNI/USD")
        clean["symbol"] = symbol
    elif action_type == "whatsapp.send":
        if not str(clean.get("to") or "").strip() or not str(clean.get("text") or "").strip():
            raise ValueError("WhatsApp action needs 'to' and 'text'")

    action_id = str(uuid.uuid4())
    now = _now()
    risk_level = risk_for_action(action_type)
    approval_required = requires_approval(action_type)
    fingerprint = uuid.uuid5(uuid.NAMESPACE_URL, json.dumps({"action_type": action_type, "payload": clean}, sort_keys=True, separators=(",", ":"))).hex
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO agent_actions
                (id, user_id, action_type, payload_json, status, needs_approval, created_at, risk_level, approval_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (action_id, str(user_id), action_type, json.dumps(clean), "awaiting_approval" if approval_required else "approved", int(approval_required), now, risk_level, fingerprint),
            )
            conn.commit()
        finally:
            conn.close()

    _audit(action_id, str(user_id), "action_created", {"risk_level": risk_level, "approval_required": approval_required, "action_type": action_type})

    try:
        from agent_core import create_job
        create_job(
            _job_type(action_type),
            title=title,
            payload={"action_id": action_id, **_sanitize_payload(clean)},
            user_id=user_id,
        )
    except Exception as exc:
        logger.warning("Could not mirror action into agent_jobs: %s", type(exc).__name__)

    return get_action(action_id, user_id)


def get_action(action_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_db()
    with _LOCK:
        conn = _connect()
        try:
            if user_id:
                row = conn.execute(
                    "SELECT * FROM agent_actions WHERE id = ? AND user_id = ?",
                    (str(action_id), str(user_id)),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM agent_actions WHERE id = ?",
                    (str(action_id),),
                ).fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["payload"] = json.loads(item.pop("payload_json") or "{}")
            except Exception:
                item["payload"] = {}
            for key in ("result_json",):
                raw = item.get(key)
                if raw:
                    try:
                        item[key] = json.loads(raw)
                    except Exception:
                        pass
            return item
        finally:
            conn.close()


def list_actions(user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    init_db()
    with _LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT id FROM agent_actions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (str(user_id), max(1, min(int(limit), 100))),
            ).fetchall()
        finally:
            conn.close()
    return [item for row in rows if (item := get_action(str(row["id"]), user_id))]


def _update(
    action_id: str,
    user_id: str,
    *,
    status: Optional[str] = None,
    approved_at: Optional[str] = None,
    executed_at: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    init_db()
    fields = []
    values: List[Any] = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if approved_at is not None:
        fields.append("approved_at = ?")
        values.append(approved_at)
    if executed_at is not None:
        fields.append("executed_at = ?")
        values.append(executed_at)
    if result is not None:
        fields.append("result_json = ?")
        values.append(json.dumps(result))
    if error is not None:
        fields.append("error = ?")
        values.append(str(error)[:1200])
    if not fields:
        return get_action(action_id, user_id)
    values.extend([str(action_id), str(user_id)])
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                f"UPDATE agent_actions SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
        finally:
            conn.close()
    return get_action(action_id, user_id)


def _record_agent_job_result(action: Dict[str, Any], status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
    try:
        from agent_core import list_jobs
        jobs = list_jobs(action["user_id"], limit=30)
        for job in jobs:
            payload = json.loads(job.get("payload_json") or "{}") if isinstance(job.get("payload_json"), str) else (job.get("payload_json") or {})
            if payload.get("action_id") == action["id"]:
                from agent_core import _update_job
                _update_job(job["id"], status=status, result=result, error=error)
                return
    except Exception:
        pass


def _trade_risk_gate(payload: Dict[str, Any]) -> Dict[str, Any]:
    symbol = normalize_symbol(str(payload.get("symbol") or ""))
    side = str(payload.get("side") or "").upper()
    if symbol not in APPROVED_SYMBOLS:
        return {"status": "BLOCK", "approved": False, "reasons": ["symbol outside approved universe"]}
    if side not in {"BUY", "SELL"}:
        return {"status": "BLOCK", "approved": False, "reasons": ["side must be BUY or SELL"]}

    try:
        from agent_core import tool_analyze_symbol, tool_news_risk
        from agent_v2 import verify_setup
        from risk_guardian import evaluate_risk_guardian
        analysis = tool_analyze_symbol(symbol)
        analysis["news_risk"] = tool_news_risk(symbol)
        verification = verify_setup(analysis)
        guardian = evaluate_risk_guardian(symbol, analysis, verification)
        if str(analysis.get("signal") or "").upper() != side:
            guardian = {
                **guardian,
                "status": "BLOCK",
                "approved": False,
                "reasons": [f"requested {side} but fresh Agent analysis is {str(analysis.get('signal') or 'WAIT').upper()}"] + list(guardian.get("reasons") or []),
            }
        return {
            "guardian": guardian,
            "analysis": analysis,
            "verification": verification,
        }
    except Exception as exc:
        return {
            "guardian": {"status": "BLOCK", "approved": False, "reasons": [f"risk gate unavailable: {type(exc).__name__}"]},
        }


def approve_action(action_id: str, user_id: str) -> Dict[str, Any]:
    action = get_action(action_id, user_id)
    if not action:
        raise ValueError("action not found")
    if action["status"] not in {"awaiting_approval", "approved"}:
        return action
    now = _now()
    if action.get("status") == "awaiting_approval":
        with _LOCK:
            conn = _connect()
            try:
                cur = conn.execute(
                    "UPDATE agent_actions SET status='approved', approved_at=? WHERE id=? AND user_id=? AND status='awaiting_approval'",
                    (now, str(action_id), str(user_id)),
                )
                conn.commit()
                if cur.rowcount != 1:
                    return get_action(action_id, user_id) or action
            finally:
                conn.close()
        _audit(action_id, str(user_id), "approval_granted", {"risk_level": action.get("risk_level", "red")})
    try:
        return execute_action(action_id, user_id)
    except Exception as exc:
        logger.error("action execution failed: %s: %s", type(exc).__name__, str(exc)[:300])
        _update(action_id, user_id, status="failed", executed_at=_now(), error=str(exc)[:1200])
        updated = get_action(action_id, user_id) or action
        _audit(action_id, str(user_id), "execution_failed", {"risk_level": action.get("risk_level", "red"), "error_type": type(exc).__name__})
        _record_agent_job_result(updated, "failed", error=str(exc)[:1200])
        return updated


def execute_action(action_id: str, user_id: str) -> Dict[str, Any]:
    action = get_action(action_id, user_id)
    if not action:
        raise ValueError("action not found")
    if action["status"] not in {"approved", "awaiting_approval"}:
        return action
    if action["status"] == "awaiting_approval":
        raise PermissionError("approval is required before execution")

    if action["status"] == "approved":
        with _LOCK:
            conn = _connect()
            try:
                cur = conn.execute(
                    "UPDATE agent_actions SET status='executing' WHERE id=? AND user_id=? AND status='approved'",
                    (str(action_id), str(user_id)),
                )
                conn.commit()
                if cur.rowcount != 1:
                    return get_action(action_id, user_id) or action
            finally:
                conn.close()
        _audit(action_id, str(user_id), "execution_claimed", {"risk_level": action.get("risk_level", "red")})
        action = get_action(action_id, user_id) or action
    elif action["status"] != "executing":
        return action

    action_type = action["action_type"]
    payload = action["payload"]

    validate_payload(action_type, payload)

    if action_type == "whatsapp.send":
        result = whatsapp_send_text(payload["to"], payload["text"])
    elif action_type == "trade.place_order":
        risk = _trade_risk_gate(payload)
        guardian = risk.get("guardian") or {}
        if not guardian.get("approved"):
            raise PermissionError("Risk Guardian blocked the trade: " + "; ".join(guardian.get("reasons") or [])[:700])
        result = place_market_order(
            payload["symbol"],
            payload["side"],
            float(payload["quantity"]),
        )
        result["risk_guardian"] = guardian
        result["verification"] = risk.get("verification")
    elif action_type == "trade.close_position":
        result = close_position(
            payload["symbol"],
            float(payload["quantity"]) if payload.get("quantity") is not None else None,
        )
    else:
        raise ValueError("unsupported action type")

    updated = _update(
        action_id,
        user_id,
        status="completed",
        executed_at=_now(),
        result=result,
        error=None,
    )
    _audit(action_id, str(user_id), "execution_completed", {"risk_level": action.get("risk_level", "red")})
    _record_agent_job_result(updated or action, "completed", result=result)
    return updated or action


def plan_action_from_goal(goal: str, user_id: str) -> Dict[str, Any]:
    """Turn a small, explicit natural-language request into an approval-gated action."""
    text = (goal or "").strip()
    lower = text.lower()
    if not text:
        return {"status": "error", "detail": "Empty goal"}

    # WhatsApp: require an international number and message text.
    if "whatsapp" in lower:
        number_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        msg_match = re.search(r"(?:saying|message|text)\s*[:=-]?\s*[“”\"']?(.+?)\s*[”\"']?$", text, re.I)
        if not number_match or not msg_match:
            return {
                "status": "needs_details",
                "detail": "WhatsApp action needs a recipient international phone number and message text. Example: Send WhatsApp to +2348012345678 saying Hello.",
            }
        to = number_match.group(0)
        message = msg_match.group(1).strip(" \"'”")
        action = create_action(
            user_id,
            "whatsapp.send",
            {"to": to, "text": message},
            title="Send WhatsApp message (approval required)",
        )
        return {
            "status": "awaiting_approval",
            "action": action,
            "message": "WhatsApp action prepared. Approve it to send through the official Meta connector.",
        }

    # Safe account/position read: no approval and no order execution.
    if any(k in lower for k in ("my positions", "open positions", "open trades", "trading account", "account status")):
        try:
            return {"status": "completed", "account": account_snapshot()}
        except Exception as exc:
            return {"status": "error", "detail": f"Could not read trading account: {type(exc).__name__}"}

    # Close an existing position. Still approval-gated because it changes an account.
    if any(k in lower for k in ("close position", "close trade", "close my")):
        aliases = {
            "btc": "BTC/USD", "bitcoin": "BTC/USD",
            "eth": "ETH/USD", "ethereum": "ETH/USD",
            "sol": "SOL/USD", "solana": "SOL/USD",
            "xau": "XAU/USD", "gold": "XAU/USD",
            "uni": "UNI/USD", "uniswap": "UNI/USD",
        }
        close_symbol = next((sym for key, sym in aliases.items() if re.search(rf"\b{re.escape(key)}\b", lower)), None)
        if not close_symbol:
            return {"status": "needs_details", "detail": "Tell me which approved market to close: BTC, ETH, SOL, XAU, or UNI."}
        action = create_action(
            user_id,
            "trade.close_position",
            {"symbol": close_symbol},
            title=f"Close {close_symbol} position (approval required)",
        )
        return {
            "status": "awaiting_approval",
            "action": action,
            "message": "Close action prepared. Approve it to close the selected position.",
        }

    # Trade: explicit direction + quantity + one of the five symbols.
    side = "BUY" if re.search(r"\b(buy|long)\b", lower) else "SELL" if re.search(r"\b(sell|short)\b", lower) else None
    symbol = None
    aliases = {
        "btc": "BTC/USD", "bitcoin": "BTC/USD",
        "eth": "ETH/USD", "ethereum": "ETH/USD",
        "sol": "SOL/USD", "solana": "SOL/USD",
        "xau": "XAU/USD", "gold": "XAU/USD",
        "uni": "UNI/USD", "uniswap": "UNI/USD",
    }
    for key, sym in aliases.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            symbol = sym
            break
    qty_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:units?|qty|quantity)?\b", lower)
    if side and symbol:
        if not qty_match:
            return {
                "status": "needs_details",
                "detail": f"Trade request detected for {side} {symbol}, but quantity is missing. Example: {side} 0.01 {symbol.split('/')[0]}",
            }
        quantity = float(qty_match.group(1))
        action = create_action(
            user_id,
            "trade.place_order",
            {"symbol": symbol, "side": side, "quantity": quantity},
            title=f"{side} {symbol} (Risk Guardian + approval required)",
        )
        return {
            "status": "awaiting_approval",
            "action": action,
            "message": "Trade action prepared. Approval triggers a fresh analysis + Risk Guardian check before execution.",
        }

    return {
        "status": "unsupported",
        "detail": (
            "This gateway currently handles explicit trade orders and WhatsApp messages. "
            "Existing market scans and briefs continue to work unchanged."
        ),
    }


def connector_status() -> Dict[str, Any]:
    return {
        "trading": trading_status(),
        "whatsapp": whatsapp_status(),
        "action_types": sorted(ACTION_TYPES),
        "risk_levels": dict(RISK_LEVELS),
        "approval_required": {action: requires_approval(action) for action in ACTION_TYPES},
        "approved_markets": list(APPROVED_SYMBOLS),
    }


def account_snapshot() -> Dict[str, Any]:
    return {
        "trading": trading_status(),
        "account": get_account(),
        "positions": list_positions(),
    }
