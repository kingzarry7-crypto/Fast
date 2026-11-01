"""Authenticated, fail-closed Fast API proxy for the isolated ZARRY explainer.

This endpoint is an optional side channel. It never calls Kitty, changes a
Kitty decision, or participates in order execution.
"""
from __future__ import annotations

import math
import os
import re
import time
import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Callable, Literal

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


NUMERIC_TEXT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![A-Za-z0-9_-])")


def _extract_numeric_text_claims(*texts: str) -> set[float]:
    claims: set[float] = set()
    for text in texts:
        for token in NUMERIC_TEXT_RE.findall(text or ""):
            claims.add(float(token.replace(",", "").rstrip("%")))
    return claims


Decision = Literal["BUY", "SELL", "WAIT", "NO TRADE"]


class KittyAssessment(StrictModel):
    decision: Decision
    reason_codes: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: list[str]) -> list[str]:
        if any(not code or len(code) > 80 for code in value):
            raise ValueError("reason codes must contain 1 to 80 characters")
        return value


class ZarryExplainRequest(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    timestamp: str = Field(min_length=10, max_length=40)
    context: dict[str, Any]
    kitty_assessment: KittyAssessment

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        max_age = int(os.getenv("ZARRY_MAX_CONTEXT_AGE_SECONDS", "86400"))
        age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        if max_age > 0 and age > max_age:
            raise ValueError("market context timestamp is stale")
        if age < -60:
            raise ValueError("market context timestamp is in the future")
        return value

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
    declared_numbers = {float(value) for value in result.numeric_claims}
    if not declared_numbers.issubset(available_numbers):
        raise ValueError("ZARRY produced an ungrounded numeric claim")
    text_numbers = _extract_numeric_text_claims(result.summary, result.uncertainty)
    if not text_numbers.issubset(declared_numbers):
        raise ValueError("ZARRY used an undeclared numeric claim in its explanation")


def create_router(
    require_user: Callable[[Request], Any],
    post: Callable[..., Any] | None = None,
) -> APIRouter:
    """Build the proxy router; dependencies are injected for deterministic tests."""
    upstream_post = post or requests.post
    router = APIRouter(tags=["zarry"])
    request_times: dict[str, deque[float]] = defaultdict(deque)
    request_times_lock = threading.Lock()

    @router.post("/api/zarry/explain", response_model=ZarryExplainResponse)
    def explain(payload: ZarryExplainRequest, request: Request):
        # Use the same web session authentication as Fast's existing chat API.
        user = require_user(request)
        user_id = str(user.get("id", "authenticated-user")) if isinstance(user, dict) else str(getattr(user, "id", "authenticated-user"))
        try:
            max_requests = int(os.getenv("ZARRY_MAX_REQUESTS_PER_MINUTE", "20"))
        except ValueError:
            raise HTTPException(status_code=503, detail="ZARRY rate-limit configuration is invalid")
        if max_requests < 1 or max_requests > 120:
            raise HTTPException(status_code=503, detail="ZARRY rate limit must be between 1 and 120 per minute")
        now = time.monotonic()
        with request_times_lock:
            bucket = request_times[user_id]
            while bucket and now - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= max_requests:
                raise HTTPException(status_code=429, detail="ZARRY explanation rate limit exceeded", headers={"Retry-After": "60"})
            bucket.append(now)

        if os.getenv("ZARRY_ENABLED", "").strip().lower() != "true":
            raise HTTPException(status_code=503, detail="ZARRY explanations are disabled")
        # ZARRY_API_URL is the established Fast deployment variable; retain
        # ZARRY_SERVICE_URL as a backward-compatible explicit override.
        service_url = (
            os.getenv("ZARRY_SERVICE_URL", "").strip()
            or os.getenv("ZARRY_API_URL", "").strip()
        ).rstrip("/")
        api_key = os.getenv("ZARRY_API_KEY", "").strip()
        if not service_url.startswith(("https://", "http://")) or not api_key:
            raise HTTPException(status_code=503, detail="ZARRY service is not configured")
        if service_url.startswith("http://"):
            host = service_url[len("http://"):].split("/", 1)[0].split(":", 1)[0].lower()
            if not host.endswith(".railway.internal"):
                raise HTTPException(status_code=503, detail="unencrypted ZARRY URLs are allowed only on Railway private networking")

        candidate_id = request.headers.get("X-Request-ID", "")[:128]
        request_id = candidate_id if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", candidate_id) else str(uuid4())
        upstream = None
        for attempt in range(2):
            try:
                upstream = upstream_post(
                    service_url + "/v1/explain",
                    json=payload.model_dump(),
                    headers={
                        "Authorization": "Bearer " + api_key,
                        "Content-Type": "application/json",
                        "X-Request-ID": request_id,
                    },
                    timeout=_timeout_seconds(),
                )
                break
            except requests.ConnectionError as exc:
                if attempt == 1:
                    raise HTTPException(status_code=502, detail="ZARRY service is unavailable") from exc
                time.sleep(0.2)
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
