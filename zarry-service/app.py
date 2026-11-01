""""Isolated, explanation-only ZARRY inference API prototype.

Kitty remains the sole authority for trading decisions. This service has no
market-data, broker, order, or tool-execution integration.
"""
from __future__ import annotations

import hmac
from copy import deepcopy
import json
import os
import re
import resource
import shutil
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from contract import MODEL_OUTPUT_SCHEMA, SYSTEM_PROMPT, extract_final_response


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KittyAssessment(StrictModel):
    decision: Literal["BUY", "SELL", "WAIT", "NO TRADE"]
    reason_codes: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: list[str]) -> list[str]:
        if any(not code or len(code) > 80 for code in value):
            raise ValueError("reason codes must contain 1 to 80 characters")
        return value


class ExplainRequest(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    timestamp: str = Field(min_length=10, max_length=40)
    context: dict[str, Any]
    expected_fields: list[str] = Field(default_factory=list, max_length=80)
    kitty_assessment: KittyAssessment
    task: Literal["explain"] = "explain"

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        age_limit = int(os.getenv("ZARRY_MAX_CONTEXT_AGE_SECONDS", "86400"))
        age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        if age_limit > 0 and age > age_limit:
            raise ValueError("market context timestamp is stale")
        if age < -60:
            raise ValueError("market context timestamp is in the future")
        return value

    @field_validator("expected_fields")
    @classmethod
    def validate_expected_fields(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(not key or len(key) > 80 for key in value):
            raise ValueError("expected fields must be unique, non-empty context keys")
        return value

    @model_validator(mode="after")
    def expected_fields_must_exist_in_context(self):
        if not set(self.expected_fields).issubset(self.context):
            raise ValueError("expected fields must be present in context")
        return self

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
            if isinstance(item, str) and len(item) > 1000:
                raise ValueError("context strings are limited to 1000 characters")
            if isinstance(item, float) and (item != item or abs(item) == float("inf")):
                raise ValueError("context numbers must be finite")
        return value


class ExplainResponse(StrictModel):
    symbol: Literal["BTCUSD", "XAUUSD"]
    decision: Literal["BUY", "SELL", "WAIT", "NO TRADE"]
    summary: str = Field(min_length=60, max_length=3000)
    uncertainty: str = Field(min_length=20, max_length=1500)
    cited_fields: list[str] = Field(max_length=80)
    numeric_claims: list[float | int] = Field(max_length=0)
    authority: Literal["KITTY_DETERMINISTIC_ENGINE"] = "KITTY_DETERMINISTIC_ENGINE"
    mode: Literal["explanation_only"] = "explanation_only"


NUMERIC_TEXT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![A-Za-z0-9_-])")


def _extract_numeric_text_claims(*texts: str) -> set[float]:
    claims: set[float] = set()
    for text in texts:
        for token in NUMERIC_TEXT_RE.findall(text or ""):
            claims.add(float(token.replace(",", "").rstrip("%")))
    return claims


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
    summary_body = re.sub(r"(?i)\\bexplanation-only\\b\\s*[:\\-–]?\\s*", "", output.summary).strip()
    summary_words = re.findall(r"[A-Za-z][A-Za-z'-]*", summary_body)
    # Structured-output fragments can satisfy JSON schema while not being explanations.
    if any(mark in summary_body for mark in ("{", "}", "[", "]", chr(34))) or re.search(
        r"(?i)\\b(?:symbol|decision|summary|uncertainty|cited_fields|numeric_claims)\\s*:",
        summary_body,
    ):
        raise ValueError("model explanation contains a malformed structured-output fragment")
    if len(summary_words) < 8 or len(set(word.lower() for word in summary_words)) / len(summary_words) < 0.55:
        raise ValueError("model explanation is too generic or repetitive")
    uncertainty_words = re.findall(r"[A-Za-z][A-Za-z'-]*", output.uncertainty)
    if len(uncertainty_words) < 4 or len(set(word.lower() for word in uncertainty_words)) / len(uncertainty_words) < 0.45:
        raise ValueError("model uncertainty is too generic or repetitive")
    if not set(output.cited_fields).issubset(request.context):
        raise ValueError("model cited fields absent from supplied context")
    if request.expected_fields and set(request.expected_fields) != set(output.cited_fields):
        raise ValueError("model cited_fields must exactly match expected_fields")
    if output.numeric_claims:
        raise ValueError("numeric claims are disabled in qualitative-only explanations")
    available_numbers = {
        float(value)
        for value in request.context.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    declared_numbers = {float(value) for value in output.numeric_claims}
    if not declared_numbers.issubset(available_numbers):
        raise ValueError("model produced an ungrounded numeric claim")
    text_numbers = _extract_numeric_text_claims(output.summary, output.uncertainty)
    if not text_numbers.issubset(declared_numbers):
        raise ValueError("model used an undeclared numeric claim in its explanation")


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

    app = FastAPI(title="ZARRY Inference Service", version="1.0.0", lifespan=lifespan)
    app.state.request_metrics = {"requests": 0, "errors": 0}

    @app.middleware("http")
    async def request_metadata(request: Request, call_next):
        import time
        candidate_id = request.headers.get("X-Request-ID", "")[:128]
        request_id = candidate_id if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", candidate_id) else str(uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        request.app.state.request_metrics["requests"] += 1
        if response.status_code >= 500:
            request.app.state.request_metrics["errors"] += 1
        response.headers["X-Request-ID"] = request_id
        response.headers["X-ZARRY-Latency-Ms"] = str(round((time.perf_counter() - started) * 1000, 2))
        response.headers["X-ZARRY-API-Version"] = "1.0.0"
        return response

    async def authenticate(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = os.getenv("ZARRY_API_KEY", "")
        if not expected:
            raise HTTPException(status_code=503, detail="service authentication is not configured")
        parts = authorization.split() if authorization else []
        supplied = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""
        if not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/")
    async def index():
        return {
            "service": "ZARRY",
            "status": "alive",
            "description": "Explanation-only model service. Kitty remains the decision authority.",
            "endpoints": {
                "health": "/health",
                "readiness": "/ready",
                "explain": "POST /v1/explain (Bearer API key required)",
                "api_docs": "/docs",
            },
            "mode": "explanation_only",
        }

    @app.get("/health")
    async def health():
        return {"status": "alive", "service": "zarry"}

    @app.get("/ready")
    async def ready(request: Request):
        if request.app.state.model is None:
            raise HTTPException(status_code=503, detail="model is not loaded")
        return {"status": "ready", "model_loaded": True, "model": os.getenv("ZARRY_MODEL_REPO", "configured-model"), "api_version": "1.0.0"}

    @app.get("/metrics", dependencies=[Depends(authenticate)])
    async def metrics(request: Request):
        usage = resource.getrusage(resource.RUSAGE_SELF)
        model_path = os.getenv("ZARRY_MODEL_PATH", "").strip()
        disk = shutil.disk_usage(model_path if model_path and os.path.exists(model_path) else "/")
        counts = dict(request.app.state.request_metrics)
        return {
            "api_version": "1.0.0",
            "requests_total": counts["requests"],
            "server_errors_total": counts["errors"],
            "process_cpu_seconds": round(time.process_time(), 3),
            "process_max_rss_mb": round(usage.ru_maxrss / 1024, 2),
            "disk_free_mb": round(disk.free / (1024 * 1024), 2),
        }

    @app.post("/v1/explain", response_model=ExplainResponse, dependencies=[Depends(authenticate)])
    def explain(payload: ExplainRequest, request: Request):
        model = request.app.state.model
        if model is None:
            raise HTTPException(status_code=503, detail="model is not loaded")
        message = {
            "symbol": payload.symbol,
            "timestamp": payload.timestamp,
            "context": payload.context,
            "expected_fields": payload.expected_fields,
            "kitty_assessment": payload.kitty_assessment.model_dump(),
            "task": "Explain Kitty's assessment without changing it.",
        }
        try:
            output_schema = deepcopy(MODEL_OUTPUT_SCHEMA)
            if payload.expected_fields:
                cited_fields_schema = output_schema["properties"]["cited_fields"]
                cited_fields_schema["items"] = {"type": "string", "enum": payload.expected_fields}
                cited_fields_schema["minItems"] = len(payload.expected_fields)
                cited_fields_schema["maxItems"] = len(payload.expected_fields)
            raw = model.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "/no_think\n" + json.dumps(message, sort_keys=True)},
                ],
                temperature=0,
                max_tokens=int(os.getenv("ZARRY_MAX_TOKENS", "300")),
                response_format={"type": "json_object", "schema": output_schema},
                chat_template_kwargs={"enable_thinking": False},
            )["choices"][0]["message"]["content"]
            parsed = ExplainResponse.model_validate_json(extract_final_response(raw or ""))
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
