"""Build leak-free hourly OHLCV features and labels from public Binance candles.

This is a research dataset builder, not an order executor. Binance public klines
are used for crypto assets; unsupported symbols fail closed. Targets enter at the
next hourly candle open and exit at the close six hours after entry.
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

FEATURES = [
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
]
BINANCE_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "BNB": "BNBUSDT"}


def fetch_hourly_klines(symbol: str, limit: int = 5000) -> pd.DataFrame:
    if symbol not in BINANCE_SYMBOLS:
        raise ValueError(f"Unsupported public Binance symbol {symbol!r}")
    if not 500 <= limit <= 5000:
        raise ValueError("limit must be between 500 and 5000")
    rows: list[list] = []
    end_time = None
    session = requests.Session()
    while len(rows) < limit:
        batch_limit = min(1000, limit - len(rows))
        params = {"symbol": BINANCE_SYMBOLS[symbol], "interval": "1h", "limit": batch_limit}
        if end_time is not None:
            params["endTime"] = end_time
        response = session.get("https://api.binance.com/api/v3/klines", params=params, timeout=25)
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        rows = batch + rows
        end_time = int(batch[0][0]) - 1
        if len(batch) < batch_limit:
            break
        time.sleep(0.15)
    unique = {int(row[0]): row for row in rows}
    rows = [unique[key] for key in sorted(unique)][-limit:]
    if len(rows) < 500:
        raise RuntimeError(f"Only {len(rows)} candles returned for {symbol}; refusing to train")
    frame = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    frame["timestamp"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    for name in ("open", "high", "low", "close", "volume"):
        frame[name] = pd.to_numeric(frame[name], errors="raise")
    # Never train on the newest candle while it may still be forming.
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    frame = frame[frame["close_time"].astype("int64") < now_ms].copy()
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return frame


def build_dataset(frame: pd.DataFrame, threshold: float = 0.003, horizon: int = 6) -> pd.DataFrame:
    if not 0.0005 <= threshold <= 0.02:
        raise ValueError("threshold must be between 0.05% and 2%")
    if horizon != 6:
        raise ValueError("The current Kitty target contract is a six-hour forward return")
    frame = frame.sort_values("timestamp").reset_index(drop=True).copy()
    close = frame["close"].astype(float)
    opn = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    if len(frame) < 500 or not np.isfinite(frame[["open", "high", "low", "close"]].to_numpy()).all():
        raise ValueError("At least 500 rows of finite OHLC data are required")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")

    changes = close.pct_change()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_series = ema12 - ema26
    macd_signal = macd_series.ewm(span=9, adjust=False).mean()
    # Keep the feature contract numerically aligned with kitty_api._kitty_features:
    # RSI and volatility are computed from fractional returns, not raw price deltas.
    delta = changes
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = (100 - 100 / (1 + rs)).where(losses != 0, np.where(gains > 0, 100.0, 50.0)).fillna(50.0)
    ret = lambda period: close / close.shift(period) - 1.0
    sma6, sma20, sma50 = close.rolling(6).mean(), close.rolling(20).mean(), close.rolling(50).mean()
    dataset = pd.DataFrame({
        "timestamp": frame["timestamp"],
        "ret_1h": ret(1), "ret_3h": ret(3), "ret_6h": ret(6),
        "ret_12h": ret(12), "ret_24h": ret(24),
        "close_vs_sma6": close / sma6 - 1.0,
        "close_vs_sma20": close / sma20 - 1.0,
        "close_vs_sma50": close / sma50 - 1.0,
        "sma6_vs_sma20": sma6 / sma20 - 1.0,
        "rsi_14": rsi,
        "macd_norm": macd_series / close,
        "macd_signal_norm": macd_signal / close,
        "macd_hist_norm": (macd_series - macd_signal) / close,
        "volatility_6h": changes.rolling(6).apply(lambda values: float(np.std(values, ddof=0)), raw=True),
        "volatility_24h": changes.rolling(24).apply(lambda values: float(np.std(values, ddof=0)), raw=True),
        "range_pct": (high - low) / close,
        "body_pct": (close - opn) / opn,
        "close_position": ((close - low) / (high - low).replace(0, np.nan)).fillna(0.5),
    })
    # A signal is only available after candle t closes. Avoid an impossible
    # same-close fill: enter at the next candle open and exit six hours after
    # entry, at the close of candle t + horizon.
    entry_price = opn.shift(-1)
    exit_price = close.shift(-horizon)
    forward_return = exit_price / entry_price - 1.0
    dataset["entry_price_next_open"] = entry_price
    dataset["exit_price_after_6h"] = exit_price
    dataset["forward_return_6h"] = forward_return
    dataset["target"] = np.select(
        [forward_return <= -threshold, forward_return >= threshold],
        [0, 2], default=1,
    )
    # Remove warm-up rows and rows without the next-open entry / six-hour exit.
    dataset = dataset.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES + ["forward_return_6h"])
    dataset["target"] = dataset["target"].astype(int)
    dataset = dataset[dataset["timestamp"] < frame["timestamp"].iloc[-horizon]].reset_index(drop=True)
    if set(dataset["target"].unique()) != {0, 1, 2}:
        raise ValueError("Dataset must contain SHORT, NO TRADE and LONG examples")
    if len(dataset) < 400:
        raise ValueError("Too few rows remain after feature warm-up and label horizon")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", choices=sorted(BINANCE_SYMBOLS), default="BTC")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--threshold", type=float, default=0.003)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candles = fetch_hourly_klines(args.symbol, args.limit)
    dataset = build_dataset(candles, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)
    print({
        "symbol": args.symbol, "rows": len(dataset),
        "class_counts": dataset["target"].value_counts().sort_index().to_dict(),
        "start": str(dataset["timestamp"].iloc[0]), "end": str(dataset["timestamp"].iloc[-1]),
        "sha256_source_rows": len(candles), "output": str(args.output),
    })


if __name__ == "__main__":
    main()
