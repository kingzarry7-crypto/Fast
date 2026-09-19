import React, { useState } from "react";
import Link from "next/link";

export interface NavItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
}

export interface SidebarProps {
  currentPath?: string;
  navItems?: NavItem[];
  userName?: string;
  userEmail?: string;
  userAvatar?: string;
  systemStatus?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onLogout?: () => void;
  className?: string;
}

export function Sidebar({
  currentPath = "/dashboard",
  navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Chat", href: "/chat" },
    { label: "Vision", href: "/vision" },
    { label: "Agents", href: "/agents" },
    { label: "Tools", href: "/tools" },
    { label: "Markets", href: "/markets" },
    { label: "Signals", href: "/signals" },
    { label: "News", href: "/news" },
    { label: "Alerts", href: "/alerts" },
    { label: "History", href: "/history" },
    { label: "Settings", href: "/settings" },
    { label: "Pricing", href: "/pricing" },
  ],
  userName = "King",
  userEmail,
  userAvatar,
  systemStatus = "ONLINE",
  collapsed = false,
  onToggleCollapse,
  onLogout,
  className = "",
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(collapsed);

  const handleToggle = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setIsCollapsed(!isCollapsed);
    }
  };

  const effectiveCollapsed = collapsed !== undefined && onToggleCollapse ? collapsed : isCollapsed;

  const isOnline =
    systemStatus.toUpperCase() === "ONLINE" ||
    systemStatus.toUpperCase() === "ACTIVE" ||
    systemStatus.toUpperCase() === "LIVE";

  return (
    <aside
      className={`hidden md:flex flex-col relative z-40 bg-black/90 backdrop-blur-2xl border-r border-cyan-500/30 shadow-[4px_0_40px_rgba(6,182,212,0.12)] transition-all duration-300 ${
        effectiveCollapsed ? "w-20" : "w-64"
      } ${className}`}
      aria-label="Sidebar Navigation"
    >
      {/* Subtle HUD scanline right border accent */}
      <div className="absolute top-0 right-0 bottom-0 w-[1px] bg-gradient-to-b from-transparent via-cyan-400/50 to-transparent pointer-events-none" aria-hidden="true" />
      <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-cyan-400/60 pointer-events-none" aria-hidden="true" />
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-cyan-400/60 pointer-events-none" aria-hidden="true" />

      {/* Brand Header */}
      <div className="p-4 border-b border-cyan-500/20 flex items-center justify-between relative bg-gradient-to-b from-cyan-950/20 to-transparent">
        <Link href="/dashboard" className="flex items-center gap-3 group focus:outline-none">
          {/* Cinematic AI Core Badge */}
          <div className="relative w-9 h-9 rounded-full bg-cyan-950/90 border border-cyan-500/50 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.35)] group-hover:border-cyan-400 transition-all shrink-0">
            <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-ping opacity-40 pointer-events-none" aria-hidden="true" />
            <div className="w-3.5 h-3.5 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,1)]" />
            <span className="absolute -bottom-1 -right-1 w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
          </div>

          {!effectiveCollapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-bold font-mono tracking-wider text-white group-hover:text-cyan-300 transition-colors truncate">
                KING ZARRY AI
              </span>
              <span className="text-[9px] font-mono text-cyan-400/70 tracking-widest uppercase truncate">
                INTELLIGENCE SYSTEM
              </span>
            </div>
          )}
        </Link>

        {onToggleCollapse && (
          <button
            type="button"
            onClick={handleToggle}
            className="p-1 bg-black/60 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors"
            aria-label="Toggle sidebar"
          >
            <svg className={`w-4 h-4 transition-transform ${effectiveCollapsed ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1.5 custom-scrollbar">
        {!effectiveCollapsed && (
          <div className="px-2 pb-1.5 text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]" />
            Command Modules
          </div>
        )}

        {navItems.map((item) => {
          const isActive =
            currentPath === item.href ||
            currentPath.toLowerCase() === item.href.toLowerCase();

          return (
            <Link
              key={item.href}
              href={item.href}
              title={effectiveCollapsed ? item.label : undefined}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-mono transition-all relative group border ${
                isActive
                  ? "bg-cyan-500/25 border-cyan-400 text-white font-bold shadow-[0_0_20px_rgba(6,182,212,0.3)] backdrop-blur-md"
                  : "bg-black/40 border-cyan-500/15 text-cyan-400/75 hover:bg-cyan-500/15 hover:text-cyan-200 hover:border-cyan-500/40"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-5 bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,1)] rounded-r" aria-hidden="true" />
              )}
              
              <div className="w-5 h-5 flex items-center justify-center shrink-0">
                {item.icon ? (
                  item.icon
                ) : (
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isActive ? "bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,1)] animate-pulse" : "bg-cyan-500/40 group-hover:bg-cyan-300"
                    }`}
                    aria-hidden="true"
                  />
                )}
              </div>

              {!effectiveCollapsed && (
                <span className="tracking-wider uppercase truncate">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer / System Status & User Profile */}
      <div className="p-3 border-t border-cyan-500/20 bg-black/80 space-y-3">
        {/* System Status HUD */}
        <div className={`flex items-center ${effectiveCollapsed ? "justify-center" : "justify-between"} px-2.5 py-2 bg-cyan-950/60 border border-cyan-500/30 rounded text-[10px] font-mono text-cyan-300 shadow-[inset_0_0_10px_rgba(6,182,212,0.1)]`}>
          {!effectiveCollapsed && <span className="text-cyan-400/70 uppercase font-bold tracking-wider">CORE STATUS</span>}
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline ? "bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,1)]" : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
            {!effectiveCollapsed && <span className="uppercase font-bold tracking-wider text-cyan-200">{systemStatus}</span>}
          </div>
        </div>

        {/* User Identity & Logout */}
        <div className={`flex items-center ${effectiveCollapsed ? "justify-center" : "justify-between"} gap-2`}>
          <div className="flex items-center gap-2 overflow-hidden">
            {userAvatar ? (
              <img src={userAvatar} alt={userName} className="w-7 h-7 rounded-full object-cover border border-cyan-400 shrink-0 shadow-[0_0_8px_rgba(6,182,212,0.4)]" />
            ) : (
              <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-400 flex items-center justify-center text-xs font-mono font-bold text-cyan-300 shrink-0 shadow-[0_0_8px_rgba(6,182,212,0.4)]">
                {userName.charAt(0).toUpperCase()}
              </div>
            )}
            {!effectiveCollapsed && (
              <div className="flex flex-col overflow-hidden">
                <span className="text-xs font-mono font-bold text-white truncate">{userName}</span>
                {userEmail && <span className="text-[9px] font-mono text-cyan-400/70 truncate">{userEmail}</span>}
              </div>
            )}
          </div>

          {onLogout && !effectiveCollapsed && (
            <button
              type="button"
              onClick={onLogout}
              title="Disconnect Session"
              className="p-1.5 bg-black/60 hover:bg-red-950/50 border border-cyan-500/30 hover:border-red-500/50 rounded text-cyan-300 hover:text-red-300 transition-colors shrink-0"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
