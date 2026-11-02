# Kitty 15-Minute Multi-Timeframe Telegram Watch Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Schedule Kitty's BTC and XAU/USD Telegram watcher every 15 minutes, anchor setup decisions to completed 15M candles, incorporate all agreed supported timeframes, and send only fully validated BUY/SELL alerts.

**Architecture:** Keep Telegram scheduling/delivery in `bot.py`, shared timeframe analysis in `market.py`, and signal/risk normalization in `kitty_alerts.py`. Preserve the hourly feature contract of existing Kitty BTC and Gold models and their production-readiness/validated-edge gates; do not convert technical candidates into trades.

**Tech Stack:** Python 3.12, python-telegram-bot JobQueue/APScheduler, shared market snapshot provider, SQLite delivery deduplication, unittest/pytest test suite.

## Global Constraints

- Work on `feat/kitty-15m-multitimeframe-telegram-watch`, based on main SHA `5345ca5d59cf346c923590acd815422d706a1312`.
- Keep live order execution disabled; this feature is alert-only.
- Do not relax confidence thresholds, production readiness, strategy-edge validation, candle freshness, or risk-level checks.
- Telegram messages are limited to authorized existing admin recipients.
- Telegram sends only BUY or SELL. NO TRADE, WAIT, missing data, stale data, conflicting timeframes and failed gates are silent.
- Polling every 15 minutes does not promise a signal every 15 minutes.
- Do not change Vercel or unrelated ZARRY services.
- Preserve the trained BTC/Gold models' hourly feature input contract. A 15M candle is the setup/alert anchor, not hourly model input.
- Tests must demonstrate red before production implementation, then green on the identical focused command.

---

### Task 1: Add deterministic watcher scheduling and single-flight protection

**Files:**
- Modify: `bot.py`
- Create: `tests/test_kitty_watch_scheduler.py`

**Interfaces:**
- Existing configuration: `KITTY_TELEGRAM_WATCH`, `KITTY_TELEGRAM_INTERVAL_SEC`.
- Existing scheduled entry point: `kitty_telegram_signal_job(context, force=False)`.
- Proposed pure helper: `kitty_watch_interval_seconds(raw_value)` returning an integer no lower than 900.
- Proposed module-level single-flight lock/guard used by `kitty_telegram_signal_job`.

- [ ] **Step 1: Add focused failing tests**

Test the actual interval helper and scheduler configuration for default 900 seconds, explicit values above 900, and configured values below 900 clamped to 900. Test that concurrent invocations of the scheduled job cannot run two scans simultaneously and that the lock is released after an exception.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_kitty_watch_scheduler.py`

Expected: import/attribute or assertion failures because the 900-second helper and single-flight guard do not yet exist.

- [ ] **Step 3: Implement the minimum behaviour**

Replace the current two-hour minimum/default with a 900-second minimum/default. Use the helper when configuring the JobQueue. Add a single-flight guard around the scan; if a run is already active, log a skip and return without starting another scan. Ensure release occurs in a `finally` path. Update scheduler and watcher log text to say 15-minute cadence rather than two-hour cadence. Do not alter other notification jobs.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_kitty_watch_scheduler.py`

Expected: all interval and concurrency tests pass.

- [ ] **Step 5: Run affected integration checks**

Run: `python -m pytest -q tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py tests/test_kitty_watch_scheduler.py`

Expected: existing signal safety and alert tests remain green alongside the new scheduling tests.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add bot.py tests/test_kitty_watch_scheduler.py
git commit -m "feat: schedule Kitty Telegram watch every 15 minutes"
```

### Task 2: Expose and validate the agreed timeframe set in the shared market snapshot

**Files:**
- Modify: `market.py`
- Create: `tests/test_market_mtf_timeframes.py`

**Interfaces:**
- Existing: `TIMEFRAME_MAP`, `get_market_snapshot(symbol, timeframe="15m")`, `_analyze_market_fresh`.
- Existing snapshot fields: `mtf_timeframes`, `timeframe_alignment`, `signal`, `trend`, `candles`.
- Required watch set: `5m, 15m, 30m, 1h, 2h, 4h, 1d`.

- [ ] **Step 1: Add focused failing tests**

Using deterministic mocked market-provider candle responses, assert that the 15M snapshot contains analysis for each supported watch timeframe; each timeframe analysis identifies its own interval and uses its matching candle series. Assert missing, malformed, or stale required timeframe data is represented as unavailable/invalid and cannot be treated as directional agreement. Assert that a valid 15M snapshot still identifies 15M as primary.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_market_mtf_timeframes.py`

Expected: failures showing the current snapshot exposes only 4H/1H/15M/5M and does not include all requested timeframe analyses.

- [ ] **Step 3: Implement the minimum behaviour**

Extend the existing shared market analysis to obtain and analyze 5M, 15M, 30M, 1H, 2H, 4H and 1D using the existing `TIMEFRAME_MAP` and provider interface. Keep 15M primary. Reuse existing indicator and candle validation functions; do not fabricate missing timeframe data or substitute one timeframe's candles for another. Carry explicit success/freshness information per timeframe so the watcher can fail closed. Avoid increasing unrelated provider polling or introducing a separate high-frequency per-symbol request loop outside the scheduled watcher.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_market_mtf_timeframes.py`

Expected: all seven timeframe, interval identity, primary-timeframe and unavailable-data assertions pass.

