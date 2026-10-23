# Kitty + JustMarkets MT5 bridge (shadow-only)

## Current safety scope
This EA only reports terminal/account/symbol metadata, polls signals, and acknowledges shadow evaluation. It contains no order-submission call. It is not proof that Kitty is profitable, and it must not be used as a live-trading system.

## Railway configuration
Set these backend environment variables as Railway secrets/configuration:
- `JUSTMARKETS_MT5_BRIDGE_TOKEN`: random secret at least 32 characters. Use a dedicated value, not a broker password or other API key.
- `JUSTMARKETS_MT5_EXPECTED_SERVER`: exact server string copied from MT5 account details.
- `JUSTMARKETS_MT5_ALLOWED_ACCOUNTS`: comma-separated approved demo login IDs only.
- Optional `JUSTMARKETS_MT5_BRIDGE_DB_PATH` or `DATA_DIR`: persistent writable storage path for the SQLite ledger. Without persistent storage, records may be lost on redeploy/restart.

Do not commit secrets to GitHub. If the bridge token is missing, all operational endpoints fail closed. Railway must deploy the branch/commit containing the bridge before the endpoints exist.

## Windows MT5 setup
1. Log in to **JustMarkets Demo 3**. Confirm the terminal's account trade mode says Demo.
2. Copy the exact server name and numeric account login from MT5. Do not guess the server string or account number.
3. In MetaEditor, open `mt5/JustMarketsKittyBridge.mq5`, compile, and require zero errors.
4. In MT5, open Tools → Options → Expert Advisors and enable WebRequest for listed URLs. Add only the exact HTTPS Railway backend origin, e.g. `https://YOUR-RAILWAY-HOST` (no path). Replace the placeholder with the real backend hostname.
5. Attach the EA to a chart. Set BridgeBaseUrl, BridgeToken, ExpectedServer and AllowedAccountLogin. Keep the terminal connected to the demo account.
6. Set BrokerSymbolBTC to the exact symbol `BTC` and BrokerSymbolGold to the exact symbol `XAUUSD` only if Market Watch shows those exact names.
7. Watch the Experts and Journal tabs. A verified status means only that identity and symbol metadata passed the bridge checks. Shadow log entries explicitly state that no order was submitted.

## API endpoints
All endpoints require `Authorization: Bearer <JUSTMARKETS_MT5_BRIDGE_TOKEN>`.
- `GET /justmarkets-mt5/status`
- `POST /justmarkets-mt5/heartbeat`
- `GET /justmarkets-mt5/work`
- `POST /justmarkets-mt5/ack`

The heartbeat is considered fresh for five minutes. The EA sends it every timer cycle. Work is only returned when the account/server allowlist has passed, the heartbeat is fresh, and the signal symbol is present in verified metadata. `NO_TRADE` is informational only. Expired signals are not returned.

## Important current limitation
Kitty's existing paper simulator uses its own market-data provider and paper ledger. The MT5 bridge does not fetch candles from the broker and does not submit orders. Kitty's existing completed-candle cycle now publishes only the actual gated output for the explicitly mapped source symbols BTC/USD → BTC and XAU/USD → XAUUSD. The current strategy safety gate forces the actionable output to NO TRADE, and the bridge records that as informational only; candidate BUY/SELL setups are never promoted. No directional work should be expected unless Kitty's signal gate is separately revalidated. Do not infer profitability from a successful heartbeat.

## Manual acceptance checklist
- [ ] MetaEditor compiles the EA with zero errors.
- [ ] Correct demo login and exact server pass heartbeat validation.
- [ ] A live/non-demo login is rejected.
- [ ] Wrong server or account login is rejected.
- [ ] Exact symbol metadata for BTC and XAUUSD appears; unknown aliases are ignored.
- [ ] Missing/invalid bridge token is rejected.
- [ ] Stale heartbeat returns no work.
- [ ] Expired signals and `NO_TRADE` never become actionable work.
- [ ] EA logs shadow evaluation and no broker order appears in account history.
- [ ] Python bridge tests and existing repository test suite pass in CI.
- [ ] Restart/redeploy behavior is checked against the configured persistent storage.
