# JARVIS V2 Core Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make King Zarry AI's existing workflow coordinator report honest states, preserve approval boundaries, and verify outcomes before declaring consequential work complete.

**Architecture:** Extend the current workflow engine and store rather than adding a parallel orchestrator. The authenticated API remains the entry point; the Action Gateway and provider connectors remain the execution authority. Specialist routing is additive, with explicit unavailable results when required tools or verified account access are missing.

**Tech Stack:** Python 3.12, FastAPI, PostgreSQL/Neon workflow store, existing SQLite Action Gateway, unittest/coverage, GitHub Actions.

## Global Constraints

- Preserve the current chat path for ordinary requests.
- All workflows and approvals remain user-scoped.
- Planning or previewing must never execute an external action.
- Consequential actions continue to require explicit approval through the existing gateway.
- Never claim delivery/completion without provider-backed evidence; report submitted/unverified where evidence is unavailable.
- Never auto-retry consequential external actions after ambiguous outcomes.
- Never invent connected-account state, market data, or confirmed revenue.
- Keep Cloudflare as frontend target and Railway as backend; do not treat a code merge as proof of live deployment.

---

### Task 1: Add workflow contract tests before changing execution semantics

**Files:**
- Modify: `test_workflow_engine.py`
- Test: existing workflow CI command in `.github/workflows/kz-workflow-check.yml`

**Interfaces:**
- Consumes: `workflow_engine.plan_goal`, `workflow_engine.run_workflow`, `workflow_engine.approve_workflow`, `workflow_store` functions.
- Produces: regression coverage for truthful completion, approval state, user scoping and retry safety.

- [ ] **Step 1: Add focused tests**
  - Verify ordinary planning retains existing classification and approval requirements.
  - Verify an external action cannot execute before approval.
  - Verify an approval for one user cannot read or mutate another user's workflow.
  - Verify failed or missing evidence does not yield a verified success result.
  - Verify an interrupted external action is surfaced for manual reconciliation rather than replayed.
- [ ] **Step 2: Run focused tests and record expected failures**
  Run: `python -m unittest test_workflow_engine.py`
  Expected: new assertions expose any current gap without changing unrelated routing behavior.
- [ ] **Step 3: Implement only the contract corrections needed**
  Preserve public function names and existing workflow JSON fields; add explicit verification/state fields only where needed.
- [ ] **Step 4: Re-run focused tests**
  Run: `python -m unittest test_workflow_engine.py`
  Expected: all workflow contract tests pass.
- [ ] **Step 5: Run affected integration checks**
  Run: `python -m py_compile workflow_models.py workflow_store.py workflow_engine.py workflow_api.py kz_agent.py test_workflow_engine.py`
  Expected: all listed modules compile.
- [ ] **Step 6: Commit the passing deliverable**
  Commit message: `fix: enforce workflow approval and evidence contracts`

### Task 2: Make approval state exact, user-scoped, and replay-safe

**Files:**
- Modify: `workflow_api.py`
- Modify: `workflow_engine.py`
- Modify: `workflow_store.py` only if existing approval helpers cannot enforce the current contract
- Test: `test_workflow_engine.py`

**Interfaces:**
- Consumes: `create_approval(workflow_id, step_id, user_id, action_preview)`, `decide_approval(approval_id, user_id, approved)`, `approve_workflow(workflow_id, user_id, approved)`, `agent_action_gateway.approve_action(action_id, user_id)`.
- Produces: an approval transition tied to the currently waiting step and its exact preview; repeated, rejected, mismatched, or stale approvals do not execute.

- [ ] **Step 1: Add failing approval tests**
  Cover approval of a different user's workflow, repeated decisions, rejected approval, missing gateway action ID, and an approval preview that no longer matches the pending action.
- [ ] **Step 2: Verify the failure**
  Run: `python -m unittest test_workflow_engine.py`
  Expected: the new tests fail against the unsafe or ambiguous transitions they target.
- [ ] **Step 3: Implement the narrow enforcement**
  Only decide the approval record associated with the exact waiting step; stop before execution if the approval record is absent, already decided, belongs to another user, or does not correspond to the pending action. Do not call the gateway when the action preview has no valid action ID.
- [ ] **Step 4: Verify**
  Run: `python -m unittest test_workflow_engine.py`
  Expected: rejected/stale/replayed approvals leave external execution untouched.
- [ ] **Step 5: Integration check**
  Run: `python -m py_compile workflow_api.py workflow_engine.py workflow_store.py agent_action_gateway.py`
  Expected: no syntax errors and no changes to the Action Gateway's existing provider risk policy.
- [ ] **Step 6: Commit**
  Commit message: `fix: bind workflow approvals to exact pending actions`

