"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

const PUBLIC_ROUTES = ["/", "/login", "/register", "/signup"];

const baseNavItems = [
  { label: "Dashboard", href: "/dashboard", icon: "◆" },
  { label: "Chat", href: "/chat", icon: "◆" },
  { label: "Agent", href: "/agent", icon: "◆" },
  { label: "Admin", href: "/admin", icon: "◆" },
  { label: "Markets", href: "/markets", icon: "◆" },
  { label: "Signals", href: "/signals", icon: "◆" },
  { label: "News", href: "/news", icon: "◆" },
  { label: "Alerts", href: "/alerts", icon: "◆" },
  { label: "History", href: "/history", icon: "◆" },
  { label: "Pricing", href: "/pricing", icon: "◆" },
  { label: "Settings", href: "/settings", icon: "◆" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const navItems = baseNavItems;

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  if (PUBLIC_ROUTES.includes(pathname)) {
    return null;
  }

  return (
    <>
      <div className="lg:hidden sticky top-0 z-50 border-b border-cyan-500/10 bg-[#020914]/95 backdrop-blur-xl">
        <div className="flex items-center justify-between px-4 py-3">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="relative w-9 h-9 shrink-0 rounded-xl border border-cyan-400/60 bg-[#020b18] flex items-center justify-center overflow-hidden shadow-[0_0_18px_rgba(0,240,255,0.45),inset_0_0_12px_rgba(0,240,255,0.16)]">
  <span className="absolute inset-0 rounded-xl border border-cyan-300/20 animate-pulse" aria-hidden="true" />
  <svg viewBox="0 0 100 100" className="relative z-10 h-8 w-8" role="img" aria-label="IQ Bot robot head">
    <defs>
      <linearGradient id="sidebarRobotShell" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#f1ffff" />
        <stop offset="40%" stopColor="#8cecff" />
        <stop offset="75%" stopColor="#12bfe8" />
        <stop offset="100%" stopColor="#063247" />
      </linearGradient>
      <filter id="sidebarRobotGlow"><feGaussianBlur stdDeviation="1.6" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
    </defs>
    <path d="M50 9v9" stroke="#00f0ff" strokeWidth="3" strokeLinecap="round" />
    <circle cx="50" cy="6" r="4" fill="#00f0ff" filter="url(#sidebarRobotGlow)" />
    <path d="M25 25Q50 11 75 25L84 37v34q-34 20-68 0V37z" fill="url(#sidebarRobotShell)" fillOpacity=".2" stroke="#00f0ff" strokeWidth="2.2" filter="url(#sidebarRobotGlow)" />
    <path d="M29 39Q50 27 71 39v25q-21 12-42 0z" fill="#020b15" stroke="#00dfff" strokeWidth="1.7" />
    <path d="M36 48h10M54 48h10" stroke="#f3ffff" strokeWidth="5" strokeLinecap="round" filter="url(#sidebarRobotGlow)" />
    <path d="M39 58q11 8 22 0" fill="none" stroke="#00f0ff" strokeWidth="2.2" strokeLinecap="round" />
    <path d="M24 47h-7M76 47h7" stroke="#00f0ff" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="14" cy="47" r="3" fill="#00f0ff" filter="url(#sidebarRobotGlow)" /><circle cx="86" cy="47" r="3" fill="#00f0ff" filter="url(#sidebarRobotGlow)" />
  </svg>
</div>
            <div>
              <p className="font-display text-[11px] font-bold text-white tracking-wider">
                KING ZARRY
              </p>
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/60">
                COMMAND CENTRE
              </p>
            </div>
          </Link>
          <button
            onClick={logout}
            className="px-3 py-1.5 rounded-md font-mono-tech text-[10px] tracking-widest text-red-400/70 border border-red-500/20 hover:bg-red-500/10"
          >
            EXIT
          </button>
        </div>
        <nav className="flex gap-1 overflow-x-auto kz-scroll px-2 pb-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex-shrink-0 px-3 py-2 rounded-md font-mono-tech text-[10px] tracking-widest transition-all ${
                isActive(item.href)
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40"
                  : "text-cyan-400/60 border border-transparent hover:bg-cyan-500/10"
              }`}
            >
              {item.label.toUpperCase()}
            </Link>
          ))}
        </nav>
      </div>

      <aside className="hidden lg:flex w-64 flex-col border-r border-cyan-500/10 bg-[#020914]/80 backdrop-blur-xl flex-shrink-0">
        <Link
          href="/dashboard"
          className="p-5 border-b border-cyan-500/10 block hover:bg-cyan-500/5 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 shrink-0 rounded-xl border border-cyan-400/60 bg-[#020b18] flex items-center justify-center overflow-hidden shadow-[0_0_18px_rgba(0,240,255,0.45),inset_0_0_12px_rgba(0,240,255,0.16)]">
  <span className="absolute inset-0 rounded-xl border border-cyan-300/20 animate-pulse" aria-hidden="true" />
  <svg viewBox="0 0 100 100" className="relative z-10 h-8 w-8" role="img" aria-label="IQ Bot robot head">
    <defs>
      <linearGradient id="sidebarRobotShell" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#f1ffff" />
        <stop offset="40%" stopColor="#8cecff" />
        <stop offset="75%" stopColor="#12bfe8" />
        <stop offset="100%" stopColor="#063247" />
      </linearGradient>
      <filter id="sidebarRobotGlow"><feGaussianBlur stdDeviation="1.6" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
    </defs>
    <path d="M50 9v9" stroke="#00f0ff" strokeWidth="3" strokeLinecap="round" />
    <circle cx="50" cy="6" r="4" fill="#00f0ff" filter="url(#sidebarRobotGlow)" />
    <path d="M25 25Q50 11 75 25L84 37v34q-34 20-68 0V37z" fill="url(#sidebarRobotShell)" fillOpacity=".2" stroke="#00f0ff" strokeWidth="2.2" filter="url(#sidebarRobotGlow)" />
    <path d="M29 39Q50 27 71 39v25q-21 12-42 0z" fill="#020b15" stroke="#00dfff" strokeWidth="1.7" />
    <path d="M36 48h10M54 48h10" stroke="#f3ffff" strokeWidth="5" strokeLinecap="round" filter="url(#sidebarRobotGlow)" />
    <path d="M39 58q11 8 22 0" fill="none" stroke="#00f0ff" strokeWidth="2.2" strokeLinecap="round" />
    <path d="M24 47h-7M76 47h7" stroke="#00f0ff" strokeWidth="2.5" strokeLinecap="round" />
    <circle cx="14" cy="47" r="3" fill="#00f0ff" filter="url(#sidebarRobotGlow)" /><circle cx="86" cy="47" r="3" fill="#00f0ff" filter="url(#sidebarRobotGlow)" />
  </svg>
</div>
            <div>
              <h1 className="font-display text-xs font-bold text-white tracking-wider">
                KING ZARRY AI
              </h1>
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/60">
                COMMAND CENTRE
              </p>
            </div>
          </div>
        </Link>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg font-mono-tech text-[11px] tracking-widest transition-all duration-200 ${
                isActive(item.href)
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.15)]"
                  : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10 border border-transparent"
              }`}
            >
              <span className="text-cyan-500/50">{item.icon}</span>
              {item.label.toUpperCase()}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-cyan-500/10">
          {user?.email && (
            <p className="font-mono-tech text-[10px] text-cyan-400/50 truncate mb-2">
              {user.email}
            </p>
          )}
          <button
            onClick={logout}
            className="w-full px-3 py-2 rounded-lg font-mono-tech text-[10px] tracking-widest text-red-400/70 border border-red-500/20 hover:bg-red-500/10"
          >
            EXIT
          </button>
        </div>
      </aside>
    </>
  );
}
