"""Kitty V3 Binance Spot Demo trader. Never submits live-market orders.

This opt-in worker evaluates completed daily BTC candles, one time per candle.
The packaged Kitty model is experimental and its training symbol is unconfirmed.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("king_zarry_kitty_demo")
router = APIRouter(prefix="/demo-trading", tags=["Kitty Binance Demo Trading"])
_lock = threading.RLock()
_worker_lock = threading.Lock()
_worker: threading.Thread | None = None
_stop = threading.Event()
_settings_lock = threading.RLock()
_settings: dict[str, Any] = {"enabled": False, "order_btc": 0.0001, "max_notional_usd": 25.0}
_settings_loaded = False
SYMBOL = "BTC/USD"
TIMEFRAME = "1h"


def _db_path() -> str:
    candidates = []
    explicit = (os.getenv("KITTY_DEMO_DB_PATH") or "").strip()
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if explicit:
        candidates.append(os.path.abspath(explicit))
    if data_dir:
        candidates.append(os.path.abspath(os.path.join(data_dir, "kitty_demo_trader.db")))
    candidates.extend([
        os.path.abspath("/app/data/kitty_demo_trader.db"),
        os.path.abspath(os.path.join(os.getcwd(), "kitty_demo_trader.db")),
    ])
    for path in dict.fromkeys(candidates):
        parent = os.path.dirname(path) or "."
        try:
            os.makedirs(parent, exist_ok=True)
            if os.access(parent, os.W_OK | os.X_OK):
                return path
        except OSError:
            continue
    raise RuntimeError("Kitty demo trading has no writable database directory")


def _connect():
    conn = sqlite3.connect(_db_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS kitty_demo_cycles (
                    candle_time TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    signal TEXT,
                    probability REAL,
                    side TEXT,
                    quantity REAL,
                    price REAL,
                    order_id TEXT,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_demo_position (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    quantity REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO kitty_demo_position(id,quantity,updated_at) VALUES(1,0,'');
                CREATE TABLE IF NOT EXISTS kitty_demo_settings (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    order_btc REAL NOT NULL DEFAULT 0.0001,
                    max_notional_usd REAL NOT NULL DEFAULT 25.0,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.commit()
        finally:
            conn.close()


def _persist_settings() -> None:
    """Persist the opt-in setting so a process restart does not silently disable Kitty."""
    _init_db()
    with _settings_lock:
        values = (
            1 if bool(_settings["enabled"]) else 0,
            float(_settings["order_btc"]),
            float(_settings["max_notional_usd"]),
            datetime.now(timezone.utc).isoformat(),
        )
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO kitty_demo_settings(id,enabled,order_btc,max_notional_usd,updated_at)
                   VALUES(1,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled,
                   order_btc=excluded.order_btc,max_notional_usd=excluded.max_notional_usd,
                   updated_at=excluded.updated_at""",
                values,
            )
            conn.commit()
        finally:
            conn.close()


def _restore_settings() -> None:
    """Load persisted settings once per process; keep safe defaults if none exist."""
    global _settings_loaded
    if _settings_loaded:
        return
    _init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT enabled,order_btc,max_notional_usd FROM kitty_demo_settings WHERE id=1"
            ).fetchone()
        finally:
            conn.close()
    if row:
        with _settings_lock:
            _settings.update({
                "enabled": bool(row["enabled"]),
                "order_btc": float(row["order_btc"]),
                "max_notional_usd": float(row["max_notional_usd"]),
            })
    _settings_loaded = True


def initialize_worker() -> None:
    """Restore the opt-in state on API startup and resume only in safe demo mode."""
    _restore_settings()
    with _settings_lock:
        enabled = bool(_settings["enabled"])
    if enabled and _trading_status()["ready"]:
        start_worker()
        logger.info("Kitty Binance Spot Demo worker restored from persisted settings")
    elif enabled:
        logger.warning("Kitty demo setting is enabled but startup checks are not ready; worker remains stopped")


