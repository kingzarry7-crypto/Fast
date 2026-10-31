# ZARRY Hugging Face image-billing gate

## Decision

Paid Hugging Face image generation remains disabled. Do not wire
`HuggingFaceImageProvider` into `/api/assistant/image` until request-level
cost can be estimated conservatively before dispatch and reconciled from a
verified source after dispatch.

## What the current Hugging Face documentation establishes

- Routed Inference Providers requests are billed at the underlying provider's
  rates; Hugging Face passes through provider costs.
- The Inference Providers settings page exposes a past-month usage breakdown by
  model and provider.
- The documented organization usage API is Enterprise-only, reports daily
  aggregates, rounds costs to cents per row, and may take up to two hours for
  requests to appear. It is not a request-level settlement feed and cannot
  safely settle a per-request microdollar reservation.
- The `InferenceClient.text_to_image` result is an image object; the image
  bytes are not proof of the provider's billed amount.

References:
- https://huggingface.co/docs/inference-providers/pricing
- https://huggingface.co/docs/hub/billing
- https://huggingface.co/docs/inference-providers/register-as-a-provider

## Requirements before enabling

1. Select and pin a specific provider and model; do not use automatic provider
   routing where provider-specific pricing is needed.
2. Obtain an authoritative price schedule and a conservative upper-bound
   estimator for the exact model, provider, and image parameters.
3. Confirm how provider billing behaves for errors, timeouts, retries, and
   partially completed generations.
4. Obtain a request-correlated actual-cost source with sufficient precision and
   latency for settlement. Daily account aggregates rounded to cents are not
   sufficient.
5. Test the estimator and settlement against real provider invoices/usage
   records, including concurrent requests and ambiguous timeouts.
6. Keep the application-side USD 2/month cap, but explain that it is not an
   account-wide Hugging Face spending limit.
7. Only after all gates pass, wire the provider behind a default-off feature
   flag and add an authenticated end-to-end acceptance test.

## Current safe behavior

- The image provider adapter is contract-only and is not wired into the route.
- The image route returns `503 Image generation is unavailable` when no image
  handler is configured.
- Unknown estimates and unknown actual costs fail closed.
- Do not substitute a guessed flat price, image dimensions, or delayed daily
  aggregates for a verified request-level cost.
- No paid inference request should be sent as part of CI or deployment smoke
  tests.
