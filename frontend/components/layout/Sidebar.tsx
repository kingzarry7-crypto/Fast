"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

const PUBLIC_ROUTES = ["/", "/login", "/register", "/signup"];

function isAdminEmail(email?: string | null): boolean {
  if (!email) return false;
  const raw = process.env.NEXT_PUBLIC_ADMIN_EMAILS || "";
  return raw
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
    .includes(email.trim().toLowerCase());
}

const baseNavItems = [
  { label: "Dashboard", href: "/dashboard", icon: "◆" },
  { label: "Chat", href: "/chat", icon: "◆" },
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
  const navItems = [
    ...baseNavItems,
    ...(isAdminEmail(user?.email)
      ? [{ label: "Admin", href: "/admin", icon: "◆" as const }]
      : []),
  ];

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
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.3)]">
              <span className="font-bold text-black text-xs">KZ</span>
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
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.3)]">
              <span className="font-bold text-black text-sm">KZ</span>
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
              <span className="text-[8px] opacity-60">{item.icon}</span>
              {item.label.toUpperCase()}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-cyan-500/10">
          {user && (
            <div className="mb-3">
              <p className="text-xs text-white truncate">
                {user.display_name || user.username || user.email}
              </p>
              <p className="font-mono-tech text-[9px] tracking-wider text-cyan-400/40 truncate">
                {user.email}
              </p>
            </div>
          )}
          <button
            onClick={logout}
            className="w-full px-3 py-2 rounded-lg font-mono-tech text-[10px] tracking-widest text-red-400/70 border border-red-500/20 hover:bg-red-500/10 hover:text-red-300 transition-all"
          >
            SIGN OUT
          </button>
        </div>
      </aside>
    </>
  );
}
