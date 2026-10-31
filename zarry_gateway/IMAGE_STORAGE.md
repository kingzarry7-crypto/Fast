# ZARRY generated-image storage

Generated images are stored in Cloudflare R2 through its S3-compatible API. The verified bucket in the connected Cloudflare account is `zarrry` (region `WEUR`).
The adapter is `zarry_gateway.image_storage.CloudflareR2ImageStorage`.

## Server-only configuration

Set these variables on the Fast API service that will host the gateway:

- `R2_ENDPOINT_URL`: the account's Cloudflare R2 S3 API endpoint, using HTTPS.
- `R2_ACCESS_KEY_ID`: an R2 API token access key with object-write permission for the target bucket.
- `R2_SECRET_ACCESS_KEY`: the matching secret.
- `R2_BUCKET`: `zarrry`.
- `R2_PUBLIC_BASE_URL`: `https://pub-93af13628c2041bfb07c627e14b65ebe.r2.dev` for development only. This bucket currently has no custom domain connected; use a Cloudflare custom domain before production.

Never put these credentials in frontend variables or source control. Do not use an account-wide Cloudflare API token where scoped R2 object access credentials are available.

## Object behavior

- Uploads PNG-encoded image bytes using a random object key under `zarry/`.
- Sets `Content-Type: image/png` and immutable one-year cache metadata.
- Returns a URL rooted at the configured HTTPS public base URL.
- Does not expose bucket credentials to the client.

## Rollout status

The adapter has contract tests using an injected S3-compatible client. It has not
been connected to a live R2 bucket or deployed. A bucket, scoped credentials,
public hostname, and an authorized integration test are still required.
The image route remains unavailable until the provider, verified cost estimator,
actual-cost reconciliation, and storage are wired together behind the default-off
feature flag.
