"""Kitty V3 local inference for King Zarry AI.

The model and scaler are packaged as base64 text assets to keep binary serialization
out of source-control tooling. This module performs inference only; it never places
trades. Input feature order is defined by metadata.json.
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

def _asset_bytes(name: str) -> bytes:
    path = ASSET_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Kitty V3 asset missing: {name}")
    return base64.b64decode(path.read_text(encoding="ascii").strip(), validate=True)

@lru_cache(maxsize=1)
def _load() -> tuple[KittyOptimizedNet, Any, dict]:
    metadata = json.loads(_asset_bytes("metadata.json.b64").decode("utf-8"))
    scaler = joblib.load(io.BytesIO(_asset_bytes("scaler.joblib.b64")))
    model = KittyOptimizedNet()
    state = torch.load(io.BytesIO(_asset_bytes("kitty_v3_weights.pt.b64")), map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    if len(metadata.get("features", [])) != 6:
        raise ValueError("Kitty V3 metadata must define exactly six features")
    if not hasattr(scaler, "transform"):
        raise ValueError("Kitty V3 scaler does not support transform")
    return model, scaler, metadata

def status() -> dict:
    try:
        _, scaler, metadata = _load()
        return {"available": True, "model": metadata.get("model_name", "Kitty V3"),
                "features": metadata["features"], "scaler_loaded": hasattr(scaler, "transform"),
                "inference_only": True}
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
    return {"model": metadata.get("model_name", "Kitty V3"),
            "probability_next_close_up": round(probability, 6),
            "signal": signal, "thresholds": {"sell_below": sell_below, "buy_above": buy_above},
            "features": {name: float(features[name]) for name in names},
            "warning": "Model output is experimental, not a validated profitable strategy or financial advice. No trades are placed."}
