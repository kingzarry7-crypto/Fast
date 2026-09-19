"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface SignalData {
  id?: string | number;
  daily_plan_id?: string;
  symbol: string;
  timeframe?: string | null;
  direction?: string | null;
  status?: string | null;

  entry?: number | null;
  entry_low?: number | null;
  entry_high?: number | null;
  stop_loss?: number | null;

  take_profit_1?: number | null;
  take_profit_2?: number | null;
  take_profit_3?: number | null;

  tp1?: number | null;
  tp2?: number | null;
  tp3?: number | null;

  confidence?: number | null;
  strength?: number | null;

  rsi?: number | null;
  ema9?: number | null;
  ema21?: number | null;
  ema50?: number | null;
  atr?: number | null;

  created_at?: string | null;
  updated_at?: string | null;
  timestamp?: string | null;
  trading_date?: string | null;

  [key: string]: unknown;
}

export interface UseSignalsOptions {
  symbol?: string;
  timeframe?: string;
  autoLoad?: boolean;
}

export interface UseSignalsReturn {
  signals: SignalData[];
  isLoading: boolean;
  error: string | null;
  symbol: string;
  timeframe: string;
  refresh: () => Promise<void>;
  setSymbol: (symbol: string) => void;
  setTimeframe: (timeframe: string) => void;
}

interface RawSignal {
  id?: unknown;
  daily_plan_id?: unknown;
  symbol?: unknown;
  asset?: unknown;
  timeframe?: unknown;
  direction?: unknown;
  signal?: unknown;
  status?: unknown;

  entry?: unknown;
  entry_price?: unknown;
  entry_low?: unknown;
  entry_high?: unknown;
  stop_loss?: unknown;
  sl?: unknown;

  take_profit_1?: unknown;
  take_profit_2?: unknown;
  take_profit_3?: unknown;

  tp1?: unknown;
  tp2?: unknown;
  tp3?: unknown;

  confidence?: unknown;
  strength?: unknown;
  setup_strength?: unknown;

  rsi?: unknown;
  ema9?: unknown;
  ema21?: unknown;
  ema50?: unknown;
  atr?: unknown;

  created_at?: unknown;
  updated_at?: unknown;
  timestamp?: unknown;
  trading_date?: unknown;

  [key: string]: unknown;
}

function normalizeSymbol(value: string): string {
  return value.trim().toUpperCase();
}

function normalizeTimeframe(value: string): string {
  return value.trim().toUpperCase();
}

function toFiniteNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function toStringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim()
    ? value
    : null;
}

function toId(value: unknown): string | number | undefined {
  if (typeof value === "string" || typeof value === "number") {
    return value;
  }

  return undefined;
}

