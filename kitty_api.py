"""Non-executing Kitty V3 inference endpoints.

Gold feature extraction uses the application's real XAU/USD candle providers.
Kitty's packaged training metadata does not identify a gold-trained model, so
this endpoint deliberately does not emit a gold BUY/SELL prediction.
"""
from math import isfinite
from typing import Dict
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import kitty_v3_retrained as kitty_model

router = APIRouter(prefix="/api/kitty", tags=["Kitty V3"])


class KittyPredictionRequest(BaseModel):
    features: Dict[str, float] = Field(
        ...,
        description="Exact 18-feature Kitty V3 retrained input contract; normally use /market-predict or /multi-timeframe.",
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


def _validate_candles(candles, timeframe, symbol):
    from datetime import datetime, timezone, timedelta
    if not isinstance(candles, list) or len(candles) < 35:
        raise ValueError(symbol + ': insufficient candles')
    raw = candles[-1].get('datetime') or candles[-1].get('time') or candles[-1].get('timestamp')
    if isinstance(raw, (int, float)):
        stamp = datetime.fromtimestamp(raw / (1000 if raw > 10000000000 else 1), tz=timezone.utc)
    elif isinstance(raw, str):
        stamp = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
    else:
        raise ValueError(symbol + ': missing latest candle timestamp')
    age = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
    limit = timedelta(days=3) if timeframe == '1d' else timedelta(hours=6)
    if age < timedelta(minutes=-10) or age > limit:
        raise ValueError(symbol + ': stale or future candle timestamp')
    for candle in candles[-35:]:
        for key in ('open', 'high', 'low', 'close'):
            value = float(candle[key])
            if not isfinite(value) or value <= 0: raise ValueError(symbol + ': invalid candle price')
    return stamp.astimezone(timezone.utc).isoformat()

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


from kitty_features import compute_kitty_features as _kitty_features


@router.get("/multi-timeframe")
def kitty_multi_timeframe(
    symbol: str = Query(default="BTC/USD", pattern="^(BTC/USD|BTC/USDT)$"),
    timeframes: str = Query(default="15m,1h,4h,1d"),
):
    """Compare research-only classifier outputs across supported candle intervals."""
    from market import get_candles
    allowed = {"1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"}
    requested = list(dict.fromkeys(item.strip() for item in timeframes.split(",") if item.strip()))
    if not requested or any(item not in allowed for item in requested):
        raise HTTPException(status_code=422, detail="timeframes must be comma-separated values from: " + ", ".join(sorted(allowed)))
    results = []
    for timeframe in requested:
        try:
            candles = get_candles(symbol, timeframe=timeframe, outputsize=160)
            # Exclude the newest candle because the provider may return a live,
            # incomplete interval. This endpoint is exploratory outside 1h.
            _validate_candles(candles, timeframe, symbol)
            if len(candles) < 56:
                raise ValueError(symbol + ": at least 56 candles are required to exclude the forming candle")
            closed_candles = candles[:-1]
            latest_time = _validate_candles(closed_candles, timeframe, symbol)
            features = _kitty_features(closed_candles)
            prediction = kitty_model.predict_features(features)
            results.append({
                "timeframe": timeframe, "available": True,
                "latest_candle_time": latest_time, "close": float(closed_candles[-1]["close"]),
                "prediction": prediction,
                "model_timeframe_match": timeframe == "1h",
                "timeframe_validated": False,
            })
        except Exception as exc:
            results.append({
                "timeframe": timeframe, "available": False,
                "error": type(exc).__name__ + ": " + str(exc)[:160],
            })
    votes = [row["prediction"]["signal"] for row in results if row.get("available")]
    directional = [vote for vote in votes if vote in {"LONG", "SHORT"}]
    # One hourly checkpoint is not a validated ensemble of timeframe-specific models.
    # Never convert agreement among out-of-timeframe predictions into an actionable signal.
    combined = "NO TRADE"
    return {
        "symbol": symbol, "requested_timeframes": requested, "results": results,
        "combined_signal": combined,
        "timeframes_available": len(votes), "timeframes_failed": len(results) - len(votes),
        "agreement": (len(directional) / len(votes)) if votes else 0.0,
        "combined_signal_reason": "No timeframe-specific model ensemble has passed validation; consensus is intentionally disabled.",
        "research_only": True, "trading_enabled": False,
        "warning": "The checkpoint was trained on hourly features, and the training symbol metadata is not fully confirmed. Other timeframes are exploratory only; this endpoint never emits an actionable combined signal.",
    }


@router.get("/status")
def kitty_status():
    result = kitty_model.status()
    if not result.get("available"):
        raise HTTPException(status_code=503, detail=result)
    result["legacy_six_feature_model_retired"] = True
    result["gold_prediction_ready"] = False
    result["gold_prediction_note"] = (
        "The packaged model metadata does not identify gold-specific training data. "
        "Use /gold-features for real XAU/USD features; do not treat this model as a gold signal until validated."
    )
    return result


@router.post("/predict")
def kitty_predict(request: KittyPredictionRequest):
    try:
        return kitty_model.predict_features(request.features)
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
        latest_candle_time = _validate_candles(candles, timeframe, "XAU/USD")
        features = _gold_features(candles)
        latest = candles[-1]
        return {
            "symbol": "XAU/USD",
            "timeframe": timeframe,
            "candle_count": len(candles),
            "latest_candle_time": latest_candle_time,
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


@router.get("/market-predict")
def kitty_market_predict(
    symbol: str = Query(default="BTC/USDT", pattern="^(BTC/USDT|BTC/USD)$"),
):
    """Run research-only Kitty V3 inference on live hourly BTC candles.

    The checkpoint contract is hourly. Other candle intervals are exposed only
    through the explicitly unvalidated multi-timeframe comparison endpoint.
    """
    try:
        from market import get_candles
        candles = get_candles(symbol, timeframe="1h", outputsize=160)
        # Providers may include the still-forming candle. Validate the feed, then
        # infer only from completed candles to match the paper-trading convention.
        _validate_candles(candles, "1h", symbol)
        if len(candles) < 56:
            raise ValueError(symbol + ": at least 56 candles are required to exclude the forming candle")
        closed_candles = candles[:-1]
        latest_candle_time = _validate_candles(closed_candles, "1h", symbol)
        features = _kitty_features(closed_candles)
        prediction = kitty_model.predict_features(features)
        return {
            "symbol": symbol,
            "timeframe": "1h",
            "candle_count": len(candles),
            "latest_candle_time": latest_candle_time,
            "prediction_available": True,
            "prediction_mode": "research_only_hourly_model",
            "training_symbol_confirmed": False,
            "training_timeframe": "1h",
            "timeframe_validated": False,
            "features": {key: round(value, 8) for key, value in features.items()},
            "prediction": prediction,
            "warning": (
                "Kitty V3 produced an inference from live hourly BTC candles, but its "
                "training metadata does not identify the training symbol. Treat this "
                "as an experimental model test, not a validated trading signal. "
                "No trades are placed."
            ),
            "trading_enabled": False,
            "source": "market.get_candles (configured live crypto providers)",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Live market inference failed: " + type(exc).__name__ + ": " + str(exc)[:180],
        )




def _technical_signal(candles, symbol: str, timeframe: str) -> dict:
    """Explainable, rule-based technical confluence for assets without a validated ML model."""
    import math
    from datetime import datetime, timezone
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    if len(closes) < 55 or not all(math.isfinite(v) and v > 0 for v in closes + highs + lows):
        raise ValueError("At least 55 valid completed candles are required")
    def ema(values, period):
        alpha = 2.0 / (period + 1.0)
        result = float(values[0])
        for value in values[1:]:
            result = alpha * float(value) + (1.0 - alpha) * result
        return result
    def sma(values, period):
        return sum(values[-period:]) / period
    e9, e21, e50 = ema(closes, 9), ema(closes, 21), ema(closes, 50)
    gains, losses = [], []
    for previous, current in zip(closes[-15:-1], closes[-14:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain, avg_loss = sum(gains) / 14, sum(losses) / 14
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (50.0 if avg_gain == 0 and avg_loss == 0 else (100.0 - 100.0 / (1.0 + avg_gain / max(avg_loss, 1e-12))))
    ema12, ema26 = ema(closes, 12), ema(closes, 26)
    macd_positive = ema12 > ema26
    momentum = closes[-1] / closes[-7] - 1.0
    # ATR(14) for volatility-aware levels; never place orders from this endpoint.
    true_ranges = []
    for i in range(-14, 0):
        prev_close = closes[i - 1]
        true_ranges.append(max(highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close)))
    atr = sum(true_ranges) / len(true_ranges)
    bullish = [
        e9 > e21 > e50,
        closes[-1] > e21,
        macd_positive,
        50.0 < rsi < 68.0,
        momentum > 0,
    ]
    bearish = [
        e9 < e21 < e50,
        closes[-1] < e21,
        not macd_positive,
        32.0 < rsi < 50.0,
        momentum < 0,
    ]
    bull, bear = sum(bullish), sum(bearish)
    if bull >= 4 and bull - bear >= 3:
        signal = "BUY"
        direction = 1
        score = bull
    elif bear >= 4 and bear - bull >= 3:
        signal = "SELL"
        direction = -1
        score = bear
    else:
        signal = "NO TRADE"
        direction = 0
        score = max(bull, bear)
    price = closes[-1]
    # ATR levels are indicative risk references, not guarantees or executable orders.
    stop = price - direction * 1.5 * atr if direction else None
    target1 = price + direction * 1.5 * atr if direction else None
    target2 = price + direction * 2.5 * atr if direction else None
    raw_time = candles[-1].get("datetime") or candles[-1].get("time") or candles[-1].get("timestamp")
    if isinstance(raw_time, (int, float)):
        candle_time = datetime.fromtimestamp(raw_time / (1000 if raw_time > 10000000000 else 1), tz=timezone.utc).isoformat()
    else:
        candle_time = str(raw_time)
    return {
        "symbol": symbol, "timeframe": timeframe, "signal": signal,
        "signal_type": "rule_based_technical_confluence",
        "price": round(price, 8), "completed_candle_time": candle_time,
        "confidence_score": round(score / 5.0, 2),
        "confirmation_count": score, "confirmations_required": 4,
        "indicators": {
            "ema_9": round(e9, 8), "ema_21": round(e21, 8), "ema_50": round(e50, 8),
            "rsi_14": round(rsi, 2), "macd_bias": "BULLISH" if macd_positive else "BEARISH",
            "momentum_6_candles_pct": round(momentum * 100.0, 4), "atr_14": round(atr, 8),
        },
        "risk_levels": {
            "stop_reference": round(stop, 8) if stop is not None else None,
            "target_1_reference": round(target1, 8) if target1 is not None else None,
            "target_2_reference": round(target2, 8) if target2 is not None else None,
            "method": "1.5x ATR stop and 1.5x/2.5x ATR targets; indicative only",
        },
        "reasons": [
            "EMA trend: " + ("bullish" if e9 > e21 > e50 else "bearish" if e9 < e21 < e50 else "mixed"),
            "Price versus EMA21: " + ("above" if price > e21 else "below"),
            "RSI(14): " + str(round(rsi, 2)),
            "MACD bias: " + ("bullish" if macd_positive else "bearish"),
            "Six-candle momentum: " + str(round(momentum * 100.0, 4)) + "%",
        ],
        "model_used": False,
        "research_only": True, "trading_enabled": False,
        "warning": "This is a transparent technical-rule signal, not a trained or validated prediction. No indicator can guarantee accuracy or profit. Confirm spread, news, session, and risk before any trade.",
    }


@router.get("/signal")
def kitty_technical_signal(
    symbol: str = Query(default="BTC/USD", min_length=3, max_length=24, pattern=r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$"),
    timeframe: str = Query(default="1h", pattern="^(5m|15m|30m|1h|2h|4h|1d)$"),
):
    """Return a completed-candle technical confluence signal for supported market symbols."""
    try:
        from market import get_candles
        symbol = symbol.upper().replace(" ", "")
        candles = get_candles(symbol, timeframe=timeframe, outputsize=180)
        _validate_candles(candles, timeframe, symbol)
        if len(candles) < 56:
            raise ValueError(symbol + ": at least 56 candles are required to exclude the possibly forming candle")
        closed_candles = candles[:-1]
        _validate_candles(closed_candles, timeframe, symbol)
        return _technical_signal(closed_candles, symbol, timeframe)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Technical signal unavailable for " + symbol + ": " + type(exc).__name__ + ": " + str(exc)[:180],
        )


# One paper engine only: multi-market technical confluence into an isolated
# SQLite ledger. Do not mount the legacy BTC classifier worker or Binance demo
# order router; neither is part of this paper-only workflow.
from kitty_multi_paper import router as kitty_multi_paper_router
router.include_router(kitty_multi_paper_router)
