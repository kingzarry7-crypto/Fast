"""Leakage-aware ZARRY dataset preparation.

Feature/forward-price labels and realized paper-trade outcomes are deliberately
separate record types. This module does not train models or change Kitty.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Iterable, Mapping

ASSET_ALIASES = {
    "BTC": "BTCUSD", "BTC/USD": "BTCUSD", "BTCUSDT": "BTCUSD",
    "BTC/USDT": "BTCUSD", "BTC-USD": "BTCUSD",
    "XAU": "XAUUSD", "XAU/USD": "XAUUSD", "GOLD": "XAUUSD",
}
TARGET_LABELS = {"0": "SHORT", "1": "NO TRADE", "2": "LONG"}
RESERVED_FEATURE_FIELDS = {
    "timestamp", "datetime", "date", "target", "symbol", "asset",
    "data_source", "source", "label", "label_type", "realized_net_return",
    "forward_return_6h", "entry_price_next_open", "exit_price_after_6h",
}


def normalize_asset(value: str) -> str:
    key = str(value or "").strip().upper().replace(" ", "")
    normalized = ASSET_ALIASES.get(key, key.replace("/", "").replace("-", ""))
    if normalized not in {"BTCUSD", "XAUUSD"}:
        raise ValueError(f"Unsupported ZARRY asset: {value!r}")
    return normalized


def _timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def build_feature_dataset(
    asset: str,
    rows: Iterable[Mapping[str, Any]],
    provenance: str,
    *,
    timeframe: str = "1h",
    feature_version: str = "kitty-hourly-v1",
) -> list[dict[str, Any]]:
    """Normalize model feature samples; labels remain forward-price proxies."""
    expected_asset = normalize_asset(asset)
    if not provenance or not str(provenance).strip():
        raise ValueError("provenance is required")
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source_row in rows:
        row = dict(source_row)
        row_asset = row.get("asset", row.get("symbol"))
        if row_asset and normalize_asset(str(row_asset)) != expected_asset:
            raise ValueError("mixed assets are not allowed in one dataset")
        stamp = _timestamp(row.get("timestamp", row.get("datetime", row.get("date"))))
        if stamp in seen:
            raise ValueError(f"duplicate timestamp for {expected_asset}: {stamp}")
        seen.add(stamp)
        raw_target = str(row.get("target", "")).strip().upper()
        label = TARGET_LABELS.get(raw_target, raw_target)
        if label not in {"SHORT", "NO TRADE", "LONG"}:
            raise ValueError(f"unsupported forward target: {raw_target!r}")
        data_source = str(row.get("data_source", row.get("source", ""))).strip()
        if not data_source:
            raise ValueError("source data_source is required")
        features: dict[str, float] = {}
        for key, value in row.items():
            if key in RESERVED_FEATURE_FIELDS or value in (None, ""):
                continue
            try:
                features[str(key)] = _finite_number(value, str(key))
            except ValueError:
                # Non-feature metadata is not silently converted into a feature.
                continue
        record = {
            "asset": expected_asset,
            "timeframe": timeframe,
            "timestamp": stamp,
            "feature_version": feature_version,
            "features": features,
            "label": label,
            "label_type": "forward_price_proxy",
            "label_horizon": "6h" if "forward_return_6h" in row else None,
            "forward_return": (
                _finite_number(row["forward_return_6h"], "forward_return_6h")
                if row.get("forward_return_6h") not in (None, "") else None
            ),
            "market_data_source": data_source,
            "provenance": str(provenance),
        }
        output.append(record)
    return sorted(output, key=lambda item: item["timestamp"])


def chronological_split(
    rows: Iterable[Mapping[str, Any]],
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    purge_rows: int = 6,
) -> dict[str, Any]:
    """Chronological split with a row embargo on both partition boundaries."""
    if purge_rows < 0:
        raise ValueError("purge_rows cannot be negative")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must sum to less than one")
    ordered = sorted((dict(row) for row in rows), key=lambda item: _timestamp(item["timestamp"]))
    stamps = [_timestamp(row["timestamp"]) for row in ordered]
    if len(stamps) != len(set(stamps)):
        raise ValueError("duplicate timestamps cannot be split")
    first = int(len(ordered) * train_fraction)
    second = int(len(ordered) * (train_fraction + validation_fraction))
    train_end = max(0, first - purge_rows)
    validation_start = min(len(ordered), first + purge_rows)
    validation_end = max(validation_start, second - purge_rows)
    test_start = min(len(ordered), second + purge_rows)
    return {
        "train": ordered[:train_end],
        "validation": ordered[validation_start:validation_end],
        "test": ordered[test_start:],
        "purged_rows": (validation_start - train_end) + (test_start - validation_end),
        "split_method": "chronological_with_purged_boundaries",
    }


def validate_paper_trade_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Accept only closed, realized paper trades; never infer outcomes from signals."""
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source_row in rows:
        row = dict(source_row)
        trade_id = str(row.get("trade_id", row.get("id", ""))).strip()
        if not trade_id or trade_id in seen:
            raise ValueError("paper trade IDs must be present and unique")
        seen.add(trade_id)
        if str(row.get("status", "")).strip().lower() not in {"closed", "settled"}:
            raise ValueError("only closed/settled paper trades can be outcomes")
        asset = normalize_asset(str(row.get("asset", row.get("symbol", ""))))
        closed_at = _timestamp(row.get("closed_at", row.get("exit_time")))
        net_return = _finite_number(row.get("realized_net_return"), "realized_net_return")
        if row.get("is_paper") is False or str(row.get("mode", "paper")).lower() == "live":
            raise ValueError("live trades are not accepted in the paper outcome dataset")
        output.append({
            "trade_id": trade_id,
            "asset": asset,
            "closed_at": closed_at,
            "realized_net_return": net_return,
            "outcome": "WIN" if net_return > 0 else "LOSS" if net_return < 0 else "BREAKEVEN",
            "outcome_type": "realized_paper_trade",
            "provenance": str(row.get("provenance", "paper_ledger")),
        })
    return sorted(output, key=lambda item: item["closed_at"])
