// Fast/frontend/types/trading.ts
// Trading data contracts for KING ZARRY AI web frontend.
// Types only. No React, logic, API calls, or side effects.

/**
 * Supported trading directions.
 */
export type TradeDirection =
  | "BUY"
  | "SELL"
  | "LONG"
  | "SHORT"
  | "NEUTRAL";

/**
 * Signal lifecycle/status.
 */
export type SignalStatus =
  | "ACTIVE"
  | "PENDING"
  | "TRIGGERED"
  | "COMPLETED"
  | "CANCELLED"
  | "EXPIRED"
  | "WAIT";

/**
 * Confidence level for a trading signal.
 */
export type SignalConfidence =
  | "LOW"
  | "MEDIUM"
  | "HIGH";

/**
 * Common market structure states.
 */
export type MarketStructure =
  | "BULLISH"
  | "BEARISH"
  | "RANGE"
  | "NEUTRAL"
  | string;

/**
 * Trading timeframe.
 */
export type TradingTimeframe =
  | "1M"
  | "5M"
  | "15M"
  | "30M"
  | "1H"
  | "2H"
  | "4H"
  | "1D"
  | string;

/**
 * Supported trading assets.
 */
export type TradingAsset =
  | "BTC"
  | "ETH"
  | "SOL"
  | "XAU/USD"
  | string;

/**
 * Entry, stop-loss, and take-profit levels.
 */
export interface TradeLevels {
  entry?: number | null;
  stopLoss?: number | null;
  sl?: number | null;

  tp1?: number | null;
  tp2?: number | null;
  tp3?: number | null;

  riskReward?: number | null;
  risk?: number | null;
  reward?: number | null;
}

/**
 * Multi-timeframe market analysis.
 */
export interface MultiTimeframeAnalysis {
  "1M"?: string | null;
  "5M"?: string | null;
  "15M"?: string | null;
  "30M"?: string | null;
  "1H"?: string | null;
  "2H"?: string | null;
  "4H"?: string | null;
  "1D"?: string | null;

  [timeframe: string]: string | null | undefined;
}

/**
 * Technical indicator snapshot.
 */
export interface TradingIndicators {
  rsi?: number | null;

  ema9?: number | null;
  ema21?: number | null;
  ema50?: number | null;

  atr?: number | null;

  marketStructure?: MarketStructure | null;
  structure?: MarketStructure | null;

  volatility?: number | null;

  [indicator: string]:
    | number
    | string
    | null
    | undefined;
}

/**
 * A single trading signal.
 */
export interface TradingSignal {
  id?: string | number | null;

  asset?: TradingAsset | null;
  symbol?: string | null;
  market?: string | null;

  direction?: TradeDirection | null;
  side?: TradeDirection | null;

  timeframe?: TradingTimeframe | null;
  executionTimeframe?: TradingTimeframe | null;

  status?: SignalStatus | string | null;
  confidence?: SignalConfidence | string | number | null;

  entry?: number | null;
  stopLoss?: number | null;
  sl?: number | null;

  tp1?: number | null;
  tp2?: number | null;
  tp3?: number | null;

  riskReward?: number | null;

  indicators?: TradingIndicators | null;

  rsi?: number | null;
  ema9?: number | null;
  ema21?: number | null;
  ema50?: number | null;
  atr?: number | null;

  marketStructure?: MarketStructure | null;
  structure?: MarketStructure | null;

  multiTimeframe?: MultiTimeframeAnalysis | null;

  analysis?: string | null;
  reasoning?: string | null;
  explanation?: string | null;
  aiAnalysis?: string | null;

  createdAt?: string | null;
  created_at?: string | null;

  updatedAt?: string | null;
  updated_at?: string | null;

  expiresAt?: string | null;
  expires_at?: string | null;
}

/**
 * Alias for components that use the shorter Signal name.
 */
export type Signal = TradingSignal;

/**
 * Trading signal collection response.
 */
export interface SignalsResponse {
  signals: TradingSignal[];

  total?: number;
  page?: number;
  pageSize?: number;
  hasMore?: boolean;

  status?: string;
  message?: string;
}

/**
 * Parameters for requesting trading signals.
 */
export interface SignalQuery {
  symbol?: string;
  asset?: string;
  timeframe?: TradingTimeframe;
}

/**
 * State used by trading signal hooks/components.
 */
export interface TradingState {
  signals: TradingSignal[];
  selectedSignal?: TradingSignal | null;

  isLoading: boolean;
  error: string | null;
}

/**
 * OHLC candle used by trading charts.
 */
export interface TradingCandle {
  time: string | number;

  open: number;
  high: number;
  low: number;
  close: number;

  volume?: number | null;
}

/**
 * Optional indicator series for chart overlays.
 */
export interface IndicatorPoint {
  time: string | number;
  value: number;
  label?: string | null;
}

/**
 * Chart data contract.
 */
export interface TradingChartData {
  candles?: TradingCandle[];
  prices?: TradingChartPoint[];
  ema9?: IndicatorPoint[];
  ema21?: IndicatorPoint[];
  ema50?: IndicatorPoint[];
  volume?: IndicatorPoint[];
}

/**
 * Simple price chart point.
 */
export interface TradingChartPoint {
  time: string | number;
  value: number;
}

/**
 * Trading alert/level marker for charts.
 */
export interface TradingLevel {
  label: string;
  value: number;
  type?:
    | "entry"
    | "stop-loss"
    | "tp1"
    | "tp2"
    | "tp3"
    | string;
}

/**
 * Lightweight trading history item.
 */
export interface TradeHistoryItem {
  id: string | number;

  asset?: string | null;
  symbol?: string | null;

  direction?: TradeDirection | null;
  timeframe?: TradingTimeframe | null;

  entry?: number | null;
  exit?: number | null;

  stopLoss?: number | null;
  takeProfit?: number | null;

  result?: string | null;
  pnl?: number | null;

  createdAt?: string | null;
  closedAt?: string | null;
}
