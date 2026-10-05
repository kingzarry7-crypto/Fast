"""Central risk policy for the KING ZARRY Action Gateway.

The policy is deliberately small and deterministic. The workflow planner may
describe work, but this module is the final risk classification authority for
external actions.
"""
from __future__ import annotations

import math
from typing import Any, Dict

RISK_GREEN = "green"
RISK_YELLOW = "yellow"
RISK_RED = "red"

ACTION_RISK = {
    "account.read": RISK_GREEN,
    "trade.place_order": RISK_RED,
    "trade.close_position": RISK_RED,
    "whatsapp.send": RISK_YELLOW,
}

APPROVAL_REQUIRED = {RISK_YELLOW, RISK_RED}


def risk_for_action(action_type: str) -> str:
    value = ACTION_RISK.get(str(action_type or "").strip())
    if not value:
        raise ValueError("unsupported action type")
    return value


def requires_approval(action_type: str) -> bool:
    return risk_for_action(action_type) in APPROVAL_REQUIRED


def validate_payload(action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate action shape without contacting an external service."""
    action_type = str(action_type or "").strip()
    data = dict(payload or {})
    risk = risk_for_action(action_type)

    if action_type.startswith("trade."):
        quantity = data.get("quantity")
        if quantity is not None:
            try:
                quantity = float(quantity)
            except (TypeError, ValueError):
                raise ValueError("trade quantity must be numeric")
            if not math.isfinite(quantity) or quantity <= 0:
                raise ValueError("trade quantity must be greater than zero")
            data["quantity"] = quantity

    if action_type == "whatsapp.send":
        if not str(data.get("to") or "").strip():
            raise ValueError("WhatsApp recipient is required")
        if not str(data.get("text") or "").strip():
            raise ValueError("WhatsApp message is required")

    data["_risk_level"] = risk
    data["_approval_required"] = requires_approval(action_type)
    return data
