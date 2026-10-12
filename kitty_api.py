"""Non-executing Kitty V3 inference endpoints."""
from typing import Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import kitty_v3

router = APIRouter(prefix="/api/kitty", tags=["Kitty V3"])

class KittyPredictionRequest(BaseModel):
    features: Dict[str, float] = Field(..., description="Exact six Kitty features: Close, SMA_20, RSI_14, BB_Upper, BB_Lower, MACD")

@router.get("/status")
def kitty_status():
    result = kitty_v3.status()
    if not result.get("available"):
        raise HTTPException(status_code=503, detail=result)
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
