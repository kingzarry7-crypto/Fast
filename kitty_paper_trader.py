"""Kitty V3 BTC/USD paper trader.

This is an isolated research simulator: it NEVER calls the broker/trading connector.
It evaluates only completed daily candles, processes each candle once, and maintains
its own SQLite cash/position/order ledger. The model is experimental; paper results
are not evidence of profitability and never authorize live trading.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("king_zarry_kitty_paper")
router = APIRouter(prefix="/paper", tags=["Kitty Paper Trading"])
_lock = threading.RLock()
_worker_lock = threading.Lock()
_worker: threading.Thread | None = None
STOP_EVENT = threading.Event()
_runtime_lock = threading.RLock()
_runtime_settings: dict[str, Any] = {"enabled": None, "order_btc": None, "max_notional_usd": None}

SYMBOL = "BTC/USD"
TIMEFRAME = "1h"
DEFAULT_STARTING_CASH = 10_000.0
DEFAULT_QUANTITY = 0.001
DEFAULT_MAX_NOTIONAL = 100.0


def _enabled() -> bool:
    with _runtime_lock:
        override = _runtime_settings["enabled"]
    if override is not None:
        return bool(override)
    return (os.getenv("KITTY_PAPER_TRADING_ENABLED", "true").strip().lower()
            not in {"0", "false", "no", "off"})


def _db_path() -> str:
    """Choose a writable SQLite location, falling back when a configured mount is unavailable."""
    configured = (os.getenv("KITTY_PAPER_DB_PATH") or "").strip()
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    candidates: list[str] = []
    if configured:
        candidates.append(os.path.abspath(configured))
    if data_dir:
        candidates.append(os.path.abspath(os.path.join(data_dir, "kitty_paper_trading.db")))
    # The Railway image creates this directory and grants it to the unprivileged app user.
    candidates.append(os.path.abspath("/app/data/kitty_paper_trading.db"))
    candidates.append(os.path.abspath(os.path.join(os.getcwd(), "kitty_paper_trading.db")))

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        parent = os.path.dirname(candidate) or "."
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as exc:
            logger.debug("Kitty DB candidate unavailable (%s): %s", parent, type(exc).__name__)
            continue
        if os.access(parent, os.W_OK | os.X_OK):
            return candidate
        logger.debug("Kitty DB candidate is not writable: %s", parent)
    raise RuntimeError("Kitty paper database has no writable storage directory")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS kitty_paper_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cash REAL NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    avg_entry REAL NOT NULL DEFAULT 0,
                    last_candle TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_paper_orders (
                    id TEXT PRIMARY KEY,
                    candle_time TEXT NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    notional REAL NOT NULL,
                    probability REAL NOT NULL,
                    signal TEXT NOT NULL,
                    cash_after REAL NOT NULL,
                    position_after REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_paper_cycles (
                    id TEXT PRIMARY KEY,
                    candle_time TEXT NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    signal TEXT,
                    probability REAL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_signal_feedback (
                    id TEXT PRIMARY KEY,
                    candle_time TEXT NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    forward_return REAL,
                    actual_label TEXT,
                    correct INTEGER,
                    settled_at TEXT,
                    created_at TEXT NOT NULL
                );

            """)
            conn.execute(
                "INSERT OR IGNORE INTO kitty_paper_state(id,cash,quantity,avg_entry,updated_at) VALUES(1,?,?,?,?)",
                (DEFAULT_STARTING_CASH, 0.0, 0.0, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def status() -> dict[str, Any]:
    _init_db()
    with _lock:
        conn = _connect()
        try:
            state = dict(conn.execute("SELECT * FROM kitty_paper_state WHERE id=1").fetchone())
            orders = conn.execute(
                "SELECT * FROM kitty_paper_orders ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            cycles = conn.execute(
                "SELECT * FROM kitty_paper_cycles ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        finally:
            conn.close()
    return {
        "enabled": _enabled(),
        "mode": "paper_only",
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "model": "Kitty V3 retrained (hourly BTC research model)",
        "live_trading_enabled": False,
        "broker_connector_used": False,
        "starting_cash_usd": DEFAULT_STARTING_CASH,
        "max_order_notional_usd": _max_notional(),
        "default_order_quantity_btc": _quantity(),
        "poll_seconds": max(60, min(int(_float_env("KITTY_PAPER_POLL_SECONDS", 900)), 3600)),
        "runtime_controls": True,
        "settings_persistence": "current backend process only; resets on restart unless environment defaults are changed",
        "state": state,
        "recent_orders": [dict(row) for row in orders],
        "recent_cycles": [
            {**dict(row), "details": _json_or_empty(row["details_json"])}
            for row in cycles
        ],
        "signal_feedback": feedback_summary(),
        "warning": "Research simulation only. No live orders are possible from this module; results do not establish profitability.",
    }


def _json_or_empty(value: str) -> dict[str, Any]:
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def _quantity() -> float:
    with _runtime_lock:
        override = _runtime_settings["order_btc"]
    value = float(override) if override is not None else _float_env("KITTY_PAPER_ORDER_BTC", DEFAULT_QUANTITY)
    if value <= 0 or not math.isfinite(value):
        return DEFAULT_QUANTITY
    return min(value, 0.01)


def _max_notional() -> float:
    with _runtime_lock:
        override = _runtime_settings["max_notional_usd"]
    value = float(override) if override is not None else _float_env("KITTY_PAPER_MAX_NOTIONAL_USD", DEFAULT_MAX_NOTIONAL)
    if value <= 0 or not math.isfinite(value):
        return DEFAULT_MAX_NOTIONAL
    return min(value, 500.0)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _features(candles: list[dict[str, Any]]) -> dict[str, float]:
    """Use the retrained model's exact 18-feature input contract."""
    from kitty_api import _kitty_features
    return _kitty_features(candles)


def _parse_candle_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _settle_signal_feedback(conn: sqlite3.Connection, candles: list[dict[str, Any]]) -> int:
    """Settle saved predictions only when both the next-open entry and exit candles exist."""
    by_time: dict[datetime, dict[str, Any]] = {}
    for candle in candles:
        stamp = candle.get("datetime") or candle.get("time")
        if not stamp:
            continue
        try:
            by_time[_parse_candle_time(str(stamp))] = candle
        except (TypeError, ValueError, OverflowError):
            continue
    pending = conn.execute(
        "SELECT * FROM kitty_signal_feedback WHERE settled_at IS NULL"
    ).fetchall()
    settled = 0
    threshold = max(0.0005, min(_float_env("KITTY_FEEDBACK_LABEL_THRESHOLD", 0.003), 0.02))
    for row in pending:
        try:
            entry = by_time.get(_parse_candle_time(row["entry_time"]))
            exit_candle = by_time.get(_parse_candle_time(row["exit_time"]))
            if not entry or not exit_candle:
                continue
            entry_price = float(entry["open"])
            exit_price = float(exit_candle["close"])
            if not (math.isfinite(entry_price) and entry_price > 0 and
                    math.isfinite(exit_price) and exit_price > 0):
                continue
            forward_return = exit_price / entry_price - 1.0
            actual = "SHORT" if forward_return <= -threshold else (
                "LONG" if forward_return >= threshold else "NO TRADE"
            )
            conn.execute(
                """UPDATE kitty_signal_feedback SET entry_price=?,exit_price=?,
                   forward_return=?,actual_label=?,correct=?,settled_at=? WHERE id=?""",
                (entry_price, exit_price, forward_return, actual,
                 int(row["signal"] == actual), _now(), row["id"]),
            )
            settled += 1
        except (TypeError, ValueError, KeyError, OverflowError):
            logger.warning("Skipping malformed Kitty feedback row %s", row["id"])
    return settled


def feedback_summary() -> dict[str, Any]:
    _init_db()
    with _lock:
        conn = _connect()
        try:
            totals = conn.execute(
                """SELECT COUNT(*) AS total,
                   SUM(CASE WHEN settled_at IS NOT NULL THEN 1 ELSE 0 END) AS settled,
                   SUM(CASE WHEN settled_at IS NULL THEN 1 ELSE 0 END) AS pending,
                   SUM(CASE WHEN settled_at IS NOT NULL AND correct=1 THEN 1 ELSE 0 END) AS correct
                   FROM kitty_signal_feedback"""
            ).fetchone()
            by_signal = conn.execute(
                """SELECT signal, COUNT(*) AS settled,
                   AVG(CASE WHEN correct=1 THEN 1.0 ELSE 0.0 END) AS accuracy,
                   AVG(forward_return) AS mean_forward_return
                   FROM kitty_signal_feedback WHERE settled_at IS NOT NULL
                   GROUP BY signal ORDER BY signal"""
            ).fetchall()
        finally:
            conn.close()
    settled = int(totals["settled"] or 0)
    correct = int(totals["correct"] or 0)
    return {
        "recorded_predictions": int(totals["total"] or 0),
        "settled_predictions": settled,
        "pending_predictions": int(totals["pending"] or 0),
        "direction_label_accuracy": (correct / settled) if settled else None,
        "by_signal": [dict(row) for row in by_signal],
        "automatic_model_updates": False,
        "note": "Outcomes are recorded for evaluation. They do not alter model weights or promote checkpoints automatically.",
    }


def run_cycle() -> dict[str, Any]:
    """Evaluate the latest completed hourly candle; record once; simulate only."""
    if not _enabled():
        return {"status": "disabled", "mode": "paper_only", "live_trading_enabled": False}
    _init_db()
    try:
        from market import get_candles
        import kitty_v3_retrained as kitty_v3

        # Treat the newest candle as potentially still forming; use the prior candle.
        candles = get_candles(SYMBOL, timeframe=TIMEFRAME, outputsize=160)
        if not isinstance(candles, list) or len(candles) < 56:
            raise ValueError("Market provider returned fewer than 56 hourly candles")
        closed_candles = candles[:-1]
        candle = closed_candles[-1]
        candle_time = str(candle.get("datetime") or candle.get("time") or "")
        if not candle_time:
            raise ValueError("Latest completed candle has no timestamp")
        features = _features(closed_candles)
        prediction = kitty_v3.predict_features(features)
        probability = float(prediction["confidence"])
        signal = str(prediction["signal"])
        price = float(candle["close"])
        if not (math.isfinite(price) and price > 0 and math.isfinite(probability) and 0 <= probability <= 1):
            raise ValueError("Model or market returned invalid values")
    except Exception as exc:
        logger.warning("Kitty paper cycle skipped: %s", type(exc).__name__)
        return {
            "status": "skipped",
            "reason": f"{type(exc).__name__}: {str(exc)[:200]}",
            "mode": "paper_only",
            "live_trading_enabled": False,
        }

    with _lock:
        conn = _connect()
        try:
            # Settle earlier predictions from completed candles before evaluating the new one.
            settled_feedback = _settle_signal_feedback(conn, closed_candles)
            if settled_feedback:
                conn.commit()
            prior = conn.execute(
                "SELECT status, signal FROM kitty_paper_cycles WHERE candle_time=?",
                (candle_time,),
            ).fetchone()
            if prior:
                return {"status": "already_processed", "candle_time": candle_time,
                        "signal": prior["signal"], "mode": "paper_only",
                        "live_trading_enabled": False}
            state = conn.execute("SELECT * FROM kitty_paper_state WHERE id=1").fetchone()
            cash = float(state["cash"])
            position = float(state["quantity"])
            avg_entry = float(state["avg_entry"])
            side = None
            quantity = 0.0
            notional = 0.0

            # Long-only spot-style paper portfolio. BUY opens one capped position;
            # SELL_BIAS exits it. HOLD does nothing; no leverage or shorting.
            order_qty = _quantity()
            if signal == "LONG" and position <= 0 and order_qty * price <= _max_notional() and cash >= order_qty * price:
                side, quantity, notional = "BUY", order_qty, order_qty * price
                cash -= notional
                avg_entry = price
                position += quantity
            elif signal == "SHORT" and position > 0:
                quantity = position
                side, notional = "SELL", position * price
                cash += notional
                position = 0.0
                avg_entry = 0.0

            now = _now()
            details = {
                "price": price, "features": features,
                "thresholds": prediction.get("thresholds"),
                "warning": prediction.get("warning"),
                "execution": "internal SQLite simulator only",
            }
            conn.execute(
                "INSERT INTO kitty_paper_cycles(id,candle_time,symbol,status,signal,probability,details_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), candle_time, SYMBOL,
                 "simulated_order" if side else "no_action", signal, probability,
                 json.dumps(details, allow_nan=False), now),
            )
            signal_time = _parse_candle_time(candle_time)
            conn.execute(
                """INSERT INTO kitty_signal_feedback(
                   id,candle_time,symbol,signal,confidence,entry_time,exit_time,created_at
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), candle_time, SYMBOL, signal, probability,
                 (signal_time + timedelta(hours=1)).isoformat(),
                 (signal_time + timedelta(hours=6)).isoformat(), now),
            )
            if side:
                conn.execute(
                    "INSERT INTO kitty_paper_orders(id,candle_time,symbol,side,quantity,price,notional,probability,signal,cash_after,position_after,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), candle_time, SYMBOL, side, quantity, price,
                     notional, probability, signal, cash, position, now),
                )
            conn.execute(
                "UPDATE kitty_paper_state SET cash=?,quantity=?,avg_entry=?,last_candle=?,updated_at=? WHERE id=1",
                (cash, position, avg_entry, candle_time, now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return {"status": "already_processed", "candle_time": candle_time,
                    "mode": "paper_only", "live_trading_enabled": False}
        finally:
            conn.close()
    return {
        "status": "simulated_order" if side else "no_action",
        "mode": "paper_only", "symbol": SYMBOL, "candle_time": candle_time,
        "signal": signal, "confidence": probability,
        "simulated_side": side, "simulated_quantity_btc": quantity,
        "price": price, "notional_usd": notional,
        "live_trading_enabled": False,
        "warning": "Experimental research simulation; no broker order was sent.",
    }


def _worker_loop() -> None:
    interval = max(60, min(int(_float_env("KITTY_PAPER_POLL_SECONDS", 900)), 3600))
    while not STOP_EVENT.is_set():
        try:
            run_cycle()
        except Exception:
            logger.exception("Kitty paper worker cycle failed")
        STOP_EVENT.wait(interval)


def start_worker() -> bool:
    """Start one process-local paper-only worker; no credentials are read."""
    global _worker
    with _worker_lock:
        if _worker and _worker.is_alive():
            return False
        STOP_EVENT.clear()
        _worker = threading.Thread(target=_worker_loop, name="kitty-paper-trader", daemon=True)
        _worker.start()
        logger.info("Kitty BTC/USD paper worker started; enabled=%s; broker orders remain disabled", _enabled())
        return True


def stop_worker() -> None:
    STOP_EVENT.set()


class KittyPaperSettingsRequest(BaseModel):
    enabled: bool
    order_btc: float = Field(default=0.001, gt=0, le=0.01)
    max_notional_usd: float = Field(default=100.0, gt=0, le=500)


def _require_settings_user(request: Request) -> None:
    # Reuse the app's established session and VIP checks. This controls the
    # global paper simulator only; it does not arm broker/demo/live orders.
    try:
        import api as web_api
        user_row = web_api._require_current_user(request)
        web_api._require_web_vip(user_row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Sign in with a VIP account to control Kitty paper settings") from exc


@router.get("/settings")
def get_paper_settings(request: Request):
    _require_settings_user(request)
    return {
        "status": "success",
        "enabled": _enabled(),
        "mode": "paper_only",
        "order_btc": _quantity(),
        "max_notional_usd": _max_notional(),
        "poll_seconds": max(60, min(int(_float_env("KITTY_PAPER_POLL_SECONDS", 900)), 3600)),
        "broker_orders_enabled": False,
        "settings_persistence": "current backend process only; resets on restart unless environment defaults are changed",
    }


@router.put("/settings")
def update_paper_settings(request: Request, body: KittyPaperSettingsRequest):
    _require_settings_user(request)
    if not math.isfinite(body.order_btc) or not math.isfinite(body.max_notional_usd):
        raise HTTPException(status_code=422, detail="Tuning values must be finite numbers")
    with _runtime_lock:
        _runtime_settings["enabled"] = body.enabled
        _runtime_settings["order_btc"] = body.order_btc
        _runtime_settings["max_notional_usd"] = body.max_notional_usd
    initial_cycle = None
    if body.enabled:
        start_worker()
        initial_cycle = run_cycle()
    return {
        "status": "success",
        "enabled": _enabled(),
        "mode": "paper_only",
        "order_btc": _quantity(),
        "max_notional_usd": _max_notional(),
        "broker_orders_enabled": False,
        "initial_cycle": initial_cycle,
        "message": "Kitty paper settings updated. This does not submit Binance demo or live orders.",
    }


@router.get("/status")
def paper_status():
    return status()


@router.get("/feedback")
def paper_feedback():
    return feedback_summary()


@router.post("/cycle")
def paper_cycle():
    try:
        return run_cycle()
    except Exception as exc:
        logger.exception("Kitty paper cycle failed")
        raise HTTPException(status_code=503, detail="Paper cycle failed: " + type(exc).__name__)


@router.on_event("startup")
def _start_paper_worker_on_api_startup() -> None:
    # FastAPI starts this only when the router is mounted; opt-out is explicit.
    # The worker only writes to the isolated paper ledger and never submits broker orders.
    start_worker()
