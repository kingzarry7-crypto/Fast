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


def _ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [float(values[0])]
    for value in values[1:]:
        result.append(alpha * float(value) + (1.0 - alpha) * result[-1])
    return result


def _kitty_features(candles):
    """Build the exact 18-feature contract expected by the retrained BTC model."""
    import math
    closes = [float(c["close"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    if len(closes) < 55:
        raise ValueError(f"At least 55 candles are required for Kitty V3; received {len(closes)}")
    arrays = closes + opens + highs + lows
    if not all(math.isfinite(v) and v > 0 for v in arrays):
        raise ValueError("Candles contain invalid OHLC prices")
    def ret(period):
        return closes[-1] / closes[-1-period] - 1.0
    def sma(period, end=None):
        seq = closes if end is None else closes[:end]
        return sum(seq[-period:]) / period
    sma6, sma20, sma50 = sma(6), sma(20), sma(50)
    changes = [closes[i] / closes[i-1] - 1.0 for i in range(1, len(closes))]
    gains = [max(v, 0.0) for v in changes[-14:]]
    losses = [max(-v, 0.0) for v in changes[-14:]]
    avg_gain = sum(gains) / 14.0
    avg_loss = sum(losses) / 14.0
    rsi = 100.0 if avg_loss == 0 and avg_gain > 0 else (50.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss))
    ema12, ema26 = _ema_series(closes, 12), _ema_series(closes, 26)
    macd_series = [a - b for a, b in zip(ema12, ema26)]
    macd_signal_series = _ema_series(macd_series, 9)
    macd = macd_series[-1] / closes[-1]
    macd_signal = macd_signal_series[-1] / closes[-1]
    macd_hist = (macd_series[-1] - macd_signal_series[-1]) / closes[-1]
    returns = changes
    vol6 = (sum((v - sum(returns[-6:]) / 6.0) ** 2 for v in returns[-6:]) / 6.0) ** 0.5
    vol24 = (sum((v - sum(returns[-24:]) / 24.0) ** 2 for v in returns[-24:]) / 24.0) ** 0.5
    candle_range = highs[-1] - lows[-1]
    return {
        "ret_1h": ret(1), "ret_3h": ret(3), "ret_6h": ret(6),
        "ret_12h": ret(12), "ret_24h": ret(24),
        "close_vs_sma6": closes[-1] / sma6 - 1.0,
        "close_vs_sma20": closes[-1] / sma20 - 1.0,
        "close_vs_sma50": closes[-1] / sma50 - 1.0,
        "sma6_vs_sma20": sma6 / sma20 - 1.0,
        "rsi_14": rsi,
        "macd_norm": macd, "macd_signal_norm": macd_signal,
        "macd_hist_norm": macd_hist, "volatility_6h": vol6,
        "volatility_24h": vol24,
        "range_pct": candle_range / closes[-1],
        "body_pct": (closes[-1] - opens[-1]) / opens[-1],
        "close_position": (closes[-1] - lows[-1]) / candle_range if candle_range > 0 else 0.5,
    }


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
            latest_time = _validate_candles(candles, timeframe, symbol)
            features = _kitty_features(candles)
            prediction = kitty_model.predict_features(features)
            results.append({
                "timeframe": timeframe, "available": True,
                "latest_candle_time": latest_time, "close": float(candles[-1]["close"]),
                "prediction": prediction,
                "timeframe_validated": timeframe == "1h",
            })
        except Exception as exc:
            results.append({
                "timeframe": timeframe, "available": False,
                "error": type(exc).__name__ + ": " + str(exc)[:160],
            })
    votes = [row["prediction"]["signal"] for row in results if row.get("available")]
    directional = [vote for vote in votes if vote in {"LONG", "SHORT"}]
    if len(directional) >= 2 and len(set(directional)) == 1 and len(directional) == len(votes):
        combined = directional[0]
    else:
        combined = "NO TRADE"
    return {
        "symbol": symbol, "requested_timeframes": requested, "results": results,
        "combined_signal": combined,
        "timeframes_available": len(votes), "timeframes_failed": len(results) - len(votes),
        "agreement": (len(directional) / len(votes)) if votes else 0.0,
        "research_only": True, "trading_enabled": False,
        "warning": "The checkpoint was trained on hourly BTC features. Applying it to other intervals is exploratory and unvalidated; combined output is not a proven profitable signal.",
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
        latest_candle_time = _validate_candles(candles, "1h", symbol)
        features = _kitty_features(candles)
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


# Paper-trading endpoints are isolated from the live broker connector.
from kitty_paper_trader import router as kitty_paper_router
router.include_router(kitty_paper_router)


# Explicit opt-in Binance Spot Demo execution is separate from the paper simulator.
from kitty_demo_trader import router as kitty_demo_trader_router
router.include_router(kitty_demo_trader_router)

@router.on_event("startup")
def _restore_kitty_demo_worker_on_startup() -> None:
    from kitty_demo_trader import initialize_worker
    initialize_worker()
