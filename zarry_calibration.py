"""Research-only probability calibration and disjoint walk-forward evaluation."""
from __future__ import annotations

import numpy as np


def probabilities_from_logits(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be positive and finite")
    values = np.asarray(logits, dtype=np.float64) / float(temperature)
    values -= values.max(axis=1, keepdims=True)
    probs = np.exp(values)
    return probs / probs.sum(axis=1, keepdims=True)


def calibration_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict:
    y = np.asarray(y_true, dtype=np.int64)
    probs = np.asarray(probabilities, dtype=np.float64)
    if probs.shape != (len(y), 3) or len(y) == 0 or not np.isfinite(probs).all():
        raise ValueError("calibration inputs must be non-empty finite three-class probabilities")
    if not np.isin(y, [0, 1, 2]).all():
        raise ValueError("calibration labels must be 0, 1, or 2")
    clipped = np.clip(probs, 1e-12, 1.0)
    nll = float(-np.log(clipped[np.arange(len(y)), y]).mean())
    one_hot = np.eye(3, dtype=np.float64)[y]
    brier = float(np.square(probs - one_hot).sum(axis=1).mean())
    confidence = probs.max(axis=1)
    correct = probs.argmax(axis=1) == y
    ece = 0.0
    for lower in np.linspace(0.0, 1.0, 11)[:-1]:
        upper = lower + 0.1
        mask = (confidence >= lower) & (confidence < upper if upper < 1.0 else confidence <= upper)
        if mask.any():
            ece += float(mask.mean() * abs(correct[mask].mean() - confidence[mask].mean()))
    return {"nll": nll, "brier_score": brier, "expected_calibration_error_10_bins": ece}


def fit_temperature_from_logits(logits: np.ndarray, y_calibration: np.ndarray) -> dict:
    """Fit scalar temperature by NLL on calibration labels only."""
    values = np.asarray(logits, dtype=np.float64)
    labels = np.asarray(y_calibration, dtype=np.int64)
    if values.shape != (len(labels), 3) or len(labels) < 30:
        raise ValueError("temperature fitting requires at least 30 aligned three-class logits")
    if not np.isfinite(values).all() or not np.isin(labels, [0, 1, 2]).all():
        raise ValueError("temperature fitting requires finite logits and three-class labels")

    def objective(log_t: float) -> float:
        return calibration_metrics(labels, probabilities_from_logits(values, float(np.exp(log_t))))["nll"]

    left, right = float(np.log(0.1)), float(np.log(10.0))
    ratio = (np.sqrt(5.0) - 1.0) / 2.0
    x1, x2 = right - ratio * (right - left), left + ratio * (right - left)
    f1, f2 = objective(x1), objective(x2)
    for _ in range(80):
        if f1 <= f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left)
            f1 = objective(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left)
            f2 = objective(x2)
    temperature = float(np.exp((left + right) / 2.0))
    before = calibration_metrics(labels, probabilities_from_logits(values, 1.0))
    after = calibration_metrics(labels, probabilities_from_logits(values, temperature))
    return {"temperature": temperature, "before": before, "after": after, "sample_count": len(labels)}


def fit_model_temperature(model, x_calibration: np.ndarray, y_calibration: np.ndarray) -> dict:
    import torch
    model.eval()
    with torch.inference_mode():
        logits = model(torch.from_numpy(np.asarray(x_calibration, dtype=np.float32))).cpu().numpy()
    return fit_temperature_from_logits(logits, y_calibration)


