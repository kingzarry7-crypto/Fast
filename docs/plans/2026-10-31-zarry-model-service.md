# ZARRY Model Service Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently hosted, open-weight ZARRY inference service that provides grounded, non-authoritative explanations of Kitty's BTC and XAUUSD analysis without changing Kitty's deterministic decisions or execution permissions.

**Architecture:** Fast remains the owner of market data, Kitty inference, signal gating, and paper/demo safety. A separate Railway service hosts a small quantized model behind an authenticated private API; Fast sends only bounded structured context and validates the explanation response. Dataset preparation and model benchmarking are reproducible research jobs, separate from production inference.

**Tech Stack:** Existing Python 3.12/FastAPI backend, existing PyTorch/scikit-learn Kitty research stack, Python tests, Docker containers, Railway private networking, and a separately selected open-weight model/runtime after license and hardware benchmarking.

## Global Constraints

- ZARRY is advisory/explanatory only; Kitty remains authoritative for prices, indicators, signals, risk checks, and execution permissions.
- BTC and XAUUSD must be evaluated and reported separately.
- Include wins, losses, and correct WAIT/no-trade cases; no fabricated or unverified outcomes.
- Use chronological train/validation/holdout splits, timestamp-only available features, overlap-aware labels, and duplicate isolation.
- Record data provenance, symbol, timeframe, timestamp, feature version, label definition, cost assumptions, dataset version, and model version.
- Remove credentials, personal data, account identifiers, and unrelated chat content from all model datasets and prompts.
- ZARRY cannot override WAIT/NO TRADE, stale-data rejection, market/news filters, stop-loss requirements, risk limits, duplicate-order prevention, or the live-trading kill switch.
- No ZARRY endpoint or response can call tools, broker APIs, order endpoints, or mutate risk settings.
- Phase one is paper/demo/research only. No live-trading enablement.
- ZARRY failure, timeout, invalid output, or unavailable model must not interrupt Kitty's deterministic path.
- Keep existing AI providers and existing Fast production deployment configuration unchanged until acceptance tests pass and a separate migration decision is approved.
- Do not change Vercel. Do not add model weights or training artifacts to the Fast application image.
- Hosting, storage, networking, and training compute can incur costs; do not describe self-hosting as cost-free.
- Do not claim profitability or guaranteed signal accuracy.

---

### Task 1: Audit Kitty inputs and build a leakage-safe, versioned explanation dataset

**Files:**
- Create: `research/zarry/README.md` (proposed; dataset workflow and provenance contract)
- Create: `research/zarry/prepare_dataset.py` (proposed; deterministic dataset builder)
- Create: `research/zarry/dataset_schema.py` (proposed; typed record/schema definitions)
- Create: `tests/test_zarry_dataset.py` (proposed; dataset integrity tests)
- Inspect without changing initially: `kitty_api.py`, `kitty_v3_retrained.py`, `kitty_gold_model.py`, `kitty_features.py`, `fetch_kitty_5m_market_data.py`, `tests/test_kitty_market_data_provenance.py`, `tests/test_kitty_signal_safety.py`

**Interfaces:**
- Consumes: existing Kitty prediction/status outputs and curated candle/signal/outcome records. Exact source adapters are to be confirmed from the audit; do not assume all existing records are suitable training labels.
- Produces: `build_dataset(input_manifest, output_dir, split_config) -> DatasetManifest`; versioned JSONL examples plus a manifest with source hashes, time boundaries, symbol/timeframe coverage, feature/label versions, and exclusion counts.
- Each example carries symbol, decision timestamp, available-at-that-time structured context, Kitty decision (including WAIT/NO TRADE), outcome/label if verified, provenance, and explicit cost assumptions. The schema does not imply missing values are fabricated or silently filled.

- [ ] **Step 1: Add failing tests for the dataset contract**

