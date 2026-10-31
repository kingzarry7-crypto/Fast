"""Direct Replicate adapter for PrunaAI Z-Image-Turbo.

Pricing is taken from the model's published resolution schedule. The adapter
pins a Replicate model version, reserves the published maximum before dispatch,
and settles the published tier only after a successful prediction.
"""
from __future__ import annotations

from decimal import Decimal
from io import BytesIO
import os
import re
import time
from urllib.parse import urlsplit

import requests


MODEL = "prunaai/z-image-turbo"
MAX_PIXELS = 2_000_000
MAX_PRICE_USD = Decimal("0.01")


def replicate_zimage_turbo_cost_usd(width: int, height: int) -> str:
    """Return the model's published per-output-image price for given pixels."""
    if isinstance(width, bool) or isinstance(height, bool):
        raise ValueError("Image dimensions must be positive integers")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive integers")
    pixels = width * height
    if pixels > MAX_PIXELS:
        raise ValueError("Image exceeds the published 2-megapixel pricing limit")
    if pixels <= 500_000:
        return "0.0025"
    if pixels <= 1_000_000:
        return "0.005"
    return "0.01"


class ReplicateZImageTurboProvider:
    """Generate one image through a pinned Replicate version with budget gating."""

    name = "replicate-z-image-turbo"

    def __init__(
        self,
        *,
        api_token: str | None = None,
        model_version: str | None = None,
        ledger,
        storage,
        session=None,
        poll_interval_seconds: float = 1.0,
        max_polls: int = 120,
    ):
        self.api_token = (api_token if api_token is not None else os.getenv("REPLICATE_API_TOKEN", "")).strip()
        self.model_version = (model_version if model_version is not None else os.getenv("ZARRY_REPLICATE_MODEL_VERSION", "")).strip()
        self.ledger = ledger
        self.storage = storage
        self.session = session or requests.Session()
        self.poll_interval_seconds = max(0.1, float(poll_interval_seconds))
        self.max_polls = max(1, min(int(max_polls), 300))

    def generate(self, prompt: str, *, request_id, width: int, height: int) -> dict:
        if not self.api_token or not self.model_version:
            raise RuntimeError("Replicate token and pinned Z-Image-Turbo version are required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.model_version):
            raise RuntimeError("Replicate model version must be an immutable 64-character version ID")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Image prompt is required")
        price = Decimal(replicate_zimage_turbo_cost_usd(width, height))
        if self.storage is None or not callable(getattr(self.storage, "save", None)):
            raise RuntimeError("Durable image storage is not configured")

        # The largest currently published tier is reserved before dispatch.
        # This prevents a price-tier mismatch from exceeding the app's cap.
        self.ledger.reserve(request_id, MAX_PRICE_USD)
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        }
        try:
            response = self.session.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={
                    "version": self.model_version,
                    "input": {"prompt": prompt.strip(), "width": width, "height": height},
                },
                timeout=(10, 75),
            )
            response.raise_for_status()
            prediction = response.json()
            prediction_id = prediction.get("id")
            get_url = prediction.get("urls", {}).get("get")
            if not prediction_id or not isinstance(get_url, str):
                raise RuntimeError("Replicate returned an invalid prediction response")
            parsed_get = urlsplit(get_url)
            if parsed_get.scheme != "https" or parsed_get.hostname != "api.replicate.com":
                raise RuntimeError("Replicate returned an untrusted prediction URL")

            for attempt in range(self.max_polls):
                status = prediction.get("status")
                if status == "succeeded":
                    break
                if status in {"failed", "canceled"}:
                    raise RuntimeError("Replicate image prediction did not succeed")
                if attempt:
                    time.sleep(self.poll_interval_seconds)
                poll = self.session.get(get_url, headers=headers, timeout=(10, 30))
                poll.raise_for_status()
                prediction = poll.json()
            else:
                # An unknown outcome retains its reservation. Never retry a
                # possibly billable prediction automatically.
                raise TimeoutError("Replicate prediction did not reach a terminal state")

            output = prediction.get("output")
            output_url = output[0] if isinstance(output, list) and output else output
            if not isinstance(output_url, str):
                raise RuntimeError("Replicate prediction returned no image")
            parsed_output = urlsplit(output_url)
            if (
                parsed_output.scheme != "https"
                or not parsed_output.hostname
                or not (
                    parsed_output.hostname == "replicate.delivery"
                    or parsed_output.hostname.endswith(".replicate.delivery")
                )
                or parsed_output.username
                or parsed_output.password
            ):
                raise RuntimeError("Replicate returned an untrusted image URL")
            image_response = self.session.get(output_url, timeout=(10, 60))
            image_response.raise_for_status()
            try:
                from PIL import Image
            except ImportError as exc:
                raise RuntimeError("Pillow is required for Replicate image decoding") from exc
            image = Image.open(BytesIO(image_response.content)).convert("RGB")

            # Replicate's published tariff is resolution-based and deterministic
            # for this pinned model family; settle the matching tier after success.
            self.ledger.settle(request_id, price)
            image_url = self.storage.save(image, request_id)
            if not isinstance(image_url, str) or not image_url.startswith("https://"):
                raise RuntimeError("Image storage did not return a secure public URL")
            return {
                "request_id": request_id,
                "image_url": image_url,
                "provider": self.name,
                "fallback_used": False,
            }
        except Exception:
            # Do not release on ambiguous errors: the provider may have accepted
            # and billed the prediction before the client observed the failure.
            raise
