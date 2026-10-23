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


def validate_mtf_watch_levels(mtf_data: dict[str, Any], signal: str) -> dict[str, Any]:
    """Require complete, directionally valid 15M entry/SL/TP levels for BUY/SELL alerts."""
    direction = str(signal or "WAIT").strip().upper()
    if direction not in {"BUY", "SELL"}:
        return {"valid": False, "reason": "No directional setup", "signal": "WAIT"}
    data = mtf_data if isinstance(mtf_data, dict) else {}
    tf15 = data.get("15m") if isinstance(data.get("15m"), dict) else {}
    aliases = {
        "entry_low": ("entry_zone_low", "entry_low"),
        "entry_high": ("entry_zone_high", "entry_high"),
        "stop_loss": ("stop_loss", "sl"),
        "tp1": ("tp1", "take_profit_1"),
        "tp2": ("tp2", "take_profit_2"),
        "tp3": ("tp3", "take_profit_3"),
        "price": ("price", "close"),
    }
    values: dict[str, float] = {}
    for target, keys in aliases.items():
        raw = next((tf15.get(key) for key in keys if tf15.get(key) is not None), None)
        try:
            number = float(raw)
        except (TypeError, ValueError, OverflowError):
            return {"valid": False, "signal": "WAIT", "reason": f"Missing or invalid {target.replace('_', ' ')}"}
        if not math.isfinite(number) or number <= 0:
            return {"valid": False, "signal": "WAIT", "reason": f"Missing or invalid {target.replace('_', ' ')}"}
        values[target] = number
    if values["entry_low"] > values["entry_high"]:
        return {"valid": False, "signal": "WAIT", "reason": "Entry zone is inverted"}
    if direction == "BUY":
        ordered = values["stop_loss"] < values["entry_low"] <= values["entry_high"] < values["tp1"] <= values["tp2"] <= values["tp3"]
    else:
        ordered = values["stop_loss"] > values["entry_high"] >= values["entry_low"] > values["tp1"] >= values["tp2"] >= values["tp3"]
    if not ordered:
        return {"valid": False, "signal": "WAIT", "reason": "SL/TP levels do not match the signal direction"}
    entry = (values["entry_low"] + values["entry_high"]) / 2.0
    risk = abs(entry - values["stop_loss"])
    reward = abs(values["tp1"] - entry)
    if risk <= 0 or reward <= 0:
        return {"valid": False, "signal": "WAIT", "reason": "Invalid risk/reward levels"}
    values["risk_reward_tp1"] = reward / risk
    values["signal"] = direction
    values["valid"] = True
    values["reason"] = "15M entry, stop-loss and all three targets passed direction checks"
    return values


def normalize_kitty_mtf_signal(
    prediction: dict[str, Any],
    mtf_data: dict[str, Any],
    late_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    """Require a validated Kitty model direction plus agreeing 4H/1H/15M/5M filters."""
    model = normalize_kitty_alert(prediction if isinstance(prediction, dict) else {})
    if not model["actionable"]:
        return {
            "signal": "WAIT",
            "reason": "Kitty model gate blocked directional output; research-only or no validated net edge",
            "model_actionable": False,
            "candidate_signal": model["candidate_signal"],
            "confidence": model["confidence"],
        }

    candidate = model["signal"]
    direction = "BUY" if candidate == "LONG" else "SELL" if candidate == "SHORT" else "WAIT"
    if direction == "WAIT":
        return {
            "signal": "WAIT",
            "reason": "Kitty model did not produce a directional class",
            "model_actionable": False,
            "candidate_signal": model["candidate_signal"],
            "confidence": model["confidence"],
        }

    data = dict(mtf_data) if isinstance(mtf_data, dict) else {}
    mtf_direction = str(data.get("mtf_signal") or "").strip().upper()
    if mtf_direction and mtf_direction != direction:
        return {
            "signal": "WAIT",
            "reason": "Kitty model direction conflicts with multi-timeframe direction",
            "model_actionable": True,
            "candidate_signal": candidate,
            "confidence": model["confidence"],
        }

    data["mtf_signal"] = direction
    mtf = normalize_mtf_watch_signal(data, late_entry)
    return {
        "signal": mtf["signal"],
        "reason": mtf["reason"],
        "model_actionable": True,
        "candidate_signal": candidate,
        "confidence": model["confidence"],
    }
