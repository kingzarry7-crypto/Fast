"""Cloudflare R2-backed durable image storage (S3-compatible API)."""
from __future__ import annotations

import os
from uuid import uuid4
from urllib.parse import urlsplit


class CloudflareR2ImageStorage:
    """Store generated PNGs in R2 and return their HTTPS public URL.

    Configure R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET, and R2_PUBLIC_BASE_URL on the server. Never expose R2
    credentials to clients.
    """

    def __init__(
        self,
        *,
        bucket: str,
        public_base_url: str,
        client=None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ):
        self.bucket = (bucket or "").strip()
        self.public_base_url = (public_base_url or "").strip().rstrip("/")
        parsed = urlsplit(self.public_base_url)
        if not self.bucket:
            raise ValueError("R2 bucket is required")
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("R2 public base URL must be an HTTPS URL")
        self.client = client or self._make_client(
            endpoint_url=endpoint_url or os.getenv("R2_ENDPOINT_URL", ""),
            access_key_id=access_key_id or os.getenv("R2_ACCESS_KEY_ID", ""),
            secret_access_key=secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY", ""),
        )

    @staticmethod
    def _make_client(*, endpoint_url: str, access_key_id: str, secret_access_key: str):
        if not endpoint_url.startswith("https://") or not access_key_id or not secret_access_key:
            raise RuntimeError("Cloudflare R2 credentials and HTTPS endpoint are not configured")
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for Cloudflare R2 image storage") from exc
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def save(self, image, request_id) -> str:
        # Provider image objects are PIL-compatible; normalize to PNG before upload.
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        payload = buffer.getvalue()
        if not payload:
            raise RuntimeError("Generated image encoded to an empty payload")
        key = f"zarry/{uuid4().hex}.png"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType="image/png",
            CacheControl="public, max-age=31536000, immutable",
        )
        return f"{self.public_base_url}/{key}"
