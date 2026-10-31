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

The image route uses direct Replicate Z-Image-Turbo and requires these additional server-only variables on the same Railway service:

- `REPLICATE_API_TOKEN`
- `ZARRY_REPLICATE_MODEL_VERSION` (immutable 64-character version ID, not a mutable alias)

`ZARRY_IMAGE_ENABLED` remains false by default. R2 storage diagnostics are initialized independently of Replicate, so the storage test can pass before Replicate is configured. The image provider is constructed only when both Replicate variables and all R2 variables are present.

Do not enable image generation until the admin storage diagnostic passes and a separately approved, low-cost Replicate generation has been uploaded and retrieved through the public hostname.
