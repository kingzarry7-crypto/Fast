"""Budget-gated Hugging Face text-to-image adapter.

This adapter is deliberately not wired into the live router until a verified
provider cost resolver and durable image-storage adapter are supplied.
"""
from __future__ import annotations

import os
from uuid import UUID


class HuggingFaceImageProvider:
    """Generate through HF Inference Providers with fail-closed cost controls."""

    name = "huggingface-inference-providers"

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
    ):
        self.api_key = (api_key if api_key is not None else os.getenv("HF_TOKEN", "")).strip()
        self.model = (model if model is not None else os.getenv("ZARRY_IMAGE_MODEL", "")).strip()
        self.ledger = ledger
        self.cost_estimator = cost_estimator
        self.actual_cost_resolver = actual_cost_resolver
        self.storage = storage
        self.client_factory = client_factory or self._default_client_factory

    @staticmethod
    def _default_client_factory(*, api_key: str):
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise RuntimeError("huggingface_hub is not installed") from exc
        return InferenceClient(api_key=api_key)

    def generate(self, prompt: str, *, request_id: UUID, size: str) -> dict:
        if not self.api_key or not self.model:
            raise RuntimeError("Hugging Face image inference is not configured")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Image prompt is required")
        if size not in {"1024x1024", "1024x768", "768x1024"}:
            raise ValueError("Unsupported image size")
        if not callable(self.cost_estimator) or not callable(self.actual_cost_resolver):
            raise RuntimeError("Verified provider pricing and actual-cost reporting are required")
        if self.storage is None or not callable(getattr(self.storage, "save", None)):
            raise RuntimeError("Durable image storage is not configured")

        estimate = self.cost_estimator(self.model, size)
        if estimate is None:
            raise RuntimeError("Provider cost estimate is unavailable; request was not sent")

        # Construct the local client before reserving; this performs no provider
        # request and avoids stranded budget if local setup fails.
        client = self.client_factory(api_key=self.api_key)

        # Reserve before any billable provider call. Unknown outcomes retain the
        # reservation; only a verified actual cost can release it via settlement.
        self.ledger.reserve(request_id, estimate)
        generated = client.text_to_image(prompt=prompt.strip(), model=self.model)
        actual = self.actual_cost_resolver(generated, self.model, size)
        if actual is None:
            raise RuntimeError("Verified actual provider cost is unavailable; reservation retained")
        self.ledger.settle(request_id, actual)

        image_url = self.storage.save(generated, request_id)
        if not isinstance(image_url, str) or not image_url.startswith("https://"):
            raise RuntimeError("Image storage did not return a secure public URL")
        return {
            "request_id": request_id,
            "image_url": image_url,
            "provider": self.name,
            "fallback_used": False,
        }
