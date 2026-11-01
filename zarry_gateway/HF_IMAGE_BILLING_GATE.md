# ZARRY image-generation provider and billing policy

## Provider order

ZARRY uses Hugging Face Inference Providers first for Tongyi-MAI's
**Z-Image-Turbo** model, explicitly routed to Fal AI:

- Hugging Face model: `Tongyi-MAI/Z-Image-Turbo`
- Inference provider: `fal-ai`
- Published tariff: **$0.005 per megapixel**, rounded up to the next whole
  megapixel.
- The app currently permits only its existing 1024x1024, 1024x768, and
  768x1024 sizes. The maximum charge under this contract is $0.01 per image.

Official pricing and model references:

- https://fal.ai/models/fal-ai/z-image/turbo
- https://huggingface.co/docs/inference-providers/pricing
- https://huggingface.co/docs/inference-providers/guides/first-api-call

Replicate's pinned PrunaAI Z-Image-Turbo API is the secondary provider. It is
used only when Hugging Face is not configured before dispatch. Its current
published resolution schedule is reserved conservatively at $0.01 before
dispatch.

## Billing contract and the $2 monthly cap

Hugging Face's consumer inference response does not provide ZARRY with a
guaranteed per-request invoice amount. Therefore ZARRY does not describe a
computed estimate as provider-reported actual billing.

For Hugging Face, ZARRY reserves the published Fal per-megapixel tariff for
the requested dimensions before dispatch, then settles the reservation using
the same published tariff evaluated against the returned image dimensions.
This is a conservative tariff settlement, not an invoice-level actual-cost
report. If the image dimensions cannot be read, the reservation is retained
and the image is not stored or returned.

For Replicate, ZARRY reserves the maximum published tier ($0.01) before
dispatch and settles the published tier after a successful prediction.

Both providers use the same atomic PostgreSQL monthly budget ledger. The
application-side limit remains **USD $2.00 per UTC calendar month**. It is not
an account-wide spending limit at Hugging Face or Replicate. Reservations are
never automatically released after a timeout, unknown provider outcome,
settlement failure, or storage failure.

## Fallback and duplicate-charge protection

- Hugging Face is primary whenever its token, fixed model/provider contract,
  cost functions, and durable R2 storage are configured.
- Replicate is selected only when Hugging Face is unavailable before dispatch,
  such as when `HF_TOKEN` is absent.
- If an HF request has started and then fails, times out, or returns an
  ambiguous result, ZARRY does **not** retry through Replicate. The HF
  reservation remains in place because the request may have been accepted and
  billed.
- There is no Hugging Face automatic-provider selection. The route pins
  `provider="fal-ai"` so the cost contract cannot silently change to another
  provider.
- Unknown pricing, unsupported model IDs, unsupported sizes, or missing
  durable storage fail closed before a billable request.

## Server-only configuration

Set these variables on the Railway **Fast API service** that hosts `api.py`:

Required for all image generation:
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`
- `R2_PUBLIC_BASE_URL`

Primary Hugging Face provider:
- `HF_TOKEN` with Inference Providers permission and access to the model.

Secondary Replicate provider:
- `REPLICATE_API_TOKEN`
- `ZARRY_REPLICATE_MODEL_VERSION` (immutable 64-character version ID).

Never put credentials in frontend variables or source control. The image
provider is constructed only when R2 is configured and at least one provider
is configured. If both providers are configured, HF is primary.

## Activation gate

`ZARRY_IMAGE_ENABLED` remains false by default. Keep it false until:

1. The HF model/provider access is confirmed for the configured token.
2. The admin R2 public round-trip diagnostic passes.
3. The one-time, admin-only image smoke test confirms generation, budget
   reservation, durable upload, and public retrieval.
4. The $2 monthly ledger and reservation/settlement migrations are present.

CI tests use fakes and never send paid provider requests. Do not enable
production image generation merely because CI passes.
