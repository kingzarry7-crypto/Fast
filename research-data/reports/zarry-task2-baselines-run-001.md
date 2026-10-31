# ZARRY Task 2 — Baseline Benchmark Report

**Run:** `zarry-task2-baselines-run-001`  
**Date:** 2026-10-31  
**Status:** Research-only; no candidate promotion or trading authorization.

## Reproducibility

- Source archive SHA-256: `5ad9ecf64982460c6c1b4a7501acd6e5586cfddc7eab003a88e6e43bca0a09c2`
- BTCUSD CSV SHA-256: `c4c017a7a32ed98c3a336e92c33e51bd9a489fe403e003a89bee6623a58674d5`
- XAUUSD CSV SHA-256: `09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c`
- Baseline implementation commit: `7716daef90e7a3a2bb2025ec30ff0caaaf9c76a8`
- Original Task 1 workflow run: [41173387628](https://github.com/kingzarry7-crypto/Fast/actions/runs/41173387628)
- Only archived run-106 CSVs were used; no new market data was fetched.
- BTCUSD source is Yahoo Finance fallback; XAUUSD source is Twelve Data XAU/USD spot.
- 18 feature columns; no duplicate timestamps, missing cells, or non-finite numeric values.
- Split counts: BTCUSD 3,414 / 726 / 734; XAUUSD 3,453 / 734 / 742 (train / validation / final test).
- Seven rows purged before each raw split boundary.
- Costs: BTCUSD 0.10% round trip; XAUUSD 0.05%; stress = 1.5× base cost.
- Trade timing: decision at t, entry next open, exit at close of t+7. A signal at the previous exit candle is permitted because its entry is after the prior exit.
- Reconciled simulator: finite precomputed `forward_return_6h` values remain valid even when t+7 falls beyond the local evaluation slice; t+7 controls overlap eligibility only. Missing/non-finite outcomes are skipped. All strategy families now use the shared `zarry_execution.py` implementation.
- The trading tables below supersede the earlier values in this report, which incorrectly dropped finite outcomes at evaluation-slice tails.
- Outcomes are forward-price proxies, not realized paper trades or broker fills.

## Final-test trading summary

| Asset | Baseline | Trades | Win rate | Net expectancy/trade | Profit factor | Net return | 1.5× cost return | Max drawdown |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | majority | 0 | — | 0.00% | — | 0.00% | 0.00% | 0.00% |
| BTCUSD | always_wait | 0 | — | 0.00% | — | 0.00% | 0.00% | 0.00% |
| BTCUSD | momentum | 89 | 41.57% | -0.24% | 0.461 | -19.77% | -23.27% | 19.77% |
| BTCUSD | trend_confirmation | 72 | 36.11% | -0.31% | 0.398 | -20.15% | -22.99% | 20.94% |
| XAUUSD | majority | 0 | — | 0.00% | — | 0.00% | 0.00% | 0.00% |
| XAUUSD | always_wait | 0 | — | 0.00% | — | 0.00% | 0.00% | 0.00% |
| XAUUSD | momentum | 75 | 52.00% | 0.05% | 1.284 | 3.50% | 1.58% | 3.52% |
| XAUUSD | trend_confirmation | 64 | 43.75% | -0.08% | 0.681 | -4.84% | -6.35% | 7.82% |

## Classification snapshot — final test

| Asset | Baseline | Accuracy | Balanced accuracy | Macro-F1 |
|---|---|---:|---:|---:|
| BTCUSD | majority | 36.92% | 33.33% | 17.98% |
| BTCUSD | always_wait | 36.92% | 33.33% | 17.98% |
| BTCUSD | momentum | 33.24% | 32.47% | 32.40% |
| BTCUSD | trend_confirmation | 35.15% | 33.23% | 30.48% |
| XAUUSD | majority | 43.80% | 33.33% | 20.31% |
| XAUUSD | always_wait | 43.80% | 33.33% | 20.31% |
| XAUUSD | momentum | 48.25% | 44.66% | 44.62% |
| XAUUSD | trend_confirmation | 45.01% | 39.11% | 37.82% |

## Three expanding-window walk-forward folds

The archived Task 1 fold indices were reused. These baselines have fixed rules; no threshold was selected from validation. Values show base-cost / 1.5×-cost compounded net return.

| Asset | Baseline | Fold 1 | Fold 2 | Fold 3 | Base-positive folds | Stress-positive folds |
|---|---|---:|---:|---:|---:|---:|
| BTCUSD | majority | -18.58% / -21.39% | 0.22% / -3.23% | 0.00% / 0.00% | 1/3 | 0/3 |
| BTCUSD | always_wait | 0.00% / 0.00% | 0.00% / 0.00% | 0.00% / 0.00% | 0/3 | 0/3 |
| BTCUSD | momentum | 3.43% / 0.68% | -0.30% / -3.15% | -1.79% / -4.65% | 1/3 | 1/3 |
| BTCUSD | trend_confirmation | 0.83% / -1.36% | -9.41% / -11.69% | 0.59% / -1.99% | 2/3 | 0/3 |
| XAUUSD | majority | 0.00% / 0.00% | 0.00% / 0.00% | 0.00% / 0.00% | 0/3 | 0/3 |
| XAUUSD | always_wait | 0.00% / 0.00% | 0.00% / 0.00% | 0.00% / 0.00% | 0/3 | 0/3 |
| XAUUSD | momentum | 1.87% / 0.60% | 3.53% / 2.24% | 0.74% / -0.54% | 3/3 | 2/3 |
| XAUUSD | trend_confirmation | 1.31% / 0.23% | -4.47% / -5.42% | -2.69% / -3.71% | 1/3 | 1/3 |

## Interpretation

- **BTCUSD:** momentum and trend-confirmation lose materially on the untouched final test (-19.77% and -20.15% after base costs). Both also fail stress-cost and drawdown robustness. No directional baseline is acceptable.
- **XAUUSD:** momentum is positive on the final test (+3.50% base; +1.58% at 1.5× costs; PF 1.284; max drawdown 3.52%) and profitable in all three folds at base cost. However, it is negative in one fold under 1.5× costs and one fold exceeds the 5% drawdown ceiling. It therefore fails the frozen robustness/promotion gates.
- **Trend confirmation** is negative on both final tests and does not pass fold robustness.
- **Majority** predicts NO TRADE on the full train partitions, matching Always-WAIT. In some expanding folds its training majority differs, so it can trade; that is expected from the train-only rule.
- No baseline is eligible for promotion. These are benchmarks, not proof of future profitability.

## Limitations and next gate

- This run evaluates the frozen baselines only; it does not evaluate Kitty checkpoints or a ZARRY model candidate.
- No realized paper-trade ledger was used. All trading metrics are computed from the archived forward-return proxy.
- Operational latency/resource metrics were not measured for these deterministic policies.
- Keep Kitty authoritative and ZARRY research-only. Do not enable live signals or orders from these results.

Full per-period and per-fold metrics, confusion matrices, per-class metrics, trade lists, costs, overlap skips, and drawdowns are retained in the accompanying machine-readable JSON report.
