# King Zarry AI — JARVIS V2 Core Design

**Status:** Proposed for review  
**Date:** 2026-10-11

## Goal

Turn the existing King Zarry AI modules into a dependable coordinator for user requests, workflows, approvals, execution evidence, and learning, without replacing the current web chat or bypassing connector-specific permission checks.

## Current repository foundation

The current `main` branch already includes `agent_router.py`, `workflow_engine.py`, `workflow_api.py`, `workflow_store.py`, `agent_action_gateway.py`, `account_agent.py`, `learning_loop.py`, `reliability_guardian.py`, and `revenue_engine.py`. The implementation should extend these boundaries rather than create a second parallel workflow system. PR #75, “Add Gmail intelligence and five-minute monitoring,” remains a draft and must be reviewed against current `main` before any changes are adopted.

## Design

### 1. Coordinator and intent routing

Keep the existing API as the entry point. Route only clearly recognized specialist requests to a specialist; ordinary chat stays on the current AI path. Workflow-oriented requests should use the existing workflow engine and return a durable workflow identifier and current status. A specialist must return an explicit unavailable/blocked result when its tool, data source, identity, or authorization is missing; it must not fabricate results.

### 2. Approval and execution boundary

The existing Action Gateway and connector-specific approval rules remain authoritative for consequential actions. Planning and previewing an action must not execute it. Approval must be scoped to the authenticated user and exact pending action; rejected, expired, mismatched, or already-consumed approvals must not execute. A completed status is only allowed when the executor returns success and the supported verification step records evidence. Where a provider cannot prove delivery or completion, report “submitted/unverified” rather than “sent/verified.”

### 3. Persistence and cross-channel identity

Use the existing workflow store and shared identity bridge. Keep workflow, event, approval, and learning records scoped to a stable user identity. Never select a customer identity by guesswork when more than one candidate exists. Database unavailability must be surfaced in status when durable persistence is required; in-memory fallback must not be described as durable.

### 4. Recovery, monitoring, and learning

Retry only safe, idempotent work, with bounded attempts. Do not automatically retry trades, outbound messages, publishing, or other consequential external actions. Monitoring should distinguish healthy, temporarily failing, and revoked-authorization states. Learn only from bounded, sanitized metadata and verified outcomes; do not store secrets or raw private messages in lessons. Opportunity values are forecasts, not confirmed revenue.

### 5. Delivery sequence

- First: coordinator/workflow integration, exact approval binding, honest execution states, and regression tests.
- Second: review and integrate suitable Gmail monitoring work from PR #75, then verify real account authorization and alert delivery.
- Third: unify web, Telegram, and Discord access to workflow status and approval queues.
- Fourth: scheduled opportunity reports and morning briefing, then revenue pipeline presentation.

## Failure behavior

- Unknown intent: leave the request on the normal chat path.
- Missing tool/data/provider: report unavailable and identify the missing prerequisite.
- Missing or ambiguous identity: stop and request account linking; do not guess.
- Approval denied or mismatched: do not execute.
- Executor timeout or missing evidence: report failure or unverified status; do not claim completion.
- Database outage: surface that persistent workflows may not be available and avoid claiming cross-channel durability.
- Repeated safe-work failure: stop after bounded retries and surface the failure.
- Production deployment not observed: do not claim the live frontend/backend has been updated.

## Verification

Focused Python tests should cover routing, workflow status transitions, approval identity/action binding, repeated approval attempts, missing executor results, evidence-required completion, persistence failure signaling, and safe retry boundaries. Run the repository's relevant Python test and compile checks, plus the existing frontend typecheck/build and workflow CI checks when changed files require them. Production behavior is considered verified only after a live health check and a real, non-destructive end-to-end test with explicit evidence.

## Scope exclusions

This phase does not introduce unrestricted autonomous browsing, automatic live trading, unapproved outbound communication, payment movement, or a new parallel memory/database system. It does not mark Shopify, Gmail, GitHub, or browser access connected without provider-backed authorization evidence.

## Review question

Please review this design before implementation proceeds. The primary choice is whether the first phase should prioritize core workflow correctness and approval/evidence safety (recommended), or cross-channel UI/command parity first.
