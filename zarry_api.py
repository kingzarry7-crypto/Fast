"""Authenticated, fail-closed Fast API proxy for the isolated ZARRY explainer.

This endpoint is an optional side channel. It never calls Kitty, changes a
Kitty decision, or participates in order execution.
"""
from __future__ import annotations

import math
import os
from typing import Any, Callable, Literal

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Decision = Literal["BUY", "SELL", "WAIT", "NO TRADE"]


class KittyAssessment(StrictModel):
    decision: Decision
    reason_codes: list[str] = Field(default_factory=list, max_length=40)


class ZarryExplainRequest(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    timestamp: str = Field(min_length=10, max_length=40)
    context: dict[str, Any]
    kitty_assessment: KittyAssessment

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value or len(value) > 80:
            raise ValueError("context must contain between 1 and 80 fields")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise ValueError("invalid context key")
            if isinstance(item, str) and len(item) > 1000:
                raise ValueError("context strings are limited to 1000 characters")
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise ValueError("context values must be scalar")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("context numbers must be finite")
        return value


class ZarryExplainResponse(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    decision: Decision
    summary: str = Field(min_length=1, max_length=3000)
    uncertainty: str = Field(max_length=1500)
    cited_fields: list[str] = Field(max_length=80)
    numeric_claims: list[float | int] = Field(max_length=80)
    authority: Literal["KITTY_DETERMINISTIC_ENGINE"]
    mode: Literal["explanation_only"]


def _timeout_seconds() -> int:
    try:
        value = int(os.getenv("ZARRY_TIMEOUT_SECONDS", "120"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=503, detail="ZARRY timeout configuration is invalid")
    if value < 1 or value > 120:
        raise HTTPException(status_code=503, detail="ZARRY timeout must be between 1 and 120 seconds")
    return value


def _validate_response(result: ZarryExplainResponse, payload: ZarryExplainRequest) -> None:
    if result.symbol != payload.symbol:
        raise ValueError("ZARRY changed symbol")
    if result.decision != payload.kitty_assessment.decision:
        raise ValueError("ZARRY changed Kitty's decision")
    if "explanation-only" not in result.summary.lower():
        raise ValueError("ZARRY response is not marked explanation-only")
    if not set(result.cited_fields).issubset(payload.context):
        raise ValueError("ZARRY cited a field not supplied by Kitty")
    available_numbers = {
        float(value)
        for value in payload.context.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    if any(float(value) not in available_numbers for value in result.numeric_claims):
        raise ValueError("ZARRY produced an ungrounded numeric claim")


def create_router(
    require_user: Callable[[Request], Any],
    post: Callable[..., Any] | None = None,
) -> APIRouter:
    """Build the proxy router; dependencies are injected for deterministic tests."""
    upstream_post = post or requests.post
    router = APIRouter(tags=["zarry"])

    @router.post("/api/zarry/explain", response_model=ZarryExplainResponse)
    def explain(payload: ZarryExplainRequest, request: Request):
        # Use the same web session authentication as Fast's existing chat API.
        require_user(request)

        if os.getenv("ZARRY_ENABLED", "").strip().lower() != "true":
            raise HTTPException(status_code=503, detail="ZARRY explanations are disabled")
        service_url = os.getenv("ZARRY_SERVICE_URL", "").strip().rstrip("/")
        api_key = os.getenv("ZARRY_API_KEY", "").strip()
        if not service_url.startswith(("https://", "http://")) or not api_key:
            raise HTTPException(status_code=503, detail="ZARRY service is not configured")

        try:
            upstream = upstream_post(
                service_url + "/v1/explain",
                json=payload.model_dump(),
                headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                timeout=_timeout_seconds(),
            )
        except requests.Timeout as exc:
            raise HTTPException(status_code=504, detail="ZARRY explanation timed out") from exc
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="ZARRY service is unavailable") from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail="ZARRY request failed") from exc

        if getattr(upstream, "status_code", None) != 200:
            raise HTTPException(status_code=502, detail="ZARRY service rejected the explanation request")
        try:
            result = ZarryExplainResponse.model_validate(upstream.json())
            _validate_response(result, payload)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="ZARRY returned an invalid or unsafe explanation") from exc

        return result

    return router
