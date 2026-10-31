# ZARRY Model Service — Design Specification

**Date:** 2026-10-31  
**Status:** Design approved by the user; implementation not yet approved  
**Repository:** `kingzarry7-crypto/Fast`  
**Target branch:** `main` (implementation target only; this document is included in draft PR #213 for review)

## 1. Goal and scope

Build **ZARRY**, an independently hosted open-weight language model service that Kitty can call for trading-focused interpretation and explanations. The first phase is limited to BTC and XAUUSD analysis. A later, separately scoped phase may extend ZARRY to general King Zarry AI conversations across web, Telegram, and Discord.

The objective is to avoid external per-request model API charges for ZARRY inference. Hosting, storage, networking, and any fine-tuning compute may still incur costs. This project does not promise profitability or make the model itself a trading strategy.

### Out of scope for phase one

- Replacing Kitty's deterministic market-data, indicator, signal, or risk-validation logic.
- Enabling live trading, placing orders, or changing broker/execution permissions.
- Rebuilding or training a frontier model from scratch.
- Expanding ZARRY to general-purpose assistant duties.
- Changing the existing production Fast Railway service or Vercel configuration.
- Removing existing AI providers until the self-hosted service has passed acceptance tests and a separate migration decision is approved.

## 2. Approved architecture

1. Keep the existing Fast/Kitty backend as the owner of market data, deterministic analysis, signal validation, risk controls, and execution permissions.
2. Deploy ZARRY as a **separate Railway service**. It communicates with Fast over Railway's private network where supported.
3. Start with a small, quantized open-weight instruct model. Select the exact model only after checking license, hardware fit, tool-use/structured-output reliability, and a representative evaluation set.
4. Keep model serving isolated from Kitty's trading process. Model failure must not take down Kitty.
5. Use a versioned model artifact and a versioned inference API. Do not make model weights or training artifacts part of the Fast application image unless later evidence supports that choice.
6. Fine-tuning is a separate training job. Prefer parameter-efficient fine-tuning (such as LoRA/QLoRA) if evaluation shows it adds value; do not assume fine-tuning is necessary before a baseline model is measured.

### Logical flow

`Market data → Kitty deterministic analysis and validation → structured context → ZARRY explanation → output validation → user`

ZARRY may explain supplied facts, identify uncertainty, summarize historical patterns, and ask for missing context. It must not invent live prices, candles, indicator values, fills, or trade outcomes. Kitty remains authoritative for all numeric market facts and trading decisions.

## 3. Data and learning design

The initial curated dataset may include historical BTC and XAUUSD candles, time-aligned indicators, multi-timeframe context (4H, 1H, 15M, 5M), Kitty's historical BUY/SELL/WAIT signals, entry/stop/target plans, and realized or simulated outcomes including fees and estimated slippage.

Include both successful and unsuccessful examples, plus cases where WAIT was the correct decision. Label outcomes and provenance explicitly. Separate assets and regimes in evaluation reports.

### Data integrity requirements

- Use chronological train/validation/holdout splits; never randomly mix future observations into earlier training samples.
- Construct each training example using only information available at its decision timestamp.
- Exclude or correctly model overlapping trades and label horizons.
- Prevent duplicate examples from crossing dataset splits.
- Record source, symbol, timeframe, timestamp, feature version, label definition, and cost assumptions.
- Remove credentials, personal data, account identifiers, and unrelated chat content from training data.
- Do not train on unverified or fabricated outcomes.
- Keep a reproducible dataset manifest and record the model/data versions for every experiment.

Fine-tuning examples should teach analysis quality and grounded explanations, not teach the model to claim profitability. The model must express uncertainty and abstain when evidence is incomplete.

## 4. Service interface and security

Fast calls the ZARRY service through an authenticated, private service-to-service interface. The exact API schema will be finalized in the implementation plan, but the initial contract should support:

- Health/readiness and model-version reporting.
- A bounded inference request containing symbol, timestamp, approved structured market context, Kitty's deterministic assessment, and the requested explanation task.
- A structured response containing concise analysis, cited input facts/field references where practical, uncertainty/limitations, and a non-authoritative recommendation label such as `explanation_only`.
- Request IDs and latency/error metadata for observability.

Security requirements:

- Authenticate every inference request with a dedicated secret stored in Railway variables; never commit secrets.
- Restrict network access to the Fast service where Railway private networking permits.
- Validate request size, symbol allowlist, timestamp freshness, and schema.
- Apply bounded input/output token limits, request timeouts, and rate limits.
- Do not expose raw prompts, secrets, or private user data in routine logs.
- Treat model output as untrusted text/data; validate schema and escape it before rendering.
- Do not let model output invoke tools, broker APIs, order endpoints, or mutate risk settings.

## 5. Reliability and failure handling

- If ZARRY is unavailable, slow, or returns invalid output, Kitty continues using its existing deterministic workflow and clearly marks the AI explanation as unavailable.
- Use a strict timeout and at most a small bounded retry policy for transient errors.
- Do not retry indefinitely or block market-data collection and risk validation on model responses.
- Reject malformed, stale, unsupported, or contradictory output.
- Include readiness checks and resource monitoring for CPU, memory, disk, latency, and error rate.
- Roll out new model versions behind an explicit version switch; retain the last known-good version for rollback.

## 6. Trading safety boundary

The following rules are mandatory:

- ZARRY is advisory and explanatory; it is not the source of truth for prices, indicators, account state, or order status.
- Kitty's deterministic validation and risk engine remains authoritative.
- ZARRY cannot override WAIT/NO TRADE, stale-data rejection, market/news filters, stop-loss requirements, risk limits, duplicate-order prevention, or the live-trading kill switch.
- Phase one remains paper/demo/research only. No live-trading enablement is included.
- No model response may directly create or submit an order.
- Any future change to this boundary requires a separate explicit design and approval.

## 7. Evaluation and acceptance criteria

Evaluate the baseline model before fine-tuning, then compare any tuned candidate on the same frozen evaluation protocol.

### Model quality

- Groundedness against supplied structured facts.
- Correct handling of BUY/SELL/WAIT context without inventing or changing Kitty's decision.
- Correct asset/timeframe identification.
- Ability to explain uncertainty, conflicting timeframes, stale data, and missing inputs.
- Valid structured output and safe refusal/abstention behavior.
- Response latency and resource use under representative load.

### Trading research

- BTC and XAUUSD results reported separately.
- Chronological unseen holdout data.
- Costs and slippage included where trade outcomes are assessed.
- Compare Kitty alone against Kitty plus ZARRY; do not attribute a performance improvement without evidence.
- Report sample sizes, win/loss distribution, expectancy, drawdown, and limitations. A language-model explanation score is not a profitability metric.

### Operational acceptance

- ZARRY can be deployed and health-checked independently.
- Fast can call it privately with authentication.
- Failure of ZARRY does not interrupt Kitty's deterministic analysis or safety checks.
- Invalid output is rejected.
- Existing Fast service and bots remain healthy during integration tests.
- No live orders are possible through the ZARRY interface.

Passing these tests does not establish future profitability or guarantee accurate signals.

## 8. Deployment and cost approach

Deploy a separate Railway service first, subject to confirming available service resources, runtime compatibility, and realistic inference latency. Benchmark CPU inference with a small quantized model before deciding whether a GPU host is necessary. Do not assume the existing Fast service's resource allocation is available to the new service.

Estimate monthly inference hosting, artifact storage, network, and one-off fine-tuning costs before provisioning. Keep the service scaled down or stopped when not needed if the platform supports this without compromising required availability. No Railway production resources are to be changed as part of this design-document commit.

## 9. Phased delivery

1. **Repository and data audit:** inspect Kitty's current signal interfaces, data sources, history quality, and existing safety tests.
2. **Baseline model benchmark:** shortlist licensed open-weight small models; benchmark on a fixed BTC/XAUUSD explanation dataset and available hosting hardware.
3. **Service prototype:** implement the isolated inference service, authentication, health checks, schema validation, timeouts, and observability.
4. **Kitty integration:** add an optional explanation path that cannot alter deterministic decisions or execute trades.
5. **Historical evaluation:** compare baseline and optional fine-tuning using chronological holdout data.
6. **Paper-mode rollout:** deploy only after tests pass; monitor reliability and resource usage.
7. **Future expansion:** separately design general assistant integration after the trading-focused phase is accepted.

## 10. Open implementation decisions

These are intentionally deferred to the implementation plan and evidence-gathering stage:

- Exact model family, parameter count, quantization, and license.
- Inference runtime and container image.
- Whether CPU-only Railway hosting meets latency and cost targets or a GPU host is justified.
- Exact request/response schema and authentication mechanism.
- Training corpus size, permissible sources, and whether fine-tuning materially improves results.
- Resource limits, scaling policy, and monthly budget.

No model name, benchmark result, profitability claim, hosting price, or deployment capability should be presented as confirmed until verified.

## 11. Task 1 dataset checkpoint and Task 2 gate

The first historical dataset retrieval and integrity review is complete. The recorded source inventory at this checkpoint is:

| Asset | Samples | Source | Evaluation note |
|---|---:|---|---|
| BTCUSD | 4,888 | Yahoo Finance fallback | Research-only |
| XAUUSD | 4,943 | Twelve Data XAU/USD | Research-only |

The retrieved CSVs were checked for duplicate timestamps, missing values, non-finite feature values, and forward-return calculation mismatches. The checkpoint report recorded zero issues in those checks. The source identity must remain explicit: BTC quote/source conventions must not be silently conflated with BTC/USD spot, and XAUUSD must remain the Twelve Data XAU/USD spot series rather than a futures proxy.

The initial model results are not sufficient for promotion:

- BTCUSD holdout: 734 samples, 39.51% accuracy, macro-F1 0.363, zero paper trades, net return 0%.
- XAUUSD holdout: 742 samples, 50.81% accuracy, macro-F1 0.484, 26 paper trades, +0.346% before the 1.5× cost stress test; the same stress test returned −0.304%.
- The XAUUSD momentum baseline returned +3.50% on the same holdout.
- Neither candidate was profitable in any of the three recorded walk-forward folds.

These figures are checkpoint evidence, not a claim of future performance. Both candidate checkpoints remain research-only and neither asset is approved for live signals or live trading.

**Task 2 entry gate:** freeze and document the dataset manifests, source hashes, feature schema, label/entry/exit convention, split boundaries, purge/embargo rules, and evaluation script before running any comparative benchmark. Compare BTCUSD and XAUUSD separately. Use identical chronological partitions for every candidate and baseline, prevent overlapping outcomes from leaking across partitions, and include fees/slippage in trade-level results. Keep a simple non-ML baseline. Do not select a model based on accuracy alone, do not tune on holdout data, and do not promote a checkpoint unless it beats the relevant baseline consistently across multiple unseen periods after realistic costs.

The existing adapter and dataset contract are ingestion/validation components only. They do not by themselves prove that the original downloaded artifacts, manifests, and checkpoints are permanently archived or independently reproducible. That artifact-archive and manifest-verification task must be completed before model benchmarking proceeds.

## 12. Approval record

The user approved:
- The name **ZARRY**.
- Trading-first scope, followed by possible broader King Zarry AI integration.
- A small model first, upgraded only if testing justifies it.
- Separate hosting connected to Kitty.
- Learning from curated historical BTC and XAUUSD data, including winning and losing examples.
- Reliability, isolation, failure handling, monitoring, and paper-only safety rules.

**This document records the design only. It does not authorize implementation, production deployment, or live trading.**
