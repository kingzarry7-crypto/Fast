# ZARRY Task 2 — XAUUSD Shared Execution and Calibrated Walk-Forward

**Run:** `zarry-task2-xau-calibrated-walkforward-run-001`  
**Date:** 2026-10-31  
**Status:** Research-only. No promotion or trading authorization.

## Verified source artifacts

- Archived Task 1 run-106 bundle: `ZARRY-Task1-verified-artifacts-run-106.zip`.
- XAUUSD CSV SHA-256: `09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c`.
- Frozen XAUUSD checkpoint SHA-256: `5da5b2130a793ee315fa6ce2ed8e34e2b5e5b689f45a81c677a280d26f0a69f6`.
- 4,943 hourly rows, 18 features; XAUUSD source is Twelve Data XAU/USD spot.
- Cost assumption: 0.05% round trip; stress: 0.075%. These are assumed all-in costs, not measured broker fills.

## Execution protocol reconciled

All research model and rule evaluations now call the shared `zarry_execution.py` simulator:

1. Decision at candle close (t).
2. Entry at next candle open.
3. Exit at close of (t+7), representing the six-hour holding window.
4. A decision on the previous exit candle (t+7) is eligible; a decision at (t+6) remains overlapping.
5. Non-overlapping returns compound sequentially; drawdown is reported as a signed negative peak-to-trough fraction.
6. Incomplete final outcomes are skipped and counted.
7. Returns remain forward-price proxies, not broker fills or a realized paper-trade ledger.

The shared simulator is used by the baseline policy runner, Kitty confidence-gated model evaluation, six-hour momentum, and trend-confirmation evaluation. Regression tests cover the exit-candle boundary, overlap suppression, incomplete outcomes, cost deductions, compounding, and signed drawdown.

## Frozen checkpoint reproduction

Using the archived checkpoint's stored scaler and weights, the shared simulator reproduces the checkpoint's embedded XAUUSD test metrics:

| Partition | Trades | Net return at base cost | Return at 1.5× cost | Profit factor | Macro-F1 |
|---|---:|---:|---:|---:|---:|
| Validation | 32 | +1.19% | +0.38% | 1.178 | 0.571 |
| Untouched final test | 26 | +0.35% | -0.30% | 1.070 | 0.484 |

This resolves the earlier report inconsistency. The previous 30-trade / +2.52% validation and 25-trade / +0.46% final-test figures were stale and are superseded. The original report keeps those values only as an audit record.

## Disjoint probability-calibration experiment

Three expanding chronological folds were trained independently. Each fold uses five non-overlapping slices:

- Core training rows fit model weights and the feature scaler.
- A later early-stopping slice selects the training epoch.
- A separate calibration slice fits one scalar temperature by minimizing multiclass negative log-likelihood.
- A later policy-selection slice selects the confidence threshold using the existing fixed gate.
- The final fold test is not used to fit weights, temperature, or threshold.

The policy gate remains unchanged: at least 30 non-overlapping trades, at least +1% compounded net return, positive average trade, profit factor at least 1.10, and max drawdown no worse than -5%.

| Fold | Train / early-stop / calibration / policy / test | Best epoch | Temperature | Calibration NLL before → after | ECE before → after | Test macro-F1 | Selected confidence |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1,727 / 236 / 360 / 367 / 494 | 19 | 1.032 | 0.9114 → 0.9113 | 0.0864 → 0.0927 | 0.5088 | 1.01 (disabled) |
| 2 | 2,162 / 295 / 360 / 367 / 495 | 25 | 1.425 | 0.9931 → 0.9766 | 0.0919 → 0.0933 | 0.5545 | 1.01 (disabled) |
| 3 | 2,597 / 354 / 360 / 368 / 494 | 20 | 1.098 | 0.9044 → 0.9031 | 0.0623 → 0.0673 | 0.5789 | 1.01 (disabled) |

Temperature scaling slightly improved calibration-slice NLL in all folds, but expected calibration error worsened in all three. The NLL gains were very small in folds 1 and 3 and more noticeable in fold 2. The result is not evidence of a reliable calibrated edge.

No policy-selection slice passed the predeclared trading gate. All three fold models therefore selected the fail-closed 1.01 confidence sentinel and emitted zero test trades. This is the correct abstention outcome; the threshold was not relaxed.

## Rule baselines on the same fold test windows

| Fold | Momentum trades | Momentum base return | Momentum 1.5× return | Trend-confirmation trades | Trend-confirmation base return |
|---|---:|---:|---:|---:|---:|
| 1 | 49 | +2.09% | +0.84% | 44 | -4.28% |
| 2 | 49 | +3.52% | +2.26% | 42 | -3.04% |
| 3 | 50 | +0.57% | -0.68% | 40 | +1.19% |

Momentum is positive at base costs in all three folds but loses its edge under stress in fold 3. Trend confirmation is inconsistent and materially negative in folds 1 and 2. Neither rule passes the full promotion/robustness gate.

## Conclusion

- Shared execution semantics now remove separate trade-timing implementations between Kitty and the rule baselines.
- The frozen XAUUSD checkpoint's final-test after-cost result remains weak: +0.35% base, -0.30% stress, PF 1.070.
- The disjoint temperature-calibration experiment did not improve ECE and did not produce a passing confidence threshold in any fold.
- Fold-trained Kitty remains fail-closed. No baseline qualifies for promotion.
- Do not lower thresholds, tune against the final test, promote a checkpoint, or enable live signals.

## Safety

No production Kitty checkpoints or services were modified. No Railway, Vercel, broker settings, or account permissions were changed. No live or demo orders were placed. ZARRY remains research-only and live trading remains disabled.
