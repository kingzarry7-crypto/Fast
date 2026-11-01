# ZARRY Chat Response Reliability Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a normal signed-in ZARRY web-chat message produce a visible answer or a clear failure within a bounded time, with Qwen3 1.7B remaining the preferred private Railway model.

**Architecture:** Keep the existing FastAPI SSE route and private `SelfHostedZarryProvider` contract. Bound the private Qwen request at the provider boundary, allow only already-configured streaming providers to be tried after a Qwen failure, and make the browser retain a visible assistant message for stream failures instead of silently deleting it and issuing an invisible duplicate request.

**Tech Stack:** Python 3.12, FastAPI, requests, unittest, Next.js 15.5, React 19, TypeScript, npm, GitHub Actions, Railway, Cloudflare Workers.

## Global Constraints

- Do not change or deploy anything on Vercel.
- Keep Qwen3 1.7B on the private Railway ZARRY service as the preferred model.
- Do not reintroduce SmolLM3 routing.
- Do not change Kitty's exclusive trading decision authority or enable live trading.
- Do not weaken authentication, membership checks, approval gates, or model safety checks.
- Do not claim a successful response until the frontend receives and renders the assistant reply.
- Use only fallback providers already configured and supported by the existing provider registry; do not add a provider, create new credentials, or spend new provider quota.
- Never expose secrets, internal Railway URLs, or raw upstream diagnostics to the browser.
- Do not automatically retry a request after partial streamed output has been delivered.

---

### Task 1: Bound the private Qwen request and prove safe fallback selection

**Files:**
- Modify: `zarry_gateway/providers.py`
- Modify: `streaming_chat.py`
- Test: `tests/test_zarry_gateway_text.py`
- Test: `test_streaming_chat_routing.py`

**Interfaces:**
- Consumes: `SelfHostedZarryProvider.generate(*, message: str, request_id: UUID, messages=None, timeout=None) -> str`.
- Consumes: `_provider_streams(messages: list)` and `_stream_zarry(messages: list)`.
- Produces: provider-level configurable connect/read timeout, retaining the existing `timeout` override for callers; Qwen remains first in AUTO mode, followed only by configured existing streaming providers.

- [ ] **Step 1: Add focused failing tests**

Add provider tests asserting:
1. The default private Qwen request uses a bounded connect/read timeout.
2. Explicit timeout arguments still override the configured defaults.
3. Invalid, non-numeric, zero, and excessively large timeout environment values resolve to safe documented bounds rather than creating an unbounded request.
4. A Qwen timeout is visible to the streaming provider loop as a provider failure.
5. In AUTO mode, Qwen is attempted first and an already-configured next provider is attempted once after Qwen fails.
6. When no other provider is configured, no unconfigured provider is attempted and the failure remains explicit.
7. An explicit `AI_PROVIDER` selection continues to be honored and is not silently replaced by an unrelated provider.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest tests.test_zarry_gateway_text test_streaming_chat_routing -v`

Expected: the new timeout-boundary tests fail against the current fixed `(5.0, 180.0)` default and any unimplemented fallback assertions fail before implementation.

- [ ] **Step 3: Implement the minimum behavior**

Add documented environment-backed connect/read timeout settings in `SelfHostedZarryProvider`. Parse defensively, clamp to finite safe bounds, and keep the existing constructor timeout tuple and per-call override compatible. Pass the bounded tuple to `requests.post`. Keep the private `/v1/chat` endpoint, bearer authentication, request-ID verification, and non-empty-response check unchanged.

Inspect and adjust `_provider_streams` only as needed so AUTO mode attempts the private Qwen service first, then the existing configured streaming providers in the established order. A failed Qwen stream must not suppress later configured providers; an absent credential must never create a provider attempt. Preserve explicit provider preference behavior and never add SmolLM3.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest tests.test_zarry_gateway_text test_streaming_chat_routing -v`

Expected: all provider timeout, Qwen-first, configured-fallback, and no-fallback tests pass without network access.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m py_compile zarry_gateway/providers.py streaming_chat.py && python -m unittest test_streaming_chat_context -v`

Expected: both modules compile and existing project-context streaming tests pass.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add zarry_gateway/providers.py streaming_chat.py tests/test_zarry_gateway_text.py test_streaming_chat_routing.py
git commit -m "fix: bound private ZARRY chat latency"
```

