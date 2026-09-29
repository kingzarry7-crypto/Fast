"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function LandingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // Logged-in users skip landing → dashboard
  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/dashboard");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#020914]">
        <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/50">
          INITIALIZING…
        </p>
      </div>
    );
  }

  if (user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#020914]">
        <p className="font-mono-tech text-[10px] tracking-[0.35em] text-cyan-400/50">
          ENTERING COMMAND CENTRE…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#020914] px-6 py-16">
      <div className="w-full max-w-3xl text-center">
        <AICore state="idle" size={200} />
        <p className="mt-8 font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/50">
          COMMAND CENTRE
        </p>
        <h1 className="mt-3 font-display text-4xl font-bold tracking-wider text-white md:text-6xl">
          KING ZARRY <span className="text-cyan-400">AI</span>
        </h1>
        <p className="mt-6 text-base leading-relaxed text-cyan-200/70 md:text-lg">
          Multi-timeframe signals, persistent memory, live news, and generative
          media — your trading intelligence command centre.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/login"
            className="rounded-lg bg-cyan-400 px-8 py-3 font-display text-sm font-bold tracking-[0.2em] text-black transition-all hover:bg-cyan-300"
          >
            ENTER COMMAND CENTRE
          </Link>
          <Link
            href="/register"
            className="rounded-lg border border-cyan-500/30 px-8 py-3 font-mono-tech text-sm tracking-widest text-cyan-300 transition-all hover:bg-cyan-950/40"
          >
            CREATE ACCOUNT
          </Link>
        </div>
        <p className="mt-8 font-mono-tech text-[10px] tracking-widest text-cyan-400/30">
          Already signed in? You will be redirected to the dashboard.
        </p>
      </div>
    </div>
  );
}
