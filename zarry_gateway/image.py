"""Budget-gated Hugging Face text-to-image adapter.

This adapter uses a fixed HF-routed Fal Z-Image-Turbo price contract and durable
image storage, with a conservative reservation before provider dispatch.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
import os
from uuid import UUID


HF_ZIMAGE_MODEL = "Tongyi-MAI/Z-Image-Turbo"
HF_ZIMAGE_PROVIDER = "fal-ai"
HF_ZIMAGE_PRICE_PER_MEGAPIXEL_USD = Decimal("0.005")
HF_ZIMAGE_MAX_PIXELS = 2_000_000
HF_ZIMAGE_MAX_RESERVATION_USD = "0.01"


def _fal_zimage_cost_for_dimensions(width: int, height: int) -> str:
    if (isinstance(width, bool) or isinstance(height, bool)
            or not isinstance(width, int) or not isinstance(height, int)
            or width <= 0 or height <= 0):
        raise ValueError("Image dimensions must be positive integers")
    pixels = width * height
    if pixels > HF_ZIMAGE_MAX_PIXELS:
        raise ValueError("Image exceeds the supported 2-megapixel limit")
    billable_megapixels = (Decimal(pixels) / Decimal(1_000_000)).to_integral_value(
        rounding=ROUND_CEILING
    )
    return format((billable_megapixels * HF_ZIMAGE_PRICE_PER_MEGAPIXEL_USD).normalize(), "f")


def fal_zimage_turbo_cost_usd(model: str, size: str) -> str:
    """Conservative published Fal tariff for HF-routed Z-Image Turbo."""
    if model != HF_ZIMAGE_MODEL:
        raise ValueError("No verified price contract exists for this Hugging Face model")
    try:
        width_text, height_text = size.split("x", 1)
        width, height = int(width_text), int(height_text)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("Image size must be WIDTHxHEIGHT")
    return _fal_zimage_cost_for_dimensions(width, height)


def fal_zimage_turbo_reservation_usd(model: str, size: str) -> str:
    """Reserve the maximum tariff for every supported output before dispatch."""
    # Validate the model and requested dimensions before reserving.
    fal_zimage_turbo_cost_usd(model, size)
    return HF_ZIMAGE_MAX_RESERVATION_USD


def fal_zimage_turbo_settlement_usd(image, model: str, size: str) -> str | None:
    """Settle the published per-megapixel tariff from the returned image dimensions.

    Hugging Face does not return a guaranteed per-request billing amount to
    inference clients. This is therefore a conservative tariff settlement,
    not a claim that it is the provider's invoice-level actual cost.
    """
    if model != HF_ZIMAGE_MODEL:
        return None
    dimensions = getattr(image, "size", None)
    if not isinstance(dimensions, tuple) or len(dimensions) != 2:
        return None
    try:
        return _fal_zimage_cost_for_dimensions(dimensions[0], dimensions[1])
    except (TypeError, ValueError):
        return None


class HuggingFaceImageProvider:
    """Generate through pinned HF-routed Fal Z-Image Turbo with budget gating."""

    name = "huggingface-fal-z-image-turbo"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        ledger,
        cost_estimator,
        actual_cost_resolver,
        storage,
        client_factory=None,
        provider: str = HF_ZIMAGE_PROVIDER,
    ):
        self.api_key = (api_key if api_key is not None else os.getenv("HF_TOKEN", "")).strip()
        self.model = (model if model is not None else os.getenv("ZARRY_IMAGE_MODEL", "")).strip()
        self.ledger = ledger
        self.cost_estimator = cost_estimator
        self.actual_cost_resolver = actual_cost_resolver
        self.storage = storage
        self.provider = provider
        self.client_factory = client_factory or self._default_client_factory

    @staticmethod
    def _default_client_factory(*, api_key: str):
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise RuntimeError("huggingface_hub is not installed") from exc
        return InferenceClient(api_key=api_key)

    def is_configured(self) -> bool:
        return bool(
            self.api_key and self.model == HF_ZIMAGE_MODEL
            and self.provider == HF_ZIMAGE_PROVIDER
            and callable(self.cost_estimator)
            and callable(self.actual_cost_resolver)
            and self.storage is not None
            and callable(getattr(self.storage, "save", None))
        )

    def generate(self, prompt: str, *, request_id: UUID, size: str) -> dict:
        if not self.api_key or not self.model:
            raise RuntimeError("Hugging Face image inference is not configured")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Image prompt is required")
        if size not in {"1024x1024", "1024x768", "768x1024"}:
            raise ValueError("Unsupported image size")
        if not callable(self.cost_estimator) or not callable(self.actual_cost_resolver):
            raise RuntimeError("Verified provider pricing and tariff settlement are required")
        if self.storage is None or not callable(getattr(self.storage, "save", None)):
            raise RuntimeError("Durable image storage is not configured")

        estimate = self.cost_estimator(self.model, size)
        if estimate is None:
            raise RuntimeError("Provider cost estimate is unavailable; request was not sent")

        # Construct the local client before reserving; this performs no provider
        # request and avoids stranded budget if local setup fails.
        client = self.client_factory(api_key=self.api_key)

        # Reserve before any billable provider call. Unknown outcomes retain the
        # reservation; only the published output tariff can settle it.
        self.ledger.reserve(request_id, estimate)
        width_text, height_text = size.split("x", 1)
        width, height = int(width_text), int(height_text)
        generated = client.text_to_image(
            prompt=prompt.strip(), model=self.model, provider=self.provider,
            width=width, height=height,
        )
        actual = self.actual_cost_resolver(generated, self.model, size)
        if actual is None:
            raise RuntimeError("Verified output dimensions are unavailable; reservation retained")
        self.ledger.settle(request_id, actual)

        image_url = self.storage.save(generated, request_id)
        if not isinstance(image_url, str) or not image_url.startswith("https://"):
            raise RuntimeError("Image storage did not return a secure public URL")
        return {
            "request_id": request_id,
            "image_url": image_url,
            "provider": self.name,
            "fallback_used": False,
            "budget_reserved_usd": str(estimate),
        }



class HuggingFaceFirstImageProvider:
    """Use HF as primary; use Replicate only when HF is unavailable pre-dispatch.

    Any exception after the HF request starts is treated as an ambiguous
    provider outcome. It is propagated without a Replicate retry to prevent
    duplicate billable generations.
    """

    def __init__(self, huggingface_provider, replicate_fallback=None):
        self.huggingface_provider = huggingface_provider
        self.replicate_fallback = replicate_fallback
        self.storage = (
            getattr(huggingface_provider, "storage", None)
            or getattr(replicate_fallback, "storage", None)
        )

    def generate(self, prompt: str, *, request_id, width: int, height: int) -> dict:
        hf_token_present = bool(
            getattr(self.huggingface_provider, "api_key", "").strip()
        ) if self.huggingface_provider is not None else False
        primary_ready = (
            self.huggingface_provider is not None
            and callable(getattr(self.huggingface_provider, "is_configured", None))
            and self.huggingface_provider.is_configured()
        )
        if hf_token_present and not primary_ready:
            # A configured HF credential with an incomplete/unknown price or
            # storage contract must block the whole request, not silently switch.
            raise RuntimeError("Hugging Face image billing or storage contract is incomplete")
        if primary_ready:
            # Deliberately do not catch errors here: once dispatched, the HF
            # request may have been billed even if the client sees a timeout.
            return self.huggingface_provider.generate(
                prompt, request_id=request_id, size=f"{width}x{height}"
            )
        if self.replicate_fallback is None:
            raise RuntimeError("Hugging Face is not configured and no fallback provider is available")
        result = self.replicate_fallback.generate(
            prompt, request_id=request_id, width=width, height=height
        )
        if not isinstance(result, dict):
            raise RuntimeError("Replicate fallback returned an invalid image result")
        result = dict(result)
        result["fallback_used"] = True
        return result
