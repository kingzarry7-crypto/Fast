"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

export default function LandingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [soundEnabled, setSoundEnabled] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (user) {
      router.replace("/dashboard");
      return;
    }
    // Play the complete animated system intro for 15 seconds, then open login.
    const timer = window.setTimeout(() => router.replace("/login"), 15000);
    return () => window.clearTimeout(timer);
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

  return (
    <main className="relative isolate flex min-h-[100dvh] items-center justify-center overflow-hidden bg-[#020711] px-5 py-10 text-[#dff7ff]">
      <div aria-hidden="true" className="kz-auth-cosmic-surface" />
      <section className="relative z-10 flex w-full max-w-2xl flex-col items-center text-center">
        <p className="mb-5 rounded-full border border-cyan-200/20 bg-[#08162f]/60 px-4 py-2 font-mono-tech text-[9px] tracking-[0.35em] text-cyan-100/70 backdrop-blur">
          PERSONAL AI · SYSTEM INITIALIZATION
        </p>
        <div className="animate-[kz-intro-core_3.8s_ease-in-out_infinite]">
          <AICore state="thinking" size={320} />
        </div>
        <p className="mt-5 font-mono-tech text-[10px] tracking-[0.42em] text-cyan-100/70">
          INITIALIZING KING ZARRY AI
        </p>
        <h1 className="mt-4 font-display text-3xl font-black tracking-[0.16em] text-white drop-shadow-[0_0_30px_rgba(56,214,255,.35)] sm:text-5xl">
          KING ZARRY <span className="text-[#f2c76b]">AI</span>
        </h1>
        <p className="mt-4 max-w-lg text-sm leading-7 text-cyan-50/65">
          Your personal AI command centre for conversations, live intelligence, connected services and approved workflows.
        </p>
        <div className="mt-7 h-px w-56 overflow-hidden bg-cyan-100/15">
          <div className="h-full w-full origin-left animate-[kz-intro-bar_15s_linear_both] bg-cyan-300 shadow-[0_0_14px_rgba(56,214,255,.9)]" />
        </div>
        <button
          type="button"
          onClick={playIntroSound}
          className="mt-7 rounded-full border border-cyan-100/25 bg-cyan-200/[0.07] px-4 py-2 font-mono-tech text-[10px] tracking-[0.15em] text-cyan-50/80 transition hover:bg-cyan-200/[0.14]"
        >
          {soundEnabled ? "INTRO SOUND PLAYED ✓" : "▶ TAP TO PLAY INTRO SOUND"}
        </button>
        <p className="mt-3 font-mono-tech text-[9px] tracking-widest text-cyan-100/35">
          SECURE SYSTEM BOOT · OPENING SIGN-IN IN 15 SECONDS
        </p>
      </section>
    </main>
  );
}
