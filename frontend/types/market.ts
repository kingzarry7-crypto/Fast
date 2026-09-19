// Fast/frontend/types/market.ts
// Market data contracts for KING ZARRY AI web frontend.
// Types only. No React, logic, API calls, or side effects.

/**
 * General market direction.
 */
export type MarketTrend =
  | "bullish"
  | "bearish"
  | "neutral"
  | "up"
  | "down";

/**
 * Common market categories.
 */
export type MarketCategory =
  | "crypto"
  | "forex"
  | "metals"
  | "index"
  | "other";

/**
 * Core market data used by market cards, dashboards,
 * charts, and market intelligence components.
 *
 * Optional fields are used because different market
 * sources may provide different levels of information.
 */
export interface MarketData {
  symbol: string;
  name?: string | null;
  category?: MarketCategory | string | null;
  market?: string | null;

  price?: number | null;
  currentPrice?: number | null;
  value?: number | null;
  lastPrice?: number | null;
  close?: number | null;

  change?: number | null;
  changePercent?: number | null;

  direction?: MarketTrend | string | null;
  trend?: MarketTrend | string | null;
  bias?: MarketTrend | string | null;
  momentum?: MarketTrend | string | null;

  timeframe?: string | null;
  interval?: string | null;
  exchange?: string | null;
  source?: string | null;

  rsi?: number | null;
  ema?: number | null;
  atr?: number | null;

  marketStructure?: string | null;
  structure?: string | null;
  confidence?: number | null;
  volatility?: number | null;

  aiRead?: string | null;
  aiInterpretation?: string | null;
  interpretation?: string | null;
  analysis?: string | null;
  summary?: string | null;
  marketRead?: string | null;

  sparkline?: number[] | null;
  chartData?: number[] | null;
  history?: number[] | null;
  prices?: number[] | null;

  lastUpdated?: string | null;
  updatedAt?: string | null;
  timestamp?: string | null;
  time?: string | null;

  loading?: boolean;
  isLoading?: boolean;
  error?: string | null;
  errorMessage?: string | null;

  selected?: boolean;
  active?: boolean;
  disabled?: boolean;
}

/**
 * Supported market asset aliases.
 *
 * This describes symbols accepted by the frontend.
 * It does not determine which markets are currently live.
 */
export type MarketSymbol =
  | "BTC"
  | "ETH"
  | "SOL"
  | "XAU/USD"
  | string;

/**
 * Request parameters for a market lookup.
 */
export interface MarketQuery {
  symbol: string;
  timeframe?: string;
}

/**
 * Collection of market data.
 */
export interface MarketsResponse {
  markets: MarketData[];
}

/**
 * Single market response.
 */
export interface MarketResponse {
  market: MarketData | null;
}

/**
 * Simple chart point for market history.
 */
export interface MarketChartPoint {
  time: string | number;
  value: number;
}

/**
 * Optional OHLC market candle.
 *
 * Use only when the connected market source actually
 * provides OHLC data.
 */
export interface MarketCandle {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
}

/**
 * Watchlist item.
 */
export interface MarketWatchlistItem {
  symbol: string;
  name?: string | null;
  selected?: boolean;
}
