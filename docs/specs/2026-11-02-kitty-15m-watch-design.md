# Kitty 15-Minute Multi-Timeframe Telegram Watch — Design

**Date:** 2026-11-02  
**Repository:** `kingzarry7-crypto/Fast`  
**Base:** `main` at `5345ca5d59cf346c923590acd815422d706a1312`

## Goal

Make Kitty evaluate BTC and XAU/USD on a 15-minute setup cadence, use all agreed supported timeframes as context, and send Telegram BUY/SELL alerts only when the existing production-safety gates approve a complete actionable setup.

## Current repository findings

- `bot.py` schedules `kitty_telegram_signal_job` with `KITTY_TELEGRAM_INTERVAL_SEC`, currently clamped to a minimum of 7,200 seconds (two hours).
- The scheduled job currently fetches 160 hourly candles for the Kitty model, then calls `analyze_multi_timeframe`, validates risk levels, suppresses non-BUY/SELL results, and persists per-recipient delivery deduplication.
- The job's current log messages describe a two-hour watch.
- `analyze_multi_timeframe` in `bot.py` calls `market.get_market_snapshot(symbol, "15m")`; its returned MTF map currently exposes 4H, 1H, 15M and 5M.
- `market.py` defines timeframe aliases for 5M, 15M, 30M, 1H, 2H, 4H and 1D, but its current MTF weighting is 4H/1H/15M/5M.
- Existing Kitty model and signal gates intentionally reject research-only or unvalidated model candidates. This design preserves those gates; it does not make a candidate production-ready.

## Approved behaviour

1. Run the Telegram Kitty watch every 900 seconds (15 minutes), with a configurable interval whose effective value cannot be less than 900 seconds.
2. Treat the latest completed 15M candle as the setup/decision anchor. Do not use an in-progress 15M candle to create an alert.
3. Evaluate 5M for entry timing; 30M, 1H, 2H, 4H and 1D for directional context; and 15M for the setup. Include a timeframe only when its market data is available, valid and fresh. Missing or stale required context must fail closed rather than be silently treated as agreement.
4. Preserve the Kitty model's existing model-readiness and validated-edge requirements. A technical candidate, research-only prediction, or AI confirmation must not independently authorize BUY/SELL.
5. Send Telegram messages to the existing authorized recipients only when the final signal is BUY or SELL and all model, timeframe, candle-freshness, risk-level and deduplication checks pass.
6. Do not send Telegram messages for NO TRADE, WAIT, unavailable data, model errors, conflicting timeframes, invalid risk levels or unvalidated candidates. Internal diagnostic logs are allowed.
7. Deduplicate by asset, completed 15M candle identity and recipient so polling/restarts do not repeat the same alert. Retry only recipients whose delivery failed, following the existing delivery-state pattern.
8. Keep this watcher alert-only. Do not place orders, change account mode, enable live trading, loosen model gates, or generate a signal merely to meet the 15-minute cadence.

## Architecture and boundaries

- `bot.py` remains the Telegram scheduling and delivery boundary. It owns the 900-second scheduler configuration, completed-candle anchor, per-recipient delivery, and BUY/SELL-only Telegram output.
- `market.py` remains the shared market-analysis boundary. Extend its MTF snapshot only as needed to expose the agreed timeframes using the existing timeframe map and freshness/data validation conventions.
- `kitty_alerts.py` remains the signal-normalization and risk-level gate boundary. Extend its tests/contracts only where the expanded timeframe set requires it; preserve fail-closed behaviour.
- Existing Kitty BTC and Gold model modules remain authoritative for production model eligibility. No model retraining, threshold relaxation, or profitability claim is part of this change.

## Failure and safety behaviour

- A failed or malformed timeframe fetch, stale candle, missing completed 15M candle, model inference exception, unvalidated model, conflicting timeframe, invalid entry/stop/target levels, or duplicate delivery results in no Telegram alert.
- A failed recipient send must not be marked delivered; successful recipients must not receive the same candle alert again.
- Scheduler overlap must not cause concurrent duplicate scans. Use a single-flight guard or an equivalent existing scheduler-safe mechanism if the current job can overlap.
- The configured polling interval controls scan frequency; it does not promise a trade every 15 minutes.

## Acceptance criteria

- The watcher is scheduled at 900 seconds by default and cannot be configured below 900 seconds.
- Tests prove that the 15M setup candle is completed and fresh before signal evaluation.
- Tests prove the supported timeframe set is evaluated and missing/stale required data suppresses alerts.
- Tests prove only a fully validated BUY or SELL reaches Telegram; WAIT/NO TRADE and model candidates never do.
- Tests prove same-candle recipient deduplication and safe retry after failed delivery.
- Tests prove no overlapping scan can create duplicate deliveries.
- Live order execution remains disabled and untouched.
- Relevant Kitty, Telegram and market tests pass; CI passes before any merge or deployment.

## Explicit non-goals

- Making Kitty profitable or claiming that it is profitable.
- Lowering model confidence thresholds or bypassing strategy-edge validation.
- Sending periodic WAIT/NO TRADE status messages.
- Automatic trade execution, broker integration changes, or live-account activation.
- Changes to Vercel or unrelated ZARRY services.

## Implementation sequence

1. Add focused failing tests for 900-second scheduling configuration, timeframe coverage, completed 15M anchoring, silent non-actionable outcomes, deduplication/retry, and single-flight execution.
2. Extend shared market MTF analysis to expose 5M/15M/30M/1H/2H/4H/1D data with explicit freshness and missing-data outcomes.
3. Update the Telegram watcher to evaluate each completed 15M setup cycle, preserve Kitty production gates, and send only validated BUY/SELL alerts.
4. Run focused tests, the complete relevant Python test suite, and CI. Merge/deploy only after successful verification and a separate go-ahead for deployment.

## Open implementation detail

The current Kitty BTC/Gold predictors consume hourly features. The implementation must preserve that trained-model input contract unless repository evidence establishes an already validated 15M model. The 15M candle is the alert/setup anchor; it must not be passed into an hourly model as though it were hourly training data.
