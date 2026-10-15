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
