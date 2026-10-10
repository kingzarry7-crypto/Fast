"use client";

import { useEffect, useRef } from "react";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";

const stateColors: Record<CoreState, string> = {
  idle: "#00f0ff",
  thinking: "#8b5cf6",
  speaking: "#10b981",
  listening: "#f59e0b",
  error: "#ef4444",
};

const stateLabels: Record<CoreState, string> = {
  idle: "READY",
  thinking: "THINKING",
  speaking: "RESPONDING",
  listening: "LISTENING",
  error: "ERROR",
};

function playBootChime() {
  try {
    const AudioCtx =
      (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const play = (freq: number, start: number, duration: number) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
      gain.gain.setValueAtTime(0, ctx.currentTime + start);
      gain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + start);
      osc.stop(ctx.currentTime + start + duration);
    };
    play(440, 0, 0.4);
    play(660, 0.18, 0.4);
    play(880, 0.36, 0.6);
    setTimeout(() => ctx.close(), 1500);
  } catch {
    // Audio is allowed after a user interaction in most browsers.
  }
}

const modules = [
  { label: "CHAT", href: "/chat", position: "left-[2%] top-[25%]" },
  { label: "AGENT", href: "/dashboard", position: "right-[0%] top-[25%]" },
  { label: "VOICE", href: "/chat", position: "left-[4%] bottom-[20%]" },
  { label: "MEMORY", href: "/settings", position: "right-[1%] bottom-[20%]" },
];

export default function AICore({
  state = "idle",
  size = 220,
  bootSound = false,
}: {
  state?: CoreState;
  size?: number;
  bootSound?: boolean;
}) {
  const hasPlayed = useRef(false);
  useEffect(() => {
    if (!bootSound || hasPlayed.current) return;
    hasPlayed.current = true;
    playBootChime();
  }, [bootSound]);

  const color = stateColors[state];
  const active = state !== "idle";

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {active && (
        <>
          <span className="kz-core-ring absolute inset-[3%] rounded-full" style={{ border: `1px solid ${color}` }} />
          <span className="kz-core-ring absolute inset-[3%] rounded-full" style={{ border: `1px solid ${color}`, animationDelay: "0.8s" }} />
        </>
      )}
      <span className="kz-core-rotate absolute rounded-full" style={{ inset: size * 0.06, border: `1px dashed ${color}55` }} />
      <span className="kz-core-rotate-reverse absolute rounded-full" style={{ inset: size * 0.15, border: `1px solid ${color}55`, boxShadow: `0 0 24px ${color}22, inset 0 0 24px ${color}11` }} />
      <span className="kz-orbit absolute rounded-full" style={{ inset: size * 0.1, animationDuration: active ? "3s" : "12s" }}>
        <span className="absolute rounded-full" style={{ width: size * 0.025, height: size * 0.025, background: color, boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`, top: 0, left: "50%", transform: "translateX(-50%)" }} />
      </span>
      <div className="kz-core-pulse absolute rounded-full" style={{ inset: size * 0.24, background: `radial-gradient(circle, ${color}35 0%, ${color}0d 48%, transparent 72%)`, boxShadow: `0 0 60px ${color}44, inset 0 0 40px ${color}22` }} />

      {/* Human hologram core — a face and shoulders, not the old robot mascot. */}
      <div className="relative z-10 flex items-center justify-center" style={{ width: size * 0.54, height: size * 0.68, filter: `drop-shadow(0 0 12px ${color}77)` }}>
        <svg viewBox="0 0 160 200" className="h-full w-full" role="img" aria-label="King Zarry AI holographic human core">
          <defs>
            <linearGradient id="kzHumanSkin" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#efffff" />
              <stop offset="48%" stopColor={color} />
              <stop offset="100%" stopColor="#087c9a" />
            </linearGradient>
            <filter id="kzHumanGlow"><feGaussianBlur stdDeviation="2.2" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            <linearGradient id="kzShoulders" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity=".3" />
              <stop offset="100%" stopColor="#041b2a" stopOpacity=".06" />
            </linearGradient>
          </defs>
          <path d="M25 190 Q29 151 58 143 L65 135 L95 135 L102 143 Q131 151 135 190 Z" fill="url(#kzShoulders)" stroke={color} strokeWidth="2.2" filter="url(#kzHumanGlow)" />
          <path d="M64 125 L64 145 Q80 160 96 145 L96 125" fill="#062231" stroke={color} strokeWidth="1.8" />
          <path d="M48 51 Q48 25 80 23 Q112 25 112 56 L108 94 Q104 119 80 128 Q56 119 52 94 Z" fill="#061a29" fillOpacity=".94" stroke="url(#kzHumanSkin)" strokeWidth="2.8" filter="url(#kzHumanGlow)" />
          <path d="M49 54 Q52 21 80 22 Q107 22 112 53 L101 45 L91 36 Q75 48 53 48 Z" fill={color} fillOpacity=".35" stroke={color} strokeWidth="1.5" />
          <path d="M57 70 Q66 64 73 70 M87 70 Q95 64 103 70" fill="none" stroke="#eaffff" strokeWidth="2.8" strokeLinecap="round" />
          <path d="M80 71 L76 88 L83 90" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
          <path d="M69 103 Q80 110 92 102" fill="none" stroke="#dffcff" strokeWidth="2.2" strokeLinecap="round" />
          <path d="M49 62 L42 78 L47 96 M111 62 L118 78 L113 96" fill="none" stroke={color} strokeOpacity=".75" strokeWidth="1.5" />
          <path d="M37 167 Q80 184 123 167 M44 177 Q80 191 116 177" fill="none" stroke={color} strokeOpacity=".65" strokeWidth="1.2" />
          <circle cx="58" cy="83" r="2" fill={color} /><circle cx="102" cy="83" r="2" fill={color} />
          <path d="M80 7 V17 M75 12 H85" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>

      {/* Orbiting shortcuts remain real links; orbital motion is automatic and hover is interactive. */}
      {modules.map((item) => (
        <a key={item.label} href={item.href} className={`absolute z-20 ${item.position} rounded-full border px-2 py-1 font-mono text-[8px] tracking-[0.16em] transition duration-200 hover:scale-110 focus-visible:outline focus-visible:outline-2`}
          style={{ borderColor: `${color}88`, color, background: "rgba(2,11,24,.92)", boxShadow: `0 0 12px ${color}22` }}>
          {item.label}
        </a>
      ))}

      <div className="absolute -bottom-3 left-1/2 -translate-x-1/2">
        <span className="whitespace-nowrap font-mono-tech text-[10px] tracking-[0.35em] uppercase" style={{ color, textShadow: `0 0 10px ${color}88` }}>
          {stateLabels[state]}
        </span>
      </div>
    </div>
  );
}