Test BTC and XAUUSD separation; inclusion of positive, negative, and WAIT examples; rejection/exclusion of records with missing provenance or unverified outcomes; timestamp-ordered split boundaries; no duplicate example IDs across splits; no future feature timestamp after decision time; and explicit handling of overlapping outcome horizons.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest tests.test_zarry_dataset -v`

Expected: import/test failures for the not-yet-created dataset module and its required contract.

- [ ] **Step 3: Audit and implement the minimum reproducible builder**

Trace existing Kitty source and outcome fields before writing adapters. Build immutable example records and a manifest; split chronologically per symbol with configurable cutoffs; ensure each feature timestamp is at or before decision time; exclude overlapping samples across splits or apply a documented overlap policy; hash inputs and outputs; redact credentials/account identifiers/private data; retain exclusion reasons. Do not merge BTC and XAUUSD into one evaluation cohort. Do not treat a candidate BUY/SELL as a verified outcome.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest tests.test_zarry_dataset -v`

Expected: all dataset integrity tests pass, including deliberate leakage, duplicate, malformed-provenance, and cross-symbol fixtures.

- [ ] **Step 5: Run affected Kitty regression tests**

Run: `python -m unittest tests.test_kitty_market_data_provenance tests.test_kitty_signal_safety -v`

Expected: existing market provenance and NO TRADE safety tests remain green; the dataset builder does not modify Kitty behavior.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add research/zarry/README.md research/zarry/prepare_dataset.py research/zarry/dataset_schema.py tests/test_zarry_dataset.py
git commit -m "feat: add leakage-safe ZARRY dataset builder"
```

### Task 2: Benchmark licensed small open-weight models and select the serving runtime

**Files:**
- Create: `research/zarry/benchmark.py` (proposed; repeatable benchmark runner)
- Create: `research/zarry/model_candidates.json` (proposed; candidate IDs, license evidence, quantization and runtime metadata)
- Create: `research/zarry/evaluation_cases.jsonl` (proposed; frozen BTC/XAUUSD explanation cases)
- Create: `tests/test_zarry_benchmark.py` (proposed; benchmark protocol and report tests)
- Modify only if needed after measurement: `requirements.txt` (do not add large inference dependencies to Fast's runtime requirements)

**Interfaces:**
- Consumes: Task 1 frozen evaluation cases and candidate model/runtime configurations.
- Produces: `run_benchmark(candidate, cases, hardware_profile) -> BenchmarkReport`; report includes model revision/hash, license/source URL, runtime/quantization, output validity, groundedness/abstention scores, BTC and XAUUSD scores separately, latency percentiles, memory/CPU use, and estimated hosting footprint.

- [ ] **Step 1: Add failing tests for benchmark reproducibility and report completeness**

Assert every report records immutable model revision and license evidence; BTC and XAUUSD metrics remain distinct; invalid/missing output counts are visible; latency and memory are measured rather than invented; repeated runs use the same frozen cases; candidate selection cannot be marked accepted when license evidence or required metrics are absent.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest tests.test_zarry_benchmark -v`

Expected: tests fail because the benchmark runner/report contract does not exist yet.

- [ ] **Step 3: Implement a small-model benchmark harness**

Shortlist small open-weight instruct models only after checking their current license and redistribution/hosting terms. Benchmark quantized CPU inference first on a representative environment; compare a second runtime only if the first cannot meet measured requirements. Include adversarial and missing-context cases: wrong symbol, stale timestamp, conflicting timeframes, absent indicators, WAIT/NO TRADE, and prompt-injection attempts. Select the smallest candidate that meets the approved quality, safety, latency, and resource criteria. Do not fine-tune at this stage.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest tests.test_zarry_benchmark -v`

Expected: benchmark protocol tests pass and produce a machine-readable report with per-asset metrics and hardware observations.

- [ ] **Step 5: Run a controlled benchmark**

Run: `python research/zarry/benchmark.py --cases research/zarry/evaluation_cases.jsonl --output artifacts/zarry/benchmark-report.json`

Expected: report contains actual measured values and candidate metadata. If no candidate meets the criteria, record that outcome and stop before provisioning; do not select a model by guesswork.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add research/zarry/benchmark.py research/zarry/model_candidates.json research/zarry/evaluation_cases.jsonl tests/test_zarry_benchmark.py
git commit -m "feat: benchmark ZARRY open-weight model candidates"
```

