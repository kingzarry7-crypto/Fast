"""Non-executing Kitty V3 inference endpoints.

Gold feature extraction uses the application's real XAU/USD candle providers.
Kitty's packaged training metadata does not identify a gold-trained model, so
this endpoint deliberately does not emit a gold BUY/SELL prediction.
"""
from math import isfinite
from typing import Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import kitty_v3

router = APIRouter(prefix="/api/kitty", tags=["Kitty V3"])


class KittyPredictionRequest(BaseModel):
    features: Dict[str, float] = Field(
        ...,
        description="Exact six Kitty features: Close, SMA_20, RSI_14, BB_Upper, BB_Lower, MACD",
    )


def _rsi(closes, period=14):
    if len(closes) < period + 1:
        raise ValueError("At least 15 closes are required for RSI_14")
    gains, losses = [], []
    for previous, current in zip(closes[-period-1:-1], closes[-period:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def _ema(values, period):
    if not values:
        raise ValueError("No close values available")
    alpha = 2.0 / (period + 1.0)
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1.0 - alpha) * result
    return result


def _gold_features(candles):
    closes = [float(c["close"]) for c in candles]
    if len(closes) < 35:
        raise ValueError(f"At least 35 valid XAU/USD candles are required; received {len(closes)}")
    if any(not isfinite(value) or value <= 0 for value in closes):
        raise ValueError("XAU/USD candles contain invalid close prices")
    window = closes[-20:]
    sma = sum(window) / 20.0
    variance = sum((value - sma) ** 2 for value in window) / 20.0
    std = variance ** 0.5
    # MACD 12/26 with the latest candle included, using only available history.
    macd = _ema(closes, 12) - _ema(closes, 26)
    return {
        "Close": closes[-1],
        "SMA_20": sma,
        "RSI_14": _rsi(closes, 14),
        "BB_Upper": sma + 2.0 * std,
        "BB_Lower": sma - 2.0 * std,
        "MACD": macd,
    }


@router.get("/status")
def kitty_status():
    result = kitty_v3.status()
    if not result.get("available"):
        raise HTTPException(status_code=503, detail=result)
    result["gold_prediction_ready"] = False
    result["gold_prediction_note"] = (
        "The packaged model metadata does not identify gold-specific training data. "
        "Use /gold-features for real XAU/USD features; do not treat this model as a gold signal until validated."
    )
    return result


@router.post("/predict")
def kitty_predict(request: KittyPredictionRequest):
    try:
        return kitty_v3.predict_features(request.features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Kitty inference unavailable: " + type(exc).__name__)


@router.get("/gold-features")
def kitty_gold_features(timeframe: str = Query(default="15m", pattern="^(1m|5m|15m|30m|1h|2h|4h|1d)$")):
    """Return real XAU/USD indicator inputs without pretending the model is gold-trained."""
    try:
        from market import get_candles
        candles = get_candles("XAU/USD", timeframe=timeframe, outputsize=150)
        features = _gold_features(candles)
        latest = candles[-1]
        return {
            "symbol": "XAU/USD",
            "timeframe": timeframe,
            "candle_count": len(candles),
            "latest_candle_time": latest.get("datetime"),
            "features": {key: round(value, 8) for key, value in features.items()},
            "prediction_available": False,
            "reason": (
                "Kitty V3's training metadata does not confirm XAU/USD training. "
                "A gold-specific model/scaler validation is required before generating a gold prediction."
            ),
            "source": "market.get_candles (configured live gold providers)",
            "trading_enabled": False,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Live gold feature extraction failed: " + type(exc).__name__ + ": " + str(exc)[:180],
        )
