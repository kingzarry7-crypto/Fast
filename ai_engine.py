import os
import re
import io
import json
import base64
import logging
import math
import time
from typing import Optional, Tuple, List, Dict, Any
import requests

logger = logging.getLogger("ai_engine")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

# ================= SECURITY & FAILOVER HELPERS =================
def _redact_secrets(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"([?&]apikey=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"([?&]api_key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    return text

def _sanitize_exception_message(exc: Exception) -> str:
    try:
        msg = str(exc)
    except Exception:
        msg = "provider error"
    return _redact_secrets(msg)

def _is_rate_limit_error(status_code: Optional[int], text: str) -> bool:
    if status_code == 429:
        return True
    low = text.lower()
    return any(k in low for k in ["429", "too many requests", "rate limit", "rate_limit", "quota exceeded", "quota_exceeded", "resource_exhausted", "resource exhausted"])

def _is_transient_error(status_code: Optional[int], text: str) -> bool:
    if status_code in (500, 502, 503, 504):
        return True
    low = text.lower()
    return any(k in low for k in ["timeout", "timed out", "connection reset", "connection aborted", "temporarily unavailable", "502", "503", "504", "500 internal", "bad gateway", "service unavailable"])

class ProviderRateLimitError(RuntimeError):
    pass

class ProviderTransientError(RuntimeError):
    pass

# Env
GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
GROQ_MODEL = clean_env_str(os.getenv("GROQ_MODEL"), "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = clean_env_str(os.getenv("GROQ_VISION_MODEL"), "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_URL = clean_env_str(os.getenv("GROQ_URL"), "https://api.groq.com/openai/v1/chat/completions")

GEMINI_API_KEY = clean_env_str(os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = clean_env_str(os.getenv("GEMINI_MODEL"), "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)
OPENROUTER_URL = clean_env_str(
    os.getenv("OPENROUTER_URL"),
    "https://openrouter.ai/api/v1/chat/completions",
)

OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_MODEL = OPENROUTER_MODEL
OPENAI_URL = OPENROUTER_URL

XAI_API_KEY = clean_env_str(os.getenv("XAI_API_KEY") or os.getenv("GROQ_API_KEY"))
XAI_MODEL = clean_env_str(os.getenv("XAI_MODEL") or os.getenv("GROK_MODEL"), "grok-4")
XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL") or os.getenv("GROQ_BASE_URL"), "https://api.x.ai/v1/chat/completions")
if "x.ai" not in XAI_URL and XAI_API_KEY:
    if "groq" not in XAI_URL.lower():
        XAI_URL = "https://api.x.ai/v1/chat/completions"
    else:
        XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL"), "https://api.x.ai/v1/chat/completions")

AI_PROVIDER = clean_env_str(os.getenv("AI_PROVIDER"), "AUTO").upper()

ELEVENLABS_API_KEY = clean_env_str(os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = clean_env_str(os.getenv("ELEVENLABS_VOICE_ID"), "hpp4J3VqNfWAUOO0d1Us")
# Support both ELEVENLABS_MODEL_ID and legacy ELEVENLABS_MODEL
ELEVENLABS_MODEL_ID = clean_env_str(
    os.getenv("ELEVENLABS_MODEL_ID") or os.getenv("ELEVENLABS_MODEL"),
    "eleven_v3"
)
# Preserve compatibility: also expose ELEVENLABS_MODEL alias
ELEVENLABS_MODEL = ELEVENLABS_MODEL_ID

SYSTEM_PROMPT = """
You are King Zarry AI 👑 - Advanced Trading & Intelligence Assistant.

Personality:
- Confident, sharp, professional trader and AI assistant
- Direct, no fluff, actionable
- Never reveal internal chain-of-thought
- Never invent live prices, news, or indicators
- If data missing, say DATA UNAVAILABLE

Trading Rules:
- Always use risk management warnings
- Never guarantee profits
- Use structured analysis
- Consider multi-timeframe when available

Memory:
- Remember user's preferred assets, timeframe, risk
- Keep memory isolated per user_id
"""

def clean_ai_response(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()

# =========================================================
# 🔒 STRICT MARKET VALIDATION LAYER - NEW
# =========================================================
MTF_WEIGHTS = {"4h": 0.35, "1h": 0.30, "15m": 0.25, "5m": 0.10}

def _safe_float(v, default=None):
    try:
        if v is None:
            return default
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return default
        return fv
    except Exception:
        return default

def _is_valid_number(v):
    if v is None:
        return False
    try:
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return False
        if fv == 0:
            # 0 can be valid for some fields but not for price/ATR etc
            return True
        return True
    except Exception:
        return False

def _is_valid_price(v):
    fv = _safe_float(v)
    if fv is None:
        return False
    if fv <= 0:
        return False
    if math.isnan(fv) or math.isinf(fv):
        return False
    return True

def validate_data_integrity(market: Dict[str, Any]) -> Tuple[bool, str]:
    """Check required fields, return (ok, missing_reason)"""
    if not market:
        return False, "Market data is empty"
    price = market.get("price") or market.get("current_price")
    if not _is_valid_price(price):
        return False, f"Invalid price: {price}"
    atr = market.get("atr")
    if atr is not None:
        fv = _safe_float(atr)
        if fv is None or fv <= 0 or math.isnan(fv) or math.isinf(fv):
            return False, f"Invalid ATR: {atr}"
    for key in ["ema9", "ema21", "ema50"]:
        if key in market and market[key] is not None:
            fv = _safe_float(market[key])
            if fv is None or fv <= 0:
                return False, f"Invalid {key}: {market[key]}"
    # entry_low/high can be None for WAIT but if direction BUY/SELL they must be valid
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    if direction in ("BUY", "SELL"):
        el = market.get("entry_low")
        eh = market.get("entry_high")
        sl = market.get("stop_loss")
        if not _is_valid_price(el) or not _is_valid_price(eh):
            return False, f"Invalid entry zone: {el}-{eh}"
        if not _is_valid_price(sl):
            return False, f"Invalid stop_loss: {sl}"
        # TPs can be None but if present must be valid
        for tp_key in ["tp1", "tp2", "tp3"]:
            tp = market.get(tp_key)
            if tp is not None and not _is_valid_price(tp):
                return False, f"Invalid {tp_key}: {tp}"
    return True, ""

def validate_ema_alignment_raw(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use RAW numeric values, not rounded display.
    Returns dict with alignment status.
    """
    ema9 = _safe_float(market.get("ema9"))
    ema21 = _safe_float(market.get("ema21"))
    ema50 = _safe_float(market.get("ema50"))
    price = _safe_float(market.get("price") or market.get("current_price"))
    if None in (ema9, ema21, ema50, price) or price <= 0:
        return {"alignment": "UNKNOWN", "bullish": False, "bearish": False, "flat": False, "separation_pct": 0, "reason": "Missing EMA data"}

    # Separation thresholds: EMA flat if all within 0.08% of price or within 0.15 ATR
    atr = _safe_float(market.get("atr"), 0)
    # Use price-based pct threshold
    price_threshold = price * 0.0008  # 0.08%
    # If ATR available, use max of price_threshold and atr*0.15
    if atr and atr > 0:
        threshold = max(price_threshold, atr * 0.15)
    else:
        threshold = price_threshold

    diff_9_21 = abs(ema9 - ema21)
    diff_21_50 = abs(ema21 - ema50)
    diff_9_50 = abs(ema9 - ema50)

    # FLAT check
    if diff_9_21 < threshold and diff_21_50 < threshold and diff_9_50 < threshold:
        return {
            "alignment": "FLAT",
            "bullish": False,
            "bearish": False,
            "flat": True,
            "separation_pct": (diff_9_50 / price * 100) if price else 0,
            "reason": f"EMA FLAT / NO CLEAR ALIGNMENT (EMA9 {ema9:.4f} ≈ EMA21 {ema21:.4f} ≈ EMA50 {ema50:.4f}, spread {diff_9_50/price*100:.3f}% < threshold)"
        }

    # Bullish alignment: ema9 > ema21 > ema50 with meaningful separation
    if ema9 > ema21 and ema21 > ema50:
        # Require ema9 above ema21 by at least 30% of threshold to be meaningful
        if diff_9_21 >= threshold * 0.3 and diff_21_50 >= threshold * 0.3:
            return {
                "alignment": "BULLISH_ALIGNED",
                "bullish": True,
                "bearish": False,
                "flat": False,
                "separation_pct": (diff_9_50 / price * 100),
                "reason": f"Bullish EMA alignment confirmed: EMA9 {ema9:.4f} > EMA21 {ema21:.4f} > EMA50 {ema50:.4f} (spread {diff_9_50/price*100:.3f}%)"
            }
        else:
            return {
                "alignment": "BULLISH_WEAK",
                "bullish": False,
                "bearish": False,
                "flat": False,
                "separation_pct": (diff_9_50 / price * 100),
                "reason": f"EMA bullish order but separation too small ({diff_9_50/price*100:.3f}%) - not counted as strong alignment, EMA crossover not confirmed"
            }

    if ema9 < ema21 and ema21 < ema50:
        if diff_9_21 >= threshold * 0.3 and diff_21_50 >= threshold * 0.3:
            return {
                "alignment": "BEARISH_ALIGNED",
                "bullish": False,
                "bearish": True,
                "flat": False,
                "separation_pct": (diff_9_50 / price * 100),
                "reason": f"Bearish EMA alignment confirmed: EMA9 {ema9:.4f} < EMA21 {ema21:.4f} < EMA50 {ema50:.4f} (spread {abs(diff_9_50)/price*100:.3f}%)"
            }
        else:
            return {
                "alignment": "BEARISH_WEAK",
                "bullish": False,
                "bearish": False,
                "flat": False,
                "separation_pct": (abs(diff_9_50) / price * 100),
                "reason": f"EMA bearish order but separation too small ({abs(diff_9_50)/price*100:.3f}%) - EMA crossover not confirmed"
            }

    # Mixed
    return {
        "alignment": "MIXED",
        "bullish": False,
        "bearish": False,
        "flat": False,
        "separation_pct": (diff_9_50 / price * 100),
        "reason": f"EMA mixed alignment: EMA9 {ema9:.4f}, EMA21 {ema21:.4f}, EMA50 {ema50:.4f} - no clear trend"
    }

def detect_countertrend(market: Dict[str, Any]) -> Dict[str, Any]:
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    h4 = (market.get("h4_trend") or "").upper()
    h1 = (market.get("h1_trend") or "").upper()
    if direction not in ("BUY", "SELL"):
        return {"is_countertrend": False, "type": "NONE", "penalty": 0, "reason": "No directional trade"}

    is_ct = False
    penalty = 0
    reasons = []
    if direction == "BUY" and h4 == "BEARISH":
        is_ct = True
        penalty += 25
        reasons.append(f"4H BEARISH vs BUY - countertrend")
        if h1 == "BEARISH":
            penalty += 10
            reasons.append("1H also BEARISH - strong countertrend, double HTF disagreement")
    elif direction == "SELL" and h4 == "BULLISH":
        is_ct = True
        penalty += 25
        reasons.append(f"4H BULLISH vs SELL - countertrend")
        if h1 == "BULLISH":
            penalty += 10
            reasons.append("1H also BULLISH - strong countertrend, double HTF disagreement")
    elif direction == "BUY" and h1 == "BEARISH" and h4 != "BULLISH":
        is_ct = True
        penalty += 12
        reasons.append("1H BEARISH vs BUY - partial countertrend")
    elif direction == "SELL" and h1 == "BULLISH" and h4 != "BEARISH":
        is_ct = True
        penalty += 12
        reasons.append("1H BULLISH vs SELL - partial countertrend")

    return {
        "is_countertrend": is_ct,
        "type": "COUNTERTREND BUY" if is_ct and direction == "BUY" else "COUNTERTREND SELL" if is_ct else "WITH_TREND",
        "penalty": penalty,
        "reason": "; ".join(reasons) if reasons else "With-trend: HTF aligns"
    }

def calculate_sr_proximity(market: Dict[str, Any]) -> Dict[str, Any]:
    price = _safe_float(market.get("price") or market.get("current_price"))
    support = _safe_float(market.get("support") or market.get("nearest_support") or market.get("major_support"))
    resistance = _safe_float(market.get("resistance") or market.get("nearest_resistance") or market.get("major_resistance"))
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    atr = _safe_float(market.get("atr"))

    if price is None or price <= 0:
        return {"distance_to_support_pct": None, "distance_to_resistance_pct": None, "penalty": 0, "flags": [], "reason": "Invalid price for SR check"}

    dist_sup_pct = None
    dist_res_pct = None
    if support and support > 0:
        dist_sup_pct = (price - support) / price * 100 if price != 0 else None
    if resistance and resistance > 0:
        dist_res_pct = (resistance - price) / price * 100 if price != 0 else None

    penalty = 0
    flags = []
    reasons = []

    if direction == "BUY":
        if dist_res_pct is not None:
            if dist_res_pct < 0.15:
                penalty += 25
                flags.append("RESISTANCE_BREAK_REQUIRED")
                reasons.append(f"Price extremely close to resistance ({dist_res_pct:.3f}% away) - almost no upside room, RESISTANCE BREAK REQUIRED")
            elif dist_res_pct < 0.35:
                penalty += 15
                flags.append("CLOSE_TO_RESISTANCE")
                reasons.append(f"Price close to resistance ({dist_res_pct:.3f}% away) - limited upside room")
            elif dist_res_pct < 0.7:
                penalty += 7
                reasons.append(f"Price moderately close to resistance ({dist_res_pct:.3f}% away)")
        # Check TP1 beyond resistance
        tp1 = _safe_float(market.get("tp1"))
        if tp1 and resistance and tp1 > resistance * 1.001:
            flags.append("TP1_BEYOND_RESISTANCE")
            reasons.append(f"TP1 {tp1} beyond resistance {resistance} - RESISTANCE BREAK REQUIRED for full target")
            penalty += 8
    elif direction == "SELL":
        if dist_sup_pct is not None:
            if dist_sup_pct < 0.15:
                penalty += 25
                flags.append("SUPPORT_BREAK_REQUIRED")
                reasons.append(f"Price extremely close to support ({dist_sup_pct:.3f}% away) - almost no downside room, SUPPORT BREAK REQUIRED")
            elif dist_sup_pct < 0.35:
                penalty += 15
                flags.append("CLOSE_TO_SUPPORT")
                reasons.append(f"Price close to support ({dist_sup_pct:.3f}% away) - limited downside room")
            elif dist_sup_pct < 0.7:
                penalty += 7
                reasons.append(f"Price moderately close to support ({dist_sup_pct:.3f}% away)")
        tp1 = _safe_float(market.get("tp1"))
        if tp1 and support and tp1 < support * 0.999:
            flags.append("TP1_BEYOND_SUPPORT")
            reasons.append(f"TP1 {tp1} beyond support {support} - SUPPORT BREAK REQUIRED")
            penalty += 8

    return {
        "distance_to_support_pct": dist_sup_pct,
        "distance_to_resistance_pct": dist_res_pct,
        "penalty": penalty,
        "flags": flags,
        "reason": "; ".join(reasons) if reasons else "SR proximity acceptable"
    }

def calculate_entry_status_strict(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strict entry status using ORIGINAL daily plan entry zone.
    Never moves entry to current price.
    """
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    entry_low = _safe_float(market.get("entry_low"))
    entry_high = _safe_float(market.get("entry_high"))
    current_price = _safe_float(market.get("price") or market.get("current_price") or market.get("fresh_price"))
    atr = _safe_float(market.get("atr"))

    if direction not in ("BUY", "SELL"):
        return {"status": "NO_TRADE", "label": "NO TRADE", "missed": False, "late": False, "reason": "No directional trade - WAIT"}

    if None in (entry_low, entry_high, current_price):
        return {"status": "UNKNOWN", "label": "UNKNOWN", "missed": False, "late": False, "reason": "Missing entry zone or current price - cannot determine entry status"}

    low = min(entry_low, entry_high)
    high = max(entry_low, entry_high)
    entry_mid = (low + high) / 2

    # For BUY: ideal entry is low to mid of zone, not upper edge
    # For SELL: ideal is high to mid

    if direction == "BUY":
        # Inside zone
        if low <= current_price <= high:
            # How far inside? If at upper edge (within 15% of top), not EARLY
            zone_size = high - low
            if zone_size > 0:
                position_pct = (current_price - low) / zone_size  # 0=bottom, 1=top
                if position_pct >= 0.85:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY - UPPER EDGE", "missed": False, "late": False, "reason": f"Price {current_price} at upper edge of entry zone {low}-{high} ({position_pct*100:.0f}% through zone) - still valid but not EARLY"}
                elif position_pct >= 0.4:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside entry zone {low}-{high} - good entry window"}
                else:
                    return {"status": "EARLY", "label": "EARLY", "missed": False, "late": False, "reason": f"Price {current_price} in lower part of entry zone {low}-{high} - early entry opportunity"}
            else:
                return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside entry zone"}

        # Above zone
        if current_price > high:
            distance_atr = (current_price - high) / atr if atr and atr > 0 else (current_price - high) / current_price * 100
            if atr and atr > 0:
                if distance_atr > 2.5:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price {current_price} moved beyond entry zone {low}-{high} by {distance_atr:.1f} ATR - ENTRY MISSED, original zone preserved, do not chase"}
                elif distance_atr > 1.0:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {current_price} above entry zone {low}-{high} by {distance_atr:.1f} ATR - LATE entry, reduced edge"}
                else:
                    return {"status": "LATE", "label": "LATE - JUST ABOVE ZONE", "missed": False, "late": True, "reason": f"Price {current_price} just above entry zone {low}-{high} - late but still near"}
            else:
                # fallback pct
                pct = (current_price - high) / high * 100 if high != 0 else 0
                if pct > 0.8:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price moved {pct:.2f}% beyond entry - ENTRY MISSED"}
                else:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {pct:.2f}% above entry zone - late"}

        # Below zone - waiting for pullback
        if current_price < low:
            distance_atr = (low - current_price) / atr if atr and atr > 0 else 0
            return {"status": "EARLY", "label": "WAITING FOR PULLBACK", "missed": False, "late": False, "reason": f"Price {current_price} below entry zone {low}-{high}, waiting for pullback into zone - EARLY stage"}

    else:  # SELL
        if low <= current_price <= high:
            zone_size = high - low
            if zone_size > 0:
                position_pct = (high - current_price) / zone_size  # 0=top, 1=bottom inverted for SELL logic? Actually for SELL upper is better? Keep similar
                # For SELL, entry zone top is resistance side, bottom is deeper
                # If price at lower edge (near bottom), it's late for SELL
                lower_position = (current_price - low) / zone_size
                if lower_position <= 0.15:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY - LOWER EDGE", "missed": False, "late": False, "reason": f"Price {current_price} at lower edge of SELL zone {low}-{high} - still valid but not early"}
                else:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside SELL entry zone {low}-{high} - good entry window"}
            else:
                return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price inside SELL zone"}

        if current_price < low:
            distance_atr = (low - current_price) / atr if atr and atr > 0 else 0
            if atr and atr > 0:
                if distance_atr > 2.5:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price {current_price} moved below SELL zone {low}-{high} by {distance_atr:.1f} ATR - ENTRY MISSED"}
                elif distance_atr > 1.0:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {current_price} below SELL zone by {distance_atr:.1f} ATR - LATE"}
                else:
                    return {"status": "LATE", "label": "LATE - JUST BELOW ZONE", "missed": False, "late": True, "reason": f"Price just below SELL zone"}
            else:
                pct = (low - current_price) / low * 100 if low != 0 else 0
                if pct > 0.8:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price moved {pct:.2f}% beyond SELL entry - MISSED"}
                else:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price below SELL zone - late"}

        if current_price > high:
            return {"status": "EARLY", "label": "WAITING FOR BOUNCE", "missed": False, "late": False, "reason": f"Price {current_price} above SELL zone {low}-{high}, waiting for bounce - EARLY stage"}

    return {"status": "UNKNOWN", "label": "UNKNOWN", "missed": False, "late": False, "reason": "Unable to determine entry status"}

def calculate_risk_reward_real(market: Dict[str, Any]) -> Dict[str, Any]:
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    entry_low = _safe_float(market.get("entry_low"))
    entry_high = _safe_float(market.get("entry_high"))
    sl = _safe_float(market.get("stop_loss"))
    tp1 = _safe_float(market.get("tp1"))
    tp2 = _safe_float(market.get("tp2"))
    tp3 = _safe_float(market.get("tp3"))

    if direction not in ("BUY", "SELL") or None in (entry_low, entry_high, sl):
        return {"valid": False, "risk": None, "reward1": None, "reward2": None, "reward3": None, "rr1": None, "rr2": None, "rr3": None, "reason": "Missing entry/SL for RR calculation"}

    entry = (entry_low + entry_high) / 2

    if direction == "BUY":
        risk = entry - sl
        if risk <= 0:
            return {"valid": False, "risk": risk, "reward1": None, "rr1": None, "reason": f"Invalid BUY risk: entry {entry} <= SL {sl} - SL must be below entry"}
        r1 = (tp1 - entry) if tp1 else None
        r2 = (tp2 - entry) if tp2 else None
        r3 = (tp3 - entry) if tp3 else None
        rr1 = (r1 / risk) if r1 and risk else None
        rr2 = (r2 / risk) if r2 and risk else None
        rr3 = (r3 / risk) if r3 and risk else None

        # Validate TPs above entry
        invalid = []
        if tp1 and tp1 <= entry:
            invalid.append(f"TP1 {tp1} not above entry {entry}")
        if tp2 and tp2 <= entry:
            invalid.append(f"TP2 {tp2} not above entry")
        if tp3 and tp3 <= entry:
            invalid.append(f"TP3 {tp3} not above entry")

        valid = len(invalid) == 0 and risk > 0
        return {"valid": valid, "risk": risk, "reward1": r1, "reward2": r2, "reward3": r3, "rr1": rr1, "rr2": rr2, "rr3": rr3, "reason": "; ".join(invalid) if invalid else f"BUY RR valid: risk {risk:.4f}, RR1 {rr1:.2f} RR2 {rr2:.2f} RR3 {rr3:.2f}" if rr1 else "RR invalid", "entry": entry}

    else:  # SELL
        risk = sl - entry
        if risk <= 0:
            return {"valid": False, "risk": risk, "reason": f"Invalid SELL risk: SL {sl} <= entry {entry} - SL must be above entry"}
        r1 = (entry - tp1) if tp1 else None
        r2 = (entry - tp2) if tp2 else None
        r3 = (entry - tp3) if tp3 else None
        rr1 = (r1 / risk) if r1 and risk else None
        rr2 = (r2 / risk) if r2 and risk else None
        rr3 = (r3 / risk) if r3 and risk else None

        invalid = []
        if tp1 and tp1 >= entry:
            invalid.append(f"TP1 {tp1} not below entry {entry}")
        if tp2 and tp2 >= entry:
            invalid.append(f"TP2 not below entry")
        if tp3 and tp3 >= entry:
            invalid.append(f"TP3 not below entry")

        valid = len(invalid) == 0 and risk > 0
        return {"valid": valid, "risk": risk, "reward1": r1, "reward2": r2, "reward3": r3, "rr1": rr1, "rr2": rr2, "rr3": rr3, "reason": "; ".join(invalid) if invalid else f"SELL RR valid: risk {risk:.4f}, RR1 {rr1:.2f} RR2 {rr2:.2f} RR3 {rr3:.2f}" if rr1 else "RR invalid", "entry": entry}

def calculate_realistic_confidence(market: Dict[str, Any], validations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Confidence must represent quality of COMPLETE setup, not just short TF agreement.
    """
    base_strength = _safe_float(market.get("setup_strength") or market.get("strength") or market.get("mtf_score") or 50, 50)
    # Start with base, but we will rebuild with independent evidence to avoid double counting
    confidence = base_strength

    penalties = []
    bonuses = []
    reasons = []

    # 1. HTF Priority - 4H major regime
    h4 = (market.get("h4_trend") or "").upper()
    h1 = (market.get("h1_trend") or "").upper()
    m15 = (market.get("m15_trend") or "").upper()
    m5 = (market.get("m5_trend") or "").upper()
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()

    # Count independent bullish/bearish evidences without double counting
    # Evidence buckets: HTF trend, M15 trend, structure, EMA alignment, RSI momentum, SR room

    # HTF disagreement penalty
    if direction == "BUY":
        if h4 == "BEARISH":
            confidence -= 25
            penalties.append(("HTF 4H BEARISH vs BUY", 25))
            reasons.append("4H bearish regime vs BUY - countertrend, confidence reduced")
        if h1 == "BEARISH":
            confidence -= 15
            penalties.append(("HTF 1H BEARISH vs BUY", 15))
            reasons.append("1H bearish vs BUY - partial HTF disagreement")
        if m15 == "BEARISH":
            confidence -= 10
            penalties.append(("M15 BEARISH vs BUY", 10))
    elif direction == "SELL":
        if h4 == "BULLISH":
            confidence -= 25
            penalties.append(("HTF 4H BULLISH vs SELL", 25))
            reasons.append("4H bullish regime vs SELL - countertrend, confidence reduced")
        if h1 == "BULLISH":
            confidence -= 15
            penalties.append(("HTF 1H BULLISH vs SELL", 15))
            reasons.append("1H bullish vs SELL - partial HTF disagreement")
        if m15 == "BULLISH":
            confidence -= 10
            penalties.append(("M15 BULLISH vs SELL", 10))

    # 2. Countertrend
    ct = validations.get("countertrend", {})
    if ct.get("is_countertrend"):
        # Already penalized above for HTF, but add extra if double HTF
        extra = ct.get("penalty", 0) - 25  # subtract already counted 4H
        if extra > 0:
            confidence -= extra
            penalties.append((ct.get("type"), extra))
        reasons.append(f"{ct.get('type')}: {ct.get('reason')}")

    # 3. EMA validation - use raw values
    ema_val = validations.get("ema", {})
    if ema_val.get("flat"):
        confidence -= 20
        penalties.append(("EMA FLAT", 20))
        reasons.append(ema_val.get("reason") + " - EMA signal not counted as strong confirmation")
    elif ema_val.get("alignment") in ("MIXED", "BULLISH_WEAK", "BEARISH_WEAK"):
        confidence -= 10
        penalties.append((f"EMA {ema_val.get('alignment')}", 10))
        reasons.append(ema_val.get("reason"))

    # 4. SR proximity
    sr = validations.get("sr", {})
    if sr.get("penalty", 0) > 0:
        confidence -= sr.get("penalty")
        penalties.append((f"SR proximity {sr.get('penalty')}", sr.get("penalty")))
        reasons.append(sr.get("reason"))

    # 5. Entry status
    entry = validations.get("entry", {})
    if entry.get("status") == "MISSED":
        confidence = 0
        penalties.append(("ENTRY MISSED", 100))
        reasons.append(entry.get("reason") + " - must return WAIT, do not chase price")
    elif entry.get("status") == "LATE":
        confidence -= 15
        penalties.append(("LATE ENTRY", 15))
        reasons.append(entry.get("reason"))
    elif "UPPER EDGE" in entry.get("label", "") or "LOWER EDGE" in entry.get("label", ""):
        confidence -= 5
        penalties.append(("ENTRY AT EDGE", 5))
        reasons.append(entry.get("reason") + " - not EARLY")

    # 6. Risk/Reward
    rr = validations.get("rr", {})
    if not rr.get("valid"):
        confidence -= 30
        penalties.append(("INVALID RR", 30))
        reasons.append(f"Risk/Reward invalid: {rr.get('reason')} - mathematically invalid setup")
    else:
        rr1 = rr.get("rr1")
        if rr1 is not None:
            if rr1 < 0.8:
                confidence -= 20
                penalties.append((f"Poor RR {rr1:.2f}", 20))
                reasons.append(f"Poor risk/reward RR1 {rr1:.2f} < 0.8 - insufficient edge")
            elif rr1 < 1.2:
                confidence -= 10
                penalties.append((f"Weak RR {rr1:.2f}", 10))
                reasons.append(f"Weak RR1 {rr1:.2f} - limited reward vs risk")

    # 7. Volatility
    vol_level = (market.get("volatility") or market.get("volatility_data", {}).get("level") if isinstance(market.get("volatility_data"), dict) else None)
    if isinstance(market.get("volatility_data"), dict):
        vol_level = market.get("volatility_data").get("level", vol_level)
    if vol_level == "EXTREME":
        confidence -= 15
        penalties.append(("VOLATILITY EXTREME", 15))
        reasons.append(f"Extreme volatility {market.get('atr')} - move may be over, reduces confidence")
    elif vol_level == "HIGH":
        confidence -= 5
        penalties.append(("VOLATILITY HIGH", 5))

    # 8. RSI reasonableness
    rsi = _safe_float(market.get("rsi"))
    if rsi is not None:
        if direction == "BUY" and rsi >= 75:
            confidence -= 12
            penalties.append((f"RSI overbought {rsi:.1f}", 12))
            reasons.append(f"RSI overbought {rsi:.1f} for BUY - exhaustion risk")
        elif direction == "BUY" and rsi >= 70:
            confidence -= 6
            penalties.append((f"RSI high {rsi:.1f}", 6))
        elif direction == "SELL" and rsi <= 25:
            confidence -= 12
            penalties.append((f"RSI oversold {rsi:.1f}", 12))
            reasons.append(f"RSI oversold {rsi:.1f} for SELL - exhaustion risk")
        elif direction == "SELL" and rsi <= 30:
            confidence -= 6
            penalties.append((f"RSI low {rsi:.1f}", 6))

    # 9. Exhaustion
    exh = market.get("exhaustion") or (market.get("exhaustion_data", {}).get("level") if isinstance(market.get("exhaustion_data"), dict) else None)
    if isinstance(market.get("exhaustion_data"), dict):
        exh = market.get("exhaustion_data").get("level", exh)
    if exh == "EXTREME":
        confidence -= 20
        penalties.append(("EXHAUSTION EXTREME", 20))
        reasons.append(f"Exhaustion EXTREME - {market.get('exhaustion_reason','move extended')}")
    elif exh == "HIGH":
        confidence -= 10
        penalties.append(("EXHAUSTION HIGH", 10))

    # 10. Late entry flag from market
    if market.get("late_entry"):
        confidence -= 12
        penalties.append(("LATE ENTRY FLAG", 12))
        reasons.append(f"Late entry flagged: {market.get('late_entry_reason','price extended')}")

    # 11. News risk
    news_risk = (market.get("news_risk") or "LOW").upper()
    if news_risk == "HIGH":
        confidence -= 15
        penalties.append(("NEWS HIGH", 15))
        reasons.append("News risk HIGH - reduce size, increase caution")
    elif news_risk == "EXTREME":
        confidence -= 30
        penalties.append(("NEWS EXTREME", 30))
        reasons.append("News risk EXTREME - high volatility expected, avoid new entries")

    # 12. MTF alignment
    align = (market.get("timeframe_alignment") or "").upper()
    if align == "MIXED":
        confidence -= 12
        penalties.append(("MTF MIXED", 12))
        reasons.append(f"Mixed MTF alignment (4H:{h4} 1H:{h1} 15M:{m15}) - wait for alignment")
    elif "STRONG" in align and direction in ("BUY","SELL"):
        # Bonus only if aligns with direction
        if (direction == "BUY" and "BULLISH" in align) or (direction == "SELL" and "BEARISH" in align):
            confidence += 5
            bonuses.append(("STRONG MTF ALIGNMENT", 5))
            reasons.append(f"Strong MTF alignment {align} supports {direction}")

    # 13. Structure support
    struct = (market.get("structure") or "").upper()
    if direction == "BUY" and struct == "BEARISH":
        confidence -= 12
        penalties.append(("STRUCTURE BEARISH vs BUY", 12))
        reasons.append(f"Market structure bearish vs BUY - structure does not support BUY")
    elif direction == "SELL" and struct == "BULLISH":
        confidence -= 12
        penalties.append(("STRUCTURE BULLISH vs SELL", 12))
        reasons.append(f"Market structure bullish vs SELL")

    # 14. Avoid double counting: ensure confidence not inflated by counting same bullish evidence 3 times
    # We already penalize heavily for disagreement, so cap bonuses

    # Clamp
    confidence = max(0, min(100, int(confidence)))

    # Countertrend cap: never allow normal countertrend to reach 90 HIGH
    if ct.get("is_countertrend"):
        # Check for strong evidence that regime invalidated
        strong_evidence = False
        # Evidence: confirmed structure break + EMA regime change + sustained momentum + multi-TF confirmation
        # Simplified: if M15 and 5M bullish, structure breakout true, EMA bullish aligned, and SR break
        breakout = market.get("breakout") or (market.get("structure_data", {}).get("breakout") if isinstance(market.get("structure_data"), dict) else False)
        breakdown = market.get("breakdown") or (market.get("structure_data", {}).get("breakdown") if isinstance(market.get("structure_data"), dict) else False)
        ema_bull = ema_val.get("bullish")
        ema_bear = ema_val.get("bearish")
        mtf_score = _safe_float(market.get("mtf_score"), 50)

        if direction == "BUY" and breakout and ema_bull and mtf_score >= 70:
            strong_evidence = True
        if direction == "SELL" and breakdown and ema_bear and mtf_score <= 30:
            strong_evidence = True

        if not strong_evidence:
            # Cap countertrend at 74 max unless strong evidence
            if confidence >= 90:
                confidence = 74
                reasons.append(f"Countertrend {direction} capped at 74/100 HIGH not allowed without strong evidence of HTF regime break")
            elif confidence >= 80:
                confidence = min(confidence, 74)
            # Additional penalty already applied
        else:
            # Even with strong evidence, cap at 84 unless exceptional
            if confidence >= 90:
                confidence = 84
                reasons.append(f"Countertrend {direction} with strong evidence but still capped at 84 - HTF disagreement reduces confidence")

    # Final interpretation
    if confidence >= 90:
        level = "EXCEPTIONAL"
    elif confidence >= 80:
        level = "STRONG"
    elif confidence >= 70:
        level = "GOOD"
    elif confidence >= 60:
        level = "MODERATE"
    elif confidence >= 50:
        level = "WEAK"
    else:
        level = "INSUFFICIENT"

    return {
        "confidence": confidence,
        "level": level,
        "penalties": penalties,
        "bonuses": bonuses,
        "reasons": reasons,
        "base_strength": base_strength
    }

def validate_market_signal(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    MAIN VALIDATION ENTRY POINT
    Flow: MARKET DATA -> DAILY PLAN -> VALIDATION -> FINAL SIGNAL
    Never invents new trade levels. Preserves daily plan.
    """
    # Preserve original
    original = dict(market) if market else {}

    # 1. Data integrity
    ok, missing = validate_data_integrity(market)
    if not ok:
        # DATA UNAVAILABLE case
        result = dict(original)
        result["signal"] = "WAIT"
        result["direction"] = "WAIT"
        result["plan_status"] = "WAIT"
        result["daily_plan_status"] = "WAIT"
        result["confidence"] = 0
        result["strength"] = 0
        result["setup_strength"] = 0
        result["reason"] = f"DATA UNAVAILABLE: {missing}"
        result["trigger_condition"] = f"DATA UNAVAILABLE: {missing}"
        result["entry_status"] = "DATA_UNAVAILABLE"
        result["entry_status_label"] = "DATA UNAVAILABLE"
        result["is_entry_missed"] = False
        result["countertrend_status"] = "NONE"
        result["validation_passed"] = False
        result["validation_errors"] = [missing]
        return result

    # 2. Gather validations
    ema_val = validate_ema_alignment_raw(market)
    ct = detect_countertrend(market)
    sr = calculate_sr_proximity(market)
    entry = calculate_entry_status_strict(market)
    rr = calculate_risk_reward_real(market)

    validations = {
        "ema": ema_val,
        "countertrend": ct,
        "sr": sr,
        "entry": entry,
        "rr": rr,
        "data_ok": True
    }

    # 3. Confidence
    conf_result = calculate_realistic_confidence(market, validations)

    # 4. Daily plan status check
    plan_status = (market.get("plan_status") or market.get("daily_plan_status") or market.get("status") or "ACTIVE").upper()
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()

    # 5. Decide final signal - downgrade to WAIT if needed
    final_signal = direction
    final_reason = market.get("reason") or market.get("trigger_condition") or ""
    downgrade_reasons = []

    # Check for ENTRY MISSED - must preserve original zone, report MISSED
    if entry.get("status") == "MISSED":
        final_signal = "WAIT"
        downgrade_reasons.append(entry.get("reason"))
        # Preserve original entry zone - do not move
        # final_reason = ENTRY MISSED

    # Check for invalid RR
    if not rr.get("valid"):
        final_signal = "WAIT"
        downgrade_reasons.append(rr.get("reason"))

    # Check for low confidence
    if conf_result["confidence"] < 50:
        final_signal = "WAIT"
        downgrade_reasons.append(f"Confidence too low {conf_result['confidence']}/100 - insufficient edge ({conf_result['level']})")

    # Check for extreme news
    news_risk = (market.get("news_risk") or "LOW").upper()
    if news_risk == "EXTREME" and direction in ("BUY", "SELL"):
        # Only allow if MTF score extremely strong
        mtf_score = _safe_float(market.get("mtf_score"), 50)
        if not (mtf_score >= 95 or mtf_score <= 5):
            final_signal = "WAIT"
            downgrade_reasons.append(f"News risk EXTREME - avoid new entries, wait for volatility to settle (MTF {mtf_score})")

    # Check for flat EMA with BUY/SELL
    if ema_val.get("flat") and direction in ("BUY", "SELL"):
        # If EMA flat, confidence already reduced, but if still BUY/SELL, require additional evidence
        if conf_result["confidence"] < 65:
            final_signal = "WAIT"
            downgrade_reasons.append(ema_val.get("reason") + " - no clear EMA alignment, insufficient edge")

    # Check SR proximity extreme
    if "RESISTANCE_BREAK_REQUIRED" in sr.get("flags", []) and direction == "BUY":
        if conf_result["confidence"] < 70:
            final_signal = "WAIT"
            downgrade_reasons.append(sr.get("reason"))
    if "SUPPORT_BREAK_REQUIRED" in sr.get("flags", []) and direction == "SELL":
        if conf_result["confidence"] < 70:
            final_signal = "WAIT"
            downgrade_reasons.append(sr.get("reason"))

    # Check for INVALIDATED plan from market.py
    if plan_status == "INVALIDATED":
        final_signal = "WAIT"
        downgrade_reasons.append(f"Daily plan INVALIDATED: {market.get('invalidation_reason') or market.get('reason') or 'thesis broken'} - WAIT for new confirmed setup, do not flip opposite")

    # Build final result - preserve original daily plan fields
    result = dict(original)  # start from market data

    # Preserve critical daily plan fields - never overwrite
    for key in ["daily_plan_id", "trading_date", "entry_low", "entry_high", "entry_zone", "stop_loss", "tp1", "tp2", "tp3", "take_profit", "original_price", "created_at"]:
        if key in original:
            result[key] = original[key]

    # Update validated fields
    result["signal"] = final_signal
    result["direction"] = final_signal
    result["confidence"] = conf_result["confidence"]
    result["strength"] = conf_result["confidence"]  # strength = confidence for consistency
    result["setup_strength"] = conf_result["confidence"]
    result["confidence_level"] = conf_result["level"]

    # Entry status strict
    result["entry_status"] = entry.get("status")
    result["entry_status_label"] = entry.get("label")
    result["entry_status_reason"] = entry.get("reason")
    result["is_entry_missed"] = entry.get("missed", False)
    result["is_entry_late"] = entry.get("late", False)

    # Countertrend
    result["countertrend_status"] = ct.get("type") if ct.get("is_countertrend") else "WITH_TREND"
    result["is_countertrend"] = ct.get("is_countertrend", False)
    result["countertrend_penalty"] = ct.get("penalty", 0)
    result["countertrend_reason"] = ct.get("reason")

    # EMA validation
    result["ema_alignment_validated"] = ema_val.get("alignment")
    result["ema_validation_reason"] = ema_val.get("reason")
    result["ema_separation_pct"] = ema_val.get("separation_pct")

    # SR
    result["sr_proximity_penalty"] = sr.get("penalty", 0)
    result["sr_flags"] = sr.get("flags", [])
    result["sr_reason"] = sr.get("reason")
    result["distance_to_support_pct"] = sr.get("distance_to_support_pct")
    result["distance_to_resistance_pct"] = sr.get("distance_to_resistance_pct")

    # RR
    result["risk_reward_valid"] = rr.get("valid")
    result["risk_reward_reason"] = rr.get("reason")
    result["risk_real"] = rr.get("risk")
    result["rr_real"] = rr.get("rr1")
    result["rr_tp1_real"] = rr.get("rr1")
    result["rr_tp2_real"] = rr.get("rr2")
    result["rr_tp3_real"] = rr.get("rr3")

    # Validations summary
    result["validation"] = validations
    result["confidence_breakdown"] = conf_result

    # Build comprehensive reason that matches numbers
    final_reasons = []

    # Add EMA reason
    final_reasons.append(ema_val.get("reason"))

    # Add countertrend if present
    if ct.get("is_countertrend"):
        final_reasons.append(f"{ct.get('type')}: {ct.get('reason')} - confidence penalty {ct.get('penalty')}")

    # Add SR if penalty
    if sr.get("reason") and sr.get("penalty", 0) > 0:
        final_reasons.append(sr.get("reason"))

    # Add entry status
    final_reasons.append(entry.get("reason"))

    # Add RR
    if not rr.get("valid"):
        final_reasons.append(rr.get("reason"))
    else:
        if rr.get("rr1") is not None:
            final_reasons.append(f"Real RR: 1:{rr.get('rr1'):.2f} (risk {rr.get('risk'):.4f}) - {rr.get('reason')}")

    # Add confidence penalties summary
    for r in conf_result["reasons"]:
        if r not in final_reasons:
            final_reasons.append(r)

    # Add downgrade reasons if WAIT
    if final_signal == "WAIT":
        for dr in downgrade_reasons:
            if dr not in final_reasons:
                final_reasons.append(dr)

    # Preserve original reason as part of history
    if original.get("reason") and original.get("reason") not in final_reasons:
        # Keep original reason but as context
        final_reasons.insert(0, f"Original plan: {original.get('reason')}")

    result["reasons"] = final_reasons[:8]
    result["reason"] = " | ".join(final_reasons[:3]) if final_reasons else original.get("reason", "No valid setup")

    if final_signal == "WAIT":
        if entry.get("status") == "MISSED":
            result["reason"] = f"ENTRY MISSED: Original entry {original.get('entry_low')}-{original.get('entry_high')} missed, current {original.get('price')}. {entry.get('reason')}. Action: WAIT, do not chase. Original zone preserved."
            result["trigger_condition"] = result["reason"]
        elif plan_status == "INVALIDATED":
            result["reason"] = f"PLAN INVALIDATED: {original.get('invalidation_reason') or 'thesis broken'}. Action: WAIT for new confirmed setup."
            result["trigger_condition"] = result["reason"]
        else:
            result["trigger_condition"] = result["reason"]
    else:
        # For BUY/SELL, ensure trigger_condition reflects validated reason
        result["trigger_condition"] = result["reason"]

    # Ensure daily plan status preserved
    if plan_status == "ACTIVE" and final_signal == "WAIT" and entry.get("status") != "MISSED":
        # If we downgraded ACTIVE to WAIT, keep plan as ACTIVE but signal WAIT? No, set plan_status to WAIT? Actually keep original but signal WAIT
        # Better to keep daily_plan_status as original, but signal WAIT indicates validation failed
        result["plan_status"] = original.get("plan_status", "ACTIVE")
        result["daily_plan_status"] = original.get("daily_plan_status", "ACTIVE")
        result["validation_downgrade"] = True
        result["validation_downgrade_reasons"] = downgrade_reasons
    else:
        result["plan_status"] = original.get("plan_status", plan_status)
        result["daily_plan_status"] = original.get("daily_plan_status", plan_status)

    # Ensure no fake prices created
    result["price"] = original.get("price")
    result["current_price"] = original.get("price") or original.get("current_price")
    result["ideal_entry"] = original.get("ideal_entry") or ((original.get("entry_low") + original.get("entry_high"))/2 if original.get("entry_low") and original.get("entry_high") else original.get("price"))

    result["validation_passed"] = final_signal != "WAIT" or entry.get("status") == "MISSED" or plan_status == "INVALIDATED"

    return result

def score_signal(market: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy compatibility - returns confidence scoring"""
    return calculate_realistic_confidence(market, {
        "ema": validate_ema_alignment_raw(market),
        "countertrend": detect_countertrend(market),
        "sr": calculate_sr_proximity(market),
        "entry": calculate_entry_status_strict(market),
        "rr": calculate_risk_reward_real(market)
    })

def is_countertrend_trade(market: Dict[str, Any]) -> bool:
    return detect_countertrend(market).get("is_countertrend", False)

def get_entry_status(market: Dict[str, Any]) -> str:
    return calculate_entry_status_strict(market).get("status", "UNKNOWN")



# =========================================================
# EXISTING AI ENGINE CLASS - WITH FIXED FAILOVER
# =========================================================

class AIEngine:
    def __init__(self, memory=None):
        self.memory = memory
        self.eleven_client = None
        if ELEVENLABS_API_KEY:
            try:
                from elevenlabs import ElevenLabs
                self.eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                logger.info("✅ ElevenLabs client initialized")
            except Exception as e:
                logger.warning(f"ElevenLabs init failed: {_redact_secrets(str(e))}")

    def _get_provider_order(self) -> List[str]:
        order = []
        if AI_PROVIDER == "XAI" and XAI_API_KEY:
            order = ["xai", "groq", "gemini", "openai"]
        elif AI_PROVIDER == "GROQ" and GROQ_API_KEY:
            order = ["groq", "gemini", "openai", "xai"]
        elif AI_PROVIDER == "GEMINI" and GEMINI_API_KEY:
            order = ["gemini", "groq", "openai", "xai"]
        elif AI_PROVIDER == "OPENAI" and OPENAI_API_KEY:
            order = ["openai", "groq", "gemini", "xai"]
        else:
            if XAI_API_KEY:
                order.append("xai")
            if GROQ_API_KEY:
                order.append("groq")
            if GEMINI_API_KEY:
                order.append("gemini")
            if OPENAI_API_KEY:
                order.append("openai")
            for p in ["groq", "gemini", "openai", "xai"]:
                if p not in order:
                    order.append(p)
        return order

    def _load_memory_history(self, user_id: str, limit: int = 20) -> List[dict]:
        if not self.memory:
            return []
        try:
            history = self.memory.get_history(user_id, limit=limit)
            return history
        except Exception as e:
            logger.warning(f"Memory load failed for {user_id}: {_redact_secrets(str(e))}")
            return []

    def _save_memory(self, user_id: str, prompt: str, response: str):
        if not self.memory:
            return
        try:
            self.memory.add_message(user_id, "user", prompt)
            self.memory.add_message(user_id, "assistant", response)
        except Exception as e:
            logger.warning(f"Memory save failed for {user_id}: {_redact_secrets(str(e))}")

    def ask(self, user_id: str, prompt: str, image: Optional[Tuple[str, bytes]] = None) -> str:
        user_id = str(user_id)
        prompt = str(prompt or "").strip()
        if not prompt and not image:
            return "Please provide a question or image."
        history = self._load_memory_history(user_id, limit=15)
        providers = self._get_provider_order()
        seen = set()
        finite_providers = []
        for p in providers:
            if p not in seen:
                seen.add(p)
                finite_providers.append(p)
        last_sanitized_error = None
        for provider in finite_providers:
            try:
                resp = None
                if provider == "xai" and XAI_API_KEY:
                    resp = self._xai(prompt, history, image)
                elif provider == "groq" and GROQ_API_KEY:
                    resp = self._groq(prompt, history, image)
                elif provider == "gemini" and GEMINI_API_KEY:
                    resp = self._gemini(prompt, history, image)
                elif provider == "openai" and OPENAI_API_KEY:
                    resp = self._openai(prompt, history, image)
                else:
                    continue
                if resp:
                    cleaned = clean_ai_response(resp)
                    if cleaned:
                        self._save_memory(user_id, prompt, cleaned)
                        if provider != finite_providers[0]:
                            logger.info(f"Fallback provider {provider} succeeded after previous failure")
                        return cleaned
            except ProviderRateLimitError as e:
                sanitized = _sanitize_exception_message(e)
                logger.warning(f"{provider} provider failed with HTTP 429 rate limit, attempting fallback. Detail: {sanitized}")
                last_sanitized_error = sanitized
                continue
            except ProviderTransientError as e:
                sanitized = _sanitize_exception_message(e)
                logger.warning(f"{provider} provider transient failure, attempting fallback. Detail: {sanitized}")
                last_sanitized_error = sanitized
                continue
            except Exception as e:
                sanitized = _sanitize_exception_message(e)
                if _is_rate_limit_error(None, sanitized):
                    logger.warning(f"{provider} provider failed with HTTP 429 rate limit, attempting fallback. Detail: {sanitized}")
                elif _is_transient_error(None, sanitized):
                    logger.warning(f"{provider} provider transient failure, attempting fallback. Detail: {sanitized}")
                else:
                    logger.warning(f"{provider} failed: {sanitized}")
                last_sanitized_error = sanitized
                continue
        logger.error(f"All AI providers failed. Last sanitized error: {last_sanitized_error}")
        return "AI temporarily unavailable. Please try again shortly."

    def _build_openai_messages(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], include_system: bool = True) -> List[dict]:
        messages = []
        if include_system:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        for h in history[-10:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _request_with_retry(self, url, headers, json_payload, provider_name: str, max_retries: int = 1, timeout: int = 45):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
                if resp.status_code == 429:
                    body = _redact_secrets(resp.text[:500])
                    logger.warning(f"{provider_name} provider failed with HTTP 429, attempt {attempt+1}/{max_retries+1}. Body: {body[:200]}")
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit 429")
                if resp.status_code in (500, 502, 503, 504):
                    body = _redact_secrets(resp.text[:500])
                    logger.warning(f"{provider_name} transient HTTP {resp.status_code}, attempt {attempt+1}/{max_retries+1}. Body: {body[:200]}")
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient HTTP {resp.status_code}")
                if resp.status_code >= 400:
                    body = _redact_secrets(resp.text[:500])
                    if _is_rate_limit_error(resp.status_code, body):
                        if attempt < max_retries:
                            time.sleep(0.6 * (attempt + 1))
                            continue
                        raise ProviderRateLimitError(f"{provider_name} rate limit {resp.status_code}: {body[:200]}")
                    if _is_transient_error(resp.status_code, body):
                        if attempt < max_retries:
                            time.sleep(0.8 * (attempt + 1))
                            continue
                        raise ProviderTransientError(f"{provider_name} transient {resp.status_code}: {body[:200]}")
                    # Raise with sanitized message
                    raise RuntimeError(_redact_secrets(f"HTTP {resp.status_code}: {body[:200]}"))
                return resp
            except ProviderRateLimitError:
                raise
            except ProviderTransientError:
                raise
            except requests.exceptions.Timeout as e:
                last_exc = e
                logger.warning(f"{provider_name} timeout attempt {attempt+1}/{max_retries+1}")
                if attempt < max_retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise ProviderTransientError(f"{provider_name} timeout")
            except requests.exceptions.ConnectionError as e:
                last_exc = e
                msg = _redact_secrets(str(e))
                logger.warning(f"{provider_name} connection error attempt {attempt+1}/{max_retries+1}: {msg[:200]}")
                if attempt < max_retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise ProviderTransientError(f"{provider_name} connection error")
            except requests.exceptions.HTTPError as e:
                sanitized = _sanitize_exception_message(e)
                status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                if _is_rate_limit_error(status, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit from HTTPError: {sanitized[:200]}")
                if _is_transient_error(status, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient from HTTPError: {sanitized[:200]}")
                raise RuntimeError(sanitized)
            except Exception as e:
                sanitized = _sanitize_exception_message(e)
                if _is_rate_limit_error(None, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit: {sanitized[:200]}")
                if _is_transient_error(None, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient: {sanitized[:200]}")
                raise RuntimeError(sanitized)
        if last_exc:
            raise ProviderTransientError(f"{provider_name} failed after retries: {_sanitize_exception_message(last_exc)}")
        raise ProviderTransientError(f"{provider_name} failed after retries")

    def _xai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not XAI_API_KEY:
            return None
        model = XAI_MODEL
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(XAI_URL, headers, payload, "xai", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _groq(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not GROQ_API_KEY:
            return None
        model = GROQ_VISION_MODEL if image else GROQ_MODEL
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(GROQ_URL, headers, payload, "groq", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _openai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not OPENAI_API_KEY:
            return None
        model = OPENAI_MODEL
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(OPENAI_URL, headers, payload, "openai", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _gemini(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not GEMINI_API_KEY:
            return None
        contents = []
        for h in history[-8:]:
            role = h.get("role")
            content = h.get("content")
            if not content:
                continue
            g_role = "user" if role == "user" else "model"
            contents.append({"role": g_role, "parts": [{"text": content}]})
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts = [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64}}]
            contents.append({"role": "user", "parts": parts})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2000}
        }
        url = GEMINI_URL.format(model=GEMINI_MODEL) + f"?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        resp = self._request_with_retry(url, headers, payload, "gemini", max_retries=1, timeout=45)
        data = resp.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text","") for p in parts)
            return text
        except Exception as e:
            logger.warning(f"Gemini parse error: {_redact_secrets(str(e))}")
            return None

    def generate_speech(self, text: str) -> io.BytesIO:
        if not text:
            raise ValueError("Text empty")
        text = str(text).strip()[:800]
        if self.eleven_client and ELEVENLABS_API_KEY:
            try:
                logger.info(f"TTS provider: ElevenLabs | TTS model: {ELEVENLABS_MODEL_ID} | TTS voice: Bella ({ELEVENLABS_VOICE_ID})")
                audio = self.eleven_client.text_to_speech.convert(
                    voice_id=ELEVENLABS_VOICE_ID,
                    model_id=ELEVENLABS_MODEL_ID,
                    text=text,
                )
                bio = io.BytesIO()
                for chunk in audio:
                    if chunk:
                        bio.write(chunk)
                bio.seek(0)
                bio.name = "voice.mp3"
                return bio
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {_redact_secrets(str(e))}")
                raise
        else:
            raise RuntimeError("ElevenLabs not configured")

    def validate_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return validate_market_signal(market_data)

    def validate_and_score(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return validate_market_signal(market_data)
