"use client";

import React, { useState } from "react";
import Link from "next/link";

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
    a: "Your membership is designed to provide access to the KING ZARRY AI environment, including AI conversation, reasoning, memory, vision, voice, agents, tools and supported intelligence features.",
  },
  {
    q: "Which plan should I choose?",
    a: "Choose the duration that fits how you intend to use the system. Monthly is the shortest commitment, 90-Day provides extended access, and Annual is the longest access period.",
  },
  {
    q: "How does Telegram Stars payment work?",
    a: "Telegram Stars are Telegram's in-app payment currency. When the payment flow is connected, your selected membership can be purchased through the authorized Telegram payment interface.",
  },
  {
    q: "What happens when my membership expires?",
    a: "Your paid access period ends when the membership reaches its expiration date. Your account and stored web data can remain associated with your account unless you choose to delete them.",
  },
  {
    q: "Can I use my account on different devices?",
    a: "Yes. Your web account is associated with your authenticated session rather than a single device, allowing you to sign in from supported devices.",
  },
];

export default function KingZarryPricingPage() {
  const [selectedPlan, setSelectedPlan] =
    useState<PlanId>("quarterly");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeFaq, setActiveFaq] = useState<number | null>(null);

  const selectedPlanData = plans.find(
    (plan) => plan.id === selectedPlan
  );

  const handleSelectPlan = (planId: PlanId) => {
    setSelectedPlan(planId);
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#03060a] text-cyan-100 selection:bg-cyan-400 selection:text-black">
      {/* BACKGROUND */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[#072438] via-[#020b14] to-[#010408]" />

      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(to_right,#091a2815_1px,transparent_1px),linear-gradient(to_bottom,#091a2815_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="pointer-events-none fixed inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,240,255,0.012)_3px,transparent_4px)]" />

      <div className="pointer-events-none fixed left-[15%] top-[-10%] h-[600px] w-[600px] rounded-full bg-cyan-600/10 blur-[140px]" />

      <div className="pointer-events-none fixed bottom-[-10%] right-[15%] h-[600px] w-[600px] rounded-full bg-indigo-600/10 blur-[140px]" />

      {/* HEADER */}
      <header className="relative z-30 border-b border-cyan-500/15 bg-[#030810]/85 px-4 py-4 backdrop-blur-xl sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          {/* BRAND */}
          <Link href="/" className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-950/30 text-cyan-400 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
              <span className="text-lg font-extrabold tracking-wider">
                KZ
              </span>

              <span className="absolute -right-1 -top-1 flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-500" />
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-widest text-white sm:text-base">
                  KING ZARRY AI
                </h1>

                <span className="hidden rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[8px] tracking-wider text-cyan-400 sm:inline-block">
                  ACCESS CONTROL
                </span>
              </div>

              <div className="flex items-center gap-2 font-mono text-[9px] text-cyan-400/70">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
                <span>SYSTEM READY</span>
              </div>
            </div>
          </Link>

          {/* DESKTOP NAV */}
          <nav className="hidden items-center gap-1 rounded-lg border border-cyan-500/10 bg-cyan-950/20 p-1 lg:flex">
            {navItems.map((item) => {
              const active = item.label === "PRICING";

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`rounded px-3 py-1.5 font-mono text-xs tracking-wider transition-all ${
                    active
                      ? "border border-cyan-500/40 bg-cyan-500/20 text-cyan-200 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                      : "text-cyan-400/60 hover:bg-cyan-500/10 hover:text-cyan-200"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* MOBILE BUTTON */}
          <button
            type="button"
            aria-label="Toggle navigation"
            onClick={() => setMobileMenuOpen((value) => !value)}
            className="rounded border border-cyan-500/30 bg-cyan-950/40 p-2 text-cyan-400 transition hover:bg-cyan-500/20 lg:hidden"
          >
            {mobileMenuOpen ? (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* MOBILE NAV */}
      {mobileMenuOpen && (
        <div className="relative z-30 border-b border-cyan-500/30 bg-[#040c16]/95 p-4 backdrop-blur-xl lg:hidden">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {navItems.map((item) => {
              const active = item.label === "PRICING";

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`rounded border p-2 text-center font-mono text-[10px] tracking-wider transition ${
                    active
                      ? "border-cyan-500/50 bg-cyan-500/20 text-cyan-300"
                      : "border-cyan-500/10 text-cyan-400/70 hover:bg-cyan-500/10"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* MAIN */}
      <main className="relative z-20 mx-auto w-full max-w-7xl space-y-8 px-4 py-6 sm:px-6 md:py-8">
        {/* TITLE */}
        <section className="flex flex-col gap-5 border-b border-cyan-500/10 pb-6 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_#00f0ff]" />

              <span className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/60">
                ACCESS MODULE / 01
              </span>
            </div>

            <h2 className="text-2xl font-bold tracking-widest text-white sm:text-3xl">
              CHOOSE YOUR ACCESS
            </h2>

            <p className="mt-2 max-w-2xl font-mono text-xs leading-relaxed text-cyan-400/60">
              Activate access to your KING ZARRY AI environment.
            </p>
          </div>

          {/* ACCESS STATUS */}
          <div className="w-full max-w-sm rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 backdrop-blur-md">
            <div className="mb-2 flex items-center justify-between font-mono text-[9px] tracking-wider text-cyan-400/70">
              <span>CURRENT ACCESS</span>
              <span className="text-cyan-500">STANDBY</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-amber-400" />

              <span className="font-mono text-xs text-cyan-100">
                SIGN IN TO VIEW YOUR ACTIVE MEMBERSHIP
              </span>
            </div>
          </div>
        </section>

        {/* CORE */}
        <section className="relative overflow-hidden rounded-2xl border border-cyan-500/20 bg-[#020914]/80 p-5 backdrop-blur-md sm:p-6">
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#00f0ff08_1px,transparent_1px),linear-gradient(to_bottom,#00f0ff08_1px,transparent_1px)] bg-[size:16px_16px]" />

          <div className="relative z-10 flex flex-col items-center gap-8 lg:flex-row">
            {/* CORE DISPLAY */}
            <div className="flex w-full flex-col items-center justify-center lg:w-1/3">
              <div className="relative flex h-36 w-36 items-center justify-center">
                <div className="absolute inset-0 animate-[spin_25s_linear_infinite] rounded-full border border-cyan-500/30" />

                <div className="absolute inset-2 animate-[spin_18s_linear_infinite_reverse] rounded-full border border-dashed border-cyan-400/20" />

                <div className="absolute inset-5 animate-pulse rounded-full bg-cyan-500/10 blur-md shadow-[0_0_25px_rgba(0,240,255,0.3)]" />

                <div className="relative z-10 flex h-16 w-16 flex-col items-center justify-center rounded-full border border-cyan-400/60 bg-[#031322] shadow-[inset_0_0_15px_rgba(0,240,255,0.4)]">
                  <span className="text-lg font-extrabold tracking-tighter text-white">
                    KZ
                  </span>

                  <span className="-mt-1 font-mono text-[8px] tracking-widest text-cyan-400/80">
                    CORE
                  </span>
                </div>

                <div className="absolute h-full w-full animate-[spin_10s_linear_infinite]">
                  <div className="absolute left-1/2 top-0 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-cyan-300 shadow-[0_0_8px_#00f0ff]" />
                </div>
              </div>

              <div className="mt-3 text-center">
                <div className="font-mono text-xs font-bold tracking-widest text-cyan-200">
                  ONE AI CORE
                </div>

                <div className="mt-1 font-mono text-[9px] text-cyan-500/70">
                  ONE CORE → MANY CAPABILITIES
                </div>
              </div>
            </div>

            {/* CAPABILITIES */}
            <div className="grid w-full grid-cols-2 gap-2.5 sm:grid-cols-5 lg:w-2/3">
              {[
                ["AI", "CORE"],
                ["VISION", "READY"],
                ["VOICE", "READY"],
                ["MEMORY", "READY"],
                ["REASONING", "ACTIVE"],
                ["AGENTS", "READY"],
                ["TOOLS", "READY"],
                ["MARKETS", "SUPPORTED"],
                ["SIGNALS", "SUPPORTED"],
                ["NEWS", "SUPPORTED"],
              ].map(([label, status]) => (
                <div
                  key={label}
                  className="rounded-xl border border-cyan-500/15 bg-cyan-950/20 p-2.5 text-center"
                >
                  <div className="mb-1 font-mono text-xs font-bold text-white">
                    {label}
                  </div>

                  <span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-1.5 py-0.5 font-mono text-[8px] text-cyan-300">
                    {status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PLANS */}
        <section>
          <div className="mb-4 flex items-end justify-between">
            <div>
              <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/50">
                MEMBERSHIP CONFIGURATION
              </div>

              <h3 className="mt-1 text-sm font-bold tracking-widest text-white">
                ACCESS TIERS
              </h3>
            </div>

            <div className="hidden font-mono text-[9px] text-cyan-400/50 sm:block">
              TELEGRAM STARS
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {plans.map((plan) => {
              const selected = selectedPlan === plan.id;

              return (
                <div
                  key={plan.id}
                  className={`relative flex flex-col overflow-hidden rounded-2xl border p-6 backdrop-blur-md transition-all duration-300 ${
                    selected
                      ? "border-cyan-400 bg-cyan-950/30 shadow-[0_0_30px_rgba(0,240,255,0.18)]"
                      : "border-cyan-500/20 bg-[#020914]/90 hover:border-cyan-500/40"
                  }`}
                >
                  {/* CORNERS */}
                  <div className="pointer-events-none absolute right-0 top-0 h-4 w-4 border-r-2 border-t-2 border-cyan-400" />

                  <div className="pointer-events-none absolute bottom-0 left-0 h-4 w-4 border-b-2 border-l-2 border-cyan-400" />

                  {/* PLAN HEADER */}
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-mono text-xs font-bold tracking-wider text-cyan-300">
                        {plan.name}
                      </div>

                      <div className="mt-1 font-mono text-[9px] text-cyan-500/60">
                        {plan.duration}
                      </div>
                    </div>

                    <span
                      className={`shrink-0 rounded border px-2 py-0.5 font-mono text-[8px] tracking-wider ${
                        selected
                          ? "border-cyan-400/50 bg-cyan-400/20 text-cyan-200"
                          : "border-cyan-500/30 bg-cyan-500/10 text-cyan-400"
                      }`}
                    >
                      {plan.tag}
                    </span>
                  </div>

                  {/* PRICE */}
                  <div className="my-5 border-y border-cyan-500/15 py-4">
                    <div className="flex items-baseline gap-2">
                      <span className="font-mono text-4xl font-extrabold tracking-tight text-white">
                        {plan.stars}
                      </span>

                      <span className="font-mono text-xs tracking-widest text-cyan-400">
                        STARS
                      </span>
                    </div>

                    <div className="mt-1 font-mono text-[9px] text-cyan-400/60">
                      ACCESS PERIOD:{" "}
                      <span className="text-cyan-200">
                        {plan.duration}
                      </span>
                    </div>
                  </div>

                  {/* DESCRIPTION */}
                  <p className="min-h-[72px] text-xs leading-relaxed text-cyan-200/75">
                    {plan.description}
                  </p>

                  {/* FEATURES */}
                  <div className="mt-5 flex-1">
                    <div className="mb-3 font-mono text-[9px] tracking-widest text-cyan-400/50">
                      INCLUDED CAPABILITIES
                    </div>

                    <ul className="space-y-2">
                      {plan.features.map((feature) => (
                        <li
                          key={feature}
                          className="flex items-start gap-2 font-mono text-[10px] leading-relaxed text-cyan-100/90"
                        >
                          <span className="mt-0.5 text-cyan-400">▸</span>
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* SELECT BUTTON */}
                  <button
                    type="button"
                    onClick={() => handleSelectPlan(plan.id)}
                    className={`mt-6 w-full rounded-lg py-3 font-mono text-[10px] font-bold tracking-widest transition ${
                      selected
                        ? "bg-cyan-400 text-black shadow-[0_0_20px_rgba(0,240,255,0.25)] hover:bg-cyan-300"
                        : "border border-cyan-500/40 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20"
                    }`}
                  >
                    {selected ? "PLAN SELECTED" : "SELECT PLAN"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        {/* SELECTED PLAN ACTION */}
        <section className="rounded-2xl border border-cyan-400/30 bg-cyan-950/20 p-5 shadow-[0_0_25px_rgba(0,240,255,0.08)] sm:p-6">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/60">
                SELECTED ACCESS
              </div>

              <h3 className="mt-1 text-lg font-bold tracking-widest text-white">
                {selectedPlanData?.name}
              </h3>

              <p className="mt-1 font-mono text-[10px] text-cyan-300/70">
                {selectedPlanData?.stars} STARS •{" "}
                {selectedPlanData?.duration}
              </p>
            </div>

            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-lg bg-cyan-400 px-6 py-3 font-mono text-xs font-bold tracking-widest text-black shadow-[0_0_20px_rgba(0,240,255,0.2)] transition hover:bg-cyan-300"
            >
              SIGN IN TO ACTIVATE
            </Link>
          </div>

          <div className="mt-4 border-t border-cyan-500/10 pt-3 font-mono text-[9px] leading-relaxed text-cyan-400/50">
            Secure account authentication is required before membership
            activation. Payment checkout will be connected to the authorized
            payment flow.
          </div>
        </section>

        {/* ACCESS MATRIX */}
        <section className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md sm:p-6">
          <div className="flex flex-col gap-2 border-b border-cyan-500/15 pb-3 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="font-mono text-xs font-bold tracking-widest text-white">
              AI ACCESS MATRIX
            </h3>

            <span className="font-mono text-[9px] text-cyan-400/50">
              SYSTEM CAPABILITY MAP
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-9">
            {[
              "CONVERSATION",
              "VISION",
              "MEMORY",
              "VOICE",
              "AGENTS",
              "TOOLS",
              "MARKETS",
              "SIGNALS",
              "NEWS",
            ].map((module) => (
              <div
                key={module}
                className="flex flex-col items-center justify-center gap-1 rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3 text-center"
              >
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />

                <span className="font-mono text-[9px] font-bold text-cyan-100">
                  {module}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* SYSTEM DESCRIPTION */}
        <section className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md sm:p-6">
          <div className="mb-3 font-mono text-[9px] tracking-[0.25em] text-cyan-400/50">
            SYSTEM ARCHITECTURE
          </div>

          <h3 className="text-sm font-mono font-bold tracking-widest text-white">
            ONE SYSTEM. MANY CAPABILITIES.
          </h3>

          <p className="mt-3 max-w-4xl text-xs leading-relaxed text-cyan-200/80 sm:text-sm">
            KING ZARRY AI brings conversation, reasoning, memory, vision,
            voice, agents, tools and supported intelligence features into
            one personal AI environment. Choose the access duration that
            matches the way you want to use the system.
          </p>
        </section>

        {/* FAQ */}
        <section className="rounded-2xl border border-cyan-500/30 bg-[#020914]/90 p-5 backdrop-blur-md sm:p-6">
          <div className="flex flex-col gap-2 border-b border-cyan-500/15 pb-3 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="font-mono text-xs font-bold tracking-widest text-white">
              ACCESS INFORMATION & FAQ
            </h3>

            <span className="font-mono text-[9px] text-cyan-400/50">
              KNOWLEDGE BASE
            </span>
          </div>

          <div className="mt-4 space-y-2">
            {faqs.map((faq, index) => {
              const open = activeFaq === index;

              return (
                <button
                  key={faq.q}
                  type="button"
                  onClick={() =>
                    setActiveFaq(open ? null : index)
                  }
                  className="w-full rounded-xl border border-cyan-500/20 bg-cyan-950/20 p-4 text-left transition hover:border-cyan-500/40 hover:bg-cyan-950/30"
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-mono text-xs font-bold text-white">
                      {faq.q}
                    </span>

                    <span className="shrink-0 font-mono text-cyan-400">
                      {open ? "[-]" : "[+]"}
                    </span>
                  </div>

                  {open && (
                    <p className="mt-3 border-t border-cyan-500/10 pt-3 font-mono text-[10px] leading-relaxed text-cyan-200/70">
                      {faq.a}
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        </section>

        {/* FOOTER */}
        <footer className="border-t border-cyan-500/10 py-6 text-center">
          <div className="font-mono text-[9px] tracking-[0.25em] text-cyan-400/40">
            KING ZARRY AI
          </div>

          <div className="mt-1 font-mono text-[8px] text-cyan-500/30">
            PERSONAL AI INTELLIGENCE ENVIRONMENT
          </div>
        </footer>
      </main>
    </div>
  );
}
