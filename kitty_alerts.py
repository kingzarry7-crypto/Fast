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


def normalize_mtf_watch_signal(mtf_data: dict[str, Any], late_entry: dict[str, Any] | None) -> dict[str, str]:
    """Return BUY/SELL only when multi-timeframe checks agree; otherwise WAIT."""
    data = mtf_data if isinstance(mtf_data, dict) else {}
    tf15 = data.get("15m") if isinstance(data.get("15m"), dict) else {}
    tf5 = data.get("5m") if isinstance(data.get("5m"), dict) else {}
    tf1 = data.get("1h") if isinstance(data.get("1h"), dict) else {}
    tf4 = data.get("4h") if isinstance(data.get("4h"), dict) else {}
    signal = str(data.get("mtf_signal") or tf15.get("signal") or "WAIT").strip().upper()
    if signal not in {"BUY", "SELL"}:
        return {"signal": "WAIT", "reason": "No confirmed multi-timeframe direction"}
    if not isinstance(late_entry, dict):
        return {"signal": "WAIT", "reason": "Late-entry safety check unavailable"}
    status = str(late_entry.get("status") or "").upper()
    action = str(late_entry.get("action") or "").upper()
    try:
        late_score = float(late_entry.get("score", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        return {"signal": "WAIT", "reason": "Late-entry safety score is invalid"}
    if not math.isfinite(late_score):
        return {"signal": "WAIT", "reason": "Late-entry safety score is not finite"}
    if status in {"LATE", "EXTENDED / AVOID", "RISKY"} or late_score >= 45 or action in {"WAIT FOR PULLBACK", "WAIT FOR RETEST", "WAIT"}:
        return {"signal": "WAIT", "reason": "Late-entry / extension filter blocked setup"}
    # Fail closed: every required timeframe must explicitly agree. Missing or
    # neutral candle directions are not confirmation and therefore become WAIT.
    required = {
        "4h": str(tf4.get("signal") or "").strip().upper(),
        "1h": str(tf1.get("signal") or "").strip().upper(),
        "15m": str(tf15.get("signal") or "").strip().upper(),
        "5m": str(tf5.get("signal") or "").strip().upper(),
    }
    opposing = "SELL" if signal == "BUY" else "BUY"
    if any(value == opposing for value in required.values()):
        return {"signal": "WAIT", "reason": "Timeframes conflict; all candles must agree"}
    missing = [timeframe for timeframe, value in required.items() if value != signal]
    if missing:
        return {"signal": "WAIT", "reason": "No confirmation from: " + ", ".join(missing)}
    return {"signal": signal, "reason": "4H, 1H, 15M and 5M candles agree; late-entry filter passed"}