- [ ] **Step 5: Run affected integration checks**

Run: `python -m pytest -q tests/test_market_mtf_timeframes.py tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py`

Expected: shared market changes preserve existing MTF and safety contracts.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add market.py tests/test_market_mtf_timeframes.py
git commit -m "feat: expose complete Kitty watch timeframes"
```

### Task 3: Anchor alert decisions to completed 15M setups while preserving Kitty model eligibility

**Files:**
- Modify: `bot.py`
- Modify: `kitty_alerts.py`
- Modify: `tests/test_kitty_alerts.py`
- Modify: `tests/test_kitty_signal_safety.py`

**Interfaces:**
- Existing watcher: `kitty_telegram_signal_job(context, force=False)`.
- Existing MTF analysis: `analyze_multi_timeframe(symbol)`.
- Existing signal gate: `normalize_kitty_mtf_signal(prediction, mtf, late)`.
- Existing risk gate: `validate_mtf_watch_levels(mtf, signal)`.
- Existing delivery persistence: `ensure_delivery_table`, `is_delivered`, `mark_delivered`, `all_recipients_delivered`.
- Existing model inference: `_kitty_features(closed_hourly_candles)`, `btc_model.predict_features`, `gold_model.predict_features`.

- [ ] **Step 1: Add focused failing tests**

Add tests proving:
  - Only a completed, fresh 15M setup candle can anchor a watch decision.
  - Hourly model inference continues to receive completed hourly candles and never receives 15M candles as hourly features.
  - Each required timeframe is present, valid, fresh and directionally aligned before a BUY/SELL alert is permitted.
  - Missing or stale timeframe data, neutral/conflicting timeframes, model inference errors, research-only models, unvalidated strategy edge, invalid entry/SL/TP levels, or non-actionable signal suppress Telegram delivery.
  - WAIT and NO TRADE never call Telegram send.
  - A valid BUY or SELL calls send only for existing authorized admins.
  - The same asset + completed 15M candle + recipient is delivered once; successful recipients are not repeated and failed recipients can be retried.
  - The existing force path used by explicit manual diagnostics does not bypass model, freshness, alignment or risk safety gates.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py`

Expected: the new 15M anchor/timeframe coverage tests fail against the current hourly-candle dedupe key and four-timeframe confirmation map, while existing safety tests remain green.

- [ ] **Step 3: Implement the minimum behaviour**

Keep hourly model inference unchanged and validate its hourly candle input as hourly. Separately obtain the completed 15M candle timestamp for the alert cycle and use that timestamp in delivery deduplication. Use the expanded shared MTF snapshot as the setup/confirmation input. Require explicit validity/freshness for every agreed timeframe; do not treat unavailable data as agreement. Preserve the existing model production-ready and signal-edge-validated checks in `normalize_kitty_mtf_signal`. Require risk levels to pass before formatting. Retain the existing per-recipient delivery table and retry semantics. Ensure the only Telegram send path is final BUY/SELL after all gates. No NO TRADE or WAIT messages are emitted.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py`

Expected: all new and existing safety, signal normalization, candle anchoring and delivery tests pass.

- [ ] **Step 5: Run affected integration checks**

Run: `python -m pytest -q tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py tests/test_kitty_watch_scheduler.py tests/test_market_mtf_timeframes.py`

Expected: all watcher, market and signal safety tests pass together.

- [ ] **Step 6: Commit the passing deliverable**

```bash
git add bot.py kitty_alerts.py tests/test_kitty_alerts.py tests/test_kitty_signal_safety.py
git commit -m "feat: gate Kitty alerts on completed 15-minute setups"
```

### Task 4: Full regression, CI and deployment readiness

**Files:**
- Review all changed files from Tasks 1–3.
- No unrelated source changes.

**Interfaces:**
- Runtime schedule: `king-zarry-kitty-v3-telegram-alerts`.
- Production health check: existing Railway Fast service health endpoint.
- Deployment remains separate from code merge approval.

- [ ] **Step 1: Run complete relevant test suite**

Run: `python -m pytest -q`

Expected: all repository tests pass; any unrelated pre-existing failures are recorded distinctly and not hidden.

- [ ] **Step 2: Run repository CI checks**

Run the repository's configured safety, security and workflow-engine checks through GitHub Actions.

Expected: all required checks pass on the feature branch/PR.

- [ ] **Step 3: Review diff and safety invariants**

Confirm no model thresholds or production-readiness gates were weakened, no broker order placement was added, no live-trading flag was enabled, no secrets were committed, and Vercel was untouched.

- [ ] **Step 4: Prepare PR**

Open a PR from `feat/kitty-15m-multitimeframe-telegram-watch` to `main), including test red/green evidence, CI results and explicit note that no validated production model means no Telegram directional alert.

- [ ] **Step 5: Stop before deployment**

Do not merge or deploy Railway until the PR is reviewed/merged and deployment is separately authorized. After authorization, deploy and verify the runtime scheduler logs report a 900-second interval and the watcher remains silent for non-actionable conditions.

## Unresolved implementation decisions

- The user-approved timeframe set is fixed. The existing hourly model input contract is also fixed. Whether a future independently validated 15M-trained model should replace hourly inference is outside this plan and requires separate evidence and approval.
- The 15M anchor timestamp and hourly model timestamp must both be fresh and mutually consistent; the implementation should fail closed when their relationship cannot be established from provider timestamps.
