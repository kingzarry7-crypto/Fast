"""Multi-market Kitty paper simulator.

Uses the transparent completed-candle technical signal and a separate SQLite ledger.
It never imports or calls the broker/trading connector, and cannot place exchange orders.
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
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger("king_zarry_kitty_multi_paper")
router = APIRouter(prefix="/multi-paper", tags=["Kitty Multi-Market Paper"])
_lock = threading.RLock()
_settings_lock = threading.RLock()
_worker_lock = threading.Lock()
_worker: threading.Thread | None = None
_stop = threading.Event()
_loaded = False
_settings: dict[str, Any] = {
    "enabled": False,
    "symbols": ["BTC/USD", "ETH/USD", "SOL/USD", "XAU/USD", "EUR/USD"],
    "timeframe": "1h",
    "max_order_notional_usd": 25.0,
}
ALLOWED_SYMBOLS = {
    "BTC/USD", "BTC/USDT", "ETH/USD", "ETH/USDT", "SOL/USD", "BNB/USD",
    "XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
}
ALLOWED_TIMEFRAMES = {"15m", "30m", "1h", "2h", "4h", "1d"}
STARTING_CASH = 10_000.0
FEE_RATE = 0.001


def _db_path() -> str:
    explicit = (os.getenv("KITTY_MULTI_PAPER_DB_PATH") or "").strip()
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    candidates = ([os.path.abspath(explicit)] if explicit else [])
    if data_dir:
        candidates.append(os.path.abspath(os.path.join(data_dir, "kitty_multi_paper.db")))
    candidates.extend([
        os.path.abspath("/app/data/kitty_multi_paper.db"),
        os.path.abspath(os.path.join(os.getcwd(), "kitty_multi_paper.db")),
    ])
    for path in dict.fromkeys(candidates):
        parent = os.path.dirname(path) or "."
        try:
            os.makedirs(parent, exist_ok=True)
            if os.access(parent, os.W_OK | os.X_OK):
                return path
        except OSError:
            continue
    raise RuntimeError("Multi-market paper ledger has no writable directory")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS kitty_multi_paper_settings (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    symbols_json TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    max_order_notional_usd REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_multi_paper_account (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    cash REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_multi_paper_positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    avg_entry REAL NOT NULL,
                    mark_price REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kitty_multi_paper_cycles (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    candle_time TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    price REAL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(symbol, timeframe, candle_time)
                );
                CREATE TABLE IF NOT EXISTS kitty_multi_paper_orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    candle_time TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    notional_usd REAL NOT NULL,
                    fee_usd REAL NOT NULL,
                    cash_after REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(symbol, candle_time)
                );
            """)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("INSERT OR IGNORE INTO kitty_multi_paper_account(id,cash,updated_at) VALUES(1,?,?)", (STARTING_CASH, now))
            conn.execute(
                "INSERT OR IGNORE INTO kitty_multi_paper_settings(id,enabled,symbols_json,timeframe,max_order_notional_usd,updated_at) VALUES(1,0,?,?,?,?)",
                (json.dumps(_settings["symbols"]), _settings["timeframe"], _settings["max_order_notional_usd"], now),
            )
            conn.commit()
        finally:
            conn.close()


def _restore_settings() -> None:
    global _loaded
    if _loaded:
        return
    _init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT * FROM kitty_multi_paper_settings WHERE id=1").fetchone()
        finally:
            conn.close()
    if row:
        try:
            symbols = json.loads(row["symbols_json"])
        except Exception:
            symbols = _settings["symbols"]
        with _settings_lock:
            _settings.update({
                "enabled": bool(row["enabled"]),
                "symbols": _normalize_symbols(symbols),
                "timeframe": row["timeframe"] if row["timeframe"] in ALLOWED_TIMEFRAMES else "1h",
                "max_order_notional_usd": float(row["max_order_notional_usd"]),
            })
    _loaded = True


