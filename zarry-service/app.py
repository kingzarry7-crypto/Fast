"""Isolated, explanation-only ZARRY inference API prototype.

Kitty remains the sole authority for trading decisions. This service has no
market-data, broker, order, or tool-execution integration.
"""
from __future__ import annotations

import hmac
import json
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KittyAssessment(StrictModel):
    decision: Literal["BUY", "SELL", "WAIT"]
    reason_codes: list[str] = Field(default_factory=list)


class ExplainRequest(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    timestamp: str = Field(min_length=10, max_length=40)
    context: dict[str, Any]
    kitty_assessment: KittyAssessment
    task: Literal["explain"] = "explain"

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value or len(value) > 80:
            raise ValueError("context must contain between 1 and 80 fields")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 80:
                raise ValueError("invalid context key")
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise ValueError("context values must be scalar")
            if isinstance(item, float) and (item != item or abs(item) == float("inf")):
                raise ValueError("context numbers must be finite")
        return value


class ExplainResponse(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    decision: Literal["BUY", "SELL", "WAIT"]
    summary: str = Field(min_length=1, max_length=3000)
    uncertainty: str = Field(max_length=1500)
    cited_fields: list[str]
    numeric_claims: list[float | int]
    authority: Literal["KITTY_DETERMINISTIC_ENGINE"] = "KITTY_DETERMINISTIC_ENGINE"
    mode: Literal["explanation_only"] = "explanation_only"


SYSTEM_PROMPT = """You are ZARRY, an explanation-only model.
Kitty's deterministic assessment is authoritative. Never change BUY/SELL/WAIT.
Never invent prices, indicators, candles, fills, account facts or outcomes.
Use only the supplied context. Explain stale data, conflicting timeframes,
unconfirmed entries or missing risk levels as reasons to WAIT.
You cannot place orders or change risk settings.
Return one JSON object with exactly: symbol, decision, summary, uncertainty,
cited_fields, numeric_claims. symbol and decision must exactly match Kitty.
cited_fields must be supplied context keys. numeric_claims must be numbers
copied exactly from supplied context. Include the phrase explanation-only."""


def _load_model(model_path: str, threads: int, context_size: int):
    from llama_cpp import Llama

    return Llama(
        model_path=model_path,
        n_ctx=context_size,
        n_threads=threads,
        n_gpu_layers=0,
        verbose=False,
    )


def _validate_grounding(output: ExplainResponse, request: ExplainRequest) -> None:
    if output.symbol != request.symbol:
        raise ValueError("model changed symbol")
    if output.decision != request.kitty_assessment.decision:
        raise ValueError("model changed Kitty's decision")
    if "explanation-only" not in output.summary.lower():
        raise ValueError("model response is not marked explanation-only")
    if not set(output.cited_fields).issubset(request.context):
        raise ValueError("model cited fields absent from supplied context")
    available_numbers = {
        float(value)
        for value in request.context.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    if any(float(value) not in available_numbers for value in output.numeric_claims):
        raise ValueError("model produced an ungrounded numeric claim")


def create_app(model_loader=_load_model) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.model = None
        model_path = os.getenv("ZARRY_MODEL_PATH", "").strip()
        if model_path:
            app.state.model = model_loader(
                model_path,
                int(os.getenv("ZARRY_THREADS", "2")),
                int(os.getenv("ZARRY_CONTEXT_SIZE", "4096")),
            )
        yield
        app.state.model = None

    app = FastAPI(title="ZARRY Inference Service", version="0.1.0", lifespan=lifespan)

    async def authenticate(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = os.getenv("ZARRY_API_KEY", "")
        if not expected:
            raise HTTPException(status_code=503, detail="service authentication is not configured")
        supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    async def health():
        return {"status": "alive", "service": "zarry"}

    @app.get("/ready")
    async def ready(request: Request):
        if request.app.state.model is None:
            raise HTTPException(status_code=503, detail="model is not loaded")
        return {"status": "ready", "model_loaded": True}

    @app.post("/v1/explain", response_model=ExplainResponse, dependencies=[Depends(authenticate)])
    def explain(payload: ExplainRequest, request: Request):
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail="model is not loaded")
        message = {
            "symbol": payload.symbol,
            "timestamp": payload.timestamp,
            "context": payload.context,
            "kitty_assessment": payload.kitty_assessment.model_dump(),
            "task": "Explain Kitty's assessment without changing it.",
        }
        try:
            raw = model.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(message, sort_keys=True)},
                ],
                temperature=0,
                max_tokens=int(os.getenv("ZARRY_MAX_TOKENS", "300")),
                response_format={"type": "json_object"},
            )["choices"][0]["message"]["content"]
            parsed = ExplainResponse.model_validate_json(raw or "")
            _validate_grounding(parsed, payload)
        except Exception as exc:
            # Fail closed: invalid model output is never passed to the caller.
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="model returned invalid or ungrounded explanation",
            ) from exc

        parsed.authority = "KITTY_DETERMINISTIC_ENGINE"
        parsed.mode = "explanation_only"
        return parsed

    return app


app = create_app()
