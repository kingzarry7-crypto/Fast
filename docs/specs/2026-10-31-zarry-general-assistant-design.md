# ZARRY General Assistant Expansion — Design Specification

**Date:** 2026-10-31  
**Status:** Design approved by user; specification submitted for review  
**Repository:** `kingzarry7-crypto/Fast`  
**Branch:** `docs/zarry-general-assistant-design`  
**Related work:** Draft PRs #221 and #222; trading-focused ZARRY design at `docs/specs/2026-10-31-zarry-model-design.md`

## 1. Goal

Extend ZARRY from its existing trading-explanation prototype into the default general-purpose assistant for King Zarry AI across the web app, Telegram, and Discord.

The rollout must preserve the existing working integrations and provider fallbacks until ZARRY demonstrates acceptable quality and reliability. This is a staged product expansion, not a replacement of Kitty or an assumption that the current small model matches frontier hosted models.

## 2. Scope and non-goals

### In scope

- A shared ZARRY gateway used by the web app, Telegram bot, and Discord bot.
- General text conversations using the self-hosted ZARRY model as the preferred provider.
- Existing text providers retained as controlled fallback during rollout.
- Hugging Face image generation through a separately selected and evaluated image model.
- Shared, user-isolated conversation memory with explicit opt-in.
- Centralized authentication, routing, rate limits, request tracing, cost controls, and provider health handling.
- Consistent capability and connection status across all three clients.
- Acceptance tests and gradual rollout before ZARRY becomes the default.

### Out of scope

- Changing Kitty's deterministic trading decisions, market-data authority, risk controls, or order execution.
- Allowing ZARRY to place trades or override BUY, SELL, WAIT, or NO TRADE.
- Removing existing AI providers before acceptance and a separate migration decision.
- Enabling ZARRY by default in production before acceptance.
- Changing Vercel configuration or unrelated production infrastructure.
- Training a frontier model from scratch or promising frontier-model capability from the current small model.
- Image editing in the initial image-generation release; initial image scope is text-to-image.

## 3. Approved architecture

All three clients call one shared gateway:

`Web app / Telegram / Discord → ZARRY Gateway → policy, identity, memory, routing and budget controls`

The gateway routes requests to isolated providers:

- **Text:** self-hosted ZARRY first. Existing approved text providers remain fallback while the new model is evaluated and during the staged migration.
- **Images:** Hugging Face image-generation inference through a dedicated image route and model. Text model output is not treated as generated image content.
- **Trading context:** Kitty remains the authoritative source for market facts, deterministic decisions, risk checks, and order state. ZARRY may explain verified Kitty output but cannot modify it.

The gateway is the common enforcement point. Clients must not independently call paid inference providers or carry Hugging Face/provider secrets.

## 4. Client identity, conversations, and memory

- The web app authenticates through the existing King Zarry web-session mechanism.
- Telegram and Discord requests are authenticated through their existing bot platform identities and authorization rules.
- The gateway maps each authenticated account/platform identity to a stable internal user identity. Linking multiple identities to one account must require an authenticated linking flow; matching display names alone is insufficient.
- Conversation history is scoped to the authenticated user and conversation.
- Cross-client shared memory is opt-in. When enabled, only the same linked internal user can access it across web, Telegram, and Discord.
- Users who do not opt in retain isolated conversation context according to the existing client behavior.
- Memory access, retention, clearing, and deletion must follow the application's privacy controls and be documented in the implementation plan.
- No credentials, provider secrets, broker credentials, or unnecessary sensitive information may be placed in prompts or memory.

## 5. Routing and provider behavior

### Text requests

1. Authenticate the user and enforce account-level and platform-level permissions.
2. Validate request size, supported content, and rate limits.
3. Load only the conversation and memory permitted for that user.
4. Route to the self-hosted ZARRY model when it is healthy and within configured capacity.
5. If ZARRY is unavailable or fails, use an approved existing text provider fallback only when the fallback is enabled, its cost is known, and budget policy permits it.
6. Return a clear provider/fallback status without exposing secrets or internal infrastructure details.

The model's limitations must be communicated honestly. If no provider is safe or available, return a clear unavailable response rather than fabricating completion.

### Image requests

