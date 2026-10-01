"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { useRouter } from "next/navigation";

type PlanId = "monthly" | "quarterly" | "yearly";

const plans = [
  { id: "monthly" as const, name: "MONTHLY ACCESS", duration: "30 DAYS", stars: "150", tag: "FLEXIBLE",
    description: "Full AI chat, agent (VIP), markets, and tools for 30 days.",
    features: ["AI Chat & Memory", "Web Agent (VIP)", "Markets & Signals", "Vision & Voice"] },
  { id: "quarterly" as const, name: "90-DAY ACCESS", duration: "90 DAYS", stars: "500", tag: "RECOMMENDED",
    description: "Extended VIP for continuous King Zarry AI use.",
    features: ["Everything in Monthly", "Priority agent jobs", "Morning briefs", "Extended context"] },
  { id: "yearly" as const, name: "ANNUAL ACCESS", duration: "365 DAYS", stars: "2500", tag: "LONG TERM",
    description: "Full year of web VIP and product access.",
    features: ["Everything in 90-Day", "Best long-term value", "Telegram + Discord", "Full tool suite"] },
];

export default function KingZarryPricingPage() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId>("quarterly");
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();
  const selected = plans.find((p) => p.id === selectedPlan);

  const startCheckout = async (provider: "paystack" | "stripe" | "stars") => {
    setCheckoutError(null);
    if (!isAuthenticated) {
      router.push("/login?next=/pricing");
      return;
    }
    setCheckoutLoading(provider);
    try {
      const res = await api.createCheckoutSession(selectedPlan, undefined, provider);
      const payUrl = res.url || res.checkout_url;
      if (payUrl) {
        window.location.href = payUrl;
        return;
      }
      setCheckoutError("No payment link returned. Check Railway billing keys.");
    } catch (e) {
      setCheckoutError(e instanceof ApiError ? e.detail || e.message : "Checkout failed");
    } finally {
      setCheckoutLoading(null);
    }
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#03060a] text-cyan-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />
      <header className="relative z-30 border-b border-cyan-500/15 bg-[#030810]/85 px-4 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/" className="font-bold tracking-widest text-white">KING ZARRY AI</Link>
          <Link href="/dashboard" className="font-mono text-xs text-cyan-400">DASHBOARD</Link>
        </div>
      </header>
      <main className="relative z-20 mx-auto max-w-5xl space-y-8 px-4 py-8">
        <section>
          <h1 className="text-2xl font-bold tracking-widest text-white">CHOOSE YOUR ACCESS</h1>
          <p className="mt-2 font-mono text-xs text-cyan-400/60">
            Pay with Paystack (NGN), Stripe (USD), or Telegram Stars.
          </p>
          {user?.is_subscribed && (
            <p className="mt-2 font-mono text-xs text-emerald-300">Active VIP{user.plan ? ` · ${String(user.plan)}` : ""}</p>
          )}
        </section>
        <section className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <button
              key={plan.id}
              type="button"
              onClick={() => setSelectedPlan(plan.id)}
              className={`rounded-2xl border p-5 text-left transition ${
                selectedPlan === plan.id
                  ? "border-cyan-400 bg-cyan-950/30 shadow-[0_0_24px_rgba(0,240,255,0.15)]"
                  : "border-cyan-500/20 bg-[#020914]/90"
              }`}
            >
              <div className="font-mono text-xs font-bold text-cyan-300">{plan.name}</div>
              <div className="mt-1 font-mono text-[9px] text-cyan-500/60">{plan.duration} · Stars alt {plan.stars}</div>
              <p className="mt-3 text-xs text-cyan-200/70">{plan.description}</p>
              <ul className="mt-3 space-y-1">
                {plan.features.map((f) => (
                  <li key={f} className="font-mono text-[10px] text-cyan-100/80">▸ {f}</li>
                ))}
              </ul>
              <span className="mt-3 inline-block rounded border border-cyan-500/30 px-2 py-0.5 font-mono text-[8px] text-cyan-400">{plan.tag}</span>
            </button>
          ))}
        </section>
        <section className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6">
          <h2 className="text-lg font-bold tracking-widest text-white">{selected?.name}</h2>
          <p className="mt-1 font-mono text-[10px] text-cyan-300/70">{selected?.duration}</p>
          <div className="mt-4 flex flex-col gap-2 sm:max-w-md">
            <button type="button" disabled={!!checkoutLoading} onClick={() => startCheckout("paystack")}
              className="rounded-lg bg-cyan-400 px-6 py-3 font-mono text-xs font-bold tracking-widest text-black disabled:opacity-50">
              {checkoutLoading === "paystack" ? "OPENING…" : "PAY WITH PAYSTACK (NGN)"}
            </button>
            <button type="button" disabled={!!checkoutLoading} onClick={() => startCheckout("stripe")}
              className="rounded-lg border border-cyan-500/40 px-6 py-3 font-mono text-xs font-bold tracking-widest text-cyan-100 disabled:opacity-50">
              {checkoutLoading === "stripe" ? "OPENING…" : "PAY WITH STRIPE (USD)"}
            </button>
            <button type="button" disabled={!!checkoutLoading} onClick={() => startCheckout("stars")}
              className="rounded-lg border border-amber-500/40 px-6 py-3 font-mono text-xs font-bold tracking-widest text-amber-200 disabled:opacity-50">
              {checkoutLoading === "stars" ? "OPENING…" : "PAY WITH TELEGRAM STARS"}
            </button>
            {!isAuthenticated && (
              <Link href="/login?next=/pricing" className="rounded-lg border border-cyan-500/40 px-6 py-3 text-center font-mono text-xs text-cyan-200">
                SIGN IN FIRST
              </Link>
            )}
          </div>
          {checkoutError && <p className="mt-3 font-mono text-[10px] text-red-300">{checkoutError}</p>}
          <p className="mt-4 border-t border-cyan-500/10 pt-3 font-mono text-[9px] text-cyan-400/50">
            Paystack/Stripe unlock web VIP via webhook. Stars open the Telegram bot (bot VIP is separate).
          </p>
        </section>
      </main>
    </div>
  );
}
