# JustMarkets MT5 Bridge for Kitty — Design

**Status:** Draft for user review  
**Date:** 2026-10-23  
**Repository:** `kingzarry7-crypto/Fast`  
**Target branch:** `main`

## Goal

Add a deliberately isolated connection between the Fast/Kitty backend and the user's locally running MetaTrader 5 terminal logged into a JustMarkets demo account. Initially, the bridge must operate in shadow mode and must never enable live trading. It must support separate BTC and XAUUSD configurations only after each exact symbol is verified against the broker terminal.

## Current-state findings

The existing `trading_connector.py` supports AUTO/Binance/OANDA paths and has conservative paper/live guards, but no JustMarkets MT5 connector. `kitty_demo_trader.py` is tied to Binance Spot Demo and BTC/USD. `kitty_multi_paper.py` is a paper simulator, not a broker bridge. Therefore, the MT5 integration must be a separate component and must not route orders through the existing Binance/OANDA adapters.

## Approaches considered

1. **Local MT5 Expert Advisor (recommended):** A small MQL5 Expert Advisor runs inside the user's Windows MT5 terminal and communicates with the Fast backend over authenticated HTTPS. This uses the logged-in terminal and broker's symbol/account metadata without exposing broker credentials to Railway.
2. **Python MetaTrader5 package on the PC:** A local Python service talks to the terminal. This adds a second local runtime and process supervision, and is less self-contained than an EA.
3. **Direct broker API:** Not selected because the required MT5 trading path and exact supported JustMarkets API are not verified; it could bypass the user's configured terminal and symbol metadata.

## Architecture

- **Backend bridge module:** Add a dedicated authenticated API component to Fast, using the repository's existing API conventions after route registration and middleware are inspected during implementation. It accepts status/heartbeat, account/symbol capability reports, and signal/order-result acknowledgements.
- **MT5 Expert Advisor:** Runs locally in the already-connected JustMarkets Demo 3 terminal. It polls for authorized work or reports state over HTTPS using MT5's configured WebRequest allowlist. It never sends terminal passwords to the backend.
- **Signal contract:** Each signal includes a unique ID, symbol, direction, source timeframe/candle timestamp, creation timestamp, expiry, stop-loss, and any required sizing/risk metadata. Only explicitly supported directions are accepted; NO TRADE means no order.
- **Identity and symbol verification:** EA verifies `ACCOUNT_TRADE_MODE_DEMO`, exact configured server identity, and account identity allowlist. It checks the exact symbol name reported by MT5 rather than assuming BTC means BTCUSD. It reports symbol trade mode, volume minimum/maximum/step, tick size/value, digits, and minimum stop distance. Unknown or unavailable symbols fail closed.
- **Order safety:** Execution is disabled by default. Shadow-only signal validation comes first. Any later demo-order mode requires an explicit local opt-in plus server-side demo-only policy. There is no live fallback. All requests require authentication, freshness checks, replay/duplicate protection, per-symbol risk caps, a global kill switch, and a daily-loss cap. Orders must include a valid stop-loss at submission; after execution the EA verifies protective stop presence and takes a documented protective action if the broker reports a fill without the required stop.
- **Auditability:** Record UTC timestamps, correlation/signal IDs, decisions, rejections, broker retcodes, order/deal identifiers, and stop verification. Never log credentials or bearer tokens.
- **Hosting:** The EA initially runs on the user's PC. Railway can host the backend endpoint but is not itself a Windows MT5 terminal/VPS. Vercel must remain untouched.

## Safe operating stages

1. **Stage A — shadow-only:** heartbeat, identity and symbol checks, signal freshness, sizing validation, and audit records; no order submission.
2. **Stage B — demo verification:** only after Stage A tests pass and the user explicitly opts in, send a controlled demo order with a valid stop-loss, verify broker acknowledgement and protection, then close/record it. This mode remains demo-only.
3. **Live trading:** explicitly out of scope and hard-disabled by design.

## Initial symbol and account configuration

- Broker terminal: JustMarkets demo; the user reports the server label as “JustMarkets Demo 3”. Implementation must use the exact server string visible in MT5 and an explicit account allowlist rather than guessing punctuation/case.
- User-reported symbols: `BTC` and `XAUUSD`. These are not considered verified tradable symbols until the EA confirms their exact names and metadata from the connected terminal.
- Signal watcher cadence: keep the user's requested two-hour scan cadence for model/provider usage; the bridge must reject expired signals regardless of scan cadence.

## Failure handling

Reject and audit any request when authentication fails, account/server is not an allowed demo account, symbol is not verified, terminal is disconnected, signal is stale or duplicated, quantity violates broker steps, stop-loss is missing/invalid, risk caps are exceeded, market is closed, or broker execution returns a rejection. Network errors must not trigger retries that can create duplicate orders; idempotency keys and broker-side state reconciliation are required. If account mode cannot be proved to be demo, no order path is available.

## Testing and acceptance criteria

- Backend unit tests for auth failures, default-disabled execution, wrong account/server, unknown symbols, stale signals, duplicate IDs, invalid volume/stop-loss, risk caps, kill switch, and safe network/retry behavior.
- Simulated broker tests for market closed, requote/rejection, partial/failed acknowledgement, missing protective stop, and service/terminal restart.
- Manual MetaEditor compile and JustMarkets demo-terminal test checklist for the EA; Python CI alone cannot prove MQL5 compilation or broker execution.
- Stage A passes with both user-reported symbols independently validated, or clearly reports the exact symbol unavailable without placing an order.
- Stage B passes only when a demo order and its protective stop are confirmed by the terminal and corresponding audit record.
- Automated trading and live trading remain disabled unless a separate, explicit demo-only enablement flow is implemented and verified. No production/live trading setting is to be introduced by this work.

## Scope exclusions

No Vercel changes, no direct live orders, no broker passwords stored in Railway, no assumed symbol aliases, no automatic risk escalation, and no claims of profitability. Kitty's signal profitability remains unproven and must be evaluated separately with leakage-safe after-cost tests.
