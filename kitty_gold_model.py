"""Symbol-isolated Kitty XAU/USD inference.

A Gold checkpoint is accepted only when it explicitly identifies XAUUSD and
uses Twelve Data XAU/USD spot history. Yahoo GC=F futures-proxy candidates are
never accepted as XAU/USD models. Research inference only; no orders are placed.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch

from kitty_v3_retrained import EXPECTED_FEATURES, KittyV3RetrainedNet

ROOT = Path(__file__).resolve().parent
CHECKPOINT_PATH = ROOT / "models" / "kitty_XAUUSD_checkpoint.pt"
EXPECTED_ARCHITECTURE = [18, 64, 32, 3]
CLASS_MAPPING = {"0": "SHORT", "1": "NO TRADE", "2": "LONG"}


def has_validated_edge(checkpoint: dict[str, Any]) -> bool:
    """Require explicit approval and sufficient positive after-cost holdout results."""
    metrics = checkpoint.get("test_metrics")
    paper = metrics.get("paper_backtest_after_assumed_costs") if isinstance(metrics, dict) else None
    try:
        minimum_confidence = float(checkpoint.get("recommended_min_confidence", 1.01))
        trade_count = int(paper.get("trade_count", 0))
        average_net = float(paper.get("average_net_return"))
        compounded_net = float(paper.get("compounded_net_return"))
        max_drawdown = float(paper.get("max_drawdown"))
        profit_factor = float(paper.get("profit_factor"))
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
    return (
        checkpoint.get("broker_spread_verified") is True
        and checkpoint.get("production_ready") is True
        and isinstance(metrics, dict)
        and metrics.get("signals_disabled_for_no_validated_edge") is False
        and 0.0 <= minimum_confidence <= 1.0
        and trade_count >= 50
        and math.isfinite(average_net)
        and math.isfinite(compounded_net)
        and math.isfinite(max_drawdown)
        and average_net > 0.0
        and compounded_net >= 0.01
        and max_drawdown >= -0.05
        and math.isfinite(profit_factor)
        and profit_factor >= 1.10
    )


def validate_checkpoint_metadata(checkpoint: dict[str, Any]) -> None:
    """Reject cross-symbol, proxy-source, and incompatible checkpoints."""
    if checkpoint.get("training_symbol") != "XAUUSD":
        raise ValueError("Gold checkpoint must explicitly declare training_symbol='XAUUSD'")
    sources = checkpoint.get("training_data_sources")
    if not isinstance(sources, list) or not any(
        isinstance(source, str) and source.startswith("Twelve Data XAU/USD")
        for source in sources
    ):
        raise ValueError("Gold checkpoint requires Twelve Data XAU/USD spot history; GC=F futures proxy is not accepted")
    if checkpoint.get("features") != EXPECTED_FEATURES:
        raise ValueError("Gold checkpoint feature order does not match Kitty's 18-feature contract")
    if checkpoint.get("architecture") != EXPECTED_ARCHITECTURE:
        raise ValueError("Gold checkpoint architecture does not match Kitty V3")
    if checkpoint.get("automatic_order_execution_enabled") is not False:
        raise ValueError("Gold research checkpoint must explicitly disable automatic order execution")


@lru_cache(maxsize=1)
def _load() -> tuple[KittyV3RetrainedNet, Any, dict[str, Any]]:
    if not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(f"Missing validated Gold research checkpoint: {CHECKPOINT_PATH.relative_to(ROOT)}")
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict):
        raise ValueError("Gold checkpoint must be a dictionary bundle")
    validate_checkpoint_metadata(checkpoint)
    state = checkpoint.get("model_state_dict")
    scaler = checkpoint.get("scaler")
    if not isinstance(state, dict) or scaler is None:
        raise ValueError("Gold checkpoint must include model_state_dict and scaler")
    expected_shapes = {
        "net.0.weight": [64, 18], "net.0.bias": [64],
        "net.3.weight": [32, 64], "net.3.bias": [32],
        "net.6.weight": [3, 32], "net.6.bias": [3],
    }
    shapes = {key: list(value.shape) for key, value in state.items() if isinstance(value, torch.Tensor)}
    if shapes != expected_shapes or getattr(scaler, "n_features_in_", None) != 18:
        raise ValueError("Gold checkpoint weights/scaler do not match Kitty V3's 18-feature contract")
    feature_names = getattr(scaler, "feature_names_in_", None)
    if feature_names is not None and list(feature_names) != EXPECTED_FEATURES:
        raise ValueError("Gold scaler feature order does not match Kitty V3")
    model = KittyV3RetrainedNet()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, scaler, checkpoint


def status() -> dict[str, Any]:
    try:
        _, scaler, checkpoint = _load()
        return {
            "available": True,
            "model": "Kitty XAU/USD research candidate",
            "training_symbol": checkpoint["training_symbol"],
            "training_data_sources": checkpoint["training_data_sources"],
            "training_timeframe": checkpoint.get("training_timeframe", "1h"),
            "scaler_features": int(scaler.n_features_in_),
            "test_metrics": checkpoint.get("test_metrics"),
            "signal_edge_validated": has_validated_edge(checkpoint),
            "research_only": True,
            "production_ready": False,
            "trading_enabled": False,
            "automatic_order_execution_enabled": False,
        }
    except Exception as exc:
        return {
            "available": False,
            "model": "Kitty XAU/USD research candidate",
            "prediction_enabled": False,
            "trading_enabled": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def predict_features(features: dict[str, float]) -> dict[str, Any]:
    model, scaler, checkpoint = _load()
    missing = [name for name in EXPECTED_FEATURES if name not in features]
    if missing:
        raise ValueError("Missing required Kitty Gold features: " + ", ".join(missing))
    try:
        values = [float(features[name]) for name in EXPECTED_FEATURES]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Kitty Gold features must be finite numeric values") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Kitty Gold features must be finite numeric values")
    scaled = np.asarray(scaler.transform(np.asarray([values], dtype=np.float64)), dtype=np.float32)
    if scaled.shape != (1, 18) or not np.isfinite(scaled).all():
        raise ValueError("Gold scaler returned invalid values")
    with torch.inference_mode():
        probabilities = torch.softmax(model(torch.from_numpy(scaled)), dim=1)[0].cpu().numpy().astype(float)
    if probabilities.shape != (3,) or not np.isfinite(probabilities).all() or abs(float(probabilities.sum()) - 1.0) > 1e-4:
        raise ValueError("Kitty Gold returned invalid class probabilities")
    ranked = np.argsort(probabilities)
    best = int(ranked[-1])
    confidence = float(probabilities[best])
    margin = confidence - float(probabilities[int(ranked[-2])])
    edge_validated = has_validated_edge(checkpoint)
    try:
        minimum_confidence = float(checkpoint.get("recommended_min_confidence", 1.01))
    except (TypeError, ValueError, OverflowError):
        minimum_confidence = 1.01
    signal = (
        CLASS_MAPPING[str(best)]
        if edge_validated and best != 1 and confidence >= minimum_confidence and margin >= 0.10
        else "NO TRADE"
    )
    return {
        "model": "Kitty XAU/USD research candidate",
        "training_symbol": checkpoint["training_symbol"],
        "signal": signal,
        "class_prediction": CLASS_MAPPING[str(best)],
        "confidence": round(confidence, 6),
        "margin_over_second_class": round(margin, 6),
        "probabilities": {CLASS_MAPPING[str(i)]: round(float(probabilities[i]), 6) for i in range(3)},
        "best_epoch": checkpoint.get("best_epoch"),
        "signal_edge_validated": edge_validated,
        "signal_block_reason": None if edge_validated else "Holdout diagnostics did not explicitly validate a positive net edge; directional signals are suppressed.",
        "research_only": True,
        "production_ready": False,
        "trading_enabled": False,
        "automatic_order_execution_enabled": False,
        "warning": "Gold model inference is research-only and must pass walk-forward and paper-trading validation before use.",
    }
