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
        <svg viewBox="0 0 180 220" className="h-full w-full" role="img" aria-label="King Zarry AI neon circuit human profile">
          <defs>
            <linearGradient id="kzHumanSkin" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#baf7ff" />
              <stop offset="45%" stopColor={color} />
              <stop offset="100%" stopColor="#075078" />
            </linearGradient>
            <linearGradient id="kzProfileFill" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#071b32" stopOpacity=".98" />
              <stop offset="100%" stopColor="#020a19" stopOpacity=".92" />
            </linearGradient>
            <clipPath id="kzProfileClip">
              <path d="M128 203 L88 203 L76 183 L66 166 L47 161 L43 148 L29 140 L22 128 L30 117 L41 108 L47 91 L46 69 Q47 34 81 20 Q118 7 143 36 Q160 57 151 91 L145 111 L151 130 L139 148 L137 174 Z" />
            </clipPath>
            <filter id="kzHumanGlow"><feGaussianBlur stdDeviation="2.2" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          </defs>
          <path d="M128 203 L88 203 L76 183 L66 166 L47 161 L43 148 L29 140 L22 128 L30 117 L41 108 L47 91 L46 69 Q47 34 81 20 Q118 7 143 36 Q160 57 151 91 L145 111 L151 130 L139 148 L137 174 Z" fill="url(#kzProfileFill)" stroke="url(#kzHumanSkin)" strokeWidth="2.6" filter="url(#kzHumanGlow)" />
          <g clipPath="url(#kzProfileClip)" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 55 H71 V43 H112 V59 H158 M15 75 H62 V88 H93 V72 H151 M18 100 H54 V112 H91 V98 H160 M18 127 H57 V137 H105 V121 H151 M37 151 H79 V164 H124 V149 H155 M57 177 H100 V190 H144" stroke={color} strokeWidth="1.5" opacity=".9" />
            <path d="M72 28 V52 H88 V68 H116 V85 H139 M55 64 V81 H76 V98 H105 V115 H133 M51 118 V132 H73 V146 H101 V160 H125 M83 19 V39 H101 V50 M117 39 V66 H133 V78 M95 92 V110 H116 V128 M70 145 V170 H88 V184" stroke="#ff4c91" strokeWidth="1.2" opacity=".8" />
            <path d="M42 91 H63 V101 H81 M32 119 H50 V128 H68 M55 151 H73 M90 57 H103 M108 102 H123 M100 137 H117" stroke="#ffc66d" strokeWidth="2" />
            <path d="M49 66 L61 72 L49 78 M43 86 L55 92 L43 98 M47 109 L59 115 L47 121" stroke="#b9faff" strokeWidth="1.5" />
            <path d="M61 35 V48 M68 35 V48 M75 35 V48 M124 92 V106 M131 92 V106 M138 92 V106 M82 126 V140 M89 126 V140" stroke={color} strokeWidth="1.2" opacity=".9" />
            <circle cx="112" cy="59" r="3" fill="#ffc66d" stroke="none" /><circle cx="93" cy="98" r="3" fill="#ff4c91" stroke="none" /><circle cx="124" cy="149" r="3" fill={color} stroke="none" /><circle cx="61" cy="72" r="2" fill="#b9faff" stroke="none" />
          </g>
          <path d="M49 80 Q57 74 64 80 M46 98 L56 101 L51 107 M43 123 Q51 129 60 124" fill="none" stroke="#d8fbff" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M68 17 Q104 0 135 27" fill="none" stroke={color} strokeWidth="1.2" opacity=".85" />
          <circle cx="143" cy="36" r="3" fill="#ff4c91" /><circle cx="151" cy="91" r="2.5" fill="#ffc66d" /><circle cx="22" cy="128" r="2.5" fill={color} />
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
