# Internal Paper Auto-Trading — Design

**Date:** 2026-10-13  
**Status:** Proposed for user review  
**Scope:** Internal simulator only; no broker execution.

## Goals
- Add an opt-in automated loop that evaluates existing King Zarry AI Agent signals and Risk Guardian decisions and can create simulated orders in the internal paper account.
- Enforce paper-only execution in code, not just through environment defaults.
- Keep the retrained Kitty V3 checkpoint's inference and automatic-order flags disabled.
- Make automation stoppable, bounded, auditable, and testable.

## Non-goals
- No OANDA, Binance, or other broker orders from the automated loop.
- No live-trading switch or automatic fallback from paper to broker mode.
- No use of the retrained Kitty V3 model until its data alignment and paper-validation gates pass.
- No claim that this strategy is profitable; this is a demo/testing feature.

## Proposed design
1. **Dedicated paper-auto-trader service.** A small service calls the existing signal analysis and Risk Guardian, then sends approved intents only to the internal paper simulator. It does not route through a broker connector. Its interface should accept an injectable clock and signal provider so tests do not need market connectivity.
2. **Fail-closed mode boundary.** The service checks a hard-coded internal-paper execution boundary before every order and rejects non-paper mode. Automated orders must use an internal simulator API/storage path. No user request, symbol payload, or environment variable can select a broker. Existing manual/approval-gated broker flows remain separate.
3. **Initial risk policy.** Maximum simulated notional: USD 100 per order; maximum 3 newly opened automated trades per UTC day; allowlist: BTC/USD, ETH/USD, SOL/USD, XAU/USD, UNI/USD; require a fresh valid signal and explicit Risk Guardian approval; reject malformed prices, missing stop-loss/take-profit, or non-positive/invalid risk-reward. These limits are enforced at execution time, not only during signal generation.
4. **Duplicate prevention.** Create a deterministic idempotency key from symbol, signal direction, and signal candle/time-window. Persist the key before/atomically with the simulated order so repeated scheduler ticks or restarts cannot duplicate the same signal.
5. **Emergency stop.** Automation starts stopped by default. An explicit internal control enables/disables it; if the control cannot be read, it is stopped. Stopping blocks new orders immediately. It does not silently liquidate open simulated positions; position management/closure remains an explicit simulator function.
6. **Auditability and API.** Expose a status/control interface using the project's existing API conventions. Report enabled/stopped state, last evaluation, last decision/reason, trades used today, and recent audit records. Any enable action should still be authenticated according to existing app patterns.
7. **Tests.** Cover paper-only boundary, broker-order rejection, disabled-by-default and emergency stop, allowlist, max notional, daily cap, invalid/missing risk fields, duplicate signals across repeated ticks/restarts, risk-gate rejection, and Kitty V3 inference remaining disabled.

## Scheduling and failure behavior
Use the existing application lifecycle/background-task conventions after inspecting startup and shutdown behavior. Do not start duplicate workers across reloads or multiple processes; if the deployment cannot guarantee a single worker, use a database-backed lease/lock or keep the scheduler disabled and expose a safe one-shot evaluation endpoint. Provider/API failures, stale signals, database errors, or unknown mode all fail closed and create an audit reason where possible.

## Verification and rollout
Run focused unit tests, the repository's relevant Python tests, syntax/type/build checks affected by changes, and inspect the final diff. Add CI coverage for the new safety contract. Open a PR against `main`; do not merge until checks are green and the diff confirms the auto-trader has no broker execution path. After merge, verify the deployed revision separately; code merge alone does not prove the runtime worker is enabled or healthy.

## Acceptance criteria
- No automated path can submit broker orders.
- Automated paper trading is disabled/stopped by default until explicitly enabled.
- A repeated signal creates at most one simulated order.
- Notional and daily trade caps cannot be bypassed by malformed or repeated requests.
- Emergency stop prevents new automated orders.
- Retrained Kitty V3 inference remains disabled.
- Tests demonstrate the above; CI passes before merge.
