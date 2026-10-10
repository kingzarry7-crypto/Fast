"use client";

/** Compact holographic human-core mark used across the King Zarry AI interface. */
export default function RobotHead({
  size = 36,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  const id = "kzHumanMark";
  return (
    <div
      className={"relative shrink-0 rounded-xl border border-cyan-400/50 bg-[#020b18] flex items-center justify-center overflow-hidden shadow-[0_0_16px_rgba(0,240,255,0.35)] " + className}
      style={{ width: size, height: size }}
      aria-label="King Zarry AI human core"
    >
      <span className="absolute inset-0 rounded-xl border border-cyan-300/20 animate-pulse pointer-events-none" />
      <svg viewBox="0 0 100 100" className="relative z-10 h-[91%] w-[91%]" role="img" aria-label="Holographic human face">
        <defs>
          <linearGradient id={id + "Face"} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f1ffff" />
            <stop offset="46%" stopColor="#00f0ff" />
            <stop offset="100%" stopColor="#087c9a" />
          </linearGradient>
          <filter id={id + "Glow"}><feGaussianBlur stdDeviation="1.3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <circle cx="50" cy="48" r="37" fill="#00dfff" fillOpacity=".06" stroke="#00dfff" strokeOpacity=".45" strokeWidth="1" />
        <path d="M18 91 Q22 72 39 69 L43 64 H57 L61 69 Q78 72 82 91" fill="#063247" fillOpacity=".7" stroke="#00dfff" strokeWidth="1.8" filter={`url(#${id}Glow)`} />
        <path d="M34 33 Q35 15 50 15 Q67 15 67 35 L64 52 Q62 65 50 70 Q38 65 36 52 Z" fill="#061a29" stroke={`url(#${id}Face)`} strokeWidth="2.5" filter={`url(#${id}Glow)`} />
        <path d="M34 35 Q34 14 50 14 Q65 14 67 34 L59 28 L52 23 Q45 31 35 30 Z" fill="#00dfff" fillOpacity=".45" stroke="#00dfff" strokeWidth="1" />
        <path d="M40 41 Q45 38 48 41 M53 41 Q57 38 61 41" fill="none" stroke="#f1ffff" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M50 42 L47 51 L52 52 M44 59 Q50 63 56 59" fill="none" stroke="#00f0ff" strokeWidth="1.8" strokeLinecap="round" />
        <path d="M12 48 H22 M78 48 H88 M50 4 V12" stroke="#00f0ff" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="10" cy="48" r="2" fill="#00f0ff" /><circle cx="90" cy="48" r="2" fill="#00f0ff" /><circle cx="50" cy="4" r="2.5" fill="#00f0ff" />
      </svg>
    </div>
  );
}
