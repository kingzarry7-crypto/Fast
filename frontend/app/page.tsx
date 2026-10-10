"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

const INTRO_STAGES = [
  {
    eyebrow: "SYSTEM ONLINE · 01 / 05",
    title: "AN AI THAT THINKS WITH YOU",
    description: "Wake the core. Ask questions, explore ideas, and turn complex problems into clear next steps.",
    marker: "INTELLIGENCE · REASONING · ANSWERS",
  },
  {
    eyebrow: "LIVE INTELLIGENCE · 02 / 05",
    title: "FIND THE SIGNAL",
    description: "Search information, research opportunities, and bring useful insights into one place.",
    marker: "SEARCH · RESEARCH · INSIGHTS",
  },
  {
    eyebrow: "CONNECTED WORKSPACE · 03 / 05",
    title: "YOUR TOOLS, WORKING TOGETHER",
    description: "Bring supported accounts and services into one assistant, instead of jumping between tabs.",
    marker: "ACCOUNTS · SERVICES · SHARED CONTEXT",
  },
  {
    eyebrow: "ACTION WITH CONTROL · 04 / 05",
    title: "FROM IDEAS TO VERIFIED WORK",
    description: "Prepare workflows, ask before sensitive actions, then check the evidence before reporting a result.",
    marker: "PLAN · APPROVE · EXECUTE · VERIFY",
  },
  {
    eyebrow: "YOUR COMMAND CENTRE · 05 / 05",
    title: "KING ZARRY AI",
    description: "Your personal AI command centre is coming up. Sign in to enter your workspace.",
    marker: "INTELLIGENCE, CONNECTED TO ACTION",
  },
] as const;

export default function LandingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [stage, setStage] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (user) {
      router.replace("/dashboard");
      return;
    }

    // Five cinematic chapters, three seconds each; the final brand reveal
    // occupies seconds 12–15 before the login dashboard opens.
    const stageTimer = window.setInterval(() => {
      setStage((current) => Math.min(current + 1, INTRO_STAGES.length - 1));
    }, 3000);
    const loginTimer = window.setTimeout(() => router.replace("/login"), 15000);

    return () => {
      window.clearInterval(stageTimer);
      window.clearTimeout(loginTimer);
    };
  }, [isLoading, user, router]);

  const playIntroSound = () => {
    try {
      const AudioContextClass = window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextClass) return;
      const audio = new AudioContextClass();
      const now = audio.currentTime;
      const master = audio.createGain();
      master.gain.setValueAtTime(0.0001, now);
      master.gain.exponentialRampToValueAtTime(0.16, now + 0.08);
      master.gain.exponentialRampToValueAtTime(0.0001, now + 1.35);
      master.connect(audio.destination);
      [
        { frequency: 440, start: 0.02, duration: 0.55 },
        { frequency: 660, start: 0.18, duration: 0.72 },
        { frequency: 880, start: 0.42, duration: 0.8 },
      ].forEach(({ frequency, start, duration }) => {
        const oscillator = audio.createOscillator();
        const tone = audio.createGain();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(frequency, now + start);
        tone.gain.setValueAtTime(0.0001, now + start);
        tone.gain.exponentialRampToValueAtTime(0.65, now + start + 0.05);
        tone.gain.exponentialRampToValueAtTime(0.0001, now + start + duration);
        oscillator.connect(tone);
        tone.connect(master);
        oscillator.start(now + start);
        oscillator.stop(now + start + duration + 0.03);
      });
      setSoundEnabled(true);
      window.setTimeout(() => void audio.close(), 1700);
    } catch {
      // Browsers can block audio until a user gesture.
    }
  };

  const currentStage = INTRO_STAGES[stage];
  const isBrandReveal = stage === INTRO_STAGES.length - 1;

  return (
    <main className="relative isolate flex min-h-[100dvh] items-center justify-center overflow-hidden bg-[#020711] px-5 py-8 text-[#dff7ff]">
      <div aria-hidden="true" className="kz-auth-cosmic-surface" />
      <section className="relative z-10 flex w-full max-w-3xl flex-col items-center text-center">
        <p key={currentStage.eyebrow} className="kz-intro-copy mb-3 rounded-full border border-cyan-200/20 bg-[#08162f]/60 px-4 py-2 font-mono-tech text-[9px] tracking-[0.35em] text-cyan-100/75 backdrop-blur">
          {currentStage.eyebrow}
        </p>

        <div className={`relative ${isBrandReveal ? "kz-intro-brand-reveal" : "kz-intro-core-motion"}`}>
          <AICore state="thinking" size={stage === 4 ? 280 : 300} />
        </div>

        <div key={stage} className="kz-intro-copy w-full">
          {isBrandReveal ? (
            <h1 className="mt-1 font-display text-3xl font-black tracking-[0.13em] text-white drop-shadow-[0_0_32px_rgba(56,214,255,.55)] sm:text-5xl">
              KING ZARRY <span className="text-[#f2c76b]">AI</span>
            </h1>
          ) : (
            <h1 className="mt-3 font-display text-2xl font-black tracking-[0.1em] text-white drop-shadow-[0_0_25px_rgba(56,214,255,.35)] sm:text-4xl">
              {currentStage.title}
            </h1>
          )}
          <p className="mx-auto mt-4 min-h-[3.5rem] max-w-xl text-sm leading-7 text-cyan-50/70 sm:text-base">
            {currentStage.description}
          </p>
          <p className="mt-4 font-mono-tech text-[9px] tracking-[0.2em] text-cyan-100/55 sm:text-[10px]">
            {currentStage.marker}
          </p>
        </div>

        <div className="mt-7 flex items-center justify-center gap-2" aria-label={`Intro chapter ${stage + 1} of 5`}>
          {INTRO_STAGES.map((item, index) => (
            <span
              key={item.eyebrow}
              className={`h-1 rounded-full transition-all duration-500 ${index === stage ? "w-10 bg-cyan-300 shadow-[0_0_12px_rgba(56,214,255,.8)]" : index < stage ? "w-5 bg-cyan-300/55" : "w-5 bg-cyan-100/15"}`}
            />
          ))}
        </div>
        <div className="mt-4 h-px w-56 overflow-hidden bg-cyan-100/10">
          <div className="h-full w-full origin-left animate-[kz-intro-bar_15s_linear_both] bg-cyan-300 shadow-[0_0_14px_rgba(56,214,255,.9)]" />
        </div>

        <button
          type="button"
          onClick={playIntroSound}
          className="mt-6 rounded-full border border-cyan-100/25 bg-cyan-200/[0.07] px-4 py-2 font-mono-tech text-[10px] tracking-[0.15em] text-cyan-50/80 transition hover:bg-cyan-200/[0.14]"
        >
          {soundEnabled ? "INTRO SOUND PLAYED ✓" : "▶ TAP TO PLAY INTRO SOUND"}
        </button>
        <p className="mt-3 font-mono-tech text-[9px] tracking-widest text-cyan-100/35">
          {isBrandReveal ? "PREPARING YOUR SIGN-IN DASHBOARD" : "KING ZARRY AI · INITIALIZING"}
        </p>
      </section>
    </main>
  );
}
