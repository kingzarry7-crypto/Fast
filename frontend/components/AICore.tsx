"use client";

import { useEffect, useRef } from "react";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";
const stateColors: Record<CoreState, string> = {
  idle: "#00f0ff", thinking: "#8b5cf6", speaking: "#10b981", listening: "#f59e0b", error: "#ef4444",
};
const stateLabels: Record<CoreState, string> = {
  idle: "READY", thinking: "THINKING", speaking: "RESPONDING", listening: "LISTENING", error: "ERROR",
};
function playBootChime() {
  try {
    const AudioCtx = (window as unknown as { AudioContext?: typeof AudioContext }).AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    [440, 660, 880].forEach((freq, i) => {
      const start = i * 0.18, duration = 0.45;
      const osc = ctx.createOscillator(), gain = ctx.createGain();
      osc.type = "sine"; osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
      gain.gain.setValueAtTime(0, ctx.currentTime + start);
      gain.gain.linearRampToValueAtTime(0.07, ctx.currentTime + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(ctx.currentTime + start); osc.stop(ctx.currentTime + start + duration);
    });
    setTimeout(() => void ctx.close(), 1500);
  } catch { /* Audio can be unavailable until user interaction. */ }
}
const modules = [
  { label: "CHAT", href: "/chat", position: "left-[2%] top-[25%]" },
  { label: "AGENT", href: "/dashboard", position: "right-[0%] top-[25%]" },
  { label: "VOICE", href: "/chat", position: "left-[4%] bottom-[20%]" },
  { label: "MEMORY", href: "/settings", position: "right-[1%] bottom-[20%]" },
];
export default function AICore({ state = "idle", size = 220, bootSound = false }: {
  state?: CoreState; size?: number; bootSound?: boolean;
}) {
  const hasPlayed = useRef(false);
  useEffect(() => {
    if (!bootSound || hasPlayed.current) return;
    hasPlayed.current = true; playBootChime();
  }, [bootSound]);
  const color = stateColors[state], active = state !== "idle";
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {active && <>
        <span className="kz-core-ring absolute inset-[3%] rounded-full" style={{ border: `1px solid ${color}` }} />
        <span className="kz-core-ring absolute inset-[3%] rounded-full" style={{ border: `1px solid ${color}`, animationDelay: "0.8s" }} />
      </>}
      <span className="kz-core-rotate absolute rounded-full" style={{ inset: size * 0.06, border: `1px dashed ${color}55` }} />
      <span className="kz-core-rotate-reverse absolute rounded-full" style={{ inset: size * 0.15, border: `1px solid ${color}55`, boxShadow: `0 0 24px ${color}22, inset 0 0 24px ${color}11` }} />
      <span className="kz-orbit absolute rounded-full" style={{ inset: size * 0.1, animationDuration: active ? "3s" : "12s" }}>
        <span className="absolute rounded-full" style={{ width: size * 0.025, height: size * 0.025, background: color, boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`, top: 0, left: "50%", transform: "translateX(-50%)" }} />
      </span>
      <div className="kz-core-pulse absolute rounded-full" style={{ inset: size * 0.24, background: `radial-gradient(circle, ${color}35 0%, ${color}0d 48%, transparent 72%)`, boxShadow: `0 0 60px ${color}44, inset 0 0 40px ${color}22` }} />
      <div className="relative z-10 flex items-center justify-center" style={{ width: size * 0.66, height: size * 0.82 }}>
        <img src="/human-ai-core.webp" alt="King Zarry AI holographic circuit human profile"
          className="h-full w-full object-contain" style={{ filter: `drop-shadow(0 0 14px ${color}77)` }} />
      </div>
      {modules.map(item => (
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