def evaluate_calibrated_walk_forward(
    x: np.ndarray,
    y: np.ndarray,
    forward_returns: np.ndarray,
    *,
    round_trip_cost: float,
    label_threshold: float,
    folds: int = 3,
    epochs: int = 30,
    patience: int = 5,
    batch_size: int = 128,
    weight_decay: float = 1e-4,
    seed: int = 42,
    purge: int = 7,
) -> dict:
    """Train/calibrate/select/evaluate on disjoint chronological slices per fold."""
    import train_kitty_v3_retrained as trainer
    from sklearn.preprocessing import StandardScaler

    x = np.asarray(x, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)
    returns = np.asarray(forward_returns, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != len(trainer.FEATURES) or len(x) != len(y) or len(y) != len(returns):
        raise ValueError("walk-forward inputs have incompatible shapes")
    if not np.isfinite(x).all() or not np.isfinite(returns).all():
        raise ValueError("walk-forward inputs must be finite")
    if not 1 <= folds <= 3 or purge < 7 or label_threshold <= 0:
        raise ValueError("folds must be 1..3, purge at least 7, and label threshold positive")

    reports = []
    confidence_grid = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75)
    ret6 = trainer.FEATURES.index("ret_6h")
    ret24 = trainer.FEATURES.index("ret_24h")
    sma20 = trainer.FEATURES.index("close_vs_sma20")

    for fold in range(folds):
        train_end = int(len(x) * (0.40 + 0.10 * fold))
        validation_end = int(len(x) * (0.55 + 0.10 * fold))
        test_end = int(len(x) * (0.65 + 0.10 * fold))
        train_stop = train_end - purge
        validation_stop = validation_end - purge
        validation_mid = train_end + (validation_stop - train_end) // 2
        calibration_stop = validation_mid - purge
        early_size = max(100, int(train_stop * 0.12))
        early_start = train_stop - early_size
        core_stop = early_start - purge
        lengths = (
            core_stop, train_stop - early_start,
            calibration_stop - train_end, validation_stop - validation_mid,
            test_end - validation_end,
        )
        if min(lengths) < 30:
            raise ValueError("insufficient rows for disjoint fold windows")

        x_train_raw, y_train = x[:core_stop], y[:core_stop]
        x_early_raw, y_early = x[early_start:train_stop], y[early_start:train_stop]
        x_cal_raw, y_cal = x[train_end:calibration_stop], y[train_end:calibration_stop]
        x_policy_raw = x[validation_mid:validation_stop]
        policy_returns = returns[validation_mid:validation_stop]
        x_test_raw, y_test = x[validation_end:test_end], y[validation_end:test_end]
        test_returns = returns[validation_end:test_end]

        scaler = StandardScaler()
        x_train = scaler.fit_transform(x_train_raw).astype(np.float32)
        x_early = scaler.transform(x_early_raw).astype(np.float32)
        x_cal = scaler.transform(x_cal_raw).astype(np.float32)
        x_policy = scaler.transform(x_policy_raw).astype(np.float32)
        x_test = scaler.transform(x_test_raw).astype(np.float32)

        model, training = trainer.train_one(
            x_train, y_train, x_early, y_early,
            variant="baseline", optimizer_name="adamw", seed=seed + fold,
            epochs=epochs, patience=patience, batch_size=batch_size,
            weight_decay=weight_decay,
        )
        calibration = fit_model_temperature(model, x_cal, y[train_end:calibration_stop])
        temperature = calibration["temperature"]

        trials = []
        for confidence in confidence_grid:
            metrics = trainer.evaluate_paper_returns(
                model, x_policy, policy_returns, round_trip_cost=round_trip_cost,
                min_confidence=confidence, label_threshold=label_threshold,
                temperature=temperature,
            )
            trials.append({"min_confidence": confidence, **metrics})
        selected, selection_note = trainer.select_confidence_threshold(trials)

        test_metrics = trainer.evaluate_paper_returns(
            model, x_test, test_returns, round_trip_cost=round_trip_cost,
            min_confidence=selected, label_threshold=label_threshold,
            temperature=temperature,
        )
        model_stress = trainer.evaluate_paper_returns(
            model, x_test, test_returns, round_trip_cost=round_trip_cost * 1.5,
            min_confidence=selected, label_threshold=label_threshold,
            temperature=temperature,
        )
        test_metrics["classification"] = trainer.evaluate(model, x_test, y_test)
        test_metrics["probability_calibration_at_test"] = None
        model.eval()
        import torch
        with torch.inference_mode():
            test_logits = model(torch.from_numpy(x_test)).cpu().numpy()
        test_metrics["probability_calibration_at_test"] = calibration_metrics(
            y_test, probabilities_from_logits(test_logits, temperature)
        )

        momentum = trainer.evaluate_directional_rule(
            x_test_raw[:, ret6], test_returns, label_threshold, round_trip_cost
        )
        trend = trainer.evaluate_trend_confirmation_rule(
            x_test_raw[:, ret6], x_test_raw[:, ret24], x_test_raw[:, sma20],
            test_returns, label_threshold, round_trip_cost,
        )
        reports.append({
            "fold": fold + 1,
            "train_end_index": core_stop,
            "early_stopping_start_index": early_start,
            "validation_start_index": train_end,
            "calibration_end_index": calibration_stop,
            "policy_selection_start_index": validation_mid,
            "policy_selection_end_index": validation_stop,
            "test_start_index": validation_end,
            "test_end_index": test_end,
            "train_samples": len(y_train),
            "early_stopping_samples": len(y_early),
            "calibration_samples": len(y_cal),
            "policy_selection_samples": len(policy_returns),
            "test_samples": len(y_test),
            "best_epoch": training["best_epoch"],
            "probability_calibration": calibration,
            "selected_min_confidence": selected,
            "threshold_selection_note": selection_note,
            "model_after_costs": test_metrics,
            "model_stress_1_5x": model_stress,
            "momentum_baseline_after_costs": momentum,
            "trend_confirmation_baseline_after_costs": trend,
        })
    return {
        "purpose": "disjoint expanding-window evaluation; early stopping, temperature fit, policy threshold selection, and test each use separate chronological slices",
        "fold_count": len(reports),
        "model_profitable_fold_count": sum(
            1 for r in reports if r["model_after_costs"]["trade_count"] > 0
            and (r["model_after_costs"]["average_net_return"] or 0) > 0
        ),
        "folds": reports,
    }


