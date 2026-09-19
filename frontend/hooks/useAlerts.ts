"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

export type AlertCondition =
  | "ABOVE"
  | "BELOW"
  | "REACHES";

export interface Alert {
  id: number | string;
  symbol: string;
  target_price: number;
  condition: AlertCondition;
  active: boolean;
  triggered: boolean;
  created_at: string;
  triggered_at?: string | null;
  last_checked_price?: number | null;
  last_checked_at?: string | null;
  user_id?: number | string;
}

export interface CreateAlertPayload {
  symbol: string;
  target_price: number;
  condition: AlertCondition;
}

export type UpdateAlertPayload = Partial<
  Pick<
    Alert,
    | "symbol"
    | "target_price"
    | "condition"
    | "active"
  >
>;

export interface UseAlertsOptions {
  autoLoad?: boolean;
}

export interface AlertMutationResult {
  success: boolean;
  id?: Alert["id"];
  error?: string;
}

export interface UseAlertsReturn {
  alerts: Alert[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createAlert: (
    payload: CreateAlertPayload
  ) => Promise<AlertMutationResult>;
  updateAlert: (
    id: Alert["id"],
    payload: UpdateAlertPayload
  ) => Promise<AlertMutationResult>;
  deleteAlert: (
    id: Alert["id"]
  ) => Promise<AlertMutationResult>;
}

interface AlertsApi {
  getAlerts?: () => Promise<Alert[]>;
  listAlerts?: () => Promise<Alert[]>;
  fetchAlerts?: () => Promise<Alert[]>;

  createAlert?: (
    payload: CreateAlertPayload
  ) => Promise<{ id: Alert["id"] } | Alert>;

  updateAlert?: (
    id: Alert["id"],
    payload: UpdateAlertPayload
  ) => Promise<void>;

  deleteAlert?: (
    id: Alert["id"]
  ) => Promise<void>;
}

interface ApiModule {
  getAlerts?: AlertsApi["getAlerts"];
  getUserPriceAlerts?: AlertsApi["getAlerts"];
  listAlerts?: AlertsApi["listAlerts"];
  fetchAlerts?: AlertsApi["fetchAlerts"];

  createAlert?: AlertsApi["createAlert"];
  createPriceAlert?: AlertsApi["createAlert"];

  updateAlert?: AlertsApi["updateAlert"];

  deleteAlert?: AlertsApi["deleteAlert"];
  cancelUserAlert?: AlertsApi["deleteAlert"];
  removeAlert?: AlertsApi["deleteAlert"];
}

async function loadAlertsApi(): Promise<AlertsApi | null> {
  try {
    const module = (await import("../lib/api")) as ApiModule;

    const api: AlertsApi = {
      getAlerts:
        module.getAlerts ??
        module.getUserPriceAlerts ??
        module.listAlerts ??
        module.fetchAlerts,

      listAlerts: module.listAlerts,

      fetchAlerts: module.fetchAlerts,

      createAlert:
        module.createAlert ??
        module.createPriceAlert,

      updateAlert: module.updateAlert,

      deleteAlert:
        module.deleteAlert ??
        module.cancelUserAlert ??
        module.removeAlert,
    };

    const hasAlertMethod =
      Boolean(api.getAlerts) ||
      Boolean(api.listAlerts) ||
      Boolean(api.fetchAlerts) ||
      Boolean(api.createAlert) ||
      Boolean(api.updateAlert) ||
      Boolean(api.deleteAlert);

    return hasAlertMethod ? api : null;
  } catch {
    return null;
  }
}

function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  ) {
    return error.message;
  }

  return fallback;
}

function extractAlertId(
  result: { id: Alert["id"] } | Alert
): Alert["id"] | undefined {
  if (
    typeof result === "object" &&
    result !== null &&
    "id" in result
  ) {
    return result.id;
  }

  return undefined;
}

function normalizeAlerts(
  value: unknown
): Alert[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (item): item is Alert =>
      typeof item === "object" &&
      item !== null &&
      "id" in item &&
      "symbol" in item &&
      "target_price" in item &&
      "condition" in item
  );
}