- Route text-to-image requests to the configured Hugging Face image model through the shared gateway.
- Validate prompt length and request parameters; apply platform/user rate limits and output safety checks.
- Return generated image data or a verified image reference and request metadata.
- If generation fails, cost cannot be determined, or the budget is exhausted, report the failure. Do not silently switch to an unapproved paid provider.
- Image editing is deferred until a separate design and acceptance plan.

### Trading-related requests

- Kitty remains the source of truth for all market facts, signal decisions, account state, and order status.
- ZARRY may summarize or explain data explicitly supplied by Kitty.
- ZARRY must not create or alter trading decisions, invoke broker APIs, submit orders, or change risk settings.
- Existing NO TRADE and live-trading safeguards remain authoritative and unchanged.

## 6. Hugging Face usage and spending controls

The user-approved application policy is a maximum of **USD $2 per calendar month in paid Hugging Face inference spend**, shared across ZARRY text and image requests where Hugging Face charges apply. Free credits should be consumed first only if Hugging Face automatically applies them and that behavior is verified.

Implementation requirements:

- Maintain one centralized monthly paid-inference budget ledger for the covered Hugging Face requests.
- Reserve the maximum known request cost atomically before dispatch; use idempotent request IDs to prevent duplicate reservations.
- Reconcile reservations against actual provider-reported cost after completion. Release unused reservation only when the provider result makes that safe.
- Reject paid requests when cost is unknown, price metadata is unavailable, or the remaining budget is insufficient.
- Fail closed on ledger, pricing, or reconciliation errors.
- Record provider/model, request ID, estimated cost, actual cost when available, reservation/reconciliation state, and failure reason. Never log tokens, API keys, or private prompts unnecessarily.
- Provide clear usage visibility and alerts only when those features are actually implemented and verified.
- The application budget controls only requests routed through this gateway. It does not cap unrelated spending elsewhere in the Hugging Face account.
- Do not claim that an application-side cap is a Hugging Face account billing limit. Verify account-level billing/credit behavior separately.

## 7. Security, privacy, and abuse controls

- Keep Hugging Face and other provider credentials server-side in managed secrets.
- Authenticate every client-to-gateway request and every private service-to-service request.
- Enforce per-user and per-platform rate limits, request-size limits, timeouts, and concurrency limits.
- Prevent one user's conversation, memory, images, or budget data from being accessed by another user.
- Treat model output and generated content as untrusted; validate and safely render output.
- Apply platform-appropriate content safety checks to image prompts and outputs.
- Do not expose raw provider errors, private prompts, secrets, or internal network details to clients.
- Record auditable request metadata while minimizing retained personal data.
- Do not allow model-generated tool calls to bypass the application's existing approval gates for consequential actions.

## 8. Reliability and failure handling

- Health-check the gateway and each provider independently.
- Bound provider timeouts, retries, and concurrency. Retries must be safe and idempotent.
- Use the existing text fallback only under the explicit policy described above.
- Do not use text-provider fallback for image generation.
- If the budget service or cost check is unavailable, block paid inference.
- If shared memory is unavailable, do not leak or substitute another user's memory; continue without memory only if the product can clearly and safely do so.
- If the gateway is unavailable, clients show a truthful unavailable state and preserve any locally safe unsent draft where supported.
- Provider failures must not affect Kitty's deterministic analysis or safety paths.

## 9. Observability and operations

Capture structured, privacy-minimized metrics for:

- Request counts and success/error rates by client and provider.
- Model/provider version and fallback frequency.
- End-to-end and provider latency.
- Token/image usage and estimated/actual paid costs where reported.
- Budget reservations, reconciliation failures, and rejected over-budget requests.
- Authentication failures, rate-limit events, and memory-access denials.
- Gateway and provider health, CPU, memory, and storage where available.

Operational dashboards and alerts are implementation deliverables only if the connected infrastructure supports them and they are tested. Logs must not contain credentials or unnecessary user content.

## 10. Acceptance and staged rollout

### Stage 1 — repository and integration audit

- Inspect current `main`, open ZARRY PRs, service code, and web/Telegram/Discord request paths.
- Map existing authentication, identity linking, memory stores, provider fallbacks, and bot permissions.
- Identify duplicate or conflicting routing paths before changing code.
- Confirm what is already implemented versus merely configured or documented.

### Stage 2 — model and provider qualification