def _normalize_symbols(values: list[str] | tuple[str, ...]) -> list[str]:
    if not isinstance(values, (list, tuple)):
        raise ValueError("symbols must be a list")
    normalized = list(dict.fromkeys(str(value).strip().upper().replace("-", "/") for value in values))
    if not normalized:
        raise ValueError("Choose at least one market")
    unsupported = [symbol for symbol in normalized if symbol not in ALLOWED_SYMBOLS]
    if unsupported:
        raise ValueError("Unsupported market(s): " + ", ".join(unsupported))
    if len(normalized) > len(ALLOWED_SYMBOLS):
        raise ValueError("Too many markets")
    return normalized


def _persist_settings() -> None:
    _init_db()
    with _settings_lock:
        enabled = bool(_settings["enabled"])
        symbols = _normalize_symbols(_settings["symbols"])
        timeframe = str(_settings["timeframe"])
        notional = float(_settings["max_order_notional_usd"])
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO kitty_multi_paper_settings(id,enabled,symbols_json,timeframe,max_order_notional_usd,updated_at)
                   VALUES(1,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled,
                   symbols_json=excluded.symbols_json,timeframe=excluded.timeframe,
                   max_order_notional_usd=excluded.max_order_notional_usd,updated_at=excluded.updated_at""",
                (1 if enabled else 0, json.dumps(symbols), timeframe, notional, now),
            )
            conn.commit()
        finally:
            conn.close()


def _require_user(request: Request) -> None:
    try:
        import api as web_api
        user_row = web_api._require_current_user(request)
        web_api._require_web_vip(user_row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Sign in with a VIP account to control Kitty paper trading") from exc


def _settings_snapshot() -> dict[str, Any]:
    _restore_settings()
    with _settings_lock:
        return {
            "enabled": bool(_settings["enabled"]),
            "symbols": list(_settings["symbols"]),
            "timeframe": str(_settings["timeframe"]),
            "max_order_notional_usd": float(_settings["max_order_notional_usd"]),
        }


def status() -> dict[str, Any]:
    _restore_settings()
    _init_db()
    settings = _settings_snapshot()
    with _lock:
        conn = _connect()
        try:
            account = dict(conn.execute("SELECT * FROM kitty_multi_paper_account WHERE id=1").fetchone())
            positions = [dict(row) for row in conn.execute("SELECT * FROM kitty_multi_paper_positions WHERE ABS(quantity)>1e-12 ORDER BY symbol").fetchall()]
            orders = [dict(row) for row in conn.execute("SELECT * FROM kitty_multi_paper_orders ORDER BY created_at DESC LIMIT 30").fetchall()]
            cycles = conn.execute("SELECT * FROM kitty_multi_paper_cycles ORDER BY created_at DESC LIMIT 20").fetchall()
        finally:
            conn.close()
    marked_value = sum(float(p["quantity"]) * float(p["mark_price"]) for p in positions)
    return {
        **settings,
        "mode": "paper_only",
        "starting_cash_usd": STARTING_CASH,
        "cash_usd": round(float(account["cash"]), 2),
        "open_positions_value_usd": round(marked_value, 2),
        "equity_usd": round(float(account["cash"]) + marked_value, 2),
        "positions": positions,
        "recent_orders": orders,
        "recent_cycles": [{**dict(row), "details": _json_or_empty(row["details_json"])} for row in cycles],
        "live_trading_enabled": False,
        "exchange_connector_used": False,
        "warning": "Simulated trades only. Rule-based signals are experimental and do not establish profitability.",
    }


def _json_or_empty(value: str) -> dict[str, Any]:
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def run_cycle(symbol: str | None = None) -> dict[str, Any]:
    _restore_settings()
    _init_db()
    cfg = _settings_snapshot()
    if not cfg["enabled"]:
        return {"status": "disabled", "mode": "paper_only", "live_trading_enabled": False}
    symbols = [str(symbol).strip().upper().replace("-", "/")] if symbol else cfg["symbols"]
    if any(item not in ALLOWED_SYMBOLS for item in symbols):
        raise ValueError("Unsupported market")
    results = []
    for market_symbol in symbols:
        try:
            from market import get_candles
            from kitty_api import _technical_signal, _validate_candles
            candles = get_candles(market_symbol, timeframe=cfg["timeframe"], outputsize=180)
            _validate_candles(candles, cfg["timeframe"], market_symbol)
            if len(candles) < 56:
                raise ValueError("At least 56 candles are required to exclude the forming candle")
            closed = candles[:-1]
            _validate_candles(closed, cfg["timeframe"], market_symbol)
            signal = _technical_signal(closed, market_symbol, cfg["timeframe"])
            candle_time = str(signal["completed_candle_time"])
            price = float(signal["price"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("Invalid market price")
        except Exception as exc:
            logger.warning("Kitty multi-market paper skipped %s: %s", market_symbol, type(exc).__name__)
            results.append({"symbol": market_symbol, "status": "unavailable", "error": type(exc).__name__ + ": " + str(exc)[:160]})
            continue

        with _lock:
            conn = _connect()
            try:
                prior = conn.execute(
                    "SELECT status,signal FROM kitty_multi_paper_cycles WHERE symbol=? AND timeframe=? AND candle_time=?",
                    (market_symbol, cfg["timeframe"], candle_time),
                ).fetchone()
                if prior:
                    results.append({"symbol": market_symbol, "status": "already_processed", "signal": prior["signal"], "candle_time": candle_time})
                    continue
                account = conn.execute("SELECT cash FROM kitty_multi_paper_account WHERE id=1").fetchone()
                cash = float(account["cash"])
                pos = conn.execute("SELECT quantity,avg_entry FROM kitty_multi_paper_positions WHERE symbol=?", (market_symbol,)).fetchone()
                quantity = float(pos["quantity"]) if pos else 0.0
                avg_entry = float(pos["avg_entry"]) if pos else 0.0
                side = None
                trade_qty = 0.0
                notional = 0.0
                fee = 0.0
                if signal["signal"] == "BUY" and quantity <= 1e-12:
                    notional = min(cfg["max_order_notional_usd"], max(0.0, cash) / (1.0 + FEE_RATE))
                    if notional >= 1.0:
                        trade_qty = notional / price
                        fee = notional * FEE_RATE
                        side = "BUY"
                        cash -= notional + fee
                        quantity = trade_qty
                        avg_entry = price
                elif signal["signal"] == "SELL" and quantity > 1e-12:
                    side = "SELL"
                    trade_qty = quantity
                    notional = trade_qty * price
                    fee = notional * FEE_RATE
                    cash += notional - fee
                    quantity = 0.0
                    avg_entry = 0.0
                now = datetime.now(timezone.utc).isoformat()
                cycle_status = "simulated_order" if side else "no_action"
                details = {
                    "signal": signal,
                    "execution": "isolated SQLite paper ledger; no exchange calls",
                    "fee_rate": FEE_RATE,
                    "cash_after": round(cash, 6),
                }
                conn.execute(
                    "INSERT INTO kitty_multi_paper_cycles(id,symbol,candle_time,timeframe,signal,status,price,details_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), market_symbol, candle_time, cfg["timeframe"], signal["signal"], cycle_status, price, json.dumps(details, allow_nan=False), now),
                )
                if side:
                    conn.execute(
                        "INSERT INTO kitty_multi_paper_orders(id,symbol,candle_time,side,quantity,price,notional_usd,fee_usd,cash_after,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), market_symbol, candle_time, side, trade_qty, price, notional, fee, cash, now),
                    )
                conn.execute(
                    """INSERT INTO kitty_multi_paper_positions(symbol,quantity,avg_entry,mark_price,updated_at)
                       VALUES(?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET quantity=excluded.quantity,
                       avg_entry=excluded.avg_entry,mark_price=excluded.mark_price,updated_at=excluded.updated_at""",
                    (market_symbol, quantity, avg_entry, price, now),
                )
                conn.execute("UPDATE kitty_multi_paper_account SET cash=?,updated_at=? WHERE id=1", (cash, now))
                conn.commit()
                results.append({
                    "symbol": market_symbol, "status": cycle_status, "signal": signal["signal"],
                    "side": side, "quantity": round(trade_qty, 10), "price": price,
                    "notional_usd": round(notional, 2), "fee_usd": round(fee, 4),
                    "candle_time": candle_time, "cash_after": round(cash, 2),
                })
            except sqlite3.IntegrityError:
                conn.rollback()
                results.append({"symbol": market_symbol, "status": "already_processed"})
            finally:
                conn.close()
    return {
        "status": "completed" if any(row["status"] != "unavailable" for row in results) else "unavailable",
        "mode": "paper_only", "results": results,
        "live_trading_enabled": False, "exchange_connector_used": False,
    }


def _worker_loop() -> None:
    interval = max(60, min(int(os.getenv("KITTY_MULTI_PAPER_POLL_SECONDS", "900")), 3600))
    while not _stop.is_set():
        try:
            run_cycle()
        except Exception:
            logger.exception("Kitty multi-market paper worker failed")
        _stop.wait(interval)


def start_worker() -> bool:
    global _worker
    with _worker_lock:
        if _worker and _worker.is_alive():
            return False
        _stop.clear()
        _worker = threading.Thread(target=_worker_loop, name="kitty-multi-paper", daemon=True)
        _worker.start()
        logger.info("Kitty multi-market paper worker started")
        return True


def stop_worker() -> None:
    _stop.set()


class MultiPaperSettingsRequest(BaseModel):
    enabled: bool = False
    symbols: list[str] = Field(default_factory=lambda: ["BTC/USD", "XAU/USD", "ETH/USD"])
    timeframe: str = "1h"
    max_order_notional_usd: float = Field(default=25.0, gt=0, le=250)


@router.get("/status")
def get_status():
    return status()


@router.get("/settings")
def get_settings(request: Request):
    _require_user(request)
    return {"status": "success", **_settings_snapshot(), "mode": "paper_only", "live_trading_enabled": False}


@router.put("/settings")
def update_settings(request: Request, body: MultiPaperSettingsRequest):
    _require_user(request)
    _restore_settings()
    if body.timeframe not in ALLOWED_TIMEFRAMES:
        raise HTTPException(status_code=422, detail="Unsupported timeframe")
    try:
        symbols = _normalize_symbols(body.symbols)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not math.isfinite(body.max_order_notional_usd):
        raise HTTPException(status_code=422, detail="Order limit must be finite")
    with _settings_lock:
        _settings.update({
            "enabled": bool(body.enabled),
            "symbols": symbols,
            "timeframe": body.timeframe,
            "max_order_notional_usd": float(body.max_order_notional_usd),
        })
    _persist_settings()
    if body.enabled:
        start_worker()
        initial_cycle = run_cycle()
    else:
        stop_worker()
        initial_cycle = None
    return {
        "status": "success", **status(), "initial_cycle": initial_cycle,
        "message": "Multi-market paper simulator " + ("enabled" if body.enabled else "paused") + ". No exchange orders can be sent.",
    }


@router.post("/cycle")
def manual_cycle(request: Request):
    _require_user(request)
    try:
        return run_cycle()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Kitty multi-market paper cycle failed")
        raise HTTPException(status_code=503, detail="Paper cycle failed: " + type(exc).__name__) from exc


@router.on_event("startup")
def initialize_worker() -> None:
    _restore_settings()
    if _settings_snapshot()["enabled"]:
        start_worker()
