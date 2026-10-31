# ZARRY General Assistant Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend ZARRY into the shared general-purpose assistant for the web app, Telegram, and Discord while preserving Kitty's trading authority and existing provider fallbacks.

**Architecture:** Add a shared authenticated gateway to the existing Fast API and route all three clients through it. The gateway owns identity resolution, opt-in shared memory, text-provider routing, Hugging Face image inference, request limits, audit metadata, and a fail-closed paid-inference ledger. The separately hosted ZARRY model remains isolated from Kitty and is the preferred text provider only after its general-chat contract and capacity are verified.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, requests, existing Neon PostgreSQL and SQLite memory adapters, Telegram bot framework, discord.py, Hugging Face Inference APIs, Railway, unittest/pytest as already used by the repository.

## Global Constraints

- Web app, Telegram, and Discord must use one shared gateway for new ZARRY general-assistant requests.
- The gateway owns authentication, shared memory, routing, rate limits, budget enforcement, and provider health.
- Text routes to the self-hosted ZARRY model first when enabled and healthy. Existing approved text providers remain controlled fallback until acceptance and separate migration approval.
- Images route to a separately qualified Hugging Face image model through the gateway. Initial scope is text-to-image only.
- Kitty remains the authoritative source for market facts, deterministic trading decisions, risk checks, account state, and order state. ZARRY may explain only verified Kitty output and must not create/alter decisions, call broker APIs, submit orders, or change risk settings.
- Web requests use existing authenticated King Zarry web sessions. Telegram and Discord use their existing platform identities and authorization rules. Cross-platform account linking requires an authenticated linking flow; matching display names are never sufficient.
- Shared cross-client memory is opt-in and scoped to one stable internal user identity. Users who do not opt in retain isolated existing client context. Memory failures must never substitute another user's data.
- Provider credentials remain server-side. Never commit or return provider secrets.
- Enforce per-user/platform rate limits, bounded request sizes, timeouts, concurrency, and safe/idempotent retries.
- Paid Hugging Face inference routed through this gateway has a shared USD $2 cap per calendar month across covered paid text/image requests. Consume free credits first only if Hugging Face's automatic credit behavior is verified. The gateway cap does not cap unrelated Hugging Face account spend and must never be described as an account billing cap.
- Reserve maximum known cost atomically before dispatch; use idempotent request IDs; reconcile actual provider cost when available; fail closed when price, ledger, or reconciliation state is unknown or unsafe. No paid image fallback.
- Keep ZARRY feature flags off by default until acceptance. No production activation, default-provider migration, provider removal, merge-to-main, or live-trading change is included in this plan.
- Do not change Vercel configuration. Keep Kitty's deterministic code, broker integrations, risk controls, and trading kill switches unchanged.

---

### Task 1: Repository audit and shared gateway contracts

**Files:**
- Modify: `api.py` — register the new general-assistant router using the existing web-session authentication and application lifecycle.
- Create: `zarry_gateway/__init__.py` — package boundary.
- Create: `zarry_gateway/schemas.py` — versioned request/response contracts for text, image, capability status, and errors.
- Create: `zarry_gateway/identity.py` — authenticated principal and canonical identity resolution interfaces.
- Create: `zarry_gateway/policy.py` — feature flags, request bounds, per-user/platform rate limits, and provider eligibility.
- Test: `tests/test_zarry_gateway_contracts.py`
- Test: `tests/test_zarry_gateway_identity.py`

**Interfaces:**
- Consumes: existing web authentication dependency used by `zarry_api.create_router`; existing Telegram/Discord platform identity and authorization helpers; existing `SharedMemory` and Neon identity-linking behavior.
- Produces: `create_general_router(require_web_user, gateway)`; `AssistantRequest`; `AssistantResponse`; `ImageRequest`; `ImageResponse`; `AuthenticatedPrincipal`; `IdentityResolver.resolve(platform, platform_user_id)`.
- Proposed path note: package paths under `zarry_gateway/` are new; existing entry points above were observed on the integration branch.

- [ ] **Step 1: Add failing contract and identity tests**

Test valid text request and response serialization; reject unknown request fields and oversized message payloads according to explicitly configured limits; preserve request/conversation IDs; require authenticated web principal; map a platform identity only through an existing verified link; prove same display name does not link identities; prove user A cannot resolve user B's conversation or budget namespace.

- [ ] **Step 2: Verify the relevant failures**