def _require_user(request: Request) -> None:
    try:
        import api as web_api
        user_row = web_api._require_current_user(request)
        web_api._require_web_vip(user_row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Sign in with a VIP account to control Kitty demo trading") from exc


def _trading_status() -> dict:
    import trading_connector
    cfg = trading_connector.status()
    key, secret = trading_connector._binance_credentials()
    ready = (
        cfg.get("mode") == "demo"
        and (os.getenv("TRADING_PROVIDER") or "auto").strip().lower() in {"auto", "binance"}
        and not cfg.get("kill_switch", True)
        and bool(key and secret)
        and (os.getenv("BINANCE_API_URL") or "https://demo-api.binance.com").rstrip("/") in {
            "https://demo-api.binance.com", "https://demo-api.binance.com/api"
        }
    )
    return {
        "mode": "binance_spot_demo_only",
        "ready": ready,
        "enabled": bool(_settings["enabled"]),
        "order_btc": float(_settings["order_btc"]),
        "max_notional_usd": float(_settings["max_notional_usd"]),
        "poll_seconds": max(60, min(int(os.getenv("KITTY_DEMO_POLL_SECONDS", "900")), 3600)),
        "model_training_symbol_confirmed": False,
        "warning": "Experimental model; training symbol is unconfirmed. Demo funds only. Live trading is not supported by this worker.",
        "requirements": {
            "TRADING_MODE_demo": cfg.get("mode") == "demo",
            "BINANCE_DEMO_CREDENTIALS_present": bool(key and secret),
            "kill_switch_off": not cfg.get("kill_switch", True),
            "TRADING_ENABLED_global_not_required": True,
        },
    }


def status() -> dict:
    _restore_settings()
    _init_db()
    cfg = _trading_status()
    with _lock:
        conn = _connect()
        try:
            position = conn.execute("SELECT quantity,updated_at FROM kitty_demo_position WHERE id=1").fetchone()
            cycles = conn.execute("SELECT * FROM kitty_demo_cycles ORDER BY created_at DESC LIMIT 10").fetchall()
        finally:
            conn.close()
    return {
        **cfg,
        "position_btc": float(position["quantity"]) if position else 0.0,
        "recent_cycles": [
            {**dict(row), "details": _json_or_empty(row["details_json"])}
            for row in cycles
        ],
    }


def _json_or_empty(value: str) -> dict:
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def run_cycle() -> dict:
    """Evaluate an hourly candle; research-only model outputs never authorize demo orders."""
    _restore_settings()
    with _settings_lock:
        enabled = bool(_settings["enabled"])
        order_btc = float(_settings["order_btc"])
        max_notional = float(_settings["max_notional_usd"])
    if not enabled:
        return {"status": "disabled", "mode": "binance_spot_demo_only"}
    cfg = _trading_status()
    if not cfg["ready"]:
        return {"status": "blocked", "reason": "Binance Spot Demo is not ready; check mode, demo credentials and kill switch", "mode": cfg["mode"]}
    try:
        from market import get_candles
        import kitty_v3_retrained as kitty_v3
        from kitty_api import _kitty_features

        candles = get_candles(SYMBOL, timeframe=TIMEFRAME, outputsize=160)
        if not isinstance(candles, list) or len(candles) < 56:
            raise ValueError("Market provider returned fewer than 56 hourly candles")
        closed = candles[:-1]
        candle = closed[-1]
        candle_time = str(candle.get("datetime") or candle.get("time") or "")
        if not candle_time:
            raise ValueError("Latest completed candle has no timestamp")
        features = _kitty_features(closed)
        prediction = kitty_v3.predict_features(features)
        if prediction.get("research_only", True) or not prediction.get("trading_enabled", False):
            return {"status": "blocked", "reason": "Kitty is research-only; validation is required before demo orders are allowed", "mode": "binance_spot_demo_only", "trading_enabled": False}
        probability = float(prediction["confidence"])
        signal = str(prediction["signal"])
        price = float(closed[-1]["close"])
        if not (math.isfinite(price) and price > 0 and math.isfinite(probability) and 0 <= probability <= 1):
            raise ValueError("Model or market returned invalid values")
    except Exception as exc:
        logger.warning("Kitty demo cycle skipped: %s", type(exc).__name__)
        return {"status": "skipped", "reason": f"{type(exc).__name__}: {str(exc)[:180]}", "mode": "binance_spot_demo_only"}

    _init_db()
    with _lock:
        conn = _connect()
        try:
            prior = conn.execute("SELECT status,side,order_id FROM kitty_demo_cycles WHERE candle_time=?", (candle_time,)).fetchone()
            if prior:
                return {"status": "already_processed", "candle_time": candle_time, "previous_status": prior["status"], "mode": "binance_spot_demo_only"}
            row = conn.execute("SELECT quantity FROM kitty_demo_position WHERE id=1").fetchone()
            position = float(row["quantity"])
            side = None
            quantity = 0.0
            if signal == "LONG" and position <= 0 and order_btc * price <= max_notional:
                side, quantity = "BUY", order_btc
            elif signal == "SHORT" and position > 0:
                side, quantity = "SELL", position
            now = datetime.now(timezone.utc).isoformat()
            # Reserve the candle before calling the exchange to prevent concurrent duplicate orders.
            conn.execute(
                "INSERT INTO kitty_demo_cycles(candle_time,status,signal,probability,side,quantity,price,details_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (candle_time, "pending" if side else "no_action", signal, probability, side, quantity, price,
                 json.dumps({"features": features, "warning": prediction.get("warning")}, allow_nan=False), now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return {"status": "already_processed", "candle_time": candle_time, "mode": "binance_spot_demo_only"}
        finally:
            conn.close()

    if not side:
        return {"status": "no_action", "candle_time": candle_time, "signal": signal, "confidence": probability, "mode": "binance_spot_demo_only"}

    try:
        import trading_connector
        result = trading_connector.place_kitty_demo_order(SYMBOL, side, quantity, price, max_notional)
        new_position = position + quantity if side == "BUY" else max(0.0, position - quantity)
        with _lock:
            conn = _connect()
            try:
                conn.execute("UPDATE kitty_demo_cycles SET status=?,order_id=?,details_json=? WHERE candle_time=?",
                             (str(result.get("status") or "accepted"), str(result.get("order_id") or ""),
                              json.dumps({"broker_result": result, "warning": prediction.get("warning")}, allow_nan=False), candle_time))
                conn.execute("UPDATE kitty_demo_position SET quantity=?,updated_at=? WHERE id=1", (new_position, now))
                conn.commit()
            finally:
                conn.close()
        return {"status": "demo_order_submitted", "mode": "binance_spot_demo_only", "symbol": SYMBOL,
                "side": side, "quantity": quantity, "reference_price": price, "order_id": result.get("order_id"),
                "signal": signal, "probability_next_close_up": probability, "warning": prediction.get("warning")}
    except Exception as exc:
        logger.exception("Kitty Binance demo order failed")
        with _lock:
            conn = _connect()
            try:
                conn.execute("UPDATE kitty_demo_cycles SET status='error',details_json=? WHERE candle_time=?",
                             (json.dumps({"error": type(exc).__name__ + ": " + str(exc)[:180]}), candle_time))
                conn.commit()
            finally:
                conn.close()
        return {"status": "order_failed", "mode": "binance_spot_demo_only", "reason": type(exc).__name__ + ": " + str(exc)[:180]}


def _worker_loop() -> None:
    interval = max(60, min(int(os.getenv("KITTY_DEMO_POLL_SECONDS", "900")), 3600))
    while not _stop.is_set():
        try:
            run_cycle()
        except Exception:
            logger.exception("Kitty demo worker cycle failed")
        _stop.wait(interval)


def start_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker and _worker.is_alive():
            return
        _stop.clear()
        _worker = threading.Thread(target=_worker_loop, name="kitty-binance-demo", daemon=True)
        _worker.start()


def stop_worker() -> None:
    _stop.set()


class DemoSettingsRequest(BaseModel):
    enabled: bool
    order_btc: float = Field(default=0.0001, gt=0, le=0.001)
    max_notional_usd: float = Field(default=25.0, gt=0, le=25.0)
    acknowledge_experimental_model: bool = False


@router.get("/settings")
def get_settings(request: Request):
    _require_user(request)
    return {"status": "success", **status()}


@router.put("/settings")
def update_settings(request: Request, body: DemoSettingsRequest):
    _require_user(request)
    _restore_settings()
    if body.enabled and not body.acknowledge_experimental_model:
        raise HTTPException(status_code=422, detail="Acknowledge that Kitty is experimental and its training symbol is unconfirmed.")
    if body.enabled and not _trading_status()["ready"]:
        raise HTTPException(status_code=409, detail="Binance Spot Demo is not ready. Verify TRADING_MODE=demo, Binance Spot Demo API keys and AGENT_TRADING_KILL_SWITCH=false. Live trading remains disabled.")
    with _settings_lock:
        _settings.update({"enabled": body.enabled, "order_btc": body.order_btc, "max_notional_usd": body.max_notional_usd})
    _persist_settings()
    if body.enabled:
        start_worker()
        initial_cycle = run_cycle()
    else:
        initial_cycle = None
        stop_worker()
    return {"status": "success", **status(), "initial_cycle": initial_cycle,
            "message": "Kitty Binance Spot Demo trading " + ("enabled" if body.enabled else "disabled") + ". No live orders are permitted."}


@router.post("/cycle")
def manual_cycle(request: Request):
    _require_user(request)
    result = run_cycle()
    return result
