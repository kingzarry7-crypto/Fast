import React, { useState } from "react";
import Link from "next/link";

export interface NavItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
}

export interface MobileNavProps {
  currentPath?: string;
  navItems?: NavItem[];
  systemStatus?: string;
  isOpen?: boolean;
  onClose?: () => void;
  className?: string;
}

export function MobileNav({
  currentPath = "/dashboard",
  navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Chat", href: "/chat" },
    { label: "Markets", href: "/markets" },
    { label: "Signals", href: "/signals" },
    { label: "Tools", href: "/tools" },
  ],
  systemStatus = "ONLINE",
  isOpen = false,
  onClose,
  className = "",
}: MobileNavProps) {
  const [drawerOpen, setDrawerOpen] = useState(isOpen);

  // Synchronize internal state with prop if controlled
  const isDrawerActive = isOpen !== undefined ? isOpen : drawerOpen;
  const handleClose = () => {
    if (onClose) onClose();
    setDrawerOpen(false);
  };

  const isOnline =
    systemStatus.toUpperCase() === "ONLINE" ||
    systemStatus.toUpperCase() === "ACTIVE" ||
    systemStatus.toUpperCase() === "LIVE";

  return (
    <>
      {/* Mobile Bottom Dock (Fixed Holographic Command Bar) */}
      <nav
        className={`md:hidden fixed bottom-0 left-0 right-0 z-50 bg-black/85 backdrop-blur-2xl border-t border-cyan-500/30 shadow-[0_-4px_30px_rgba(6,182,212,0.15)] px-2 py-2 pb-safe transition-all ${className}`}
        aria-label="Mobile Navigation"
      >
        {/* Subtle scanline top border */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent" aria-hidden="true" />

        <div className="flex items-center justify-around gap-1">
          {navItems.slice(0, 5).map((item) => {
            const isActive =
              currentPath === item.href ||
              currentPath.toLowerCase() === item.href.toLowerCase();
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center justify-center py-1.5 px-2 rounded-xl transition-all relative group min-w-[60px] ${
                  isActive
                    ? "bg-cyan-500/20 border border-cyan-400/50 text-white shadow-[0_0_15px_rgba(6,182,212,0.3)]"
                    : "bg-black/40 border border-transparent text-cyan-400/70 hover:text-cyan-200 hover:bg-cyan-500/10"
                }`}
              >
                {isActive && (
                  <span className="absolute -top-1 w-6 h-[2px] bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.9)] rounded-full" aria-hidden="true" />
                )}
                {/* Icon or Fallback Indicator */}
                <div className="w-5 h-5 flex items-center justify-center mb-1">
                  {item.icon ? (
                    item.icon
                  ) : (
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isActive
                          ? "bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)] animate-pulse"
                          : "bg-cyan-500/40"
                      }`}
                      aria-hidden="true"
                    />
                  )}
                </div>
                <span className="text-[10px] font-mono tracking-wider uppercase truncate max-w-[64px]">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Slide-out Holographic Navigation Drawer if triggered or supported */}
      {isDrawerActive && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-md transition-opacity animate-in fade-in duration-200"
            onClick={handleClose}
            aria-hidden="true"
          />

          {/* Drawer Content */}
          <div className="relative w-4/5 max-w-xs bg-black/95 border-r border-cyan-500/40 shadow-[10px_0_40px_rgba(6,182,212,0.2)] p-6 flex flex-col justify-between z-10 animate-in slide-in-from-left duration-300">
            {/* HUD Corner Accents */}
            <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-cyan-400" aria-hidden="true" />
            <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-cyan-400" aria-hidden="true" />
            <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-cyan-400" aria-hidden="true" />
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-cyan-400" aria-hidden="true" />

            <div>
              {/* Drawer Header */}
              <div className="flex items-center justify-between pb-4 mb-6 border-b border-cyan-500/25">
                <div className="flex items-center gap-3">
                  <div className="relative w-8 h-8 rounded-full bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.3)]">
                    <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.9)]" />
                  </div>
                  <div>
                    <span className="text-sm font-bold font-mono tracking-wider text-white block">
                      KING ZARRY AI
                    </span>
                    <span className="text-[9px] font-mono text-cyan-400/70 tracking-widest uppercase">
                      COMMAND DECK
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleClose}
                  className="p-1.5 bg-black/50 hover:bg-cyan-500/20 border border-cyan-500/30 rounded text-cyan-300 transition-colors"
                  aria-label="Close menu"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Navigation Links List */}
              <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-220px)] pr-1">
                {navItems.map((item) => {
                  const isActive =
                    currentPath === item.href ||
                    currentPath.toLowerCase() === item.href.toLowerCase();
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={handleClose}
                      className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-mono transition-all border ${
                        isActive
                          ? "bg-cyan-500/25 border-cyan-400 text-white font-bold shadow-[0_0_15px_rgba(6,182,212,0.25)]"
                          : "bg-black/40 border-cyan-500/15 text-cyan-300/80 hover:bg-cyan-500/10 hover:text-cyan-200"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isActive ? "bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.9)]" : "bg-cyan-500/40"
                        }`}
                        aria-hidden="true"
                      />
                      <span className="tracking-wider uppercase">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* System Status Footer */}
            <div className="pt-4 mt-4 border-t border-cyan-500/20 flex items-center justify-between">
              <span className="text-[10px] font-mono text-cyan-400/60 uppercase">SYSTEM STATUS</span>
              <div className="flex items-center gap-2 px-2.5 py-1 bg-cyan-950/60 border border-cyan-500/30 rounded text-[10px] font-mono text-cyan-300">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isOnline
                      ? "bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]"
                      : "bg-amber-400"
                  }`}
                  aria-hidden="true"
                />
                <span className="uppercase font-bold tracking-wider">{systemStatus}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