Run: `python -m unittest tests.test_zarry_gateway_contracts tests.test_zarry_gateway_identity -v`

Expected: tests fail because the gateway package, contracts, and identity resolver do not yet exist.

- [ ] **Step 3: Implement minimum contracts and identity boundary**

Define versioned Pydantic models and typed principal fields. Implement resolver against the existing Neon identity-link records only after confirming their exact schema; retain platform-scoped identity when no verified link exists. Do not create automatic links from names, usernames, email guesses, or matching IDs across platforms. Keep web-session authentication injected rather than duplicating cookie/session logic. Define explicit errors for unauthenticated, forbidden, disabled, rate-limited, invalid, and unavailable requests.

- [ ] **Step 4: Verify focused pass**

Run: `python -m unittest tests.test_zarry_gateway_contracts tests.test_zarry_gateway_identity -v`

Expected: all contract and isolation tests pass; unauthenticated and unlinked identities cannot access another identity's records.

- [ ] **Step 5: Run affected integration check**

Run: `python -m unittest discover -s tests -p "test_zarry_api.py" -v`

Expected: the existing trading explanation proxy tests remain green and its `ZARRY_ENABLED` default-off behavior is unchanged.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add api.py zarry_gateway tests/test_zarry_gateway_contracts.py tests/test_zarry_gateway_identity.py
git commit -m "feat: define shared ZARRY gateway contracts"
```

### Task 2: Text routing, conversation memory, and Hugging Face spend ledger

**Files:**
- Create: `zarry_gateway/service.py` — orchestrate authenticated text request lifecycle.
- Create: `zarry_gateway/providers.py` — self-hosted ZARRY text adapter and approved existing-provider fallback adapter.
- Create: `zarry_gateway/memory.py` — user/conversation-scoped memory facade with explicit opt-in.
- Create: `zarry_gateway/budget.py` — atomic monthly reservation, idempotency, reconciliation, and fail-closed accounting.
- Create: `zarry_gateway/repository.py` — persistence interfaces and Neon implementation for gateway conversations, memory preference, and inference ledger.
- Test: `tests/test_zarry_gateway_text.py`
- Test: `tests/test_zarry_gateway_memory.py`
- Test: `tests/test_zarry_gateway_budget.py`

**Interfaces:**
- Consumes: Task 1 `AuthenticatedPrincipal`, `AssistantRequest`, `AssistantResponse`, `IdentityResolver`; current ZARRY service endpoint and key contract; existing AI provider registry/failover interfaces in `ai_engine.py`; existing Neon database connection conventions.
- Produces: `AssistantService.respond(principal, request)`; `TextProvider.generate(messages, request_id, timeout)`; `MemoryStore.load/save(principal, conversation_id)`; `BudgetLedger.reserve/reconcile/release(request_id, month, maximum_cost, actual_cost)`.
- Database table names and exact SQL migration location must follow the repository's current Neon migration convention after audit; do not introduce a second database or assume a schema not present.

- [ ] **Step 1: Add failing text, memory, and ledger tests**

Cover ZARRY-first selection when healthy; controlled existing-provider fallback after ZARRY connection failure; no fallback when disabled or cost is unknown; explicit provider attribution in response metadata; shared memory available only when the user's opt-in is true; no cross-user or cross-conversation reads; memory-store outage continues without memory only when no data can leak and the response clearly indicates memory unavailable; repeated request ID reserves only once; concurrent reservations cannot exceed the USD $2 monthly cap; unknown pricing, ledger outage, reconciliation failure, and exhausted budget reject paid inference; actual cost above reserved maximum fails closed and records an accounting incident.

- [ ] **Step 2: Verify the relevant failures**

Run: `python -m unittest tests.test_zarry_gateway_text tests.test_zarry_gateway_memory tests.test_zarry_gateway_budget -v`

Expected: tests fail because provider orchestration, opt-in memory facade, and atomic ledger do not yet exist.

- [ ] **Step 3: Implement routing and accounting**

Implement a server-side adapter to the existing ZARRY service with bounded timeouts and request IDs. Confirm whether its current `/v1/explain` contract can be extended safely or whether a separate `/v1/chat` contract is required; do not send general prompts to the trading-only explanation endpoint. Implement fallback through existing provider abstractions without duplicating provider credentials or bypassing existing cost controls. Implement one monthly ledger shared across all gateway-routed Hugging Face paid inference. Use database transactions/unique idempotency keys and an atomic conditional update so concurrent reservations cannot exceed the cap. Persist estimated/actual cost, provider/model, request ID, reservation state, and safe failure metadata. Never store API keys or unnecessary raw prompts in ledger rows.

- [ ] **Step 4: Verify focused pass**

Run: `python -m unittest tests.test_zarry_gateway_text tests.test_zarry_gateway_memory tests.test_zarry_gateway_budget -v`

Expected: all provider selection, memory isolation, opt-in, idempotency, concurrent cap, and fail-closed accounting tests pass.

- [ ] **Step 5: Run affected integration check**

Run: `python -m unittest discover -s tests -p "test_zarry_api.py" -v`

Expected: current explanation endpoint contract and Kitty decision-preservation tests still pass without invoking the new general-chat path.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add zarry_gateway tests/test_zarry_gateway_text.py tests/test_zarry_gateway_memory.py tests/test_zarry_gateway_budget.py
git commit -m "feat: add ZARRY text routing and budget controls"
```

