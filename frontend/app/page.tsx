"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AICore from "@/components/AICore";
import { useAuth } from "@/hooks/useAuth";

const FEATURES = [
  ["AI WORKFLOWS", "Prepare tasks and review them before execution"],
  ["LIVE INTELLIGENCE", "Market context, signals and news in one place"],
  ["SHARED MEMORY", "A consistent assistant experience across channels"],
  ["CONNECTED SERVICES", "Manage authorized services from your dashboard"],
];

export default function LandingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [introDone, setIntroDone] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(false);

  useEffect(() => {
    if (!isLoading && user) router.replace("/dashboard");
  }, [isLoading, user, router]);

  useEffect(() => {
    const timer = window.setTimeout(() => setIntroDone(true), 2800);
    return () => window.clearTimeout(timer);
  }, []);

  const playIntroSound = () => {
    try {
      const AudioContextClass = window.AudioContext;
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
      // Browsers can block audio until the user interacts with the page.
    }
  };

  if (isLoading || user) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center overflow-hidden bg-[#040b1a]">
        <div className="text-center">
          <AICore state="thinking" size={150} />
          <p className="mt-5 font-mono-tech text-[10px] tracking-[0.35em] text-cyan-200/60">
            {user ? "ENTERING COMMAND CENTRE…" : "INITIALIZING KING ZARRY AI…"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <main className="relative isolate flex min-h-[100dvh] items-center justify-center overflow-hidden bg-[#040b1a] px-5 py-12 text-[#dff7ff]">
      {!introDone && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden bg-[#020711]">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(56,214,255,.18),transparent_48%)] animate-pulse" />
          <div className="relative animate-[kz-intro-core_2.4s_ease-out_both]">
            <AICore state="thinking" size={190} />
          </div>
          <p className="relative mt-7 animate-[kz-intro-text_1.1s_.35s_both] font-mono-tech text-[10px] tracking-[0.42em] text-cyan-100/70">
            INITIALIZING KING ZARRY AI
          </p>
          <h1 className="relative mt-4 animate-[kz-intro-text_1.1s_.65s_both] font-display text-3xl font-black tracking-[0.16em] text-white sm:text-5xl">
            KING ZARRY <span className="text-[#f2c76b]">AI</span>
          </h1>
          <div className="relative mt-7 h-px w-48 overflow-hidden bg-cyan-100/15">
            <div className="h-full w-full origin-left animate-[kz-intro-bar_2.2s_ease-out_both] bg-cyan-300 shadow-[0_0_12px_rgba(56,214,255,.9)]" />
          </div>
          <button
            type="button"
            onClick={playIntroSound}
            className="relative mt-8 rounded-full border border-cyan-100/25 bg-cyan-200/[0.07] px-4 py-2 font-mono-tech text-[10px] tracking-[0.15em] text-cyan-50/80 transition hover:bg-cyan-200/[0.14]"
            aria-label="Play intro sound"
          >
            {soundEnabled ? "INTRO SOUND PLAYED ✓" : "▶ TAP TO PLAY INTRO SOUND"}
          </button>
          <p className="relative mt-3 font-mono-tech text-[9px] tracking-widest text-cyan-100/35">
            {soundEnabled ? "AUDIO ENABLED" : "SOUND REQUIRES A TAP ON THIS DEVICE"}
          </p>
        </div>
      )}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -inset-[20%] animate-[kz-aurora_18s_ease-in-out_infinite_alternate] bg-[radial-gradient(ellipse_at_25%_30%,rgba(56,214,255,.23),transparent_32%),radial-gradient(ellipse_at_75%_65%,rgba(242,199,107,.14),transparent_32%),radial-gradient(ellipse_at_60%_20%,rgba(120,90,255,.16),transparent_35%)]" />
        <div className="absolute inset-0 opacity-35" style={{ backgroundImage: "radial-gradient(rgba(223,247,255,.7) .7px,transparent .7px)", backgroundSize: "34px 34px" }} />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_15%,rgba(2,6,16,.78)_100%)]" />
      </div>

      <div className={"relative z-10 mx-auto w-full max-w-5xl transition-all duration-1000 " + (introDone ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0")}>
        <div className="grid items-center gap-10 md:grid-cols-[1.05fr_.95fr] md:gap-12">
          <section className="text-center md:text-left">
            <div className="mx-auto mb-5 w-fit rounded-full border border-cyan-200/20 bg-[#08162f]/60 px-4 py-2 font-mono-tech text-[9px] tracking-[0.3em] text-cyan-100/70 backdrop-blur md:mx-0">
              PERSONAL AI · COMMAND CENTRE
            </div>
            <div className="mx-auto max-w-[220px] md:mx-0">
              <AICore state="idle" size={210} />
            </div>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-[0.08em] text-white drop-shadow-[0_0_30px_rgba(56,214,255,.25)] sm:text-5xl lg:text-6xl">
              KING ZARRY <span className="text-[#f2c76b]">AI</span>
            </h1>
            <p className="mt-5 max-w-xl text-sm leading-7 text-cyan-50/65 sm:text-base">
              Your trading and intelligence assistant — bringing conversations, market context, news, connected services and approved workflows together in one command centre.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row md:justify-start">
              <Link href="/login" className="rounded-xl bg-[linear-gradient(110deg,#38d6ff,#63a7ff)] px-7 py-3.5 text-center font-display text-xs font-bold tracking-[0.2em] text-[#021024] shadow-[0_0_30px_rgba(56,214,255,.18)] transition hover:brightness-110">
                ENTER COMMAND CENTRE
              </Link>
              <Link href="/register" className="rounded-xl border border-cyan-100/20 bg-[#08162f]/50 px-7 py-3.5 text-center font-mono-tech text-xs tracking-[0.18em] text-cyan-100/85 transition hover:border-cyan-200/50 hover:bg-cyan-300/10">
                CREATE ACCOUNT
              </Link>
            </div>
            <p className="mt-5 font-mono-tech text-[9px] tracking-widest text-cyan-100/30">SECURE SIGN-IN · YOUR ACCOUNT · YOUR APPROVALS</p>
          </section>

          <section className="rounded-[24px] border border-cyan-300/15 bg-[linear-gradient(145deg,rgba(8,22,47,.78),rgba(4,11,26,.72))] p-5 shadow-[0_24px_90px_rgba(0,0,0,.35)] backdrop-blur-2xl sm:p-7">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-sm font-bold tracking-[0.18em] text-white">BUILT FOR YOUR WORKFLOW</h2>
                <p className="mt-1 text-xs text-cyan-100/45">A single place to manage your AI tools</p>
              </div>
              <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(56,214,255,.8)]" />
            </div>
            <div className="space-y-3">
              {FEATURES.map(([title, detail], index) => (
                <div key={title} className="flex gap-4 rounded-2xl border border-cyan-100/10 bg-[#040b1a]/45 p-4 transition hover:border-cyan-200/25 hover:bg-cyan-300/[0.04]">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-200/15 bg-cyan-300/[0.07] font-mono-tech text-xs text-[#f2c76b]">
                    0{index + 1}
                  </span>
                  <div>
                    <h3 className="font-display text-[11px] font-bold tracking-[0.14em] text-cyan-50">{title}</h3>
                    <p className="mt-1 text-xs leading-5 text-cyan-50/50">{detail}</p>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-5 text-[10px] leading-5 text-cyan-100/35">
              Service status is shown inside the app based on available connection evidence — not decorative demo labels.
            </p>
          </section>
        </div>
      </div>
      <style jsx global>{`
        @keyframes kz-intro-core {
          0% { transform: scale(.55); opacity: 0; filter: blur(12px); }
          35% { transform: scale(1.06); opacity: 1; filter: blur(0); }
          75% { transform: scale(1); opacity: 1; }
          100% { transform: scale(.96); opacity: 0; }
        }
        @keyframes kz-intro-text {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes kz-intro-bar {
          from { transform: scaleX(0); }
          to { transform: scaleX(1); }
        }
        @keyframes kz-aurora {
          0% { transform: translate3d(-1%, -1%, 0) rotate(-2deg) scale(1); }
          100% { transform: translate3d(3%, 2%, 0) rotate(5deg) scale(1.08); }
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-\\[kz-aurora_18s_ease-in-out_infinite_alternate\\] { animation: none !important; }
          * { scroll-behavior: auto !important; }
        }
      `}</style>
    </main>
  );
}