def labels_from_forward_returns(forward_returns: np.ndarray, threshold: float) -> np.ndarray:
    """Rebuild SHORT/NO TRADE/LONG targets from the six-hour forward-return proxy."""
    values = np.asarray(forward_returns, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("forward returns must be a finite one-dimensional array")
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("label threshold must be positive and finite")
    return np.where(values <= -threshold, 0, np.where(values >= threshold, 2, 1)).astype(np.int64)


def evaluate_label_threshold_sensitivity(
    x: np.ndarray,
    forward_returns: np.ndarray,
    *,
    thresholds: tuple[float, ...] = (0.001, 0.0015, 0.002),
    round_trip_cost: float,
    folds: int = 3,
    epochs: int = 30,
    patience: int = 5,
    batch_size: int = 128,
    weight_decay: float = 1e-4,
    seed: int = 42,
    purge: int = 7,
) -> dict:
    """Compare label definitions without selecting a threshold on test outcomes."""
    values = np.asarray(forward_returns, dtype=np.float64)
    if len(set(thresholds)) != len(thresholds) or not thresholds:
        raise ValueError("label thresholds must be a non-empty unique sequence")
    results = []
    for threshold in thresholds:
        labels = labels_from_forward_returns(values, threshold)
        walk = evaluate_calibrated_walk_forward(
            x, labels, values, round_trip_cost=round_trip_cost,
            label_threshold=threshold, folds=folds, epochs=epochs,
            patience=patience, batch_size=batch_size,
            weight_decay=weight_decay, seed=seed, purge=purge,
        )
        results.append({
            "label_threshold": threshold,
            "full_dataset_class_counts_short_no_trade_long": np.bincount(labels, minlength=3).tolist(),
            "folds": [
                {
                    "fold": fold["fold"],
                    "best_epoch": fold["best_epoch"],
                    "temperature": fold["probability_calibration"]["temperature"],
                    "calibration_nll_before": fold["probability_calibration"]["before"]["nll"],
                    "calibration_nll_after": fold["probability_calibration"]["after"]["nll"],
                    "selected_confidence": fold["selected_min_confidence"],
                    "test_trades": fold["model_after_costs"]["trade_count"],
                    "test_macro_f1": fold["model_after_costs"]["classification"]["macro_f1"],
                }
                for fold in walk["folds"]
            ],
        })
    return {
        "selection_policy": "descriptive sensitivity only; no label threshold is selected using fold test results",
        "thresholds": results,
    }
