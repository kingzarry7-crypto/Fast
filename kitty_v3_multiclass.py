"""Isolated inference loader for Kitty V3's 18-feature, 3-class checkpoint.

This deliberately does not replace the legacy six-feature Kitty model.
Inference remains blocked until target timing and split-boundary audits pass.
No trading or order execution is performed here.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent
WEIGHTS_PATH = ROOT / "kitty_v3_state_dict.pt"
SCALER_PATH = ROOT / "scaler_v3.joblib"
METADATA_PATH = ROOT / "metadata.json"


class KittyV3MulticlassNet(nn.Module):
    """Architecture whose parameter names/shapes match the uploaded metadata."""

    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(18, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def _read_metadata() -> dict[str, Any]:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    features = metadata.get("feature_order")
    if not isinstance(features, list) or len(features) != 18 or len(set(features)) != 18:
        raise ValueError("Kitty V3 metadata must define 18 unique ordered features")
    if metadata.get("architecture_expected") != [18, 64, 32, 3]:
        raise ValueError("Unexpected Kitty V3 architecture metadata")
    if metadata.get("class_mapping") != {"0": "SHORT", "1": "NO_TRADE", "2": "LONG"}:
        raise ValueError("Unexpected Kitty V3 class mapping")
    return metadata


@lru_cache(maxsize=1)
def _load() -> tuple[KittyV3MulticlassNet, Any, dict[str, Any]]:
    metadata = _read_metadata()
    for path in (WEIGHTS_PATH, SCALER_PATH):
        if not path.is_file():
            raise FileNotFoundError(f"Required Kitty V3 artifact missing: {path.name}")

    scaler = joblib.load(SCALER_PATH)
    if getattr(scaler, "n_features_in_", None) != 18:
        raise ValueError("Kitty V3 scaler must have exactly 18 fitted input features")

    # weights_only avoids unpickling arbitrary Python objects from the checkpoint.
    state = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True)
    expected_shapes = metadata.get("state_dict_shapes", {})
    actual_shapes = {key: list(value.shape) for key, value in state.items()
                     if isinstance(value, torch.Tensor)}
    if actual_shapes != expected_shapes:
        raise ValueError("Checkpoint tensor names/shapes do not match metadata")
    model = KittyV3MulticlassNet()
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, scaler, metadata


def status() -> dict[str, Any]:
    try:
        _, scaler, metadata = _load()
        audit_ready = (
            metadata.get("target_execution_alignment_verified") is True
            and metadata.get("split_boundary_audit_passed") is True
        )
        return {
            "available": True,
            "model": metadata["model_name"],
            "num_features": 18,
            "classes": metadata["class_mapping"],
            "scaler_features": int(scaler.n_features_in_),
            "paper_only": True,
            "prediction_enabled": audit_ready,
            "blocking_audits": [
                name for name in ("target_execution_alignment_verified", "split_boundary_audit_passed")
                if metadata.get(name) is not True
            ],
            "automatic_order_execution_enabled": False,
        }
    except Exception as exc:
        return {"available": False, "model": "Kitty V3 BTC", "error": str(exc)}


def predict_features(features: dict[str, float]) -> dict[str, Any]:
    model, scaler, metadata = _load()
    if (metadata.get("target_execution_alignment_verified") is not True
            or metadata.get("split_boundary_audit_passed") is not True):
        raise RuntimeError(
            "Kitty V3 prediction is blocked until target execution alignment "
            "and split-boundary audits are verified."
        )

    names = metadata["feature_order"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError("Missing Kitty V3 features: " + ", ".join(missing))
    values = []
    for name in names:
        value = float(features[name])
        if not math.isfinite(value):
            raise ValueError(f"Feature {name} must be finite")
        values.append(value)

    scaled = scaler.transform([values])
    tensor = torch.as_tensor(scaled, dtype=torch.float32)
    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0].tolist()
    labels = metadata["class_mapping"]
    best_index = max(range(3), key=lambda i: probabilities[i])
    return {
        "model": metadata["model_name"],
        "class": labels[str(best_index)],
        "probabilities": {labels[str(i)]: round(float(probabilities[i]), 6) for i in range(3)},
        "forecast_horizon_hours": metadata["forecast_horizon_hours"],
        "paper_only": True,
        "orders_placed": False,
        "warning": "Experimental model; not evidence of profitability or financial advice.",
    }
