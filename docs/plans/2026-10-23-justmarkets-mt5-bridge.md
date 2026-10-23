# JustMarkets MT5 Bridge Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separately authenticated, shadow-first bridge between Fast/Kitty on Railway and a local MT5 Expert Advisor connected to a verified JustMarkets demo account, without enabling live trading.

**Architecture:** Add a dedicated FastAPI router and durable SQLite-backed signal/acknowledgement ledger, isolated from the Binance/OANDA connector. A local MQL5 Expert Advisor reports account and symbol capabilities, polls for work over HTTPS, validates demo identity and broker metadata, and initially reports decisions without submitting orders.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, unittest, MQL5 / MetaEditor, HTTPS WebRequest.

## Global Constraints

- Existing `trading_connector.py`, `kitty_demo_trader.py`, and `kitty_multi_paper.py` remain independent; no MT5 request may flow through Binance/OANDA order functions.
- Execution starts disabled and shadow-only. This plan does not enable live trading; live order support is out of scope.
- The account must be positively verified as demo using MT5 account trade mode, exact configured server identity, and an explicit account allowlist. If identity cannot be verified, reject all work.
- User-reported symbols are `BTC` and `XAUUSD`. Never silently map either to a guessed alias. Accept a symbol for a given session only after MT5 reports the exact name and tradable metadata.
- Keep the requested Kitty scan cadence at two hours; bridge polling and signal expiry are separate concerns, and stale signals must never execute.
- Never send broker passwords to Railway or log bearer tokens, shared secrets, or account credentials.
- Vercel must remain untouched. The EA runs on the user's Windows PC initially; Railway hosts only the backend API.
- Do not claim model profitability; bridge correctness and trading strategy profitability are separate validations.

---

### Task 1: Add isolated bridge domain, authenticated API, and durable idempotency ledger

**Files:**
- Create: `justmarkets_mt5_bridge.py`
- Create: `tests/test_justmarkets_mt5_bridge.py`
- Modify: `api.py` (router import/include only, following existing router registration conventions)

**Interfaces:**
- Router prefix: `/justmarkets-mt5`.
- `GET /status`: authenticated EA heartbeat/capability snapshot; returns bridge mode, last heartbeat timestamp, verified demo boolean, server identity match, and verified symbol metadata summary.
- `POST /heartbeat`: authenticated EA reports terminal connectivity, account trade mode, exact server string, configured account identity token/allowlist identifier, and per-symbol metadata.
- `GET /work`: authenticated EA polls for the next unexpired, unclaimed shadow signal; returns `{work: null}` when none exists.
- `POST /ack`: authenticated EA submits a result for a signal ID with status and structured reason/code.
- Signal records contain unique signal ID, exact symbol, direction (`BUY`, `SELL`, or `NO_TRADE`), source candle timestamp, creation timestamp, expiry timestamp, optional entry reference, stop-loss, and strategy/risk metadata.
- Authentication uses a dedicated environment secret such as `JUSTMARKETS_MT5_BRIDGE_TOKEN` over HTTPS with constant-time comparison. Missing server secret disables the router's operational endpoints (fail closed); do not reuse web-session auth or Binance credentials.

- [ ] **Step 1: Add focused failing tests**
  Test missing/invalid bearer token rejection; absent bridge secret means no authenticated operation; status and heartbeat reject non-demo account mode; exact server mismatch fails closed; duplicate signal ID is idempotent; expired signal is never returned; `NO_TRADE` never becomes actionable; unknown symbol metadata is not marked verified; acknowledgement for unknown IDs is rejected; secrets do not appear in responses/log output.

- [ ] **Step 2: Verify relevant failures**
  Run: `python -m unittest tests.test_justmarkets_mt5_bridge -v`
  Expected: tests fail because the bridge module and routes do not yet exist.