### Task 2: Make streaming completion and failure events deterministic

**Files:**
- Modify: `streaming_chat.py`
- Test: `test_streaming_chat_routing.py`
- Test: `test_streaming_chat_context.py`

**Interfaces:**
- Consumes: `_build_stream_generator(*, user_id, message, conversation_id, memory_factory)`.
- Produces: the existing SSE event contract: `activity`, `start`, `delta`, `done`, and `error`.

- [ ] **Step 1: Add focused failing tests**

Add tests for an ordinary message that assert:
1. A configured Qwen response emits a start event, a non-empty delta, and exactly one done event.
2. A Qwen timeout followed by a configured fallback emits only the fallback answer and one done event.
3. If every configured provider fails before the first token, the stream emits one safe error event and no done event claiming success.
4. If a provider fails after emitting a partial delta, the stream emits a safe terminal error and does not restart another provider or append a second answer.
5. Internal provider URLs, bearer tokens, and raw exception bodies are absent from browser-visible error events.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest test_streaming_chat_routing test_streaming_chat_context -v`

Expected: new terminal-event and no-retry-after-partial-output assertions fail before implementation.

- [ ] **Step 3: Implement the minimum behavior**

Review the current provider iteration and SSE generator. Track whether any delta has been yielded. Permit the existing configured-provider fallback only before the first delta. Once output begins, terminate that attempt on failure with a sanitized error event; never switch providers and concatenate a second response. Ensure exactly one terminal event is emitted and only a non-empty completed response emits `done`. Log provider identity and exception class/status server-side without logging credentials or returning raw upstream bodies.

Do not route specialist, market, coding, media, or account/approval requests around their existing handlers. The change applies only to the ordinary text-generation path after those handlers decline the request.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest test_streaming_chat_routing test_streaming_chat_context -v`

Expected: success, fallback-before-first-token, sanitized terminal error, and no-fallback-after-partial-output tests all pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m py_compile streaming_chat.py && python -m unittest test_streaming_chat_routing test_streaming_chat_context -v`

Expected: clean compile and passing streaming regression suite.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add streaming_chat.py test_streaming_chat_routing.py test_streaming_chat_context.py
git commit -m "fix: make ZARRY stream failures explicit"
```

### Task 3: Keep failed assistant messages visible and prevent silent duplicate requests

**Files:**
- Modify: `frontend/hooks/useChat.ts`
- Modify: `frontend/lib/api.ts`
- Test: authenticated browser smoke test using the existing deployed sign-in flow; no new browser test framework is assumed.

**Interfaces:**
- Consumes: `api.streamChatMessage(message, { conversationId, signal, onDelta, onStart, onActivity, onAgent })`.
- Produces: stable assistant message lifecycle in `useChat`: pending → completed, failed, or stopped; `sending` is reset for every terminal path.

- [ ] **Step 1: Define the focused failure cases**

Use the existing test/browser tooling if present; otherwise add no new dependency solely for a one-off test. Exercise the following cases in the smallest available harness:
1. Stream fails before the first token: the existing assistant placeholder remains and shows a safe failure message/status.
2. Stream fails after partial output: the partial text remains visible with a failed status; no non-streaming duplicate request is sent.
3. User cancellation: no provider-failure message appears, the pending item is marked stopped, and sending resets.
4. HTTP 401: the user sees the sign-in-again message; there is no fallback to an unauthenticated endpoint.
5. HTTP 403, timeout, network failure, malformed stream, empty stream, and premature close: a visible actionable failure remains.
6. Successful stream: the placeholder is replaced with the final reply and transient status text is cleared.

- [ ] **Step 2: Verify the relevant failure**

Run: `cd frontend && npm run typecheck`

Expected: baseline typecheck passes; then reproduce the current silent-removal behavior with the authenticated browser and record the failed assistant placeholder disappearing when the stream rejects. If the repository has an existing browser harness, run its focused test and record the expected failure before changing the hook.

