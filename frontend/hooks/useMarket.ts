"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface MarketData {
  symbol: string;
  price?: number | null;
  change?: number | null;
  change_percent?: number | null;
  direction?: string | null;
  timeframe?: string | null;
  timestamp?: string | null;
  [key: string]: unknown;
}

export interface UseMarketOptions {
  symbol?: string;
  timeframe?: string;
  autoLoad?: boolean;
}

export interface UseMarketReturn {
  market: MarketData | null;
  isLoading: boolean;
  error: string | null;
  symbol: string;
  timeframe: string;
  refresh: () => Promise<void>;
  setSymbol: (symbol: string) => void;
  setTimeframe: (timeframe: string) => void;
}

interface ApiMarketResponse {
  symbol?: unknown;
  asset?: unknown;
  price?: unknown;
  currentPrice?: unknown;
  lastPrice?: unknown;
  change?: unknown;
  changeValue?: unknown;
  change_percent?: unknown;
  changePercent?: unknown;
  percentChange?: unknown;
  direction?: unknown;
  trend?: unknown;
  bias?: unknown;
  timeframe?: unknown;
  timestamp?: unknown;
  lastUpdated?: unknown;
  data?: unknown;
  market?: unknown;
  detail?: unknown;
  message?: unknown;
  error?: unknown;
  [key: string]: unknown;
}

function getApiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
}

function normalizeSymbol(value: string): string {
  return value.trim().toUpperCase();
}

function normalizeTimeframe(value: string): string {
  return value.trim().toUpperCase();
}

function getErrorMessage(
  status: number,
  data: ApiMarketResponse | null
): string {
  if (status === 401 || status === 403) {
    return "Authentication required. Please sign in again.";
  }

  if (typeof data?.detail === "string" && data.detail.trim()) {
    return data.detail;
  }

  if (typeof data?.message === "string" && data.message.trim()) {
    return data.message;
  }

  if (typeof data?.error === "string" && data.error.trim()) {
    return data.error;
  }

  return `Market request failed (${status}).`;
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function normalizeMarketData(
  response: ApiMarketResponse,
  fallbackSymbol: string,
  fallbackTimeframe: string
): MarketData | null {
  const candidate =
    response.market && typeof response.market === "object"
      ? (response.market as ApiMarketResponse)
      : response.data && typeof response.data === "object"
        ? (response.data as ApiMarketResponse)
        : response;

  const rawSymbol =
    candidate.symbol ?? candidate.asset ?? fallbackSymbol;

  if (typeof rawSymbol !== "string" || !rawSymbol.trim()) {
    return null;
  }

  const rawTimeframe =
    candidate.timeframe ?? fallbackTimeframe;

  return {
    ...candidate,

    symbol: rawSymbol.trim().toUpperCase(),

    price: toNumber(
      candidate.price ??
        candidate.currentPrice ??
        candidate.lastPrice
    ),

    change: toNumber(
      candidate.change ?? candidate.changeValue
    ),

    change_percent: toNumber(
      candidate.change_percent ??
        candidate.changePercent ??
        candidate.percentChange
    ),

    direction:
      typeof (
        candidate.direction ??
        candidate.trend ??
        candidate.bias
      ) === "string"
        ? String(
            candidate.direction ??
              candidate.trend ??
              candidate.bias
          )
        : null,

    timeframe:
      typeof rawTimeframe === "string"
        ? rawTimeframe.toUpperCase()
        : fallbackTimeframe,

    timestamp:
      typeof (
        candidate.timestamp ??
        candidate.lastUpdated
      ) === "string"
        ? String(
            candidate.timestamp ??
              candidate.lastUpdated
          )
        : null,
  };
}

async function fetchMarket(
  symbol: string,
  timeframe: string,
  signal: AbortSignal
): Promise<MarketData | null> {
  const base = getApiBase();

  /*
   * There is currently no confirmed dedicated web market endpoint
   * in the frontend API contract.
   *
   * Do not invent an endpoint here.
   *
   * Once the FastAPI market endpoint is officially added, this
   * function should be updated to call that exact endpoint.
   */
  if (!base) {
    return null;
  }

  // Intentionally no guessed endpoint.
  // This prevents the frontend from pretending that live market
  // data exists before the backend contract is actually ready.
  void symbol;
  void timeframe;
  void signal;

  return null;
}

export function useMarket(
  options: UseMarketOptions = {}
): UseMarketReturn {
  const initialSymbol = normalizeSymbol(
    options.symbol ?? "BTC"
  );

  const initialTimeframe = normalizeTimeframe(
    options.timeframe ?? "15M"
  );

  const [symbol, setSymbolState] =
    useState<string>(initialSymbol);

  const [timeframe, setTimeframeState] =
    useState<string>(initialTimeframe);

  const [market, setMarket] =
    useState<MarketData | null>(null);

  const [isLoading, setIsLoading] =
    useState<boolean>(false);

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

    const nextSymbol = normalizeSymbol(options.symbol);

    if (nextSymbol && nextSymbol !== symbol) {
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

    const requestId = ++requestIdRef.current;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();

    abortControllerRef.current = controller;

    setIsLoading(true);
    setError(null);

    try {
      const result = await fetchMarket(
        symbol,
        timeframe,
        controller.signal
      );

      if (
        requestId !== requestIdRef.current ||
        !mountedRef.current
      ) {
        return;
      }

      setMarket(result);
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
          : "Failed to load market data.";

      setError(
        message.replace(
          /token|key|secret|password/gi,
          "[redacted]"
        )
      );
    } finally {
      if (
        requestId === requestIdRef.current &&
        mountedRef.current
      ) {
        setIsLoading(false);
      }

      if (
        abortControllerRef.current === controller
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

  const setSymbol = useCallback((value: string) => {
    const nextSymbol = normalizeSymbol(value);

    if (!nextSymbol) {
      return;
    }

    setSymbolState(nextSymbol);
  }, []);

  const setTimeframe = useCallback((value: string) => {
    const nextTimeframe =
      normalizeTimeframe(value);

    if (!nextTimeframe) {
      return;
    }

    setTimeframeState(nextTimeframe);
  }, []);

  return {
    market,
    isLoading,
    error,
    symbol,
    timeframe,
    refresh,
    setSymbol,
    setTimeframe,
  };
}

export default useMarket;
