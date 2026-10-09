"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";

type PluginTool = {
  name: string;
  provider: string;
  description: string;
  risk?: string;
  available?: boolean;
  connection_status?: string;
  parameters?: { properties?: Record<string, unknown> };
};
type PluginResponse = {
  status?: string;
  plugin_system?: string;
  connection_status_note?: string;
  tools?: PluginTool[];
  providers?: Record<string, { connected?: boolean }>;
  detail?: string;
};

const labels: Record<string, string> = {
  github: "GitHub",
  google: "Google Workspace",
  shopify: "Shopify",
};
function status(tool: PluginTool) {
  if (tool.connection_status === "linked_unverified") return "LINKED · TEST REQUIRED";
  if (tool.connection_status === "not_configured") return "SERVER SETUP REQUIRED";
  if (tool.connection_status === "disconnected") return "NOT CONNECTED";
  return tool.available ? "AVAILABLE" : "UNAVAILABLE";
}

export default function PluginsPage() {
  const [data, setData] = useState<PluginResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/plugins", { credentials: "include", cache: "no-store" });
      const raw = await response.text();
      let parsed: PluginResponse;
      try { parsed = JSON.parse(raw) as PluginResponse; }
      catch { throw new Error(`Plugin API returned a non-JSON response (HTTP ${response.status}).`); }
      if (!response.ok) {
        throw new Error(parsed.detail || (response.status === 401
          ? "Your session is not authenticated. Sign in again and reload this page."
          : `Could not load plugin status (HTTP ${response.status}).`));
      }
      setData(parsed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load plugin status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  return (
    <ProtectedRoute>
      <div className="min-h-full bg-[#05080f] p-4 text-white sm:p-6 lg:p-10">
        <div className="mx-auto max-w-5xl space-y-6">
          <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/55">KING ZARRY AI · EXTENSIONS</p>
              <h1 className="mt-2 font-display text-2xl font-bold tracking-wider sm:text-3xl">Plugin Registry</h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-cyan-100/60">
                View the tools the AI is allowed to use with your linked accounts. This page reports server status; it does not create or fake a connection.
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/settings" className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300 hover:bg-white/5">Settings</Link>
              <button type="button" onClick={() => void refresh()} disabled={loading} className="rounded-lg border border-cyan-400/35 bg-cyan-400/10 px-4 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-100 disabled:opacity-50">
                {loading ? "CHECKING…" : "REFRESH STATUS"}
              </button>
            </div>
          </header>

          {error && <section role="alert" className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4 text-sm text-amber-100">
            <p className="font-semibold">Plugin status could not be loaded</p>
            <p className="mt-1 break-words text-xs leading-relaxed">{error}</p>
            <p className="mt-2 text-xs text-amber-100/60">If this persists, the frontend route may be deployed before the Railway API route, or your session may not be reaching the backend.</p>
          </section>}

          {loading && !data && <div className="rounded-xl border border-cyan-500/15 p-8 text-center text-sm text-cyan-100/60">Checking the plugin registry…</div>}

          {data && <>
            <section className="grid gap-3 sm:grid-cols-3">
              {Object.entries(data.providers || {}).map(([provider, state]) => (
                <article key={provider} className="rounded-xl border border-cyan-500/20 bg-cyan-500/[0.035] p-4">
                  <p className="text-xs text-zinc-400">PROVIDER</p>
                  <h2 className="mt-2 text-lg font-semibold">{labels[provider] || provider}</h2>
                  <p className={"mt-2 text-[10px] font-mono-tech tracking-widest " + (state.connected ? "text-amber-200" : "text-zinc-500")}>
                    {state.connected ? "LINK RECORD FOUND · NOT VERIFIED" : "NOT LINKED"}
                  </p>
                </article>
              ))}
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-display text-sm font-bold tracking-widest text-cyan-100">REGISTERED TOOLS</h2>
                <span className="text-xs text-zinc-500">{data.tools?.length || 0} tools</span>
              </div>
              {(data.tools || []).map((tool) => (
                <article key={tool.name} className="rounded-xl border border-white/10 bg-white/[0.025] p-4 sm:p-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="break-all font-mono-tech text-sm text-white">{tool.name}</p>
                      <p className="mt-2 text-sm leading-relaxed text-zinc-400">{tool.description}</p>
                      <p className="mt-3 text-[10px] uppercase tracking-widest text-zinc-600">{labels[tool.provider] || tool.provider} · {tool.risk || "read_only"}</p>
                    </div>
                    <span className={"w-fit shrink-0 rounded-md border px-3 py-1.5 text-[10px] font-mono-tech tracking-wider " +
                      (tool.available ? "border-cyan-400/30 bg-cyan-400/5 text-cyan-100" : tool.connection_status === "linked_unverified" ? "border-amber-400/30 text-amber-200" : "border-white/10 text-zinc-500")}>
                      {status(tool)}
                    </span>
                  </div>
                </article>
              ))}
              {!loading && !(data.tools || []).length && <p className="rounded-xl border border-white/10 p-6 text-sm text-zinc-400">The API returned no registered tools.</p>}
            </section>
            <p className="rounded-xl border border-amber-400/15 bg-amber-400/[0.035] p-4 text-xs leading-relaxed text-amber-100/65">
              {data.connection_status_note || "A saved link is not proof of authorization. Verify a real tool request before relying on provider data."}
            </p>
          </>}
        </div>
      </div>
    </ProtectedRoute>
  );
}