- [ ] **Step 3: Implement the minimum behavior**

In `useChat.ts`, replace the stream catch path that filters out `aiId`. Preserve the placeholder and set its text/status to a user-safe error, distinguishing intentional abort from timeout/network/auth/upstream errors. Do not fall through to `sendChatMessage` after a stream error; the current catch block's silent removal followed by the non-streaming request is the duplicate/long-wait path. Keep the existing `/api/chat` fallback inside `streamChatMessage` only for explicit route-not-found/method-not-allowed responses (404/405), where the stream route is not deployed; do not broaden that fallback to provider timeouts or stream failures.

In `api.ts`, preserve the current same-origin credentials and SSE event contract. Ensure non-2xx, absent body, empty response, explicit error frame, and premature stream close reject with typed safe errors; always release the reader lock. Do not retry after partial content. In the hook's outer catch/finally, retain existing 401/403 handling and always clear `sending`; make retry possible without resubmitting the original message automatically.

- [ ] **Step 4: Verify the focused pass**

Run: `cd frontend && npm run typecheck`

Expected: no TypeScript errors. Repeat the focused browser cases and verify the failed assistant item remains visible, cancellation clears the pending state, and no second POST is sent after a stream failure.

- [ ] **Step 5: Run the affected integration check**

Run: `cd frontend && npm run lint && npm run build`

Expected: ESLint and Next.js production build pass. Run `npm run cf:build` only as a build verification if the environment has the existing Cloudflare credentials/config; do not deploy to Vercel.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add frontend/hooks/useChat.ts frontend/lib/api.ts
git commit -m "fix: show ZARRY chat stream failures"
```

### Task 4: Verify production signed-in chat before merge or deployment

**Files:**
- No production source changes unless a failing verification identifies a specific defect.
- Evidence: GitHub Actions checks, Railway deployment logs, and the authenticated browser result.

**Interfaces:**
- Consumes: deployed Fast web chat, private Railway Fast-to-ZARRY service connection, and the authenticated session.
- Produces: verified visible response or a captured actionable failure for the exact message `how`.

- [ ] **Step 1: Run repository regression checks**

Run: `python -m unittest tests.test_zarry_gateway_text test_streaming_chat_routing test_streaming_chat_context -v`

Expected: all focused backend tests pass. Run the frontend commands from Task 3 and the existing CI-equivalent checks for changed files.

- [ ] **Step 2: Verify the production branch and environment**

Confirm the branch is based on the latest `main`, review the complete diff, and confirm the changed deployment target is the existing Railway Fast service only. Confirm no Vercel project, token, deployment, or configuration is touched. Confirm the production environment still has Qwen private-service configuration and only already-enabled fallback credentials.

- [ ] **Step 3: Run the signed-in browser smoke test**

Using the existing authenticated web session, send exactly `how`. Verify the user message appears once, the assistant shows a pending state, then either a non-empty final assistant reply or a clear actionable error appears within the configured request budget. Verify no duplicate POST occurs. Correlate the request with Fast and ZARRY logs and confirm the selected provider and elapsed time without exposing secrets.

- [ ] **Step 4: Verify safety invariants**

Confirm no changes to Kitty's decision-authority code, no live-trading enablement, no weakened authentication or membership checks, and no unapproved external action. If any invariant or browser test fails, do not merge or deploy; fix the specific failure and repeat the relevant tests.

- [ ] **Step 5: Prepare the reviewable PR**

Open a PR from `fix/zarry-chat-response-latency` to `main` with the test results, browser evidence, provider timing, and explicit statement that Vercel was untouched. Keep it unmerged until required checks pass and the user explicitly approves the merge/deployment.

## Unresolved operational decisions

- The exact Qwen connect/read timeout values must be chosen from the Railway service's measured latency and request limits; the values must be finite, configurable, and tested at their boundaries.
- Fallback order is limited to the existing configured provider registry and current production credentials. If no fallback is both configured and supported, the correct outcome is a prompt visible error rather than adding a provider or silently using an unverified service.
- A signed-in production browser session is required for the final end-to-end proof. Connector-level health checks and direct service smoke tests are not substitutes.
