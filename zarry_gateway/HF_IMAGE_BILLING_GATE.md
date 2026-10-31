# ZARRY image-generation billing decision

## Decision

ZARRY uses the direct Replicate API for `prunaai/z-image-turbo`, not Hugging
Face-routed billing. This avoids relying on delayed Hugging Face aggregate usage
records for request settlement. The Hugging Face token is not used for this
provider path.

Official model pricing page:
https://replicate.com/prunaai/z-image-turbo

The published resolution tiers are:

| Output pixels | Published price |
| ---: | ---: |
| Up to 500,000 | $0.0025 |
| Up to 1,000,000 | $0.005 |
| Up to 2,000,000 | $0.01 |

The model page identifies this as PrunaAI's optimized Z-Image-Turbo model,
based on Tongyi-MAI's Z-Image-Turbo. It is not interchangeable with the
unoptimized base model identifier.

## Budget behavior

- The adapter rejects outputs above 2 megapixels.
- It reserves the maximum currently published tier ($0.01) before submitting
  a prediction. This is conservative across all supported resolutions.
- Once Replicate reports `succeeded`, it settles the reservation using the
  published tier for the requested output dimensions.
- Failed, timed-out, or ambiguous predictions retain their reservation. They
  are not automatically retried or released because the provider may have
  accepted the request before the client observed the failure.
- The existing PostgreSQL USD 2/month ledger remains the application-side cap.
  It is not an account-wide Replicate spending limit.
- Price schedules can change. Before production activation, re-check the
  provider's published price and update the price contract/tests if it changes.

## Required server configuration

Set these on the **Fast API service** that hosts `api.py`, not only on the
separate ZARRY model-inference service:

- `REPLICATE_API_TOKEN`: direct Replicate API token.
- `ZARRY_REPLICATE_MODEL_VERSION`: an immutable version ID copied from the
  selected Replicate model's API/version page.
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_PUBLIC_BASE_URL`

Never put credentials in frontend variables or source control. The adapter is
constructed only when every required variable exists. Invalid image-storage
configuration must not disable the separate ZARRY text gateway.

## One-time admin smoke-test database migration

Before deploying the admin smoke-test endpoint, apply the repository's
checksum-tracked PostgreSQL migrations explicitly. The new
`003_image_smoke_lock.sql` migration provisions the globally unique,
one-use claim and audit row. The application request does not create or alter
tables and therefore does not need schema-owner privileges.

Use a migration-capable PostgreSQL connection in the deployment environment:

```bash
export ZARRY_MIGRATION_DATABASE_URL='postgresql://...'
export ZARRY_ALLOW_MIGRATIONS=1
python scripts/apply_zarry_migrations.py --apply
```

The runner uses an advisory transaction lock, checks migration checksums, and
is idempotent. Run it as an explicit release/operations step; do not add it to
application startup. The Fast API runtime database role needs ordinary
SELECT/INSERT/UPDATE access to `zarry_image_smoke_test_lock` after the
migration is applied. Keep migration credentials out of frontend variables
and source control.

## Activation

`ZARRY_IMAGE_ENABLED` defaults to false. Keep it false until the Replicate
token and immutable model version are configured on the Fast API service,
the R2 upload path is verified, and a user-approved low-cost live smoke test
confirms the provider and billing behavior. CI tests use fakes and never send
paid provider requests.

## Safety limits

- No automatic provider fallback.
- No Hugging Face token is sent to Replicate.
- No unpinned model version or automatic model alias.
- No output URL is downloaded unless it uses HTTPS on a Replicate delivery
  hostname.
- The route remains unavailable when the feature flag is off or provider
  configuration is incomplete.
