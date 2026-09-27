"""
KING ZARRY AI — Agent core (Phase 1)

Planner + tools that already exist:
  - market analysis (market.py)
  - news risk (market/news)
  - memory preferences / facts (memory.py)
  - job log with approval flags for risky actions

Phase 1 ships:
  - Overnight / daily market watch brief
  - Morning signal package (BTC, ETH, SOL, XAU)
  - Auto-learn loop: store outcomes + user preferences
  - Job log (safe jobs auto-run; risky jobs need approval)

Later phases (stubs only — do not claim live):
  - Browser tool on user device
  - Social OAuth connectors
  - WhatsApp Business API
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("king_zarry_agent")

DEFAULT_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD"]
RISKY_JOB_TYPES = {"social_post", "whatsapp_send", "browser_action", "email_send"}

_DB_LOCK = threading.Lock()


def _agent_db_path() -> str:
    """Prefer DATA_DIR / AGENT_DB_PATH; never die if /data is not writable."""
    safe_local = os.path.join(os.getcwd(), "king_zarry_agent.db")
    candidates = []

    agent_explicit = (os.getenv("AGENT_DB_PATH") or "").strip()
    if agent_explicit:
        candidates.append(agent_explicit)

    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if data_dir and not data_dir.endswith(".db"):
        candidates.append(os.path.join(data_dir, "king_zarry_agent.db"))

    mem = (os.getenv("MEMORY_DB_PATH") or "").strip()
    if mem:
        if mem.endswith(".db"):
            base = os.path.dirname(mem) or "."
        else:
            base = mem
        candidates.append(os.path.join(base, "king_zarry_agent.db"))

    candidates.append(safe_local)

    last_err = None
    for path in candidates:
        try:
            abspath = os.path.abspath(path)
            directory = os.path.dirname(abspath) or os.getcwd()
            os.makedirs(directory, exist_ok=True)
            test = os.path.join(directory, ".kz_agent_write_test")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            if path != safe_local and last_err:
                print(
                    f"⚠️ Agent DB fallback avoided; using writable {abspath}",
                    flush=True,
                )
            return abspath
        except OSError as e:
            last_err = e
            continue

    print(
        f"⚠️ Agent DB: all paths failed (last={last_err}). Using {safe_local}",
        flush=True,
    )
    return os.path.abspath(safe_local)


def _connect() -> sqlite3.Connection:
    path = _agent_db_path()
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    except sqlite3.OperationalError:
        # Absolute last resort
        path = os.path.abspath(os.path.join(os.getcwd(), "king_zarry_agent.db"))
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_agent_db() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    job_type TEXT NOT NULL,
                    title TEXT,
                    payload_json TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    needs_approval INTEGER NOT NULL DEFAULT 0,
                    approved_at TEXT,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agent_learning (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    symbol TEXT,
                    signal TEXT,
                    confidence TEXT,
                    notes TEXT,
                    outcome TEXT,
                    meta_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS morning_briefs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    trading_date TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_user ON agent_jobs(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_learn_user ON agent_learning(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_briefs_date ON morning_briefs(trading_date);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trading_date_str() -> str:
    try:
        from market import get_trading_date

        return str(get_trading_date())
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def create_job(
    job_type: str,
    title: str,
    payload: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    init_agent_db()
    job_id = str(uuid.uuid4())
    now = _now_iso()
    needs_approval = 1 if job_type in RISKY_JOB_TYPES else 0
    status = "awaiting_approval" if needs_approval else "pending"
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO agent_jobs
                (id, user_id, job_type, title, payload_json, status, needs_approval, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    str(user_id) if user_id else None,
                    job_type,
                    title,
                    json.dumps(payload or {}),
                    status,
                    needs_approval,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    return get_job(job_id) or {"id": job_id, "status": status}


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    init_agent_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM agent_jobs WHERE id = ?", (job_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def list_jobs(user_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    init_agent_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            if user_id:
                rows = conn.execute(
                    """
                    SELECT * FROM agent_jobs
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (str(user_id), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def approve_job(job_id: str) -> Optional[Dict[str, Any]]:
    init_agent_db()
    now = _now_iso()
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE agent_jobs
                SET status = 'pending', approved_at = ?, updated_at = ?, needs_approval = 0
                WHERE id = ? AND status = 'awaiting_approval'
                """,
                (now, now, job_id),
            )
            conn.commit()
        finally:
            conn.close()
    return get_job(job_id)


def _update_job(
    job_id: str,
    *,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE agent_jobs
                SET status = ?, result_json = ?, error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(result) if result is not None else None,
                    error,
                    _now_iso(),
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Tools (existing stack)
# ---------------------------------------------------------------------------

def tool_analyze_symbol(symbol: str, timeframe: str = "15m") -> Dict[str, Any]:
    try:
        from market import analyze_market

        data = analyze_market(symbol, timeframe=timeframe)
        if not isinstance(data, dict):
            return {"symbol": symbol, "error": "no data", "signal": "WAIT"}
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": data.get("price") or data.get("current_price"),
            "signal": data.get("signal") or data.get("mtf_signal") or "WAIT",
            "trend": data.get("trend") or data.get("mtf_bias"),
            "confidence": data.get("confidence"),
            "strength": data.get("strength") or data.get("mtf_strength"),
            "rsi": data.get("rsi"),
            "support": data.get("support"),
            "resistance": data.get("resistance"),
            "reasons": (data.get("reasons") or [])[:6],
            "raw_keys": list(data.keys())[:20],
        }
    except Exception as e:
        logger.warning("tool_analyze_symbol failed %s: %s", symbol, type(e).__name__)
        return {"symbol": symbol, "error": type(e).__name__, "signal": "WAIT"}


def tool_news_risk(symbol: str) -> Dict[str, Any]:
    try:
        from market import get_news_risk_safe

        return get_news_risk_safe(symbol) or {}
    except Exception as e:
        return {"symbol": symbol, "error": type(e).__name__}


def tool_learn(
    user_id: Optional[str],
    symbol: str,
    signal: str,
    confidence: str = "",
    notes: str = "",
    outcome: str = "observed",
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist a learning event so the agent improves preference weighting over time."""
    init_agent_db()
    lid = str(uuid.uuid4())
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO agent_learning
                (id, user_id, symbol, signal, confidence, notes, outcome, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lid,
                    str(user_id) if user_id else None,
                    symbol,
                    signal,
                    confidence,
                    notes[:2000],
                    outcome,
                    json.dumps(meta or {}),
                    _now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # Also mirror a short fact into Memory when available (Telegram-style memory DB)
    if user_id:
        try:
            from memory import Memory

            mem = Memory()
            fact = f"Agent observed {symbol} signal={signal} confidence={confidence} ({outcome})"
            if hasattr(mem, "add_user_fact"):
                mem.add_user_fact(user_id, fact, category="agent_learning", source="agent")
            elif hasattr(mem, "save_fact"):
                mem.save_fact(user_id, fact)
        except Exception:
            pass
    return lid


def recent_learning(user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    init_agent_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            if user_id:
                rows = conn.execute(
                    """
                    SELECT * FROM agent_learning
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (str(user_id), limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM agent_learning ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Morning brief / overnight watch
# ---------------------------------------------------------------------------

def build_morning_brief(
    symbols: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Watch what the market did and package a fresh multi-asset signal brief.
    Intended to run near wake-up time (cron / manual / API).
    """
    symbols = symbols or list(DEFAULT_SYMBOLS)
    trading_date = _trading_date_str()
    started = time.time()
    assets: List[Dict[str, Any]] = []

    for sym in symbols:
        analysis = tool_analyze_symbol(sym, timeframe="15m")
        news = tool_news_risk(sym)
        analysis["news_risk"] = news
        assets.append(analysis)
        tool_learn(
            user_id,
            symbol=sym,
            signal=str(analysis.get("signal") or "WAIT"),
            confidence=str(analysis.get("confidence") or ""),
            notes=f"morning_brief {trading_date}",
            outcome="morning_scan",
            meta={"price": analysis.get("price"), "trend": analysis.get("trend")},
        )

    actionable = [
        a
        for a in assets
        if str(a.get("signal") or "").upper() in ("BUY", "SELL")
    ]
    waits = [a for a in assets if a not in actionable]

    summary_lines = [
        f"📅 Trading date: {trading_date}",
        f"🧠 King Zarry overnight watch complete ({len(assets)} assets).",
        "",
    ]
    if actionable:
        summary_lines.append("⚡ Actionable bias:")
        for a in actionable:
            summary_lines.append(
                f"  • {a.get('symbol')}: {a.get('signal')} "
                f"@ {a.get('price')} | conf={a.get('confidence')} | trend={a.get('trend')}"
            )
    else:
        summary_lines.append("⏸ No strong multi-asset BUY/SELL — market is mixed/WAIT.")

    if waits:
        summary_lines.append("")
        summary_lines.append("WAIT / watchlist:")
        for a in waits:
            summary_lines.append(
                f"  • {a.get('symbol')}: {a.get('signal')} @ {a.get('price')}"
            )

    summary_lines.append("")
    summary_lines.append(
        "⚠️ Not financial advice. Trading involves risk. Auto-learn logged this scan."
    )

    brief = {
        "id": str(uuid.uuid4()),
        "trading_date": trading_date,
        "generated_at": _now_iso(),
        "duration_sec": round(time.time() - started, 2),
        "assets": assets,
        "actionable_count": len(actionable),
        "summary_text": "\n".join(summary_lines),
        "user_id": user_id,
        "disclaimer": "Not financial advice. Trading involves risk.",
    }

    init_agent_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO morning_briefs (id, user_id, trading_date, brief_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    brief["id"],
                    str(user_id) if user_id else None,
                    trading_date,
                    json.dumps(brief),
                    _now_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    return brief


def get_latest_morning_brief(user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_agent_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            if user_id:
                row = conn.execute(
                    """
                    SELECT brief_json FROM morning_briefs
                    WHERE user_id = ? OR user_id IS NULL
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (str(user_id),),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT brief_json FROM morning_briefs ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            if not row:
                return None
            return json.loads(row["brief_json"])
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def plan_and_run(
    goal: str,
    user_id: Optional[str] = None,
    auto_approve_safe: bool = True,
) -> Dict[str, Any]:
    """
    Lightweight planner: map natural language goal → job + tools.
    Risky social/browser goals are logged as awaiting_approval only.
    """
    g = (goal or "").strip().lower()
    if not g:
        return {"status": "error", "detail": "Empty goal"}

    # Risky stubs — never auto-execute
    if any(k in g for k in ("whatsapp", "post on", "tweet", "instagram", "facebook")):
        job = create_job(
            "social_post",
            title="Social / messaging action (needs approval)",
            payload={"goal": goal},
            user_id=user_id,
        )
        return {
            "status": "awaiting_approval",
            "job": job,
            "message": (
                "This needs your approval and an official connector "
                "(WhatsApp Business / OAuth). Not auto-run."
            ),
        }

    if "browser" in g or "open chrome" in g:
        job = create_job(
            "browser_action",
            title="Browser action (needs approval + user-device tool)",
            payload={"goal": goal},
            user_id=user_id,
        )
        return {
            "status": "awaiting_approval",
            "job": job,
            "message": "Browser control runs only on your device with approval. Not server-side.",
        }

    # Safe: morning brief / overnight watch / new signal
    if any(
        k in g
        for k in (
            "morning",
            "wake",
            "overnight",
            "daily brief",
            "watch market",
            "full day",
            "new signal",
            "morning signal",
        )
    ):
        job = create_job(
            "morning_brief",
            title="Daily market watch + morning signal",
            payload={"goal": goal},
            user_id=user_id,
        )
        brief = build_morning_brief(user_id=user_id)
        _update_job(job["id"], status="completed", result=brief)
        return {
            "status": "completed",
            "job_id": job["id"],
            "brief": brief,
            "summary": brief.get("summary_text"),
        }

    # Safe: analyze one symbol if mentioned
    symbol_map = {
        "btc": "BTC/USD",
        "bitcoin": "BTC/USD",
        "eth": "ETH/USD",
        "ethereum": "ETH/USD",
        "sol": "SOL/USD",
        "solana": "SOL/USD",
        "gold": "XAU/USD",
        "xau": "XAU/USD",
    }
    hit = None
    for k, sym in symbol_map.items():
        if k in g:
            hit = sym
            break
    if hit or "signal" in g or "analy" in g:
        sym = hit or "BTC/USD"
        job = create_job(
            "market_scan",
            title=f"Analyze {sym}",
            payload={"symbol": sym, "goal": goal},
            user_id=user_id,
        )
        analysis = tool_analyze_symbol(sym)
        tool_learn(
            user_id,
            symbol=sym,
            signal=str(analysis.get("signal") or "WAIT"),
            confidence=str(analysis.get("confidence") or ""),
            notes=goal[:500],
            outcome="on_demand_scan",
        )
        _update_job(job["id"], status="completed", result=analysis)
        return {
            "status": "completed",
            "job_id": job["id"],
            "analysis": analysis,
        }

    # Default: run full morning-style multi scan as research job
    job = create_job(
        "research",
        title="General market research",
        payload={"goal": goal},
        user_id=user_id,
    )
    brief = build_morning_brief(user_id=user_id)
    _update_job(job["id"], status="completed", result={"goal": goal, "brief": brief})
    return {
        "status": "completed",
        "job_id": job["id"],
        "brief": brief,
        "summary": brief.get("summary_text"),
    }


def agent_status() -> Dict[str, Any]:
    init_agent_db()
    return {
        "phase": 1,
        "tools_live": ["market", "news_risk", "memory_learn", "morning_brief", "job_log"],
        "tools_roadmap": ["browser_user_device", "social_oauth", "whatsapp_business"],
        "db": _agent_db_path(),
        "default_symbols": DEFAULT_SYMBOLS,
        "risky_job_types": sorted(RISKY_JOB_TYPES),
    }


# CLI entry for Railway cron / manual
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_agent_db()
    print("Agent status:", json.dumps(agent_status(), indent=2))
    brief = build_morning_brief()
    print(brief.get("summary_text", ""))
    print("Brief id:", brief.get("id"))