function isRawSignal(value: unknown): value is RawSignal {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function normalizeSignal(
  raw: RawSignal
): SignalData | null {
  const rawSymbol = raw.symbol ?? raw.asset;

  if (
    typeof rawSymbol !== "string" ||
    !rawSymbol.trim()
  ) {
    return null;
  }

  return {
    id: toId(raw.id ?? raw.daily_plan_id),

    daily_plan_id:
      toStringOrNull(raw.daily_plan_id) ?? undefined,

    symbol: normalizeSymbol(rawSymbol),

    timeframe:
      toStringOrNull(raw.timeframe)?.toUpperCase() ?? null,

    direction: toStringOrNull(
      raw.direction ?? raw.signal
    ),

    status: toStringOrNull(raw.status),

    entry: toFiniteNumberOrNull(
      raw.entry ?? raw.entry_price
    ),

    entry_low: toFiniteNumberOrNull(raw.entry_low),

    entry_high: toFiniteNumberOrNull(raw.entry_high),

    stop_loss: toFiniteNumberOrNull(
      raw.stop_loss ?? raw.sl
    ),

    take_profit_1: toFiniteNumberOrNull(
      raw.take_profit_1 ?? raw.tp1
    ),

    take_profit_2: toFiniteNumberOrNull(
      raw.take_profit_2 ?? raw.tp2
    ),

    take_profit_3: toFiniteNumberOrNull(
      raw.take_profit_3 ?? raw.tp3
    ),

    tp1: toFiniteNumberOrNull(raw.tp1),

    tp2: toFiniteNumberOrNull(raw.tp2),

    tp3: toFiniteNumberOrNull(raw.tp3),

    confidence: toFiniteNumberOrNull(
      raw.confidence
    ),

    strength: toFiniteNumberOrNull(
      raw.strength ?? raw.setup_strength
    ),

    rsi: toFiniteNumberOrNull(raw.rsi),

    ema9: toFiniteNumberOrNull(raw.ema9),

    ema21: toFiniteNumberOrNull(raw.ema21),

    ema50: toFiniteNumberOrNull(raw.ema50),

    atr: toFiniteNumberOrNull(raw.atr),

    created_at: toStringOrNull(raw.created_at),

    updated_at: toStringOrNull(raw.updated_at),

    timestamp: toStringOrNull(
      raw.timestamp ?? raw.created_at
    ),

    trading_date: toStringOrNull(
      raw.trading_date
    ),

    ...raw,
  };
}

function extractSignalArray(
  value: unknown
): RawSignal[] {
  if (Array.isArray(value)) {
    return value.filter(isRawSignal);
  }

  if (
    typeof value === "object" &&
    value !== null
  ) {
    const object = value as Record<string, unknown>;

    if (Array.isArray(object.signals)) {
      return object.signals.filter(isRawSignal);
    }

    if (Array.isArray(object.data)) {
      return object.data.filter(isRawSignal);
    }
  }

  return [];
}

function sanitizeErrorMessage(message: string): string {
  return message.replace(
    /api[_-]?key|token|secret|password/gi,
    "[redacted]"
  );
}

export function useSignals(
  options: UseSignalsOptions = {}
): UseSignalsReturn {
  const initialSymbol = normalizeSymbol(
    options.symbol ?? "BTC"
  );

  const initialTimeframe = normalizeTimeframe(
    options.timeframe ?? "15M"
  );

  const [symbol, setSymbolState] =
    useState(initialSymbol);

  const [timeframe, setTimeframeState] =
    useState(initialTimeframe);

  const [signals, setSignals] =
    useState<SignalData[]>([]);

  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const mountedRef = useRef(false);

  const requestIdRef = useRef(0);

  const abortControllerRef =
    useRef<AbortController | null>(null);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      requestIdRef.current += 1;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!options.symbol) {
      return;
    }

    const nextSymbol =
      normalizeSymbol(options.symbol);

    if (
      nextSymbol &&
      nextSymbol !== symbol
    ) {
      setSymbolState(nextSymbol);
    }
  }, [options.symbol, symbol]);

  useEffect(() => {
    if (!options.timeframe) {
      return;
    }

    const nextTimeframe =
      normalizeTimeframe(options.timeframe);

    if (
      nextTimeframe &&
      nextTimeframe !== timeframe
    ) {
      setTimeframeState(nextTimeframe);
    }
  }, [options.timeframe, timeframe]);

  const refresh = useCallback(async () => {
    if (!mountedRef.current) {
      return;
    }

    const requestId =
      ++requestIdRef.current;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller =
      new AbortController();

    abortControllerRef.current =
      controller;

    setIsLoading(true);
    setError(null);

    try {
      /*
       * The web FastAPI backend does not currently
       * expose a confirmed signal endpoint.
       *
       * Do not guess one here.
       *
       * The real signal API will be connected once
       * the backend endpoint and response contract
       * have been implemented.
       */

      void symbol;
      void timeframe;
      void controller.signal;

      const fetchedSignals: SignalData[] = [];

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return;
      }

      setSignals(fetchedSignals);
    } catch (error: unknown) {
      if (
        error instanceof DOMException &&
        error.name === "AbortError"
      ) {
        return;
      }

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return;
      }

      const message =
        error instanceof Error
          ? error.message
          : "Failed to load signals.";

      setError(
        sanitizeErrorMessage(message)
      );
    } finally {
      if (
        requestId === requestIdRef.current &&
        mountedRef.current
      ) {
        setIsLoading(false);
      }

      if (
        abortControllerRef.current ===
        controller
      ) {
        abortControllerRef.current = null;
      }
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    if (options.autoLoad) {
      void refresh();
    }
  }, [options.autoLoad, refresh]);

  const setSymbol = useCallback(
    (value: string) => {
      const nextSymbol =
        normalizeSymbol(value);

      if (!nextSymbol) {
        return;
      }

      setSymbolState(nextSymbol);
    },
    []
  );

  const setTimeframe = useCallback(
    (value: string) => {
      const nextTimeframe =
        normalizeTimeframe(value);

      if (!nextTimeframe) {
        return;
      }

      setTimeframeState(nextTimeframe);
    },
    []
  );

  return {
    signals,
    isLoading,
    error,
    symbol,
    timeframe,
    refresh,
    setSymbol,
    setTimeframe,
  };
}

export default useSignals;
