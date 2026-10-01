"""
KING ZARRY AI — Agent V2 decision + lifecycle layer.

Additive upgrade for the existing agent:
- second-pass setup verification
- explicit SIGNAL / WAIT decision
- persistent signal IDs across restarts
- active signal lifecycle tracking
- TP/SL milestone events
- terminal outcome learning
- performance summary helpers

This module never invents prices. It only evaluates data already returned by the
existing market/agent analysis layer.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("king_zarry_agent_v2")

_DB_LOCK = threading.Lock()


def _db_path() -> str:
    try:
        from agent_core import _agent_db_path
        return _agent_db_path()
    except Exception:
        explicit = (os.getenv("AGENT_DB_PATH") or "").strip()
        if explicit:
            return os.path.abspath(explicit)
        data_dir = (os.getenv("DATA_DIR") or "").strip()
        if data_dir and not data_dir.endswith(".db"):
            return os.path.abspath(os.path.join(data_dir, "king_zarry_agent.db"))
        return os.path.abspath("king_zarry_agent.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _env_bool(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return default


def _min_score() -> float:
    try:
        return max(0.0, min(100.0, float(os.getenv("AGENT_V2_MIN_SCORE", "65"))))
    except Exception:
        return 65.0


def _max_age_hours() -> float:
    try:
        return max(1.0, float(os.getenv("AGENT_V2_MAX_AGE_HOURS", "48")))
    except Exception:
        return 48.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _numeric(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    text = str(value).replace(",", "")
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not nums:
        return None
    try:
        if len(nums) >= 2 and any(sep in text for sep in ("-", "to", "–", "—")):
            return (float(nums[0]) + float(nums[1])) / 2.0
        return float(nums[0])
    except Exception:
        return None


def _percent_like(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        v = float(value)
        if 0 <= v <= 1:
            return v * 100.0
        return v
    if value is None:
        return None
    text = str(value).upper()
    n = _numeric(text)
    return n


def _direction(text: Any) -> str:
    return str(text or "").upper().strip()


def _alignment_score(signal: str, trend: Any) -> Tuple[int, str]:
    t = str(trend or "").upper()
    if not t:
        return 0, "trend unavailable"
    bullish = any(k in t for k in ("BULL", "UPTREND", "UP", "LONG", "BUY", "HH", "HIGHER HIGH"))
    bearish = any(k in t for k in ("BEAR", "DOWNTREND", "DOWN", "SHORT", "SELL", "LL", "LOWER LOW"))
    if signal == "BUY" and bullish and not bearish:
        return 12, "higher-timeframe bias aligned"
    if signal == "SELL" and bearish and not bullish:
        return 12, "higher-timeframe bias aligned"
    if (signal == "BUY" and bearish) or (signal == "SELL" and bullish):
        return -14, "trend conflicts with signal direction"
    return 0, "trend not decisive"


def _structure_score(structure: Any) -> Tuple[int, str]:
    s = str(structure or "").upper()
    if not s:
        return 0, "structure unavailable"
    strong = (
        "BREAKOUT" in s
        or "PULLBACK" in s
        or "RETEST" in s
        or "HIGHER HIGH" in s
        or "LOWER LOW" in s
        or "CONTINUATION" in s
        or "CONFIRMED" in s
    )
    conflict = "CHOP" in s or "RANGE" in s or "CONFLICT" in s
    if strong and not conflict:
        return 8, "market structure confirms setup"
    if conflict:
        return -6, "market structure is mixed/choppy"
    return 0, "structure neutral"


def _news_score(news_risk: Any) -> Tuple[int, str]:
    if not news_risk:
        return 0, "no news-risk flag"
    raw = news_risk
    if isinstance(raw, dict):
        raw = " ".join(
            str(raw.get(k) or "")
            for k in ("risk", "level", "severity", "status", "reason", "summary")
        )
    s = str(raw).upper()
    if any(k in s for k in ("CRITICAL", "EXTREME")):
        return -18, "critical news risk"
    if any(k in s for k in ("HIGH", "RED", "MAJOR")):
        return -12, "high news risk"
    if any(k in s for k in ("MEDIUM", "ELEVATED", "AMBER")):
        return -5, "elevated news risk"
    return 0, "news risk not elevated"


def verify_setup(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Second-pass verifier. Returns a structured SIGNAL/WAIT decision.
    The verifier only uses existing analysis fields.
    """
    signal = _direction(analysis.get("signal"))
    reasons: List[str] = []
    checks: List[Dict[str, Any]] = []

    if signal not in ("BUY", "SELL"):
        return {
            "enabled": _env_bool("AGENT_V2_VERIFY", True),
            "decision": "WAIT",
            "score": 0,
            "threshold": _min_score(),
            "reasons": ["no actionable direction"],
            "checks": [{"name": "direction", "ok": False, "impact": 0}],
        }

    data_ok = bool(analysis.get("data_ok", True))
    if not data_ok:
        return {
            "enabled": _env_bool("AGENT_V2_VERIFY", True),
            "decision": "WAIT",
            "score": 0,
            "threshold": _min_score(),
            "reasons": ["market data is unavailable"],
            "checks": [{"name": "data", "ok": False, "impact": 0}],
        }

    if bool(analysis.get("late_entry")) or str(analysis.get("entry_quality") or "").upper() in ("LATE", "RISKY"):
        return {
            "enabled": _env_bool("AGENT_V2_VERIFY", True),
            "decision": "WAIT",
            "score": 0,
            "threshold": _min_score(),
            "reasons": [str(analysis.get("late_entry_reason") or "entry is too late")[:220]],
            "checks": [{"name": "entry_location", "ok": False, "impact": 0}],
        }

    # Start from a conservative baseline, then reward corroborating evidence.
    score = 40.0

    conf = _percent_like(analysis.get("confidence"))
    if conf is not None:
        conf = max(0.0, min(100.0, conf))
        impact = (conf - 50.0) * 0.45
        score += impact
        checks.append({"name": "confidence", "ok": conf >= 50, "impact": round(impact, 1), "value": conf})
        reasons.append(f"confidence={conf:.0f}")
    else:
        score += 12.0
        checks.append({"name": "confidence", "ok": None, "impact": 12.0, "value": None})
        reasons.append("confidence unavailable; corroboration required")

    impact, reason = _alignment_score(signal, analysis.get("trend"))
    score += impact
    checks.append({"name": "trend_alignment", "ok": impact >= 0, "impact": impact})
    reasons.append(reason)

    impact, reason = _structure_score(analysis.get("structure"))
    score += impact
    checks.append({"name": "structure", "ok": impact >= 0, "impact": impact})
    reasons.append(reason)

    impact, reason = _news_score(analysis.get("news_risk"))
    score += impact
    checks.append({"name": "news_risk", "ok": impact >= 0, "impact": impact})
    reasons.append(reason)

    eq = str(analysis.get("entry_quality") or "").upper()
    if eq in ("IDEAL", "GOOD", "OK", "VALID"):
        score += 5
        checks.append({"name": "entry_quality", "ok": True, "impact": 5, "value": eq})
        reasons.append("entry location is acceptable")
    elif eq:
        score -= 3
        checks.append({"name": "entry_quality", "ok": False, "impact": -3, "value": eq})
        reasons.append(f"entry quality={eq.lower()}")

    if _numeric(analysis.get("entry")) is None and _numeric(analysis.get("price")) is None:
        score -= 7
        checks.append({"name": "entry_data", "ok": False, "impact": -7})
        reasons.append("entry/price missing")
    else:
        checks.append({"name": "entry_data", "ok": True, "impact": 0})

    if _numeric(analysis.get("stop_loss")) is None:
        score -= 4
        checks.append({"name": "stop_loss", "ok": False, "impact": -4})
        reasons.append("stop-loss unavailable")
    else:
        checks.append({"name": "stop_loss", "ok": True, "impact": 0})

    score = max(0.0, min(100.0, score))
    decision = "SIGNAL" if score >= _min_score() else "WAIT"
    if decision == "WAIT":
        reasons.append(f"verification score {score:.0f} below threshold {_min_score():.0f}")

    result = {
        "enabled": _env_bool("AGENT_V2_VERIFY", True),
        "decision": decision,
        "score": round(score, 1),
        "threshold": _min_score(),
        "reasons": reasons[:8],
        "checks": checks,
    }
    if not result["enabled"]:
        result["decision"] = "SIGNAL"
        result["reasons"] = ["verification disabled by AGENT_V2_VERIFY"]
    return result


