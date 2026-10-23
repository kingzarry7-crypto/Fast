"""Inference for Kitty's retrained 18-feature BTC classifier.

Research-only: this checkpoint was trained on hourly BTC features. Reusing it
on other symbols or candle intervals is exploratory, not a validated strategy.
This module never places trades.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent
CHECKPOINT_PATH = ROOT / "kitty_v3_retrained_checkpoint.pt"
EXPECTED_FEATURES = [
    "ret_1h", "ret_3h", "ret_6h", "ret_12h", "ret_24h",
    "close_vs_sma6", "close_vs_sma20", "close_vs_sma50",
    "sma6_vs_sma20", "rsi_14", "macd_norm", "macd_signal_norm",
    "macd_hist_norm", "volatility_6h", "volatility_24h",
    "range_pct", "body_pct", "close_position",
]
CLASS_MAPPING = {"0": "SHORT", "1": "NO TRADE", "2": "LONG"}


class KittyV3RetrainedNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(18, 64), nn.ReLU(), nn.Dropout(0.15),
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.10),
            nn.Linear(32, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@lru_cache(maxsize=1)
def _load() -> tuple[KittyV3RetrainedNet, Any, dict[str, Any]]:
    if not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(f"Missing checkpoint: {CHECKPOINT_PATH.name}")
    # This is a trusted repository artifact, not a user-uploaded checkpoint.
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint must be a dictionary bundle")
    if checkpoint.get("features") != EXPECTED_FEATURES:
        raise ValueError("Checkpoint feature order does not match the 18-feature contract")
    if checkpoint.get("architecture") != [18, 64, 32, 3]:
        raise ValueError("Unexpected model architecture")
    state = checkpoint.get("model_state_dict")
    scaler = checkpoint.get("scaler")
    if not isinstance(state, dict) or scaler is None:
        raise ValueError("Checkpoint must include model_state_dict and scaler")
    expected_shapes = {
        "net.0.weight": [64, 18], "net.0.bias": [64],
        "net.3.weight": [32, 64], "net.3.bias": [32],
        "net.6.weight": [3, 32], "net.6.bias": [3],
    }
    shapes = {k: list(v.shape) for k, v in state.items() if isinstance(v, torch.Tensor)}
    if shapes != expected_shapes:
        raise ValueError("Checkpoint tensor names/shapes do not match the trained network")
    if getattr(scaler, "n_features_in_", None) != 18:
        raise ValueError("Bundled scaler must accept exactly 18 features")
    if getattr(scaler, "feature_names_in_", None) is not None:
        if list(scaler.feature_names_in_) != EXPECTED_FEATURES:
            raise ValueError("Scaler feature order does not match the model")
    model = KittyV3RetrainedNet()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, scaler, checkpoint


def status() -> dict[str, Any]:
    try:
        _, scaler, checkpoint = _load()
        return {
            "available": True,
            "model": "Kitty V3 BTC retrained",
            "num_features": 18,
            "features": EXPECTED_FEATURES,
            "classes": CLASS_MAPPING,
            "scaler_features": int(scaler.n_features_in_),
            "best_epoch": checkpoint.get("best_epoch"),
            "validation_accuracy": checkpoint.get("validation_accuracy"),
            "validation_metrics": checkpoint.get("validation_metrics"),
            "test_metrics": checkpoint.get("test_metrics"),
            "training_timeframe": "1h",
            "training_symbol": "BTC (training dataset convention; runtime symbol metadata still needs confirmation)",
            "research_only": True,
            "prediction_enabled": True,
            "signals_enabled": checkpoint.get("production_ready") is True and not (checkpoint.get("test_metrics") or {}).get("signals_disabled_for_no_validated_edge", False),
            "signal_gate": "production approval and validated net edge required",
            "automatic_order_execution_enabled": False,
            "warning": "Experimental classification only. BUY/SELL signals remain blocked until the checkpoint has explicit production approval and a validated positive net edge.",
        }
    except Exception as exc:
        return {
            "available": False,
            "model": "Kitty V3 BTC retrained",
            "prediction_enabled": False,
            "automatic_order_execution_enabled": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def apply_research_signal_gate(raw_signal: str, confidence: float, checkpoint: dict[str, Any]) -> tuple[str, str]:
    """Fail closed unless the approved checkpoint has sufficient positive net holdout trades."""
    test_metrics = checkpoint.get("test_metrics") or {}
    try:
        minimum_confidence = float(checkpoint.get("recommended_min_confidence", 1.01))
    except (TypeError, ValueError, OverflowError):
        minimum_confidence = 1.01
    if checkpoint.get("production_ready") is not True:
        return "NO TRADE", "checkpoint_not_approved_for_production"
    if not isinstance(test_metrics, dict):
        return "NO TRADE", "holdout_validation_metrics_incomplete_or_unprofitable"
    if test_metrics.get("signals_disabled_for_no_validated_edge") is True:
        return "NO TRADE", "holdout_validation_found_no_positive_net_edge"
    if not math.isfinite(minimum_confidence) or not 0.0 <= minimum_confidence <= 1.0:
        return "NO TRADE", "no_validated_confidence_threshold"
    paper_metrics = test_metrics.get("paper_backtest_after_assumed_costs")
    try:
        trade_count = int(paper_metrics.get("trade_count", 0))
        average_net = float(paper_metrics.get("average_net_return"))
        compounded_net = float(paper_metrics.get("compounded_net_return"))
        max_drawdown = float(paper_metrics.get("max_drawdown"))
        profit_factor = float(paper_metrics.get("profit_factor"))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return "NO TRADE", "holdout_validation_metrics_incomplete_or_unprofitable"
    if (
        test_metrics.get("signals_disabled_for_no_validated_edge") is not False
        or trade_count < 30
        or not math.isfinite(average_net)
        or not math.isfinite(compounded_net)
        or not math.isfinite(max_drawdown)
        or average_net <= 0.0
        or compounded_net < 0.01
        or max_drawdown < -0.05
        or not math.isfinite(profit_factor)
        or profit_factor < 1.10
    ):
        return "NO TRADE", "holdout_validation_metrics_incomplete_or_unprofitable"
    if confidence < minimum_confidence:
        return "NO TRADE", "confidence_below_validated_threshold"
    if raw_signal not in {"LONG", "SHORT"}:
        return "NO TRADE", "no_directional_model_signal"
    return raw_signal, "validated_checkpoint_gate_passed"


def predict_features(features: dict[str, float]) -> dict[str, Any]:
    model, scaler, checkpoint = _load()
    missing = [name for name in EXPECTED_FEATURES if name not in features]
    if missing:
        raise ValueError("Missing required Kitty features: " + ", ".join(missing))
    values = []
    for name in EXPECTED_FEATURES:
        try:
            value = float(features[name])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Feature {name} must be a finite number") from exc
        if not math.isfinite(value):
            raise ValueError(f"Feature {name} must be a finite number")
        values.append(value)
    scaled = np.asarray(scaler.transform(np.asarray([values], dtype=np.float64)), dtype=np.float32)
    if scaled.shape != (1, 18) or not np.isfinite(scaled).all():
        raise ValueError("Scaler returned invalid values; expected one row of 18 finite features")
    with torch.inference_mode():
        logits = model(torch.from_numpy(scaled))
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy().astype(float)
    if probs.shape != (3,) or not np.isfinite(probs).all() or abs(float(probs.sum()) - 1.0) > 1e-4:
        raise ValueError("Kitty returned invalid class probabilities")
    ranked = np.argsort(probs)
    best = int(ranked[-1])
    confidence = float(probs[best])
    margin = confidence - float(probs[int(ranked[-2])])
    # Conservative guardrails; these are operating filters, not optimized trading thresholds.
    if best == 1 or confidence < 0.50 or margin < 0.10:
        raw_signal = "NO TRADE"
    else:
        raw_signal = CLASS_MAPPING[str(best)]
    signal, signal_gate = apply_research_signal_gate(raw_signal, confidence, checkpoint)
    return {
        "model": "Kitty V3 BTC retrained",
        "signal": signal,
        "proposed_signal": raw_signal,
        "signal_gate": signal_gate,
        "class_prediction": CLASS_MAPPING[str(best)],
        "confidence": round(confidence, 6),
        "margin_over_second_class": round(margin, 6),
        "probabilities": {CLASS_MAPPING[str(i)]: round(float(probs[i]), 6) for i in range(3)},
        "features": {name: float(features[name]) for name in EXPECTED_FEATURES},
        "best_epoch": checkpoint.get("best_epoch"),
        "research_only": True,
        "training_timeframe": "1h",
        "trading_enabled": False,
        "warning": "Research signal only. Multi-timeframe and non-hourly predictions are unvalidated; no orders are placed.",
    }
