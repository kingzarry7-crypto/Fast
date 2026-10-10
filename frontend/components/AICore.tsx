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
    [440, 660, 880].forEach((freq, i) => {
      const start = i * 0.18;
      const duration = 0.45;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
      gain.gain.setValueAtTime(0, ctx.currentTime + start);
      gain.gain.linearRampToValueAtTime(0.07, ctx.currentTime + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + start);
      osc.stop(ctx.currentTime + start + duration);
    });
    setTimeout(() => void ctx.close(), 1500);
  } catch {
    /* Audio can be unavailable until user interaction. */
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
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      aria-label={`King Zarry AI human core: ${stateLabels[state].toLowerCase()}`}
    >
      {/* The uploaded human portrait is the core visual; no cartoon face or robot illustration. */}
      <div
        className="absolute rounded-full transition-all duration-500"
        style={{
          inset: size * 0.12,
          background: `radial-gradient(ellipse at 50% 45%, ${color}28 0%, ${color}12 42%, transparent 74%)`,
          filter: active ? "blur(8px)" : "blur(14px)",
          transform: active ? "scale(1.04)" : "scale(1)",
        }}
        aria-hidden="true"
      />
      <div
        className="relative z-10 flex items-center justify-center overflow-hidden"
        style={{
          width: size * 0.76,
          height: size * 0.88,
          filter: `drop-shadow(0 0 ${active ? 22 : 14}px ${color}66)`,
          transition: "filter 300ms ease",
        }}
      >
        <img
          src="/human-ai-core.webp"
          alt="King Zarry AI real human-style core portrait"
          className="h-full w-full object-contain"
          draggable={false}
        />
      </div>

      {modules.map((item) => (
        <a
          key={item.label}
          href={item.href}
          className={`absolute z-20 ${item.position} rounded-full border px-2 py-1 font-mono text-[8px] tracking-[0.16em] transition duration-200 hover:scale-110 focus-visible:outline focus-visible:outline-2`}
          style={{
            borderColor: `${color}88`,
            color,
            background: "rgba(2,11,24,.92)",
            boxShadow: `0 0 12px ${color}22`,
          }}
        >
          {item.label}
        </a>
      ))}

      <div className="absolute -bottom-3 left-1/2 -translate-x-1/2">
        <span
          className="whitespace-nowrap font-mono-tech text-[10px] tracking-[0.35em] uppercase"
          style={{ color, textShadow: `0 0 10px ${color}88` }}
        >
          {stateLabels[state]}
        </span>
      </div>
    </div>
  );
}