- Verify Hugging Face account identity, model availability, license/usage terms, pricing, and supported inference route.
- Select a text-to-image model based on quality, safety, latency, and known cost.
- Benchmark the current ZARRY text model on representative general-assistant tasks: factual question answering, writing, summarization, simple coding, instruction following, and refusal/uncertainty.
- Document limitations and fallback criteria. Do not imply that a 3B quantized model is equivalent to a frontier model.

### Stage 3 — gateway and policy implementation

- Implement shared authenticated routes and typed request/response contracts.
- Centralize user identity, conversation routing, opt-in memory, provider selection, rate limits, and request IDs.
- Implement the shared Hugging Face paid-inference ledger and fail-closed budget guard.
- Keep secrets server-side and isolate Kitty from general assistant routing.

### Stage 4 — client integration

- Connect web, Telegram, and Discord to the shared gateway.
- Preserve existing authentication and permissions.
- Ensure all clients observe the same account-level memory and budget policy.
- Keep existing text providers available as controlled fallbacks.
- Do not duplicate provider credentials or budget enforcement in clients.

### Stage 5 — automated and end-to-end acceptance

Required tests include:

- Authentication and identity-linking correctness across all clients.
- User and conversation memory isolation; opt-in, opt-out, and clearing behavior.
- Shared gateway routing and provider fallback behavior.
- Hugging Face cost reservation, concurrent requests, idempotency, reconciliation, unknown-cost rejection, and monthly cap exhaustion.
- Image generation success, failure, safety handling, and no-paid-fallback behavior.
- Rate limits, oversized requests, timeouts, provider outage, and gateway outage.
- Verification that Kitty decisions, NO TRADE protections, broker paths, and live-trading state remain unchanged.
- Regression tests for existing web, Telegram, and Discord functions.

### Stage 6 — private pilot and default migration

- Keep `ZARRY_ENABLED` false/default-off in production until the required tests pass and a separate enablement approval is given.
- Pilot with controlled users and monitor quality, latency, fallback rate, cost, and failures.
- Make ZARRY the default general assistant only after acceptance and explicit rollout approval.
- Retain existing providers as fallback until sustained reliability supports a separate decision to remove them.
- No production deployment, provider removal, or live-trading change is authorized by this design approval alone.

## 11. Rollback

- Keep the previous client routing configuration and provider path available during rollout.
- Feature flags must allow ZARRY text, image generation, and shared-memory functionality to be disabled independently.
- On quality, safety, cost, or availability regression, disable the affected feature and restore the existing provider path.
- Rollback must not alter Kitty's independent trading service or its risk controls.

## 12. Open implementation questions

These must be answered with repository inspection or verified provider evidence during planning, not guessed:

- Which existing text providers are currently configured, healthy, and approved as fallbacks?
- What stable account-linking mechanism exists for web, Telegram, and Discord?
- Which memory store and privacy controls can support opt-in cross-client memory without cross-user leakage?
- Which Hugging Face image models and inference providers are currently available to the connected account, and what are their actual per-request costs?
- Can provider pricing and actual usage be obtained reliably enough to enforce the $2 application cap? If not, paid inference remains disabled until a safe cost bound is available.
- What representative latency and quality thresholds are appropriate for the current self-hosted text model and selected image model?

## 13. Approval record

The user approved the following design decisions on 2026-10-31:

- ZARRY is intended to become the default general assistant across web, Telegram, and Discord after acceptance.
- A shared gateway centralizes authentication, memory, routing, rate limits, and budget enforcement.
- Self-hosted ZARRY is the preferred text model; existing text providers remain fallback until acceptance.
- Hugging Face supplies image generation through a separate image model and shared gateway.
- Shared cross-client memory is opt-in and user-isolated.
- Paid Hugging Face inference is subject to a shared USD $2/month application cap, using free credits first only if automatic credit use is verified.
- Unknown costs, budget-service failures, and over-budget requests fail closed.
- Kitty remains the separate deterministic trading authority; ZARRY cannot alter decisions or execute trades.
- Rollout is staged; production enablement and provider removal require separate approval.

**Authorization boundary:** The user authorized preparation of this design specification. Implementation planning, code changes, merges, production deployment, production flag changes, and live-trading changes remain separate steps with their own review and approval gates.
