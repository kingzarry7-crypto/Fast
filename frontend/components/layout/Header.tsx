import React, { useState } from "react";
import Link from "next/link";

export interface HeaderProps {
  currentPath?: string;
  userName?: string;
  userEmail?: string;
  userAvatar?: string;
  systemStatus?: string;
  onOpenSettings?: () => void;
  onOpenNotifications?: () => void;
  onLogout?: () => void;
  className?: string;
}

export function Header({
  currentPath = "DASHBOARD",
  userName = "King",
  userEmail,
  userAvatar,
  systemStatus = "ONLINE",
  onOpenSettings,
  onOpenNotifications,
  onLogout,
  className = "",
}: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { label: "DASHBOARD", href: "/dashboard" },
    { label: "CHAT", href: "/chat" },
    { label: "MARKETS", href: "/markets" },
    { label: "SIGNALS", href: "/signals" },
    { label: "TOOLS", href: "/tools" },
  ];

  const isOnline = systemStatus.toUpperCase() === "ONLINE" || systemStatus.toUpperCase() === "ACTIVE" || systemStatus.toUpperCase() === "LIVE";

  return (
    <header
      className={`relative z-50 w-full bg-black/80 backdrop-blur-xl border-b border-cyan-500/25 shadow-[0_4px_30px_rgba(6,182,212,0.1)] px-4 md:px-8 py-3.5 transition-all ${className}`}
    >
      {/* Subtle scanline / glow top border */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-60" aria-hidden="true" />

      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Brand & AI Core Identifier */}
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="flex items-center gap-3 group focus:outline-none">
            {/* Cinematic AI Core Badge */}
            <div className="relative w-9 h-9 rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.3)] group-hover:border-cyan-400 transition-all">
              <div className="absolute inset-0 rounded-full border border-cyan-400/20 animate-ping opacity-40 pointer-events-none" aria-hidden="true" />
              <div className="w-3.5 h-3.5 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.9)]" />
              <span className="absolute -bottom-1 -right-1 w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-sm md:text-base font-bold font-mono tracking-wider text-white group-hover:text-cyan-300 transition-colors">
                  KING ZARRY AI
                </span>
                <span className="hidden sm:inline-block px-1.5 py-0.5 bg-cyan-950/60 border border-cyan-500/30 rounded text-[9px] font-mono text-cyan-300">
                  CORE v4.8
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400/70 tracking-widest uppercase">
                PERSONAL INTELLIGENCE
              </span>
            </div>
          </Link>

          {/* Desktop Context / Page Indicator */}
          <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-cyan-500/20">
            <span className="text-[10px] font-mono text-cyan-400/50 uppercase">CONTEXT:</span>
            <span className="px-2.5 py-0.5 bg-cyan-950/40 border border-cyan-500/25 rounded text-[10px] font-mono font-bold text-cyan-200 tracking-wider">
              {currentPath}
            </span>
          </div>
        </div>

        {/* Center Nav Items (Desktop) */}
        <nav className="hidden md:flex items-center gap-1 bg-black/40 border border-cyan-500/20 rounded-lg p-1">
          {navItems.map((item) => {
            const isActive = currentPath.toUpperCase() === item.label;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={`px-3.5 py-1.5 rounded text-xs font-mono transition-all ${
                  isActive
                    ? "bg-cyan-500/25 border border-cyan-400/50 text-white font-bold shadow-[0_0_15px_rgba(6,182,212,0.25)]"
                    : "text-cyan-400/70 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Actions & System Status HUD */}
        <div className="flex items-center gap-3">
          {/* System Status Indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-cyan-950/50 border border-cyan-500/25 rounded text-xs font-mono text-cyan-300">
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline
                  ? "bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]"
                  : "bg-amber-400"
              }`}
              aria-hidden="true"
            />
            <span className="uppercase font-bold tracking-wider text-[10px]">
              {systemStatus}
            </span>
          </div>

          {/* Notifications Action */}
          {onOpenNotifications && (
            <button
              type="button"
              onClick={onOpenNotifications}
              title="Notifications"
              className="p-2 bg-black/50 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors relative"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-cyan-400" aria-hidden="true" />
            </button>
          )}

          {/* Settings Action */}
          {onOpenSettings && (
            <button
              type="button"
              onClick={onOpenSettings}
              title="System Settings"
              className="p-2 bg-black/50 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          )}

          {/* User Account / Logout Control */}
          <div className="flex items-center gap-2 pl-2 border-l border-cyan-500/20">
            <div className="flex items-center gap-2 px-2.5 py-1 bg-black/60 border border-cyan-500/30 rounded">
              {userAvatar ? (
                <img src={userAvatar} alt={userName} className="w-5 h-5 rounded-full object-cover border border-cyan-400" />
              ) : (
                <div className="w-5 h-5 rounded-full bg-cyan-950 border border-cyan-400 flex items-center justify-center text-[10px] font-mono font-bold text-cyan-300">
                  {userName.charAt(0).toUpperCase()}
                </div>
              )}
              <span className="text-xs font-mono font-bold text-white hidden sm:inline">
                {userName}
              </span>
            </div>

            {onLogout && (
              <button
                type="button"
                onClick={onLogout}
                title="Disconnect Session"
                className="p-2 bg-black/50 hover:bg-red-950/40 border border-cyan-500/30 hover:border-red-500/40 rounded text-cyan-300 hover:text-red-300 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            )}
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 bg-black/50 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors"
            aria-label="Toggle navigation menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-3 pt-3 border-t border-cyan-500/20 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between px-3 py-1 bg-cyan-950/40 border border-cyan-500/20 rounded text-[10px] font-mono text-cyan-300 mb-2">
            <span>CONTEXT: {currentPath}</span>
            <span className="uppercase">{systemStatus}</span>
          </div>
          {navItems.map((item) => {
            const isActive = currentPath.toUpperCase() === item.label;
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block w-full px-3 py-2 rounded text-xs font-mono transition-all ${
                  isActive
                    ? "bg-cyan-500/25 border border-cyan-400 text-white font-bold"
                    : "bg-black/40 border border-cyan-500/15 text-cyan-300 hover:bg-cyan-500/10"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}
