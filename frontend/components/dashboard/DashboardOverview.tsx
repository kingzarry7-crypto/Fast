import React from "react";

export interface DashboardOverviewProps {
  userName?: string;
  systemStatus?: string;
  activeModulesCount?: number;
  totalConversations?: number;
  savedMemories?: number;
  activeAgents?: number;
  recentActivity?: Array<{
    id: string | number;
    title: string;
    timestamp?: string;
    type?: string;
    status?: string;
  }>;
  marketData?: Array<{
    symbol: string;
    name: string;
    price?: string | number;
    change?: string | number;
  }>;
  onNavigate?: (view: string) => void;
  className?: string;
}

export function DashboardOverview({
  userName = "KING ZARRY",
  systemStatus = "ONLINE",
  activeModulesCount,
  totalConversations,
  savedMemories,
  activeAgents,
  recentActivity = [],
  marketData = [],
  onNavigate,
  className = "",
}: DashboardOverviewProps) {
  const isOnline = systemStatus.toUpperCase() === "ONLINE" || systemStatus.toUpperCase() === "ACTIVE";

  const capabilities = [
    { name: "AI CORE", desc: "Neural processing & chat", view: "chat" },
    { name: "VISION", desc: "Image analysis & Qwen models", view: "vision" },
    { name: "VOICE", desc: "ElevenLabs & audio module", view: "voice" },
    { name: "MEMORY", desc: "Stored knowledge & context", view: "memory" },
    { name: "REASONING", desc: "Advanced logic & synthesis", view: "reasoning" },
    { name: "AGENTS", desc: "Autonomous task executors", view: "agents" },
    { name: "TOOLS", desc: "Integrated utility suite", view: "tools" },
    { name: "MARKETS", desc: "Gold & BTC analytics", view: "markets" },
    { name: "SIGNALS", desc: "Technical alerts & indicators", view: "signals" },
    { name: "NEWS", desc: "Intelligence feeds", view: "news" },
  ];

  return (
    <div
      className={`kz-panel kz-bracket relative p-6 md:p-8 bg-black/75 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_40px_rgba(6,182,212,0.15)] rounded-lg overflow-hidden space-y-8 ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* AI System Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-cyan-500/20">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
              NEXUS INTELLIGENCE CORE
            </span>
            <span className="text-cyan-500/40">/</span>
            <span className="text-[10px] font-mono text-cyan-300 uppercase">
              COMMAND OVERVIEW
            </span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-white tracking-wide flex items-center gap-3">
            WELCOME BACK, <span className="text-cyan-400">{userName}</span>
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3.5 py-1.5 bg-cyan-950/60 border border-cyan-500/30 rounded text-xs font-mono text-cyan-300">
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline
                  ? "bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]"
                  : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
            <span className="uppercase font-bold tracking-wider">
              SYSTEM {systemStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Central Holographic AI Core Spotlight */}
      <div className="relative p-6 md:p-8 bg-black/50 border border-cyan-500/25 rounded-xl overflow-hidden flex flex-col items-center text-center">
        <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 via-transparent to-transparent pointer-events-none" aria-hidden="true" />
        <div className="absolute -right-16 -top-16 w-48 h-48 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" aria-hidden="true" />

        <div className="relative flex items-center justify-center w-20 h-20 rounded-full bg-cyan-500/10 border border-cyan-500/40 shadow-[0_0_30px_rgba(6,182,212,0.25)] mb-4 group">
          <div className="absolute inset-0 rounded-full border border-cyan-400/40 animate-spin opacity-60 pointer-events-none" aria-hidden="true" />
          <span className="w-3 h-3 rounded-full bg-cyan-400 animate-ping absolute" aria-hidden="true" />
          <span className="text-xl font-mono font-bold text-cyan-300">KZ</span>
        </div>

        <h2 className="text-base font-bold text-white tracking-wider mb-2">
          ONE AI CORE → MANY INTELLIGENCE CAPABILITIES
        </h2>
        <p className="text-xs font-mono text-cyan-400/80 max-w-xl leading-relaxed mb-6">
          Personal intelligence nexus active across neural communication channels, analytical tools, vision systems, and market tracking modules.
        </p>

        {/* Intelligence Capability Matrix Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 w-full">
          {capabilities.map((cap, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onNavigate && onNavigate(cap.view)}
              className="p-3 text-left bg-black/40 hover:bg-cyan-500/15 border border-cyan-500/20 hover:border-cyan-400 rounded transition-all group"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono font-bold text-cyan-300 group-hover:text-white transition-colors">
                  {cap.name}
                </span>
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500/60 group-hover:bg-cyan-400 transition-colors" aria-hidden="true" />
              </div>
              <p className="text-[9px] font-mono text-cyan-400/60 line-clamp-1">
                {cap.desc}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Intelligence Snapshot / Metrics if available */}
      {(totalConversations !== undefined || savedMemories !== undefined || activeAgents !== undefined || activeModulesCount !== undefined) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {totalConversations !== undefined && (
            <div className="p-4 bg-black/40 border border-cyan-500/20 rounded-lg">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                TOTAL CONVERSATIONS
              </span>
              <span className="text-lg font-mono font-bold text-white">
                {totalConversations}
              </span>
            </div>
          )}

          {savedMemories !== undefined && (
            <div className="p-4 bg-black/40 border border-cyan-500/20 rounded-lg">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                STORED MEMORIES
              </span>
              <span className="text-lg font-mono font-bold text-white">
                {savedMemories}
              </span>
            </div>
          )}

          {activeAgents !== undefined && (
            <div className="p-4 bg-black/40 border border-cyan-500/20 rounded-lg">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                ACTIVE AGENTS
              </span>
              <span className="text-lg font-mono font-bold text-white">
                {activeAgents}
              </span>
            </div>
          )}

          {activeModulesCount !== undefined && (
            <div className="p-4 bg-black/40 border border-cyan-500/20 rounded-lg">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                SYSTEM MODULES
              </span>
              <span className="text-lg font-mono font-bold text-white">
                {activeModulesCount}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Two-Column Detail Section: AI Activity & Market Intelligence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AI Activity Stream */}
        <div className="p-5 bg-black/50 border border-cyan-500/20 rounded-lg flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-cyan-500/15">
            <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest">
              AI ACTIVITY STREAM
            </h3>
            <span className="text-[10px] font-mono text-cyan-400/60 uppercase">
              REAL-TIME LOG
            </span>
          </div>

          {recentActivity && recentActivity.length > 0 ? (
            <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-1">
              {recentActivity.map((item) => (
                <div
                  key={item.id}
                  className="p-3 bg-black/40 border border-cyan-500/15 rounded flex items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <p className="text-xs font-mono text-white font-medium">
                      {item.title}
                    </p>
                    {item.timestamp && (
                      <span className="text-[10px] font-mono text-cyan-400/60 block">
                        {item.timestamp}
                      </span>
                    )}
                  </div>
                  {item.status && (
                    <span className="px-2 py-0.5 bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 rounded text-[9px] font-mono uppercase shrink-0">
                      {item.status}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="h-40 flex flex-col items-center justify-center text-center p-6 space-y-2 my-auto">
              <span className="w-2 h-2 rounded-full bg-cyan-400/50 animate-pulse" aria-hidden="true" />
              <p className="text-xs font-mono text-cyan-400/70">
                NO RECENT INTELLIGENCE EVENTS
              </p>
              <p className="text-[10px] font-mono text-cyan-400/40">
                The system is ready for your next command.
              </p>
            </div>
          )}
        </div>

        {/* Market Intelligence Module */}
        <div className="p-5 bg-black/50 border border-cyan-500/20 rounded-lg flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-cyan-500/15">
            <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest">
              MARKET INTELLIGENCE // ASSETS
            </h3>
            <span className="text-[10px] font-mono text-cyan-400/60 uppercase">
              GOLD &amp; CRYPTO
            </span>
          </div>

          {marketData && marketData.length > 0 ? (
            <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-1">
              {marketData.map((market, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-black/40 border border-cyan-500/15 rounded flex items-center justify-between gap-3"
                >
                  <div>
                    <span className="text-xs font-mono font-bold text-white">
                      {market.symbol}
                    </span>
                    <span className="text-[10px] font-mono text-cyan-400/70 block">
                      {market.name}
                    </span>
                  </div>

                  <div className="text-right">
                    {market.price !== undefined && (
                      <span className="text-xs font-mono text-cyan-200 font-bold block">
                        {market.price}
                      </span>
                    )}
                    {market.change !== undefined && (
                      <span className="text-[10px] font-mono text-cyan-400 block">
                        {market.change}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-40 flex flex-col items-center justify-center text-center p-6 space-y-2 my-auto">
              <span className="w-2 h-2 rounded-full bg-cyan-400/50 animate-pulse" aria-hidden="true" />
              <p className="text-xs font-mono text-cyan-400/70">
                MARKET INTELLIGENCE STANDBY
              </p>
              <p className="text-[10px] font-mono text-cyan-400/40">
                Tracking XAU/USD and BTC/USD analytics streams.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
