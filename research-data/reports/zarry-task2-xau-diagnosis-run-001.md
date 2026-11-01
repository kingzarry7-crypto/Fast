> **SUPERSEDED — 2026-10-31:** This earlier diagnosis used a separate simulator that dropped valid finite forward-return outcomes when the t+7 exit index fell beyond the evaluation slice. The canonical corrected analysis now uses the shared simulator and disjoint calibration/policy windows. See [the calibrated XAUUSD walk-forward report](zarry-task2-xau-calibrated-walkforward-run-001.md).

# ZARRY Task 2 — XAUUSD Validation/Test Diagnosis and Fold-Trained Walk-Forward

**Run:** `zarry-task2-xau-diagnosis-run-001`  
**Date:** 2026-10-31  
**Status:** Research-only. No promotion or trading authorization.

## Reproducibility and scope

- Source: archived Task 1 run-106 XAUUSD Twelve Data XAU/USD spot CSV.
- CSV SHA-256: `09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c`.
- Frozen checkpoint SHA-256: `5da5b2130a793ee315fa6ce2ed8e34e2b5e5b689f45a81c677a280d26f0a69f6`.
- 4,943 hourly samples; 18 Kitty features; 7-row purge at each boundary.
- The frozen checkpoint was re-evaluated without changing its weights. Three separate models were then trained from scratch inside three expanding chronological folds. Each fold's scaler was fit on that fold's training rows only; confidence selection used only that fold's validation rows.
- Model: existing Kitty V3 baseline MLP `[18, 64, 32, 3]`, AdamW, seed 42/43/44, max 30 epochs, early stopping patience 5, batch 128, weight decay `1e-4`.
- Cost assumption: 0.05% round trip; stress: 0.075%. Costs are assumptions, not measured broker fills.
- Labels/returns are forward-price proxies, not realized broker fills or a paper-trade ledger.

## Frozen-checkpoint reproduction and report discrepancy

The archived checkpoint's stored validation/test results were independently reproduced using its stored scaler and the repository's current `train_kitty_v3_retrained.py` evaluation convention (including the corrected prior-exit-candle eligibility rule).

| Partition | Trades | Net return at base cost | Return at 1.5× cost | Profit factor | Macro-F1 |
|---|---:|---:|---:|---:|---:|
| Validation | 32 | +1.19% | +0.38% | 1.178 | 0.571 |
| Untouched final test | 26 | +0.35% | -0.30% | 1.070 | 0.484 |

The earlier `zarry-task2-kitty-evaluation-run-001.md` in PR #215 reports validation 30 trades / +2.52% and final test 25 trades / +0.46% / -0.17% stress. Those values do **not** reproduce from the archived checkpoint with the corrected repository evaluator. The archived checkpoint's own `test_metrics` and the independent re-run agree at 26 trades, +0.3459% base, and -0.3042% stress. Treat the earlier report's XAUUSD trading figures as superseded pending a protocol-level reconciliation; do not silently combine the two result sets.

Classification degradation is also clear: accuracy fell from 57.49% to 50.81%, balanced accuracy from 56.79% to 48.37%, and macro-F1 from 57.13% to 48.35%. In the final test, the model predicted 350 SHORT / 207 NO TRADE / 185 LONG, while the true counts were 240 / 325 / 177. It over-predicted SHORT and under-predicted NO TRADE.

## Regime and distribution diagnosis

| Measure | Validation | Final test | Change |
|---|---:|---:|---:|
| 6-hour volatility mean, relative to validation | 1.000 | 0.891 | -10.9% |
| 24-hour volatility mean, relative to validation | 1.000 | 0.888 | -11.2% |
| Forward-return standard deviation | 0.593% | 0.488% | -17.7% |
| SHORT label share | 32.4% | 32.3% | -0.1 pp |
| NO TRADE label share | 39.6% | 43.8% | +4.3 pp |
| LONG label share | 27.9% | 23.9% | -4.0 pp |

The largest validation-to-test feature mean shift was volatility_24h at about -0.17 training-standard-deviations; the maximum feature mean shift across train-to-test was about 0.29 standard deviations. This is measurable but not an extreme wholesale distribution break. The forward-return distribution narrowed and the class mix shifted toward NO TRADE. The checkpoint's directional predictions did not adjust to that mix: SHORT predictions rose while LONG predictions fell. This supports a generalization/calibration and regime-sensitivity problem; it does not prove that volatility alone caused the decline.

## Proper fold-trained walk-forward

Each fold trained a new model from its own expanding training window. No frozen full-training checkpoint was applied to earlier folds.

| Fold | Train / validation / test rows | Best epoch | Validation-selected confidence | Kitty test trades | Kitty test net return | Momentum test trades | Momentum base return | Momentum 1.5× return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1,970 / 734 / 494 | 22 | 1.01 (disabled) | 0 | 0.00% | 50 | +1.87% | +0.60% |
| 2 | 2,464 / 734 / 495 | 15 | 1.01 (disabled) | 0 | 0.00% | 50 | +3.53% | +2.24% |
| 3 | 2,958 / 735 / 494 | 27 | 1.01 (disabled) | 0 | 0.00% | 51 | +0.74% | -0.54% |

The predeclared threshold gate requires at least 30 validation trades, at least 1% compounded net return, positive average trade, profit factor at least 1.10, and max drawdown no worse than -5%. No fold qualified:

- Fold 1 at 0.50 confidence had 28 trades and +0.75% net, below both the trade-count and return minimums.
- Fold 2 at 0.50 had 12 trades and -2.18% net.
- Fold 3 at 0.50 had 32 trades but only +0.48% net, PF 1.058, and -5.80% drawdown.

Therefore all three fold models correctly selected the fail-closed 1.01 confidence sentinel and emitted zero test trades. The model's fold test macro-F1 scores were 0.516, 0.563, and 0.577, but classification scores did not translate into a qualifying after-cost trading edge. The momentum rule was positive at base cost in all three fold tests, but lost money under stress in fold 3 and had a 6.18% drawdown in fold 1; it also fails the full robustness gate. No strategy is approved.

## Conclusion and next gate

1. The frozen XAUUSD checkpoint's validation edge was weak and did not survive the final test after costs. Its directional class behavior drifted toward excessive SHORT predictions as the later sample became quieter and more NO-TRADE-heavy.
2. The genuinely fold-trained experiment found no validation window that met the predeclared trade-count, return, profit-factor, and drawdown requirements. Fail-closed zero-trade outcomes are the correct result, not a reason to lower thresholds.
3. The earlier PR #215 checkpoint-evaluation report contains XAUUSD trading figures that conflict with the archived checkpoint's own metrics and the corrected evaluator. Reconcile and regenerate that report before treating it as the canonical result.
4. Do not tune against the final test, relax the confidence gate to force trades, promote a checkpoint, or enable Kitty live signals. Any further research should first standardize the simulator and then test label/calibration improvements on new chronological folds.

No production checkpoint or Kitty code was changed. No Railway or Vercel configuration was changed. No broker connection or order was used. Live trading remains disabled.
