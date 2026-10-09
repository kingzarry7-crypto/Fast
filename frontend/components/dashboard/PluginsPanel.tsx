"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

type PluginTool = {
  name: string;
  provider: string;
  description: string;
  risk?: string;
  available?: boolean;
  connection_status?: string;
  parameters?: { properties?: Record<string, { type?: string; description?: string; minimum?: number; maximum?: number }> };
};

type PluginResponse = {
  status?: string;
  plugin_system?: string;
  connection_status_note?: string;
  tools?: PluginTool[];
  providers?: Record<string, { connected?: boolean }>;
  detail?: string;
};

const providerLabel: Record<string, string> = {
  github: "GitHub",
  google: "Google Workspace",
  shopify: "Shopify",
};

function statusLabel(tool: PluginTool) {
  if (tool.connection_status === "linked_unverified") return "LINKED · TEST REQUIRED";
  if (tool.connection_status === "not_configured") return "SERVER SETUP REQUIRED";
  if (tool.connection_status === "disconnected") return "NOT CONNECTED";
  return tool.available ? "AVAILABLE" : "UNAVAILABLE";
}

export default function PluginsPanel() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<PluginResponse | null>(null);
  const [error, setError] = useState("");

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/plugins", {
        credentials: "include",
        cache: "no-store",
      });
      const raw = await response.text();
      let result: PluginResponse;
      try { result = JSON.parse(raw) as PluginResponse; }
      catch { throw new Error(`Server returned an invalid response (HTTP ${response.status}).`); }
      if (!response.ok) {
        throw new Error(result.detail || (response.status === 401
          ? "Please sign in again to view your plugins."
          : `Could not load plugins (HTTP ${response.status}).`));
      }
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load plugins.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && !data && !loading && !error) void loadPlugins();
  }, [open, data, loading, error, loadPlugins]);

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className={"rounded-md border px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest transition shrink-0 " +
          (open ? "border-cyan-300/60 bg-cyan-400/15 text-cyan-100" : "border-cyan-400/35 bg-cyan-400/5 text-cyan-200 hover:bg-cyan-400/15")}
      >
        ◈ PLUGINS
      </button>

      {open && (
        <>
          <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close plugins panel" onClick={() => setOpen(false)} />
          <section className="absolute right-0 top-full z-50 mt-2 w-[min(92vw,460px)] max-h-[min(76vh,680px)] overflow-y-auto rounded-xl border border-cyan-400/25 bg-[#050b15] p-4 shadow-[0_20px_70px_rgba(0,0,0,0.65)]">
            <div className="flex items-start justify-between gap-3 border-b border-cyan-500/15 pb-3">
              <div>
                <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/55">KING ZARRY AI · EXTENSIONS</p>
                <h2 className="mt-1 text-base font-semibold tracking-wide text-white">Plugin Registry</h2>
                <p className="mt-1 text-xs text-zinc-400">Read-only tools available to the AI for your linked accounts.</p>
              </div>
              <button type="button" onClick={() => void loadPlugins()} disabled={loading} className="rounded-md border border-cyan-500/25 px-2.5 py-1.5 font-mono-tech text-[9px] tracking-widest text-cyan-200 disabled:opacity-50">
                {loading ? "LOADING…" : "REFRESH"}
              </button>
            </div>

            {loading && !data && <p className="py-6 text-center text-xs text-cyan-100/60">Loading registered plugins…</p>}
            {error && <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/5 p-3 text-xs leading-relaxed text-amber-100">{error}<button type="button" onClick={() => void loadPlugins()} className="ml-2 underline">Retry</button></div>}

            {data && (
              <>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {Object.entries(data.providers || {}).map(([provider, state]) => (
                    <div key={provider} className="rounded-lg border border-white/10 bg-white/[0.025] p-2">
                      <div className="text-xs font-medium text-white">{providerLabel[provider] || provider}</div>
                      <div className={"mt-1 text-[9px] tracking-wider " + (state.connected ? "text-cyan-300" : "text-zinc-500")}>
                        {state.connected ? "LINKED" : "NOT LINKED"}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 space-y-2">
                  {(data.tools || []).map((tool) => (
                    <article key={tool.name} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="break-all text-xs font-semibold text-white">{tool.name}</div>
                          <div className="mt-1 text-[11px] leading-relaxed text-zinc-400">{tool.description}</div>
                        </div>
                        <span className={"shrink-0 rounded border px-2 py-1 text-[8px] tracking-wider " +
                          (tool.available ? "border-cyan-400/25 text-cyan-200" : tool.connection_status === "linked_unverified" ? "border-amber-400/25 text-amber-200" : "border-white/10 text-zinc-500")}>
                          {statusLabel(tool)}
                        </span>
                      </div>
                      <div className="mt-2 text-[9px] uppercase tracking-widest text-zinc-600">
                        {providerLabel[tool.provider] || tool.provider} · {tool.risk || "read_only"}
                      </div>
                    </article>
                  ))}
                  {!loading && !(data.tools || []).length && <p className="py-4 text-center text-xs text-zinc-500">No registered plugins were returned by the server.</p>}
                </div>
                <Link href="/plugins" className="mt-3 flex items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-2.5 text-xs font-semibold text-cyan-100 hover:bg-cyan-400/20">
                  CONNECT / MANAGE PLUGINS →
                </Link>
                <p className="mt-3 rounded-lg border border-amber-400/15 bg-amber-400/[0.035] p-3 text-[10px] leading-relaxed text-amber-100/65">
                  {data.connection_status_note || "A linked record alone does not prove the provider is authorized. Verify a real tool request before relying on its data."}
                </p>
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