- [ ] **Step 3: Implement minimum backend behavior**
  Create a focused module with Pydantic request models, token dependency, UTC timestamp parsing, a SQLite schema for latest terminal heartbeat, verified symbol metadata, queued signals, and acknowledgements. Use parameterized SQL and a uniqueness constraint on signal IDs. Require explicit demo trade mode and exact server/account allowlist configuration before setting `demo_verified=true`. Reject expired/duplicate/replayed requests. Keep signal creation internal to a small service function so later Kitty integration does not couple directly to HTTP handlers. Do not implement an order-submit endpoint in this task.

- [ ] **Step 4: Verify focused pass**
  Run: `python -m unittest tests.test_justmarkets_mt5_bridge -v`
  Expected: all bridge API/domain tests pass, including fail-closed identity and idempotency cases.

- [ ] **Step 5: Run integration checks**
  Run: `python -m unittest discover -s tests -v`
  Expected: all existing tests and new bridge tests pass; imports of existing trading modules remain unchanged.

- [ ] **Step 6: Commit the passing deliverable**
  `git add justmarkets_mt5_bridge.py tests/test_justmarkets_mt5_bridge.py api.py`
  `git commit -m "feat: add isolated JustMarkets MT5 bridge API"`

### Task 2: Implement the local MT5 Expert Advisor in shadow-only mode

**Files:**
- Create: `mt5/JustMarketsKittyBridge.mq5`
- Create: `docs/KITTY_JUSTMARKETS_MT5_SETUP.md`
- Test: manual MetaEditor compile and demo-terminal checklist documented in `docs/KITTY_JUSTMARKETS_MT5_SETUP.md`

**Interfaces:**
- Uses the backend's `/heartbeat`, `/work`, and `/ack` HTTPS endpoints.
- Inputs: backend base URL, bridge token, expected exact server string, approved account identifier, and local execution mode defaulting to `SHADOW_ONLY`.
- Reports `ACCOUNT_TRADE_MODE`, server identity, connection status, and symbol properties for exact configured `BTC` and `XAUUSD` names. Do not transmit the account password.
- Uses MT5 `WebRequest`; setup instructions must tell the user to add only the exact HTTPS backend origin to MT5's allowed URLs.

- [ ] **Step 1: Add a testable manual acceptance checklist first**
  Document expected shadow behavior, compile checks, demo account identity verification, symbol metadata display, backend disconnection, and no-order proof.

- [ ] **Step 2: Record baseline compile/setup failure**
  Run the documented MetaEditor compile against the not-yet-created EA.
  Expected: compile cannot proceed because the EA file does not exist yet; record that as the baseline, not as a product test failure.

- [ ] **Step 3: Implement shadow-only EA**
  On initialization, refuse to operate if token/URL/server/account configuration is empty. Verify demo trade mode and exact server/account allowlist before publishing trusted status. Report exact symbol metadata (trade mode, volume min/max/step, tick size/value, digits, stops level). Poll with bounded interval and HTTP timeouts. Validate signal ID, symbol, direction, timestamps and expiry locally; acknowledge accepted/rejected/shadow-evaluated work. The EA must contain no order-submission call in this task.

- [ ] **Step 4: Verify compile and local behavior**
  Run: compile `mt5/JustMarketsKittyBridge.mq5` in MetaEditor.
  Expected: zero errors and no warnings indicating unsafe or deprecated API use. Attach it to a demo chart and verify heartbeat, identity, and symbol metadata are visible.

- [ ] **Step 5: Run backend integration checks**
  Run: `python -m unittest discover -s tests -v`
  Expected: backend contract tests pass. Manual terminal test confirms wrong server, non-demo account, disconnected terminal, missing symbol, expired signal, and invalid auth are rejected without any order attempt.

- [ ] **Step 6: Commit the passing deliverable**
  `git add mt5/JustMarketsKittyBridge.mq5 docs/KITTY_JUSTMARKETS_MT5_SETUP.md`
  `git commit -m "feat: add shadow-only MT5 Expert Advisor"`

### Task 3: Connect Kitty signals to the shadow bridge and verify safe end-to-end behavior

