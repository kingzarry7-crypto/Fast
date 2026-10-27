"""Fetch genuine 5-minute market candles for Kitty research only.

BTC source: Binance public BTCUSDT spot klines.
XAUUSD source: Twelve Data XAU/USD spot, with no futures/Yahoo fallback.
Provider timestamps denote bar opens and are shifted to candle-close UTC times.
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

COINBASE_URL = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
TWELVEDATA_URL = "https://api.twelvedata.com/time_series"


def fetch_btc(output: Path, limit: int = 5000) -> pd.DataFrame:
    """Fetch BTC/USD spot candles from Coinbase Exchange (Binance may geo-block CI)."""
    end = pd.Timestamp.now(tz="UTC").floor("5min")
    start = end - pd.Timedelta(minutes=5 * limit)
    cursor = start
    rows = []
    window = 300 * 5 * 60  # Coinbase caps a candle response at 300 rows.
    while cursor < end:
        chunk_end = min(cursor + pd.Timedelta(seconds=window), end)
        response = requests.get(COINBASE_URL, params={
            "granularity": 300,
            "start": cursor.isoformat().replace("+00:00", "Z"),
            "end": chunk_end.isoformat().replace("+00:00", "Z"),
        }, headers={"User-Agent": "KittyResearchBacktest/1.0"}, timeout=30)
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected Coinbase candle response")
        rows.extend(batch)
        cursor = chunk_end
        time.sleep(0.12)
    if not rows:
        raise RuntimeError("Coinbase returned no BTC-USD candles")
    frame = pd.DataFrame(rows, columns=["open_time", "low", "high", "open", "close", "volume"])
    frame["timestamp"] = pd.to_datetime(frame["open_time"], unit="s", utc=True) + pd.Timedelta(minutes=5)
    frame = frame[["timestamp", "open", "high", "low", "close"]].drop_duplicates("timestamp").sort_values("timestamp").tail(limit)
    _write(frame, output)
    return frame


def fetch_xauusd(output: Path, limit: int = 5000) -> pd.DataFrame:
    key = os.getenv("TWELVEDATA_API_KEY") or os.getenv("TWELVE_DATA_API_KEY")
    if not key:
        raise RuntimeError("Missing TWELVEDATA_API_KEY/TWELVE_DATA_API_KEY; refusing a non-spot gold fallback")
    response = requests.get(TWELVEDATA_URL, params={
        "symbol": "XAU/USD", "interval": "5min", "outputsize": min(limit, 5000),
        "order": "ASC", "timezone": "UTC", "apikey": key,
    }, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") == "error" or "values" not in payload:
        # Do not print the request URL, which contains the credential.
        raise RuntimeError(f"Twelve Data XAU/USD request failed: {payload.get('message', 'unexpected response')}")
    values = payload["values"]
    frame = pd.DataFrame(values)
    frame["timestamp"] = pd.to_datetime(frame["datetime"], utc=True) + pd.Timedelta(minutes=5)
    frame = frame[["timestamp", "open", "high", "low", "close"]].sort_values("timestamp").tail(limit)
    _write(frame, output)
    return frame


def _write(frame: pd.DataFrame, output: Path) -> None:
    if len(frame) < 1500:
        raise RuntimeError(f"Only {len(frame)} candles available; at least 1500 are required")
    for col in ("open", "high", "low", "close"):
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    frame = frame.drop_duplicates("timestamp").sort_values("timestamp")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", choices=("BTC", "XAUUSD"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    if not 1500 <= args.limit <= 5000:
        raise SystemExit("--limit must be between 1500 and 5000 to respect the Twelve Data endpoint limit")
    frame = fetch_btc(args.output, args.limit) if args.symbol == "BTC" else fetch_xauusd(args.output, args.limit)
    # Only non-secret provenance and timestamps are emitted.
    print({
        "symbol": args.symbol, "source": "Binance BTCUSDT spot" if args.symbol == "BTC" else "Twelve Data XAU/USD spot",
        "rows": len(frame), "first_close_time": frame["timestamp"].iloc[0].isoformat(),
        "last_close_time": frame["timestamp"].iloc[-1].isoformat(),
        "output": str(args.output),
    })


if __name__ == "__main__":
    main()
