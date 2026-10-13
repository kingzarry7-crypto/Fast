# King Zarry AI — Vantage MT5 Windows bridge

## Scope and safety

This release is signal-monitoring only. It has no order-submission function and cannot place orders. It rejects accounts whose MT5 trade mode is not explicitly ACCOUNT_TRADE_MODE_DEMO, and the local control server binds to loopback (127.0.0.1) only. A restart returns the bridge to STOPPED unless an emergency stop was active, in which case the emergency stop remains active.

Kitty's current checkpoint is BTC-trained. Its feature engineering and target horizon have not been proven to match the original training pipeline for gold or forex. Predictions are experimental monitoring output only and must not be used to place orders.

## Requirements

- Windows computer with Vantage MetaTrader 5 installed and logged into your Vantage demo account.
- Python 3.12 (64-bit) matching the installed MetaTrader 5 terminal.
- Repository checkout including kitty_v3_retrained_checkpoint.pt.
- Install dependencies: pip install MetaTrader5 numpy torch scikit-learn.
- The Vantage account's exact MT5 server name and trading account number. Never commit the password or put it in chat.

## Configure in Windows PowerShell

Run these in a private PowerShell session; replace the example values with your own local values. These are process-level environment variables, not source-code edits:

```powershell
$env:KZ_MT5_LOGIN = "YOUR_DEMO_ACCOUNT_NUMBER"
$env:KZ_MT5_PASSWORD = "YOUR_DEMO_TRADING_PASSWORD"
$env:KZ_MT5_SERVER = "YOUR_EXACT_VANTAGE_DEMO_SERVER"
$env:KZ_MT5_PATH = "C:\Program Files\Vantage MetaTrader 5\terminal64.exe"
$env:KITTY_V3_SIGNAL_MONITORING_ENABLED = "true"
$env:KZ_MT5_POLL_SECONDS = "60"
python vantage_mt5_bridge.py
```

KZ_MT5_PATH is optional if MT5 is discoverable automatically. Do not store credentials in a .py file or commit a .env file.

If Vantage uses suffixes such as XAUUSD.a, the bridge only auto-resolves a symbol when the match is unique. If it reports ambiguity, configure exact names locally:

```powershell
$env:KZ_MT5_SYMBOL_XAUUSD = "EXACT_SYMBOL_FROM_MARKET_WATCH"
$env:KZ_MT5_SYMBOL_EURUSD = "EXACT_SYMBOL_FROM_MARKET_WATCH"
$env:KZ_MT5_SYMBOL_GBPUSD = "EXACT_SYMBOL_FROM_MARKET_WATCH"
$env:KZ_MT5_SYMBOL_USDJPY = "EXACT_SYMBOL_FROM_MARKET_WATCH"
```

Set only the aliases that are needed. The bridge refuses to continue if any approved symbol cannot be resolved unambiguously.

## Local controls

Open http://127.0.0.1:8765/ on the same computer.

- Start monitoring — reads completed H1 bars and records Kitty's monitor-only predictions.
- Pause — stops new monitoring cycles.
- Emergency stop — persistently blocks monitoring until you explicitly confirm resume.
- Confirm resume — clears emergency stop only after a browser confirmation.
- Refresh status — shows mode, allowlisted markets, and order_submission_available: false.
- /audit shows recent local audit events.

The control server must remain bound to localhost. Do not expose port 8765 to your LAN or the public internet.

## Important model limitation

The provisional H1 feature calculations in vantage_mt5_bridge.py are experimental because the original training feature-generation source has not been found and verified. The model was trained on BTC, not validated on XAU/USD, EUR/USD, GBP/USD, or USD/JPY. This bridge logs predictions for analysis only; no order API is implemented. Before any future demo-order implementation, first confirm exact training feature formulas, label horizon, broker contract sizes, stops/targets, sizing and risk limits, then test in a separate change.

## Tests

Run from the repository root:

```powershell
python -m unittest tests.test_vantage_mt5_bridge -v
python -m unittest tests.test_kitty_v3_retrained -v
```
