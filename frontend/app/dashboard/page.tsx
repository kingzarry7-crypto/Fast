"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
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
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-6xl mx-auto">
        <div className="mb-10">
          <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/50 mb-2">
            SYSTEM ONLINE
          </p>
          <h1 className="font-display text-3xl font-bold text-white kz-glow-text tracking-wider">
            Command Centre
          </h1>
          <p className="font-mono-tech text-xs tracking-widest text-cyan-200/50 mt-2">
            WELCOME BACK{user?.display_name ? `, ${user.display_name.toUpperCase()}` : ""}
          </p>
        </div>

        <div className="kz-panel p-12 mb-8 flex flex-col items-center">
          <AICore state="idle" size={260} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {[
            { label: "AI CORE", value: "ACTIVE", color: "text-emerald-400" },
            { label: "DATABASE", value: "NEON", color: "text-cyan-400" },
            { label: "SESSION", value: user ? "AUTHENTICATED" : "—", color: "text-cyan-400" },
          ].map((s) => (
            <div key={s.label} className="kz-panel p-5">
              <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-2">
                {s.label}
              </p>
              <p className={`font-display text-lg font-bold ${s.color}`}>
                {s.value}
              </p>
            </div>
          ))}
        </div>

        <div>
          <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/40 mb-3">
            QUICK ACCESS
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {quickLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="kz-panel p-5 hover:border-cyan-500/60 transition-all group"
              >
                <p className="font-display text-sm font-bold text-white group-hover:text-cyan-300 transition-colors tracking-wider">
                  {link.label}
                </p>
                <p className="font-mono-tech text-[10px] tracking-widest text-cyan-200/40 mt-2">
                  {link.desc}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
