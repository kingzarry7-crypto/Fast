# Kitty Archived-Data Alternative Model Screen

**Run:** `kitty-archive-model-screen-2026-11-02`  
**Status:** Exploratory research only. No checkpoint promotion, signal enablement, or trading authorization.

## Purpose

Screen a small set of non-neural classifiers against the existing Kitty V3 MLP on the archived BTCUSD and XAUUSD feature datasets. The objective is to determine whether a simpler model family provides a more robust after-cost candidate. This is a screening experiment, not a replacement for the frozen benchmark protocol or a broker-fill simulation.

## Data and split

- Source: verified Task 1 run-106 archive, with BTC and XAUUSD kept separate.
- XAUUSD: 4,943 hourly rows; Twelve Data XAU/USD spot.
- BTCUSD: 4,888 hourly rows; Yahoo Finance fallback source recorded in the archive.
- Both datasets span 2026-04-07 through 2026-10-30 UTC.
- Features: the same 18 Kitty V3 features; target classes remain SHORT=0, NO TRADE=1, LONG=2.
- Chronological split: first 70% training, next 15% validation, final 15% untouched test; seven rows purged at each boundary.
- Scaling for logistic regression was fit only on training rows. Tree models were fit only on training rows.
- Validation alone selected a confidence threshold. The final test was evaluated once for a model/threshold pair only when the validation gate passed.

This archived sample ends on 2026-10-30. It is not fresh data as of this report date.

## Candidate models and fixed settings

- Logistic regression: standardized features, balanced class weights, C=0.1, max_iter=1,500.
- Extra Trees: 250 trees, min_samples_leaf=12, max_features=0.8, balanced class weights, seed 42.
- Random Forest: 250 trees, min_samples_leaf=12, max_features=0.8, balanced_subsample, seed 42.
- Histogram Gradient Boosting: 120 iterations, learning_rate=0.04, max_leaf_nodes=7, L2=3, seed 42.
- Confidence thresholds screened on validation: 0.40 to 0.90 in 0.025 increments.
- Validation gate: at least 30 non-overlapping trades, compounded net return >=1%, positive mean trade, profit factor >=1.10, and max drawdown no worse than -5%.
- Decision at row t uses the archived forward six-hour price proxy, with one trade allowed per six-hour outcome window. Estimated round-trip cost is 0.05%; stress cost is 0.075%.

The forward-return field is a proxy, not an intrabar OHLC fill simulation. Cost assumptions are not verified broker spreads or realized fills. These results must not be compared as if they were broker performance.

## Results

### XAUUSD

| Model | Validation trades | Validation net | Threshold | Test trades | Test net | Test stress | Test PF | Test drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 34 | +3.01% | 0.475 | 21 | -6.76% | -7.25% | 0.314 | -7.78% |
| Extra Trees | 59 | +7.51% | 0.475 | 63 | -0.65% | -2.20% | 0.956 | -4.58% |
| Random Forest | 79 | +4.77% | 0.400 | 83 | -4.16% | -6.13% | 0.801 | -6.03% |
| Histogram Gradient Boosting | 30 | +5.17% | 0.575 | 33 | +0.42% | -0.41% | 1.086 | -2.24% |

No XAUUSD model passed the final test after costs. Histogram Gradient Boosting was closest at base cost but fell negative under the 1.5x cost stress and had test PF below 1.10.

### BTCUSD

| Model | Validation trades | Validation net | Threshold | Test trades | Test net | Test stress | Test PF | Test drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | — | No validation candidate passed | — | — | Not evaluated | — | — | — |
| Extra Trees | — | No validation candidate passed | — | — | Not evaluated | — | — | — |
| Random Forest | 39 | +5.62% | 0.500 | 47 | -2.72% | -3.85% | 0.871 | -9.43% |
| Histogram Gradient Boosting | 73 | +7.93% | 0.425 | 72 | +1.29% | -0.52% | 1.064 | -6.89% |

No BTC model passed the final test after-cost robustness checks. Histogram Gradient Boosting had a small positive base-cost return but negative stress return, PF below 1.10, and drawdown beyond the -5% gate.

## Decision

- Do not promote any candidate model.
- Do not lower Kitty's confidence or edge gates to force directional signals.
- BTC remains fail-closed; XAUUSD remains fail-closed.
- Keep all outputs research/demo only and automatic order execution disabled.
- The next valid improvement attempt needs newer independently sourced market data, broker-specific spread/slippage observations, and repeated chronological walk-forward folds. The archived sample is too old and the validation-to-test degradation is too large to justify production signals.

## Reproducibility notes

The experiment used the archived CSVs and the settings stated above. The source archive is `/ZARRY/Task1/ZARRY-Task1-verified-artifacts-run-106.zip`. The canonical Task 1 manifest and corrected XAUUSD walk-forward report remain the source of truth for the original Kitty checkpoint results. This screen is supplementary and does not supersede them.

No production checkpoint, Railway service, Vercel project, broker setting, account permission, or trading order was changed.
