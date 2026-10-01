"""
KING ZARRY AI — Trading connector.

Safe-by-default trading bridge:
- Five-symbol allowlist only.
- PAPER mode is the default.
- LIVE mode requires TRADING_ENABLED=true.
- Provider can be selected explicitly or AUTO.
- No withdrawal/transfer APIs exist in this module.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("king_zarry_trading")

APPROVED_SYMBOLS = (
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XAU/USD",
    "UNI/USD",
)

_CRYPTO_BINANCE = {
    "BTC/USD": "BTCUSDT",
    "ETH/USD": "ETHUSDT",
    "SOL/USD": "SOLUSDT",
    "UNI/USD": "UNIUSDT",
}

_LOCK = threading.Lock()


def _bool_env(name: str, default: bool = False) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _num_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def normalize_symbol(symbol: str) -> str:
    raw = (symbol or "").strip().upper().replace("-", "/")
    aliases = {
        "BTC": "BTC/USD",
        "BTCUSDT": "BTC/USD",
        "ETH": "ETH/USD",
        "ETHUSDT": "ETH/USD",
        "SOL": "SOL/USD",
        "SOLUSDT": "SOL/USD",
        "XAU": "XAU/USD",
        "GOLD": "XAU/USD",
        "UNI": "UNI/USD",
        "UNIUSDT": "UNI/USD",
    }
    return aliases.get(raw, raw)


def _db_path() -> str:
    explicit = (os.getenv("TRADING_DB_PATH") or "").strip()
    if explicit:
        return os.path.abspath(explicit)
    data_dir = (os.getenv("DATA_DIR") or "").strip()
    if data_dir:
        return os.path.abspath(os.path.join(data_dir, "king_zarry_trading.db"))
    return os.path.abspath(os.path.join(os.getcwd(), "king_zarry_trading.db"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_paper_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS paper_orders (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol TEXT PRIMARY KEY,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def _paper_balance() -> float:
    return _num_env("PAPER_STARTING_BALANCE", 10000.0)


def status() -> Dict[str, Any]:
    mode = (os.getenv("TRADING_MODE") or "paper").strip().lower()
    provider = (os.getenv("TRADING_PROVIDER") or "auto").strip().lower()
    enabled = _bool_env("TRADING_ENABLED", False)
    kill_switch = _bool_env("AGENT_TRADING_KILL_SWITCH", True)
    max_notional = _num_env("TRADING_MAX_NOTIONAL", 100.0)
    max_trades = int(_num_env("TRADING_MAX_TRADES_PER_DAY", 3))
    live_ready = bool(
        mode == "live"
        and enabled
        and not kill_switch
        and provider in {"auto", "binance", "oanda"}
    )
    if mode not in {"paper", "live"}:
        mode = "paper"
    return {
        "mode": mode,
        "provider": provider,
        "enabled": enabled,
        "kill_switch": kill_switch,
        "max_notional": max_notional,
        "max_trades_per_day": max_trades,
        "approved_symbols": list(APPROVED_SYMBOLS),
        "live_ready": live_ready,
        "live_note": (
            "Live execution is disabled until TRADING_ENABLED=true, "
            "the kill switch is off, and supported credentials/provider are configured."
        ),
    }


def _http_json(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> Dict[str, Any]:
    data = None
    final_headers = {"Accept": "application/json"}
    final_headers.update(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        final_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw or "{}")


def _binance_credentials() -> tuple[str, str]:
    return (
        (os.getenv("BINANCE_API_KEY") or "").strip(),
        (os.getenv("BINANCE_API_SECRET") or "").strip(),
    )


def _binance_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    signed: bool = False,
) -> Dict[str, Any]:
    api_key, secret = _binance_credentials()
    if signed and (not api_key or not secret):
        raise RuntimeError("Binance credentials are not configured")
    params = dict(params or {})
    if signed:
        params.setdefault("timestamp", int(time.time() * 1000))
        params.setdefault("recvWindow", 5000)
        query = urllib.parse.urlencode(params)
        signature = hmac.new(
            secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        query = f"{query}&signature={signature}"
    else:
        query = urllib.parse.urlencode(params)
    url = f"https://api.binance.com{path}"
    if query:
        url += f"?{query}"
    headers = {"X-MBX-APIKEY": api_key} if api_key else {}
    return _http_json(method, url, headers=headers)


def _oanda_credentials() -> tuple[str, str]:
    return (
        (os.getenv("OANDA_API_TOKEN") or "").strip(),
        (os.getenv("OANDA_ACCOUNT_ID") or "").strip(),
    )


def _oanda_base_url() -> str:
    return (
        os.getenv("OANDA_API_URL")
        or "https://api-fxpractice.oanda.com/v3"
    ).rstrip("/")


def _oanda_request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    token, account_id = _oanda_credentials()
    if not token or not account_id:
        raise RuntimeError("OANDA credentials are not configured")
    return _http_json(
        method,
        f"{_oanda_base_url()}{path}",
        headers={"Authorization": f"Bearer {token}"},
        body=body,
    )


def _market_price(symbol: str) -> Optional[float]:
    try:
        from market import get_price, analyze_market

        if callable(get_price):
            value = get_price(symbol)
            if value is not None:
                return float(value)
        data = analyze_market(symbol)
        if isinstance(data, dict):
            value = data.get("price") or data.get("current_price")
            if value is not None:
                return float(value)
    except Exception:
        pass
    return None


def _provider_for(symbol: str) -> str:
    configured = (os.getenv("TRADING_PROVIDER") or "auto").strip().lower()
    if configured != "auto":
        return configured
    return "oanda" if symbol == "XAU/USD" else "binance"


def get_account() -> Dict[str, Any]:
    cfg = status()
    mode = cfg["mode"]
    provider = (cfg["provider"] or "auto").lower()
    if mode == "paper":
        _init_paper_db()
        with _LOCK:
            conn = _connect()
            try:
                rows = conn.execute("SELECT symbol, quantity, avg_price FROM paper_positions WHERE quantity != 0").fetchall()
                positions = [dict(r) for r in rows]
            finally:
                conn.close()
        return {
            "mode": "paper",
            "provider": "paper",
            "balance": _paper_balance(),
            "positions": positions,
        }
    if not cfg["live_ready"]:
        return {"mode": "live", "provider": provider, "ready": False, "positions": []}

    if provider == "binance":
        data = _binance_request("GET", "/api/v3/account", signed=True)
        balances = [
            {
                "asset": b.get("asset"),
                "free": b.get("free"),
                "locked": b.get("locked"),
            }
            for b in (data.get("balances") or [])
            if float(b.get("free") or 0) != 0 or float(b.get("locked") or 0) != 0
        ]
        return {"mode": "live", "provider": "binance", "ready": True, "balances": balances}
    if provider == "oanda":
        _, account_id = _oanda_credentials()
        data = _oanda_request("GET", f"/accounts/{account_id}/summary")
        account = data.get("account") or {}
        return {
            "mode": "live",
            "provider": "oanda",
            "ready": True,
            "balance": account.get("balance"),
            "NAV": account.get("NAV"),
            "open_trade_count": account.get("openTradeCount"),
        }
    raise RuntimeError(f"Unsupported trading provider: {provider}")


def _paper_place(symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
    _init_paper_db()
    order_id = f"paper-{int(time.time()*1000)}-{os.getpid()}"
    now = datetime.now(timezone.utc).isoformat()
    side = side.upper()
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT quantity, avg_price FROM paper_positions WHERE symbol = ?",
                (symbol,),
            ).fetchone()
            current_qty = float(row["quantity"]) if row else 0.0
            current_avg = float(row["avg_price"]) if row else 0.0
            signed_qty = quantity if side == "BUY" else -quantity
            new_qty = current_qty + signed_qty
            if current_qty == 0 or (current_qty > 0 and new_qty > current_qty) or (current_qty < 0 and new_qty < current_qty):
                base_qty = current_qty
                total = abs(base_qty) + quantity
                avg = ((abs(base_qty) * current_avg) + (quantity * price)) / total if total else price
            elif new_qty == 0:
                avg = 0.0
            else:
                avg = current_avg
            conn.execute(
                """
                INSERT INTO paper_positions(symbol, quantity, avg_price, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_price = excluded.avg_price,
                    updated_at = excluded.updated_at
                """,
                (symbol, new_qty, avg, now),
            )
            conn.execute(
                "INSERT INTO paper_orders(id, symbol, side, quantity, price, status, created_at) VALUES (?, ?, ?, ?, ?, 'FILLED', ?)",
                (order_id, symbol, side, quantity, price, now),
            )
            conn.commit()
        finally:
            conn.close()
    return {
        "order_id": order_id,
        "status": "FILLED",
        "mode": "paper",
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
    }


def place_market_order(symbol: str, side: str, quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    side = (side or "").strip().upper()
    if symbol not in APPROVED_SYMBOLS:
        raise ValueError("symbol is outside the five approved Agent markets")
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    cfg = status()
    price = float(price if price is not None else (_market_price(symbol) or 0))
    if price <= 0:
        raise RuntimeError("No current price is available for this order")
    notional = price * quantity
    if notional > float(cfg["max_notional"]):
        raise ValueError(f"order notional {notional:.2f} exceeds TRADING_MAX_NOTIONAL")
    if cfg["kill_switch"]:
        raise RuntimeError("Agent trading kill switch is ON")

    if cfg["mode"] == "paper":
        return _paper_place(symbol, side, quantity, price)

    if not cfg["live_ready"]:
        raise RuntimeError("Live trading is not enabled and/or provider credentials are missing")

    provider = _provider_for(symbol)
    if provider == "binance":
        market_symbol = _CRYPTO_BINANCE.get(symbol)
        if not market_symbol:
            raise RuntimeError(f"{symbol} is not supported by the Binance live connector")
        data = _binance_request(
            "POST",
            "/api/v3/order",
            params={
                "symbol": market_symbol,
                "side": side,
                "type": "MARKET",
                "quantity": f"{quantity:.8f}".rstrip("0").rstrip("."),
                "newOrderRespType": "FULL",
            },
            signed=True,
        )
        return {
            "mode": "live",
            "provider": "binance",
            "status": "FILLED" if data.get("status") == "FILLED" else str(data.get("status") or "ACCEPTED"),
            "order_id": data.get("orderId"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "raw": data,
        }

    if provider == "oanda":
        if symbol != "XAU/USD":
            raise RuntimeError("The OANDA connector in this build is reserved for XAU/USD")
        _, account_id = _oanda_credentials()
        units = str(quantity if side == "BUY" else -quantity)
        data = _oanda_request(
            "POST",
            f"/accounts/{account_id}/orders",
            body={
                "order": {
                    "instrument": "XAU_USD",
                    "units": units,
                    "type": "MARKET",
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                }
            },
        )
        tx = data.get("orderFillTransaction") or data.get("orderCreateTransaction") or {}
        return {
            "mode": "live",
            "provider": "oanda",
            "status": "FILLED" if data.get("orderFillTransaction") else "ACCEPTED",
            "order_id": tx.get("id"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "raw": data,
        }

    raise RuntimeError(f"Unsupported live provider: {provider}")


def list_positions() -> List[Dict[str, Any]]:
    cfg = status()
    if cfg["mode"] == "paper":
        return get_account().get("positions") or []
    if not cfg["live_ready"]:
        return []
    provider = (cfg["provider"] or "auto").lower()
    if provider == "oanda" or (provider == "auto" and os.getenv("OANDA_ACCOUNT_ID")):
        _, account_id = _oanda_credentials()
        data = _oanda_request("GET", f"/accounts/{account_id}/openPositions")
        return data.get("positions") or []
    return []


def close_position(symbol: str, quantity: Optional[float] = None) -> Dict[str, Any]:
    symbol = normalize_symbol(symbol)
    if symbol not in APPROVED_SYMBOLS:
        raise ValueError("symbol is outside the five approved Agent markets")
    cfg = status()
    if cfg["mode"] == "paper":
        _init_paper_db()
        with _LOCK:
            conn = _connect()
            try:
                row = conn.execute("SELECT quantity FROM paper_positions WHERE symbol = ?", (symbol,)).fetchone()
            finally:
                conn.close()
        current = float(row["quantity"]) if row else 0.0
        if current == 0:
            return {"mode": "paper", "status": "NO_POSITION", "symbol": symbol}
        qty = min(abs(current), float(quantity)) if quantity else abs(current)
        side = "SELL" if current > 0 else "BUY"
        return place_market_order(symbol, side, qty)

    if not cfg["live_ready"]:
        raise RuntimeError("Live trading is not enabled")
    provider = _provider_for(symbol)
    if provider == "oanda" and symbol == "XAU/USD":
        _, account_id = _oanda_credentials()
        data = _oanda_request("GET", f"/accounts/{account_id}/openPositions")
        for pos in data.get("positions") or []:
            if pos.get("instrument") == "XAU_USD":
                long_units = float((pos.get("long") or {}).get("units") or 0)
                short_units = float((pos.get("short") or {}).get("units") or 0)
                body: Dict[str, Any] = {"longUnits": "ALL" if long_units else "NONE", "shortUnits": "ALL" if short_units else "NONE"}
                return _oanda_request("PUT", f"/accounts/{account_id}/positions/XAU_USD/close", body=body)
        return {"mode": "live", "status": "NO_POSITION", "symbol": symbol}
    if provider == "binance":
        raise RuntimeError("Binance spot close requires the base-asset position size; use an explicit SELL order for now")
    raise RuntimeError(f"Unsupported live provider: {provider}")