### Task 3: Hugging Face image generation through the shared gateway

**Files:**
- Create: `zarry_gateway/images.py` — Hugging Face image provider adapter and output validation.
- Modify: `zarry_gateway/service.py` — dispatch image requests through shared policy and ledger.
- Modify: `zarry_gateway/schemas.py` — image response metadata if provider response requires it.
- Test: `tests/test_zarry_gateway_images.py`
- Test: `tests/test_zarry_gateway_budget.py`

**Interfaces:**
- Consumes: Task 1 `AuthenticatedPrincipal`, `ImageRequest`, rate-limit/policy interfaces; Task 2 `BudgetLedger`; verified Hugging Face account identity, current inference pricing/credit behavior, and selected model details.
- Produces: `ImageProvider.generate(prompt, model, request_id, timeout)`; `AssistantService.generate_image(principal, request)` returning an image reference or supported image payload plus model/provider/request/cost status.

- [ ] **Step 1: Add failing image route and budget tests**

Test valid text-to-image request; unsupported editing request is rejected as not in initial scope; unauthenticated and over-limit requests are rejected; model is selected only from server configuration; prompt and output are bounded; no provider key is returned; image cost must be known and reserved before dispatch; exhausted budget, missing pricing, provider failure, and ledger failure produce truthful errors; image provider failure never invokes text fallback or another paid provider; repeated request IDs do not double-charge.

- [ ] **Step 2: Verify the relevant failures**

Run: `python -m unittest tests.test_zarry_gateway_images -v`

Expected: tests fail because the Hugging Face image adapter and image route do not exist.

- [ ] **Step 3: Verify Hugging Face model and billing facts before enabling adapter**

Use the connected Hugging Face account identity and official model/provider documentation to verify selected model availability, task support, license, current pricing, reported usage/cost fields, automatic free-credit application, and response format. Record the exact model revision/provider and supported output format in configuration/docs. If actual cost cannot be known or bounded before dispatch, keep paid image inference disabled rather than weakening the $2 guard.

- [ ] **Step 4: Implement image adapter and route**

Call Hugging Face only from the server. Enforce shared user/platform rate limits and the same monthly ledger used by covered paid text requests. Store/return only a verified image reference or response payload supported by the provider. Validate provider response type and size. Reconcile actual cost. Do not add image editing or paid fallback.

- [ ] **Step 5: Verify focused pass**

Run: `python -m unittest tests.test_zarry_gateway_images tests.test_zarry_gateway_budget -v`

