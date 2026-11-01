# ZARRY generated-image storage

Generated images are stored in the Cloudflare R2 bucket `zarrry` (region `WEUR`) through its S3-compatible API. The production public hostname is `https://images.kingzarry.bid`; Cloudflare has confirmed that the custom domain is active and ownership is verified.

The adapter is `zarry_gateway.image_storage.CloudflareR2ImageStorage`.

## Server-only configuration

Set these variables on the Railway **Fast API service** (the service running `api.py`):

- `R2_ENDPOINT_URL`: the account's Cloudflare R2 S3 API endpoint, using HTTPS.
- `R2_ACCESS_KEY_ID`: an R2 API token access key with object-write and object-delete permission for the `zarrry` bucket. Read access is exercised by the public custom domain.
- `R2_SECRET_ACCESS_KEY`: the matching secret.
- `R2_BUCKET`: `zarrry`.
- `R2_PUBLIC_BASE_URL`: `https://images.kingzarry.bid`.

Never put these credentials in frontend variables or source control. Do not use an account-wide Cloudflare API token where scoped R2 object access credentials are available.

## Object behavior

- Generated PNGs use random object keys under `zarry/`.
- Uploads set `Content-Type: image/png` and immutable one-year cache metadata.
- The adapter returns an HTTPS URL rooted at `R2_PUBLIC_BASE_URL`.
- Bucket credentials remain server-side and are never returned to clients.

## Admin storage verification

The authenticated admin-only endpoint is:

`POST /api/assistant/admin/image-storage-test`

It does not call Replicate and does not generate an image. It uploads a small random text object under `zarry/diagnostics/`, retrieves that exact object through the configured public HTTPS hostname, compares the returned bytes, and deletes the temporary object in a `finally` cleanup path. The response contains only the status and public hostname, not credentials or object keys.

Run it with an authenticated administrator session on the Fast API service. A successful response reports `upload: ok`, `public_retrieval: ok`, and `cleanup: ok`. A failure returns a generic HTTP 502; inspect Railway application logs for the corresponding failure context. If the route returns 503, check that all five R2 variables above are present and valid.

## Image-generation gate

The image route uses Hugging Face Inference Providers first with
`Tongyi-MAI/Z-Image-Turbo` explicitly routed through `fal-ai`. It requires
`HF_TOKEN` with Inference Providers permission and access to the model.
Replicate is the secondary provider and requires:

- `REPLICATE_API_TOKEN`
- `ZARRY_REPLICATE_MODEL_VERSION` (immutable 64-character version ID, not a mutable alias)

The provider chain is initialized only when all R2 variables are present and
at least one image provider is configured. Hugging Face is primary when
configured. Replicate is selected only when Hugging Face is unavailable before
dispatch; an ambiguous Hugging Face failure is never retried through
Replicate, preventing duplicate paid generations.

`ZARRY_IMAGE_ENABLED` remains false by default, and the independent `ZARRY_IMAGE_LIVE_SMOKE_APPROVED` gate must also be explicitly true after a successful live smoke test. Both gates are required to enable public generation. R2 storage diagnostics are
initialized independently of provider credentials, so the storage test can
pass before either inference provider is configured.

Do not enable image generation until the admin storage diagnostic passes and
the one-time admin smoke test verifies provider generation, the budget
reservation, durable upload, and public retrieval. See
`HF_IMAGE_BILLING_GATE.md` for the published pricing contract and $2 monthly
cap.
