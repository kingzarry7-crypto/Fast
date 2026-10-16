# Kitty V3 BTC/USD paper trading

Kitty paper trading is an isolated research simulation. It does not call
`trading_connector.place_market_order`, read broker credentials, or submit live
orders. The existing six-feature Kitty V3 model is experimental and its metadata
does not confirm the training symbol; paper results must not be interpreted as
evidence of profitability or as approval for live trading.

## Defaults

- Symbol: BTC/USD
- Timeframe: daily candles; the newest potentially-open candle is excluded
- Starting simulated cash: USD 10,000
- Simulated buy size: 0.001 BTC, capped at USD 100 notional per order
- Strategy: BUY_BIAS opens a small long paper position; SELL_BIAS closes it;
  HOLD does nothing. No leverage or short selling.
- Candle deduplication: each completed candle is processed at most once in the
  SQLite ledger.
- Live execution: always disabled in this module.

The paper worker starts with FastAPI startup unless
`KITTY_PAPER_TRADING_ENABLED=false`. Set `KITTY_PAPER_POLL_SECONDS` (60–3600,
default 900) to change polling. Optional `KITTY_PAPER_ORDER_BTC` and
`KITTY_PAPER_MAX_NOTIONAL_USD` tune simulated order size (hard-capped at 0.01
BTC and USD 500). Set `KITTY_PAPER_DB_PATH` to a persistent disk path, or use
`DATA_DIR` for the default database location. On ephemeral hosting, the paper
ledger may reset when the instance is replaced unless a persistent volume is
configured.

## API

- `GET /api/kitty/paper/status` — mode, simulated balance, position and recent ledger.
- `POST /api/kitty/paper/cycle` — manually request one paper-only evaluation.

A cycle may return `skipped` if market data or model validation fails, or
`already_processed` if the latest completed candle was already handled. It
does not force a trade when data is stale or invalid.

Do not enable live trading by changing this paper module. Live trading requires a
separate review of model/target alignment, validated backtests and forward paper
results, provider/account configuration, risk limits, and explicit live-mode
authorization. The existing live connector's kill switch and safeguards must
remain in force.
