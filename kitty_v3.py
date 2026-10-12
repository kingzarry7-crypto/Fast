"""Kitty V3 local inference for King Zarry AI.

Inference only; this module never places trades. Feature order is defined by metadata.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import torch
from torch import nn

logger = logging.getLogger("king_zarry_kitty")
ASSET_DIR = Path(__file__).resolve().parent / "kitty_v3_assets"

# Verified from the packaged six-feature StandardScaler. This fallback avoids
# pickle/joblib compatibility failures across Python/NumPy/sklearn environments.
_SCALER_MEAN = [
    53990.878397032764, 53625.73539316434, 52.24818795669928,
    58035.154544454905, 49216.316241873756, 276.2951492237883,
]
_SCALER_SCALE = [
    31040.441903947303, 30510.269121710633, 17.490193792131915,
    32300.862122537816, 28902.077741073736, 1638.5673916408148,
]

class KittyOptimizedNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layer_1 = nn.Linear(6, 32)
        self.layer_2 = nn.Linear(32, 16)
        self.layer_out = nn.Linear(16, 1)
        self.dropout_1 = nn.Dropout(0.3)
        self.dropout_2 = nn.Dropout(0.2)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.dropout_1(self.relu(self.layer_1(x)))
        x = self.dropout_2(self.relu(self.layer_2(x)))
        return self.sigmoid(self.layer_out(x))

class _ScalerFallback:
    """Small StandardScaler-compatible transform using verified saved statistics."""
    n_features_in_ = 6

    def transform(self, rows):
        return [[(float(value) - mean) / scale
                 for value, mean, scale in zip(row, _SCALER_MEAN, _SCALER_SCALE)]
                for row in rows]

def _asset_bytes(name: str) -> bytes:
    path = ASSET_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Kitty V3 asset missing: {name}")
    raw = path.read_bytes()
    try:
        return base64.b64decode(raw.decode("ascii").strip(), validate=True)
    except (UnicodeDecodeError, ValueError):
        return raw

@lru_cache(maxsize=1)
def _load() -> tuple[KittyOptimizedNet, Any, dict]:
    metadata = json.loads(_asset_bytes("metadata.json.b64").decode("utf-8"))
    if len(metadata.get("features", [])) != 6:
        raise ValueError("Kitty V3 metadata must define exactly six features")
    try:
        scaler = joblib.load(io.BytesIO(_asset_bytes("scaler.joblib.b64")))
        if not hasattr(scaler, "transform"):
            raise TypeError("Packaged Kitty scaler has no transform method")
    except Exception as exc:
        logger.warning("Kitty V3 using compatible scaler fallback (%s)", type(exc).__name__)
        scaler = _ScalerFallback()
    model = KittyOptimizedNet()
    state = torch.load(
        io.BytesIO(_asset_bytes("kitty_v3_weights.pt.b64")),
        map_location="cpu",
        weights_only=True,
    )
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, scaler, metadata

def status() -> dict:
    try:
        _, scaler, metadata = _load()
        return {
            "available": True,
            "model": metadata.get("model_name", "Kitty V3"),
            "features": metadata["features"],
            "scaler_loaded": hasattr(scaler, "transform"),
            "scaler_mode": "compatible_fallback" if isinstance(scaler, _ScalerFallback) else "packaged",
            "inference_only": True,
        }
    except Exception as exc:
        logger.exception("Kitty V3 failed to load")
        return {"available": False, "model": "Kitty V3", "error": type(exc).__name__}

def predict_features(features: dict[str, float]) -> dict:
    model, scaler, metadata = _load()
    names = metadata["features"]
    missing = [name for name in names if name not in features]
    if missing:
        raise ValueError("Missing required Kitty features: " + ", ".join(missing))
    values = []
    for name in names:
        value = float(features[name])
        if not torch.isfinite(torch.tensor(value)).item():
            raise ValueError(f"Feature {name} must be finite")
        values.append(value)
    scaled = scaler.transform([values])
    tensor = torch.tensor(scaled, dtype=torch.float32)
    with torch.no_grad():
        probability = float(model(tensor).item())
    thresholds = metadata.get("thresholds", {})
    sell_below = float(thresholds.get("sell_below", 0.47))
    buy_above = float(thresholds.get("buy_above", 0.53))
    signal = "BUY_BIAS" if probability >= buy_above else "SELL_BIAS" if probability <= sell_below else "HOLD"
    return {
        "model": metadata.get("model_name", "Kitty V3"),
        "probability_next_close_up": round(probability, 6),
        "signal": signal,
        "thresholds": {"sell_below": sell_below, "buy_above": buy_above},
        "features": {name: float(features[name]) for name in names},
        "warning": "Model output is experimental, not a validated profitable strategy or financial advice. No trades are placed.",
    }
