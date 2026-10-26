# Kitty V3 retraining experiments

This script adds a controlled experiment path for the 18-feature, three-class Kitty V3 model. It **does not overwrite** `kitty_v3_retrained_checkpoint.pt`, enable inference, or place orders.

## Run locally

Install the project's ML dependencies (PyTorch, pandas, NumPy, scikit-learn), then run:

```bash
python train_kitty_v3_retrained.py --csv path/to/historical_features.csv
```

The CSV must contain the exact 18 feature columns listed in the script plus a `target` column. Target values may be `SHORT`, `NO TRADE`, `LONG` or `0`, `1`, `2`. Optional `timestamp`, `datetime`, or `date` columns are sorted oldest-to-newest.

## What it compares

- Baseline MLP, batch-normalized MLP, and LeakyReLU MLP.
- AdamW and Adam optimizers.
- Dropout, weight decay, gradient clipping, class-weighted loss, validation-loss learning-rate scheduling, and early stopping.
- Chronological 70% train / 15% validation / 15% holdout test split.
- StandardScaler is fitted on the training partition only. The learning rate is reduced when validation loss plateaus.
- Candidate selection uses validation macro-F1, with validation log loss as a tie-breaker. The holdout test partition is evaluated only once, after selecting the candidate, to reduce test-set overfitting.

Artifacts are written to `kitty_v3_experiments/`: separate candidate checkpoints and `comparison_report.json`. The report includes accuracy, balanced accuracy, macro-F1, log loss, confusion matrix, and class-wise metrics. **Do not choose a model on accuracy alone.** Validate calibration, costs, slippage, drawdown and walk-forward/paper-trading performance.

## Safety and compatibility

These are research candidates, not production-ready checkpoints. The experimental batch-normalization and LeakyReLU variants have different state-dict layouts from the current production loader. Do not copy them over the production checkpoint. Integration requires an explicit model-config-aware loader and passing the existing inference tests plus separate realistic paper-trading validation.


## Automated historical retraining workflow

The GitHub Actions workflow `.github/workflows/kitty-retrain-research.yml` runs on relevant changes to the training pipeline, can be launched manually, and runs weekly. It downloads up to 5,000 completed hourly public candles per asset for BTC, ETH, SOL, and BNB, trying Binance first and falling back to Yahoo Finance if Binance blocks the hosted runner, creates the same 18 features used by Kitty inference, labels the return from the next hourly candle open to the close six hours after that entry, and trains separate candidates per asset.

- The target uses a realistic timing convention: signal after candle t closes, entry at candle t+1 open, exit at candle t+7 close. Because signals enter at the next candle open and exit at t+7 close, at least seven rows are purged at train/validation/test boundaries; a six-row purge leaves a one-candle label overlap.
- The candidate report includes a single untouched chronological holdout evaluation plus a diagnostic paper-return simulation that subtracts an assumed 0.10% round-trip fee/slippage cost. The simulator skips new signals through the prior trade's exit candle (signal at t, entry t+1 open, exit t+7 close; next eligible signal t+7).
- Experimental BatchNorm/LeakyReLU models are reported for research comparison, but only the baseline architecture is promotion-compatible with the current inference loader. Do not remove that compatibility gate without implementing and testing a model-config-aware production loader.
- The current runtime loader is BTC-only. ETH/SOL/BNB outputs are research candidates, not live model integrations.
- Gold and forex are intentionally not trained from crypto data. They need their own verified historical price source and separate evaluation.
- Artifacts are retained in GitHub Actions for 30 days. This workflow does **not** overwrite the production checkpoint or enable order execution. A candidate must be reviewed against existing baseline metrics and paper trading before promotion.


## Paper-trade outcome feedback

The BTC paper simulator now records every completed-candle prediction in its
SQLite ledger and settles the prediction only after the next candle open and
six-hour exit candle are available. It records the realized forward return,
the threshold-derived outcome label, whether the original signal matched that
label, and summary accuracy by signal. The API exposes the summary at
`GET /paper/feedback`; `GET /paper/status` also includes it.

This is evaluation feedback, not online learning: it does not modify model
weights, automatically retrain from recent outcomes, or promote a checkpoint.
Review a meaningful sample of settled outcomes and run a time-separated
retraining/holdout evaluation before considering any model update. Outcomes
are stored in the paper simulator's configured SQLite database, so durability
depends on the backend's persistent-volume configuration.



## Gold and forex research pipeline

`prepare_kitty_fx_market_dataset.py` uses Twelve Data hourly candles for XAU/USD,
EUR/USD, GBP/USD and USD/JPY, then applies the same 18-feature contract and
six-hour outcome definition as the crypto research builder. Add a repository
Actions secret named `TWELVEDATA_API_KEY` to train on the actual XAU/USD spot feed.
Without that secret, the no-key Yahoo fallback uses `GC=F` COMEX gold futures for
XAUUSD. That is a clearly labelled gold-futures proxy, **not XAU/USD spot**, and
its candidate must not be promoted to the live spot prediction path. The dataset
source is recorded in the candidate checkpoint/report. Provider plan limits or
unsupported symbols can still make a market job fail; no synthetic or crypto
candles are substituted for missing gold/FX data.

The target timing is signal after candle t closes, entry at candle t+1 open, and
exit at candle t+7 close. Samples whose hourly window crosses missing candles are
excluded so row gaps cannot silently change the holding period. The label builder
and paper feedback use the same entry/exit convention. Each gold/FX model is a
separate research candidate and must not be loaded into the BTC production inference
path. The holdout gate disables signals unless at least 10 trades have positive
average and compounded net returns after assumed costs.

## Scheduled learning and promotion controls

The weekly GitHub Actions workflow refreshes historical candles, reruns tests,
trains candidate checkpoints and emits validation/holdout reports. This is
automated research retraining, not online weight mutation. The paper ledger
settles actual forward outcomes for monitoring, but its Railway SQLite data is
not currently exported into GitHub Actions, so it is not directly used as
training rows. Production weights are not overwritten automatically: the
existing Kitty holdout/backtest results have not established an edge after costs.
Review candidate reports and paper outcomes before any explicit promotion.