def _fingerprint(symbol: str, analysis: Dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(symbol).upper(),
            _direction(analysis.get("signal")),
            str(analysis.get("entry") or analysis.get("price") or ""),
            str(analysis.get("stop_loss") or ""),
            str(analysis.get("tp1") or ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def init_agent_v2_db() -> None:
    with _DB_LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_signals (
                    signal_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    entry_text TEXT,
                    entry_price REAL,
                    stop_loss REAL,
                    tp1 REAL,
                    tp2 REAL,
                    tp3 REAL,
                    verification_score REAL,
                    verification_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_at TEXT,
                    terminal_outcome TEXT,
                    source TEXT DEFAULT 'agent_v2'
                );
                CREATE TABLE IF NOT EXISTS agent_signal_events (
                    id TEXT PRIMARY KEY,
                    signal_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    price REAL,
                    detail_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_signals_status
                    ON agent_signals(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_agent_signals_symbol
                    ON agent_signals(symbol, created_at);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_signals_active_fp
                    ON agent_signals(fingerprint, status);
                CREATE INDEX IF NOT EXISTS idx_agent_signal_events_signal
                    ON agent_signal_events(signal_id, created_at);
                """
            )
            conn.commit()
        finally:
            conn.close()


def _record_event_locked(
    conn: sqlite3.Connection,
    signal_id: str,
    event_type: str,
    price: Optional[float],
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO agent_signal_events
        (id, signal_id, event_type, price, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            signal_id,
            event_type,
            price,
            json.dumps(detail or {}),
            _now_iso(),
        ),
    )


def _was_event_recorded_locked(
    conn: sqlite3.Connection,
    signal_id: str,
    event_type: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM agent_signal_events
        WHERE signal_id = ? AND event_type = ?
        LIMIT 1
        """,
        (signal_id, event_type),
    ).fetchone()
    return bool(row)


def register_signal(
    symbol: str,
    analysis: Dict[str, Any],
    verification: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Persist a new signal. Returns None when an identical active signal exists."""
    init_agent_v2_db()
    direction = _direction(analysis.get("signal"))
    if direction not in ("BUY", "SELL"):
        return None

    fp = _fingerprint(symbol, analysis)
    now = _now_iso()
    signal_id = "KZ-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()

    entry_price = _numeric(analysis.get("entry"))
    if entry_price is None:
        entry_price = _numeric(analysis.get("price"))

    with _DB_LOCK:
        conn = _connect()
        try:
            existing = conn.execute(
                """
                SELECT signal_id FROM agent_signals
                WHERE fingerprint = ? AND status = 'ACTIVE'
                LIMIT 1
                """,
                (fp,),
            ).fetchone()
            if existing:
                return str(existing["signal_id"])

            conn.execute(
                """
                INSERT INTO agent_signals (
                    signal_id, symbol, direction, fingerprint, status,
                    entry_text, entry_price, stop_loss, tp1, tp2, tp3,
                    verification_score, verification_json,
                    created_at, updated_at, source
                )
                VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'agent_v2')
                """,
                (
                    signal_id,
                    str(symbol),
                    direction,
                    fp,
                    str(analysis.get("entry") or analysis.get("price") or ""),
                    entry_price,
                    _numeric(analysis.get("stop_loss")),
                    _numeric(analysis.get("tp1")),
                    _numeric(analysis.get("tp2")),
                    _numeric(analysis.get("tp3")),
                    float((verification or {}).get("score") or 0),
                    json.dumps(verification or {}),
                    now,
                    now,
                ),
            )
            _record_event_locked(
                conn,
                signal_id,
                "SIGNAL_CREATED",
                entry_price,
                {"symbol": symbol, "direction": direction},
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Another worker/restart may have created the same fingerprint.
            row = conn.execute(
                """
                SELECT signal_id FROM agent_signals
                WHERE fingerprint = ? AND status = 'ACTIVE'
                LIMIT 1
                """,
                (fp,),
            ).fetchone()
            return str(row["signal_id"]) if row else None
        finally:
            conn.close()

    return signal_id


def _targets_crossed(direction: str, price: float, row: sqlite3.Row) -> List[Tuple[str, float]]:
    levels: List[Tuple[str, float]] = []
    for name in ("tp1", "tp2", "tp3"):
        value = row[name]
        if value is None:
            continue
        value = float(value)
        if direction == "BUY" and price >= value:
            levels.append((name.upper() + "_HIT", value))
        if direction == "SELL" and price <= value:
            levels.append((name.upper() + "_HIT", value))
    return levels


def _stop_crossed(direction: str, price: float, row: sqlite3.Row) -> bool:
    if row["stop_loss"] is None:
        return False
    stop = float(row["stop_loss"])
    return price <= stop if direction == "BUY" else price >= stop


def update_signal_lifecycle(
    symbol: str,
    price: Any,
    analysis: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate ACTIVE signals using the latest observed price.

    This is intentionally point-in-time tracking. It does not claim intrabar
    order or fill precision that the available data does not prove.
    """
    if not _env_bool("AGENT_V2_TRACKING", True):
        return []

    current_price = _numeric(price)
    if current_price is None:
        return []

    init_agent_v2_db()
    events: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM agent_signals
                WHERE symbol = ? AND status = 'ACTIVE'
                ORDER BY created_at ASC
                """,
                (str(symbol),),
            ).fetchall()

            for row in rows:
                signal_id = str(row["signal_id"])
                direction = str(row["direction"]).upper()
                created_at = datetime.fromisoformat(str(row["created_at"]))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                stop_hit = _stop_crossed(direction, current_price, row)
                target_hits = _targets_crossed(direction, current_price, row)

                # Expire stale signals before they become misleading.
                if (now - created_at) > timedelta(hours=_max_age_hours()):
                    conn.execute(
                        """
                        UPDATE agent_signals
                        SET status='EXPIRED', terminal_outcome='EXPIRED',
                            closed_at=?, updated_at=?
                        WHERE signal_id=? AND status='ACTIVE'
                        """,
                        (_now_iso(), _now_iso(), signal_id),
                    )
                    _record_event_locked(
                        conn,
                        signal_id,
                        "EXPIRED",
                        current_price,
                        {"max_age_hours": _max_age_hours()},
                    )
                    events.append(
                        {
                            "signal_id": signal_id,
                            "symbol": symbol,
                            "direction": direction,
                            "event": "EXPIRED",
                            "price": current_price,
                        }
                    )
                    continue

                # Record newly crossed TP milestones.
                for event_type, level in target_hits:
                    if _was_event_recorded_locked(conn, signal_id, event_type):
                        continue
                    _record_event_locked(
                        conn,
                        signal_id,
                        event_type,
                        current_price,
                        {"target_level": level, "observed_price": current_price},
                    )
                    events.append(
                        {
                            "signal_id": signal_id,
                            "symbol": symbol,
                            "direction": direction,
                            "event": event_type,
                            "price": current_price,
                            "level": level,
                        }
                    )

                # If TP3 is reached, close as WON. If stop is crossed first,
                # close as LOST. The available point-in-time price cannot prove
                # which happened first when both conditions are simultaneously true.
                tp3_crossed = any(event_type == "TP3_HIT" for event_type, _ in target_hits)
                ambiguous = stop_hit and tp3_crossed
                if ambiguous:
                    terminal = "AMBIGUOUS"
                    status = "REVIEW"
                    if not _was_event_recorded_locked(conn, signal_id, "AMBIGUOUS_PRICE_STATE"):
                        _record_event_locked(
                            conn,
                            signal_id,
                            "AMBIGUOUS_PRICE_STATE",
                            current_price,
                            {"note": "stop and TP3 conditions were both true at one observation"},
                        )
                        events.append(
                            {
                                "signal_id": signal_id,
                                "symbol": symbol,
                                "direction": direction,
                                "event": "AMBIGUOUS",
                                "price": current_price,
                            }
                        )
                    conn.execute(
                        """
                        UPDATE agent_signals
                        SET status=?, terminal_outcome=?, closed_at=?, updated_at=?
                        WHERE signal_id=?
                        """,
                        (status, terminal, _now_iso(), _now_iso(), signal_id),
                    )
                    continue

                if stop_hit:
                    if not _was_event_recorded_locked(conn, signal_id, "STOP_HIT"):
                        _record_event_locked(
                            conn,
                            signal_id,
                            "STOP_HIT",
                            current_price,
                            {"stop_loss": row["stop_loss"]},
                        )
                    conn.execute(
                        """
                        UPDATE agent_signals
                        SET status='LOST', terminal_outcome='STOP_LOSS',
                            closed_at=?, updated_at=?
                        WHERE signal_id=? AND status='ACTIVE'
                        """,
                        (_now_iso(), _now_iso(), signal_id),
                    )
                    events.append(
                        {
                            "signal_id": signal_id,
                            "symbol": symbol,
                            "direction": direction,
                            "event": "STOP_LOSS",
                            "price": current_price,
                            "terminal": True,
                        }
                    )
                    continue

                if tp3_crossed:
                    conn.execute(
                        """
                        UPDATE agent_signals
                        SET status='WON', terminal_outcome='TP3',
                            closed_at=?, updated_at=?
                        WHERE signal_id=? AND status='ACTIVE'
                        """,
                        (_now_iso(), _now_iso(), signal_id),
                    )
                    events.append(
                        {
                            "signal_id": signal_id,
                            "symbol": symbol,
                            "direction": direction,
                            "event": "TP3",
                            "price": current_price,
                            "terminal": True,
                        }
                    )

            conn.commit()
        finally:
            conn.close()

    # Feed terminal outcomes back into the existing learning store.
    for event in events:
        if event.get("event") not in ("STOP_LOSS", "TP3", "EXPIRED"):
            continue
        try:
            from agent_core import tool_learn

            outcome = {
                "STOP_LOSS": "v2_stop_loss",
                "TP3": "v2_tp3",
                "EXPIRED": "v2_expired",
            }.get(str(event.get("event")), "v2_outcome")
            tool_learn(
                user_id="telegram_agent",
                symbol=str(event.get("symbol")),
                signal=str(event.get("direction")),
                confidence="",
                notes=f"signal_id={event.get('signal_id')} lifecycle_outcome={event.get('event')}",
                outcome=outcome,
                meta={"price": event.get("price")},
            )
        except Exception as e:
            logger.debug("Agent V2 learning mirror failed: %s", e)

    return events


def get_active_signals(limit: int = 20) -> List[Dict[str, Any]]:
    init_agent_v2_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM agent_signals
                WHERE status='ACTIVE'
                ORDER BY created_at DESC LIMIT ?
                """,
                (max(1, min(int(limit), 100)),),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def get_agent_performance_summary() -> Dict[str, Any]:
    init_agent_v2_db()
    with _DB_LOCK:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS n
                FROM agent_signals
                GROUP BY status
                """
            ).fetchall()
            counts = {str(r["status"]): int(r["n"]) for r in rows}
            won = counts.get("WON", 0)
            lost = counts.get("LOST", 0)
            closed = won + lost
            return {
                "total": int(sum(counts.values())),
                "active": counts.get("ACTIVE", 0),
                "won": won,
                "lost": lost,
                "expired": counts.get("EXPIRED", 0),
                "review": counts.get("REVIEW", 0),
                "closed": closed,
                "win_rate": round((won / closed) * 100.0, 1) if closed else None,
            }
        finally:
            conn.close()


def format_agent_performance() -> str:
    p = get_agent_performance_summary()
    wr = "—" if p.get("win_rate") is None else f"{p['win_rate']:.1f}%"
    return (
        "📊 <b>AGENT V2 TRACKING</b>\n"
        f"• Tracked: <b>{p['total']}</b>\n"
        f"• Active: <b>{p['active']}</b>\n"
        f"• TP3: <b>{p['won']}</b>\n"
        f"• Stop: <b>{p['lost']}</b>\n"
        f"• Expired: <b>{p['expired']}</b>\n"
        f"• Review: <b>{p['review']}</b>\n"
        f"• Closed win-rate: <b>{wr}</b>"
    )