### Task 3: Build the isolated ZARRY inference service and authenticated API

**Files:**
- Create: `zarry_service/app.py` (proposed; FastAPI app and routes)
- Create: `zarry_service/schemas.py` (proposed; request/response models)
- Create: `zarry_service/inference.py` (proposed; selected runtime adapter)
- Create: `zarry_service/security.py` (proposed; service authentication and request limits)
- Create: `zarry_service/Dockerfile` (proposed; isolated serving image)
- Create: `zarry_service/README.md` (proposed; local run, health, deployment configuration)
- Create: `tests/test_zarry_service.py` (proposed; route, auth, schema and failure tests)

**Interfaces:**
- `GET /health` returns liveness only.
- `GET /ready` returns readiness and active model version only when model load and warm-up succeed.
- `POST /v1/explain` accepts a bounded request containing request ID, symbol, decision timestamp, approved structured context, Kitty deterministic assessment, and explanation task.
- Response returns request ID, model version, concise explanation, referenced input field names, uncertainty/limitations, and fixed non-authoritative label `explanation_only`.
- Consumes: selected model/runtime and environment configuration; produces: validated JSON response. No tools or order/execution capabilities are registered.

- [ ] **Step 1: Add failing tests for route and security boundaries**

Test unauthenticated request rejection; valid authenticated BTC and XAUUSD requests; unsupported symbol; malformed payload; oversized body; stale context; request timeout; model load failure/readiness false; inference exception; malformed model output; response schema mismatch; and explicit absence of order/tool capabilities.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest tests.test_zarry_service -v`

Expected: service import/route tests fail before implementation.

- [ ] **Step 3: Implement service using only the benchmark-selected runtime**

Keep model loading lazy/isolated within the ZARRY process. Authenticate every request with a dedicated shared secret from Railway variables; compare secrets safely; never log the secret or raw private prompt. Apply request-size, symbol, timestamp freshness, token/output, timeout, and rate limits. Keep liveness separate from readiness. Validate generated output against the response schema and reject unsupported claims or references to fields not supplied. Model output is data, never executable instructions. Configure bounded retries only for transient transport/model errors; do not retry schema-invalid generations indefinitely.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest tests.test_zarry_service -v`

Expected: all route, authentication, validation, readiness, timeout, malformed-output, and failure-isolation tests pass with a mocked inference adapter.

- [ ] **Step 5: Build and smoke-test the isolated container**

Run: `docker build -f zarry_service/Dockerfile -t zarry-service:test .`

Expected: container builds without modifying Fast's existing `dockerfile` or `requirements.txt`; a local smoke test reports `/health` live and `/ready` only after a test model is loaded.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add zarry_service tests/test_zarry_service.py
git commit -m "feat: add isolated ZARRY inference service"
```

### Task 4: Add optional Kitty explanation integration, evaluation gates, and paper-only deployment procedure

**Files:**
- Create: `zarry_client.py` (proposed; authenticated bounded Fast-to-ZARRY client)
- Create: `tests/test_zarry_client.py` (proposed; timeout, auth, validation and fallback tests)
- Create: `tests/test_kitty_zarry_integration.py` (proposed; deterministic decision invariance tests)
- Create: `research/zarry/evaluate.py` (proposed; frozen baseline-vs-ZARRY evaluation)
- Create: `research/zarry/DEPLOYMENT.md` (proposed; separate Railway service and staged rollout checklist)
- Modify only after route audit: `kitty_api.py` (optional explanation field/path; never change prediction/signal logic)
- Modify only after route audit: `api.py` (mount optional explanation endpoint only if existing route organization requires it)

**Interfaces:**
- `explain_kitty_context(context, request_id) -> ExplanationResult` returns either a validated explanation or a typed unavailable result; it never returns a replacement signal.
- Kitty response preserves all existing deterministic signal, gate, risk, and trading-enabled fields. Explanation status is separately exposed as available/unavailable.
- `evaluate(dataset_manifest, frozen_cases, baseline_outputs, zarry_outputs) -> EvaluationReport` compares explanation quality and operational behavior without converting explanation scores into trading-edge claims.

- [ ] **Step 1: Add failing tests for decision invariance and fail-open-to-Kitty behavior**

For BUY, SELL, WAIT/NO TRADE, stale data, rejected risk gates, and missing XAUUSD model cases, assert ZARRY cannot change the original signal or gate. Simulate connection refused, auth failure, 5xx, timeout, invalid JSON, unknown model version, and unsupported output; assert Kitty's deterministic result is returned unchanged with explanation marked unavailable. Assert the client sends only allowlisted structured context and no account credentials/private unrelated chat data.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m unittest tests.test_zarry_client tests.test_kitty_zarry_integration -v`

