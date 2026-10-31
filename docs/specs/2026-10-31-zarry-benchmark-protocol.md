# ZARRY Task 2 — Frozen Benchmark Protocol

**Frozen:** 2026-10-31  
**Status:** Protocol only; no new model training, benchmark execution, promotion, or deployment is authorized by this document.  
**Repository:** `kingzarry7-crypto/Fast`  
**Task 1 dependency:** draft PR #213, branch `feat/zarry-dataset-task1`  
**Task 2 branch:** `feat/zarry-task2-benchmark-protocol`

## 1. Purpose and decision boundary

This protocol fixes the data, split, baselines, cost assumptions, metrics, and reporting rules before any new comparative run. BTCUSD and XAUUSD are separate experiments. No pooled asset score is permitted.

ZARRY and Kitty candidates are research-only. Kitty's deterministic signal and risk logic remains authoritative. No model may create or submit orders, override WAIT/NO TRADE, or change risk settings. No live signal, production promotion, Railway change, or Vercel change is part of Task 2.

## 2. Immutable source data

Use only the Task 1 run-106 files in the verified archive:

- Archive: `/ZARRY/Task1/ZARRY-Task1-verified-artifacts-run-106.zip`
- Archive SHA-256: `5ad9ecf64982460c6c1b4a7501acd6e5586cfddc7eab003a88e6e43bca0a09c2`
- Workflow run: [41173387628](https://github.com/kingzarry7-crypto/Fast/actions/runs/41173387628)
- Source commit: `7d37df7e104f388a1197cfd8c9c1f70c0733565a`

| Asset | Rows | UTC range | Source | CSV SHA-256 |
|---|---:|---|---|---|
| BTCUSD | 4,888 | 2026-04-07 21:00 to 2026-10-30 21:00 | Yahoo Finance fallback | `c4c017a7a32ed98c3a336e92c33e51bd9a489fe403e003a89bee6623a58674d5` |
| XAUUSD | 4,943 | 2026-04-07 23:00 to 2026-10-30 21:00 | Twelve Data XAU/USD spot | `09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c` |

The 18-feature schema and order are fixed by the Task 1 adapter. Preserve source identity: do not silently relabel Yahoo Finance BTC as a particular exchange's BTC/USD spot feed, and do not substitute gold futures for Twelve Data XAU/USD spot. Do not fetch newer data, repair rows, or recompute features during this benchmark. A changed source file or feature schema requires a new protocol version.

## 3. Labels and timing

Class mapping is fixed: `0 = SHORT`, `1 = NO TRADE`, `2 = LONG`.

The dataset target is a **forward-price proxy**, not a realized paper-trade outcome. The recorded convention is decision at candle t, entry at the next hourly candle open, and exit at the close of the candle seven hourly indices after t (six hours after entry). Use the supplied `forward_return_6h`, `entry_price_next_open`, and `exit_price_after_6h` fields only after verifying the source hashes and the existing consistency checks.

Do not present proxy-label accuracy as realized trading performance. No unverified or open trade may be counted as a realized outcome.

## 4. Chronological partitions and leakage control

Use the exact Task 1 chronological partition sizes, in source timestamp order:

| Asset | Train | Validation | Final test | Purged rows at each boundary |
|---|---:|---:|---:|---:|
| BTCUSD | 3,414 | 726 | 734 | 7 |
| XAUUSD | 3,453 | 734 | 742 | 7 |

The counts exclude exactly 14 rows per asset: seven rows immediately before each raw 70%/85% boundary. To reproduce the archived partitions, let `b1 = floor(N × 0.70)` and `b2 = floor(N × 0.85)`, then use `train = rows[0:b1-7]`, `validation = rows[b1:b2-7]`, and `test = rows[b2:N]`. For BTCUSD, `b1=3421` and `b2=4154`; for XAUUSD, `b1=3460` and `b2=4201`. This is a seven-row trailing purge on the earlier partition at each boundary—not seven rows removed from both sides. The `chronological_split()` helper has been corrected to purge only the seven rows immediately before each raw boundary. Regression tests assert both archived asset counts and exact boundary indices. Do not shuffle. Do not allow an example's six-hour outcome window to cross a partition boundary. Fit all scalers, imputers, feature transforms, class weights, and model-selection decisions on train only; use validation for hyperparameters, confidence thresholds, and checkpoint selection. The final test is evaluated once after the complete candidate and threshold are frozen. No test-driven tuning, threshold changes, checkpoint swaps, or repeated peeking.

In addition, simulate trades chronologically and skip any new signal whose outcome window overlaps an already-open simulated trade. Record skipped overlapping signals. Apply the same overlap rule to every trading baseline and candidate.

## 5. Predeclared baselines

Run the following for each asset independently, on identical validation/test periods and with identical cost/overlap rules:

1. **Majority-class classifier:** always predict the most frequent train-set class. Report accuracy, balanced accuracy, macro-F1, and confusion matrix. The majority class must be calculated from train, not test.
2. **Always-WAIT policy:** always output class 1 and place zero simulated trades. This is the safety/abstention reference, not a profitable strategy.
3. **Six-hour momentum:** use the sign of `ret_6h`; emit LONG or SHORT only when absolute momentum meets or exceeds the asset's recorded label threshold (BTCUSD 0.003; XAUUSD 0.0015); otherwise WAIT.
4. **Trend-confirmation baseline:** require the six-hour momentum direction to meet the same threshold and require `close_vs_sma6`, `close_vs_sma20`, and `sma6_vs_sma20` all to agree with that direction; otherwise WAIT.

For the model candidate, use the checkpoint and inference code pinned in the run manifest. Do not compare a newly trained model with an old baseline implementation or silently change baseline definitions between assets. If the existing trend baseline implementation differs from the explicit rule above, stop and reconcile the implementation before running; do not reinterpret old report numbers as if they came from a different rule.

## 6. Costs and trade simulation

Use the existing conservative all-in round-trip assumptions:

- BTCUSD: 0.10% per completed trade (0.001).
- XAUUSD: 0.05% per completed trade (0.0005).
- Stress case: 1.5 times the base cost for each asset.

Subtract costs from each trade return before compounding. State clearly that these are assumptions covering spread, commissions/fees, and slippage; they are not verified broker fills or live bid/ask measurements. Do not use gross returns for any promotion decision. Report base-cost and 1.5x-cost results side by side.

## 7. Required metrics

**Classification:** sample count, class distribution, accuracy, balanced accuracy, macro-F1, per-class precision/recall/F1, confusion matrix, and log loss where calibrated probabilities exist.

**Trading:** number of completed trades, win rate, average net trade return, expectancy, profit factor, compounded net return, maximum drawdown, exposure/time-in-market, overlap skips, and results under both cost levels. If no trades occur, report zero trades and zero return; do not manufacture a win rate or profit factor.

**Robustness:** three chronological expanding-window walk-forward folds, each with its own prior-only validation threshold selection; report every fold, not just the average. Keep each fold's test outcomes isolated from its threshold-selection window.

**Operational:** inference latency, memory/resource use, invalid-output rate, and abstention behavior are measured separately from trading performance. A language-model quality score is not a trading metric.

## 8. Evaluation and promotion gates

A candidate is **not eligible** for promotion unless all conditions hold:

- It is evaluated separately on BTCUSD and XAUUSD with the frozen data and code.
- It has at least 30 non-overlapping completed trades per asset in the aggregate evaluation; report smaller samples as insufficient evidence.
- Net compounded return is positive after base costs and remains positive under the 1.5x cost stress test.
- Profit factor exceeds 1.0 and maximum drawdown is no worse than 5% in every reported out-of-sample fold.
- It improves on the relevant predeclared trading baseline after costs, without relying on accuracy alone.
- Results are directionally consistent across all three walk-forward folds; any fold failure blocks promotion pending new data or a new protocol version.
- All dataset, leakage, reproducibility, safety, and inference-contract tests pass.

Passing these gates is necessary, not a guarantee of future profitability. Failure or insufficient trade count means remain research-only and emit WAIT/NO TRADE where appropriate. No live trading approval is implied.

## 9. Reproducibility and report contract

Every run must record: protocol version and file hash; source archive and per-CSV hashes; source workflow run and commit; feature schema/version; asset/source identity; code commit; Python and dependency versions; checkpoint SHA-256; random seeds; exact partition indices/timestamps; purge and overlap rules; cost assumptions; baseline definitions; all metrics; and a machine-readable report.

A run that cannot reproduce its source hashes, partition sizes, model artifact, or baseline implementation is invalid and must not be compared. Keep raw outputs and logs with the report. Do not overwrite prior runs.

## 10. Existing evidence — historical only, not a new Task 2 run

The Task 1 reports contain earlier diagnostics. They predate this frozen protocol and are retained only as context; they are not a confirmatory Task 2 benchmark.

- BTCUSD selected candidate: 39.51% final-test accuracy, macro-F1 0.363, zero paper trades. The prior three-fold report recorded zero candidate trades; momentum was profitable in one fold and trend confirmation in two folds.
- XAUUSD selected candidate: 50.81% final-test accuracy, macro-F1 0.484, 26 paper trades, +0.346% at the base assumed cost and −0.304% at 1.5x cost. Its prior three-fold diagnostics recorded zero candidate trades; momentum was profitable in all three folds, while trend confirmation was profitable in one fold.
- These earlier results do not meet the evidence bar above. Neither checkpoint is promoted.

## 11. Execution sequence

1. Merge/review the Task 1 dataset-contract PR only after its tests pass; do not merge it automatically as part of Task 2.
2. Confirm the benchmark runner implements this document exactly; the split-boundary and seven-row trailing-purge regression tests are now in place. Add tests for non-overlap, cost deduction, and baseline decisions before running the benchmark.
3. Run the baselines first and save their immutable report.
4. Run the existing selected Kitty checkpoints against those same partitions.
5. Run any ZARRY model candidate only after its model artifact, inference code, and seed are pinned.
6. Publish per-asset and per-fold reports. Keep all artifacts research-only.

**Freeze rule:** Any change to data, labels, partitions, baseline rules, cost assumptions, metrics, or gates requires a new dated protocol version and must be disclosed before the next run.
