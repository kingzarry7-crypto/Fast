"""Adapter for Kitty's existing 18-feature hourly research CSVs.

This is an ingestion/manifest step only. It never creates realized paper-trade
outcomes and never trains or promotes a model.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from zarry_dataset import build_feature_dataset_from_csv, normalize_asset

KITTY_FEATURES = (
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
)


def adapt_kitty_hourly_csv(asset: str, csv_path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate source identity/schema and produce a reproducible ZARRY manifest."""
    normalized_asset = normalize_asset(asset)
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing {normalized_asset} source CSV: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    # Parse once for source/schema checks; the shared builder performs strict
    # timestamp, target, finite-number, duplicate, and feature normalization.
    import csv
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        rows = list(reader)
    required = set(KITTY_FEATURES) | {
        "timestamp", "target", "forward_return_6h", "entry_price_next_open",
        "exit_price_after_6h", "data_source",
    }
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"{normalized_asset} Kitty CSV missing required columns: {', '.join(missing)}")
    if not rows:
        raise ValueError(f"{normalized_asset} Kitty CSV has no samples")

    sources = sorted({str(row.get("data_source", "")).strip() for row in rows})
    if "" in sources:
        raise ValueError(f"{normalized_asset} CSV has rows without data_source provenance")
    if normalized_asset == "XAUUSD":
        if any(not source.startswith("Twelve Data XAU/USD") for source in sources):
            raise ValueError("XAUUSD ZARRY training requires verified Twelve Data XAU/USD spot; futures proxies are rejected")
    else:
        allowed = ("Binance public klines", "Yahoo Finance")
        if any(not source.startswith(allowed) for source in sources):
            raise ValueError(f"BTCUSD CSV source is not an approved recorded historical provider: {sources}")

    # The Kitty target convention is signal at t close, entry t+1 open, exit
    # t+7 close. The 7-row embargo is therefore required at each split edge.
    for row_number, row in enumerate(rows, start=2):
        entry = float(row["entry_price_next_open"])
        exit_price = float(row["exit_price_after_6h"])
        forward_return = float(row["forward_return_6h"])
        if not all(map(__import__("math").isfinite, (entry, exit_price, forward_return))) or entry <= 0 or exit_price <= 0:
            raise ValueError(f"row {row_number}: invalid entry/exit/forward-return value")
        calculated = exit_price / entry - 1.0
        if abs(calculated - forward_return) > 1e-8:
            raise ValueError(f"row {row_number}: forward_return_6h does not match next-open/t+7-close prices")

    samples = build_feature_dataset_from_csv(
        normalized_asset,
        path,
        provenance=f"sha256:{digest}",
        timeframe="1h",
        feature_version="kitty-v3-18f-hourly-v1",
    )
    for sample in samples:
        if set(sample["features"]) != set(KITTY_FEATURES):
            raise ValueError("Kitty feature schema mismatch; unexpected or missing numeric feature columns")
    timestamps = [sample["timestamp"] for sample in samples]
    manifest = {
        "schema_version": "zarry-dataset-manifest-v1",
        "asset": normalized_asset,
        "timeframe": "1h",
        "feature_version": "kitty-v3-18f-hourly-v1",
        "feature_columns": list(KITTY_FEATURES),
        "sample_count": len(samples),
        "class_counts": dict(Counter(sample["label"] for sample in samples)),
        "first_timestamp": min(timestamps),
        "last_timestamp": max(timestamps),
        "market_data_sources": sources,
        "source_file_sha256": digest,
        "label_type": "forward_price_proxy",
        "label_horizon": "6h",
        "entry_convention": "next_hour_open",
        "exit_convention": "close_of_t_plus_7_hourly_candle",
        "purge_rows_per_boundary": 7,
        "quote_currency_note": "BTC source may be BTC/USDT or BTC/USD; source identity is retained and must not be silently conflated",
        "realized_paper_outcomes_included": False,
        "training_or_promotion_performed": False,
    }
    return samples, manifest
