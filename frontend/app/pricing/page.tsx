"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { getTelegramVipStartUrl } from "@/lib/membership";
import { useRouter } from "next/navigation";

type PlanId = "monthly" | "quarterly" | "yearly";

type Plan = {
  id: PlanId;
  name: string;
  duration: string;
  stars: string;
  description: string;
  features: string[];
  tag: string;
};

const navItems = [
  { label: "HOME", href: "/" },
  { label: "CHAT", href: "/chat" },
  { label: "MARKETS", href: "/markets" },
  { label: "SIGNALS", href: "/signals" },
  { label: "NEWS", href: "/news" },
  { label: "ALERTS", href: "/alerts" },
  { label: "HISTORY", href: "/history" },
  { label: "PRICING", href: "/pricing" },
];

const plans: Plan[] = [
  {
    id: "monthly",
    name: "MONTHLY ACCESS",
    duration: "30 DAYS",
    stars: "150",
    description:
      "Flexible access for users who want the complete KING ZARRY AI environment without a long commitment.",
    features: [
      "Full AI Chat & Reasoning",
      "Memory & Context Retention",
      "Vision & Voice Capabilities",
      "Core Agent & Tool Access",
      "Market Intelligence",
    ],
    tag: "FLEXIBLE",
  },
  {
    id: "quarterly",
    name: "90-DAY ACCESS",
    duration: "90 DAYS",
    stars: "500",
    description:
      "Extended access for users who want continuous use of the KING ZARRY AI intelligence suite.",
    features: [
      "Everything in Monthly",
      "Priority AI Agent Execution",
      "Advanced Market Intelligence",
      "Extended Memory Context",
      "Deep News & Context Analysis",
    ],
    tag: "RECOMMENDED",
  },
  {
    id: "yearly",
    name: "ANNUAL ACCESS",
    duration: "365 DAYS",
    stars: "2500",
    description:
      "Long-term access for users who want the complete AI environment available throughout the year.",
    features: [
      "Everything in 90-Day Access",
      "Maximum Priority Processing",
      "Full Agents, Vision & Tools Suite",
      "Telegram & Discord Integration",
      "Extended Memory Architecture",
    ],
    tag: "LONG TERM",
  },
];

const faqs = [
  {
    q: "What does KING ZARRY AI access include?",
    a: "Access includes AI conversation, reasoning, memory, vision, voice, agents, tools and supported intelligence features.",
  },
  {
    q: "Which plan should I choose?",
    a: "Monthly is the shortest commitment ($9.99). 90-Day is $24.99. Annual is $79.99.",
  },
  {
    q: "How does payment work?",
    a: "Pay with card on the web via Stripe. Telegram Stars remain available for bot VIP. After Stripe payment, webhook activates VIP on your web account.",
  },
  {
    q: "What happens when my membership expires?",
    a: "Paid access ends at the expiration date. Your account and web data can remain unless you delete them.",
  },
  {
    q: "Can I use my account on different devices?",
    a: "Yes. Sign in from any supported device with your web account.",
  },
];

