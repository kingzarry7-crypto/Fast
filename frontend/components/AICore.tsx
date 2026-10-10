"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";

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

const modules = [
  { label: "CHAT", sub: "CONVERSATION", href: "/chat", position: "left-[0%] top-[28%]", angle: "-5deg" },
  { label: "AGENT", sub: "WORKFLOWS", href: "/dashboard", position: "right-[0%] top-[28%]", angle: "5deg" },
  { label: "VOICE", sub: "REAL-TIME", href: "/chat", position: "left-[0%] bottom-[22%]", angle: "4deg" },
  { label: "MEMORY", sub: "PERSONAL CONTEXT", href: "/settings", position: "right-[0%] bottom-[22%]", angle: "-4deg" },
];

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
    window.setTimeout(() => void ctx.close(), 1500);
  } catch {
    /* Audio can be unavailable until user interaction. */
  }
}

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
  const detailed = size >= 280;

  return (
    <div
      className="relative isolate flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      aria-label={`King Zarry AI human core: ${stateLabels[state].toLowerCase()}`}
      role="group"
    >
      {/* Real interface layers: orbital rings, connection paths, controls and status panels. */}
      <div
        aria-hidden="true"
        className="absolute rounded-full border border-cyan-300/20"
        style={{
          inset: "7%",
          transform: "rotate(-22deg) scaleY(.72)",
          boxShadow: `0 0 24px ${color}12, inset 0 0 22px ${color}08`,
          transition: "border-color 300ms ease, box-shadow 300ms ease",
          borderColor: `${color}38`,
        }}
      />
      <div
        aria-hidden="true"
        className="absolute rounded-full border border-dashed"
        style={{
          inset: "13%",
          transform: "rotate(28deg) scaleY(.82)",
          borderColor: `${color}55`,
          animation: "kz-core-orbit 28s linear infinite",
        }}
      />
      <div
        aria-hidden="true"
        className="absolute rounded-full"
        style={{
          inset: "19%",
          background: `radial-gradient(ellipse at 50% 45%, ${color}24 0%, ${color}0b 48%, transparent 74%)`,
          filter: active ? "blur(8px)" : "blur(14px)",
          transform: active ? "scale(1.05)" : "scale(1)",
          transition: "all 350ms ease",
        }}
      />

      {/* Connection rails are decorative paths; each destination is a real navigation link. */}
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox="0 0 320 320"
        fill="none"
      >
        <path d="M52 105 L105 125 L128 142" stroke={`${color}80`} strokeWidth="1" strokeDasharray="3 5" />
        <path d="M268 105 L215 125 L192 142" stroke={`${color}80`} strokeWidth="1" strokeDasharray="3 5" />
        <path d="M52 224 L104 205 L128 184" stroke={`${color}80`} strokeWidth="1" strokeDasharray="3 5" />
        <path d="M268 224 L216 205 L192 184" stroke={`${color}80`} strokeWidth="1" strokeDasharray="3 5" />
        <circle cx="128" cy="142" r="2.5" fill={color} />
        <circle cx="192" cy="142" r="2.5" fill={color} />
        <circle cx="128" cy="184" r="2.5" fill={color} />
        <circle cx="192" cy="184" r="2.5" fill={color} />
      </svg>

      {/* Portrait remains an image asset; all surrounding interface elements are live HTML. */}
      <div
        className="relative z-10 flex items-center justify-center overflow-hidden"
        style={{
          width: size * (detailed ? 0.43 : 0.76),
          height: size * (detailed ? 0.57 : 0.88),
          filter: `drop-shadow(0 0 ${active ? 24 : 15}px ${color}70)`,
          transition: "filter 300ms ease",
        }}
      >
        <img
          src="/human-ai-core.webp"
          alt="King Zarry AI human-style core portrait"
          className="h-full w-full object-contain"
          draggable={false}
        />
      </div>

      {modules.map((item) => (
        <Link
          key={item.label}
          href={item.href}
          className={`absolute z-20 ${item.position} flex flex-col rounded-lg border px-2 py-1.5 font-mono-tech transition duration-200 hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2`}
          style={{
            borderColor: `${color}70`,
            color,
            background: "linear-gradient(135deg, rgba(3,15,31,.96), rgba(3,10,22,.88))",
            boxShadow: `0 0 16px ${color}18, inset 0 0 10px ${color}08`,
            transform: `rotate(${detailed ? item.angle : "0deg"})`,
            minWidth: detailed ? size * 0.29 : undefined,
          }}
          aria-label={`Open ${item.label.toLowerCase()} module`}
        >
          <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.16em]">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: color, boxShadow: `0 0 7px ${color}` }}
              aria-hidden="true"
            />
            {item.label}
          </span>
          {detailed && <span className="mt-0.5 text-[6px] tracking-[0.12em] text-cyan-100/45">{item.sub}</span>}
        </Link>
      ))}

      {detailed && (
        <>
          <div className="absolute left-1/2 top-[5%] z-20 -translate-x-1/2 whitespace-nowrap rounded-full border px-2.5 py-1 font-mono-tech text-[7px] tracking-[0.2em]"
            style={{ borderColor: `${color}45`, color, background: "rgba(2,8,19,.88)" }}>
            KZ / HUMAN INTERFACE
          </div>
          <div className="absolute bottom-[4%] left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1.5 font-mono-tech text-[8px] tracking-[0.22em]"
            style={{ borderColor: `${color}55`, color, background: "rgba(2,8,19,.92)", boxShadow: `0 0 18px ${color}12` }}>
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" style={{ backgroundColor: color }} />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
            </span>
            CORE {stateLabels[state]}
          </div>
          <div className="absolute left-[2%] top-[48%] z-20 -translate-y-1/2 border-l-2 py-1 pl-1.5 font-mono-tech text-[6px] leading-3 tracking-[0.12em] text-cyan-100/55"
            style={{ borderColor: `${color}80` }}>
            <div>STATE</div>
            <div style={{ color }}>{stateLabels[state]}</div>
            <div className="mt-1">SIGNAL</div>
            <div style={{ color }}>ACTIVE</div>
          </div>
          <div className="absolute right-[2%] top-[48%] z-20 -translate-y-1/2 border-r-2 py-1 pr-1.5 text-right font-mono-tech text-[6px] leading-3 tracking-[0.12em] text-cyan-100/55"
            style={{ borderColor: `${color}80` }}>
            <div>MODULES</div>
            <div style={{ color }}>04 LINKED</div>
            <div className="mt-1">INTERFACE</div>
            <div style={{ color }}>ONLINE</div>
          </div>
        </>
      )}

      {!detailed && (
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2">
          <span
            className="whitespace-nowrap font-mono-tech text-[10px] uppercase tracking-[0.3em]"
            style={{ color, textShadow: `0 0 10px ${color}88` }}
          >
            {stateLabels[state]}
          </span>
        </div>
      )}
      <style jsx>{`
        @keyframes kz-core-orbit {
          from { transform: rotate(28deg) scaleY(.82); }
          to { transform: rotate(388deg) scaleY(.82); }
        }
        @media (prefers-reduced-motion: reduce) {
          div[style*="kz-core-orbit"] { animation: none !important; }
        }
      `}</style>
    </div>
  );
}