### Task 3: Add explicit execution evidence and honest persistence status

**Files:**
- Modify: `workflow_engine.py`
- Modify: `workflow_store.py` if required to expose persistence health without changing existing return contracts
- Modify: `learning_loop.py`
- Test: `test_workflow_engine.py` and existing learning-loop tests

**Interfaces:**
- Consumes: step executor output, browser/provider verification payloads, `learning_loop.learn_from_workflow`, existing store save/get APIs.
- Produces: workflow results that distinguish completed analysis, action submitted, verified external outcome, execution failure, and ambiguous outcome.

- [ ] **Step 1: Add failing tests**
  Check that ordinary research may complete without external-action evidence, but any consequential step requires an explicit verification result before the workflow can report verified completion; check that an ambiguous timeout does not auto-replay the external step; check that learning does not label unverified external work as success.
- [ ] **Step 2: Verify failures**
  Run: `python -m unittest test_workflow_engine.py test_learning_loop.py`
  Expected: new evidence assertions fail until the completion boundary is explicit.
- [ ] **Step 3: Implement explicit result semantics**
  Keep existing status values compatible; add a clear verification object/status to result data. Missing evidence becomes `unverified` or `verification_required`, not a fabricated success. Keep provider error logs sanitized and bounded.
- [ ] **Step 4: Verify focused tests**
  Run: `python -m unittest test_workflow_engine.py test_learning_loop.py`
  Expected: no unverified external workflow is learned as a verified success.
- [ ] **Step 5: Integration check**
  Run: `python -m py_compile workflow_engine.py workflow_store.py learning_loop.py reliability_guardian.py`
  Expected: all modules compile.
- [ ] **Step 6: Commit**
  Commit message: `fix: require evidence for consequential workflow outcomes`

### Task 4: Integrate coordinator behavior, run full regression checks, and prepare review

**Files:**
- Modify: `agent_router.py` only for missing specialist routing cases proven by tests
- Modify: `api.py` only if workflow-oriented requests are not routed through existing authenticated workflow entry points
- Modify: `test_agent_router.py` and `test_workflow_engine.py`
- Modify: `.github/workflows/kz-workflow-check.yml` only if new test files need explicit inclusion

**Interfaces:**
- Consumes: existing agent router, authenticated API, workflow API, specialist tool modules.
- Produces: deterministic routing for explicit specialist intents while normal conversation remains on the generic chat path.

- [ ] **Step 1: Add routing tests**
  Cover generic chat passthrough, known specialist intents, missing tool/provider, and explicit unavailable outcomes.
- [ ] **Step 2: Verify the focused failure**
  Run: `python -m unittest test_agent_router.py`
  Expected: any unsupported or falsely successful route is identified.
- [ ] **Step 3: Implement only test-backed routing gaps**
  Avoid duplicate workflow stores, alternate identity maps, or parallel execution APIs.
- [ ] **Step 4: Run focused checks**
  Run: `python -m unittest test_agent_router.py test_workflow_engine.py test_learning_loop.py test_reliability_guardian.py`
  Expected: all focused tests pass.
- [ ] **Step 5: Run the repository's workflow CI command set**
  Run:
  ```bash
  python -m py_compile workflow_models.py workflow_store.py workflow_engine.py workflow_api.py workflow_scheduler.py reliability_guardian.py learning_loop.py revenue_engine.py channel_work.py work_intent.py api.py agent_router.py test_agent_router.py browser_operator.py browser_api.py connector_api.py job_outreach_agent.py test_browser_operator.py test_job_outreach_agent.py test_workflow_engine.py bot.py discord_bot.py web_research_engine.py test_web_research_engine.py
  python -m pip install --disable-pip-version-check coverage requests
  coverage run -m unittest test_workflow_engine.py test_agent_router.py test_work_intent.py test_delivery_agent.py test_business_dashboard.py test_workflow_scheduler.py test_learning_loop.py test_reliability_guardian.py test_browser_operator.py test_job_outreach_agent.py test_web_research_engine.py
  coverage report -m
  ```
  Expected: compilation succeeds and the configured unittest suite passes.
- [ ] **Step 6: Open a reviewable pull request**
  Use a draft PR until all relevant checks pass; document any external provider/deployment check that cannot be exercised from CI. Do not merge if a required check fails.
  Commit message: `feat: strengthen JARVIS V2 workflow coordination`

## Unresolved external verification

- Provider credentials and live Gmail/Shopify/GitHub authorizations cannot be verified from unit tests; perform non-destructive provider checks only where credentials are actually available.
- Cloudflare production rollout and Railway runtime health must be checked separately after merge/deployment. No production-success claim should be made from a green CI run alone.
