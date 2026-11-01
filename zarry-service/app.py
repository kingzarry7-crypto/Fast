""""Isolated, explanation-only ZARRY inference API prototype.

Kitty remains the sole authority for trading decisions. This service has no
market-data, broker, order, or tool-execution integration.
"""
from __future__ import annotations

import hmac
import json
import logging
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

from contract import extract_final_response

logger = logging.getLogger("zarry.service")


SERVICE_EXPLANATION_PROMPT = """You are ZARRY, an explanation-only assistant.
Kitty's deterministic assessment is authoritative. Explain the supplied assessment; never make or change a trading decision.
Never change Kitty's symbol or BUY/SELL/WAIT/NO TRADE decision. Never recommend a different action.
Use only the supplied context. Never invent prices, indicators, candles, fills, account facts, outcomes, probabilities, or confidence.
Write one short, natural-language paragraph explaining why the supplied Kitty decision is preserved, grounded in the context.
Do not include numeric digits, prices, percentages, probabilities, or numeric time labels. Use qualitative wording such as "shorter-term" instead of numeric timeframe labels.
Do not return JSON, labels, markdown fences, or reasoning. Do not place orders or change risk settings."""


def _sanitize_model_value(value):
    """Remove numeric payloads before they reach a model that must not repeat them."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return "numeric detail omitted"
    if isinstance(value, str):
        return "numeric detail omitted" if any(char.isdigit() for char in value) else value
    if isinstance(value, list):
        return [_sanitize_model_value(item) for item in value]
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if any(char.isdigit() for char in str(key)):
                continue
            cleaned[str(key)] = _sanitize_model_value(item)
        return cleaned
    return "detail omitted"


def _sanitize_context_for_model(context: dict) -> dict:
    """Keep qualitative evidence while omitting prices, numeric keys, and time labels."""
    aliases = {
        "trend_4h": "higher_timeframe_trend",
        "direction_1h": "shorter_timeframe_direction",
        "setup_15m": "setup",
        "entry_5m": "entry",
        "stale_minutes": "staleness_present",
        "stop_loss": "stop_loss_available",
        "take_profit": "take_profit_available",
        "take_profit_1": "take_profit_available",
        "take_profit_2": "take_profit_available",
    }
    cleaned = {}
    for key, value in context.items():
        key = str(key)
        if key in {"stop_loss", "take_profit", "take_profit_1", "take_profit_2"}:
            cleaned[aliases[key]] = value is not None
            continue
        if key == "stale_minutes":
            cleaned[aliases[key]] = value is not None and value is not False
            continue
        if key in aliases:
            clean_key = aliases[key]
        elif any(char.isdigit() for char in key):
            continue
        else:
            clean_key = key
        cleaned[clean_key] = _sanitize_model_value(value)
    return cleaned


def _parse_model_explanation(raw: str) -> tuple[str, str]:
    """Extract model prose without trusting model-generated authority fields."""
    text = extract_final_response(raw or "").strip()
    text = re.sub(r"(?is)^\s*```(?:json|text)?\s*|\s*```\s*$", "", text).strip()

    try:
        value = json.loads(text)
        if isinstance(value, dict) and isinstance(value.get("summary"), str):
            return value["summary"].strip(), value.get("uncertainty", "").strip() if isinstance(value.get("uncertainty", ""), str) else ""
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(
        r"(?is)\bSUMMARY\s*:\s*(.*?)\s*\n\s*UNCERTAINTY\s*:\s*(.*?)\s*$",
        text,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Some small models emit a malformed JSON wrapper but a recoverable summary
    # string. Recover only that string; all content is still validated below.
    summary_match = re.search(r'"summary"\s*:\s*("(?:\\.|[^"\\])*")', text, re.IGNORECASE)
    if summary_match:
        try:
            return json.loads(summary_match.group(1)).strip(), ""
        except (json.JSONDecodeError, AttributeError):
            pass

    # Otherwise treat the final response as prose. It must still pass strict
    # length, numeric, and explanation-only checks before it can be returned.
    if text and not text.lstrip().startswith(("{", "[")):
        return text, ""
    raise ValueError("model response did not contain usable explanation prose")


def _deterministic_summary(request: "ExplainRequest") -> str:
    """Build a transparent, qualitative fallback from validated context only."""
    context = request.context
    facts = []
    if context.get("data_fresh") is False or "stale_minutes" in context:
        facts.append("the supplied market context is marked stale")
    elif context.get("data_fresh") is True:
        facts.append("the supplied market context is marked fresh")

    trend = str(context.get("trend_4h", "")).lower()
    direction = str(context.get("direction_1h", "")).lower()
    if trend and direction:
        if trend == direction:
            facts.append("the higher-timeframe trend and shorter-term direction agree")
        else:
            facts.append("the supplied timeframe directions conflict")

    setup = str(context.get("setup_15m", "")).lower()
    if setup in {"mixed", "extended", "pullback_held", "pullback", "breakout", "lower_high_rejected", "bullish_reversal_attempt", "breakdown"}:
        setup_text = {
            "mixed": "the setup is marked mixed",
            "extended": "the setup is marked extended",
            "pullback_held": "the pullback setup is marked held",
            "pullback": "the setup is marked as a pullback",
            "breakout": "the setup is marked as a breakout",
            "lower_high_rejected": "the setup is marked as a rejected lower high",
            "bullish_reversal_attempt": "the setup is marked as a reversal attempt",
            "breakdown": "the setup is marked as a breakdown",
        }[setup]
        facts.append(setup_text)

    entry = str(context.get("entry_5m", "")).lower()
    if entry in {"not_confirmed", "unconfirmed", "late", "bullish_reclaim", "bullish", "bearish_breakdown", "bearish"}:
        entry_text = {
            "not_confirmed": "entry confirmation is not established",
            "unconfirmed": "entry confirmation remains unresolved",
            "late": "the entry is marked late",
            "bullish_reclaim": "the entry context is marked as a bullish reclaim",
            "bullish": "the entry context is marked bullish",
            "bearish_breakdown": "the entry context is marked as a bearish breakdown",
            "bearish": "the entry context is marked bearish",
        }[entry]
        facts.append(entry_text)

    if "stop_loss" not in context or not any(key.startswith("take_profit") for key in context):
        facts.append("risk levels are not fully supplied")
    if not facts:
        facts.append("the explanation is limited to the supplied context")

    reason = "; ".join(facts[:3])
    return (
        f"Explanation-only: deterministic fallback preserves Kitty's {request.kitty_assessment.decision} "
        f"decision because {reason}. No new trading decision is made."
    )


def _deterministic_uncertainty(request: "ExplainRequest") -> str:
    """Describe only limitations that can be inferred directly from supplied context."""
    context = request.context
    if context.get("data_fresh") is False or "stale_minutes" in context:
        return "Data freshness is uncertain and the supplied context may be stale."
    values = {str(value).lower() for value in context.values() if isinstance(value, (str, bool))}
    if any(token in values for token in {"not_confirmed", "unconfirmed", "late", "not confirmed"}):
        return "Entry confirmation remains unresolved in the supplied context."
    trend = str(context.get("trend_4h", "")).lower()
    direction = str(context.get("direction_1h", "")).lower()
    if trend and direction and trend != direction:
        return "The supplied timeframes conflict, so alignment remains uncertain."
    if "stop_loss" not in context or not any(key.startswith("take_profit") for key in context):
        return "Risk levels are not fully represented in the supplied context."
    return "The explanation is limited to supplied context and cannot verify future outcomes."




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
    explanation_source: Literal["model", "deterministic_fallback"] = "model"


NUMERIC_TEXT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![A-Za-z0-9_])")


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
    if any(character.isdigit() for character in output.summary + output.uncertainty):
        raise ValueError("numeric digits are not allowed in explanation text")
    summary_body = re.sub(r"(?i)\bexplanation-only\b\s*[:\-–]?\s*", "", output.summary).strip()
    if len(summary_body.split()) < 8:
        raise ValueError("model explanation is too generic")
    if len(output.uncertainty.split()) < 4:
        raise ValueError("model uncertainty is too generic")
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
            "kitty_decision": payload.kitty_assessment.decision,
            "reason_codes": _sanitize_model_value(payload.kitty_assessment.reason_codes),
            "context": _sanitize_context_for_model(payload.context),
            "task": "Explain Kitty's supplied decision using only qualitative context. Numeric details were deliberately omitted.",
        }
        base_messages = [
            {"role": "system", "content": SERVICE_EXPLANATION_PROMPT},
            {"role": "user", "content": "/no_think\n" + json.dumps(message, sort_keys=True)},
        ]
        last_error = None
        parsed = None
        # Keep retries bounded and every semantic safety gate strict. The model
        # supplies prose only; authority fields are built from the request.
        for attempt in range(2):
            messages = list(base_messages)
            if attempt:
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous response failed server validation: "
                        + str(last_error)
                        + ". Return one short plain-text paragraph only; do not return JSON, labels, or markdown. "
                        "Do not use numeric digits, numeric time labels, "
                        "prices, percentages, probabilities, or numeric claims. Use qualitative wording. "
                        "Preserve Kitty's exact decision and explain only the supplied context."
                    ),
                })
            try:
                raw = model.create_chat_completion(
                    messages=messages,
                    temperature=0,
                    max_tokens=int(os.getenv("ZARRY_MAX_TOKENS", "300")),
                )["choices"][0]["message"]["content"]
                summary, _model_uncertainty = _parse_model_explanation(raw or "")
                if "explanation-only" not in summary.lower():
                    summary = "Explanation-only: " + summary
                uncertainty = _deterministic_uncertainty(payload)
                parsed = ExplainResponse(
                    symbol=payload.symbol,
                    decision=payload.kitty_assessment.decision,
                    summary=summary,
                    uncertainty=uncertainty,
                    cited_fields=list(payload.expected_fields),
                    numeric_claims=[],
                    explanation_source="model",
                )
                _validate_grounding(parsed, payload)
                break
            except Exception as exc:
                last_error = exc
                parsed = None
                logger.warning(
                    "ZARRY explanation validation failed (attempt %s/2): %s",
                    attempt + 1,
                    type(exc).__name__ + ": " + str(exc),
                )

        if parsed is None:
            # Preserve service availability without disguising a model failure:
            # this response is explicitly labeled as a deterministic fallback.
            logger.warning(
                "ZARRY using deterministic explanation fallback after two invalid model attempts: %s",
                type(last_error).__name__ + ": " + str(last_error),
            )
            try:
                parsed = ExplainResponse(
                    symbol=payload.symbol,
                    decision=payload.kitty_assessment.decision,
                    summary=_deterministic_summary(payload),
                    uncertainty=_deterministic_uncertainty(payload),
                    cited_fields=list(payload.expected_fields),
                    numeric_claims=[],
                    explanation_source="deterministic_fallback",
                )
                _validate_grounding(parsed, payload)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="model and deterministic fallback both failed validation",
                ) from exc

        parsed.authority = "KITTY_DETERMINISTIC_ENGINE"
        parsed.mode = "explanation_only"
        return parsed

    return app


app = create_app()
