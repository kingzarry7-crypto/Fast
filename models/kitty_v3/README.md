# Kitty V3 BTC — isolated model artifacts

This folder is the intended home for the 18-feature, three-class Kitty V3 BTC model.
The uploaded artifacts currently live at the repository root on this branch so the
inference loader in `kitty_v3_multiclass.py` can validate them without altering the
legacy six-feature `kitty_v3.py` model. Move the files together only in a later
change that updates the loader paths and verifies the actual binary files.

## Artifact contract

- `kitty_v3_state_dict.pt`: PyTorch state dict for 18 → 64 → 32 → 3.
- `scaler_v3.joblib`: fitted StandardScaler with exactly 18 input features.
- `metadata.json`: feature order, class mapping, expected tensor shapes, and audit gates.

Feature order and class mapping are in `metadata.json`. Class indices are 0=SHORT,
1=NO_TRADE, 2=LONG. The intended horizon is six hours and the move threshold is 0.30%.

## Current safety gates

The metadata currently records `target_execution_alignment_verified=false` and
`split_boundary_audit_passed=false`. The loader deliberately refuses predictions
until both are verified using the training notebook/data and documented audit output.
Do not flip these flags just to enable predictions.

This is paper/research-only. It never submits orders. Do not enable live trading or
merge an integration until the model, scaler, target timing, purge gap, and tests pass.