**Files:**
- Modify: `kitty_multi_paper.py` (call a bridge-neutral signal publication service only after a completed candle is evaluated; paper ledger behavior stays unchanged)
- Modify: `justmarkets_mt5_bridge.py` (signal publication and risk/freshness policy)
- Modify: `tests/test_justmarkets_mt5_bridge.py`
- Modify: `docs/KITTY_JUSTMARKETS_MT5_SETUP.md`

**Interfaces:**
- Internal function: `publish_shadow_signal(signal: dict) -> dict`, returning signal ID, publication status, and rejection reason if rejected.
- A completed-candle signal is translated only into a shadow record; `NO_TRADE` is recorded as informational and never returned as executable work.
- No call to `trading_connector.place_market_order`, `place_kitty_demo_order`, or any live/demo broker order function is permitted from the bridge path.

- [ ] **Step 1: Add focused failing tests**
  Verify signals from unfinished candles are not published; expired candles/signals are rejected; repeated signal/candle IDs create one record; NO TRADE remains informational; unverified account or symbol blocks actionable work; bridge unavailable does not break the existing paper simulator; signal cadence configuration remains two hours where the existing watcher is configured.

- [ ] **Step 2: Verify relevant failures**
  Run: `python -m unittest tests.test_justmarkets_mt5_bridge -v`
  Expected: new publication and isolation tests fail until the signal publisher is wired.

- [ ] **Step 3: Implement minimum shadow publication**
  Keep existing paper ledger and strategy calculations intact. Publish only completed-candle outputs to the bridge's isolated service, with source candle time, timeframe, generated-at time, expiry, direction, and stop-loss if available. If required stop-loss data is missing, record a rejected/non-actionable signal rather than synthesizing a value. A bridge persistence or network failure must not cause paper simulation to crash or imply successful publication; return and log a distinct degraded status.

- [ ] **Step 4: Verify focused pass**
  Run: `python -m unittest tests.test_justmarkets_mt5_bridge -v`
  Expected: signal freshness, deduplication, NO TRADE, and paper-isolation tests pass.

- [ ] **Step 5: Run full relevant suite**
  Run: `python -m unittest discover -s tests -v`
  Expected: all tests pass; existing Binance demo safeguards and paper simulation behavior remain intact. Review the diff to confirm no changes to Vercel config and no broker order submission path was added.

- [ ] **Step 6: Commit the passing deliverable**
  `git add justmarkets_mt5_bridge.py kitty_multi_paper.py tests/test_justmarkets_mt5_bridge.py docs/KITTY_JUSTMARKETS_MT5_SETUP.md`
  `git commit -m "feat: publish Kitty signals to MT5 shadow bridge"`

## Verification and release gate

- Before considering the bridge ready, verify CI and the full Python test suite on the exact commit intended for `main`.
- Deploy backend only after bridge tests pass; confirm the bridge token is configured as a Railway secret and not committed to the repository. If the secret is absent, endpoints remain fail-closed.
- Verify the local EA compile and shadow heartbeat from the user's connected demo terminal. Backend health alone does not prove MT5 connectivity.
- Stage B demo-order support is deliberately not implemented in these tasks. After shadow operation is reviewed, prepare a separate design/approval for a controlled demo order path with broker-confirmed stop-loss protection, risk caps, and emergency handling. Live trading remains out of scope.

## Unresolved product decisions

1. **Account allowlist identifier:** select which non-secret MT5 account identifier should be allowlisted. The implementation must not guess an account number; configuration remains disabled until it is supplied locally and stored as a secret/config value.
2. **Demo order phase:** whether to design a separate Stage B controlled demo-order implementation after Stage A shadow acceptance. No order path is part of this plan.
3. **Signal expiry duration:** recommend expiry at the earlier of the next completed candle boundary or two hours after signal creation, but confirm before making it a fixed public contract. Until decided, implement the expiry field as required input and reject signals after the supplied expiry rather than hard-coding a duration.
