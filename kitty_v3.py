"""Kitty V3 local inference for King Zarry AI.

Inference only; this module never places trades. The six input features and
their order are part of the trained model contract.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import torch
from torch import nn

logger = logging.getLogger("king_zarry_kitty")
ASSET_DIR = Path(__file__).resolve().parent / "kitty_v3_assets"

EXPECTED_FEATURES = [
    "Close", "SMA_20", "RSI_14", "BB_Upper", "BB_Lower", "MACD",
]

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
    """Small StandardScaler-compatible transform using saved statistics."""
    n_features_in_ = 6

    def transform(self, rows):
        transformed = []
        for row in rows:
            if len(row) != len(EXPECTED_FEATURES):
                raise ValueError("Kitty scaler expects exactly six features")
            values = [float(value) for value in row]
            if not all(math.isfinite(value) for value in values):
                raise ValueError("Kitty scaler input must contain only finite values")
            transformed.append([
                (value - mean) / scale
                for value, mean, scale in zip(values, _SCALER_MEAN, _SCALER_SCALE)
            ])
        return transformed


def _asset_bytes(name: str) -> bytes:
    path = ASSET_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Kitty V3 asset missing: {name}")
    raw = path.read_bytes()
    try:
        return base64.b64decode(raw.decode("ascii").strip(), validate=True)
    except (UnicodeDecodeError, ValueError):
        # Supports either Base64 text assets or raw binary checkpoints.
        return raw


@lru_cache(maxsize=1)
def _load() -> tuple[KittyOptimizedNet, Any, dict]:
    metadata = json.loads(_asset_bytes("metadata.json.b64").decode("utf-8"))
    if metadata.get("features") != EXPECTED_FEATURES:
        raise ValueError(
            "Kitty V3 metadata feature names/order do not match the trained six-feature contract"
        )
    if metadata.get("architecture") != [6, 32, 16, 1]:
        raise ValueError("Kitty V3 metadata architecture must be [6, 32, 16, 1]")

    # Use the verified six-feature statistics directly. The packaged joblib
    # scaler is incompatible in this runtime and previously failed during load.
    # These constants are the matching StandardScaler mean_/scale_ values.
    scaler = _ScalerFallback()

    model = KittyOptimizedNet()
    state = torch.load(
        io.BytesIO(_asset_bytes("kitty_v3_weights.pt.b64")),
        map_location="cpu",
        weights_only=True,
    )
    if not isinstance(state, dict):
        raise ValueError("Kitty V3 weights must contain a state dictionary")
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
        try:
            value = float(features[name])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Feature {name} must be a finite number") from exc
        if not math.isfinite(value):
            raise ValueError(f"Feature {name} must be finite")
        values.append(value)

    scaled = scaler.transform([values])
    if len(scaled) != 1 or len(scaled[0]) != len(names):
        raise ValueError("Kitty scaler must return exactly six scaled features")
    scaled_values = [float(value) for value in scaled[0]]
    if not all(math.isfinite(value) for value in scaled_values):
        raise ValueError("Kitty scaler returned non-finite feature values")

    tensor = torch.tensor([scaled_values], dtype=torch.float32)
    with torch.inference_mode():
        probability = float(model(tensor).item())
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("Kitty model returned an invalid probability")

    thresholds = metadata.get("thresholds", {})
    sell_below = float(thresholds.get("sell_below", 0.47))
    buy_above = float(thresholds.get("buy_above", 0.53))
    if not (
        math.isfinite(sell_below)
        and math.isfinite(buy_above)
        and 0.0 <= sell_below < buy_above <= 1.0
    ):
        raise ValueError("Kitty model thresholds must satisfy 0 <= sell_below < buy_above <= 1")

    signal = (
        "BUY_BIAS" if probability >= buy_above
        else "SELL_BIAS" if probability <= sell_below
        else "HOLD"
    )
    return {
        "model": metadata.get("model_name", "Kitty V3"),
        "probability_next_close_up": round(probability, 6),
        "signal": signal,
        "thresholds": {"sell_below": sell_below, "buy_above": buy_above},
        "features": {name: float(features[name]) for name in names},
        "warning": "Model output is experimental, not a validated profitable strategy or financial advice. No trades are placed.",
    }
