# ZARRY Chat Response Reliability Design

**Status:** Proposed for user review  
**Branch:** `fix/zarry-chat-response-latency`  
**Base:** `main`

## Problem

Production health and authenticated smoke checks prove that Fast can reach the private ZARRY service, but they do not prove that a normal message reliably produces a visible answer in the signed-in web chat. Production observations include long request durations (roughly 70–133 seconds in Fast chat requests) and slow Qwen responses. The web chat hook currently removes the streaming assistant placeholder after a stream error and silently retries through the non-streaming endpoint. This can leave the user waiting without a useful explanation.

## Goals

1. Make normal text chat return a visible answer or a clear, actionable failure.
2. Keep Qwen3 1.7B on the private Railway ZARRY service as the preferred model.
3. Bound waiting time and prevent a slow Qwen request from making the UI appear permanently stuck.
4. Use an already-configured, verified fallback provider only when available; never assume a provider is configured or healthy.
5. Preserve authenticated access, Kitty's exclusive trading decision authority, and all live-trading safety gates.
6. Verify the full signed-in web-chat request/response path, not just service health or a direct model smoke test.

## Non-goals and constraints

- Do not change or deploy anything on Vercel.
- Do not enable live trading or change Kitty's decision authority.
- Do not reintroduce SmolLM3 routing.
- Do not weaken authentication, membership checks, approval gates, or model safety checks.
- Do not claim a successful response until the frontend receives and renders the assistant reply.

## Proposed behavior

### Request and provider path

- Normal text chat continues to prefer the authenticated Fast-to-ZARRY private `/v1/chat` route using Qwen3 1.7B.
- Apply a configurable, bounded timeout to the Qwen request. The timeout must cover the actual upstream response wait and be coordinated with the frontend request lifecycle.
- On a timeout or retryable upstream failure, use only a fallback provider that is already configured and explicitly supported by the existing backend provider registry. If no healthy fallback is available, return a structured, user-safe error promptly.
- Do not automatically retry a request after partial streamed content has already been delivered unless the stream protocol can safely mark/reconcile the partial response; avoid duplicate or concatenated answers.
- Keep provider errors and diagnostics in server logs without exposing secrets or internal URLs to the browser.

### Frontend chat lifecycle

- Preserve the assistant message placeholder on stream failure and replace it with a clear error state rather than silently deleting it.
- Distinguish an intentional user cancellation from timeout, network failure, authentication failure, and upstream provider failure.
- Ensure the sending state is always reset and the user can retry.
- Do not launch a second full chat request as an invisible fallback if the first request may still be running; use the backend's bounded fallback behavior or a clearly surfaced retry state.
- A successful response must replace transient status text with the actual reply.

## Interfaces and responsibilities

- `frontend/hooks/useChat.ts`: owns the visible client-side message lifecycle, cancellation, timeout/error presentation, and retry affordance.
- `frontend/lib/api.ts`: owns the browser request and stream parsing contract; preserve existing authentication and event semantics while surfacing non-2xx, malformed, empty, and prematurely-closed stream failures.
- Existing ZARRY backend chat/provider modules (exact module paths to be confirmed during implementation): own Qwen timeout, provider selection, configured fallback, and structured error mapping.
- Existing tests for chat API/provider routing: extend them to prove timeout/fallback and no-fallback behavior without network calls.

## Acceptance criteria

1. A normal message such as `how` yields a visible assistant reply in the signed-in website, or a visible actionable error within the configured request budget.
2. Qwen remains the first-choice provider and is called through the private authenticated Railway connection.
3. A simulated Qwen timeout selects a configured fallback once; if none is configured, the API returns a structured failure within budget.
4. A stream that fails before its first token leaves a visible failed assistant message; it is not silently removed.
5. A stream that fails after partial output does not trigger an automatic duplicate answer.
6. User cancellation does not show as a provider failure and always clears the sending state.
7. Authentication failures remain authentication failures and do not fall through to an unauthenticated provider.
8. Kitty decision authority and live-trading-disabled protections remain unchanged.
9. Focused tests, affected integration tests, and the production signed-in chat smoke test pass before merge/deploy.

## Verification plan

- Add focused failing tests before implementation for: stream failure visibility, cancellation cleanup, upstream timeout, configured fallback, missing fallback, and no retry after partial output.
- Run the exact focused frontend and backend test commands identified from repository scripts and existing test conventions.
- Run relevant lint/type checks and the repository's CI-equivalent checks for changed packages.
- Deploy only the approved branch/PR through the existing Railway workflow after tests pass; do not touch Vercel.
- Perform an authenticated end-to-end browser test by sending `how`, verify the assistant reply appears, and correlate the request with Fast and ZARRY logs. Health checks alone are insufficient.

## Operational decisions to confirm during implementation

- Select timeout values from measured Qwen latency and Railway request limits; expose them as configuration rather than hard-coding a guess.
- Select the fallback from the provider registry and currently configured production secrets. Do not add a new provider or spend quota without confirming it is already enabled.
- If no verified fallback is configured, prefer a prompt, explicit error over a long wait or an unverified provider.