Expected: all image success/failure and spend-cap tests pass; no image failure triggers another provider.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add zarry_gateway tests/test_zarry_gateway_images.py tests/test_zarry_gateway_budget.py
git commit -m "feat: add budgeted Hugging Face image generation"
```

### Task 4: Migrate web, Telegram, and Discord; acceptance and guarded rollout

**Files:**
- Modify: `api.py` — mount general gateway routes and expose authenticated capability status.
- Modify: `bot.py` — route eligible general-assistant text/image intents to gateway using Telegram identity; preserve commands and trading handlers.
- Modify: `discord_bot.py` — route eligible general-assistant text/image intents to gateway using Discord identity; preserve slash commands and trading handlers.
- Modify: existing web chat route/client files discovered in repository audit — call gateway and display provider, memory, image, disabled, and unavailable states truthfully.
- Create: `tests/test_zarry_client_routing.py` — client adapter tests using mocked gateway.
- Create: `docs/operations/zarry-general-assistant-rollout.md` — flags, verification, rollback, and operator checklist.

**Interfaces:**
- Consumes: Task 1 `create_general_router`, `AuthenticatedPrincipal`, `IdentityResolver`; Task 2 `AssistantService.respond`, memory opt-in and provider metadata; Task 3 `AssistantService.generate_image`.
- Produces: web/Telegram/Discord adapters that send the same versioned gateway contracts and preserve platform-specific authentication/authorization; capability/status response reporting text, image, and memory flags independently.

- [ ] **Step 1: Add failing client routing tests**

For each client, verify ordinary general text is sent to gateway only when its feature flag is enabled; image intent uses image route; trading commands and Kitty workflows continue through their existing handlers and never become model-authoritative; gateway unavailable produces a truthful unavailable response; user/platform identity is attached server-side and cannot be overridden by message payload; no client contains Hugging Face keys or calls Hugging Face directly.

- [ ] **Step 2: Verify the relevant failures**

Run: `python -m unittest tests.test_zarry_client_routing -v`

Expected: tests fail because all three clients do not yet use the shared general-assistant gateway.

- [ ] **Step 3: Implement client adapters behind independent default-off flags**

Mount gateway on Fast API with existing web-session authentication. Add thin Telegram and Discord adapters that call the same backend service contract using their existing bot authorization. Keep each platform's trading commands, approval gates, and Kitty calls unchanged. Add truthful provider/memory/image capability status. Preserve unsent user drafts where the existing client supports it. Do not silently route failed images to text providers.

- [ ] **Step 4: Verify focused pass**

Run: `python -m unittest tests.test_zarry_client_routing -v`

Expected: web, Telegram, and Discord routing tests pass; disabled flags leave existing client behavior unchanged; trading handlers are unaffected.

- [ ] **Step 5: Run full acceptance checks**

Run:
```bash
python -m unittest discover -s tests -v
python -m unittest discover -s zarry-service/tests -p "test_*.py" -v
python -m unittest discover -s tests -p "test_zarry_api.py" -v
```

Expected: full existing suite and ZARRY contract suites pass. Also run authenticated non-production smoke tests for text, image (only if HF pricing is verified), memory opt-in/isolation, provider fallback, budget exhaustion, and all three clients. Verify Kitty signal/NO TRADE outputs and broker/order paths are byte-for-byte unaffected by gateway enablement tests; no order is submitted.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add api.py bot.py discord_bot.py [verified web client paths] tests/test_zarry_client_routing.py docs/operations/zarry-general-assistant-rollout.md
git commit -m "feat: integrate clients with shared ZARRY assistant"
```

## Unresolved product and operational decisions

1. **Identity linking UX:** choose the authenticated web flow and confirmation steps for linking Telegram and Discord identities to a web account. Until approved and implemented, identities remain separate.
2. **Memory controls:** decide where users enable/disable cross-client memory and how they view, export, clear, and delete shared memory; shared memory remains off until this is implemented.
3. **General-chat model contract:** decide whether to add a separate `/v1/chat` endpoint to the existing ZARRY service or run a separate general-chat model/service. The existing `/v1/explain` endpoint is trading-only and must not be repurposed without a distinct contract.
4. **Model acceptance thresholds:** define minimum quality, latency, concurrency, and resource thresholds for general questions, writing, reasoning, and simple coding before private pilot.
5. **Hugging Face image model/provider:** select exact model revision/provider only after verifying account availability, license, task support, pricing, and cost reporting.
6. **Free-credit treatment:** verify whether Hugging Face automatically consumes credits before paid billing; do not assume credits are applied.
7. **Budget overage semantics:** decide the operator action when provider-reported actual cost exceeds a pre-reserved maximum; until then, block further paid requests and flag reconciliation incident.
8. **Fallback policy:** confirm which existing text providers are approved for fallback and whether they have separate user/account spending limits. Do not route to any fallback whose cost is unknown or not permitted.
9. **Conversation retention:** set retention period and user-facing deletion behavior for general assistant conversations and inference metadata, consistent with existing privacy obligations.
10. **Rollout approval:** private pilot cohort and rollout success thresholds require separate approval. All production feature flags remain off until acceptance and explicit activation approval.
