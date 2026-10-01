# KING ZARRY AI — Action Gateway setup

This layer is additive. The existing Signal Agent, five-market Telegram delivery, Market Intelligence Agent, Risk Guardian, chat, and morning brief continue to work.

## Default safety

- Trading mode: `paper`
- Live trading: disabled unless `TRADING_MODE=live` and `TRADING_ENABLED=true`
- Live kill switch: `AGENT_TRADING_KILL_SWITCH=true` by default
- Approved trading markets: BTC/USD, ETH/USD, SOL/USD, XAU/USD, UNI/USD
- Max order notional: `TRADING_MAX_NOTIONAL=100` by default
- Max trades/day setting: `TRADING_MAX_TRADES_PER_DAY=3`
- External actions require explicit approval in the Agent dashboard.
- Broker/API secrets are read from Railway environment variables only.

## Paper trading

No broker credentials are needed.

Recommended Railway variables:

```
TRADING_MODE=paper
TRADING_ENABLED=false
AGENT_TRADING_KILL_SWITCH=true
TRADING_MAX_NOTIONAL=100
TRADING_MAX_TRADES_PER_DAY=3
PAPER_STARTING_BALANCE=10000
```

The dashboard can prepare a trade action and approval will run a fresh market analysis + Agent V2 + Risk Guardian check before the paper order is recorded.

## Binance live connector

Only configure this after paper testing.

```
TRADING_MODE=live
TRADING_ENABLED=true
AGENT_TRADING_KILL_SWITCH=false
TRADING_PROVIDER=binance
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

Use a dedicated API key with only the permissions required for trading/account data. Do not enable withdrawals.

The current Binance adapter supports market orders for BTC/USD, ETH/USD, SOL/USD and UNI/USD.

## OANDA live connector

For XAU/USD:

```
TRADING_MODE=live
TRADING_ENABLED=true
AGENT_TRADING_KILL_SWITCH=false
TRADING_PROVIDER=oanda
OANDA_API_TOKEN=...
OANDA_ACCOUNT_ID=...
OANDA_API_URL=https://api-fxpractice.oanda.com/v3
```

The default URL is OANDA practice/demo. Switch to a live endpoint only when the account and testing are ready.

## WhatsApp Business Cloud API

Use a dedicated WhatsApp Business number and Meta's official Cloud API.

Railway variables:

```
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_GRAPH_VERSION=vXX.X
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_APP_SECRET=...
```

Set Meta's webhook URL to:

`https://YOUR-RAILWAY-HOST/api/whatsapp/webhook`

The GET route handles Meta verification. The POST route validates `X-Hub-Signature-256` and acknowledges events. Outbound messages are approval-gated through the Agent Action Gateway.

Never put access tokens, API secrets, or app secrets in chat or source code.
