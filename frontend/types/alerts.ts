// Fast/frontend/types/alerts.ts
// Alert data contracts for KING ZARRY AI web frontend.
// Types only, no React, logic, API calls, or side effects.

/**
 * Condition under which an alert triggers.
 */
export type AlertCondition =
  | "ABOVE"
  | "BELOW"
  | "REACHES";

/**
 * Derived UI status.
 * This is not a persisted database field.
 */
export type AlertStatus =
  | "active"
  | "triggered"
  | "inactive";

/**
 * Primary alert data structure.
 *
 * Snake_case field names are preserved for compatibility
 * with the current alert data model.
 */
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

/**
 * Payload used when creating an alert.
 */
export interface CreateAlertPayload {
  symbol: string;
  target_price: number;
  condition: AlertCondition;
}

/**
 * Fields currently editable by the frontend.
 */
export type UpdateAlertPayload = Partial<
  Pick<
    Alert,
    "symbol" |
    "target_price" |
    "condition" |
    "active"
  >
>;

/**
 * Generic alert collection response shape.
 *
 * Optional summary fields are included only when supplied
 * by the connected API.
 */
export interface AlertsResponse {
  alerts: Alert[];
  total_alerts?: number;
  active_alerts?: number;
  triggered_alerts?: number;
  success?: boolean;
}

/**
 * Single-alert response shape.
 */
export interface AlertResponse {
  alert: Alert;
  success?: boolean;
  id?: number | string;
}

/**
 * Local form state.
 *
 * target_price remains a string because form inputs are
 * represented as text until validated and submitted.
 */
export interface AlertFormState {
  symbol: string;
  target_price: string;
  condition: AlertCondition;
}

/**
 * Alert item with optional UI-derived status.
 */
export interface AlertListItem extends Alert {
  status?: AlertStatus;
}
