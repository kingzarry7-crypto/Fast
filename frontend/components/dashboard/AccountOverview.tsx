import React from "react";

export interface AccountOverviewProps {
  user?: {
    name?: string;
    email?: string;
    username?: string;
    avatarUrl?: string;
    role?: string;
    status?: string;
    membershipTier?: string;
    joinedDate?: string;
  };
  metrics?: {
    totalConversations?: number;
    savedMemories?: number;
    activeAgents?: number;
    tokensUsed?: string | number;
  };
  onManageAccount?: () => void;
  className?: string;
}

export function AccountOverview({
  user,
  metrics,
  onManageAccount,
  className = "",
}: AccountOverviewProps) {
  const displayName = user?.name || user?.username || user?.email || "KING ZARRY OPERATOR";
  const displayEmail = user?.email || user?.username || "operator@kingzarry.ai";
  const accountStatus = user?.status || "ACTIVE";
  const membershipTier = user?.membershipTier || "AI COMMAND CORE";
  const role = user?.role || "SYSTEM OPERATOR";

  const isSuspended = accountStatus.toUpperCase() === "SUSPENDED" || accountStatus.toUpperCase() === "INACTIVE";
  const isPending = accountStatus.toUpperCase() === "PENDING";

  return (
    <div
      className={`kz-panel kz-bracket relative p-6 bg-black/70 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_35px_rgba(6,182,212,0.15)] rounded-lg overflow-hidden transition-all duration-300 ${className}`}
    >
      {/* HUD Corner Accents */}
      <div className="kz-hud-corner kz-hud-corner-tl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-tr" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-bl" aria-hidden="true" />
      <div className="kz-hud-corner kz-hud-corner-br" aria-hidden="true" />

      {/* Top Header / System Badge */}
      <div className="flex items-center justify-between pb-4 mb-5 border-b border-cyan-500/20">
        <div className="flex items-center gap-2.5">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isSuspended
                ? "bg-red-400"
                : isPending
                ? "bg-amber-400 animate-pulse"
                : "bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]"
            }`}
            aria-hidden="true"
          />
          <h2 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-widest">
            ACCOUNT CORE // IDENTITY PROFILE
          </h2>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-cyan-950/60 border border-cyan-500/30 rounded text-[10px] font-mono text-cyan-300">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" aria-hidden="true" />
          <span className="uppercase">{accountStatus}</span>
        </div>
      </div>

      {/* Main Identity Info Section */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 mb-6">
        {/* Holographic Avatar Core */}
        <div className="relative flex items-center justify-center w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.2)] shrink-0 group">
          <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-spin opacity-40 pointer-events-none" aria-hidden="true" />
          {user?.avatarUrl ? (
            <img
              src={user.avatarUrl}
              alt={displayName}
              className="w-full h-full object-cover rounded-full"
            />
          ) : (
            <span className="text-lg font-mono font-bold text-cyan-300">
              {displayName.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-cyan-400 border-2 border-black animate-pulse" aria-hidden="true" />
        </div>

        {/* Identity Details */}
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg font-bold text-white tracking-wide">
              {displayName}
            </h1>
            <span className="px-2 py-0.5 bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 rounded text-[10px] font-mono uppercase">
              {role}
            </span>
          </div>
          <p className="text-xs font-mono text-cyan-400/70">
            {displayEmail}
          </p>
          {user?.joinedDate && (
            <p className="text-[10px] font-mono text-cyan-400/50 pt-1">
              INITIALIZED: {user.joinedDate}
            </p>
          )}
        </div>
      </div>

      {/* Membership & Access Tier */}
      <div className="p-4 mb-5 bg-black/50 border border-cyan-500/20 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-[10px] font-mono text-cyan-400/60 uppercase tracking-widest block mb-1">
            INTELLIGENCE ACCESS TIER
          </span>
          <span className="text-sm font-mono font-bold text-cyan-200 tracking-wider">
            {membershipTier}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-cyan-300">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" aria-hidden="true" />
          <span>NEURAL LINK SECURE</span>
        </div>
      </div>

      {/* Metrics Grid if available */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {metrics.totalConversations !== undefined && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                CONVERSATIONS
              </span>
              <span className="text-sm font-mono font-bold text-white">
                {metrics.totalConversations}
              </span>
            </div>
          )}

          {metrics.savedMemories !== undefined && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                MEMORIES
              </span>
              <span className="text-sm font-mono font-bold text-white">
                {metrics.savedMemories}
              </span>
            </div>
          )}

          {metrics.activeAgents !== undefined && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                ACTIVE AGENTS
              </span>
              <span className="text-sm font-mono font-bold text-white">
                {metrics.activeAgents}
              </span>
            </div>
          )}

          {metrics.tokensUsed !== undefined && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <span className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-wider block mb-1">
                TOKENS / USAGE
              </span>
              <span className="text-sm font-mono font-bold text-white">
                {metrics.tokensUsed}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Action Footer */}
      {onManageAccount && (
        <div className="pt-4 border-t border-cyan-500/20 flex justify-end">
          <button
            type="button"
            onClick={onManageAccount}
            className="kz-button kz-button-primary px-4 py-2 text-xs font-mono tracking-wider"
          >
            MANAGE ACCOUNT PROTOCOLS
          </button>
        </div>
      )}
    </div>
  );
}
