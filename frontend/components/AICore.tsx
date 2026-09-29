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
      (window as unknown as { AudioContext?: typeof AudioContext })
        .AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();

    const play = (freq: number, start: number, duration: number) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + start);
      gain.gain.setValueAtTime(0, ctx.currentTime + start);
      gain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + start + 0.02);
      gain.gain.exponentialRampToValueAtTime(
        0.0001,
        ctx.currentTime + start + duration
      );
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
    // Audio blocked by browser until first interaction
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

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {active && (
        <>
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{ border: `1px solid ${color}` }}
          />
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{ border: `1px solid ${color}`, animationDelay: "0.8s" }}
          />
        </>
      )}

      <span
        className="kz-core-rotate absolute rounded-full"
        style={{ inset: size * 0.02, border: `1px dashed ${color}33` }}
      />

      <span
        className="kz-core-rotate-reverse absolute rounded-full"
        style={{
          inset: size * 0.1,
          border: `1px solid ${color}55`,
          boxShadow: `0 0 24px ${color}22, inset 0 0 24px ${color}11`,
        }}
      />

      <span
        className="kz-orbit absolute rounded-full"
        style={{
          inset: size * 0.06,
          animationDuration: active ? "3s" : "12s",
        }}
      >
        <span
          className="absolute rounded-full"
          style={{
            width: size * 0.028,
            height: size * 0.028,
            background: color,
            boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`,
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        />
      </span>

      <div
        className="kz-core-pulse absolute rounded-full"
        style={{
          inset: size * 0.2,
          background: `radial-gradient(circle, ${color}44 0%, ${color}11 40%, transparent 70%)`,
          boxShadow: `0 0 60px ${color}55, inset 0 0 40px ${color}33`,
        }}
      />

      <div
        className="absolute rounded-full"
        style={{
          inset: size * 0.28,
          border: `1px solid ${color}77`,
          opacity: 0.6,
        }}
      />

      {/* IQ Bot robot mascot — neon face from the selected Modern Dark Neon design. */}
      <div
        className="relative z-10 flex items-center justify-center rounded-[28%]"
        style={{
          width: size * 0.38,
          height: size * 0.38,
          background: "linear-gradient(145deg, rgba(5,18,28,.98), rgba(1,8,14,.98))",
          border: `1px solid ${color}99`,
          boxShadow: `0 0 28px ${color}66, 0 0 70px ${color}22, inset 0 0 28px ${color}22`,
        }}
      >
        <svg
          viewBox="0 0 160 160"
          className="h-[82%] w-[82%]"
          aria-label="IQ Bot robot"
          role="img"
        >
          <defs>
            <linearGradient id="iqRobotFace" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#e9ffff" stopOpacity=".98" />
              <stop offset="42%" stopColor={color} stopOpacity=".9" />
              <stop offset="100%" stopColor="#063442" stopOpacity=".98" />
            </linearGradient>
            <filter id="iqRobotGlow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          <path d="M52 32 Q80 14 108 32 L126 54 L121 112 Q80 138 39 112 L34 54 Z"
            fill="url(#iqRobotFace)" fillOpacity=".16" stroke={color} strokeWidth="3" filter="url(#iqRobotGlow)" />
          <path d="M48 52 Q80 35 112 52 L108 103 Q80 119 52 103 Z"
            fill="#020b12" stroke={color} strokeWidth="2" />
          <rect x="57" y="67" width="18" height="10" rx="5" fill="#fff" filter="url(#iqRobotGlow)" />
          <rect x="85" y="67" width="18" height="10" rx="5" fill="#fff" filter="url(#iqRobotGlow)" />
          <path d="M64 91 Q80 101 96 91" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <path d="M80 16 V30" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <circle cx="80" cy="11" r="6" fill={color} filter="url(#iqRobotGlow)" />
          <path d="M35 66 H24 M125 66 H136" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <circle cx="20" cy="66" r="4" fill={color} />
          <circle cx="140" cy="66" r="4" fill={color} />
          <path d="M58 119 L52 130 M102 119 L108 130" stroke={color} strokeWidth="3" strokeLinecap="round" />
        </svg>
      </div>

      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2">
        <span
          className="font-mono-tech text-[10px] tracking-[0.4em] uppercase"
          style={{ color, textShadow: `0 0 10px ${color}88` }}
        >
          {stateLabels[state]}
        </span>
      </div>
    </div>
  );
}
