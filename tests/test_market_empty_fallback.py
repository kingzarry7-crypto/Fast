"""Regression tests for market-data fallback behavior."""
import market


def test_empty_paid_market_responses_fall_through_to_public_binance(monkeypatch):
    candles = [{"time": "2026-10-18T21:00:00Z", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10.0}]

    monkeypatch.setattr(market, "_is_gold_symbol", lambda symbol: False)
    monkeypatch.setattr(market, "_should_try_alpaca_market_data", lambda: True)
    monkeypatch.setattr(market, "_alpaca_supports_symbol", lambda symbol: True)
    monkeypatch.setattr(market, "_alpaca_get_candles", lambda *args: [])
    monkeypatch.setattr(market, "_should_try_massive_market_data", lambda: True)
    monkeypatch.setattr(market, "_massive_get_candles", lambda *args: [])
    monkeypatch.setattr(market, "binance_pair", lambda symbol: "BTCUSDT")
    monkeypatch.setattr(market, "_binance_get_candles", lambda *args: candles)
    monkeypatch.setattr(market, "_twelve_get_candles", lambda *args: (_ for _ in ()).throw(AssertionError("should not need Twelve Data")))

    result = market.get_candles("BTC/USD", "1h", 100)

    assert result == candles


def test_market_data_does_not_return_empty_candles(monkeypatch):
    monkeypatch.setattr(market, "_is_gold_symbol", lambda symbol: False)
    monkeypatch.setattr(market, "_should_try_alpaca_market_data", lambda: False)
    monkeypatch.setattr(market, "_alpaca_supports_symbol", lambda symbol: False)
    monkeypatch.setattr(market, "_should_try_massive_market_data", lambda: False)
    monkeypatch.setattr(market, "binance_pair", lambda symbol: None)
    monkeypatch.setattr(market, "_twelve_get_candles", lambda *args: [])

    try:
        market.get_candles("UNKNOWN/USD", "1h", 100)
    except RuntimeError as exc:
        assert "No candle provider returned data" in str(exc)
    else:
        raise AssertionError("empty candle data must not be treated as a successful result")
