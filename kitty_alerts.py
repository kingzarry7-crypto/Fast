"""Safety normalization for Kitty model alert messages.

Alert delivery is separate from trade execution. Research-only checkpoints may
show a candidate class, but never an actionable LONG/SHORT signal.
"""
from __future__ import annotations

import math
from typing import Any


DIRECTIONAL = {"LONG", "SHORT"}


def normalize_kitty_alert(prediction: dict[str, Any]) -> dict[str, Any]:
    """Return safe alert fields without upgrading a research prediction."""
    raw_signal = str(prediction.get("signal") or "NO TRADE").strip().upper()
    candidate = str(
        prediction.get("class_prediction")
        or prediction.get("candidate_signal")
        or prediction.get("proposed_signal")
        or raw_signal
    ).strip().upper()
    approved = (
        (prediction.get("production_ready") is True and prediction.get("signal_edge_validated") is True)
        or prediction.get("signal_gate") == "validated_checkpoint_gate_passed"
    )
    try:
        confidence = float(prediction.get("confidence"))
    except (TypeError, ValueError, OverflowError):
        confidence = float("nan")
    confidence_valid = math.isfinite(confidence) and 0.0 <= confidence <= 1.0
    if not confidence_valid:
        confidence = 0.0
    if candidate not in DIRECTIONAL | {"NO TRADE"}:
        candidate = "NO TRADE"
    signal = (
        raw_signal
        if raw_signal in DIRECTIONAL and approved and confidence_valid
        else "NO TRADE"
    )
    return {
        "signal": signal,
        "candidate_signal": candidate,
        "confidence": confidence,
        "production_ready": approved,
        "research_only": not approved,
        "actionable": signal in DIRECTIONAL and approved and confidence_valid,
    }
