"""Research-only XAUUSD validation/test diagnosis and fold-trained walk-forward.

Run from the Fast repository root:
  python research-data/scripts/zarry_xau_diagnose.py --csv PATH --output PATH

Uses the repository's existing Kitty trainer and frozen Task 1 run-106 CSV.
No production checkpoint, Kitty service, broker, or deployment is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import train_kitty_v3_retrained as trainer  # noqa: E402
from zarry_calibration import evaluate_calibrated_walk_forward  # noqa: E402

EXPECTED_CSV_SHA256 = "09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c"
PURGE_ROWS = 7
LABEL_THRESHOLD = 0.0015


def feature_drift(x: np.ndarray, y: np.ndarray, train_end: int, val_end: int) -> dict:
    train_stop, val_stop = train_end - PURGE_ROWS, val_end - PURGE_ROWS
    train, validation, test = x[:train_stop], x[train_end:val_stop], x[val_end:]
    scale = np.where(train.std(axis=0) < 1e-12, 1.0, train.std(axis=0))

    def compare(left: np.ndarray, right: np.ndarray) -> dict:
        smd = (right.mean(axis=0) - left.mean(axis=0)) / scale
        order = np.argsort(np.abs(smd))[::-1][:8]
        return {
            "max_abs_mean_smd": float(np.max(np.abs(smd))),
            "top_shifted_features": [
                {"feature": trainer.FEATURES[i], "standardized_mean_difference": float(smd[i])}
                for i in order
            ],
            "volatility_6h_mean_ratio": float(right[:, trainer.FEATURES.index("volatility_6h")].mean() / left[:, trainer.FEATURES.index("volatility_6h")].mean()),
            "volatility_24h_mean_ratio": float(right[:, trainer.FEATURES.index("volatility_24h")].mean() / left[:, trainer.FEATURES.index("volatility_24h")].mean()),
        }

    return {
        "train_vs_validation": compare(train, validation),
        "train_vs_test": compare(train, test),
        "validation_vs_test": compare(validation, test),
        "label_counts_short_no_trade_long": [
            np.bincount(part, minlength=3).tolist()
            for part in (y[:train_stop], y[train_end:val_stop], y[val_end:])
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("zarry-xau-diagnosis.json"))
    parser.add_argument("--round-trip-cost", type=float, default=0.0005)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    digest = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    if digest != EXPECTED_CSV_SHA256:
        raise SystemExit(f"XAUUSD CSV hash mismatch: {digest}")

    frame = pd.read_csv(args.csv)
    time_col = next((name for name in ("timestamp", "datetime", "date") if name in frame), None)
    if time_col:
        frame[time_col] = pd.to_datetime(frame[time_col], errors="raise", utc=True)
        frame = frame.sort_values(time_col, kind="stable").reset_index(drop=True)
    x, y, loaded_digest = trainer.load_dataset(args.csv)
    if loaded_digest != digest or len(frame) != len(x):
        raise SystemExit("Dataset loader did not preserve the verified source rows")
    returns = pd.to_numeric(frame["forward_return_6h"], errors="raise").to_numpy(dtype=np.float64)
    if not np.isfinite(returns).all():
        raise SystemExit("Forward returns contain non-finite values")

    walk_forward = evaluate_calibrated_walk_forward(
        x, y, returns,
        round_trip_cost=args.round_trip_cost,
        label_threshold=LABEL_THRESHOLD,
        folds=3, epochs=30, patience=5, batch_size=128,
        weight_decay=1e-4, seed=args.seed, purge=PURGE_ROWS,
    )
    for fold in walk_forward["folds"]:
        start, end = fold["test_start_index"], fold["test_end_index"]
        raw_test, test_returns = x[start:end], returns[start:end]
        fold["momentum_baseline_stress_1_5x"] = trainer.evaluate_directional_rule(
            raw_test[:, trainer.FEATURES.index("ret_6h")],
            test_returns, threshold=LABEL_THRESHOLD,
            round_trip_cost=args.round_trip_cost * 1.5,
        )
        fold["trend_confirmation_stress_1_5x"] = trainer.evaluate_trend_confirmation_rule(
            raw_test[:, trainer.FEATURES.index("ret_6h")],
            raw_test[:, trainer.FEATURES.index("ret_24h")],
            raw_test[:, trainer.FEATURES.index("close_vs_sma20")],
            test_returns, threshold=LABEL_THRESHOLD,
            round_trip_cost=args.round_trip_cost * 1.5,
        )

    n = len(x)
    output = {
        "run_id": "zarry-task2-xau-calibrated-walkforward-run-001",
        "research_only": True,
        "dataset_sha256": digest,
        "sample_count": n,
        "round_trip_cost": args.round_trip_cost,
        "stress_cost_multiplier": 1.5,
        "purge_rows": PURGE_ROWS,
        "fold_trained_walk_forward": walk_forward,
        "final_split_feature_drift": feature_drift(x, y, int(n * .70), int(n * .85)),
        "safety": {
            "production_checkpoint_modified": False,
            "production_service_modified": False,
            "broker_or_orders_touched": False,
            "live_trading_enabled": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "fold_count": walk_forward["fold_count"],
        "model_profitable_fold_count": walk_forward["model_profitable_fold_count"],
        "selected_thresholds": [f["selected_min_confidence"] for f in walk_forward["folds"]],
    }, indent=2))


if __name__ == "__main__":
    main()
