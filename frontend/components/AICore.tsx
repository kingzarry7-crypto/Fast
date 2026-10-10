"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";

const stateColors: Record<CoreState, string> = {
  idle: "#00f0ff",
  thinking: "#a78bfa",
  speaking: "#34f5c5",
  listening: "#ffd166",
  error: "#ff416c",
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
      className={`kz-human-core relative isolate flex shrink-0 items-center justify-center ${active ? "is-active" : ""} state-${state}`}
      style={{ width: size, height: size, "--core-color": color } as React.CSSProperties}
      aria-label={`King Zarry AI human core: ${stateLabels[state].toLowerCase()}`}
      role="group"
    >
      <div aria-hidden="true" className="kz-core-aura absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-ring kz-core-ring-one absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-ring kz-core-ring-two absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-ring kz-core-ring-three absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-orbit kz-core-orbit-one absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-orbit kz-core-orbit-two absolute rounded-full" />
      <div aria-hidden="true" className="kz-core-sweep absolute" />

      <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 320 320" fill="none">
        <path className="kz-energy-line" d="M52 105 L105 125 L128 142" stroke={color} strokeWidth="1" strokeDasharray="3 7" />
        <path className="kz-energy-line reverse" d="M268 105 L215 125 L192 142" stroke={color} strokeWidth="1" strokeDasharray="3 7" />
        <path className="kz-energy-line reverse" d="M52 224 L104 205 L128 184" stroke={color} strokeWidth="1" strokeDasharray="3 7" />
        <path className="kz-energy-line" d="M268 224 L216 205 L192 184" stroke={color} strokeWidth="1" strokeDasharray="3 7" />
        {[ [128,142], [192,142], [128,184], [192,184] ].map(([cx, cy], i) => (
          <circle key={i} className="kz-energy-node" cx={cx} cy={cy} r="2.5" fill={color} />
        ))}
      </svg>

      {/* The dark edges of the portrait are blended into the app canvas; the app's own background shows through. */}
      <div className="kz-portrait-stage relative z-10 flex items-center justify-center"
        style={{ width: size * (detailed ? 0.46 : 0.78), height: size * (detailed ? 0.62 : 0.9) }}>
        <img src="/human-ai-core.webp" alt="King Zarry AI human-style core portrait"
          className="kz-portrait kz-portrait-main h-full w-full object-contain" draggable={false} />
        <img src="/human-ai-core.webp" alt="" aria-hidden="true"
          className="kz-portrait kz-portrait-glitch kz-portrait-cyan h-full w-full object-contain" draggable={false} />
        <img src="/human-ai-core.webp" alt="" aria-hidden="true"
          className="kz-portrait kz-portrait-glitch kz-portrait-magenta h-full w-full object-contain" draggable={false} />
        <div aria-hidden="true" className="kz-portrait-scanlines absolute inset-0" />
        <div aria-hidden="true" className="kz-portrait-shine absolute inset-0" />
      </div>

      {modules.map((item, index) => (
        <Link key={item.label} href={item.href}
          className={`kz-core-module absolute z-20 ${item.position} flex flex-col rounded-lg border px-2 py-1.5 font-mono-tech transition duration-200 hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2`}
          style={{
            borderColor: `${color}85`,
            color,
            background: "linear-gradient(135deg, rgba(3,15,31,.88), rgba(3,10,22,.68))",
            boxShadow: `0 0 20px ${color}26, inset 0 0 14px ${color}0e`,
            transform: `rotate(${detailed ? item.angle : "0deg"})`,
            minWidth: detailed ? size * 0.29 : undefined,
            animationDelay: `${index * -0.7}s`,
          }}
          aria-label={`Open ${item.label.toLowerCase()} module`}
        >
          <span className="flex items-center gap-1.5 text-[9px] font-bold tracking-[0.16em]">
            <span className="kz-module-dot inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: color, boxShadow: `0 0 9px ${color}` }} aria-hidden="true" />
            {item.label}
          </span>
          {detailed && <span className="mt-0.5 text-[6px] tracking-[0.12em] text-cyan-100/60">{item.sub}</span>}
        </Link>
      ))}

      {detailed && (
        <>
          <div className="absolute left-1/2 top-[5%] z-20 -translate-x-1/2 whitespace-nowrap rounded-full border px-2.5 py-1 font-mono-tech text-[7px] tracking-[0.2em]"
            style={{ borderColor: `${color}60`, color, background: "rgba(2,8,19,.72)", boxShadow: `0 0 18px ${color}20` }}>
            KZ / HUMAN INTERFACE
          </div>
          <div className="absolute bottom-[4%] left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1.5 font-mono-tech text-[8px] tracking-[0.22em]"
            style={{ borderColor: `${color}70`, color, background: "rgba(2,8,19,.76)", boxShadow: `0 0 22px ${color}20` }}>
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-70" style={{ backgroundColor: color }} />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
            </span>
            CORE {stateLabels[state]}
          </div>
          <div className="absolute left-[2%] top-[48%] z-20 -translate-y-1/2 border-l-2 py-1 pl-1.5 font-mono-tech text-[6px] leading-3 tracking-[0.12em] text-cyan-100/65"
            style={{ borderColor: `${color}95` }}>
            <div>STATE</div><div style={{ color }}>{stateLabels[state]}</div>
            <div className="mt-1">SIGNAL</div><div style={{ color }}>LIVE</div>
          </div>
          <div className="absolute right-[2%] top-[48%] z-20 -translate-y-1/2 border-r-2 py-1 pr-1.5 text-right font-mono-tech text-[6px] leading-3 tracking-[0.12em] text-cyan-100/65"
            style={{ borderColor: `${color}95` }}>
            <div>MODULES</div><div style={{ color }}>04 LINKED</div>
            <div className="mt-1">MODE</div><div style={{ color }}>HOLOGRAPHIC</div>
          </div>
        </>
      )}

      {!detailed && (
        <div className="absolute -bottom-3 left-1/2 -translate-x-1/2">
          <span className="whitespace-nowrap font-mono-tech text-[10px] uppercase tracking-[0.3em]"
            style={{ color, textShadow: `0 0 10px ${color}, 0 0 22px ${color}99` }}>
            {stateLabels[state]}
          </span>
        </div>
      )}

      <style jsx>{`
        .kz-human-core { --core-color: #00f0ff; isolation: isolate; }
        .kz-core-aura {
          inset: 17%;
          background: radial-gradient(ellipse at 50% 48%, color-mix(in srgb, var(--core-color) 38%, transparent), color-mix(in srgb, var(--core-color) 13%, transparent) 43%, transparent 72%);
          filter: blur(10px);
          animation: kz-aura-breathe 2.8s ease-in-out infinite;
        }
        .kz-core-ring { pointer-events: none; border: 1px solid color-mix(in srgb, var(--core-color) 58%, transparent); }
        .kz-core-ring-one { inset: 9%; transform: rotate(-22deg) scaleY(.72); box-shadow: 0 0 24px color-mix(in srgb, var(--core-color) 22%, transparent), inset 0 0 22px color-mix(in srgb, var(--core-color) 12%, transparent); animation: kz-ring-breathe 3.2s ease-in-out infinite; }
        .kz-core-ring-two { inset: 13%; border-style: dashed; opacity: .8; transform: rotate(28deg) scaleY(.82); animation: kz-core-orbit 13s linear infinite; }
        .kz-core-ring-three { inset: 22%; border-style: dotted; opacity: .55; transform: rotate(-40deg) scaleY(.64); animation: kz-core-orbit-reverse 19s linear infinite; }
        .kz-core-orbit { inset: 4%; border: 1px solid transparent; border-top-color: color-mix(in srgb, var(--core-color) 90%, transparent); border-bottom-color: color-mix(in srgb, var(--core-color) 30%, transparent); transform: rotate(25deg) scaleY(.44); filter: drop-shadow(0 0 5px var(--core-color)); animation: kz-core-orbit 8s linear infinite; }
        .kz-core-orbit-two { inset: 1%; border-top-color: rgba(255, 65, 160, .6); border-bottom-color: rgba(0, 240, 255, .35); transform: rotate(-25deg) scaleY(.3); animation-duration: 11s; animation-direction: reverse; }
        .kz-core-sweep { z-index: 11; left: 12%; right: 12%; height: 2px; top: 10%; opacity: .8; background: linear-gradient(90deg, transparent, var(--core-color), white, var(--core-color), transparent); box-shadow: 0 0 12px var(--core-color); animation: kz-sweep 3.2s ease-in-out infinite; pointer-events: none; }
        .kz-portrait-stage { isolation: isolate; animation: kz-portrait-float 4s ease-in-out infinite; filter: drop-shadow(0 0 12px color-mix(in srgb, var(--core-color) 58%, transparent)); }
        .kz-portrait { position: absolute; inset: 0; display: block; object-fit: contain; user-select: none; pointer-events: none; -webkit-user-drag: none; }
        .kz-portrait-main { z-index: 2; mix-blend-mode: screen; filter: brightness(1.14) contrast(1.12) saturate(1.16); -webkit-mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 53%, rgba(0,0,0,.92) 68%, transparent 100%); mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 53%, rgba(0,0,0,.92) 68%, transparent 100%); animation: kz-human-breathe 3.8s ease-in-out infinite; }
        .kz-portrait-glitch { z-index: 3; opacity: 0; mix-blend-mode: screen; -webkit-mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 50%, transparent 100%); mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 50%, transparent 100%); }
        .kz-portrait-cyan { filter: sepia(1) saturate(6) hue-rotate(145deg) brightness(1.8); animation: kz-glitch-cyan 5.5s steps(1,end) infinite; }
        .kz-portrait-magenta { filter: sepia(1) saturate(7) hue-rotate(265deg) brightness(1.5); animation: kz-glitch-magenta 6.7s steps(1,end) infinite; }
        .kz-portrait-scanlines { z-index: 4; pointer-events: none; opacity: .32; background: repeating-linear-gradient(to bottom, transparent 0 4px, rgba(105,245,255,.2) 5px, transparent 6px); mix-blend-mode: screen; animation: kz-scan-drift 7s linear infinite; -webkit-mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 48%, transparent 100%); mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 48%, transparent 100%); }
        .kz-portrait-shine { z-index: 5; pointer-events: none; background: linear-gradient(115deg, transparent 28%, rgba(102,245,255,.22) 48%, transparent 62%); mix-blend-mode: screen; opacity: .65; animation: kz-shine 5.2s ease-in-out infinite; -webkit-mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 45%, transparent 100%); mask-image: radial-gradient(ellipse 48% 49% at 50% 47%, #000 45%, transparent 100%); }
        .kz-energy-line { stroke-dashoffset: 0; animation: kz-energy-flow 2.4s linear infinite; filter: drop-shadow(0 0 3px var(--core-color)); }
        .kz-energy-line.reverse { animation-direction: reverse; animation-duration: 3s; }
        .kz-energy-node { animation: kz-node-flash 1.8s ease-in-out infinite; filter: drop-shadow(0 0 4px var(--core-color)); }
        .kz-core-module { backdrop-filter: blur(8px); animation: kz-module-float 4.4s ease-in-out infinite; }
        .kz-module-dot { animation: kz-dot-pulse 1.4s ease-in-out infinite; }
        .is-active .kz-portrait-stage { animation-duration: 1.6s; }
        .state-thinking .kz-portrait-main { animation-duration: 1.15s; filter: brightness(1.35) contrast(1.15) saturate(1.4) hue-rotate(12deg); }
        .state-speaking .kz-portrait-main { animation-duration: .72s; filter: brightness(1.5) contrast(1.18) saturate(1.45); }
        .state-listening .kz-portrait-main { animation-duration: 1.2s; filter: brightness(1.4) contrast(1.2) hue-rotate(-12deg); }
        .state-error .kz-portrait-main { filter: brightness(1.4) sepia(.2) saturate(2) hue-rotate(300deg); }
        .is-active .kz-portrait-cyan { animation-duration: 2.2s; }
        .is-active .kz-portrait-magenta { animation-duration: 2.8s; }
        @keyframes kz-core-orbit { from { transform: rotate(0deg) scaleY(.82); } to { transform: rotate(360deg) scaleY(.82); } }
        @keyframes kz-core-orbit-reverse { from { transform: rotate(360deg) scaleY(.64); } to { transform: rotate(0deg) scaleY(.64); } }
        @keyframes kz-ring-breathe { 0%,100% { opacity: .55; scale: .97; } 50% { opacity: 1; scale: 1.035; } }
        @keyframes kz-aura-breathe { 0%,100% { opacity: .62; scale: .94; } 50% { opacity: 1; scale: 1.08; } }
        @keyframes kz-portrait-float { 0%,100% { transform: translateY(0) rotate(-.6deg); } 50% { transform: translateY(-5px) rotate(.6deg); } }
        @keyframes kz-human-breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.018); } }
        @keyframes kz-sweep { 0% { top: 12%; opacity: 0; } 12% { opacity: .9; } 88% { opacity: .9; } 100% { top: 88%; opacity: 0; } }
        @keyframes kz-scan-drift { from { transform: translateY(-8%); } to { transform: translateY(8%); } }
        @keyframes kz-shine { 0%,100% { transform: translateX(-32%); opacity: .18; } 50% { transform: translateX(32%); opacity: .8; } }
        @keyframes kz-energy-flow { to { stroke-dashoffset: -40; } }
        @keyframes kz-node-flash { 0%,100% { opacity: .45; r: 2; } 50% { opacity: 1; r: 3.5; } }
        @keyframes kz-module-float { 0%,100% { translate: 0 0; } 50% { translate: 0 -3px; } }
        @keyframes kz-dot-pulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
        @keyframes kz-glitch-cyan { 0%,87%,90%,100% { opacity: 0; transform: translateX(0); clip-path: inset(0 0 0 0); } 88% { opacity: .48; transform: translateX(-4px); clip-path: inset(12% 0 64% 0); } 89% { opacity: .35; transform: translateX(3px); clip-path: inset(43% 0 35% 0); } }
        @keyframes kz-glitch-magenta { 0%,72%,75%,100% { opacity: 0; transform: translateX(0); clip-path: inset(0 0 0 0); } 73% { opacity: .38; transform: translateX(4px); clip-path: inset(28% 0 52% 0); } 74% { opacity: .28; transform: translateX(-3px); clip-path: inset(63% 0 17% 0); } }
        @media (prefers-reduced-motion: reduce) {
          .kz-human-core *, .kz-human-core *::before, .kz-human-core *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; }
        }
      `}</style>
    </div>
  );
}
