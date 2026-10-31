> **SUPERSEDED XAUUSD FIGURES — 2026-10-31:** The XAUUSD trading metrics in this historical report do not reproduce from the archived checkpoint under the corrected repository evaluator. The reproduced values are validation **32 trades / +1.19% base / +0.38% at 1.5× costs** and untouched test **26 trades / +0.35% base / -0.30% at 1.5× costs**, PF **1.070**. Keep the original figures below only as an audit record; do not use them as canonical results. See [the corrected XAUUSD shared-execution and calibrated walk-forward report](zarry-task2-xau-calibrated-walkforward-run-001.md) for the canonical reproduction, regime analysis, and disjoint-fold results.

# ZARRY Task 2 — Frozen Kitty Checkpoint Evaluation

**Run:** `zarry-task2-kitty-evaluation-run-001`  
**Date:** 2026-10-31  
**Status:** Research-only; no promotion, retraining, deployment, or trading authorization.

## Method and integrity

- Used only the archived run-106 BTCUSD and XAUUSD CSVs and their selected Kitty checkpoint bundles; no new market data was fetched.
- Rechecked CSV SHA-256 against each checkpoint's `dataset_sha256`; both matched. Checkpoint SHA-256 values also match the Task 1 manifest.
- Both checkpoints have the expected 18-feature order, `[18, 64, 32, 3]` MLP architecture, scaler width 18, and class mapping `0=SHORT`, `1=NO TRADE`, `2=LONG`.
- Both are explicitly `research_only=true`, `production_ready=false`, and `automatic_order_execution_enabled=false`.
- Reused the exact archived split: seven purged rows before each boundary; BTC train/validation/test = 3,414/726/734; XAUUSD = 3,453/734/742.
- Applied the checkpoint's already-frozen `recommended_min_confidence` (BTC 1.01 fail-closed; XAUUSD 0.50) and Kitty inference's 0.10 minimum top-two probability margin. No threshold was tuned on the final test.
- Trading proxy: class 1 abstains; directional classes trade only after the frozen confidence/margin gate; decision at t, entry next open, exit at close of t+7; one trade at a time; same base costs as the baseline protocol and 1.5× stress costs. These are forward-price proxies, not broker fills or realized paper trades.

### Artifact hashes

| Asset | CSV SHA-256 | Selected checkpoint SHA-256 |
|---|---|---|
| BTCUSD | `c4c017a7a32ed98c3a336e92c33e51bd9a489fe403e003a89bee6623a58674d5` | `926c34af3b06127bb87d67446914501d6faa386101ce47007e04b52a68a3cee3` |
| XAUUSD | `09dc53065c2026178b50046398b93cdb441568bacf681c7f9f429b0fde7d6a9c` | `5da5b2130a793ee315fa6ce2ed8e34e2b5e5b689f45a81c677a280d26f0a69f6` |

## Final-test results

Classification below is the raw model argmax before the confidence gate. Trading results use the frozen confidence/margin gate.

| Asset | Accuracy | Balanced accuracy | Macro-F1 | Frozen min confidence | Trades | Win rate | Net expectancy/trade | Profit factor | Net return | 1.5× cost return | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 39.51% | 37.86% | 36.32% | 1.01 (disabled) | 0 | — | 0.00% | — | 0.00% | 0.00% | 0.00% |
| XAUUSD | 50.81% | 48.37% | 48.35% | 0.50 | 25 | 44.00% | +0.0197% | 1.093 | +0.46% | -0.17% | 1.53% |

### Comparison against the fixed baselines on the same final test

| Asset | Strategy | Trades | Net return | 1.5× cost return | Profit factor | Max drawdown |
|---|---|---:|---:|---:|---:|---:|
| BTCUSD | Kitty checkpoint (confidence-gated) | 0 | 0.00% | 0.00% | — | 0.00% |
| BTCUSD | Momentum baseline | 88 | -19.43% | -22.91% | 0.466 | 19.56% |
| BTCUSD | Trend confirmation baseline | 71 | -20.12% | -22.92% | 0.399 | 20.94% |
| XAUUSD | Kitty checkpoint (confidence-gated) | 25 | +0.46% | -0.17% | 1.093 | 1.53% |
| XAUUSD | Momentum baseline | 74 | +3.33% | +1.43% | 1.271 | 3.52% |
| XAUUSD | Trend confirmation baseline | 63 | -5.00% | -6.48% | 0.670 | 7.82% |

## Findings

- **BTCUSD:** the checkpoint's frozen confidence threshold is 1.01, an explicit no-signal sentinel. It produced zero directional trades on validation and final test. The raw classifier's final-test macro-F1 is 36.32%, below a useful signal standard; the model is not a candidate for promotion. This is consistent with the archived selection decision, which found no validation threshold meeting its positive-edge requirements.
- **XAUUSD:** the checkpoint did produce a positive validation result under its frozen threshold (30 trades, +2.52% base cost, +1.75% at 1.5× cost), but the untouched final test fell to 25 trades, +0.46% base, -0.17% at 1.5×, PF 1.093. It is below the fixed XAU momentum baseline (+3.33% base, +1.43% stress, PF 1.271) and does not meet the minimum 50-trade / 1% net-return / PF 1.10 promotion checks.
- The XAUUSD model's confidence gate allowed 60 candidate rows before overlap suppression; 35 were skipped as overlapping, leaving 25 completed trades.
- **No Kitty checkpoint qualifies for promotion.** Keep Kitty's current deterministic risk/signal workflow authoritative and keep ZARRY research-only.

## Walk-forward limitation

The frozen checkpoints were trained on the full 70% training partition and their confidence thresholds were selected on the subsequent validation partition. Applying those same checkpoint weights to the earlier expanding-window walk-forward test folds would leak future training information into those earlier periods. Therefore this run does **not** report Kitty walk-forward scores. A valid fold-by-fold Kitty walk-forward evaluation would require training a separate model inside each fold; that is intentionally not done in this frozen-checkpoint-only task.

## Runtime / reproducibility note

The checkpoint bundles contain scikit-learn `StandardScaler` objects serialized under scikit-learn 1.9.1, while this evaluation environment has 1.8.0 and emitted `InconsistentVersionWarning`. The scaler transform was independently checked against `(X - mean_) / scale_` for both checkpoints with maximum absolute difference 0.0. The warning remains a portability caveat; a future reproducibility environment should pin the training dependency versions.

## Safety and next gate

No model was trained or modified. No Kitty production files, Railway service, Vercel project, broker, or trading permissions were changed. No live or demo orders were placed. No signals are authorized from this report.

The next useful step is to diagnose the XAUUSD validation-to-test degradation and improve the research protocol (including a genuinely fold-trained walk-forward comparison) before considering any new candidate. Do not tune against this final test or enable trading.
