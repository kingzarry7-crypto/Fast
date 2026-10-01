"""
KING ZARRY AI — Risk Guardian Agent.

A separate pre-delivery safety layer for Agent signals.
It does not generate trades. It challenges a proposed setup using
already-available market/MTF/verification data and returns:
APPROVE, HOLD, or BLOCK.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

APPROVED_SYMBOLS = {
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XAU/USD",
    "UNI/USD",
}


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    text = str(value).replace(",", "")
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not nums:
        return None
    try:
        if len(nums) >= 2 and any(sep in text for sep in ("-", "to", "–", "—")):
            return (float(nums[0]) + float(nums[1])) / 2.0
        return float(nums[0])
    except Exception:
        return None


def _rr(analysis: Dict[str, Any]) -> Optional[float]:
    direction = str(analysis.get("signal") or "").upper().strip()
    entry = _num(analysis.get("entry") or analysis.get("price"))
    sl = _num(analysis.get("stop_loss"))
    tp1 = _num(analysis.get("tp1"))
    if direction not in {"BUY", "SELL"} or None in (entry, sl, tp1):
        return None
    if direction == "BUY":
        risk = entry - sl
        reward = tp1 - entry
    else:
        risk = sl - entry
        reward = entry - tp1
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def evaluate_risk_guardian(
    symbol: str,
    analysis: Dict[str, Any],
    verification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Challenge a candidate setup before it is persisted/pushed.

    APPROVE = no critical warning detected.
    HOLD    = setup may be valid, but current conditions need another check.
    BLOCK   = do not register or deliver the setup.
    """
    normalized = str(symbol or "").upper().strip()
    verification = verification or {}
    checks: List[Dict[str, Any]] = []
    reasons: List[str] = []
    hard_block = False
    hold = False

    if normalized not in APPROVED_SYMBOLS:
        return {
            "status": "BLOCK",
            "approved": False,
            "symbol": normalized,
            "reasons": ["symbol is outside the approved Agent delivery universe"],
            "checks": [{"name": "symbol_allowlist", "ok": False, "severity": "BLOCK"}],
        }

    signal = str(analysis.get("signal") or "").upper().strip()
    if signal not in {"BUY", "SELL"}:
        return {
            "status": "BLOCK",
            "approved": False,
            "symbol": normalized,
            "reasons": ["no actionable direction"],
            "checks": [{"name": "direction", "ok": False, "severity": "BLOCK"}],
        }
    checks.append({"name": "direction", "ok": True, "severity": "PASS", "value": signal})

    if not bool(analysis.get("data_ok", True)):
        hard_block = True
        reasons.append("market data is unavailable or incomplete")
        checks.append({"name": "data_quality", "ok": False, "severity": "BLOCK"})
    else:
        checks.append({"name": "data_quality", "ok": True, "severity": "PASS"})

    entry_quality = str(analysis.get("entry_quality") or "").upper().strip()
    late = bool(analysis.get("late_entry")) or entry_quality in {"LATE", "RISKY"}
    if late:
        hard_block = True
        reasons.append(
            str(analysis.get("late_entry_reason") or "entry is late or risky")[:220]
        )
        checks.append({"name": "entry_timing", "ok": False, "severity": "BLOCK", "value": entry_quality or "LATE"})
    else:
        checks.append({"name": "entry_timing", "ok": True, "severity": "PASS", "value": entry_quality or "OK"})

    news_risk = str(analysis.get("news_risk") or "LOW").upper().strip()
    if news_risk == "EXTREME":
        hard_block = True
        reasons.append("extreme news risk")
        checks.append({"name": "news_risk", "ok": False, "severity": "BLOCK", "value": news_risk})
    elif news_risk == "HIGH":
        hold = True
        reasons.append("high news risk requires confirmation before delivery")
        checks.append({"name": "news_risk", "ok": False, "severity": "HOLD", "value": news_risk})
    else:
        checks.append({"name": "news_risk", "ok": True, "severity": "PASS", "value": news_risk})

    volatility = str(analysis.get("volatility") or "").upper()
    if "EXTREME" in volatility:
        hard_block = True
        reasons.append("extreme volatility")
        checks.append({"name": "volatility", "ok": False, "severity": "BLOCK", "value": volatility})
    elif "HIGH" in volatility:
        hold = True
        reasons.append("high volatility")
        checks.append({"name": "volatility", "ok": False, "severity": "HOLD", "value": volatility})
    else:
        checks.append({"name": "volatility", "ok": True, "severity": "PASS", "value": volatility or "UNKNOWN"})

    structure = str(analysis.get("structure") or "").upper()
    if (signal == "BUY" and structure == "BEARISH") or (signal == "SELL" and structure == "BULLISH"):
        hold = True
        reasons.append(f"market structure conflicts with {signal}")
        checks.append({"name": "structure", "ok": False, "severity": "HOLD", "value": structure})
    else:
        checks.append({"name": "structure", "ok": True, "severity": "PASS", "value": structure or "UNKNOWN"})

    verification_decision = str(verification.get("decision") or "").upper()
    verification_score = _num(verification.get("score"))
    verification_threshold = _num(verification.get("threshold")) or 65.0
    if verification_decision != "SIGNAL":
        hard_block = True
        reasons.append("Agent V2 verification did not approve the setup")
        checks.append({
            "name": "agent_v2",
            "ok": False,
            "severity": "BLOCK",
            "value": verification_decision or "UNKNOWN",
            "score": verification_score,
        })
    else:
        checks.append({
            "name": "agent_v2",
            "ok": True,
            "severity": "PASS",
            "value": verification_score,
        })

    if verification_score is not None and verification_score < verification_threshold:
        hard_block = True
        reasons.append(
            f"verification score {verification_score:.0f} is below threshold {verification_threshold:.0f}"
        )
        checks.append({
            "name": "verification_score",
            "ok": False,
            "severity": "BLOCK",
            "value": verification_score,
        })

    mtf = analysis.get("mtf_data") or analysis.get("mtf")
    if isinstance(mtf, dict):
        if bool(mtf.get("conflict")):
            hold = True
            reasons.append("multi-timeframe conflict detected")
            checks.append({"name": "mtf_conflict", "ok": False, "severity": "HOLD"})
        else:
            checks.append({"name": "mtf_conflict", "ok": True, "severity": "PASS"})

        mtf_signal = str(mtf.get("mtf_signal") or "").upper().strip()
        if mtf_signal in {"BUY", "SELL"} and mtf_signal != signal:
            hard_block = True
            reasons.append(f"MTF consensus conflicts with {signal}")
            checks.append({
                "name": "mtf_consensus",
                "ok": False,
                "severity": "BLOCK",
                "value": mtf_signal,
            })
        elif mtf_signal == signal:
            checks.append({"name": "mtf_consensus", "ok": True, "severity": "PASS", "value": mtf_signal})

        ai_verdict = str(mtf.get("ai_verdict") or "").upper()
        if ai_verdict.startswith("REJECT"):
            hard_block = True
            reasons.append("AI multi-timeframe cross-check rejected the setup")
            checks.append({"name": "ai_crosscheck", "ok": False, "severity": "BLOCK", "value": ai_verdict})
        elif ai_verdict.startswith("CONFIRM"):
            checks.append({"name": "ai_crosscheck", "ok": True, "severity": "PASS", "value": ai_verdict})

    rr = _rr(analysis)
    if rr is None:
        hard_block = True
        reasons.append("risk/reward cannot be validated from the supplied entry, SL and TP1")
        checks.append({"name": "risk_reward", "ok": False, "severity": "BLOCK"})
    elif rr < 1.0:
        hard_block = True
        reasons.append(f"risk/reward is only {rr:.2f}R")
        checks.append({"name": "risk_reward", "ok": False, "severity": "BLOCK", "value": round(rr, 2)})
    elif rr < 1.2:
        hold = True
        reasons.append(f"risk/reward is thin at {rr:.2f}R")
        checks.append({"name": "risk_reward", "ok": False, "severity": "HOLD", "value": round(rr, 2)})
    else:
        checks.append({"name": "risk_reward", "ok": True, "severity": "PASS", "value": round(rr, 2)})

    status = "BLOCK" if hard_block else "HOLD" if hold else "APPROVE"
    return {
        "status": status,
        "approved": status == "APPROVE",
        "symbol": normalized,
        "signal": signal,
        "reasons": reasons[:8],
        "checks": checks,
        "risk_reward": round(rr, 2) if rr is not None else None,
        "verification_score": verification_score,
    }