export default function KingZarryPricingPage() {
  const [selectedPlan, setSelectedPlan] = useState<PlanId>("quarterly");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const { user, isAuthenticated } = useAuth();
  const router = useRouter();

  const startStripeCheckout = async () => {
    setCheckoutError(null);
    if (!isAuthenticated) {
      router.push("/login?next=/pricing");
      return;
    }
    setCheckoutLoading(true);
    try {
      const plan = selectedPlan === "quarterly" ? "quarterly" : selectedPlan;
      const res = await api.createCheckoutSession(plan);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      setCheckoutError("No checkout URL returned");
    } catch (e) {
      setCheckoutError(
        e instanceof ApiError
          ? e.detail || e.message
          : "Checkout failed. Is STRIPE_SECRET_KEY set on the API?"
      );
    } finally {
      setCheckoutLoading(false);
    }
  };

  const selectedPlanData = plans.find((plan) => plan.id === selectedPlan);

  const handleSelectPlan = (planId: PlanId) => {
    setSelectedPlan(planId);
  };

  const usdLabel =
    selectedPlan === "monthly"
      ? "$9.99"
      : selectedPlan === "yearly"
        ? "$79.99"
        : "$24.99";

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#03060a] text-cyan-100 selection:bg-cyan-400 selection:text-black">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />

      <header className="relative z-30 border-b border-cyan-500/15 bg-[#030810]/85 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
              <span className="text-lg font-extrabold tracking-wider">KZ</span>
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-widest text-white sm:text-base">
                KING ZARRY AI
              </h1>
              <div className="flex items-center gap-2 font-mono text-[9px] text-cyan-400/70">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                <span>PRICING</span>
              </div>
            </div>
          </Link>
          <nav className="hidden items-center gap-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">
            {navItems.map((item) => {
              const active = item.label === "PRICING";
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition-all ${
                    active
                      ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-200"
                      : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            aria-label="Toggle navigation"
            onClick={() => setMobileMenuOpen((v) => !v)}
            className="rounded border border-cyan-500/30 bg-cyan-950/40 p-2 text-cyan-400 lg:hidden"
          >
            {mobileMenuOpen ? "✕" : "≡"}
          </button>
        </div>
      </header>

      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 lg:hidden">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="rounded border border-cyan-500/10 p-2 text-center font-mono text-[10px] tracking-wider text-cyan-400/70"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      )}

      <main className="relative z-20 mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 md:py-8">
        <section className="border-b border-cyan-500/10 pb-6">
          <h2 className="text-2xl font-bold tracking-widest text-white sm:text-3xl">
            CHOOSE YOUR ACCESS
          </h2>
          <p className="mt-2 max-w-2xl font-mono text-xs leading-relaxed text-cyan-400/60">
            Pay with card (Stripe) or Telegram Stars. Card unlocks web VIP via
            webhook.
          </p>
          {user?.is_subscribed && (
            <p className="mt-3 font-mono text-xs text-emerald-300/90">
              You already have active VIP
              {user.plan ? ` · ${String(user.plan).toUpperCase()}` : ""}.
            </p>
          )}
        </section>

        <section>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {plans.map((plan) => {
              const selected = selectedPlan === plan.id;
              const price =
                plan.id === "monthly"
                  ? "$9.99"
                  : plan.id === "yearly"
                    ? "$79.99"
                    : "$24.99";
              return (
                <button
                  key={plan.id}
                  type="button"
                  onClick={() => handleSelectPlan(plan.id)}
                  className={`relative flex flex-col overflow-hidden rounded-2xl border p-6 text-left transition-all ${
                    selected
                      ? "border-cyan-400 bg-cyan-950/30 shadow-[0_0_30px_rgba(0,240,255,0.18)]"
                      : "border-cyan-500/20 bg-[#020914]/90 hover:border-cyan-500/40"
                  }`}
                >
                  <div className="font-mono text-xs font-bold tracking-wider text-cyan-300">
                    {plan.name}
                  </div>
                  <div className="mt-1 font-mono text-[9px] text-cyan-500/60">
                    {plan.duration}
                  </div>
                  <div className="my-4 border-y border-cyan-500/15 py-4">
                    <span className="font-mono text-3xl font-extrabold text-white">
                      {price}
                    </span>
                    <span className="ml-2 font-mono text-[10px] text-cyan-400">
                      USD · {plan.stars} STARS ALT
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-cyan-200/75">
                    {plan.description}
                  </p>
                  <ul className="mt-4 space-y-2">
                    {plan.features.map((f) => (
                      <li
                        key={f}
                        className="flex gap-2 font-mono text-[10px] text-cyan-100/90"
                      >
                        <span className="text-cyan-400">▸</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <span
                    className={`mt-4 inline-block rounded border px-2 py-0.5 font-mono text-[8px] tracking-wider ${
                      selected
                        ? "border-cyan-400/50 bg-cyan-400/20 text-cyan-200"
                        : "border-cyan-500/30 text-cyan-400"
                    }`}
                  >
                    {plan.tag}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/60">
                SELECTED ACCESS
              </div>
              <h3 className="mt-1 text-lg font-bold tracking-widest text-white">
                {selectedPlanData?.name}
              </h3>
              <p className="mt-1 font-mono text-[10px] text-cyan-300/70">
                {usdLabel} · {selectedPlanData?.duration}
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={startStripeCheckout}
                disabled={checkoutLoading}
                className="inline-flex items-center justify-center rounded-lg bg-cyan-400 px-6 py-3 font-mono text-xs font-bold tracking-widest text-black shadow-[0_0_20px_rgba(0,240,255,0.2)] transition hover:bg-cyan-300 disabled:opacity-50"
              >
                {checkoutLoading ? "REDIRECTING…" : "PAY WITH CARD (STRIPE)"}
              </button>
              {!isAuthenticated && (
                <Link
                  href="/login?next=/pricing"
                  className="inline-flex items-center justify-center rounded-lg border border-cyan-500/40 px-6 py-3 font-mono text-xs font-bold tracking-widest text-cyan-200"
                >
                  SIGN IN FIRST
                </Link>
              )}
              <a
                href={getTelegramVipStartUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center rounded-lg border border-cyan-500/40 px-6 py-3 font-mono text-xs font-bold tracking-widest text-cyan-200"
              >
                OR TELEGRAM STARS
              </a>
            </div>
          </div>
          {checkoutError && (
            <p className="mt-3 font-mono text-[10px] text-red-300/90">
              {checkoutError}
            </p>
          )}
          <p className="mt-4 border-t border-cyan-500/10 pt-3 font-mono text-[9px] text-cyan-400/50">
            Web: Stripe card → webhook → VIP. Telegram Stars: bot only. After
            card payment, open Settings to confirm status.
          </p>
        </section>

        <section className="space-y-3">
          <h3 className="font-mono text-xs font-bold tracking-widest text-white">
            FAQ
          </h3>
          {faqs.map((faq, i) => (
            <div
              key={faq.q}
              className="rounded-xl border border-cyan-500/15 bg-cyan-950/20"
            >
              <button
                type="button"
                onClick={() => setActiveFaq(activeFaq === i ? null : i)}
                className="flex w-full items-center justify-between px-4 py-3 text-left font-mono text-xs text-cyan-100"
              >
                {faq.q}
                <span>{activeFaq === i ? "−" : "+"}</span>
              </button>
              {activeFaq === i && (
                <p className="border-t border-cyan-500/10 px-4 py-3 text-xs text-cyan-300/70">
                  {faq.a}
                </p>
              )}
            </div>
          ))}
        </section>

        <footer className="border-t border-cyan-500/10 pt-6 pb-10 text-center">
          <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/40">
            KING ZARRY AI
          </div>
        </footer>
      </main>
    </div>
  );
}
