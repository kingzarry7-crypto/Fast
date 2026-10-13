"""Isolated loader for the Colab Kitty V3 retraining checkpoint.
Signal inference is opt-in and monitor-only; this module never places trades.
"""
from __future__ import annotations
import math
import os
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
MONITORING_ENV = "KITTY_V3_SIGNAL_MONITORING_ENABLED"

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

def _monitoring_enabled() -> bool:
    return (os.getenv(MONITORING_ENV) or "").strip().lower() in {"1", "true", "yes", "on"}

@lru_cache(maxsize=1)
def _load() -> tuple[KittyV3RetrainedNet, Any, dict[str, Any]]:
    if not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError(f"Missing checkpoint: {CHECKPOINT_PATH.name}")
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint must be a dictionary bundle")
    if checkpoint.get("features") != EXPECTED_FEATURES:
        raise ValueError("Checkpoint feature order does not match the 18-feature contract")
    if checkpoint.get("architecture") != [18, 64, 32, 3]:
        raise ValueError("Unexpected model architecture")
    state, scaler = checkpoint.get("model_state_dict"), checkpoint.get("scaler")
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
    if getattr(scaler, "feature_names_in_", None) is not None and list(scaler.feature_names_in_) != EXPECTED_FEATURES:
        raise ValueError("Scaler feature order does not match the model")
    model = KittyV3RetrainedNet()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, scaler, checkpoint

def status() -> dict[str, Any]:
    enabled = _monitoring_enabled()
    try:
        model, scaler, checkpoint = _load()
        return {
            "available": True, "model": "Kitty V3 BTC retrained", "num_features": 18,
            "classes": CLASS_MAPPING, "scaler_features": int(scaler.n_features_in_),
            "best_epoch": checkpoint.get("best_epoch"),
            "validation_accuracy": checkpoint.get("validation_accuracy"),
            "research_only": True, "prediction_enabled": enabled,
            "signal_monitoring_only": True, "automatic_order_execution_enabled": False,
            "gold_forex_validation": "unverified",
            "reason": "Opt-in monitor-only inference. BTC-trained checkpoint, feature engineering, target horizon and gold/forex transfer are not validated.",
        }
    except Exception as exc:
        return {
            "available": False, "model": "Kitty V3 BTC retrained",
            "prediction_enabled": False, "signal_monitoring_only": True,
            "automatic_order_execution_enabled": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

def predict_features(features: dict[str, float]) -> dict[str, Any]:
    """Return experimental inference only; this function cannot authorize orders."""
    if not _monitoring_enabled():
        raise RuntimeError(f"Kitty signal monitoring is disabled; set {MONITORING_ENV}=true locally to opt in. No orders are placed.")
    if not isinstance(features, dict) or set(features) != set(EXPECTED_FEATURES):
        raise ValueError("features must contain exactly the 18 expected Kitty feature names")
    try:
        ordered = [float(features[name]) for name in EXPECTED_FEATURES]
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("all Kitty features must be numeric") from exc
    if not all(math.isfinite(value) for value in ordered):
        raise ValueError("Kitty features must all be finite numbers")
    model, scaler, checkpoint = _load()
    scaled = scaler.transform(np.asarray(ordered, dtype=np.float64).reshape(1, -1))
    tensor = torch.as_tensor(scaled, dtype=torch.float32)
    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0].cpu().numpy().tolist()
    index = int(np.argmax(probabilities))
    return {
        "signal": CLASS_MAPPING[str(index)], "class_index": index,
        "confidence": float(probabilities[index]),
        "probabilities": {CLASS_MAPPING[str(i)]: float(probabilities[i]) for i in range(3)},
        "model": "Kitty V3 BTC retrained", "best_epoch": checkpoint.get("best_epoch"),
        "monitor_only": True, "trading_authorized": False,
        "gold_forex_validation": "unverified",
        "warning": "Experimental cross-market output only. Confirm feature formulas and target horizon against the original training pipeline; do not use this output to place orders.",
    }
