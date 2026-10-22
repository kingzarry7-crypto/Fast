# Kitty V3 — Paper-Trading Review

Upload the following artifacts from the Colab export into this folder:

- `kitty_v3_state_dict.pt`
- `scaler_v3.joblib`
- `metadata.json`

Do not merge this pull request yet. This model is for inspection and paper-trading only. Keep live trading disabled and do not add API keys, account credentials, or other secrets.

Before integration, verify the model architecture, feature order, scaler compatibility, target/execution alignment, and chronological split boundaries. Do not load `scaler_v3.joblib` from an untrusted source without reviewing it first.