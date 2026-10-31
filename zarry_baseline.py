"""Deterministic, research-only ZARRY benchmark baselines and simulator."""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

SHORT, NO_TRADE, LONG = 0, 1, 2
LABEL_TO_CLASS = {"SHORT": SHORT, "NO TRADE": NO_TRADE, "LONG": LONG, "0": SHORT, "1": NO_TRADE, "2": LONG}
CLASS_NAMES = ("SHORT", "NO TRADE", "LONG")
BTC_ROUND_TRIP_COST = 0.001
XAU_ROUND_TRIP_COST = 0.0005
LABEL_THRESHOLDS = {"BTCUSD": 0.003, "XAUUSD": 0.0015}
ROUND_TRIP_COSTS = {"BTCUSD": BTC_ROUND_TRIP_COST, "XAUUSD": XAU_ROUND_TRIP_COST}


def _finite(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _features(row: Mapping[str, Any]) -> Mapping[str, Any]:
    features = row.get("features", row)
    if not isinstance(features, Mapping):
        raise ValueError("row features must be a mapping")
    return features


def _class(value: Any) -> int:
    key = str(value).strip().upper()
    if key not in LABEL_TO_CLASS:
        raise ValueError(f"unsupported class label: {value!r}")
    return LABEL_TO_CLASS[key]


def classification_metrics(y_true: Sequence[Any], y_pred: Sequence[Any]) -> dict[str, Any]:
    """Calculate fixed three-class metrics without third-party dependencies."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal lengths")
    if not y_true:
        raise ValueError("classification metrics require at least one sample")
    truth = [_class(value) for value in y_true]
    predicted = [_class(value) for value in y_pred]
    matrix = [[0, 0, 0] for _ in range(3)]
    for actual, guess in zip(truth, predicted):
        matrix[actual][guess] += 1
    per_class: dict[str, dict[str, float | int]] = {}
    recalls = []
    f1_values = []
    for index, name in enumerate(CLASS_NAMES):
        tp = matrix[index][index]
        support = sum(matrix[index])
        predicted_count = sum(matrix[row][index] for row in range(3))
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        recalls.append(recall)
        f1_values.append(f1)
    return {
        "sample_count": len(truth),
        "class_distribution": {name: truth.count(index) for index, name in enumerate(CLASS_NAMES)},
        "accuracy": sum(matrix[i][i] for i in range(3)) / len(truth),
        "balanced_accuracy": sum(recalls) / 3,
        "macro_f1": sum(f1_values) / 3,
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def predict_baseline(
    policy: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    train_rows: Iterable[Mapping[str, Any]] | None = None,
    asset: str | None = None,
) -> list[int]:
    """Return class IDs using the protocol's frozen, deterministic policies."""
    samples = list(rows)
    name = str(policy).strip().lower()
    if name == "majority":
        if train_rows is None:
            raise ValueError("majority baseline requires train_rows; evaluation labels are forbidden")
        training = list(train_rows)
        if not training:
            raise ValueError("majority baseline requires non-empty training rows")
        counts = [0, 0, 0]
        for row in training:
            counts[_class(row.get("label"))] += 1
        majority = max(range(3), key=lambda index: counts[index])
        return [majority] * len(samples)
    if name == "always_wait":
        return [NO_TRADE] * len(samples)
    if name not in {"momentum", "trend_confirmation"}:
        raise ValueError(f"unknown baseline policy: {policy!r}")
    normalized_asset = str(asset or "").upper().replace("/", "").replace("-", "")
    if normalized_asset not in LABEL_THRESHOLDS:
        raise ValueError("momentum and trend baselines require asset BTCUSD or XAUUSD")
    threshold = LABEL_THRESHOLDS[normalized_asset]
    predictions: list[int] = []
    for row in samples:
        features = _features(row)
        momentum = _finite(features.get("ret_6h"), "ret_6h")
        if abs(momentum) < threshold:
            predictions.append(NO_TRADE)
            continue
        direction = LONG if momentum > 0 else SHORT
        if name == "trend_confirmation":
            trend_values = (
                _finite(features.get("close_vs_sma6"), "close_vs_sma6"),
                _finite(features.get("close_vs_sma20"), "close_vs_sma20"),
                _finite(features.get("sma6_vs_sma20"), "sma6_vs_sma20"),
            )
            agrees = all(value > 0 for value in trend_values) if direction == LONG else all(value < 0 for value in trend_values)
            if not agrees:
                predictions.append(NO_TRADE)
                continue
        predictions.append(direction)
    return predictions


def simulate_predictions(
    rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[int],
    *,
    asset: str,
    round_trip_cost: float | None = None,
    stress_multiplier: float = 1.0,
    outcome_horizon_rows: int = 7,
) -> dict[str, Any]:
    """Simulate non-overlapping proxy trades after fixed round-trip costs.

    A decision at row t exits at t+7. The forward return is a proxy label, not
    a realized broker fill or paper-ledger outcome.
    """
    if len(rows) != len(predictions):
        raise ValueError("rows and predictions must have equal lengths")
    if outcome_horizon_rows < 1:
        raise ValueError("outcome_horizon_rows must be positive")
    normalized_asset = str(asset).upper().replace("/", "").replace("-", "")
    if normalized_asset not in ROUND_TRIP_COSTS:
        raise ValueError("asset must be BTCUSD or XAUUSD")
    cost = ROUND_TRIP_COSTS[normalized_asset] if round_trip_cost is None else _finite(round_trip_cost, "round_trip_cost")
    multiplier = _finite(stress_multiplier, "stress_multiplier")
    if cost < 0 or multiplier <= 0:
        raise ValueError("cost must be non-negative and stress multiplier positive")
    next_available_index = 0
    net_returns: list[float] = []
    overlap_skips = 0
    incomplete_skips = 0
    trade_indices: list[dict[str, int]] = []
    for index, (row, prediction) in enumerate(zip(rows, predictions)):
        action = int(prediction)
        if action not in (SHORT, NO_TRADE, LONG):
            raise ValueError(f"invalid prediction class: {prediction!r}")
        if action == NO_TRADE:
            continue
        if index < next_available_index:
            overlap_skips += 1
            continue
        exit_index = index + outcome_horizon_rows
        if exit_index >= len(rows):
            incomplete_skips += 1
            continue
        forward_return = _finite(row.get("forward_return"), "forward_return")
        direction = 1.0 if action == LONG else -1.0
        net_returns.append(direction * forward_return - cost * multiplier)
        trade_indices.append({"entry_index": index, "exit_index": exit_index})
        next_available_index = exit_index + 1

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    for result in net_returns:
        equity *= 1.0 + result
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
        if result > 0:
            wins += 1
            gross_profit += result
        elif result < 0:
            gross_loss += abs(result)
    trade_count = len(net_returns)
    return {
        "asset": normalized_asset,
        "completed_trades": trade_count,
        "win_rate": wins / trade_count if trade_count else None,
        "average_net_trade_return": sum(net_returns) / trade_count if trade_count else 0.0,
        "expectancy": sum(net_returns) / trade_count if trade_count else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "compounded_net_return": equity - 1.0,
        "max_drawdown": max_drawdown,
        "exposure_fraction": (sum(item["exit_index"] - item["entry_index"] + 1 for item in trade_indices) / len(rows)) if rows else 0.0,
        "overlap_skips": overlap_skips,
        "incomplete_outcome_skips": incomplete_skips,
        "round_trip_cost": cost * multiplier,
        "net_trade_returns": net_returns,
        "trades": trade_indices,
        "outcome_type": "forward_price_proxy_not_realized_paper_trade",
    }


def run_baseline_benchmark(
    policy: str,
    train_rows: Sequence[Mapping[str, Any]],
    evaluation_rows: Sequence[Mapping[str, Any]],
    *,
    asset: str,
) -> dict[str, Any]:
    """Evaluate one frozen baseline on a supplied chronological partition.

    Inputs must already be verified Task 1 samples from the same asset and
    partition. This function never loads new market data or fits on evaluation
    labels; only the majority policy reads train labels.
    """
    train = list(train_rows)
    evaluation = list(evaluation_rows)
    if not evaluation:
        raise ValueError("evaluation_rows must not be empty")
    name = str(policy).strip().lower()
    predictions = predict_baseline(
        name,
        evaluation,
        train_rows=train if name == "majority" else None,
        asset=asset,
    )
    truth = [row.get("label") for row in evaluation]
    classification = classification_metrics(truth, predictions)
    base_cost = ROUND_TRIP_COSTS.get(str(asset).upper().replace("/", "").replace("-", ""))
    if base_cost is None:
        raise ValueError("asset must be BTCUSD or XAUUSD")
    base_result = simulate_predictions(
        evaluation, predictions, asset=asset, round_trip_cost=base_cost
    )
    stress_result = simulate_predictions(
        evaluation, predictions, asset=asset, round_trip_cost=base_cost,
        stress_multiplier=1.5,
    )
    return {
        "policy": name,
        "asset": str(asset).upper().replace("/", "").replace("-", ""),
        "train_sample_count": len(train),
        "evaluation_sample_count": len(evaluation),
        "predictions": predictions,
        "classification": classification,
        "trading": {
            "base_cost": base_result,
            "stress_1_5x_cost": stress_result,
        },
        "research_only": True,
        "outcome_type": "forward_price_proxy_not_realized_paper_trade",
    }
