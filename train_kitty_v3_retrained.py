"""Research-only Kitty V3 retraining experiments.

Input CSV must contain the 18 features in EXPECTED_FEATURES and a target column
named "target" with SHORT/NO TRADE/LONG or 0/1/2. An optional timestamp column
("timestamp", "datetime", or "date") is sorted chronologically. No live trading
or production checkpoint is changed by this script.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, f1_score, log_loss
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

FEATURES = [
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
]
LABELS = {"SHORT": 0, "NO TRADE": 1, "LONG": 2}
ARCHITECTURE = [18, 64, 32, 3]
LABEL_HORIZON_HOURS = 6
# Entry is at t+1 open and exit at t+7 close, so labels can touch the next
# partition unless we leave a seven-row gap at each split boundary.
MIN_LABEL_PURGE_ROWS = LABEL_HORIZON_HOURS + 1


class KittyExperimentNet(nn.Module):
    """Small MLP with selectable normalization/activation for fair comparisons."""

    def __init__(self, variant: str = "baseline", dropout: float = 0.15):
        super().__init__()
        if variant not in {"baseline", "batchnorm", "leaky_relu"}:
            raise ValueError("variant must be baseline, batchnorm, or leaky_relu")
        activation = nn.LeakyReLU(0.05) if variant == "leaky_relu" else nn.ReLU()
        layers: list[nn.Module] = [nn.Linear(18, 64)]
        if variant == "batchnorm":
            layers.append(nn.BatchNorm1d(64))
        layers.extend([activation, nn.Dropout(dropout), nn.Linear(64, 32)])
        if variant == "batchnorm":
            layers.append(nn.BatchNorm1d(32))
        layers.extend([copy.deepcopy(activation), nn.Dropout(0.10), nn.Linear(32, 3)])
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray, str]:
    frame = pd.read_csv(path)
    missing = [name for name in FEATURES + ["target"] if name not in frame.columns]
    if missing:
        raise ValueError("CSV is missing required columns: " + ", ".join(missing))
    time_col = next((name for name in ("timestamp", "datetime", "date") if name in frame.columns), None)
    if time_col:
        frame[time_col] = pd.to_datetime(frame[time_col], errors="raise", utc=True)
        frame = frame.sort_values(time_col, kind="stable").reset_index(drop=True)
    x = frame[FEATURES].apply(pd.to_numeric, errors="raise").to_numpy(dtype=np.float32)
    raw_y = frame["target"].astype(str).str.strip().str.upper()
    y = raw_y.map({**LABELS, "0": 0, "1": 1, "2": 2})
    if y.isna().any():
        bad = sorted(raw_y[y.isna()].unique().tolist())
        raise ValueError(f"Unsupported target labels: {bad}. Use SHORT, NO TRADE, LONG or 0, 1, 2.")
    y_array = y.to_numpy(dtype=np.int64)
    if len(x) < 100:
        raise ValueError("At least 100 rows are required for chronological train/validation/test splits.")
    if not np.isfinite(x).all():
        raise ValueError("Feature values contain NaN or infinity; clean them before training.")
    if set(np.unique(y_array)) != {0, 1, 2}:
        raise ValueError("Dataset must contain all three classes: SHORT, NO TRADE, LONG.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return x, y_array, digest


def split_chronologically(x: np.ndarray, y: np.ndarray, purge: int = 0):
    """Chronological 70/15/15 split, optionally purging overlapping label horizons."""
    n = len(x)
    train_end, val_end = int(n * 0.70), int(n * 0.85)
    if purge < 0:
        raise ValueError("purge must be non-negative")
    if min(train_end - purge, val_end - train_end - purge, n - val_end) < 1:
        raise ValueError("Not enough rows for chronological splits with the requested purge.")
    return (
        (x[:train_end - purge], y[:train_end - purge]),
        (x[train_end:val_end - purge], y[train_end:val_end - purge]),
        (x[val_end:], y[val_end:]),
    )


def evaluate_paper_returns(model: nn.Module, x: np.ndarray, forward_returns: np.ndarray,
                            round_trip_cost: float = 0.001, min_confidence: float = 0.50,
                            min_margin: float = 0.10, label_threshold: float | None = None,
                            min_edge_cost_multiple: float = 1.25) -> dict:
    """One-pass holdout simulation matching inference confidence/margin filters."""
    if len(x) != len(forward_returns):
        raise ValueError("Test features and forward returns must have equal lengths")
    if not 0 <= round_trip_cost < 0.05:
        raise ValueError("round_trip_cost must be between 0 and 5%")
    if not 0.50 <= min_confidence <= 1.01:
        raise ValueError("min_confidence must be between 0.50 and 1.01; 1.01 is the fail-closed no-signal sentinel")
    if not 0.0 <= min_margin <= 1.0:
        raise ValueError("min_margin must be between 0 and 1")
    if label_threshold is not None and (not np.isfinite(label_threshold) or label_threshold <= 0):
        raise ValueError("label_threshold must be a positive finite return fraction")
    if not np.isfinite(min_edge_cost_multiple) or min_edge_cost_multiple < 1.0:
        raise ValueError("min_edge_cost_multiple must be finite and at least 1.0")
    model.eval()
    with torch.inference_mode():
        probs = torch.softmax(model(torch.from_numpy(x)), dim=1).cpu().numpy()
    trades = []
    next_entry_index = 0
    skipped_overlapping_signals = 0
    skipped_low_margin_signals = 0
    for index, (probabilities, raw_return) in enumerate(zip(probs, forward_returns)):
        if index < next_entry_index:
            skipped_overlapping_signals += 1
            continue
        if not np.isfinite(raw_return):
            continue
        ranked = np.argsort(probabilities)
        side_class = int(ranked[-1])
        confidence = float(probabilities[side_class])
        margin = confidence - float(probabilities[int(ranked[-2])])
        if side_class == 1 or confidence < min_confidence:
            continue
        if margin < min_margin:
            skipped_low_margin_signals += 1
            continue
        # Confidence is not an estimate of profit. Require the directional
        # probability gap, scaled by the dataset's move threshold, to clear
        # the assumed all-in cost by a predeclared safety multiple.
        # This is a conservative edge proxy, not a calibrated return forecast.
        if label_threshold is not None:
            directional_gap = abs(float(probabilities[2]) - float(probabilities[0]))
            directional_edge_proxy = directional_gap * label_threshold
            if directional_edge_proxy < round_trip_cost * min_edge_cost_multiple:
                skipped_low_margin_signals += 1
                continue
        gross = -float(raw_return) if side_class == 0 else float(raw_return)
        trades.append(gross - round_trip_cost)
        # A signal after candle t closes enters at t+1 open and exits at t+7 close.
        # The exit candle is part of the holding window, so the next eligible
        # signal is t+7; t+6 would overlap the prior trade's exit candle.
        next_entry_index = index + 7
    if not trades:
        return {
            "trade_count": 0, "win_rate": None, "average_net_return": None, "profit_factor": None,
            "compounded_net_return": 0.0, "max_drawdown": 0.0,
            "skipped_overlapping_signals": skipped_overlapping_signals,
            "skipped_low_margin_signals": skipped_low_margin_signals,
            "round_trip_cost_assumption": round_trip_cost,
            "minimum_class_confidence": min_confidence,
            "minimum_probability_margin": min_margin,
            "label_threshold_for_edge_proxy": label_threshold,
            "minimum_edge_cost_multiple": min_edge_cost_multiple,
        }
    net = np.asarray(trades, dtype=np.float64)
    equity = np.cumprod(1.0 + net)
    peaks = np.maximum.accumulate(np.concatenate(([1.0], equity)))[1:]
    drawdowns = equity / peaks - 1.0
    gross_profit = float(net[net > 0].sum())
    gross_loss = float(-net[net < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    return {
        "trade_count": len(trades),
        "profit_factor": float(profit_factor),
        "skipped_overlapping_signals": skipped_overlapping_signals,
        "skipped_low_margin_signals": skipped_low_margin_signals,
        "minimum_probability_margin": min_margin,
        "win_rate": float(np.mean(np.asarray(trades) > 0)),
        "average_net_return": float(np.mean(trades)),
        "compounded_net_return": float(equity[-1] - 1.0),
        "max_drawdown": float(np.min(drawdowns)),
        "round_trip_cost_assumption": round_trip_cost,
        "minimum_class_confidence": min_confidence,
        "label_threshold_for_edge_proxy": label_threshold,
        "minimum_edge_cost_multiple": min_edge_cost_multiple,
    }


def evaluate_cost_sensitivity(
    model: nn.Module, x: np.ndarray, forward_returns: np.ndarray,
    round_trip_cost: float, min_confidence: float,
    label_threshold: float | None = None,
) -> dict:
    """Diagnostic-only holdout stress test; never used to select the model or threshold."""
    scenarios = {}
    for multiplier in (1.0, 1.5, 2.0):
        cost = round_trip_cost * multiplier
        metrics = evaluate_paper_returns(
            model, x, forward_returns, round_trip_cost=cost,
            min_confidence=min_confidence, label_threshold=label_threshold,
        )
        scenarios[f"{multiplier:g}x_assumed_cost"] = metrics
    return {
        "purpose": "holdout robustness diagnostic only; not used for model or threshold selection",
        "base_round_trip_cost": round_trip_cost,
        "scenarios": scenarios,
    }


def select_confidence_threshold(threshold_trials: list[dict], min_trades: int = 30) -> tuple[float, str]:
    """Select only a validation threshold with meaningful net returns, sample size, and bounded drawdown."""
    eligible = []
    for trial in threshold_trials:
        try:
            trades = int(trial.get("trade_count", 0) or 0)
            compounded = float(trial.get("compounded_net_return"))
            average = float(trial.get("average_net_return"))
            drawdown = float(trial.get("max_drawdown"))
            profit_factor = float(trial.get("profit_factor"))
            threshold = float(trial.get("min_confidence", 1.01))
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            trades >= min_trades and threshold <= 1.0
            and np.isfinite(compounded) and compounded >= 0.01
            and np.isfinite(average) and average > 0.0
            and np.isfinite(drawdown) and drawdown >= -0.05
            and np.isfinite(profit_factor) and profit_factor >= 1.10
        ):
            eligible.append(trial)
    if not eligible:
        return 1.01, "signals_disabled_no_validation_threshold_meets_30_trades_1pct_net_return_and_5pct_drawdown"
    selected = max(
        eligible,
        key=lambda trial: (
            float(trial["compounded_net_return"]),
            float(trial["average_net_return"]),
            -abs(float(trial["max_drawdown"])),
        ),
    )
    return float(selected["min_confidence"]), "best_validation_net_return_with_30_trades_1pct_net_return_and_5pct_drawdown"



def should_disable_signals(selected_confidence: float, holdout_metrics: dict, min_trades: int = 30) -> bool:
    """Fail closed unless untouched holdout has 30+ trades, >=1% net return, and <=5% drawdown."""
    if not np.isfinite(selected_confidence) or selected_confidence > 1.0:
        return True
    try:
        trade_count = int(holdout_metrics.get("trade_count", 0) or 0)
        average = float(holdout_metrics.get("average_net_return"))
        compounded = float(holdout_metrics.get("compounded_net_return"))
        drawdown = float(holdout_metrics.get("max_drawdown"))
        profit_factor = float(holdout_metrics.get("profit_factor"))
    except (TypeError, ValueError, OverflowError):
        return True
    return not (
        trade_count >= min_trades
        and np.isfinite(average) and average > 0.0
        and np.isfinite(compounded) and compounded >= 0.01
        and np.isfinite(drawdown) and drawdown >= -0.05
        and np.isfinite(profit_factor) and profit_factor >= 1.10
    )



def select_validation_candidate(candidate_trials: list[dict], min_trades: int = 30) -> dict | None:
    """Choose only validation trials with >=30 trades, >=1% compounded net return, and <=5% drawdown."""
    eligible = []
    for trial in candidate_trials:
        try:
            trades = int(trial.get("trade_count", 0) or 0)
            average = float(trial.get("average_net_return"))
            compounded = float(trial.get("compounded_net_return"))
            threshold = float(trial.get("min_confidence", 1.01))
            drawdown = float(trial.get("max_drawdown"))
            profit_factor = float(trial.get("profit_factor"))
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            trades >= min_trades
            and threshold <= 1.0
            and np.isfinite(average)
            and np.isfinite(compounded)
            and np.isfinite(drawdown)
            and average > 0.0
            and compounded >= 0.01
            and drawdown >= -0.05
            and profit_factor >= 1.10
        ):
            eligible.append(trial)
    if not eligible:
        return None
    # Prefer compounded validation return, then average return, then smaller drawdown.
    return max(
        eligible,
        key=lambda trial: (
            float(trial["compounded_net_return"]),
            float(trial["average_net_return"]),
            -abs(float(trial.get("max_drawdown", 0.0) or 0.0)),
        ),
    )


def train_one(
    x_train: np.ndarray, y_train: np.ndarray,
    x_val: np.ndarray, y_val: np.ndarray,
    variant: str, optimizer_name: str, seed: int, epochs: int, patience: int,
    batch_size: int, weight_decay: float,
) -> tuple[KittyExperimentNet, dict]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    model = KittyExperimentNet(variant=variant)
    counts = np.bincount(y_train, minlength=3).astype(np.float32)
    class_weights = counts.sum() / np.maximum(counts, 1.0) / 3.0
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32))
    if optimizer_name == "adamw":
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=weight_decay)
    elif optimizer_name == "adam":
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=weight_decay)
    else:
        raise ValueError("optimizer must be adamw or adam")
    # Reduce the learning rate when validation loss plateaus instead of continuing
    # large updates after the model has stopped improving.
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3, min_lr=1e-5
    )

    # Scaling is fitted only on the training window to avoid future-data leakage.
    train_ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=(variant == "batchnorm" and len(train_ds) > batch_size))
    val_x = torch.from_numpy(x_val)
    val_y = torch.from_numpy(y_val)
    best_loss, best_state, best_epoch, stale = float("inf"), None, 0, 0
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_losses.append(float(loss.detach()))
        model.eval()
        with torch.inference_mode():
            val_logits = model(val_x)
            val_loss = float(nn.functional.cross_entropy(val_logits, val_y))
        scheduler.step(val_loss)
        history.append({
            "epoch": epoch,
            "train_loss": float(np.mean(train_losses)),
            "val_loss": val_loss,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
        })
        if val_loss < best_loss - 1e-5:
            best_loss, best_state, best_epoch, stale = val_loss, copy.deepcopy(model.state_dict()), epoch, 0
        else:
            stale += 1
            if stale >= patience:
                break
    if best_state is None:
        raise RuntimeError("Training did not produce a valid checkpoint.")
    model.load_state_dict(best_state)
    model.eval()
    return model, {"best_epoch": best_epoch, "best_validation_loss": best_loss, "history": history}


def evaluate(model: nn.Module, x: np.ndarray, y: np.ndarray) -> dict:
    model.eval()
    with torch.inference_mode():
        logits = model(torch.from_numpy(x))
        probs = torch.softmax(logits, dim=1).cpu().numpy()
    pred = probs.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "log_loss": float(log_loss(y, probs, labels=[0, 1, 2])),
        "confusion_matrix_labels_0_SHORT_1_NO_TRADE_2_LONG": confusion_matrix(y, pred, labels=[0, 1, 2]).tolist(),
        "classification_report": classification_report(y, pred, labels=[0, 1, 2], target_names=["SHORT", "NO TRADE", "LONG"], output_dict=True, zero_division=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path, help="Historical feature dataset CSV")
    parser.add_argument("--symbol", choices=("BTC", "ETH", "SOL", "BNB", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"), default="BTC", help="Market represented by this research dataset; every market requires its own data and evaluation")
    parser.add_argument("--output-dir", type=Path, default=Path("kitty_v3_experiments"))
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--purge", type=int, default=MIN_LABEL_PURGE_ROWS, help="Rows purged at split boundaries; must cover next-open entry plus the six-hour exit horizon (minimum 7)")
    parser.add_argument("--round-trip-cost", type=float, default=0.001, help="Assumed all-in round-trip spread + commissions/fees + slippage per trade; default 0.10%. This is a conservative assumption, not a broker-quote measurement.")
    parser.add_argument("--label-threshold", type=float, default=None, help="Forward-return class threshold used by the dataset builder")
    args = parser.parse_args()
    if args.epochs < 1 or args.patience < 1 or args.batch_size < 2:
        parser.error("epochs/patience must be positive and batch-size must be at least 2")
    if args.purge < MIN_LABEL_PURGE_ROWS:
        parser.error(f"--purge must be at least {MIN_LABEL_PURGE_ROWS}; labels enter at t+1 open and exit at t+7 close")
    x, y, dataset_sha256 = load_dataset(args.csv)
    (x_train, y_train), (x_val, y_val), (x_test, y_test) = split_chronologically(x, y, purge=args.purge)
    source_frame = pd.read_csv(args.csv)
    time_col = next((name for name in ("timestamp", "datetime", "date") if name in source_frame.columns), None)
    if time_col:
        source_frame[time_col] = pd.to_datetime(source_frame[time_col], errors="raise", utc=True)
        source_frame = source_frame.sort_values(time_col, kind="stable").reset_index(drop=True)
    data_sources = sorted(set(source_frame["data_source"].dropna().astype(str))) if "data_source" in source_frame.columns else ["unspecified historical source"]
    if "forward_return_6h" not in source_frame.columns:
        raise ValueError("Dataset must include forward_return_6h for a cost-aware holdout paper evaluation")
    forward_returns = pd.to_numeric(source_frame["forward_return_6h"], errors="raise").to_numpy(dtype=np.float64)
    if len(forward_returns) != len(x) or not np.isfinite(forward_returns).all():
        raise ValueError("forward_return_6h must contain one finite value per dataset row")
    # Match the exact chronological split, including purged rows, when slicing
    # the forward-return series. The untouched test starts at the 85% boundary.
    n_rows = len(x)
    train_end, val_end = int(n_rows * 0.70), int(n_rows * 0.85)
    val_returns = forward_returns[train_end:val_end - args.purge]
    test_returns = forward_returns[val_end:]
    if len(val_returns) != len(y_val) or len(test_returns) != len(y_test):
        raise ValueError("Forward-return slices do not match the purged validation/test partitions")
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train).astype(np.float32)
    x_val = scaler.transform(x_val).astype(np.float32)
    x_test = scaler.transform(x_test).astype(np.float32)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    candidates = []
    # Run a small, predeclared seed sweep for the inference-compatible baseline.
    # This reduces dependence on one lucky/unlucky random initialization. All
    # seed candidates are selected on validation only; the holdout remains untouched.
    training_runs = [
        (variant, optimizer_name, run_seed)
        for variant in ("baseline", "batchnorm", "leaky_relu")
        for optimizer_name in ("adamw", "adam")
        for run_seed in ((args.seed, args.seed + 17, args.seed + 37) if variant == "baseline" else (args.seed,))
    ]
    for variant, optimizer_name, run_seed in training_runs:
        model, training = train_one(
            x_train, y_train, x_val, y_val, variant, optimizer_name,
            run_seed, args.epochs, args.patience, args.batch_size, args.weight_decay,
        )
        val_metrics = evaluate(model, x_val, y_val)
        run_name = f"{variant}_{optimizer_name}_seed{run_seed}"
        checkpoint_path = args.output_dir / f"{run_name}_candidate.pt"
        # Do not inspect the holdout test set for every candidate: that would
        # turn it into another tuning set. Candidate selection uses validation only.
        torch.save({
            "model_state_dict": model.state_dict(),
            "scaler": scaler,
            "features": FEATURES,
            "architecture": ARCHITECTURE,
            "model_variant": variant,
            "optimizer": optimizer_name,
            "seed": run_seed,
            "training_symbol": args.symbol,
            "training_data_sources": data_sources,
            "training_timeframe": "1h",
            "label_horizon_hours": 6,
            "label_threshold": args.label_threshold if args.label_threshold is not None else "dataset-defined",
            "best_epoch": training["best_epoch"],
            "best_validation_loss": training["best_validation_loss"],
            "validation_metrics": val_metrics,
            "dataset_sha256": dataset_sha256,
            "split_sizes": {"train": len(y_train), "validation": len(y_val), "test": len(y_test)},
            "research_only": True,
            "production_ready": False,
            "automatic_order_execution_enabled": False,
        }, checkpoint_path)
        candidate = {
            "variant": variant, "optimizer": optimizer_name, "seed": run_seed,
            "best_epoch": training["best_epoch"],
            "best_validation_loss": training["best_validation_loss"],
            "validation": val_metrics,
            "checkpoint": str(checkpoint_path),
        }
        results.append(candidate)
        candidates.append((candidate, model))
        print(json.dumps({"run": run_name, "validation": val_metrics, "checkpoint": str(checkpoint_path)}))

    # Predeclare selection using validation macro-F1, then validation log loss.
    # The holdout test partition is evaluated exactly once, after selection.
    # Keep the reported winner loadable by the current production inference
    # contract. BatchNorm/LeakyReLU variants remain comparisons, not deployable
    # checkpoints until the runtime loader is explicitly upgraded.
    compatible_candidates = [
        item for item in candidates if item[0]["variant"] == "baseline"
    ]
    for candidate in results:
        candidate["promotion_compatible_architecture"] = candidate["variant"] == "baseline"

    # Select the production-compatible architecture using validation trading
    # outcomes after assumed costs, not classification accuracy alone. The final
    # holdout remains untouched until one candidate and threshold are selected.
    # Runtime inference never emits a directional candidate below 0.50 confidence.
    # Keep threshold search on the same operating envelope to avoid backtest/live drift.
    confidence_grid = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75)
    candidate_validation_trials = []
    validation_trials_by_name = {}
    for item, model in compatible_candidates:
        local_trials = []
        for confidence_threshold in confidence_grid:
            trial = evaluate_paper_returns(
                model, x_val, val_returns,
                round_trip_cost=args.round_trip_cost,
                min_confidence=confidence_threshold,
                label_threshold=args.label_threshold,
            )
            local_trials.append({"min_confidence": confidence_threshold, **trial})
        confidence, selection_note = select_confidence_threshold(local_trials)
        validation_trials_by_name[item["checkpoint"]] = local_trials
        if confidence <= 1.0:
            selected_trial = next(t for t in local_trials if t["min_confidence"] == confidence)
            candidate_validation_trials.append({
                **selected_trial,
                "candidate": item,
                "model": model,
                "selection_note": selection_note,
            })

    selected_candidate_trial = select_validation_candidate(candidate_validation_trials)
    if selected_candidate_trial is not None:
        winner = selected_candidate_trial["candidate"]
        winning_model = selected_candidate_trial["model"]
        selected_confidence = float(selected_candidate_trial["min_confidence"])
        threshold_selection_note = selected_candidate_trial["selection_note"]
        threshold_trials = validation_trials_by_name[winner["checkpoint"]]
        winner["selected_by"] = "validation_positive_net_return_after_costs_then_compounded_return"
    else:
        # No candidate demonstrated a positive validation edge with enough
        # trades. Keep a research candidate for diagnostics but force the
        # selected confidence to 1.01 so directional signals remain disabled.
        winner, winning_model = max(
            compatible_candidates,
            key=lambda item: (
                item[0]["validation"]["macro_f1"],
                -item[0]["validation"]["log_loss"],
            ),
        )
        threshold_trials = validation_trials_by_name[winner["checkpoint"]]
        selected_confidence, threshold_selection_note = select_confidence_threshold(threshold_trials)
        winner["selected_by"] = "validation_macro_f1_then_log_loss_no_positive_net_return_candidate"

    winner["promotion_compatible_architecture"] = True


    test_metrics = evaluate(winning_model, x_test, y_test)
    paper_metrics = evaluate_paper_returns(
        winning_model, x_test, test_returns,
        round_trip_cost=args.round_trip_cost,
        min_confidence=selected_confidence,
        label_threshold=args.label_threshold,
    )
    test_metrics["paper_backtest_after_assumed_costs"] = paper_metrics
    # Stress-test the untouched holdout at higher costs. These results are
    # diagnostic only and must never be used to tune or select the candidate.
    test_metrics["holdout_cost_sensitivity"] = evaluate_cost_sensitivity(
        winning_model, x_test, test_returns, args.round_trip_cost,
        selected_confidence, args.label_threshold,
    )
    test_metrics["selected_min_confidence_from_validation"] = selected_confidence
    test_metrics["validation_threshold_trials"] = threshold_trials
    test_metrics["threshold_selection_note"] = threshold_selection_note
    test_metrics["signals_disabled_for_no_validated_edge"] = should_disable_signals(selected_confidence, paper_metrics)
    # Reference points make it harder to mistake a weak classifier for a useful
    # trading model. These are diagnostics, not competing deployable models.
    test_metrics["majority_class_baseline_accuracy"] = float(
        max(np.mean(y_test == class_id) for class_id in (0, 1, 2))
    )
    test_metrics["always_no_trade_baseline_trade_count"] = 0
    winner["test"] = test_metrics
    winner.setdefault("selected_by", "validation_macro_f1_then_validation_log_loss")
    winner_path = Path(winner["checkpoint"])
    winner_checkpoint = torch.load(winner_path, map_location="cpu", weights_only=False)
    winner_checkpoint["test_metrics"] = test_metrics
    winner_checkpoint["selected_by"] = winner["selected_by"]
    winner_checkpoint["recommended_min_confidence"] = selected_confidence
    winner_checkpoint["confidence_threshold_selection"] = threshold_selection_note
    torch.save(winner_checkpoint, winner_path)
    print(json.dumps({"selected_candidate": winner["checkpoint"], "selection_metric": winner["selected_by"], "test": test_metrics}))
    report = {
        "model": "Kitty V3 retraining experiment",
        "training_symbol": args.symbol,
        "training_data_sources": data_sources,
        "training_timeframe": "1h",
        "label_horizon_hours": 6,
        "label_threshold": args.label_threshold if args.label_threshold is not None else "dataset-defined",
        "research_only": True,
        "production_ready": False,
        "dataset_sha256": dataset_sha256,
        "feature_order": FEATURES,
        "chronological_split": {"train": len(y_train), "validation": len(y_val), "test": len(y_test), "purged_rows_per_boundary": args.purge},
        "selection": {"candidate": winner["checkpoint"], "rule": winner["selected_by"], "holdout_test_evaluations": 1, "production_architecture_compatible": True},
        "cost_model": {
            "round_trip_cost_assumption": args.round_trip_cost,
            "cost_components": ["spread", "commissions_and_fees", "slippage"],
            "cost_basis": "assumed all-in deduction; not measured live bid/ask or broker-specific fills",
            "broker_spread_verified": False,
        },
        "validation_threshold_selection": {
            "chosen_min_confidence": selected_confidence,
            "rule": threshold_selection_note,
            "trials": threshold_trials,
            "minimum_validation_trades": 10,
        },
        "baseline_checks": {
            "majority_class_test_accuracy": test_metrics["majority_class_baseline_accuracy"],
            "always_no_trade_trade_count": 0,
        },
        "note": "Candidate architecture is selected using validation classification metrics; the abstention threshold is tuned using validation-only net paper returns and a minimum trade count, then evaluated once on the untouched holdout. Targets enter at the next hourly open and exit at the close six hours after entry; the return simulation subtracts assumed costs and skips overlapping trades. This is still a preliminary single-holdout diagnostic, not a walk-forward or executable portfolio backtest. Inspect several chronological test windows, realistic spreads/fills/funding, calibration, and drawdown before production use.",
        "results": results,
    }
    report_path = args.output_dir / "comparison_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved comparison report: {report_path}")


if __name__ == "__main__":
    main()