Expected: tests fail because the optional client/integration does not exist.

- [ ] **Step 3: Implement the optional explanation boundary and frozen evaluation**

Add an explicit feature flag defaulting off. The call must be bounded and non-blocking to Kitty's core decision path; where request lifecycle requires waiting, enforce a short configured deadline and return the deterministic Kitty result when it expires. Do not send model responses into trading/signal/risk functions. Add evaluation of grounding, correct preservation of Kitty decisions, correct asset/timeframe references, uncertainty, invalid-output rejection, latency, and failure rate. Compare Kitty alone with Kitty plus explanatory text; do not describe any explanation metric as profitability or signal improvement.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m unittest tests.test_zarry_client tests.test_kitty_zarry_integration -v`

Expected: all failure-mode tests pass and every paired test shows byte-for-byte-equivalent deterministic decision fields with ZARRY enabled or disabled.

- [ ] **Step 5: Run the affected regression suite and evaluation**

Run: `python -m unittest tests.test_kitty_signal_safety tests.test_kitty_market_data_provenance tests.test_kitty_gold_prediction tests.test_zarry_dataset tests.test_zarry_benchmark tests.test_zarry_service tests.test_zarry_client tests.test_kitty_zarry_integration -v`

Run: `python research/zarry/evaluate.py --manifest <versioned-manifest> --output artifacts/zarry/evaluation-report.json`

Expected: existing Kitty safety tests remain green; BTC and XAUUSD results are separately reported; holdout data remains untouched during model selection; no evaluation path enables live trading.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add zarry_client.py kitty_api.py api.py tests/test_zarry_client.py tests/test_kitty_zarry_integration.py research/zarry/evaluate.py research/zarry/DEPLOYMENT.md
git commit -m "feat: integrate optional ZARRY explanations with Kitty"
```

## Unresolved product decisions

These decisions must be confirmed from benchmark and cost evidence before the corresponding deployment or model-selection gate; they are not silently assumed in this plan:

1. Monthly hosting and inference budget ceiling, including artifact storage and network charges.
2. Maximum acceptable explanation latency and expected concurrent request volume.
3. Approved historical data sources and licensing/redistribution permissions for each BTC/XAUUSD dataset.
4. Final candidate model, exact immutable revision, quantization, serving runtime, and host; these depend on license review and measured benchmark results.
5. Whether a fine-tuning experiment is justified by baseline evaluation; if justified, approve its data scope and compute budget separately.
6. Whether Fast should expose explanations on an existing Kitty response or through a separate optional endpoint; settle after the API route audit, preserving backward compatibility either way.
7. Whether Railway CPU hosting meets the measured target or a separately priced GPU host is required. No service is provisioned until this is approved.
8. Rollout observation window and numerical operational acceptance thresholds for latency/error rate; determine from baseline measurements and the approved budget before paper-mode deployment.
