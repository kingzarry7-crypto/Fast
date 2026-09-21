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

    // Three-note ascending chime
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

      <div
        className="relative rounded-full"
        style={{
          width: size * 0.3,
          height: size * 0.3,
          background: `radial-gradient(circle at 35% 35%, #ffffff 0%, ${color} 40%, ${color}88 100%)`,
          boxShadow: `0 0 40px ${color}, 0 0 80px ${color}88, inset 0 0 20px #ffffff44`,
        }}
      />

      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.06,
          height: size * 0.06,
          background: "#ffffff",
          boxShadow: `0 0 20px #ffffff, 0 0 40px ${color}`,
        }}
      />

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
