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

from fastapi import APIRouter, HTTPException, Query, Request
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
                    updated_at TEXT NOT NULL,
                    stop_loss REAL,
                    take_profit REAL
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
            # Add risk columns to existing paper ledgers without deleting positions.
            position_columns = {row["name"] for row in conn.execute("PRAGMA table_info(kitty_multi_paper_positions)").fetchall()}
            if "stop_loss" not in position_columns:
                conn.execute("ALTER TABLE kitty_multi_paper_positions ADD COLUMN stop_loss REAL")
            if "take_profit" not in position_columns:
                conn.execute("ALTER TABLE kitty_multi_paper_positions ADD COLUMN take_profit REAL")
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
    # Settings mutate one shared paper ledger, so retain the app's established
    # VIP authorization gate even though the ledger itself never sends orders.
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
            # Publish only the actual gated signal (never candidate_signal) to the
            # separate shadow bridge. The current safety gate forces NO TRADE.
            broker_symbol = {"BTC/USD": "BTC", "XAU/USD": "XAUUSD"}.get(market_symbol)
            if broker_symbol:
                try:
                    from justmarkets_mt5_bridge import publish_shadow_signal
                    from datetime import timedelta
                    published_at = datetime.now(timezone.utc)
                    bridge_result = publish_shadow_signal({
                        "signal_id": market_symbol + ":" + cfg["timeframe"] + ":" + str(candle_time),
                        "symbol": broker_symbol,
                        "direction": "NO_TRADE" if str(signal.get("signal", "")).upper().replace(" ", "_") in {"NO_TRADE", "NO_TRADE"} else str(signal.get("signal", "")).upper(),
                        "candle_time": candle_time,
                        "created_at": published_at.isoformat(),
                        "expires_at": (published_at + timedelta(hours=2)).isoformat(),
                        "entry_reference": price,
                        "stop_loss": (signal.get("risk_levels") or {}).get("stop_reference"),
                        "metadata": {"timeframe": cfg["timeframe"], "source_symbol": market_symbol,
                                     "signal_type": signal.get("signal_type"), "strategy_edge_validated": False},
                    })
                    logger.info("MT5 shadow signal publication status=%s reason=%s",
                                "published" if bridge_result.get("published") else "rejected",
                                bridge_result.get("reason", bridge_result.get("state", "unknown")))
                except Exception as bridge_exc:
                    # The optional bridge must never break the isolated paper ledger.
                    logger.warning("MT5 shadow publication unavailable: %s", type(bridge_exc).__name__)
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
                pos = conn.execute("SELECT * FROM kitty_multi_paper_positions WHERE symbol=?", (market_symbol,)).fetchone()
                quantity = float(pos["quantity"]) if pos else 0.0
                avg_entry = float(pos["avg_entry"]) if pos else 0.0
                stop_loss = float(pos["stop_loss"]) if pos and pos["stop_loss"] is not None else None
                take_profit = float(pos["take_profit"]) if pos and pos["take_profit"] is not None else None
                side = None
                trade_qty = 0.0
                notional = 0.0
                fee = 0.0
                execution_price = price
                exit_reason = None
                risk_budget_usd = None

                # Enforce stored long-position exits on every completed candle.
                # If both stop and target trade inside one candle, assume stop first.
                if quantity > 1e-12 and stop_loss is not None and take_profit is not None:
                    last_candle = closed[-1]
                    candle_low = float(last_candle["low"])
                    candle_high = float(last_candle["high"])
                    candle_open = float(last_candle["open"])
                    if candle_low <= stop_loss:
                        side = "SELL"
                        exit_reason = "stop_loss"
                        execution_price = min(stop_loss, candle_open)
                    elif candle_high >= take_profit:
                        side = "SELL"
                        exit_reason = "take_profit"
                        execution_price = take_profit

                if side is None and signal["signal"] == "BUY" and quantity <= 1e-12:
                    levels = signal.get("risk_levels") or {}
                    proposed_stop = levels.get("stop_reference")
                    proposed_target = levels.get("target_1_reference")
                    valid_levels = False
                    try:
                        proposed_stop = float(proposed_stop)
                        proposed_target = float(proposed_target)
                        valid_levels = (
                            math.isfinite(proposed_stop) and math.isfinite(proposed_target)
                            and 0 < proposed_stop < price < proposed_target
                        )
                    except (TypeError, ValueError):
                        valid_levels = False
                    if valid_levels:
                        # Size from a 0.5% starting-equity risk budget, then apply
                        # the existing notional and available-cash caps.
                        risk_budget_usd = STARTING_CASH * 0.005
                        risk_notional = risk_budget_usd * price / (price - proposed_stop)
                        cash_cap = max(0.0, cash) / (1.0 + FEE_RATE)
                        notional = min(cfg["max_order_notional_usd"], cash_cap, risk_notional)
                        if notional >= 1.0:
                            trade_qty = notional / price
                            fee = notional * FEE_RATE
                            side = "BUY"
                            cash -= notional + fee
                            quantity = trade_qty
                            avg_entry = price
                            stop_loss = proposed_stop
                            take_profit = proposed_target
                if side is None and signal["signal"] == "SELL" and quantity > 1e-12:
                    side = "SELL"
                    trade_qty = quantity
                    notional = trade_qty * price
                    fee = notional * FEE_RATE
                    exit_reason = "signal_exit"
                    quantity = 0.0
                    avg_entry = 0.0
                    stop_loss = None
                    take_profit = None

                if side == "SELL":
                    trade_qty = quantity if exit_reason in {"stop_loss", "take_profit"} else trade_qty
                    notional = trade_qty * execution_price
                    fee = notional * FEE_RATE
                    cash += notional - fee
                    quantity = 0.0
                    avg_entry = 0.0
                    stop_loss = None
                    take_profit = None
                now = datetime.now(timezone.utc).isoformat()
                cycle_status = "simulated_order" if side else "no_action"
                details = {
                    "signal": signal,
                    "execution": "isolated SQLite paper ledger; no exchange calls",
                    "fee_rate": FEE_RATE,
                    "exit_reason": exit_reason,
                    "risk_budget_usd": risk_budget_usd,
                    "cash_after": round(cash, 6),
                }
                conn.execute(
                    "INSERT INTO kitty_multi_paper_cycles(id,symbol,candle_time,timeframe,signal,status,price,details_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), market_symbol, candle_time, cfg["timeframe"], signal["signal"], cycle_status, price, json.dumps(details, allow_nan=False), now),
                )
                if side:
                    conn.execute(
                        "INSERT INTO kitty_multi_paper_orders(id,symbol,candle_time,side,quantity,price,notional_usd,fee_usd,cash_after,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), market_symbol, candle_time, side, trade_qty, execution_price if side == "SELL" else price, notional, fee, cash, now),
                    )
                conn.execute(
                    """INSERT INTO kitty_multi_paper_positions(symbol,quantity,avg_entry,mark_price,updated_at,stop_loss,take_profit)
                       VALUES(?,?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET quantity=excluded.quantity,
                       avg_entry=excluded.avg_entry,mark_price=excluded.mark_price,updated_at=excluded.updated_at,
                       stop_loss=excluded.stop_loss,take_profit=excluded.take_profit""",
                    (market_symbol, quantity, avg_entry, price, now, stop_loss, take_profit),
                )
                conn.execute("UPDATE kitty_multi_paper_account SET cash=?,updated_at=? WHERE id=1", (cash, now))
                conn.commit()
                results.append({
                    "symbol": market_symbol, "status": cycle_status, "signal": signal["signal"],
                    "side": side, "quantity": round(trade_qty, 10), "price": price,
                    "notional_usd": round(notional, 2), "fee_usd": round(fee, 4),
                    "execution_price": execution_price if side == "SELL" else price,
                    "exit_reason": exit_reason, "stop_loss": stop_loss, "take_profit": take_profit,
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



@router.get("/signals")
def current_signals(
    request: Request,
    symbols: str | None = Query(default=None, description="Comma-separated market symbols; defaults to all supported Kitty markets"),
    timeframe: str | None = Query(default=None, description="Candle timeframe; defaults to the saved paper-trading timeframe"),
):
    """Return current completed-candle technical signals without enabling or placing paper orders."""
    _require_user(request)
    cfg = _settings_snapshot()
    selected_timeframe = timeframe or cfg["timeframe"]
    if selected_timeframe not in ALLOWED_TIMEFRAMES:
        raise HTTPException(status_code=422, detail="Unsupported timeframe")
    try:
        selected_symbols = _normalize_symbols(
            [item.strip() for item in symbols.split(",") if item.strip()]
            if symbols is not None else sorted(ALLOWED_SYMBOLS)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from market import get_candles
    from kitty_api import _technical_signal, _validate_candles

    results = []
    for market_symbol in selected_symbols:
        try:
            candles = get_candles(market_symbol, timeframe=selected_timeframe, outputsize=180)
            _validate_candles(candles, selected_timeframe, market_symbol)
            if len(candles) < 56:
                raise ValueError("At least 56 candles are required to exclude the forming candle")
            closed_candles = candles[:-1]
            latest_time = _validate_candles(closed_candles, selected_timeframe, market_symbol)
            signal = _technical_signal(closed_candles, market_symbol, selected_timeframe)
            price = float(signal["price"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("Signal provider returned an invalid price")
            results.append({
                "symbol": market_symbol,
                "status": "available",
                "timeframe": selected_timeframe,
                "completed_candle_time": latest_time,
                "signal": signal,
                "signal_type": "technical_rule_based",
                "model_validated_for_market": False,
                "trading_enabled": False,
            })
        except Exception as exc:
            logger.warning("Kitty current signal unavailable for %s: %s", market_symbol, type(exc).__name__)
            results.append({
                "symbol": market_symbol,
                "status": "unavailable",
                "timeframe": selected_timeframe,
                "error": type(exc).__name__ + ": " + str(exc)[:160],
                "trading_enabled": False,
            })
    return {
        "status": "completed" if any(row["status"] == "available" for row in results) else "unavailable",
        "mode": "read_only",
        "timeframe": selected_timeframe,
        "results": results,
        "available_markets": sum(row["status"] == "available" for row in results),
        "unavailable_markets": sum(row["status"] != "available" for row in results),
        "live_trading_enabled": False,
        "paper_orders_created": False,
        "warning": "These are experimental rule-based technical signals, not validated per-market ML predictions or a promise of profitability.",
    }


def _worker_loop() -> None:
    interval = 7200  # Fixed two-hour cadence requested; avoids frequent provider/API polling.
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
def get_status(request: Request):
    _require_user(request)
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
