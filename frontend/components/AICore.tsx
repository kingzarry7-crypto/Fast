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
  idle: "SYSTEM ACTIVE",
  thinking: "PROCESSING",
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
    // Audio blocked until first interaction
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
  const faceSize = size * 0.72;

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {active && (
        <>
          <span
            className="kz-core-ring absolute inset-0 rounded-full pointer-events-none"
            style={{ border: `1px solid ${color}` }}
          />
          <span
            className="kz-core-ring absolute inset-0 rounded-full pointer-events-none"
            style={{ border: `1px solid ${color}`, animationDelay: "0.8s" }}
          />
        </>
      )}

      <span
        className="kz-core-rotate absolute rounded-full pointer-events-none"
        style={{
          inset: size * 0.02,
          border: `1px dashed ${color}44`,
        }}
      />

      <span
        className="kz-core-rotate-reverse absolute rounded-full pointer-events-none"
        style={{
          inset: size * 0.06,
          border: `2px solid ${color}88`,
          boxShadow: `0 0 28px ${color}33, inset 0 0 24px ${color}18`,
        }}
      />

      <span
        className="kz-orbit absolute rounded-full pointer-events-none"
        style={{
          inset: size * 0.04,
          animationDuration: active ? "3s" : "14s",
        }}
      >
        <span
          className="absolute rounded-full"
          style={{
            width: size * 0.025,
            height: size * 0.025,
            background: color,
            boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`,
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        />
      </span>

      <div
        className="absolute left-1/2 -translate-x-1/2 pointer-events-none z-20"
        style={{ top: size * 0.04 }}
      >
        <span
          className="font-mono-tech font-bold tracking-[0.25em] uppercase whitespace-nowrap"
          style={{
            fontSize: Math.max(8, size * 0.045),
            color,
            textShadow: `0 0 12px ${color}aa`,
          }}
        >
          KING ZARRY AI CORE
        </span>
      </div>

      <div
        className="relative z-10 overflow-hidden rounded-full"
        style={{
          width: faceSize,
          height: faceSize,
          boxShadow: `0 0 40px ${color}55, 0 0 80px ${color}33`,
          border: `1px solid ${color}66`,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/king-zarry-core.jpg"
          alt="King Zarry AI Core"
          width={faceSize}
          height={faceSize}
          className="h-full w-full object-cover object-center"
          style={{
            filter:
              state === "error"
                ? "grayscale(0.3) saturate(1.1) brightness(0.9)"
                : active
                  ? "saturate(1.15) brightness(1.05)"
                  : "saturate(1.05)",
          }}
          draggable={false}
        />

        <div
          className="pointer-events-none absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle at 50% 40%, transparent 45%, ${color}22 75%, #020914cc 100%)`,
            mixBlendMode: "screen",
            opacity: 0.55,
          }}
        />

        <div
          className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-sm"
          style={{
            width: faceSize * 0.55,
            height: faceSize * 0.7,
            border: `1px solid ${color}55`,
            boxShadow: `inset 0 0 20px ${color}22`,
          }}
        />
      </div>

      <div
        className="absolute z-20 pointer-events-none"
        style={{
          left: 0,
          bottom: size * 0.02,
          maxWidth: size * 0.48,
        }}
      >
        <div
          className="rounded border px-2 py-1 backdrop-blur-sm"
          style={{
            borderColor: `${color}55`,
            background: "rgba(2, 9, 20, 0.75)",
          }}
        >
          <p
            className="font-mono-tech tracking-widest uppercase leading-tight"
            style={{
              fontSize: Math.max(7, size * 0.032),
              color: `${color}99`,
            }}
          >
            HUMAN INTELLIGENCE CORE
          </p>
          <p
            className="font-mono-tech font-bold tracking-wider uppercase leading-tight"
            style={{
              fontSize: Math.max(8, size * 0.038),
              color,
              textShadow: `0 0 8px ${color}88`,
            }}
          >
            {stateLabels[state]}
          </p>
        </div>
      </div>

      <div
        className="absolute z-20 pointer-events-none"
        style={{
          right: 0,
          bottom: size * 0.02,
          maxWidth: size * 0.42,
        }}
      >
        <div
          className="rounded border px-2 py-1 backdrop-blur-sm text-right"
          style={{
            borderColor: `${color}44`,
            background: "rgba(2, 9, 20, 0.75)",
          }}
        >
          <p
            className="font-mono-tech tracking-widest uppercase leading-tight"
            style={{
              fontSize: Math.max(7, size * 0.032),
              color: `${color}99`,
            }}
          >
            NEURAL NETWORK
          </p>
          <p
            className="font-mono-tech tracking-wider uppercase leading-tight"
            style={{
              fontSize: Math.max(7, size * 0.032),
              color: active ? color : `${color}aa`,
            }}
          >
            {active ? "ONLINE" : "STANDBY"}
          </p>
        </div>
      </div>
    </div>
  );
}