export function useAlerts(
  options: UseAlertsOptions = {}
): UseAlertsReturn {
  const {
    autoLoad = true,
  } = options;

  const [alerts, setAlerts] =
    useState<Alert[]>([]);

  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const mountedRef =
    useRef(true);

  const apiRef =
    useRef<AlertsApi | null>(null);

  const requestIdRef =
    useRef(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const getApi = useCallback(
    async (): Promise<AlertsApi | null> => {
      if (apiRef.current) {
        return apiRef.current;
      }

      const api =
        await loadAlertsApi();

      if (
        api &&
        mountedRef.current
      ) {
        apiRef.current = api;
      }

      return api;
    },
    []
  );

  const refresh = useCallback(
    async () => {
      const requestId =
        ++requestIdRef.current;

      if (mountedRef.current) {
        setIsLoading(true);
        setError(null);
      }

      try {
        const api =
          await getApi();

        if (!api) {
          const message =
            "Alerts API is not connected.";

          if (
            requestId ===
              requestIdRef.current &&
            mountedRef.current
          ) {
            setAlerts([]);
            setError(message);
          }

          return;
        }

        let fetched: Alert[] | null =
          null;

        if (api.getAlerts) {
          fetched =
            await api.getAlerts();
        } else if (api.listAlerts) {
          fetched =
            await api.listAlerts();
        } else if (api.fetchAlerts) {
          fetched =
            await api.fetchAlerts();
        } else {
          throw new Error(
            "Alerts list API is not connected."
          );
        }

        if (
          requestId !==
            requestIdRef.current ||
          !mountedRef.current
        ) {
          return;
        }

        setAlerts(
          normalizeAlerts(fetched)
        );
      } catch (error) {
        if (
          requestId !==
            requestIdRef.current ||
          !mountedRef.current
        ) {
          return;
        }

        setError(
          getErrorMessage(
            error,
            "Failed to load alerts."
          )
        );
      } finally {
        if (
          requestId ===
            requestIdRef.current &&
          mountedRef.current
        ) {
          setIsLoading(false);
        }
      }
    },
    [getApi]
  );

  useEffect(() => {
    if (!autoLoad) {
      return;
    }

    void refresh();
  }, [
    autoLoad,
    refresh,
  ]);

  const createAlert =
    useCallback<
      UseAlertsReturn["createAlert"]
    >(
      async (payload) => {
        if (mountedRef.current) {
          setError(null);
        }

        const symbol =
          payload.symbol
            .trim()
            .toUpperCase();

        const targetPrice =
          Number(
            payload.target_price
          );

        if (!symbol) {
          const message =
            "Alert symbol is required.";

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }

        if (
          !Number.isFinite(
            targetPrice
          ) ||
          targetPrice <= 0
        ) {
          const message =
            "Target price must be greater than zero.";

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }

        try {
          const api =
            await getApi();

          if (!api?.createAlert) {
            const message =
              "Alert creation API is not connected.";

            if (mountedRef.current) {
              setError(message);
            }

            return {
              success: false,
              error: message,
            };
          }

          const result =
            await api.createAlert({
              ...payload,
              symbol,
              target_price:
                targetPrice,
            });

          const id =
            extractAlertId(result);

          await refresh();

          return {
            success: true,
            id,
          };
        } catch (error) {
          const message =
            getErrorMessage(
              error,
              "Failed to create alert."
            );

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }
      },
      [getApi, refresh]
    );

  const updateAlert =
    useCallback<
      UseAlertsReturn["updateAlert"]
    >(
      async (id, payload) => {
        if (mountedRef.current) {
          setError(null);
        }

        try {
          const api =
            await getApi();

          if (!api?.updateAlert) {
            const message =
              "Alert update API is not connected.";

            if (mountedRef.current) {
              setError(message);
            }

            return {
              success: false,
              error: message,
            };
          }

          const cleanedPayload = {
            ...payload,
            ...(payload.symbol !== undefined
              ? {
                  symbol:
                    payload.symbol
                      .trim()
                      .toUpperCase(),
                }
              : {}),
          };

          if (
            cleanedPayload.target_price !==
              undefined &&
            (!Number.isFinite(
              Number(
                cleanedPayload.target_price
              )
            ) ||
              Number(
                cleanedPayload.target_price
              ) <= 0)
          ) {
            const message =
              "Target price must be greater than zero.";

            if (mountedRef.current) {
              setError(message);
            }

            return {
              success: false,
              error: message,
            };
          }

          await api.updateAlert(
            id,
            cleanedPayload
          );

          await refresh();

          return {
            success: true,
          };
        } catch (error) {
          const message =
            getErrorMessage(
              error,
              "Failed to update alert."
            );

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }
      },
      [getApi, refresh]
    );

  const deleteAlert =
    useCallback<
      UseAlertsReturn["deleteAlert"]
    >(
      async (id) => {
        if (mountedRef.current) {
          setError(null);
        }

        try {
          const api =
            await getApi();

          if (!api?.deleteAlert) {
            const message =
              "Alert deletion API is not connected.";

            if (mountedRef.current) {
              setError(message);
            }

            return {
              success: false,
              error: message,
            };
          }

          await api.deleteAlert(id);

          await refresh();

          return {
            success: true,
          };
        } catch (error) {
          const message =
            getErrorMessage(
              error,
              "Failed to delete alert."
            );

          if (mountedRef.current) {
            setError(message);
          }

          return {
            success: false,
            error: message,
          };
        }
      },
      [getApi, refresh]
    );

  return {
    alerts,
    isLoading,
    error,
    refresh,
    createAlert,
    updateAlert,
    deleteAlert,
  };
}

export default useAlerts;
