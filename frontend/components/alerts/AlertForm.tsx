"use client";
import { useState, type FormEvent } from "react";
import type {
  AlertSeverity,
  AlertType,
} from "./AlertCard";
export interface AlertFormData {
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description: string;
  asset: string;
  timeframe: string;
  confidence: string;
  source: string;
  agent: string;
  signal: string;
}
export interface AlertFormProps {
  initialValues?: Partial<AlertFormData>;
  submitLabel?: string;
  onSubmit?: (data: AlertFormData) => void | Promise<void>;
  onCancel?: () => void;
  className?: string;
}
const DEFAULT_FORM: AlertFormData = {
  type: "MARKET",
  severity: "INFO",
  title: "",
  description: "",
  asset: "",
  timeframe: "",
  confidence: "",
  source: "",
  agent: "",
  signal: "",
};
const ALERT_TYPES: AlertType[] = [
  "MARKET",
  "AI",
  "NEWS",
  "SYSTEM",
  "AGENT",
  "SECURITY",
];
const ALERT_SEVERITIES: AlertSeverity[] = [
  "INFO",
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];
export function AlertForm({
  initialValues,
  submitLabel = "CREATE ALERT",
  onSubmit,
  onCancel,
  className = "",
}: AlertFormProps) {
  const [form, setForm] = useState<AlertFormData>({
    ...DEFAULT_FORM,
    ...initialValues,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  function updateField<K extends keyof AlertFormData>(
    field: K,
    value: AlertFormData[K]
  ) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
    if (error) {
      setError("");
    }
  }
  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();
    const title = form.title.trim();
    const description = form.description.trim();
    if (!title) {
      setError("Alert title is required.");
      return;
    }
    if (!description) {
      setError("Alert description is required.");
      return;
    }
    const cleanedData: AlertFormData = {
      ...form,
      title,
      description,
      asset: form.asset.trim(),
      timeframe: form.timeframe.trim(),
      confidence: form.confidence.trim(),
      source: form.source.trim(),
      agent: form.agent.trim(),
      signal: form.signal.trim(),
    };
    try {
      setSaving(true);
      setError("");
      await onSubmit?.(cleanedData);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Unable to create the alert."
      );
    } finally {
      setSaving(false);
    }
  }
  function handleReset() {
    setForm({
      ...DEFAULT_FORM,
      ...initialValues,
    });
    setError("");
  }
  const inputClass =
    "w-full rounded-sm border border-cyan-500/25 bg-black/30 px-3 py-2.5 text-sm text-cyan-50 outline-none transition focus:border-cyan-400/70 focus:ring-1 focus:ring-cyan-400/20";
  const labelClass =
    "mb-1.5 block text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400/70";
  return (
    <form
      onSubmit={handleSubmit}
      className={`kz-panel kz-bracket relative p-5 ${className}`}
    >
      {/* HUD CORNERS */}
      <div
        className="kz-hud-corner kz-hud-corner-tl"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-tr"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-bl"
        aria-hidden="true"
      />
      <div
        className="kz-hud-corner kz-hud-corner-br"
        aria-hidden="true"
      />
      {/* HEADER */}
      <div className="mb-5 border-b border-cyan-500/15 pb-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="kz-hud-label text-cyan-300">
              ALERT CONTROL
            </div>
            <h2 className="mt-1 text-lg font-bold tracking-wide text-white">
              CREATE INTELLIGENCE ALERT
            </h2>
          </div>
          <div className="hidden sm:block">
            <span className="rounded-sm border border-cyan-500/20 bg-cyan-500/5 px-2 py-1 text-[9px] font-mono uppercase tracking-widest text-cyan-400/70">
              LOCAL FORM
            </span>
          </div>
        </div>
      </div>
      {/* ERROR */}
      {error && (
        <div
          role="alert"
          className="mb-4 rounded-sm border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-xs font-mono text-red-300"
        >
          {error}
        </div>
      )}
      {/* TYPE + SEVERITY */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="alert-type"
            className={labelClass}
          >
            Alert Type
          </label>
          <select
            id="alert-type"
            value={form.type}
            onChange={(event) =>
              updateField(
                "type",
                event.target.value as AlertType
              )
            }
            disabled={saving}
            className={inputClass}
          >
            {ALERT_TYPES.map((type) => (
              <option
                key={type}
                value={type}
                className="bg-slate-950"
              >
                {type}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label
            htmlFor="alert-severity"
            className={labelClass}
          >
            Severity
          </label>
          <select
            id="alert-severity"
            value={form.severity}
            onChange={(event) =>
              updateField(
                "severity",
                event.target.value as AlertSeverity
              )
            }
            disabled={saving}
            className={inputClass}
          >
            {ALERT_SEVERITIES.map((severity) => (
              <option
                key={severity}
                value={severity}
                className="bg-slate-950"
              >
                {severity}
              </option>
            ))}
          </select>
        </div>
      </div>
      {/* TITLE */}
      <div className="mt-4">
        <label
          htmlFor="alert-title"
          className={labelClass}
        >
          Title
        </label>
        <input
          id="alert-title"
          type="text"
          value={form.title}
          onChange={(event) =>
            updateField("title", event.target.value)
          }
          disabled={saving}
          maxLength={160}
          placeholder="Enter alert title..."
          className={inputClass}
        />
      </div>
      {/* DESCRIPTION */}
      <div className="mt-4">
        <label
          htmlFor="alert-description"
          className={labelClass}
        >
          Description
        </label>
        <textarea
          id="alert-description"
          value={form.description}
          onChange={(event) =>
            updateField(
              "description",
              event.target.value
            )
          }
          disabled={saving}
          rows={4}
          maxLength={2000}
          placeholder="Describe the intelligence event..."
          className={`${inputClass} resize-y`}
        />
      </div>
      {/* MARKET DATA */}
      <div className="mt-5">
        <div className="mb-3 text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400/70">
          INTELLIGENCE METADATA
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="alert-asset"
              className={labelClass}
            >
              Asset
            </label>
            <input
              id="alert-asset"
              type="text"
              value={form.asset}
              onChange={(event) =>
                updateField(
                  "asset",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="BTC/USD"
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="alert-timeframe"
              className={labelClass}
            >
              Timeframe
            </label>
            <input
              id="alert-timeframe"
              type="text"
              value={form.timeframe}
              onChange={(event) =>
                updateField(
                  "timeframe",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="15M"
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="alert-confidence"
              className={labelClass}
            >
              Confidence
            </label>
            <input
              id="alert-confidence"
              type="text"
              value={form.confidence}
              onChange={(event) =>
                updateField(
                  "confidence",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="HIGH"
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="alert-signal"
              className={labelClass}
            >
              Signal
            </label>
            <input
              id="alert-signal"
              type="text"
              value={form.signal}
              onChange={(event) =>
                updateField(
                  "signal",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="BUY"
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="alert-source"
              className={labelClass}
            >
              Source
            </label>
            <input
              id="alert-source"
              type="text"
              value={form.source}
              onChange={(event) =>
                updateField(
                  "source",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="Signal Engine"
              className={inputClass}
            />
          </div>
          <div>
            <label
              htmlFor="alert-agent"
              className={labelClass}
            >
              Agent
            </label>
            <input
              id="alert-agent"
              type="text"
              value={form.agent}
              onChange={(event) =>
                updateField(
                  "agent",
                  event.target.value
                )
              }
              disabled={saving}
              placeholder="KZ Trading Agent"
              className={inputClass}
            />
          </div>
        </div>
      </div>
      {/* ACTIONS */}
      <div className="mt-6 flex flex-col-reverse gap-2 border-t border-cyan-500/15 pt-4 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={handleReset}
          disabled={saving}
          className="kz-button px-4 py-2 text-[11px]"
        >
          RESET
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="kz-button px-4 py-2 text-[11px]"
          >
            CANCEL
          </button>
        )}
        <button
          type="submit"
          disabled={saving}
          className="kz-button kz-button-primary px-5 py-2 text-[11px]"
        >
          {saving ? "CREATING..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
export default AlertForm;
