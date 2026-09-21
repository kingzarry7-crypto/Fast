"use client";

import { useEffect, useState } from "react";

export interface SignalData {
  id?: string | number;
  name?: string;
  symbol?: string;
  status?: string | null;
  exchange?: string | null;
  type?: string | null;
  side?: string | null;
  entry_price?: number | null;
  current_price?: number | null;
  quantity?: number | null;
  leverage?: number | null;
  margin?: number | null;
  pnl?: number | null;
  pnl_percent?: number | null;
  take_profit?: number | null;
  stop_loss?: number | null;
  created_at?: number | null;
  updated_at?: number | null;
  closed_at?: number | null;
  close_reason?: string | null;
  notes?: string | null;
  tags?: string | null;
  metadata?: string | null;
  signal_provider?: string | null;
  risk_reward_ratio?: number | null;
  win_rate?: number | null;
  confidence?: number | null;
}

function getApiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").replace(/\/$/, "");
}

export function useSignals() {
  const [signals, setSignals] = useState<SignalData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    const fetchSignals = async () => {
      const base = getApiBase();
      if (!base) {
        setSignals([]);
        setLoading(false);
        setError("API base URL not configured.");
        return;
      }

      try {
        const response = await fetch(`${base}/api/signals`, {
          credentials: "include",
          signal: controller.signal,
        });

        if (response.status === 401 || response.status === 403) {
          setSignals([]);
          setLoading(false);
          setError("Authentication required.");
          return;
        }

        if (response.status === 404) {
          // Endpoint not yet implemented on backend — treat as empty,
          // not an error.
          setSignals([]);
          setLoading(false);
          setError(null);
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch signals (${response.status})`);
        }

        const data = await response.json();
        const arr = Array.isArray(data)
          ? data
          : Array.isArray((data as { signals?: unknown }).signals)
            ? (data as { signals: unknown[] }).signals
            : [];

        const typedSignals: SignalData[] = arr.map(
          (item: Record<string, unknown>) => ({
            id: item.id as string | number | undefined,
            name: item.name as string | undefined,
            symbol: item.symbol as string | undefined,
            status: item.status as string | null | undefined,
            exchange: item.exchange as string | null | undefined,
            type: item.type as string | null | undefined,
            side: item.side as string | null | undefined,
            entry_price: item.entry_price as number | null | undefined,
            current_price: item.current_price as number | null | undefined,
            quantity: item.quantity as number | null | undefined,
            leverage: item.leverage as number | null | undefined,
            margin: item.margin as number | null | undefined,
            pnl: item.pnl as number | null | undefined,
            pnl_percent: item.pnl_percent as number | null | undefined,
            take_profit: item.take_profit as number | null | undefined,
            stop_loss: item.stop_loss as number | null | undefined,
            created_at: item.created_at as number | null | undefined,
            updated_at: item.updated_at as number | null | undefined,
            closed_at: item.closed_at as number | null | undefined,
            close_reason: item.close_reason as string | null | undefined,
            notes: item.notes as string | null | undefined,
            tags: item.tags as string | null | undefined,
            metadata: item.metadata as string | null | undefined,
            signal_provider: item.signal_provider as string | null | undefined,
            risk_reward_ratio: item.risk_reward_ratio as number | null | undefined,
            win_rate: item.win_rate as number | null | undefined,
            confidence: item.confidence as number | null | undefined,
          })
        );

        setSignals(typedSignals);
        setLoading(false);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to fetch signals");
        setLoading(false);
      }
    };

    fetchSignals();
    return () => controller.abort();
  }, []);

  return { signals, loading, error };
}
