"""Vantage MT5 Windows bridge for Kitty V3.

This first release is signal-monitoring only. It deliberately contains no order
submission method. The HTTP control surface binds to loopback only.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable

APPROVED_SYMBOLS = ("XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY")
BRIDGE_VERSION = "0.1.0-monitor-only"
BASE_SYMBOLS = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY",
}
FEATURE_CONTRACT_WARNING = (
    "Experimental monitoring only: verify feature engineering against the original "
    "Kitty training pipeline before using predictions for trade decisions."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    dtype = getattr(value, "dtype", None)
    field_names = getattr(dtype, "names", None)
    if field_names:
        return {name: value[name].item() if hasattr(value[name], "item") else value[name] for name in field_names}
    names = ("trade_mode", "login", "server", "currency", "balance", "equity")
    return {name: getattr(value, name) for name in names if hasattr(value, name)}


def verify_demo_account(account_info: Any, demo_trade_mode: int = 0) -> None:
    """Reject unknown and non-demo account modes. Server names are not trusted."""
    info = _as_dict(account_info)
    if "trade_mode" not in info or info["trade_mode"] is None:
        raise PermissionError("MT5 account mode cannot be verified; bridge remains stopped")
    if int(info["trade_mode"]) != int(demo_trade_mode):
        raise PermissionError("Vantage MT5 demo account required; live/contest accounts are rejected")


def resolve_symbols(
    available_symbols: Iterable[str],
    aliases: dict[str, str] | None = None,
) -> dict[str, str]:
    """Resolve canonical markets only when each broker symbol is unambiguous."""
    available = [str(item) for item in available_symbols]
    aliases = aliases or {}
    result: dict[str, str] = {}
    for canonical, base in BASE_SYMBOLS.items():
        override = str(aliases.get(canonical) or "").strip()
        if override:
            if override not in available:
                raise ValueError(f"configured broker symbol {override!r} for {canonical} is unavailable")
            result[canonical] = override
            continue
        candidates = [
            name for name in available
            if name.upper() == base
            or (name.upper().startswith(base) and len(name) > len(base))
        ]
        if not candidates:
            raise ValueError(f"could not resolve Vantage MT5 symbol for {canonical}; configure an exact symbol alias")
        if len(candidates) != 1:
            raise ValueError(f"ambiguous Vantage MT5 symbols for {canonical}: {', '.join(candidates[:5])}")
        result[canonical] = candidates[0]
    return result


class BridgeState:
    """SQLite-backed controls, signal de-duplication and append-only audit events."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            root = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
            db_path = str(root / "KingZarryAI" / "vantage_bridge.sqlite3")
        self.db_path = str(Path(db_path).expanduser().resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        self._fail_stopped_on_startup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS bridge_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    mode TEXT NOT NULL,
                    reason TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bridge_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bridge_signals (
                    signal_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO bridge_state(id, mode, reason, updated_at)
                VALUES (1, 'STOPPED', 'initial fail-stopped state', CURRENT_TIMESTAMP);
                """
            )

    def _audit(self, event: str, details: dict[str, Any] | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO bridge_audit(event, details, created_at) VALUES (?, ?, ?)",
                (event, json.dumps(details or {}, sort_keys=True, default=str), _utc_now()),
            )

    def _set_mode(self, mode: str, reason: str) -> None:
        with self._lock, self._connect() as conn:
            current = conn.execute("SELECT mode FROM bridge_state WHERE id=1").fetchone()
            if current and current["mode"] == "EMERGENCY_STOP" and mode != "EMERGENCY_STOP":
                raise PermissionError("emergency stop is active; explicit confirmed resume is required")
            conn.execute(
                "UPDATE bridge_state SET mode=?, reason=?, updated_at=? WHERE id=1",
                (mode, reason[:500], _utc_now()),
            )
        self._audit("mode_changed", {"mode": mode, "reason": reason[:500]})

    def _fail_stopped_on_startup(self) -> None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT mode FROM bridge_state WHERE id=1").fetchone()
            if row and row["mode"] == "EMERGENCY_STOP":
                self._audit("startup_kept_emergency_stop", {})
                return
            conn.execute(
                "UPDATE bridge_state SET mode='STOPPED', reason='process restart; explicit start required', updated_at=? WHERE id=1",
                (_utc_now(),),
            )
        self._audit("startup_fail_stopped", {})

    def get_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT mode, reason, updated_at FROM bridge_state WHERE id=1").fetchone()
        return {
            "mode": row["mode"],
            "reason": row["reason"],
            "updated_at": row["updated_at"],
            "approved_symbols": list(APPROVED_SYMBOLS),
            "version": BRIDGE_VERSION,
            "signal_monitoring_only": True,
            "order_submission_available": False,
            "live_trading_allowed": False,
        }

    def start_monitoring(self) -> dict[str, Any]:
        self._set_mode("MONITORING", "operator started signal monitoring")
        return self.get_status()

    def pause(self, reason: str = "operator paused monitoring") -> dict[str, Any]:
        self._set_mode("PAUSED", reason)
        return self.get_status()

    def emergency_stop(self, reason: str = "operator emergency stop") -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE bridge_state SET mode='EMERGENCY_STOP', reason=?, updated_at=? WHERE id=1",
                (reason[:500], _utc_now()),
            )
        self._audit("emergency_stop", {"reason": reason[:500]})
        return self.get_status()

    def resume_monitoring(self, confirm: bool = False) -> dict[str, Any]:
        if not confirm:
            raise PermissionError("explicit confirmation is required to clear emergency stop")
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE bridge_state SET mode='MONITORING', reason='operator confirmed resume; monitoring only', updated_at=? WHERE id=1",
                (_utc_now(),),
            )
        self._audit("emergency_stop_cleared", {"confirmed": True})
        return self.get_status()

    def record_signal(self, signal_id: str, payload: dict[str, Any]) -> bool:
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO bridge_signals(signal_id, payload, created_at) VALUES (?, ?, ?)",
                    (str(signal_id), json.dumps(payload, sort_keys=True, default=str), _utc_now()),
                )
            except sqlite3.IntegrityError:
                self._audit("signal_duplicate_blocked", {"signal_id": str(signal_id)})
                return False
        self._audit("signal_recorded", {"signal_id": str(signal_id), "symbol": payload.get("symbol"), "signal": payload.get("signal")})
        return True

    def audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event, details, created_at FROM bridge_audit ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 500)),),
            ).fetchall()
        return [
            {"event": row["event"], "details": json.loads(row["details"]), "created_at": row["created_at"]}
            for row in rows
        ]


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def build_features(rates: Iterable[Any]) -> dict[str, float]:
    """Build a provisional H1 feature vector; see FEATURE_CONTRACT_WARNING."""
    bars = [_as_dict(row) if not isinstance(row, dict) else row for row in rates]
    if len(bars) < 60:
        raise ValueError("at least 60 completed H1 bars are required for Kitty features")
    opens = [float(row["open"]) for row in bars]
    highs = [float(row["high"]) for row in bars]
    lows = [float(row["low"]) for row in bars]
    closes = [float(row["close"]) for row in bars]
    if any(not math.isfinite(x) or x <= 0 for x in closes):
        raise ValueError("market bars contain invalid close prices")
    close = closes[-1]

    def sma(period: int) -> float:
        return sum(closes[-period:]) / period

    def returns(period: int) -> float:
        return close / closes[-period - 1] - 1.0

    changes = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(len(closes) - 14, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(len(closes) - 14, len(closes))]
    avg_gain = sum(gains) / 14.0
    avg_loss = sum(losses) / 14.0
    rsi = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    macd_series = [a - b for a, b in zip(_ema(closes, 12), _ema(closes, 26))]
    macd_signal = _ema(macd_series, 9)[-1]
    macd = macd_series[-1]
    bar_range = highs[-1] - lows[-1]
    features = {
        "ret_1h": returns(1),
        "ret_3h": returns(3),
        "ret_6h": returns(6),
        "ret_12h": returns(12),
        "ret_24h": returns(24),
        "close_vs_sma6": close / sma(6) - 1.0,
        "close_vs_sma20": close / sma(20) - 1.0,
        "close_vs_sma50": close / sma(50) - 1.0,
        "sma6_vs_sma20": sma(6) / sma(20) - 1.0,
        "rsi_14": rsi,
        "macd_norm": macd / close,
        "macd_signal_norm": macd_signal / close,
        "macd_hist_norm": (macd - macd_signal) / close,
        "volatility_6h": statistics.pstdev(changes[-6:]),
        "volatility_24h": statistics.pstdev(changes[-24:]),
        "range_pct": bar_range / close,
        "body_pct": (closes[-1] - opens[-1]) / close,
        "close_position": (close - lows[-1]) / bar_range if bar_range > 0 else 0.5,
    }
    if any(not math.isfinite(value) for value in features.values()):
        raise ValueError("computed Kitty feature vector contains non-finite values")
    return features


def _configured_aliases() -> dict[str, str]:
    env_names = {
        "XAU/USD": "KZ_MT5_SYMBOL_XAUUSD",
        "EUR/USD": "KZ_MT5_SYMBOL_EURUSD",
        "GBP/USD": "KZ_MT5_SYMBOL_GBPUSD",
        "USD/JPY": "KZ_MT5_SYMBOL_USDJPY",
    }
    return {symbol: os.getenv(name, "").strip() for symbol, name in env_names.items() if os.getenv(name, "").strip()}


def monitor_once(state: BridgeState, mt5: Any = None) -> dict[str, Any]:
    """Read demo MT5 H1 data and record monitor-only Kitty signals."""
    if state.get_status()["mode"] != "MONITORING":
        return {"status": "stopped", "signals": []}
    owns_mt5 = mt5 is None
    if mt5 is None:
        try:
            import MetaTrader5 as mt5_module
        except ImportError as exc:
            state.pause("MetaTrader5 Python package is not installed")
            raise RuntimeError("Install the MetaTrader5 package on Windows and open Vantage MT5") from exc
        mt5 = mt5_module

    try:
        path = os.getenv("KZ_MT5_PATH", "").strip()
        login = os.getenv("KZ_MT5_LOGIN", "").strip()
        password = os.getenv("KZ_MT5_PASSWORD", "")
        server = os.getenv("KZ_MT5_SERVER", "").strip()
        if not login or not password or not server:
            state.pause("MT5 credentials/server are not configured")
            raise RuntimeError("Set KZ_MT5_LOGIN, KZ_MT5_PASSWORD and KZ_MT5_SERVER in the local Windows environment")
        kwargs = {"login": int(login), "password": password, "server": server}
        if path:
            connected = mt5.initialize(path, **kwargs)
        else:
            connected = mt5.initialize(**kwargs)
        if not connected:
            state.pause("MT5 initialization failed")
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        account = mt5.account_info()
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
        verify_demo_account(account, demo_trade_mode=demo_mode)

        all_symbols = mt5.symbols_get()
        available = [getattr(item, "name", "") for item in (all_symbols or [])]
        aliases = _configured_aliases()
        resolved = resolve_symbols(available, aliases)
        from kitty_v3_retrained import predict_features

        signals = []
        for canonical, broker_symbol in resolved.items():
            if not mt5.symbol_select(broker_symbol, True):
                raise RuntimeError(f"MT5 could not select broker symbol for {canonical}")
            rates = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_H1, 1, 80)
            if rates is None or len(rates) < 60:
                raise RuntimeError(f"insufficient completed H1 bars for {canonical}")
            features = build_features(rates)
            prediction = predict_features(features)
            timestamp = int(rates[-1]["time"])
            record = {
                "symbol": canonical,
                "broker_symbol": broker_symbol,
                "bar_time": timestamp,
                "signal": prediction["signal"],
                "confidence": prediction["confidence"],
                "probabilities": prediction["probabilities"],
                "monitor_only": True,
                "trading_authorized": False,
                "feature_contract_warning": FEATURE_CONTRACT_WARNING,
            }
            signal_id = f"{canonical}:{timestamp}:{prediction['signal']}"
            if state.record_signal(signal_id, record):
                signals.append(record)
        return {
            "status": "ok",
            "account_mode": "demo",
            "signals": signals,
            "symbols": resolved,
            "monitor_only": True,
            "orders_submitted": 0,
            "feature_contract_warning": FEATURE_CONTRACT_WARNING,
        }
    except PermissionError as exc:
        state.emergency_stop(str(exc))
        raise
    finally:
        if owns_mt5:
            try:
                mt5.shutdown()
            except Exception:
                pass


def create_control_server(state: BridgeState, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Expose a tiny local-only control dashboard; non-loopback binds are forbidden."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("bridge controls must bind to loopback only")

    class Handler(BaseHTTPRequestHandler):
        def _json(self, code: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/status":
                self._json(200, state.get_status())
                return
            if self.path == "/audit":
                self._json(200, {"events": state.audit_events()})
                return
            if self.path != "/":
                self._json(404, {"error": "not found"})
                return
            page = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>King Zarry AI — Vantage Bridge</title><style>body{font:16px system-ui;max-width:760px;margin:32px auto;padding:0 16px;background:#10141d;color:#f3f5f8}button{padding:12px;margin:5px;border:0;border-radius:8px;cursor:pointer}pre{white-space:pre-wrap;background:#1c2431;padding:16px;border-radius:8px}.warn{color:#ffc76b}</style></head><body><h1>King Zarry AI · Vantage MT5</h1><p class="warn">DEMO ONLY · SIGNAL MONITORING · NO ORDER SUBMISSION</p><button onclick="post('/start')">Start monitoring</button><button onclick="post('/pause')">Pause</button><button onclick="post('/emergency-stop')">Emergency stop</button><button onclick="post('/resume')">Confirm resume</button><button onclick="refresh()">Refresh status</button><pre id="status">Loading…</pre><script>async function refresh(){let r=await fetch('/status');document.querySelector('#status').textContent=JSON.stringify(await r.json(),null,2)}async function post(path){let body=path==='/resume'?{confirm:confirm('Clear emergency stop and resume signal monitoring?')}:{ };if(path==='/resume'&&!body.confirm)return;let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});document.querySelector('#status').textContent=JSON.stringify(await r.json(),null,2)}refresh();setInterval(refresh,5000)</script></body></html>"""
            raw = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                if self.path == "/start":
                    result = state.start_monitoring()
                elif self.path == "/pause":
                    result = state.pause()
                elif self.path == "/emergency-stop":
                    result = state.emergency_stop(str(payload.get("reason") or "operator emergency stop"))
                elif self.path == "/resume":
                    result = state.resume_monitoring(confirm=payload.get("confirm") is True)
                else:
                    self._json(404, {"error": "not found"})
                    return
                self._json(200, result)
            except PermissionError as exc:
                self._json(409, {"error": str(exc), **state.get_status()})
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(400, {"error": str(exc)})
            except Exception as exc:
                self._json(500, {"error": type(exc).__name__})

        def log_message(self, fmt: str, *args: Any) -> None:
            # Do not log request bodies or credentials.
            return

    return ThreadingHTTPServer((host, port), Handler)


def run_bridge() -> None:
    state = BridgeState()
    server = create_control_server(state)
    worker_stop = threading.Event()

    def monitor_worker() -> None:
        while not worker_stop.is_set():
            if state.get_status()["mode"] == "MONITORING":
                try:
                    monitor_once(state)
                except Exception as exc:
                    state._audit("monitor_cycle_failed", {"error_type": type(exc).__name__, "message": str(exc)[:240]})
            worker_stop.wait(max(15, int(os.getenv("KZ_MT5_POLL_SECONDS", "60"))))

    worker = threading.Thread(target=monitor_worker, name="vantage-mt5-monitor", daemon=True)
    worker.start()
    print("King Zarry AI Vantage bridge: http://127.0.0.1:8765")
    print("Signal-monitoring only. No order submission is implemented.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        worker_stop.set()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run_bridge()
