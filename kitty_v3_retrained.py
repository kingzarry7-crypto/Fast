"""Isolated loader for the Colab Kitty V3 retraining checkpoint.

The checkpoint bundles a PyTorch state dict and a fitted sklearn scaler.
Only load this trusted repository artifact: loading a bundled sklearn object
requires pickle deserialization. This module never places trades.
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
    # weights_only=False is required because this trusted checkpoint bundles a
    # StandardScaler object. Never use this loader for an untrusted file.
    checkpoint = torch.load(
        CHECKPOINT_PATH, map_location="cpu", weights_only=False
    )
    if not isinstance(checkpoint, dict):
        raise ValueError("Checkpoint must be a dictionary bundle")
    features = checkpoint.get("features")
    if features != EXPECTED_FEATURES:
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
        model, scaler, checkpoint = _load()
        return {
            "available": True,
            "model": "Kitty V3 BTC retrained",
            "num_features": 18,
            "classes": CLASS_MAPPING,
            "scaler_features": int(scaler.n_features_in_),
            "best_epoch": checkpoint.get("best_epoch"),
            "validation_accuracy": checkpoint.get("validation_accuracy"),
            "research_only": True,
            "prediction_enabled": False,
            "automatic_order_execution_enabled": False,
            "reason": "Target/execution alignment and realistic paper-trading validation remain unverified.",
        }
    except Exception as exc:
        return {
            "available": False,
            "model": "Kitty V3 BTC retrained",
            "prediction_enabled": False,
            "automatic_order_execution_enabled": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def predict_features(features: dict[str, float]) -> dict[str, Any]:
    # Explicitly fail closed: good classification scores alone do not authorize
    # predictions or trades until target timing and trading validation are audited.
    raise RuntimeError(
        "Kitty V3 retrained inference is disabled pending target/execution alignment "
        "and paper-trading validation. No orders are placed."
    )
