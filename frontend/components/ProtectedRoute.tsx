"use client";

import Link from "next/link";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function DashboardPage() {
  const { user } = useAuth();

  const quickLinks = [
    { label: "Chat", href: "/chat", desc: "Ask the AI anything" },
    { label: "Signals", href: "/signals", desc: "Live MTF trading signals" },
    { label: "Markets", href: "/markets", desc: "BTC • ETH • SOL • XAU" },
    { label: "News", href: "/news", desc: "Economic calendar & headlines" },
    { label: "Settings", href: "/settings", desc: "Account & preferences" },
  ];

  return (
    <div className="p-6 lg:p-10 max-w-6xl mx-auto">
      <div className="mb-10">
        <p className="text-[10px] font-mono text-cyan-400/50 tracking-[0.4em] mb-2">
          SYSTEM ONLINE
        </p>
        <h1 className="text-3xl font-bold text-white kz-glow-text">
          Command Centre
        </h1>
        <p className="text-sm text-cyan-200/50 mt-1">
          Welcome back{user?.display_name ? `, ${user.display_name}` : ""}.
        </p>
      </div>

      <div className="kz-panel p-10 mb-8 flex flex-col items-center">
        <AICore state="idle" size={180} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {[
          { label: "AI CORE", value: "ACTIVE", color: "text-emerald-400" },
          { label: "DATABASE", value: "NEON", color: "text-cyan-400" },
          {
            label: "SESSION",
            value: user ? "AUTHENTICATED" : "—",
            color: "text-cyan-400",
          },
        ].map((s) => (
          <div key={s.label} className="kz-panel p-5">
            <p className="text-[10px] font-mono text-cyan-400/40 tracking-widest mb-1">
              {s.label}
            </p>
            <p className={`text-lg font-bold font-mono ${s.color}`}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div>
        <p className="text-[10px] font-mono text-cyan-400/40 tracking-[0.3em] mb-3">
          QUICK ACCESS
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {quickLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="kz-panel p-5 hover:border-cyan-500/40 transition-all group"
            >
              <p className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                {link.label}
              </p>
              <p className="text-xs text-cyan-200/40 mt-1">
                {link.desc}
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
