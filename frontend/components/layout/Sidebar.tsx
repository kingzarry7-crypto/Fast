"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import AICore from "@/components/AICore";
import RobotHead from "@/components/RobotHead";

const PUBLIC_ROUTES = ["/", "/login", "/register", "/signup", "/forgot-password", "/reset-password", "/verify-email", "/pricing"];
const HIDE_SIDEBAR_ROUTES = ["/dashboard", "/chat"];

const baseNavItems = [
  { label: "Dashboard", href: "/dashboard", icon: "◆" },
  { label: "Chat", href: "/chat", icon: "◆" },
  { label: "Agent", href: "/agent", icon: "◆" },
  { label: "Plugins", href: "/plugins", icon: "◇" },
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

  if (
    PUBLIC_ROUTES.includes(pathname) ||
    HIDE_SIDEBAR_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"))
  ) {
    return null;
  }

  return (
    <>
      <div className="lg:hidden sticky top-0 z-50 border-b border-cyan-500/10 bg-[#020914]/95 backdrop-blur-xl">
        <div className="flex items-center justify-between px-4 py-3">
          <Link href="/dashboard" className="flex items-center gap-2">
            <RobotHead size={36} />
            <div>
              <p className="font-display text-[11px] font-bold text-white tracking-wider">KING ZARRY</p>
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/60">COMMAND CENTRE</p>
            </div>
          </Link>
          <button
            onClick={logout}
            className="px-3 py-1.5 rounded-md font-mono-tech text-[10px] tracking-widest text-red-400/70 border border-red-500/20 hover:bg-red-500/10"
          >
            EXIT
          </button>
        </div>
      </div>

      <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-cyan-500/10 bg-[#020914]/80 min-h-screen">
        <div className="p-4 border-b border-cyan-500/10">
          <Link href="/dashboard" className="flex items-center gap-3">
            <RobotHead size={40} />
            <div>
              <h1 className="font-display text-xs font-bold text-white tracking-wider">KING ZARRY AI</h1>
              <p className="font-mono-tech text-[9px] tracking-[0.3em] text-cyan-400/60">COMMAND CENTRE</p>
            </div>
          </Link>
          <div className="px-1 pt-5 pb-2">
            <div className="rounded-2xl border border-cyan-500/10 bg-black/20 py-3 flex justify-center">
              <AICore state="idle" size={145} />
            </div>
            <div className="mt-4 flex items-center justify-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="font-mono-tech text-[9px] tracking-[0.25em] text-cyan-300">COMMAND CENTRE · IDLE</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={
                "flex items-center gap-3 px-3 py-2.5 rounded-lg font-mono-tech text-[11px] tracking-widest transition-all duration-200 " +
                (isActive(item.href)
                  ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,240,255,0.15)]"
                  : "text-cyan-400/60 hover:text-cyan-200 hover:bg-cyan-500/10 border border-transparent")
              }
            >
              <span className="text-cyan-500/50">{item.icon}</span>
              {item.label.toUpperCase()}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-cyan-500/10">
          {user?.email && (
            <p className="font-mono-tech text-[10px] text-cyan-400/50 truncate mb-2">{user.email}</p>
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
