"""Research-only hourly gold/forex dataset builder using Twelve Data.

Requires TWELVEDATA_API_KEY. Uses the same 18-feature/three-class target contract
as Kitty V3, but keeps every market's dataset and checkpoint separate.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import requests

from prepare_kitty_market_dataset import build_dataset

SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
}


def fetch_hourly_candles(symbol: str, api_key: str | None = None, outputsize: int = 5000) -> pd.DataFrame:
    if symbol not in SYMBOLS:
        raise ValueError(f"Unsupported Twelve Data symbol {symbol!r}; choose one of {sorted(SYMBOLS)}")
    if not 500 <= outputsize <= 5000:
        raise ValueError("outputsize must be between 500 and 5000")
    key = (api_key or os.getenv("TWELVEDATA_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("TWELVEDATA_API_KEY is required; add it as a GitHub Actions repository secret.")
    response = requests.get(
        "https://api.twelvedata.com/time_series",
        params={"symbol": SYMBOLS[symbol], "interval": "1h", "outputsize": outputsize,
                "apikey": key, "format": "JSON", "order": "ASC"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("status") == "error" or not isinstance(payload.get("values"), list):
        message = payload.get("message", "Unexpected response from Twelve Data") if isinstance(payload, dict) else "Unexpected response from Twelve Data"
        raise RuntimeError(f"Twelve Data historical request failed: {message}")
    frame = pd.DataFrame(payload["values"])
    required = {"datetime", "open", "high", "low", "close"}
    if not required.issubset(frame.columns):
        raise RuntimeError("Twelve Data response is missing required hourly OHLC fields")
    frame["timestamp"] = pd.to_datetime(frame["datetime"], errors="raise", utc=True)
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if "volume" not in frame.columns:
        frame["volume"] = 0.0
    else:
        frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0.0)
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    if len(frame) < 500:
        raise RuntimeError(f"Only {len(frame)} hourly candles returned for {symbol}; refusing to train")
    return frame[["timestamp", "open", "high", "low", "close", "volume"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", choices=sorted(SYMBOLS), required=True)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--threshold", type=float, default=0.003)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candles = fetch_hourly_candles(args.symbol, outputsize=args.limit)
    dataset = build_dataset(candles, threshold=args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)
    print({"symbol": args.symbol, "provider_symbol": SYMBOLS[args.symbol], "rows": len(dataset),
           "class_counts": dataset["target"].value_counts().sort_index().to_dict(),
           "start": str(dataset["timestamp"].iloc[0]), "end": str(dataset["timestamp"].iloc[-1]),
           "output": str(args.output), "research_only": True})


if __name__ == "__main__":
    main()
